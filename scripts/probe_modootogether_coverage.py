#!/usr/bin/env python3
"""Inspect robots-permitted ModooTogether lists for missed campaign cards."""
import re,html,time,json,urllib.parse
from urllib.parse import urljoin
from collect import safe_fetch,plain,one
BASE="https://www.modootogether.com/"
PAGES=["","campaign_list.php","campaign_list.php?category_id=047A",
       "campaign_list.php?category_id=001A","campaign_list.php?page=2",
       "campaign_list.php?page=3"]
def main():
 for rel in PAGES:
  url=urljoin(BASE,rel)
  try:
   doc=safe_fetch(url)
   if not doc:print("UNAVAILABLE",rel,flush=True);continue
   cards=re.findall(r'<li>\s*<div class="box">([\s\S]*?)</li>',doc,re.I)
   matches=re.findall(r'campaign\.php\?cp_id=(\d+)',doc,re.I)
   dds=re.findall(r'(?:D-?\s*day|D-\d+|상시모집|모집마감)',doc,re.I)
   print("LIST",rel,"bytes",len(doc),"distinct links",len(set(matches)),
         "cards",len(cards),"deadline markers",len(dds),"raw candidates",matches[:8],flush=True)
   for c in cards[:5]:
    cid=one(r'campaign\.php\?cp_id=(\d+)',c)
    txt=plain(c)[:400]
    dtag=plain(one(r'<span[^>]*class="[^"]*\bdday\b[^"]*"[^>]*>([\s\S]*?)</span>',c))
    print("CARD",cid,"dday",dtag,"text",txt,"HTML",re.sub(r'\s+',' ',c[:3900])[:3900],flush=True)
   for mark in ("page=", "pg=", "p=", "paging","pagination","page-link"):
    pos=doc.lower().find(mark.lower())
    if pos>=0:print("PAGE_CONTROL",mark,re.sub(r'\s+',' ',doc[max(0,pos-180):pos+360])[:540],flush=True)
  except Exception as e: print("ERROR",rel,type(e).__name__,str(e)[:200],flush=True)
  time.sleep(0.7)

def probe_published_ajax():
    """Uses only the publicly advertised GET URL from the page's own JS."""
    for cat,page in (("",1),("",2),("",3),("047A",1),("047A",2)):
        query=urllib.parse.urlencode({
            "json":"list","category_id":cat,"keyword":"",
            "cp_media":"","orderby":"","page":str(page)
        })
        url=BASE+"campaign_list.php?"+query
        try:
            raw=safe_fetch(url)
            if not raw:
                print("PUBLIC AJAX UNAVAILABLE",cat,page,flush=True);continue
            data=json.loads(raw)
            keys=list(data) if isinstance(data,dict) else []
            print("AJAX",cat,page,"bytes",len(raw),"keys",keys,
                  "count",data.get("count") if isinstance(data,dict) else None,
                  "sample",raw[:1900],flush=True)
        except Exception as exc:
            print("PUBLIC AJAX ERROR",cat,page,type(exc).__name__,str(exc)[:200],flush=True)
        time.sleep(1)

if __name__=="__main__":
 main()
 probe_published_ajax()
