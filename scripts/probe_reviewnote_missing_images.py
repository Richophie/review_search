#!/usr/bin/env python3
"""Read-only audit of public Reviewnote detail images after browser rendering.

Scrutinize only already verified campaign URLs missing thumbnails. Never
access protected APIs, infer image addresses, or copy unrelated site logos.
"""
import json
from pathlib import Path
from collect import safe_fetch

rows=json.loads(Path("public/data/campaigns.json").read_text(encoding="utf-8"))
missing=[r for r in rows if r.get("source_id")=="reviewnote" and not r.get("image_url")]
print("Reviewnote image missing",len(missing),flush=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(locale="ko-KR",timezone_id="Asia/Seoul",viewport={"width":1150,"height":800})
    try:
        for r in missing[:5]:
            url=r["original_url"]
            if not safe_fetch(url):
                print("SKIP robots",r["id"],flush=True)
                continue
            try:
                page.goto(url,wait_until="domcontentloaded",timeout=30000)
                page.wait_for_timeout(1800)
                data=page.evaluate("""() => ({
                  heading: document.querySelector('h1')?.innerText?.slice(0,150) || '',
                  title: document.title,
                  images: [...document.querySelectorAll('img')].map(img => ({
                    src: img.currentSrc||img.getAttribute('src')||'',
                    alt: img.alt,
                    naturalW: img.naturalWidth,
                    naturalH: img.naturalHeight,
                    width: img.getBoundingClientRect().width,
                    height: img.getBoundingClientRect().height,
                    context: img.parentElement?.parentElement?.innerText?.slice(0,110)||''
                  })).filter(x => x.src.startsWith('http')).slice(0,36)
                })""")
                print("RENDERED",r["id"],"title",r["title"][:100],"page",str(data["title"])[:100],
                      "heading",str(data["heading"])[:100],"images",data["images"][:15],flush=True)
            except Exception as e: print("BROWSER_ERROR",r["id"],type(e).__name__,str(e)[:160],flush=True)
    finally:
        browser.close()
