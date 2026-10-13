#!/usr/bin/env python3
"""Backfill media from original-title badges; merge also preserves the evidence."""
import json
from pathlib import Path
from collect import media_from_bracketed_title

path=Path("public/data/campaigns.json")
rows=json.loads(path.read_text(encoding="utf-8"))
sources={"bqueens","modan"}
count={}
for row in rows:
    source=row.get("source_id")
    if source not in sources or row.get("channels"):
        continue
    channels=media_from_bracketed_title(row.get("title") or "")
    if not channels:
        continue
    row["channels"]=channels
    row["search_text"]=" ".join([row.get("search_text") or "",*channels]).strip().lower()
    count[source]=count.get(source,0)+1
print("Verified explicit channel tags applied",count,"total",sum(count.values()),flush=True)
if count:
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
