#!/usr/bin/env python3
"""Public browser-rendered campaign discovery; no auth, no internal API calls."""
import json,re,time
from collect import safe_fetch
from playwright.sync_api import sync_playwright
urls=[
 ("popomon","https://popomon.com/"),
 ("revu","https://webview.revu.net/"),
]
def strip(t):return re.sub(r"\s+"," ",t or "")[:3000]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1260,"height":950})
 for name,url in urls:
  if not safe_fetch(url):
   print("SKIP",name,"robots or request unavailable",flush=True);continue
  try:
   response=page.goto(url,wait_until="domcontentloaded",timeout=40000)
   page.wait_for_timeout(3000)
   rendered=page.evaluate("""() => ({
      url: location.href, title: document.title,
      text: document.body.innerText.slice(0,18000),
      anchors: [...document.querySelectorAll('a[href]')].map(a=>({href:a.href,txt:(a.innerText||'').trim().slice(0,115)})).filter(x=>/^https?:/.test(x.href)).slice(0,180),
      snippets: [...document.querySelectorAll('[class*="campaign"],[class*="card"],[class*="Campaign"],[class*="Card"]')].filter(n=>n.getBoundingClientRect().width>110 && n.getBoundingClientRect().height>100).slice(0,14).map(n=>({tag:n.tagName,class:n.className?.toString().slice(0,110),html:n.outerHTML.slice(0,2600),text:n.innerText?.slice(0,450)}))
   })""")
   print("BROWSER_SITE",name,"status",response.status if response else None,
         "url",rendered["url"],"title",rendered["title"],flush=True)
   print("BROWSER_TEXT",name,strip(rendered["text"][:7000]),flush=True)
   relevant=[a for a in rendered["anchors"] if re.search(r"campaign|experience|review|product|detail|apply|service|item|ppl|\\d{4,}",a["href"],re.I)]
   print("BROWSER_LINKS",name,len(rendered["anchors"]),"campaign",len(relevant),json.dumps(relevant[:75],ensure_ascii=False),flush=True)
   for card in rendered["snippets"][:6]:
    print("BROWSER_CARD",name,json.dumps(card,ensure_ascii=False)[:2300],flush=True)
   page.mouse.wheel(0,1750)
   page.wait_for_timeout(2200)
   after=page.evaluate("""() => ({
     text: document.body.innerText.slice(0,8500),
     links: [...document.querySelectorAll('a[href]')].map(a=>a.href).filter(s=>/campaign|detail|experience|item|review/.test(s)).slice(0,40)
   })""")
   print("SCROLLED_TEXT",name,strip(after["text"]),flush=True)
   print("SCROLLED_LINKS",name,json.dumps(after["links"],ensure_ascii=False),flush=True)
  except Exception as ex:print("BROWSER_FAIL",name,type(ex).__name__,str(ex)[:300],flush=True)
 browser.close()
