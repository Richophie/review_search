#!/usr/bin/env python3
"""Read-only count unique public official category pages; no guessing routes."""
import re,json,time
from urllib.parse import urlsplit
from collect import robots_permit
from playwright.sync_api import sync_playwright
SITES=[
("ohmy-A","https://www.ohmyblog.co.kr/user/search?app_cate_detail=A","ohmyblog"),
("ohmy-B","https://www.ohmyblog.co.kr/user/search?app_cate_detail=B","ohmyblog"),
("ohmy-E","https://www.ohmyblog.co.kr/user/search?app_cate_detail=E","ohmyblog"),
("chvu-new","https://chvu.co.kr/campaign?sort=latest","chvu"),
("chvu-deadline","https://chvu.co.kr/campaign?sort=deadline","chvu"),
("cherivu-all","https://cherivu.co.kr/campaigns","cherivu"),
]
JS=r"""(source)=>({
   href:location.href,title:document.title,
   cards:[...document.querySelectorAll(source==='ohmyblog'?'a[href*="productDetail.apsl?app_seq="]':
       source==='chvu'?'a[href^="/campaign/"]':'a[href^="/campaigns/"]')]
       .map(a=>a.href).filter(h=>/\d+/.test(h)),
   controls:[...document.querySelectorAll('button,a,[role="button"]')]
     .filter(n=>/(?:다음|더보기|끝|전체|페이지|1|2|3)/.test((n.innerText||'').trim()) && (n.innerText||'').length<70)
     .slice(-20).map(n=>({text:n.innerText?.trim(),html:n.outerHTML.slice(0,270)}))
})"""
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 page=b.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1280,"height":900})
 for label,url,source in SITES:
  if not robots_permit(url):
   print("BLOCKED",label,url,flush=True);continue
  try:
   r=page.goto(url,wait_until="domcontentloaded",timeout=34000)
   page.wait_for_timeout(2300)
   initial=page.evaluate(JS,source)
   page.mouse.wheel(0,3600)
   page.wait_for_timeout(900)
   after=page.evaluate(JS,source)
   ids=set(initial["cards"])|set(after["cards"])
   print("LIST",label,"status",r.status if r else None,"actualURL",after["href"],
     "top",len(set(initial["cards"])),"scrolled",len(set(after["cards"])),
     "union",len(ids),"controls",json.dumps(after["controls"][-12:],ensure_ascii=False)[:1900],
     "examples",list(ids)[:5],flush=True)
  except Exception as e:print("ERROR",label,type(e).__name__,str(e)[:160],flush=True)
  time.sleep(.5)
 b.close()
