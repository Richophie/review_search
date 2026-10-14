#!/usr/bin/env python3
"""Targeted, publicly permitted Gangnam Matzip snapshot enrichment."""
import json
import re
import time
import html
import urllib.parse
from collect import OUT, gangnammat, safe_fetch

def main():
    paths = [
        "https://gangnam-review.net/cp/",
        "https://gangnam-review.net/cp/?ca=20",
        "https://gangnam-review.net/cp/?ca=30",
        "https://gangnam-review.net/cp/?ca=40",
        "https://gangnam-review.net/cp/?ch=clip",
    ]
    # Discover only category URLs that are directly linked from the
    # provider's official public listing navigation. No generated IDs,
    # guessing, or access to unadvertised endpoints.
    discovered = []
    for parent in paths:
        try:
            body = safe_fetch(parent)
            if not body:
                continue
            for href in re.findall(r'href\s*=\s*["\x27]([^"\x27]+)',body,re.I):
                href = html.unescape(href).replace("http://gangnam-review.net/", "https://gangnam-review.net/")
                url=urllib.parse.urljoin(parent,href)
                parts=urllib.parse.urlsplit(url)
                if parts.scheme!="https" or parts.hostname!="gangnam-review.net" or parts.path!="/cp/":
                    continue
                ca=urllib.parse.parse_qs(parts.query).get("ca",[])
                if len(ca)!=1 or not re.fullmatch(r"\d{2,5}",ca[0]):
                    continue
                canonical="https://gangnam-review.net/cp/?ca="+ca[0]
                if canonical not in paths and canonical not in discovered:
                    discovered.append(canonical)
        except Exception as exc:
            print("Gangnam public nav discovery skipped",parent,repr(exc)[:125],flush=True)
    paths.extend(discovered[:60])
    print("Gangnam official nav discovered",len(discovered),"following",len(paths),"public pages",flush=True)
    verified = {}
    for url in paths:
        try:
            batch = gangnammat(url)
            for item in batch:
                verified[item["id"]] = item
        except Exception as exc:
            print("Gangnam category not verified:", url, repr(exc)[:160], flush=True)
        time.sleep(0.45)
    items = list(verified.values())
    print("Gangnam listing categories verified:", len(paths), "unique records:", len(items), flush=True)
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
