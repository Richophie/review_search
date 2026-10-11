#!/usr/bin/env python3
"""Merge verified public Bloglab campaigns into the shared snapshot."""
import json
from collect import OUT,bloglab
def main():
    entries=bloglab()
    if not entries:
        raise SystemExit("No verified Bloglab public recruiting campaigns")
    saved=json.loads(OUT.read_text(encoding="utf-8"))
    by_id={entry["id"]:entry for entry in saved}
    for row in entries:
        previous=by_id.get(row["id"])
        if previous:
            row["first_seen_at"]=previous.get("first_seen_at",row["first_seen_at"])
            if not row.get("image_url") and previous.get("image_url"):
                row["image_url"]=previous["image_url"]
        by_id[row["id"]]=row
    result=sorted(by_id.values(),key=lambda x:(x["source_id"],x["id"]))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("Bloglab verified:",len(entries),"snapshot:",len(result),flush=True)
if __name__=="__main__":
    main()
