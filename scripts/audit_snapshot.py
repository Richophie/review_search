#!/usr/bin/env python3
"""Audit the current verified snapshot. No external requests or inferred values."""
import collections
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
today = datetime.now(KST).date().isoformat()
data_path = Path("public/data/campaigns.json")
out_path = Path("public/data/collection_status.json")
rows = json.loads(data_path.read_text(encoding="utf-8"))

sources = collections.defaultdict(list)
media = collections.Counter()
unknown_deadline = 0
published_today = 0
missing_media = 0
seen_ids, seen_urls = set(), set()
duplicates = []
for r in rows:
    cid, url = r.get("id"), r.get("original_url")
    if cid in seen_ids or url in seen_urls:
        duplicates.append(cid)
    seen_ids.add(cid)
    seen_urls.add(url)
    sources[r.get("source_id", "unknown")].append(r)
    channels = r.get("channels") or []
    if not channels:
        missing_media += 1
    for ch in set(channels):
        media[ch] += 1
    if r.get("apply_deadline") is None:
        unknown_deadline += 1
    published = r.get("published_at")
    if published:
        try:
            published_day = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(KST).date().isoformat()
            if published_day == today:
                published_today += 1
        except (TypeError, ValueError):
            pass

def observed_recently(value, hours):
    if not isinstance(value, str):
        return False
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if when.tzinfo is None:
            return False
        age = datetime.now(timezone.utc) - when.astimezone(timezone.utc)
        return timedelta(0) <= age <= timedelta(hours=hours)
    except (ValueError, TypeError, OverflowError):
        return False


scan_meta = {}
scan_dir = Path("public/data/scans")
if scan_dir.exists():
    for file in sorted(scan_dir.glob("*.json")):
        try:
            scan = json.loads(file.read_text(encoding="utf-8"))
            source = scan.get("source_id")
            if source in sources:
                scan_meta[source] = {
                    "last_scan_at": scan.get("scanned_at"),
                    "verified_during_last_scan": scan.get("unique_verified"),
                    "discovered_list_urls": scan.get("discovered_list_urls"),
                    "scan_complete": scan.get("complete") is True,
                    "traversal_capped": scan.get("traversal_capped"),
                    "discovery_failures": len(scan.get("failed_discovery_urls") or []),
                    "collection_failures": len(scan.get("failed_collection_urls") or []),
                }
        except (ValueError, OSError, TypeError) as error:
            print("Skipping invalid scan manifest", file, str(error)[:120])

result = {
    "as_of_date_kst": today,
    "snapshot_records": len(rows),
    "target_records": 20000,
    "records_to_target": max(0, 20000 - len(rows)),
    "target_progress_pct": round(min(100.0, 100 * len(rows) / 20000), 2),
    "platforms_with_records": len(sources),
    "source_scan_status": scan_meta,
    "source_observation_freshness": {
        name: {
            "retained_records": len(items),
            "seen_last_24h": sum(observed_recently(r.get("last_seen_at"), 24) for r in items),
            "seen_last_48h": sum(observed_recently(r.get("last_seen_at"), 48) for r in items),
            "not_reverified_last_48h": sum(not observed_recently(r.get("last_seen_at"), 48) for r in items),
            "full_coverage_proven": scan_meta.get(name, {}).get("scan_complete") is True,
        }
        for name, items in sorted(sources.items())
    },
    "source_last_observed": {name: max((str(r.get("last_seen_at") or "") for r in items), default="") for name, items in sorted(sources.items())},
    "media_counts": dict(sorted(media.items())),
    "media_unknown": missing_media,
    "deadline_unknown": unknown_deadline,
    "images_present": sum(bool(r.get("image_url")) for r in rows),
    "images_missing": sum(not r.get("image_url") for r in rows),
    "images_missing_sources": {name: sum(not r.get("image_url") for r in items) for name, items in sorted(sources.items()) if any(not r.get("image_url") for r in items)},
    "media_unknown_sources": {name: sum(not (r.get("channels") or []) for r in items) for name, items in sorted(sources.items()) if any(not (r.get("channels") or []) for r in items)},
    "published_today_confirmed": published_today,
    "duplicate_id_or_original_url_count": len(duplicates),
    "sources": {
        name: {
            "records": len(items),
            "images_present": sum(bool(r.get("image_url")) for r in items),
            "images_missing": sum(not r.get("image_url") for r in items),
            "media_unknown": sum(not (r.get("channels") or []) for r in items),
            "deadline_unknown": sum(r.get("apply_deadline") is None for r in items),
        }
        for name, items in sorted(sources.items())
    },
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if duplicates:
    raise SystemExit("Snapshot audit failed: duplicate IDs or original URLs")
