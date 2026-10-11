#!/usr/bin/env python3
"""Enrich source snapshot from official Odiya campaign cards and details."""
import json
from collect import OUT, odiya

def main():
    rows=odiya()
    if not rows:
        raise SystemExit("No Odiya public cards passed title and application-D-day verification")
    current=json.loads(OUT.read_text(encoding="utf-8"))
    byid={r["id"]:r for r in current}
    for r in rows:
        prev=byid.get(r["id"])
        if prev:
            r["first_seen_at"]=prev.get("first_seen_at",r["first_seen_at"])
            if not r.get("image_url") and prev.get("image_url"):
                r["image_url"]=prev["image_url"]
        byid[r["id"]]=r
    result=sorted(byid.values(),key=lambda x:(x["source_id"],x["id"]))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("Odiya verified:",len(rows),"snapshot:",len(result),flush=True)

if __name__=="__main__":
    main()
