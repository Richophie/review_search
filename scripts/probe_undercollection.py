#!/usr/bin/env python3
"""Test real, robots-allowed listing pagination for current under-collected sources."""
import re,time,urllib.request,urllib.parse,urllib.robotparser
sources={
 "modootogether":("https://www.modootogether.com/",["campaign_list.php","campaign_list.php?page=2","campaign_list.php?page=3","campaign_list.php?pg=2","campaign_list.php?pg=3","campaign_list.php?category_id=047A&page=2","campaign_list.php?page=10","campaign_list.php?page=20","campaign_list.php?page=40"]),
 "fourblog":("https://4blog.net/",["list/all","list/all?page=2","list/all?page=3","list/all?pg=2","list/all?pg=3","list/all?pg=10","list/all?pg=20","list/all?pg=40"]),
 "assaview":("https://www.assaview.co.kr/",["campaign_list.php","campaign_list.php?page=7","campaign_list.php?page=15","campaign_list.php?page=25","campaign_list.php?page=40"]),
}
UA="ReviewSearchBot/0.1 (+public campaign list coverage)"
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(req,timeout=16) as r:return r.geturl(),r.read(2400000).decode("utf-8","replace")
for source,(base,urls) in sources.items():
 print("SOURCE",source,flush=True)
 try:
  _,rob=fetch(urllib.parse.urljoin(base,"robots.txt"))
  if not re.search(r"(?im)^\s*user-agent\s*:",rob):raise ValueError("Invalid robots")
  rp=urllib.robotparser.RobotFileParser();rp.parse(rob.splitlines())
 except Exception as ex:print("ROBOTS unavailable, skip",repr(ex)[:100]);continue
 ids_seen=set()
 for path in urls:
  url=urllib.parse.urljoin(base,path)
  if not rp.can_fetch(UA,url):
   print("DENIED",path);continue
  try:
   final,body=fetch(url)
   pat={
    "modootogether":r'campaign\.php\?cp_id=(\d+)',
    "fourblog":r'href="/campaign/(\d+)/"',
    "assaview":r'campaign\.php\?cp_id=(\d+)',
   }[source]
   ids=set(re.findall(pat,body))
   title=re.findall(r'<title[^>]*>([^<]+)',body,re.I)[:1]
   print("LIST",path,"len",len(body),"unique",len(ids),"new",len(ids-ids_seen),"first",list(ids)[:5],"actual",final,"title",title,flush=True)
   ids_seen|=ids
   if path==urls[0]:
    pages=list(dict.fromkeys(re.findall(r'href="([^"]*(?:page=|pg=|category_id=)[^"]*)"',body,re.I)))
    print("PAGINATION",pages[:35],flush=True)
  except Exception as ex:print("ERROR",path,repr(ex)[:150],flush=True)
  time.sleep(1.1)

# No private or disallowed listing endpoints.
