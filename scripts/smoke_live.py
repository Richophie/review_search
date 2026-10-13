#!/usr/bin/env python3
"""Read-only production smoke test for server-rendered search and filter URLs."""
import re
import urllib.error
import urllib.request
from urllib.parse import urlencode

BASE="https://review-search-two.vercel.app/"
CASES=[
  ("전국 기본",{}),
  ("경쟁률 낮은순",{"sort":"ratio","tab":"lowcomp"}),
  ("마감 임박",{"sort":"deadline","tab":"soon"}),
  ("지역 검색",{"sido":"서울","q":"서울"}),
  ("새로 발견한 공고",{"tab":"new"}),
  ("두 번째 페이지",{"page":"2"}),
  ("깊은 페이지 직접 접근",{"page":"400"}),
  ("없는 검색어",{"q":"__chehum_search_no_results_test__"}),
]
for title,params in CASES:
 url=BASE+("?" + urlencode(params) if params else "")
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"ReviewSearchSmokeTest/0.1","Accept":"text/html"})
  with urllib.request.urlopen(req,timeout=25) as r:
   body=r.read(2000000).decode("utf-8","replace")
   status=r.status
   ctype=r.headers.get("content-type","")
 except Exception as exc:
  raise AssertionError(f"{title}: request failed: {exc}") from exc
 assert status==200 and "text/html" in ctype, (title,status,ctype)
 assert "체험단 모아보기" in body, (title,"brand missing",len(body),body[:300])
 assert "전국 체험단" in body, (title,"search UI missing",len(body),body[:300])
 assert "An unexpected error has occurred" not in body, (title,"runtime error page")
 assert "페이지를 불러오지 못했어요" not in body, (title,"app error component")
 if not params:
  assert "원본 보기" in body or "원본 ↗" in body, (title,"No real campaign result cards rendered")
  assert "마지막" in body, (title,"Numbered pagination missing")
  assert "오늘 새로 발견" in body, (title,"Discovery-day label missing")
 if params.get("q") == "__chehum_search_no_results_test__":
  assert "원본 보기" not in body and "원본 ↗" not in body, (title,"Impossible query returned a campaign")
 print(title,"OK",status,"HTML bytes",len(body),"contains search UI")
print("All production smoke checks passed.")
