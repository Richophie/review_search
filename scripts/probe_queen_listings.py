#!/usr/bin/env python3
"""Check public Queen-platform listing coverage and machine access rules."""
import re,time,urllib.parse,urllib.request,urllib.robotparser
UA="ReviewSearchBot/0.1 (+public campaign search index)"
SOURCES={"택배의여왕":"https://tqueens.net/","뷰티의여왕":"https://bqueens.net/"}
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(req,timeout=17) as r:return r.geturl(),r.read(3000000).decode("utf-8","replace")
for name,base in SOURCES.items():
 print("SOURCE",name,base,flush=True)
 try:
  _,rb=fetch(urllib.parse.urljoin(base,"robots.txt"))
  if not re.search(r"(?im)^user-agent\s*:",rb):raise ValueError("Invalid robots")
  p=urllib.robotparser.RobotFileParser();p.parse(rb.splitlines())
  print("ROBOTS",repr(rb[:1250]),flush=True)
 except Exception as ex:print("NO ROBOTS",repr(ex)[:200],flush=True);continue
 for page in (1,2,5,10,20):
  u=urllib.parse.urljoin(base,"taste"+(f"?page={page}" if page>1 else ""))
  allowed=p.can_fetch(UA,u)
  print("PAGE",page,"ALLOWED",allowed,flush=True)
  if not allowed:continue
  try:
   final,html=fetch(u)
   if re.search(r"cf-challenge|Just a moment",html[:5000],re.I):
    print("CHALLENGE",page,flush=True);continue
   cards=html.split('class="qz-dq-card campaign')[1:]
   ids=set(re.findall(r'href="/taste/(\d+)"',html))
   print("RESULT",page,"URL",final,"BYTES",len(html),"CARDS",len(cards),"LINKS",len(ids),"DAYLABELS",len(re.findall(r"\d+\s*일 남음",html)),flush=True)
   if cards:print("SAMPLE",repr(cards[0][:1100]),flush=True)
   if name=="택배의여왕" and page==1:
    idx=html.find('<div class="item">')
    print("TQUEENS_ITEM_POS",idx,flush=True)
    if idx>=0: print("TQUEENS_ITEM_SAMPLE",repr(html[idx:idx+4300]),flush=True)
    match=re.search(r'href="/taste/\\d+"',html)
    if match:
     print("TQUEENS_LINK_SAMPLE",repr(html[max(0,match.start()-3300):match.start()+2400])[:5900],flush=True)
  except Exception as ex:print("ERROR",page,repr(ex)[:180],flush=True)
  time.sleep(1.3)

# Public pages only; no authentication or bot-control workarounds.
