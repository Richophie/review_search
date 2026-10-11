#!/usr/bin/env python3
"""Read-only audit of official publicly linked campaign listings.

Reports robots-permitted links, campaign IDs and D-day markers. No snapshot
writes; no authentication, private API, or challenges.
"""
import re,html,time
from urllib.parse import urljoin,urlparse
from collect import safe_fetch,plain
SOURCES={
 "mrblog":("https://www.mrblog.net/",["/","/campaigns","/campaign","/campaigns?area=서울","/campaigns?page=2"]),
 "modan":("https://modan.kr/",["/","/campaigns","/campaigns?page=2","/campaigns?category=지역","/rss/campaigns.xml"]),
 "fourblog":("https://4blog.net/",["/list/all","/list/all?pg=2","/list/all?pg=3"]),
}
def main():
 for name,(base,urls) in SOURCES.items():
  print("### SOURCE",name,flush=True)
  for path in urls:
   try:
    url=urljoin(base,path)
    body=safe_fetch(url)
    if not body:print("SKIP",url,flush=True);continue
    urlsFound=[html.unescape(m) for m in re.findall(r'(?:href|action)\s*=\s*["\x27]([^"\x27]+)',body,re.I)]
    links=list(dict.fromkeys(urljoin(url,t) for t in urlsFound if not t.startswith(("javascript:","#","mailto:"))))
    campaigns=list(dict.fromkeys(re.findall({
      "mrblog":r'(?:https://www\.mrblog\.net)?/campaigns/(\d+)',
      "modan":r'(?:https://modan\.kr)?/campaigns/(\d+)',
      "fourblog":r'/campaign/(\d+)/'
    }[name],body)))
    listlinks=[x for x in links if ("campaign" in x or "list" in x or "page=" in x or "region" in x or "/area" in x) and re.search(r'^(?:https://www\.mrblog\.net|https://modan\.kr|https://4blog\.net)/',x)]
    print("PAGE",url,"bytes",len(body),"campaigns",len(campaigns),
          "links",len(links),"listlinks",listlinks[:45],"sampleIDs",campaigns[:8],
          "markers",{k:body.count(k) for k in ("일 남음","D-Day","캠페인","다음","모집중")},
          flush=True)
    # Identify publicly advertised pagination markup and route hints.
    for marker in ("pagination","page=","current_page","totalPage","전체","더보기","loadMore","다음"):
     p=body.find(marker)
     if p>=0:
      cut=body[max(0,p-170):p+320]
      print("MARK",marker,re.sub(r'\s+',' ',cut)[:500],flush=True)
    if name=="modan" and path.endswith(".xml"):
     print("RSS HEAD",body[:1200],flush=True)
   except Exception as e:print("ERROR",name,path,type(e).__name__,str(e)[:150],flush=True)
   time.sleep(0.6)
if __name__=="__main__":main()
