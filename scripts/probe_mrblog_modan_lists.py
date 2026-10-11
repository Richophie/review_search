#!/usr/bin/env python3
"""Targeted read-only inspection of MiBL and Modan public HTML details."""
import re,html,time,urllib.parse
from collect import safe_fetch,plain
urls=[
 "https://www.mrblog.net/campaigns/region",
 "https://www.mrblog.net/campaigns/delivery",
 "https://www.mrblog.net/campaigns?is_instagram=1",
 "https://www.mrblog.net/campaigns?category=%EB%A7%9B%EC%A7%91",
 "https://www.mrblog.net/campaigns/search?query=%EB%B6%80%EC%82%B0",
 "https://modan.kr/campaigns?page=1",
 "https://modan.kr/campaigns?page=2",
 "https://modan.kr/campaigns?page=3",
 "https://modan.kr/campaigns?status=soon",
 "https://modan.kr/campaigns?sort=newest",
]
def main():
 for url in urls:
  try:
   body=safe_fetch(url)
   if not body:print("BLOCKED",url,flush=True);continue
   is_mr="mrblog.net" in url
   expr=(r'(?:https://www\.mrblog\.net)?/campaigns/(\d+)' if is_mr else r'(?:https://modan\.kr)?/campaigns/(\d+)')
   ids=list(dict.fromkeys(re.findall(expr,body)))
   print("LIST",url,"bytes",len(body),"ids",len(ids),"examples",ids[:10],
         "exact tags",body.count('class="campaign_item"'),
         "data labels",body.count("application/ld+json"),flush=True)
   for id in ids[:2]:
    for pattern in (f"/campaigns/{id}",f"campaigns/{id}"):
     pos=body.find(pattern)
     if pos>=0:
      chunk=body[max(0,pos-250):pos+1900]
      print("ITEM",id,re.sub(r'\s+',' ',chunk)[:2150],flush=True)
      break
   if not is_mr:
    for text in ("class=\"pages\"","status=all&amp;page=","page=10","page=5","마감","신청기간","모집 기간"):
     pos=body.find(text)
     if pos>=0:print("CONTROL",text,re.sub(r'\s+',' ',body[max(0,pos-220):pos+700])[:880],flush=True)
   else:
    for marker in ("campaign_item","__NEXT_DATA__","/api/","data-page","pagination","swiper"):
     print("MRBLOG MARKER",marker,body.count(marker),flush=True)
  except Exception as ex:print("ERROR",url,type(ex).__name__,str(ex)[:150],flush=True)
  time.sleep(.6)
if __name__=="__main__":main()
