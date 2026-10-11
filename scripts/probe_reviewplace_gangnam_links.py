#!/usr/bin/env python3
"""Read-only permitted navigation census on Gangnam Matzip and ReviewPlace."""
import re,html,time
from urllib.parse import urljoin,urlsplit,parse_qs
from collect import safe_fetch,plain
SOURCES={
 "gangnammat":("https://gangnam-review.net/",["/","/cp/","/cp/?ca=20"]),
 "reviewplace":("https://www.reviewplace.co.kr/",["/","/pr/","/pr/?ct1=제품","/pr/?ct1=지역"]),
}
def main():
 for name,(base,paths) in SOURCES.items():
  print("SOURCE",name,flush=True)
  for p in paths:
   u=urljoin(base,p)
   try:
    h=safe_fetch(u)
    if not h:print("UNAVAILABLE",u,flush=True);continue
    anchors=[html.unescape(v) for v in re.findall(r'href\s*=\s*["\x27]([^"\x27]+)',h,re.I)]
    links=list(dict.fromkeys(urljoin(u,v) for v in anchors))
    pubnav=[v for v in links if ("/cp/" in v if name=="gangnammat" else "/pr/" in v) and urlsplit(v).hostname==urlsplit(base).hostname]
    detailids=set(re.findall(r'data-product=["\x27](\d+)',h)) if name=="gangnammat" else set(re.findall(r'/pr/\?id=(\d+)',h))
    params={}
    for link in pubnav:
     for k,v in parse_qs(urlsplit(link).query).items():
      if k not in ("id",):
       params.setdefault(k,set()).update(v)
    print("PAGE",u,"bytes",len(h),"public links",len(pubnav),
          "cards",len(detailids),"paramValues",{k:sorted(v)[:40] for k,v in params.items()},
          "nav examples",pubnav[:37],flush=True)
    for marker in ("pagination","page=","pg=","load-more","next","ajax","더보기","ct1=","ca="):
     n=h.find(marker)
     if n>=0:print("MARK",marker,re.sub(r'\s+',' ',h[max(0,n-220):n+320])[:545],flush=True)
    if name=="reviewplace":
     for m in re.finditer(r'/(?:pr|product|review)\b[^"\x27 >]{0,65}',h,re.I):
      if 'id=' in m.group(0):
       print("REVIEWPLACE_NEAR",re.sub(r'\s+',' ',h[max(0,m.start()-170):m.start()+260])[:450],flush=True)
       break
   except Exception as e:print("ERROR",u,type(e).__name__,str(e)[:160],flush=True)
   time.sleep(0.5)
if __name__=="__main__":main()
