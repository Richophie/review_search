#!/usr/bin/env python3
"""Inspect public browser-rendered Cherivu cards only."""
import json,re
from collect import safe_fetch
from playwright.sync_api import sync_playwright
url="https://cherivu.co.kr/"
if not safe_fetch(url):raise SystemExit("No publicly permitted page")
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 page=b.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1260,"height":900})
 try:
  response=page.goto(url,wait_until="domcontentloaded",timeout=40000)
  page.wait_for_timeout(2700)
  data=page.evaluate("""() => ({
    page:location.href, text:document.body.innerText.slice(0,9000),
    links:[...document.querySelectorAll('a[href]')].map(a=>({
      url:a.href, text:a.innerText?.trim().slice(0,450)||'',
      html:a.outerHTML.slice(0,4100)
    })).filter(x=>x.text.length>15||/campaign|product|detail|event|view/.test(x.url)).slice(0,90)
  })""")
  print("RENDER",response.status if response else None,data["page"],"TEXT",re.sub(r'\s+',' ',data["text"])[:2000],flush=True)
  print("LINK_COUNT",len(data["links"]),flush=True)
  for x in data["links"][:26]:print("CARD_LINK",json.dumps(x,ensure_ascii=False)[:3200],flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e)[:250],flush=True)
 b.close()
