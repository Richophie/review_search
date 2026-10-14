#!/usr/bin/env python3
"""Inspect DOM-rendered campaign cards on robots-permitted official pages."""
import json,re,time
from collect import robots_permit,safe_fetch
from playwright.sync_api import sync_playwright
SITES=[("ohmyblog","https://www.ohmyblog.co.kr/"),("chvu","https://chvu.co.kr/campaign")]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1200,"height":920})
 for name,url in SITES:
  if not robots_permit(url):print("BLOCKED",name,url,flush=True);continue
  try:
   response=page.goto(url,wait_until="domcontentloaded",timeout=36000)
   page.wait_for_timeout(3300)
   data=page.evaluate("""() => ({
     page:location.href,title:document.title,text:document.body.innerText.slice(0,13500),
     links:[...document.querySelectorAll('a[href]')].map(a=>({
       url:a.href,title:a.innerText.trim().slice(0,520),
       html:a.outerHTML.slice(0,2700)
     })).filter(x=>/(?:campaign|review|search|product|trial|\\/view|\\.apsl|\\d{4,})/i.test(x.url)).slice(0,140),
     cards:[...document.querySelectorAll('article,[class*="Campaign"],[class*="campaign"],[class*="Card"],[class*="card"],li')]
       .filter(el=>el.getBoundingClientRect().width>165&&el.getBoundingClientRect().height>105
         &&/(?:모집|신청|마감|남음)/.test(el.innerText))
       .slice(0,9).map(el=>({html:el.outerHTML.slice(0,4000),text:el.innerText.slice(0,700)}))
   })""")
   print("PAGE",name,response.status if response else None,data["page"],"text",re.sub(r'\s+',' ',data["text"])[:3000],flush=True)
   print("LINKS",name,len(data["links"]),flush=True)
   for item in data["links"][:16]:print("LINK",name,json.dumps(item,ensure_ascii=False)[:3200],flush=True)
   for item in data["cards"][:5]:print("CARD",name,json.dumps(item,ensure_ascii=False)[:3800],flush=True)
   page.mouse.wheel(0,2500)
   page.wait_for_timeout(1600)
   nextlinks=page.evaluate("""() => [...document.querySelectorAll('a[href]')].map(a=>a.href).filter(h=>/(?:campaign|product|search|review|\\.apsl)/i.test(h)).slice(0,180)""")
   print("SCROLLED",name,len(nextlinks),json.dumps(nextlinks.slice(-28),ensure_ascii=False),flush=True)
  except Exception as ex:print("FAIL",name,type(ex).__name__,str(ex)[:400],flush=True)
 browser.close()
