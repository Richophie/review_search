#!/usr/bin/env python3
"""Collect public, browser-rendered campaigns from Popomon and Revu.

Fetch only pages advertised on the public site and allowed by robots. No auth,
anti-bot bypass, API reverse engineering, or guesswork about application dates.
"""
import json,os,time,re
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from collect import OUT,robots_permit
from popomon_revu_cards import parse_card

TARGETS=[
    ("popomon", "https://popomon.com/"),
    ("revu", "https://webview.revu.net/"),
]
# Use only publicly rendered cards; no direct API access.
JS=r"""() => [...document.querySelectorAll('a[href]')].map(a => {
 const isPop=a.href.startsWith('https://popomon.com/next/campaign/');
 const isRev=/https:\/\/(?:webview|www)\.revu\.net\/campaign\/\d+$/.test(a.href);
 if (!isPop && !isRev) return null;
 const heading=a.querySelector(isPop?'h3':'.card-title');
 if (!heading || !heading.innerText?.trim()) return null;
 const image=a.querySelector(isPop?'img:not([alt="포인트 코인"])':'.thumb-img');
 const tags=isPop ? [...a.querySelectorAll('span')].slice(0,7)
                 : [...a.querySelectorAll('.thumb-media-icons img')];
 const targettext=a.innerText||'';
 const status=isPop ? a.querySelector('.line-2skip span')?.innerText || ''
                    : a.querySelector('.card-status')?.innerText || '';
 const desc=isPop ? (a.querySelector('.line-2skip')?.innerText || '').replace(status,'').trim()
                  : a.querySelector('.card-desc')?.innerText || '';
 return {
    url:a.href, title:heading.innerText.trim(),
    text:targettext.slice(0,1100),status:status.trim(),
    benefit:desc.slice(0,350),image:image?.getAttribute('src') || '',
    badges:isPop?tags.map(e=>e.innerText.trim()).filter(Boolean):[],
    mediaIcons:isRev?tags.map(e=>e.getAttribute('src')||'').filter(Boolean):[],
    type:isPop?targettext.split('\n').filter(x=>/^(?:방문형|배송형|기자단)$/.test(x.trim())).join(' '):''
 };
}).filter(Boolean)"""

def main():
    existing=json.loads(OUT.read_text(encoding="utf-8"))
    byid={r["id"]:r for r in existing}
    counts={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(locale="ko-KR",timezone_id="Asia/Seoul",
                              viewport={"width":1240,"height":930})
        for name,url in TARGETS:
            if not robots_permit(url):
                print("Public landing blocked by robots:",name,flush=True)
                continue
            cards=[]
            try:
                res=page.goto(url,wait_until="domcontentloaded",timeout=40000)
                if not res or res.status!=200:
                    print("No public home:",name,flush=True)
                    continue
                page.wait_for_timeout(2600)
                page.mouse.wheel(0,1450)
                page.wait_for_timeout(650)
                cards=page.evaluate(JS)
                print(name,"public rendered anchors",len(cards),flush=True)
            except Exception as exc:
                print("Public rendering unavailable:",name,type(exc).__name__,str(exc)[:140],flush=True)
                continue
            counted=0
            for card in cards:
                row=parse_card(card,name)
                if row is None: continue
                if not robots_permit(row["original_url"]):
                    # A public card can point to a login-only detail. Do not
                    # crawl that page; the campaign card itself was public.
                    # Original URL remains an ordinary user-facing link.
                    pass
                previous=byid.get(row["id"])
                if previous:
                    row["first_seen_at"]=previous.get("first_seen_at",row["first_seen_at"])
                    if not row.get("image_url") and previous.get("image_url"):
                        row["image_url"]=previous["image_url"]
                    if not row.get("published_at") and previous.get("published_at"):
                        row["published_at"]=previous["published_at"]
                byid[row["id"]]=row
                counted+=1
            counts[name]=counted
            print(name,"verified live public campaigns",counted,flush=True)
            time.sleep(.7)
        browser.close()
    if not all(counts.get(name,0)>=5 for name,_ in TARGETS):
        raise SystemExit("One source had fewer than 5 eligible public recruiting cards; not publishing partial source collection")
    rows=sorted(byid.values(),key=lambda r:(r["source_id"],r["id"]))
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("NEW_SOURCE_VERIFIED",counts,"snapshot",len(rows),flush=True)

if __name__=="__main__":
    main()
