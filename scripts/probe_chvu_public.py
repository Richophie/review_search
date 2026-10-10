#!/usr/bin/env python3
"""Inspect a publicly advertised campaign LIST route, never its restricted detail routes."""
import re,urllib.request,urllib.robotparser,urllib.parse
BASE="https://chvu.co.kr"
UA="ReviewSearchBot/0.1 (+public campaign list inspection)"
def fetch(u):
 req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=15) as r:return r.geturl(),r.read(2600000).decode("utf-8","replace")
_,rb=fetch(BASE+"/robots.txt")
rules=urllib.robotparser.RobotFileParser();rules.parse(rb.splitlines())
for path in ("/campaign","/campaign/","/campaign?sort=latest"):
 url=BASE+path
 allowed=rules.can_fetch(UA,url)
 print("PATH",path,"allowed",allowed,flush=True)
 if not allowed:continue
 try:
  final,html=fetch(url)
  print("RESULT",len(html),"url",final,flush=True)
  for pat in (r'__NEXT_DATA__',r'/campaign/(\d+)',r'(\d+)\s*명\s*모집',r'"campaigns"\s*:',r'"campaignList"\s*:',r'"title"\s*:',r'계약',r'모집',r'__next_f.push'):
   m=list(re.finditer(pat,html,re.I))
   print("PAT",pat,"count",len(m),flush=True)
   if m:print("SAMPLE",repr(html[max(0,m[0].start()-250):m[0].start()+1600])[:1850],flush=True)
 except Exception as e:print("FAIL",repr(e)[:250],flush=True)
