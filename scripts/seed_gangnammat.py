#!/usr/bin/env python3
"""Targeted, publicly permitted Gangnam Matzip snapshot enrichment."""
import json
import re
import time
import html
import urllib.parse
from datetime import datetime, timezone
from campaign_lifecycle import reconcile
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
    # Traverse page links actually advertised by each public listing.
    # Do not invent page numbers or use private/internal endpoints.
    queue = list(paths)
    visited = set()
    page_links = []
    while queue and len(visited) < 160:
        parent = queue.pop(0)
        if parent in visited:
            continue
        visited.add(parent)
        try:
            body = safe_fetch(parent)
            if not body:
                continue
            for href in re.findall(r'href\s*=\s*["\x27]([^"\x27]+)', body, re.I):
                url = urllib.parse.urljoin(parent, html.unescape(href))
                parts = urllib.parse.urlsplit(url)
                if parts.scheme != "https" or parts.hostname != "gangnam-review.net" or parts.path != "/cp/":
                    continue
                params = urllib.parse.parse_qs(parts.query)
                if "page" not in params or any(k not in {"page", "ca", "ch"} for k in params):
                    continue
                if len(params["page"]) != 1 or not re.fullmatch(r"\d{1,3}", params["page"][0]):
                    continue
                if not 1 <= int(params["page"][0]) <= 100:
                    continue
                canonical = "https://gangnam-review.net/cp/?" + urllib.parse.urlencode(
                    [(k, params[k][0]) for k in ("ca", "ch", "page") if k in params]
                )
                if canonical not in visited and canonical not in queue:
                    queue.append(canonical)
                    page_links.append(canonical)
        except Exception as exc:
            print("Gangnam public pagination skipped", parent, repr(exc)[:110], flush=True)
        time.sleep(0.2)
    paths = list(dict.fromkeys([*paths, *page_links]))
    print("Gangnam advertised paginated lists", len(page_links), flush=True)
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
    # A bounded scan is not proof of exhaustive coverage.
    # Track starts and updates without marking missing records closed.
    previous_source = [r for r in stored if r.get("source_id") == "gangnammat"]
    _, events = reconcile(
        previous_source, items,
        source_id="gangnammat", complete=False,
        observed_at=datetime.now(timezone.utc).isoformat(),
    )
    print("Gangnam partial scan lifecycle events:", {
        name: sum(event["event"] == name for event in events)
        for name in ("started", "updated", "reappeared")
    }, flush=True)
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
