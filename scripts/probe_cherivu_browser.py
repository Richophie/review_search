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
  try:
   page.wait_for_function("document.body.innerText.includes('D-')",timeout=14000)
   page.wait_for_timeout(350)
  except Exception:
   print("CAMPAIGNS_NOT_RENDERED",flush=True)
  inspect=page.evaluate("""() => {
    const leaf=[...document.querySelectorAll('*')].find(e=>e.children.length===0 &&
      /(신라호텔|기프트인포|D-7)/.test(e.textContent||''));
    if(!leaf)return {found:false,body:document.body.innerText.slice(0,260)};
    const output=[];let n=leaf;
    for(let i=0;n&&i<6;i++,n=n.parentElement){
      output.push({tag:n.tagName,class:n.className?.toString().slice(0,150),
       id:n.id,href:n.getAttribute('href'),role:n.getAttribute('role'),
       cursor:getComputedStyle(n).cursor,
       outer:n.outerHTML.slice(0,7000)});
    }
    return {found:true,parents:output};
  }""")
  print("CARD_ANCESTORS",json.dumps(inspect,ensure_ascii=False)[:15000],flush=True)
  data=page.evaluate("""() => ({
    page:location.href, text:document.body.innerText.slice(0,9000),
    links:[...document.querySelectorAll('a[href]')].map(a=>({
      url:a.href, text:a.innerText?.trim().slice(0,450)||'',
      html:a.outerHTML.slice(0,4100)
    })).filter(x=>x.text.length>15||/campaign|product|detail|event|view/.test(x.url)).slice(0,90)
  })""")
  print("RENDER",response.status if response else None,data["page"],"TEXT",re.sub(r'\s+',' ',data["text"])[:2000],flush=True)
  print("LINK_COUNT",len(data["links"]),flush=True)
  cards=page.evaluate("""() => {
    const nodes=[...document.querySelectorAll('a[href], [role="link"], article, [class*="campaign"], [class*="Campaign"], [class*="card"], [class*="Card"]')];
    return nodes.filter(n=>/D-\\d+|마감임박/.test(n.innerText||'') &&
        n.getBoundingClientRect().width>135 && n.getBoundingClientRect().width<560 &&
        n.getBoundingClientRect().height>100)
      .slice(0,10).map(n=>({tag:n.tagName,class:n.className?.toString().slice(0,100),
         href:n.getAttribute('href'),outer:n.outerHTML.slice(0,4200),
         text:n.innerText.slice(0,390)}))
  }""")
  for item in cards:print("CARDDOM",json.dumps(item,ensure_ascii=False)[:4300],flush=True)
  for item in data["links"]:
    if re.search(r"/(?:campaign|review|detail|trial|product)/\\d+|/[0-9]{4,}$",item["url"]):
      print("DETAIL_LINK",json.dumps(item,ensure_ascii=False)[:2200],flush=True)

  for x in data["links"][:26]:print("CARD_LINK",json.dumps(x,ensure_ascii=False)[:3200],flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e)[:250],flush=True)
 b.close()
