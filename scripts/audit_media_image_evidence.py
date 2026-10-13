#!/usr/bin/env python3
"""Read-only media and thumbnail evidence audit. Never invent missing fields."""
import collections,html,json,re
from urllib.parse import urljoin
from pathlib import Path
from collect import safe_fetch,plain

rows=json.loads(Path("public/data/campaigns.json").read_text())
for source in ("dinnerqueen","assaview","bqueens","modan","tqueens","reviewnote"):
    pool=[r for r in rows if r["source_id"]==source]
    unknown=[r for r in pool if not r.get("channels")]
    missing=[r for r in pool if not r.get("image_url")]
    print("SOURCE_STATS",source,"total",len(pool),"media_unknown",len(unknown),"image_missing",len(missing),flush=True)
    for r in unknown[:7]:
        print("UNKNOWN_SAMPLE",source,r["id"],repr(r["title"][:110]),
              "DESC",repr(str(r.get("description") or "")[:100]),flush=True)
    for r in missing[:8]:
        print("IMAGE_SAMPLE",source,r["id"],repr(r["title"][:100]),r["original_url"],flush=True)

targets=[
    ("assaview","https://www.assaview.co.kr/campaign_list.php"),
    ("dinnerqueen","https://dinnerqueen.net/taste"),
    ("bqueens","https://bqueens.net/taste"),
    ("tqueens","https://tqueens.net/taste"),
]
for source,url in targets:
    try:
        body=safe_fetch(url)
        if not body: print("UNAVAILABLE",source,url,flush=True);continue
        if source=="assaview":
            cards=[v for _,v in re.findall(
                r'<a\s+href="campaign\.php\?cp_id=(\d+)"[^>]*>([\s\S]*?)</a>',
                body,re.I)]
        elif source=="dinnerqueen":
            cards=body.split('class="qz-dq-card campaign')[1:]
        elif source=="bqueens":
            cards=body.split('<div class="item">')[1:]
        else:
            cards=body.split('class="qz-dq-card qz-button fluid hover"')[1:]
        print("LIST_CARD_COUNT",source,len(cards),flush=True)
        for c in cards[:3]:
            print("LIST_CARD_HTML",source,re.sub(r'\s+',' ',c[:5500])[:5000],flush=True)
    except Exception as e:print("LIST_ERROR",source,type(e).__name__,str(e)[:200],flush=True)

# Sample only a few missing Reviewnote images, no blind ID probing.
missing=[r for r in rows if r["source_id"]=="reviewnote" and not r.get("image_url")]
for r in missing[:6]:
    url=r["original_url"]
    try:
        body=safe_fetch(url)
        if not body:print("REVIEWNOTE_DETAIL_UNAVAILABLE",r["id"],flush=True);continue
        image_meta=re.findall(r'<meta\s+[^>]*?(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*>',body,re.I)
        candidates=re.findall(r'(?:src|data-src|srcset)=["\']([^"\']+)',body,re.I)
        snippets=[u[:220] for u in candidates if re.search(r"https?://|/_next/image|/uploads?/|/images?/",u,re.I)]
        print("REVIEWNOTE_DETAIL",r["id"],"bytes",len(body),"meta",image_meta[:3],
              "image_candidates",snippets[:10],flush=True)
    except Exception as e:print("REVIEWNOTE_DETAIL_ERROR",r["id"],type(e).__name__,str(e)[:130],flush=True)
