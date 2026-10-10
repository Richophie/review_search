#!/usr/bin/env python3
"""Inspect cards on public, robots-permitted pages of Huki, OpenReview and WeReview."""
import re,html,urllib.request,urllib.parse,urllib.robotparser
UA="ReviewSearchBot/0.1 (public campaign summaries)"
targets={
 "huki":("https://huki.co.kr/",["/","/theme/huki/skin/board/gallery/productCampaign.php","/theme/huki/skin/board/gallery/localCampaign.php"]),
 "openreview":("https://openreview.kr/",["/","/main/m/page/exp_list.php?ex_adver_type=area","/main/m/page/exp_list.php?ex_adver_type=product"]),
 "wereview":("https://www.wereview.fun/",["/campaign-list"]),
 "pavlovu":("https://pavlovu.com/",["/sitemap_campaign.php"]),
}
def get(url):
 r=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xml"})
 with urllib.request.urlopen(r,timeout=15) as x:
  b=x.read(2100000)
  return x.geturl(),b.decode("utf-8","replace")
for name,(base,paths) in targets.items():
 print("\n===",name,flush=True)
 try:
  _,rb=get(urllib.parse.urljoin(base,"/robots.txt"))
  if not re.search(r"(?mi)^user-agent\s*:",rb):raise ValueError("No robots")
  rules=urllib.robotparser.RobotFileParser();rules.parse(rb.splitlines())
 except Exception as e:print("ROBOTS BLOCK",repr(e)[:150],flush=True);continue
 for path in paths:
  url=urllib.parse.urljoin(base,path)
  print("PERMIT",path,rules.can_fetch(UA,url),flush=True)
  if not rules.can_fetch(UA,url):continue
  try:
   actual,body=get(url)
   print("PAGE",path,len(body),"FINAL",actual,flush=True)
   if name=="huki":
    for pattern in [r'href="([^"]*(?:wr_id|view\.php|\.html)\b[^"]*)"',r'wr_subject',r'class="[^"]*campaign[^"]*"',r'D-(\d+)',r'<li class="[^"]*item[^"]*"']:
     m=list(re.finditer(pattern,body,re.I));print("PAT",pattern,len(m),flush=True)
     if m: print("PAT SAMPLE",repr(body[max(0,m[0].start()-600):m[0].start()+2600])[:3150],flush=True)
   if name=="openreview":
    pats=[r'href="([^"]*exp_view\.php\?ex_idx=\d+[^"]*)"',r'D-?\s*\d+',r'<div class="horizontal-card">',r'<div class="vertical-card">',r'\d{4}-\d\d-\d\d']
    for pat in pats:
     m=list(re.finditer(pat,body,re.I));print("PAT",pat,len(m),flush=True)
     if m:print("PAT SAMPLE",repr(body[max(0,m[0].start()-150):m[0].start()+3100])[:3400],flush=True)
   if name=="wereview":
    for pat in [r'href="([^"]*/campaign(?:/\d+|-detail[^"]*)?)"',r'__NEXT_DATA__',r'campaignName',r'recruitEndDate',r'deadline']:
     m=list(re.finditer(pat,body,re.I));print("PAT",pat,len(m),flush=True)
     if m:print("PAT SAMPLE",repr(body[max(0,m[0].start()-220):m[0].start()+1400])[:1700],flush=True)
   if name=="pavlovu":
    print("XML HEAD",repr(body[:1700]),flush=True)
  except Exception as e:print("FAIL",repr(e)[:270],flush=True)

# Check only robots-permitted HTML/XML pages.
