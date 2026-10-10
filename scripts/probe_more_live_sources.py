#!/usr/bin/env python3
"""Audit candidate campaign sites; only fetch pages permitted by public robots.txt."""
import re,urllib.request,urllib.robotparser,urllib.parse,html
SOURCES={
 "ohmyblog":"https://ohmyblog.co.kr/",
 "realreview":"https://realreview.co.kr/",
 "storyn":"https://storyn.kr/",
 "blogdex":"https://blogdexreview.space/",
 "wereview":"https://wereview.fun/",
 "alljam":"https://alljam.co.kr/",
 "huki":"https://huki.co.kr/",
 "pavlovu":"https://pavlovu.com/",
 "nolleowa":"https://nolleowa.com/",
 "cloudreview":"https://cloudreview.co.kr/",
 "openreview":"https://openreview.kr/",
 "ddok":"https://ddok.co.kr/",
 "stylec":"https://stylec.co.kr/",
}
UA="ReviewSearchBot/0.1 (public campaign index research)"
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(req,timeout=14) as r:
  raw=r.read(1800000)
  encoding=re.search(r"charset=([\w-]+)",r.headers.get("Content-Type",""),re.I)
  for enc in ([encoding.group(1)] if encoding else [])+["utf-8","euc-kr","cp949"]:
   try:return r.geturl(),raw.decode(enc)
   except (UnicodeError,LookupError):pass
  return r.geturl(),raw.decode("utf-8","replace")
for name,home in SOURCES.items():
 print("\nSOURCE",name,home,flush=True)
 host=urllib.parse.urlparse(home).hostname
 try:
  _,robots=get("https://"+host+"/robots.txt")
  if not re.search(r"(?im)^\s*user-agent\s*:",robots):raise ValueError("No robots directives")
  rp=urllib.robotparser.RobotFileParser();rp.parse(robots.splitlines())
  print("ROBOTS",repr(robots[:750]),flush=True)
 except Exception as e:print("BLOCKED robots unavailable",repr(e)[:260],flush=True);continue
 for path in ["/"]:
  u=urllib.parse.urljoin(home,path)
  if not rp.can_fetch(UA,u):print("DISALLOWED",u,flush=True);continue
  try:
   final,doc=get(u)
   if re.search(r"cf-challenge|captcha|verify you are human",doc[:4000],re.I):
    print("CHALLENGE",flush=True);continue
   title=re.findall(r"<title[^>]*>([^<]+)",doc,re.I)[:1]
   links=[html.unescape(x) for x in re.findall(r'(?:href|data-href)=["\']([^"\']+)["\']',doc,re.I)]
   candidates=list(dict.fromkeys(x for x in links if re.search(r'campaign|review|experience|trial|event|detail|item|view|id=|idx=|seq=|/\\d{2,}',x,re.I) and not x.startswith("javascript:")))
   print("HOME",len(doc),"final",final,"title",title,"candidate_links",len(candidates),candidates[:20],flush=True)
   # Compact raw card sample (if direct campaign link)
   for link in candidates:
    if re.search(r"(?:campaign|detail|item|event|view|trial|[?&](?:id|idx|seq)=)",link,re.I) and not link.endswith("all"):
     pos=doc.find(link)
     print("SAMPLE",repr(doc[max(0,pos-250):pos+1800])[:2100],flush=True)
     break
   # Show lead search/schema snippets without dumping all site HTML
   for marker in ("모집기간","모집 마감","신청마감","신청기간","모집중","일 남음"):
    mm=re.search(re.escape(marker),doc)
    if mm:print("TEXT",marker,repr(re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',doc[max(0,mm.start()-300):mm.start()+370])))[:360]),flush=True)
  except Exception as e:print("FAIL",type(e).__name__,str(e)[:200],flush=True)

# Run the audit using only normal publicly advertised pages.
