#!/usr/bin/env python3
"""Inspect newly considered official public sites, fail closed on robots."""
import re, html, time
from urllib.parse import urljoin, urlsplit
from collect import safe_fetch
targets={
 "ohmyblog":["https://www.ohmyblog.co.kr/","https://ohmyblog.co.kr/"],
 "cheble":["https://www.cheble.net/"],
 "chvu":["https://chvu.co.kr/","https://chvu.co.kr/campaign"],
 "dailyview":["https://dailyview.kr/"],
 "yogitg":["https://yogitg.co.kr/"],
}
for name,urls in targets.items():
 for url in urls:
  try:
   raw=safe_fetch(url)
   if not raw:
    print("NO_PUBLIC",name,url,flush=True)
    continue
   links=[html.unescape(x) for x in re.findall(r'href\s*=\s*["\x27]([^"\x27]+)',raw,re.I)]
   relevant=list(dict.fromkeys(urljoin(url,x) for x in links if
      re.search(r'(?:camp|review|detail|view|item|^/\d+|idx=|id=|product|page=)',x,re.I)
      and not x.startswith(("javascript:","#","mailto:"))))
   scripts=re.findall(r'<script\b[^>]*src=["\x27]([^"\x27]+)',raw,re.I)
   print("PAGE",name,url,"bytes",len(raw),"links",len(links),
         "relevant",relevant[:45],"scripts",scripts[-12:],
         "title",re.findall(r'<title[^>]*>([^<]+)',raw,re.I)[:1],flush=True)
   for kw in ("상시모집","오늘 마감","일 남음","모집중","모집마감","체험단","캠페인","__NEXT_DATA__"):
    p=raw.find(kw)
    if p>=0:
     sub=raw[max(0,p-450):p+1100]
     print("MARK",name,kw,re.sub(r'\s+',' ',sub)[:1400],flush=True)
   if name=="cheble":
    for pat in (r'/campaign/(\d+)',r'/(?:campaign|trial|review|item)/(\d+)',r'(\d+)\s*명',r'상시모집'):
     print("COUNTS",pat,len(re.findall(pat,raw)),flush=True)
  except Exception as e:
   print("ERROR",name,url,type(e).__name__,str(e)[:200],flush=True)
  time.sleep(.5)
