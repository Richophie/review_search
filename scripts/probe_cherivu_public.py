#!/usr/bin/env python3
"""Read-only, robots-respecting audit of Cherivu official campaign page."""
import re,html,time
from urllib.parse import urljoin
from collect import safe_fetch
url="https://cherivu.co.kr/"
try:
 page=safe_fetch(url)
 if not page:raise SystemExit("Cherivu public landing not permitted or unavailable")
 print("SITE_BYTES",len(page),flush=True)
 links=[html.unescape(x) for x in re.findall(r'href\s*=\s*["\x27]([^"\x27]+)',page,re.I)]
 relevant=list(dict.fromkeys(urljoin(url,a) for a in links if
   re.search(r"(?:campaign|review|/view|/detail|/product|idx=|id=|/event|/\d+)",a,re.I)
   and not a.startswith(("javascript:", "#"))))
 print("PUBLIC_LINKS",len(links),"interesting",len(relevant),relevant[:65],flush=True)
 for word in ("[서울/","신청","D-8","모집중","캠페인","__NEXT_DATA__"):
  n=page.find(word)
  if n>=0:
   print("MARK",word,re.sub(r'\s+',' ',page[max(0,n-800):n+2300])[:3000],flush=True)
except Exception as e:print("ERROR",type(e).__name__,str(e)[:250],flush=True)
