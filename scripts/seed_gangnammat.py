#!/usr/bin/env python3
"""Targeted, publicly permitted Gangnam Matzip snapshot enrichment."""
import json
from collect import OUT, gangnammat

def main():
    items = gangnammat()
    if not items:
        raise SystemExit("No verified Gangnam Matzip public cards; preserve existing dataset.")
    stored = json.loads(OUT.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in stored}
    for item in items:
        old = by_id.get(item["id"])
        if old:
            item["first_seen_at"] = old.get("first_seen_at", item["first_seen_at"])
            if not item.get("image_url") and old.get("image_url"):
                item["image_url"] = old["image_url"]
        by_id[item["id"]] = item
    merged = sorted(by_id.values(), key=lambda r: (r["source_id"], r["id"]))
    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"Gangnam Matzip seed: {len(items)} verified public listings; snapshot {len(merged)}")

if __name__ == "__main__":
    main()
