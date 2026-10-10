#!/usr/bin/env python3
"""Inspect only allowed public endpoints of the six priority providers."""
import urllib.request,urllib.error,urllib.parse,urllib.robotparser,re
SITES={
  "강남맛집":("https://www.gangnammatzip.net/",["/"]),
  "레뷰":("https://www.revu.net/",["/"]),
  "미블":("https://www.mrblog.net/",["/campaigns/search?query=%ED%8F%AC%ED%95%AD","/campaigns/region","/campaigns","/"]),
  "리뷰노트":("https://www.reviewnote.co.kr/",["/","/campaigns"]),
  "디너의여왕":("https://dinnerqueen.net/",["/taste"]),
  "포블로그":("https://4blog.net/",["/list/all","/"]),
}
UA="ChehumMoaBot/0.1 (+read-only feasibility probe; respects robots.txt)"
def read(u):
 req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html,application/xml"})
 with urllib.request.urlopen(req,timeout=20) as r:
  return r.geturl(),r.read(2500000).decode("utf-8","replace")
for name,(root,paths) in SITES.items():
 print("\nSOURCE",name,root,flush=True)
 domain=urllib.parse.urlsplit(root).netloc
 try:
  _,rob=read("https://"+domain+"/robots.txt")
  if not re.search(r"(?im)^\s*user-agent\s*:",rob):raise ValueError("robots.txt not valid")
  parser=urllib.robotparser.RobotFileParser();parser.parse(rob.splitlines())
  print("ROBOTS",repr(rob[:950]),flush=True)
 except Exception as ex:
  print("ROBOTS unavailable, skipping",str(ex)[:160],flush=True);continue
 for path in paths:
  url=urllib.parse.urljoin(root,path)
  allowed=parser.can_fetch(UA,url)
  print("PATH",path,"allowed",allowed,flush=True)
  if not allowed:continue
  try:
   final,body=read(url)
   print("RESULT",len(body),"redirect",final,"title",re.findall(r"<title[^>]*>([^<]+)",body,re.I)[:1],"campaigns",len(re.findall(r'/campaign[s]?/\d+',body)),flush=True)
   if name=="포블로그" and path=="/list/all":
    match=re.search(r'href=["\'][^"\']*/campaign/\d+/?["\']',body)
    if match:
     a=max(0,match.start()-400);b=min(len(body),match.end()+1250)
     print("FOURBLOG SAMPLE",repr(body[a:b])[:1700],flush=True)
    print("FOURBLOG LINKS",re.findall(r'href=["\']([^"\']*/campaign/\d+/?)[\'"]',body)[:12],flush=True)
    chunks=re.findall(r'<a\s+class="nounderline"\s+href="/campaign/(\\d+)/">([\\s\\S]*?)</a>',body,re.I)
    print("FOURBLOG CARD MATCHES",len(chunks),flush=True)
    if chunks:
     print("FOURBLOG CARD BODY",repr(chunks[0][1])[:10000],flush=True)
    print("FOURBLOG PAGINATION",re.findall(r'(?:href|data-page)=["\\']([^"\\']*(?:page|pg|offset|limit)[^"\\']*)',body,re.I)[:20],flush=True)

   if name=="미블" and "search" in path:
    print("SEARCH POHANG",body.find("포항"),"LOGIN",body.find("비밀번호"),flush=True)
  except Exception as ex:print("FAILED",path,type(ex).__name__,str(ex)[:210],flush=True)

# Read-only public eligibility inspection; never request disallowed paths.
