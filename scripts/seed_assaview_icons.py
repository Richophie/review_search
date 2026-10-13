#!/usr/bin/env python3
"""Refresh Assaview media from robots-permitted public campaign cards."""
import json
from collect import OUT, assaview

items=assaview()
if not items:
    raise SystemExit("No verified public Assaview cards; preserving snapshot")
current=json.loads(OUT.read_text(encoding="utf-8"))
by_id={r["id"]:r for r in current}
observed=0
for row in items:
    previous=by_id.get(row["id"])
    if previous:
        row["first_seen_at"]=previous.get("first_seen_at",row["first_seen_at"])
        if not row.get("image_url") and previous.get("image_url"):
            row["image_url"]=previous["image_url"]
        if not row.get("published_at") and previous.get("published_at"):
            row["published_at"]=previous["published_at"]
    if row.get("media_evidence"):
        observed+=1
    by_id[row["id"]]=row
rows=sorted(by_id.values(),key=lambda r:(r["source_id"],r["id"]))
OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
print("Assaview verified public cards",len(items),"icon-verified",observed,"total",len(rows),flush=True)
