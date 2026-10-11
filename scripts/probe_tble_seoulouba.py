#!/usr/bin/env python3
"""Strictly robots-respecting public campaign page inspect for new platforms."""
import html,re,time
from urllib.parse import urljoin,urlparse
from collect import safe_fetch,plain
SOURCES={
 "tble":("https://tble.kr/",["/","/index.php","/campaign/list.php","/campaign/"]),
 "seoulouba":("https://m.seoulouba.co.kr/",["/","/campaign","/campaigns"])
}
def main():
 for name,(base,paths) in SOURCES.items():
  print("SOURCE",name,flush=True)
  for path in paths:
   u=urljoin(base,path)
   try:
    s=safe_fetch(u)
    if not s:
     print("UNAVAILABLE",u,flush=True);continue
    links=[html.unescape(x) for x in re.findall(r'(?:href|data-href)\s*=\s*["\x27]([^"\x27]+)',s,re.I)]
    candidates=list(dict.fromkeys(urljoin(u,x) for x in links
     if re.search(r"(?i)(?:list|detail|campaign|product|view|item|cp_id=|idx=|seq=|\d{4,})",x) 
     and not x.startswith(("javascript:","#","mailto:"))))
    print("PAGE",u,"bytes",len(s),"links",len(links),"candidate",len(candidates),
          "examples",candidates[:40],flush=True)
    for cand in candidates[:3]:
     key=cand.replace(base,"")
     pos=s.find(key)
     if pos<0:pos=s.find(cand)
     if pos>=0:print("CAND_CONTEXT",cand,re.sub(r"\s+"," ",s[max(0,pos-450):pos+1700])[:2100],flush=True)
    for label in ("1일 남음","오늘 마감","신청","모집","23:59","D-Day","더보기"):
     k=s.find(label)
     if k>=0:print("LABEL",label,re.sub(r"\s+"," ",s[max(0,k-300):k+450])[:730],flush=True)
   except Exception as exc:
    print("ERROR",u,type(exc).__name__,str(exc)[:170],flush=True)
   time.sleep(.45)
if __name__=="__main__":main()
