#!/usr/bin/env python3
"""Browser-visible public listing coverage probe for Reviewnote.

Uses a normal Chromium browser to scroll public pages and count distinct
campaign links. Never logs in, calls private APIs, or bypasses access controls.
This is a read-only diagnostic; it does not publish unverified campaigns.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "https://www.reviewnote.co.kr/campaigns"
PAGES = [
    BASE,
    BASE + "?channel=BLOG",
    BASE + "?channel=INSTAGRAM",
    BASE + "?channel=ETC",
]
OUT = Path("public/data/reviewnote_browser_probe.json")

def probe(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2200)
    found = set()
    rounds_without_growth = 0
    steps = 0
    while steps < 65:
        # Only links that a normal, unauthenticated visitor can see.
        hrefs = page.locator('a[href*="/campaigns/"]').evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('href') || '')"
        )
        before = len(found)
        for href in hrefs:
            m = re.search(r"/campaigns/(\d+)(?:[/?#]|$)", href)
            if m:
                found.add(m.group(1))
        if len(found) == before:
            rounds_without_growth += 1
        else:
            rounds_without_growth = 0
        if rounds_without_growth >= 6:
            break
        page.evaluate("""() => {
          window.scrollTo(0, document.documentElement.scrollHeight);
          for (const el of document.querySelectorAll('main, section, div, ul')) {
            const s = getComputedStyle(el);
            if (el.scrollHeight > el.clientHeight + 250 && /(auto|scroll)/.test(s.overflowY))
              el.scrollTop = el.scrollHeight;
          }
        }""")
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(900)
        steps += 1
    return {"page":url, "end_url":page.url, "document_height":page.evaluate("document.documentElement.scrollHeight"), "distinct_visible_campaign_ids":len(found),
            "scroll_rounds":steps, "campaign_ids":sorted(found)}

def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="ko-KR", timezone_id="Asia/Seoul")
        try:
            for url in PAGES:
                try:
                    results.append(probe(page,url))
                    print(url,results[-1]["distinct_visible_campaign_ids"],flush=True)
                except Exception as exc:
                    results.append({"page":url,"error":str(exc)[:200]})
        finally:
            browser.close()
    unique = set()
    for result in results:
        unique.update(result.get("campaign_ids",[]))
    report = {
        "checked_at_kst":datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "observed_distinct_public_campaign_ids":len(unique),
        "not_a_platform_total":True,
        "pages":results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Distinct campaign IDs visible across checked pages:",len(unique))

if __name__=="__main__":
    main()
