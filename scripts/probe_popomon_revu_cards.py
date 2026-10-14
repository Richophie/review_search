#!/usr/bin/env python3
"""Read-only verify public campaign anchors, card semantics and detail paths."""
import json,re
from collect import safe_fetch
from playwright.sync_api import sync_playwright
hosts=[("popomon","https://popomon.com/","a[href^='/next/campaign/']", "https://popomon.com/next/campaign/327925"),
       ("revu","https://webview.revu.net/","a[href*='/campaign/']", "https://webview.revu.net/campaign/1417051")]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 page=b.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1200,"height":900})
 for name,url,selector,detail in hosts:
  if not safe_fetch(url): print("BLOCKED",name,flush=True);continue
  try:
   page.goto(url,wait_until="domcontentloaded",timeout=33000)
   page.wait_for_timeout(2200)
   rows=page.locator(selector).evaluate_all("""els => els.map(a=>({
      href:a.href,text:a.innerText?.slice(0,850),
      img:a.querySelector('img')?.getAttribute('src') || '',
      srcset:a.querySelector('img')?.getAttribute('srcset') || '',
      sample:a.outerHTML.slice(0,4300)
    })).filter(r=>/\/(?:next\/)?campaign\/\d+$/.test(new URL(r.href).pathname)).slice(0,12)""")
   print("CARD_COUNT",name,len(rows),flush=True)
   for item in rows[:4]: print("CARD",name,json.dumps(item,ensure_ascii=False)[:4600],flush=True)
   if not safe_fetch(detail): print("DETAIL_BLOCKED",name,flush=True);continue
   page.goto(detail,wait_until="domcontentloaded",timeout=33000)
   page.wait_for_timeout(1700)
   text=page.locator("body").inner_text()[:13000]
   print("DETAIL",name,detail,re.sub(r"\s+"," ",text)[:6500],flush=True)
  except Exception as ex:print("PROBE_ERROR",name,type(ex).__name__,str(ex)[:450],flush=True)
 b.close()
