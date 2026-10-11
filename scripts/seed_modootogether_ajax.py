#!/usr/bin/env python3
"""Public ModooTogether AJAX listing refresher. No private sources."""
import json
from collect import OUT, modootogether_ajax

def main():
    items=modootogether_ajax()
    if not items:
        raise SystemExit("No verified public ModooTogether recruiting listings")
    existing=json.loads(OUT.read_text(encoding="utf-8"))
    by_id={row["id"]:row for row in existing}
    for row in items:
        old=by_id.get(row["id"])
        if old:
            row["first_seen_at"]=old.get("first_seen_at",row["first_seen_at"])
            if not row.get("image_url") and old.get("image_url"):
                row["image_url"]=old["image_url"]
        by_id[row["id"]]=row
    rows=sorted(by_id.values(),key=lambda r:(r["source_id"],r["id"]))
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("ModooTogether AJAX verified:",len(items),"snapshot:",len(rows),flush=True)
if __name__=="__main__":
    main()
