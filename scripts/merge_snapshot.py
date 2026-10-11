#!/usr/bin/env python3
"""Merge an independently collected snapshot with the newest main snapshot.

This runs only after a collector has validated its own output. GitHub Actions
refreshes main before invoking it, so a simultaneous browser collector cannot
silently replace campaigns found by the other collector.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
DEST = Path("public/data/campaigns.json")


def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    return datetime.min.replace(tzinfo=timezone.utc)


def read_rows(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Campaign snapshot must be a JSON array: " + str(path))
    for row in data:
        if not isinstance(row, dict) or not row.get("id") or not row.get("original_url"):
            raise ValueError("Invalid campaign record in " + str(path))
    return data


def combined(existing, incoming, now):
    merged = {}
    for row in [*existing, *incoming]:
        cid = row["id"]
        old = merged.get(cid)
        if old is None:
            merged[cid] = dict(row)
            continue

        # Prefer the source observation made more recently, not the last
        # workflow to finish or the last process to push its commit.
        if timestamp(row.get("last_seen_at")) >= timestamp(old.get("last_seen_at")):
            winner, loser = dict(row), old
        else:
            winner, loser = dict(old), row

        first = min(
            (v for v in (winner.get("first_seen_at"), loser.get("first_seen_at"))
             if v and timestamp(v) != datetime.min.replace(tzinfo=timezone.utc)),
            key=timestamp,
            default=None,
        )
        if first:
            winner["first_seen_at"] = first
        if not winner.get("image_url") and loser.get("image_url"):
            winner["image_url"] = loser["image_url"]
        if not winner.get("published_at") and loser.get("published_at"):
            winner["published_at"] = loser["published_at"]
        merged[cid] = winner

    today = now.date().isoformat()
    cutoff = now - timedelta(days=21)
    unknown_cutoff = now - timedelta(hours=48)

    def active(row):
        observed = timestamp(row.get("last_seen_at"))
        deadline = row.get("apply_deadline")
        if deadline is not None:
            return isinstance(deadline, str) and deadline >= today and observed >= cutoff
        return (row.get("deadline_precision") == "unknown"
                and row.get("open_verified") is True and observed >= unknown_cutoff)

    # Keep one canonical ID per URL even if two collectors discovered it under
    # different IDs; the more recently observed listing wins.
    by_url = {}
    for row in merged.values():
        if not active(row):
            continue
        url = row["original_url"]
        prev = by_url.get(url)
        if prev is None or timestamp(row.get("last_seen_at")) > timestamp(prev.get("last_seen_at")):
            by_url[url] = row

    rows = sorted(by_url.values(), key=lambda r: (r["source_id"], r["id"]))
    return rows


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/merge_snapshot.py INCOMING_SNAPSHOT.json")
    incoming = read_rows(sys.argv[1])
    existing = read_rows(DEST) if DEST.exists() else []
    rows = combined(existing, incoming, datetime.now(KST))
    if not rows:
        raise SystemExit("Refusing to replace a populated snapshot with zero active campaigns")
    DEST.write_text(json.dumps(rows, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"Merged public snapshot: {len(existing)} current + {len(incoming)} collected -> {len(rows)} unique active")


if __name__ == "__main__":
    main()
