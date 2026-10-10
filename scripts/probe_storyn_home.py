#!/usr/bin/env python3
"""Inspect only StoryN's robots-permitted public homepage campaign cards."""
import re,urllib.request,urllib.robotparser,urllib.parse,html
home="https://storyn.kr/"
UA="ReviewSearchBot/0.1 (public campaign listing)"
def fetch(u):
 req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=18) as r:return r.read(1100000).decode("utf-8","replace")
robots=fetch(urllib.parse.urljoin(home,"robots.txt"))
rp=urllib.robotparser.RobotFileParser();rp.parse(robots.splitlines())
assert rp.can_fetch(UA,home), "Homepage robots-restricted"
doc=fetch(home)
print("HTML bytes",len(doc),flush=True)
for pat in (r'review_campaign\.php\?cp_id=(\d+)',r'D-Day',r'신청\s*[\d,]+',r'모집\s*[\d,]+'):
 print("MATCH",pat,len(re.findall(pat,doc,re.I)),flush=True)
ids=list(dict.fromkeys(re.findall(r'review_campaign\.php\?cp_id=(\d+)',doc,re.I)))
print("IDS",ids[:20],flush=True)
for cid in ids[:3]:
 m=re.search(r'href=["\'][^"\']*review_campaign\.php\?cp_id='+cid+r'[^"\']*["\']',doc,re.I)
 if m: print("CARD",cid,repr(doc[max(0,m.start()-800):m.end()+3500])[:5000],flush=True)

# Homepage campaign-card inspection only.
