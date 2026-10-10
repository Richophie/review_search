#!/usr/bin/env python3
"""Inspect public campaign card HTML on selected official websites."""
import re,urllib.request,urllib.robotparser,urllib.parse,html
UA="ReviewSearchBot/0.1 (public listing research)"
SITES={
 "cherrycook":("https://cherry-cook.com/",["/"]),
 "gaboja":("https://xn--o39a04kpnjo4k9hgflp.com/",["/"]),
 "bqueens":("https://bqueens.net/",["/","/taste"]),
 "bloglab":("https://bloglab.kr/",["/"]),
 "chvu":("https://chvu.co.kr/",["/campaign"]),
}
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xml"})
 with urllib.request.urlopen(req,timeout=15) as r:return r.read(2500000).decode("utf-8","replace")
for name,(home,paths) in SITES.items():
 print("===",name,flush=True)
 host=urllib.parse.urlparse(home).hostname
 try:
  robots=get("https://"+host+"/robots.txt")
  if "User-agent" not in robots:continue
  rp=urllib.robotparser.RobotFileParser();rp.parse(robots.splitlines())
 except Exception as e:print("NO ROBOTS",str(e),flush=True);continue
 for path in paths:
  url=urllib.parse.urljoin(home,path)
  if not rp.can_fetch(UA,url):print("DISALLOWED",path,flush=True);continue
  try:body=get(url)
  except Exception as e:print("FAIL",path,str(e),flush=True);continue
  print("PAGE",path,len(body),flush=True)
  specs={
   "cherrycook": r'href="/item/(\d+)"',
   "gaboja": r'href="https://xn--o39a04kpnjo4k9hgflp.com/cmp/\?id=(\d+)"',
   "bqueens": r'href="/taste/(\d+)"',
   "bloglab":r'href="([^"]*?campaign[^"]+)"',
   "chvu":r'href="/campaign/(\d+)"',
  }
  regex=specs[name]
  hits=list(re.finditer(regex,body,re.I))
  print("MATCHES",len(hits),"UNIQUE",len(set(m.group(1) for m in hits)),flush=True)
  for ix,m in enumerate(hits[:2]):
   pre=max(0,m.start()-1400);end=min(len(body),m.end()+5000)
   print("CARD",ix,repr(body[pre:end])[:9500],flush=True)
  for pat in [r"(\d+)일\s*남",r"D[- ]\d+",r"모집\s*\d+",r"신청\s*\d+",r"\d{4}-\d\d-\d\d",r"\d{4}/\d\d/\d\d"]:
   print("PAT",pat,len(re.findall(pat,body)),flush=True)

# Read-only; public HTML, no authentication.
