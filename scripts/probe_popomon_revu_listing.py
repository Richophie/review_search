#!/usr/bin/env python3
"""Read-only investigate public listing navigation, without guessing routes."""
import json,re
from collect import robots_permit
from playwright.sync_api import sync_playwright
TARGETS=[
("popomon_latest","https://popomon.com/next/campaign?&recruitType=visiting&searchAlign=latest&cityLocation=&countyLocation="),
("popomon_popular","https://popomon.com/next/campaign?cityLocation=ALL&recruitType=visiting&searchAlign=volunteerU"),
("revu_region","https://www.revu.net/category/%EC%A7%80%EC%97%AD"),
]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 page=b.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1200,"height":900})
 for label,url in TARGETS:
  if not robots_permit(url):
   print("NOT_PERMITTED",label,url,flush=True)
   continue
  try:
   response=page.goto(url,wait_until="domcontentloaded",timeout=35000)
   page.wait_for_timeout(2000)
   def inspect(pos):
    data=page.evaluate("""() => ({
      title:document.title,url:location.href,
      links:[...document.querySelectorAll('a[href]')].map(a=>a.href).filter(h=>/\\/campaign\\/\\d+/.test(h)).slice(0,1000),
      controls:[...document.querySelectorAll('button,[role="button"],a')].filter(n=>/(?:더보기|다음|전체|지역|식품|뷰티|페이지)/.test(n.textContent||'')).slice(0,60).map(n=>({text:n.textContent.trim().slice(0,100),html:n.outerHTML.slice(0,300)})),
      text:document.body.innerText.slice(-4500)
    })""")
    ids=set(re.findall(r'/campaign/(\d+)'," ".join(data["links"])))
    print("LIST",label,pos,"status",response.status if response else None,"url",data["url"],"links",len(data["links"]),"uniqueIDs",len(ids),"controls",json.dumps(data["controls"][:25],ensure_ascii=False)[:3100],flush=True)
    print("LIST_TEXT",label,pos,re.sub(r"\s+"," ",data["text"])[-1350:],flush=True)
    return ids
   first=inspect("top")
   page.mouse.wheel(0,4500)
   page.wait_for_timeout(1700)
   second=inspect("scrolled")
   print("LINK_INCREASE",label,len(second-first),flush=True)
  except Exception as e: print("LIST_ERROR",label,type(e).__name__,str(e)[:250],flush=True)
 b.close()
