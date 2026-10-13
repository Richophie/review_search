#!/usr/bin/env python3
"""Read-only compare production server-rendered count with GitHub snapshot."""
import json,re,urllib.request
BASE="https://review-search-two.vercel.app/"
MANIFEST="https://raw.githubusercontent.com/Richophie/review_search/main/public/data/collection_status.json"
def get(url,accept):
 req=urllib.request.Request(url,headers={"User-Agent":"ReviewSearchSmoke/0.2","Accept":accept,"Cache-Control":"no-cache"})
 with urllib.request.urlopen(req,timeout=35) as r:return r.status,r.read(2000000).decode("utf-8","replace")
status,body=get(BASE,"text/html")
assert status==200 and "체험단 모아보기" in body
m=re.search(r'현재[\s\S]{0,500}?<span[^>]*>([\d,]+)</span>',body)
if not m:
 at=body.find("현재")
 print("SSR total snippet:",body[at:at+700],flush=True)
 raise AssertionError("Cannot find campaign total in production SSR")
shown=int(m.group(1).replace(",",""))
_,raw=get(MANIFEST,"application/json")
data=json.loads(raw)
expected=data["snapshot_records"]
print("Production SSR total",shown,flush=True)
print("Live GitHub snapshot",expected,flush=True)
print("Platforms",data["platforms_with_records"],flush=True)
# A small difference is acceptable during a 10-minute live cache period.
tolerance=max(15,round(expected*0.025))
assert abs(shown-expected)<=tolerance,(shown,expected,tolerance)
print("Live production snapshot matches GitHub within cache tolerance",flush=True)
