#!/usr/bin/env python3
"""Read-only robots-aware campaign source discovery (no credentials/bypass)."""
import re,html,json,time
from urllib.parse import urljoin,urlsplit,parse_qs
from collect import safe_fetch
sources={
 "popomon":[
   "https://popomon.com/",
   "https://www.popomon.com/",
 ],
 "revu":[
   "https://webview.revu.net/",
   "https://www.revu.net/",
   "https://revu.net/",
 ],
 "mrblog":[
   "https://www.mrblog.net/",
   "https://www.mrblog.net/campaigns/region",
   "https://www.mrblog.net/campaigns/delivery",
   "https://www.mrblog.net/campaigns",
   "https://www.mrblog.net/campaigns?category=맛집",
 ],
}
for name,urls in sources.items():
  print("SOURCE",name,flush=True)
  for u in urls:
    try:
      page=safe_fetch(u)
      if not page:
        print("NOT_AVAILABLE",u,flush=True);continue
      anchors=[html.unescape(x) for x in re.findall(r'(?:href|data-href)=["\']([^"\']+)',page,re.I)]
      links=list(dict.fromkeys(urljoin(u,a) for a in anchors if not a.startswith(("javascript:","#","mailto:"))))
      relevant=[a for a in links if re.search(r"(?:campaign|review|experience|detail|view|list|/cp/|/taste|page=|/events/)",a,re.I)]
      ids=list(dict.fromkeys(re.findall(r"/campaigns/(\d+)",page)))
      scripts=list(dict.fromkeys(re.findall(r'<script[^>]*src=["\']([^"\']+)',page,re.I)))
      print("PUBLIC_HTML",u,"bytes",len(page),"links",len(links),"campaignIds",len(ids),
         "linksSample",relevant[:35],"scriptCount",len(scripts),"scriptsSample",scripts[-12:],
         "headTitle",re.findall(r"<title[^>]*>([^<]+)",page,re.I)[:1],flush=True)
      for word in ("모집중","모집","전체","신청","마감","캠페인","__NEXT_DATA__","__NUXT__","__INITIAL_STATE__","campaign_item"):
        n=page.find(word)
        if n>=0:print("MARK",name,word,re.sub(r"\s+"," ",page[max(0,n-150):n+390])[:560],flush=True)
      if name=="popomon":
        print("HTML_START",re.sub(r"\s+"," ",page[:2600]),flush=True)
      if name=="mrblog" and ids:
        for cid in ids[:2]:
          n=page.find("/campaigns/"+cid)
          print("MRBLOG_SAMPLE",cid,re.sub(r"\s+"," ",page[max(0,n-350):n+1500])[:1900],flush=True)
    except Exception as ex:print("ERROR",u,type(ex).__name__,str(ex)[:230],flush=True)
    time.sleep(0.6)
