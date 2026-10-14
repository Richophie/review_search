#!/usr/bin/env python3
"""Collect only public robots-permitted displayed campaign cards from two sites."""
import json,time
from collect import OUT,robots_permit
from parse_ohmy_chvu import parse_card
from playwright.sync_api import sync_playwright

SITES=[
    ("ohmyblog","https://www.ohmyblog.co.kr/"),
    ("ohmyblog","https://www.ohmyblog.co.kr/user/search?app_cate_detail=A"),
    ("ohmyblog","https://www.ohmyblog.co.kr/user/search?app_cate_detail=B"),
    ("ohmyblog","https://www.ohmyblog.co.kr/user/search?app_cate_detail=C"),
    ("ohmyblog","https://www.ohmyblog.co.kr/user/search?app_cate_detail=D"),
    ("ohmyblog","https://www.ohmyblog.co.kr/user/search?app_cate_detail=E"),
    ("ohmyblog","https://www.ohmyblog.co.kr/user/search?app_cate_detail=F"),
    ("chvu","https://chvu.co.kr/campaign"),
    ("chvu","https://chvu.co.kr/campaign?sort=latest"),
]
DOM=r"""(source) => {
 const elems=source==='ohmyblog'
   ? [...document.querySelectorAll('a[href*="productDetail.apsl?app_seq="]')]
   : [...document.querySelectorAll('a[href^="/campaign/"]')];
 return elems.map(a=>{
  if(source==='ohmyblog') {
    return {url:a.href,title:a.querySelector('.lnkTit01')?.innerText?.trim()||'',
      benefit:a.querySelector('.lnkTxt01')?.innerText?.trim()||'',
      status:a.querySelector('.lnkLimitDay')?.innerText?.trim()||'',
      slots:a.querySelector('.lnkTxt02')?.innerText?.trim()||'',
      type:a.querySelector('.lnkPdcCate')?.innerText?.trim()||'',
      media:[...a.querySelectorAll('.lnkSnsIco img[alt]')].map(n=>n.alt),
      image:a.querySelector('.lnkImgBox img')?.getAttribute('src')||''};
  }
  const count=[...a.querySelectorAll('[class*="Application"] > div')];
  return {url:a.href,title:a.querySelector('[class*="__Title-"]')?.innerText?.trim()||'',
    benefit:a.querySelector('[class*="__Details-"]')?.innerText?.trim()||'',
    status:count[1]?.innerText?.trim()||'', count:count[0]?.innerText?.trim()||'',
    type:a.querySelector('[class*="ItemHeader"]')?.innerText?.trim()||'',
    media:[...a.querySelectorAll('[class*="ChannelType__TypeDiv"]')].map(e=>e.innerText.trim()),
    image:a.querySelector('img')?.getAttribute('src')||''};
 }).filter(r=>r.url&&r.title);
}"""
def main():
    byid={r["id"]:r for r in json.loads(OUT.read_text(encoding="utf-8"))}
    counts={}
    distinct={}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1200,"height":900})
        try:
            for name,url in SITES:
                if not robots_permit(url):
                    print("Not permitted:",name,url,flush=True)
                    continue
                try:
                    response=page.goto(url,wait_until="domcontentloaded",timeout=38000)
                    if not response or response.status!=200:continue
                    page.wait_for_timeout(2400)
                    cards=page.evaluate(DOM,name)
                    for _ in range(3):
                        page.mouse.wheel(0,2600)
                        page.wait_for_timeout(850)
                        cards.extend(page.evaluate(DOM,name))
                except Exception as e:
                    print("Public page unavailable:",name,type(e).__name__,str(e)[:180],flush=True)
                    continue
                verified={}
                for card in cards:
                    row=parse_card(card,name)
                    if row:verified[row["id"]]=row
                for row in verified.values():
                    prev=byid.get(row["id"])
                    if prev:
                        row["first_seen_at"]=prev.get("first_seen_at",row["first_seen_at"])
                        if not row.get("image_url") and prev.get("image_url"):row["image_url"]=prev["image_url"]
                        if not row.get("published_at") and prev.get("published_at"):row["published_at"]=prev["published_at"]
                    byid[row["id"]]=row
                distinct.setdefault(name,set()).update(verified)
                counts[name]=len(distinct[name])
                print("Verified public:",name,"url",url,"displayed",len(cards),
                      "page unique",len(verified),"source unique",counts[name],flush=True)
                time.sleep(.7)
        finally:
            browser.close()
    if not all(counts.get(name,0)>=5 for name,_ in SITES):
        raise SystemExit("Not enough verified public cards for both sources. Preserving snapshot.")
    rows=sorted(byid.values(),key=lambda r:(r["source_id"],r["id"]))
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("PUBLIC_SOURCES_VERIFIED",counts,"records",len(rows),flush=True)

if __name__=="__main__":main()
