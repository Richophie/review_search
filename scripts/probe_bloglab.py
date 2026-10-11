#!/usr/bin/env python3
"""Bounded diagnostic of public Bloglab campaign cards; no data writes."""
import re,html
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from urllib.robotparser import RobotFileParser
HOST="https://www.bloglab.kr/"
UA="ReviewSearchBot/0.1 (+public campaign research; respects robots.txt)"
def get(url):
 with urlopen(Request(url,headers={"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"}),timeout=18) as r:
  raw=r.read(1800000)
  charset=r.headers.get_content_charset() or "utf-8"
  for enc in (charset,"utf-8","cp949","euc-kr"):
   try:return r.geturl(),raw.decode(enc)
   except (LookupError,UnicodeError):pass
  return r.geturl(),raw.decode("utf-8","replace")
def main():
 for origin in ("https://www.bloglab.kr/","https://bloglab.kr/"):
  try:
   ru=origin+"robots.txt";_,txt=get(ru)
   if not re.search(r"(?im)^\s*user-agent\s*:",txt):
    print("INVALID ROBOTS",ru,repr(txt[:220]),flush=True);continue
   rp=RobotFileParser();rp.parse(txt.splitlines())
   print("ROBOTS",ru,repr(txt[:1450]),flush=True)
   for path in ("","index.php","campaign_list.php","campaign_list.php?category=1"):
    url=urljoin(origin,path)
    if not rp.can_fetch(UA,url):
     print("ROBOTS BLOCKED",url,flush=True);continue
    try:
     final,doc=get(url)
     title=re.findall(r'<title[^>]*>([^<]+)',doc,re.I)[:1]
     print("PAGE_DIAGNOSTIC",url,"title",title,"start",re.sub(r"\\s+"," ",doc[:1300])[:1300],flush=True)
     if re.search(r"cf-challenge|verify you are human|Just a moment",doc[:2200],re.I) and not re.search("모집중|상시모집|실시간 리뷰",doc,re.I):
      print("CHALLENGE",url,flush=True);continue
     links=[html.unescape(x) for x in re.findall(r'(?:href|data-href)\s*=\s*["\x27]([^"\x27]+)',doc,re.I)]
     hits=list(dict.fromkeys([urljoin(final,u) for u in links if re.search(r"(?i)(?:view|item|detail|campaign|experience|review|\bno=|\bidx=|\bnum=|\bid=)",u)]))
     print("PAGE",url,"FINAL",final,"BYTES",len(doc),"TOTAL_LINKS",len(links),"CANDIDATE",len(hits),"SAMPLES",hits[:35],flush=True)
     for u in hits[:4]:
      needle=u.replace(origin,"")
      pos=doc.find(needle) if needle in doc else doc.find(u)
      print("CARD_HTML",re.sub(r"\s+"," ",doc[max(0,pos-450):pos+2000])[:2450],flush=True)
     for marker in ("상시모집","모집중","신청/","신청", "모집마감","마감","신청기간"):
      mat=re.search(re.escape(marker),doc,re.I)
      if mat:
       print("MARKER",marker,re.sub(r"\s+"," ",doc[max(0,mat.start()-180):mat.start()+380])[:560],flush=True)
    except Exception as e:print("PAGE ERROR",url,type(e).__name__,str(e)[:160],flush=True)
  except Exception as e:print("ROBOTS ERROR",origin,type(e).__name__,str(e)[:160],flush=True)
if __name__=="__main__":main()
