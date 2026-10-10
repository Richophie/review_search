#!/usr/bin/env python3
"""Inspect explicitly robots-allowed listing pagination for source coverage."""
import urllib.request,urllib.parse,urllib.robotparser,re,html,time
UA="ReviewSearchBot/0.1 (public campaign listing feasibility)"
CASES={
 "assaview":("https://www.assaview.co.kr/",["campaign_list.php?page=2","campaign_list.php?pg=2"]),
 "bqueens":("https://bqueens.net/",["taste?page=2","taste?page=3"]),
 "cherrycook":("https://cherry-cook.com/",["mission"]),
 "99das":("https://99das.com/",["amz/cmpn/amzCmpnList.do"]),
 "fourblog":("https://4blog.net/",["list/all?page=2","list/all?pg=2"]),
}
def req(u):
 r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html,application/xml"})
 with urllib.request.urlopen(r,timeout=13) as x:return x.geturl(),x.read(2600000).decode("utf-8","replace")
for name,(base,paths) in CASES.items():
 print("SOURCE",name,flush=True)
 host=urllib.parse.urlsplit(base).hostname
 try:
  _,robots=req("https://"+host+"/robots.txt")
  if not re.search(r"(?im)^user-agent\s*:",robots):raise ValueError("No robots directives")
  p=urllib.robotparser.RobotFileParser();p.parse(robots.splitlines())
 except Exception as e:print("SKIP unknown robots",str(e),flush=True);continue
 for path in paths:
  url=urllib.parse.urljoin(base,path)
  permitted=p.can_fetch(UA,url)
  print("PAGE",path,"permitted",permitted,flush=True)
  if not permitted:continue
  try:
   final,doc=req(url)
   ids={
    "assaview":re.findall(r'campaign\.php\?cp_id=(\d+)',doc),
    "bqueens":re.findall(r'href="/taste/(\d+)"',doc),
    "cherrycook":re.findall(r'href="/item/(\d+)"',doc),
    "99das":re.findall(r'(?:cmpn|event)[^"\']*(?:no|id|seq)=(\d+)',doc,re.I),
    "fourblog":re.findall(r'href="/campaign/(\d+)"',doc),
   }[name]
   print("RESULT",len(doc),"actual_url",final,"ids",len(ids),"unique",len(set(ids)),"first",list(dict.fromkeys(ids))[:9],flush=True)
   if name in ("cherrycook","99das"):
    print("CONTENT SAMPLE",repr(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(doc[:300000])))[:850]),flush=True)
  except Exception as e:print("FAIL",type(e).__name__,str(e)[:260],flush=True)
  time.sleep(.7)
