#!/usr/bin/env python3
"""Read-only source feasibility for two high-priority review platforms.

Respect each site's robots.txt and never fetch login/private URLs, authenticated
endpoints or hidden APIs. This script is a diagnostic, not a campaign collector.
"""
import html,re,urllib.parse,urllib.request,urllib.robotparser
UA="ReviewSearchResearch/0.1 (public listing availability audit)"
SITES={
 "popomon":("https://popomon.com/",["/","/campaign","/campaignList","/campaign/list","/sitemap.xml"]),
 "mrblog":("https://www.mrblog.net/",["/","/campaigns","/campaigns/region","/campaigns/search?query=%ED%8F%AC%ED%95%AD","/sitemap.xml"])
}
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xml","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(req,timeout=13) as r:
  data=r.read(1900000)
  return r.geturl(),r.headers.get("Content-Type",""),data.decode("utf-8","replace")
for name,(origin,paths) in SITES.items():
 host=urllib.parse.urlsplit(origin).hostname
 print("SOURCE",name,origin,flush=True)
 try:
  final,_,robots=get("https://"+host+"/robots.txt")
  if not re.search(r"(?im)^\s*User-agent\s*:",robots):
   raise RuntimeError("Invalid or unavailable robots.txt")
  rp=urllib.robotparser.RobotFileParser();rp.parse(robots.splitlines())
  print("ROBOTS",repr(robots[:2000]),flush=True)
 except Exception as exc:
  print("NO RELIABLE ROBOTS DECISION; SKIP",repr(exc)[:220],flush=True)
  continue
 for path in paths:
  url=urllib.parse.urljoin(origin,path)
  allowed=rp.can_fetch(UA,url)
  print("PATH",path,"allowed",allowed,flush=True)
  if not allowed:continue
  try:
   final,ct,page=get(url)
   if re.search(r"verify you are human|cf-challenge|captcha challenge|<title>access denied",page[:12000],re.I):
    print("CHALLENGE; SKIP",path,flush=True);continue
   anchors=[html.unescape(a) for a in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\']',page,re.I)]
   links=list(dict.fromkeys(a for a in anchors if re.search(r'camp|campaign|review|deal|recruit|apply|list|sitemap|\/\d{3,}',a,re.I) and not a.startswith("#")))
   print("RESULT",path,"len",len(page),"redirect",final,"type",ct[:70],"links",len(links),flush=True)
   print("LINK EXAMPLES",links[:30],flush=True)
   for key in ("포항","모집","신청 0명","일 남음","recruitment","campaignList","__NEXT_DATA__","__NUXT__","login","로그인"):
    print("MARKER",repr(key),page.find(key),flush=True)
   for q in (r'<script[^>]*src=["\']([^"\']+)',r'<link[^>]*rel=["\'](?:preload|prefetch)[^>]*href=["\']([^"\']+)'):
    print("SCRIPT ASSET SAMPLES",re.findall(q,page,re.I)[:8],flush=True)
  except Exception as exc:
   print("ERROR",path,type(exc).__name__,str(exc)[:210],flush=True)
