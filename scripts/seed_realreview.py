#!/usr/bin/env python3
"""Safely enrich saved public campaigns with verified RealReview open listings."""
import json
from collect import OUT, realreview

def main():
    items=realreview()
    if not items:
        raise SystemExit("No verified public, currently recruiting RealReview media campaigns.")
    stored=json.loads(OUT.read_text(encoding="utf-8"))
    by_id={row["id"]:row for row in stored}
    for row in items:
        previous=by_id.get(row["id"])
        if previous:
            row["first_seen_at"]=previous.get("first_seen_at",row["first_seen_at"])
            if not row.get("image_url") and previous.get("image_url"):
                row["image_url"]=previous["image_url"]
        by_id[row["id"]]=row
    merged=sorted(by_id.values(),key=lambda x:(x["source_id"],x["id"]))
    OUT.write_text(json.dumps(merged,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("RealReview verified:",len(items),"snapshot:",len(merged),flush=True)

if __name__=="__main__":
    main()
