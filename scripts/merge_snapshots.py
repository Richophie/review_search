#!/usr/bin/env python3
"""Merge independently collected real campaigns with the latest remote snapshot.

Usage:
  python scripts/merge_snapshots.py REMOTE_JSON BACKFILL_JSON OUTPUT_JSON

Preserve all verified sources, the newest observed details per source campaign,
and the oldest first-seen timestamp. No synthesized campaigns or data.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KST=timezone(timedelta(hours=9))
TODAY=datetime.now(KST).date()
NOW=datetime.now(timezone.utc)
remote_path, backfill_path, target_path=map(Path,sys.argv[1:4])
remote=json.loads(remote_path.read_text(encoding="utf-8"))
backfill=json.loads(backfill_path.read_text(encoding="utf-8"))
assert isinstance(remote,list) and isinstance(backfill,list)
def timestamp(text):
    return datetime.fromisoformat(text.replace("Z","+00:00"))
def valid(row):
    if not isinstance(row,dict) or not row.get("id") or not row.get("original_url"):
        return False
    deadline=row.get("apply_deadline")
    last=timestamp(row["last_seen_at"]).astimezone(timezone.utc)
    if deadline:
        return date.fromisoformat(deadline)>=TODAY and last>=NOW-timedelta(days=21)
    return (
        row.get("deadline_precision")=="unknown"
        and row.get("open_verified") is True
        and last>=NOW-timedelta(hours=48)
    )
combined={}
for row in remote+backfill:
    if not valid(row):
        continue
    key=row["id"]
    existing=combined.get(key)
    if existing is None:
        combined[key]=row.copy()
        continue
    newer=row if timestamp(row["last_seen_at"])>timestamp(existing["last_seen_at"]) else existing
    older_first=min(timestamp(row["first_seen_at"]),timestamp(existing["first_seen_at"]))
    newer=newer.copy()
    newer["first_seen_at"]=older_first.isoformat()
    combined[key]=newer
# The source ID is stable, but if a site changes its IDs for the same URL,
# display that live URL only once.
by_url={}
for row in combined.values():
    url=row["original_url"]
    if url not in by_url or timestamp(row["last_seen_at"])>timestamp(by_url[url]["last_seen_at"]):
        by_url[url]=row
out=sorted(by_url.values(),key=lambda x:(x["source_id"],x["id"]))
target_path.write_text(json.dumps(out,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
per={}
for row in out:
    per[row["source_id"]]=per.get(row["source_id"],0)+1
print("Merged",len(remote),"current +",len(backfill),"backfill =>",len(out),"verified live URLs",flush=True)
print("Breakdown:",dict(sorted(per.items())),flush=True)
