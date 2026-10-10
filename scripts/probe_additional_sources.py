#!/usr/bin/env python3
"""Probe candidate source PUBLIC pages only; fail closed on robots.txt."""
import re,urllib.request,urllib.parse,urllib.robotparser,html,time
UA="ReviewSearchBot/0.1 (public listing feasibility; obey robots.txt)"
SOURCES={
 "bloglab":("https://bloglab.kr/",["/"]),
 "yogitg":("https://yogitg.co.kr/",["/"]),
 "chehumdan":("https://chehumdan.com/",["/"]),
 "cherrycook":("https://cherry-cook.com/",["/"]),
 "chvu":("https://chvu.co.kr/",["/"]),
 "gaboja":("https://xn--o39a04kpnjo4k9hgflp.com/",["/"]),
 "bqueens":("https://bqueens.net/",["/"]),
 "99das":("https://99das.com/",["/"]),
 "popomon":("https://popomon.com/",["/"]),
}
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xml","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(req,timeout=12) as r:
  buf=r.read(2200000)
  charset=re.search(r"charset=([\w-]+)",r.headers.get("Content-Type",""),re.I)
  for enc in ([charset.group(1)] if charset else [])+["utf-8","euc-kr","cp949"]:
   try:return r.geturl(),buf.decode(enc)
   except (UnicodeError,LookupError):pass
  return r.geturl(),buf.decode("utf-8","replace")
for name,(home,paths) in SOURCES.items():
 print("== SOURCE",name,home,flush=True)
 host=urllib.parse.urlparse(home).hostname
 try:
  _,raw=fetch("https://"+host+"/robots.txt")
  if not re.search(r"(?im)^\s*user-agent\s*:",raw):raise ValueError("No valid robots directives")
  rp=urllib.robotparser.RobotFileParser();rp.parse(raw.splitlines())
  print("ROBOTS",repr(raw[:1700]),flush=True)
 except Exception as ex:
  print("BLOCKED unknown robots",repr(ex)[:200],flush=True);continue
 for path in paths:
  url=urllib.parse.urljoin(home,path)
  print("PERMIT",path,rp.can_fetch(UA,url),flush=True)
  if not rp.can_fetch(UA,url):continue
  try:
   final,doc=fetch(url)
   if re.search(r"captcha|verify you are human|cloudflare challenge",doc[:2500],re.I):print("SKIP challenge");continue
   print("FETCH",len(doc),"url",final,"title",re.findall(r"<title[^>]*>([^<]+)",doc,re.I)[:1],flush=True)
   links=[html.unescape(x) for x in re.findall(r'(?:href|data-href)=["\']([^"\']+)["\']',doc,re.I)]
   candidates=list(dict.fromkeys(x for x in links if re.search(r"camp|campaign|review|detail|event|board|item|view|product|체험|\/\d{3,}|idx=|no=|id=",x,re.I) and not x.startswith("javascript:")))
   print("LINKS",len(links),"CANDIDATES",len(candidates),candidates[:35],flush=True)
   for marker in ("모집","신청","마감","D-day","남음","리뷰어","campaign"):
    mm=re.search(re.escape(marker),doc,re.I)
    if mm:print("TEXT",marker,repr(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(doc[max(0,mm.start()-220):mm.end()+700])))[:700]),flush=True)
   for h in candidates:
    if re.search(r"(?:view|detail|campaign|item|\/\d{3,}|idx=\d+)",h,re.I):
     ix=doc.find(h)
     print("CARD",repr(doc[max(0,ix-450):ix+3500])[:3800],flush=True);break
  except Exception as ex:
   print("ERROR",type(ex).__name__,str(ex)[:260],flush=True)
  time.sleep(.5)

# Probe observes site policies and stops at public HTML only.
