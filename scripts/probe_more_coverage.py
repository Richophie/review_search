#!/usr/bin/env python3
"""Discover bounded, robots-allowed pagination already published on linked providers."""
import re,urllib.request,urllib.parse,urllib.robotparser,time,html
UA="ReviewSearchBot/0.1 (+public index, honors robots)"
sites={
"cherrycook":("https://cherry-cook.com/",["mission","mission?page=2","mission?page=3","mission?pg=2","mission?pg=3"]),
"huki":("https://huki.co.kr/",["theme/huki/skin/board/gallery/productCampaign.php","theme/huki/skin/board/gallery/productCampaign.php?page=2","theme/huki/skin/board/gallery/localCampaign.php?page=2","theme/huki/skin/board/gallery/productCampaign.php?pg=2"]),
"pavlovu":("https://pavlovu.com/",["review_campaign_list.php","review_campaign_list.php?page=2","review_campaign_list.php?page=3","review_campaign_list.php?pg=2"]),
"nolleowa":("https://nolleowa.com/",["/"]),
"reviewplace":("https://reviewplace.co.kr/",["/"]),
"chvu":("https://chvu.co.kr/",["/"]),
"dailyview":("https://dailyview.kr/",["/"]),
"storyn":("https://storyn.kr/",["/"]),
"realreview":("https://realreview.co.kr/",["/"]),
}
def fetch(u):
 q=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html,application/xml","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(q,timeout=12) as r:return r.geturl(),r.read(2400000).decode("utf-8","replace")
for name,(base,paths) in sites.items():
 print("SITE",name,flush=True)
 try:
  _,txt=fetch(urllib.parse.urljoin(base,"robots.txt"))
  if not re.search(r"(?im)^\s*User-agent\s*:",txt):raise ValueError("invalid robots")
  rp=urllib.robotparser.RobotFileParser();rp.parse(txt.splitlines())
  print("ROBOTS",repr(txt[:800]),flush=True)
 except Exception as e:print("SKIP unknown robots",repr(e)[:200],flush=True);continue
 seen=set()
 for path in paths:
  u=urllib.parse.urljoin(base,path)
  allowed=rp.can_fetch(UA,u)
  print("URL",path,"ALLOWED",allowed,flush=True)
  if not allowed:continue
  try:
   redirect,doc=fetch(u)
   patterns={
    "cherrycook":r'href="/item/(\d+)"',
    "huki":r'wr_id=(\d+)',
    "pavlovu":r'review_campaign\.php\?cp_id=(\d+)',
    "nolleowa":r'(?:campaign|product|view)[^"\' ]*?(?:id|no|seq)=(\d+)',
    "reviewplace":r'(?:campaign|review|view)[^"\' ]*?(?:id|no|seq)=(\d+)',
    "chvu":r'(?:campaign|review|view)[^"\' ]*?(?:id|no|seq)=(\d+)',
    "dailyview":r'(?:campaign|review|view)[^"\' ]*?(?:id|no|seq)=(\d+)',
    "storyn":r'(?:campaign|review|view)[^"\' ]*?(?:id|no|seq)=(\d+)',
    "realreview":r'(?:campaign|review|view)[^"\' ]*?(?:id|no|seq)=(\d+)',
   }
   ids=set(re.findall(patterns[name],doc,re.I))
   print("RESULT",path,"length",len(doc),"ids",len(ids),"fresh",len(ids-seen),"final",redirect,"title",re.findall(r'<title[^>]*>([^<]+)',doc,re.I)[:1],flush=True)
   seen|=ids
   links=list(dict.fromkeys(html.unescape(x) for x in re.findall(r'href=["\']([^"\']+)["\']',doc,re.I) if re.search(r'page=|pg=|pageno=|pageNo=',x,re.I)))
   print("PAGINATION LINKS",links[:18],flush=True)
   if name not in ("pavlovu","huki","cherrycook"):
    interesting=list(dict.fromkeys(html.unescape(x) for x in re.findall(r'href=["\']([^"\']+)["\']',doc,re.I) if re.search("campaign|detail|review|experience|event|view",x,re.I)))
    print("INTERESTING LINKS",interesting[:16],flush=True)
  except Exception as e:print("FAIL",path,type(e).__name__,str(e)[:140],flush=True)
  time.sleep(.8)
