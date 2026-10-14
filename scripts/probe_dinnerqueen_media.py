#!/usr/bin/env python3
"""Read-only official Dinnerqueen media evidence audit, no inferred defaults."""
import json,re,time
from pathlib import Path
from collect import safe_fetch,plain,one

rows=json.loads(Path("public/data/campaigns.json").read_text(encoding="utf-8"))
unknown={r["id"].split(":")[-1]:r for r in rows if r.get("source_id")=="dinnerqueen" and not r.get("channels")}
print("KNOWN_UNKNOWN_MEDIA",len(unknown),flush=True)
for page in (1,2,10,30,60,120,200,260):
    url="https://dinnerqueen.net/taste"+("?page="+str(page) if page>1 else "")
    try:
        content=safe_fetch(url)
        if not content:
            print("PAGE_UNAVAILABLE",page,flush=True)
            continue
        cards=content.split('class="qz-dq-card campaign')[1:]
        known=0
        potential=0
        icon_counts={}
        for card in cards:
            cid=one(r'href="/taste/(\d+)"',card)
            title=plain(one(r'title="([^"]+?)\s*신청하기"',card))
            icons=list(dict.fromkeys(re.findall(r"qz_b_([a-z0-9_]+)",card,re.I)))
            for i in icons:icon_counts[i]=icon_counts.get(i,0)+1
            if not cid or cid not in unknown:continue
            known+=1
            if any(v in icons for v in ("reels","clip","shorts","youtube","blog")):potential+=1
            snippet=one(r'<div class="qz-dq-card__badge-row[^"]*"[^>]*>([\s\S]*?)</div>\s*</a>',card)
            print("UNKNOWN_CARD",cid,"TITLE",repr(title[:140]),"ICONS",icons,
                  "BADGE_TEXT",plain(snippet)[:240],"MARKERS",re.findall(r"\[[^\]]{1,14}\]",title)[:6],flush=True)
        print("PAGE",page,"cards",len(cards),"unknown_current",known,
              "unknown_with_explicit_icon",potential,"all_icons",icon_counts,flush=True)
    except Exception as e:
        print("ERROR",page,type(e).__name__,str(e)[:170],flush=True)
    time.sleep(0.65)
detail_samples=[(cid,r["original_url"],r["title"]) for cid,r in list(unknown.items())[:2]]
detail_samples.append(("1597713","https://dinnerqueen.net/taste/1597713","official reels reference"))
for cid,url,title in detail_samples:
    try:
        body=safe_fetch(url)
        if not body:continue
        print("DETAIL",cid,"bytes",len(body),"actual_title",title[:60],flush=True)
        content_text=plain(body)
        for phrase in ("리뷰어 미션","매체","블로그","인스타그램 릴스","네이버 클립","리뷰 작성"):
            found=re.search(re.escape(phrase),content_text,re.I)
            if found:
                print("DETAIL_CONTEXT",cid,phrase,
                      repr(content_text[max(0,found.start()-100):found.start()+460]),flush=True)

        for word in ("리뷰어 미션","블로그 포스팅","인스타그램 릴스","네이버 클립","유튜브 쇼츠","체험단 미션","리뷰 작성"):
            occ=[m.start() for m in list(re.finditer(re.escape(word),plain(body)))[:3]]
            print("DETAIL_MARKER",cid,word,"positions",occ,flush=True)
        for pattern in (r'qz_b_[a-z_]+',r'블로그.{0,60}포스팅',r'인스타그램.{0,60}릴스'):
            print("DETAIL_PATS",cid,pattern,re.findall(pattern,body,re.I)[:9],flush=True)
    except Exception as e:print("DETAIL_ERROR",cid,type(e).__name__,str(e)[:100],flush=True)
    time.sleep(0.5)
