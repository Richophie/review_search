#!/usr/bin/env python3
"""HTTP integration tests: real data filters must alter result counts.

Read-only; no login or external API credentials.
"""
import re
import urllib.request
from urllib.parse import urlencode

BASE="https://review-search-pulim.vercel.app/"
TESTS={
  "all": {},
  "sido": {"sido":"서울"},
  "sigungu": {"sigungu":"포항"},
  "search": {"q":"포항"},
  "cat": {"cat":"맛집"},
  "cat_cafe": {"cat":"카페"},
  "type": {"type":"방문형"},
  "channel": {"ch":"블로그"},
  "low": {"tab":"lowcomp"},
  "nonsense": {"q":"__no_exact_campaign_match_test_731650__"},
}
out={}
for title,params in TESTS.items():
  url=BASE+("?" + urlencode(params) if params else "")
  req=urllib.request.Request(url,headers={"User-Agent":"ReviewSearchFilterTest/0.2"})
  with urllib.request.urlopen(req,timeout=40) as r:
    assert r.status==200,(title,r.status)
    body=r.read(2500000).decode("utf-8","replace")
  assert "체험단 모아보기" in body,(title,"No brand")
  if title=="all":
    assert "aspect-square" in body, "Card thumbnail not square"
    assert "사이트 전체" not in body, "Provider selector still visible"
  match=re.search(r'<strong[^>]*class="text-foreground"[^>]*>([\d,]+)</strong>\s*건',body)
  if not match:
    # Alternate SSR markup order/HTML encoding
    matches=re.findall(r'[\d,]{1,8}</strong>\s*건',body)
    raise AssertionError((title,"Cannot locate server-rendered result count",matches[:2],body.find("원본 보기")))
  n=int(match.group(1).replace(",",""))
  out[title]=n
  print(title,"=>",n,flush=True)
assert out["all"]>=100,("Missing real indexed results",out)
for title in ("sido","sigungu","search","cat","cat_cafe","type","channel","low"):
  assert 0 < out[title] < out["all"],(title,"filter did not narrow or incorrectly empty",out)
assert out["nonsense"]==0,("Nonexistent keyword should not match",out)
print("Verified live filters narrow actual results:",out)

# Regression check for real public source data and normalized search attributes.

# Recheck after verified 4blog source was added.
