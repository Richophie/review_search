#!/usr/bin/env python3
"""Public browser-rendered Cherivu campaign cards, no auth or API probing."""
import json,time
from collect import OUT,robots_permit
from parse_cherivu import parse_card
from playwright.sync_api import sync_playwright

HOME="https://cherivu.co.kr/"
JS=r"""() => [...document.querySelectorAll('a.campaign_common_item[href]')].map(a=>({
    url:a.href,
    title:a.querySelector('h4.title')?.innerText?.trim()||'',
    benefit:a.querySelector('.sub_title')?.innerText?.trim()||'',
    status:a.querySelector('.d-day')?.innerText?.trim()||'',
    image:a.querySelector('.campaign-thumb')?.getAttribute('data-src')||'',
    icons:[...a.querySelectorAll('.sns_wrap img.sns')].map(n=>n.getAttribute('src')||'')
})).filter(x=>x.url&&x.title)"""
def main():
    if not robots_permit(HOME):
        raise SystemExit("Cherivu robots restrictions prevent public collection")
    previous=json.loads(OUT.read_text(encoding="utf-8"))
    existing={r["id"]:r for r in previous}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1280,"height":940})
        try:
            resp=page.goto(HOME,wait_until="domcontentloaded",timeout=38000)
            if not resp or resp.status!=200:
                raise SystemExit("Cherivu home did not respond as public")
            page.wait_for_function("document.querySelectorAll('a.campaign_common_item').length>4",timeout=18000)
            page.wait_for_timeout(300)
            cards=page.evaluate(JS)
            page.mouse.wheel(0,2300)
            page.wait_for_timeout(850)
            cards.extend(page.evaluate(JS))
        finally:
            browser.close()
    observations={}
    for card in cards:
        row=parse_card(card)
        if row:observations[row["id"]]=row
    if len(observations)<5:
        raise SystemExit("Fewer than 5 confirmed Cherivu recruiting cards, refusing publish")
    for row in observations.values():
        prev=existing.get(row["id"])
        if prev:
            row["first_seen_at"]=prev.get("first_seen_at",row["first_seen_at"])
            if not row.get("image_url") and prev.get("image_url"):
                row["image_url"]=prev["image_url"]
        existing[row["id"]]=row
    rows=sorted(existing.values(),key=lambda r:(r["source_id"],r["id"]))
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("CHERIVU_VERIFIED public cards",len(cards),"unique",len(observations),"snapshot",len(rows),flush=True)

if __name__=="__main__":main()
