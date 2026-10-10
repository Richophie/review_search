#!/usr/bin/env python3
"""Verify robots rules and public recruitment cards of two official platforms."""
import re,urllib.request,urllib.parse,urllib.robotparser,html
SOURCES={
 "후기업":("https://www.whogiup.com/",["/","/details?idx=12977"]),
 "리뷰진":("https://www.reviewjin.com/",["/"]),
}
UA="ReviewSearchBot/0.1 (public campaign listings)"
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(req,timeout=14) as r:
  buf=r.read(2500000)
  for enc in ("utf-8","euc-kr","cp949"):
   try:return r.geturl(),buf.decode(enc)
   except UnicodeError:pass
  return r.geturl(),buf.decode("utf-8","replace")
for name,(home,paths) in SOURCES.items():
 print("SOURCE",name,flush=True)
 try:
  _,robots=fetch(urllib.parse.urljoin(home,"robots.txt"))
  if not re.search(r"(?im)^User-agent\s*:",robots):raise ValueError("No robots directives")
  rule=urllib.robotparser.RobotFileParser();rule.parse(robots.splitlines())
  print("ROBOTS",repr(robots[:1900]),flush=True)
 except Exception as e:
  print("SKIP ROBOTS UNKNOWN",repr(e)[:250],flush=True);continue
 for path in paths:
  url=urllib.parse.urljoin(home,path)
  print("PATH",path,"ALLOWED",rule.can_fetch(UA,url),flush=True)
  if not rule.can_fetch(UA,url):continue
  try:
   final,body=fetch(url)
   print("RESULT",len(body),"REDIRECT",final,"TITLE",re.findall(r"<title[^>]*>([^<]+)",body,re.I)[:1],flush=True)
   links=[html.unescape(x) for x in re.findall(r'(?:href|data-href)=["\']([^"\']+)["\']',body,re.I)]
   campaigns=list(dict.fromkeys(x for x in links if re.search("details|campaign|experience|review|list|idx=",x,re.I)))
   print("LINKS",len(links),"RELEVANT",len(campaigns),campaigns[:32],flush=True)
   for term in ("모집기간","모집 기간","모집마감","신청자","모집 인원","2026-10","campaigns"):
    m=re.search(re.escape(term),body,re.I)
    if m:print("MARKER",term,repr(body[max(0,m.start()-600):m.start()+900])[:1600],flush=True)
   if campaigns:
    sample=campaigns[0]; pos=body.find(sample)
    print("HTML SAMPLE",repr(body[max(0,pos-550):pos+2450])[:3150],flush=True)
  except Exception as e:print("FAILED",path,type(e).__name__,str(e)[:160],flush=True)
