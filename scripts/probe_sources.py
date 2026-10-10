#!/usr/bin/env python3
"""Read only public index/robots pages for source feasibility analysis; no crawling."""
import re,urllib.request,urllib.robotparser,urllib.parse,xml.etree.ElementTree as ET
from html import unescape
SOURCES={
 "modootogether":"https://www.modootogether.com/",
 "modan":"https://modan.kr/",
 "tble":"https://tble.kr/",
 "dailyview":"https://dailyview.kr/",
 "reviewplace":"https://www.reviewplace.co.kr/",
}
AGENT="ChehumMoaBot/0.1 (+public listing index; respects robots.txt)"
def fetch(url):
 request=urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"text/html","Accept-Language":"ko-KR"})
 with urllib.request.urlopen(request,timeout=20) as r:
  content=r.read(2500000); ct=r.headers.get("Content-Type","")
  charset=re.search(r"charset=([\w-]+)",ct,re.I)
  if charset:
   try:return content.decode(charset[1],"replace")
   except LookupError:pass
  for enc in ("utf-8","euc-kr","cp949"):
   try:return content.decode(enc)
   except UnicodeDecodeError:pass
  return content.decode("utf-8","replace")
for name,base in SOURCES.items():
 print("===",name,base)
 try:
  rb=urllib.parse.urljoin(base,"/robots.txt")
  raw=fetch(rb)
  rp=urllib.robotparser.RobotFileParser();rp.parse(raw.splitlines())
  print("robots (first 20 lines):",repr(raw[:1500]))
  print("home permitted:",rp.can_fetch(AGENT,base))
  candidates={"modootogether":["/index.php","/campaign_list.php","/campaign_view.php"],
    "modan":["/","/campaigns"],"tble":["/","/campaign"],"dailyview":["/","/campaign"]}.get(name,[])
  print("path permits:",[(c,rp.can_fetch(AGENT,urllib.parse.urljoin(base,c))) for c in candidates])
  if not rp.can_fetch(AGENT,base):continue
  if name == "modan":
   feed="https://modan.kr/rss/campaigns.xml"
   print("RSS permitted",rp.can_fetch(AGENT,feed))
   if rp.can_fetch(AGENT,feed):
    feed_text=fetch(feed)
    print("RSS size",len(feed_text),"first800",repr(feed_text[:800]))
    try:
     feed_root=ET.fromstring(feed_text)
     items=feed_root.findall(".//item")
     print("RSS item count",len(items))
     for it in items[:3]:
      print("RSS sample",[(e.tag,e.text[:200] if e.text else "") for e in list(it)[:10]])
     if items:
      sample_link=items[0].findtext("link","")
      print("DETAIL sample URL",sample_link)
      if sample_link and rp.can_fetch(AGENT,sample_link):
       detail=fetch(sample_link)
       print("DETAIL HTML size",len(detail))
       for pat in [r".{0,100}(?:모집마감|마감일|종료일|신청기간|deadline|endsAt|endDate|apply_end|closeDate|recruitEnd|모집인원|신청인원|지원인원|신청\s*\d+\s*/\s*\d+).{0,230}"]:
        found=list(re.finditer(pat,detail,re.I))
        print("DETAIL relevant matches",len(found))
        for mm in found[:13]:print("DETAIL hit",repr(mm.group(0)[:330]))

    except Exception as ex:print("RSS parsing error",repr(ex))
  body=fetch(base)
  print("index bytes",len(body))
  hrefs=re.findall(r'(?:href|data-href)\s*=\s*["\']([^"\']{1,240})',body,re.I)
  output=[]
  for h in hrefs:
   if re.search(r"camp|review|detail|view|campaign|체험|모집",h,re.I):
    if h not in output:output.append(h)
  print("campaign-like links",output[:35])
  print("link stats",len(hrefs),"unique",len(set(hrefs)))
  for pat in [r"campaign[^<>]{0,80}",r"신청\s*[\d,]+\s*명",r"D-?Day\s*\d+",r'<a[^>]+href=["\'][^"\']*(?:campaign|view)[^"\']*']:
   m=re.search(pat,body,re.I)
   print("pattern",pat[:22],repr(body[max(0,m.start()-170):m.end()+250] if m else None)[:500])
 except Exception as e:print("FAILED",type(e).__name__,str(e)[:350])
