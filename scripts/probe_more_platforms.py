#!/usr/bin/env python3
"""Read-only inspection of public campaign lists; respect robots.txt."""
import urllib.request,urllib.robotparser,urllib.parse,html,re,time,json
sites={
 "assaview":("https://www.assaview.co.kr/",["/campaign_list.php","/campaign_list.php?type=area","/"]),
 "ohmyblog":("https://ohmyblog.co.kr/",["/"]),
 "ringble":("https://www.ringble.co.kr/",["/"]),
 "seoulouba":("https://m.seoulouba.co.kr/",["/"]),
 "tble":("https://tble.kr/",["/"]),
 "dilo":("https://dilo.kr/",["/trials","/"]),
}
ua="ReviewSearchBot/0.1 (+public campaign index; obeys robots.txt)"
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":ua,"Accept":"text/html,application/xml","Accept-Language":"ko-KR,ko;q=0.9"})
 with urllib.request.urlopen(req,timeout=18) as r:
  b=r.read(2800000)
  for enc in ("utf-8","euc-kr","cp949"):
   try:return r.geturl(),b.decode(enc)
   except UnicodeDecodeError:pass
  return r.geturl(),b.decode("utf-8","replace")
for source,(home,paths) in sites.items():
 print("\n###",source,home,flush=True)
 host=urllib.parse.urlsplit(home).hostname
 try:
  _,raw=get("https://"+host+"/robots.txt")
  if not re.search(r"(?im)^\s*user-agent\s*:",raw):raise ValueError("invalid robots.txt")
  rp=urllib.robotparser.RobotFileParser();rp.parse(raw.splitlines())
  print("ROBOTS",repr(raw[:1150]),flush=True)
 except Exception as ex:
  print("ROBOTS-UNKNOWN: DO NOT FETCH",str(ex)[:250],flush=True)
  continue
 for path in paths:
  url=urllib.parse.urljoin(home,path)
  print("PATH",path,"permitted",rp.can_fetch(ua,url),flush=True)
  if not rp.can_fetch(ua,url):continue
  try:
   final,doc=get(url)
   if "captcha" in doc[:800].lower() or "location.href" in doc[:600].lower():
    print("CHALLENGE DETECTED; skip");continue
   print("HTTP RESULT",len(doc),final,flush=True)
   print("TITLE",re.findall(r"<title[^>]*>([^<]+)",doc,re.I)[:1],flush=True)
   links=[html.unescape(x) for x in re.findall(r'(?:href|data-href)=["\']([^"\']+)["\']',doc,re.I)]
   hit=[x for x in links if re.search(r"camp|campaign|trial|review|detail|experience|체험|\/\d+|view",x,re.I) and not re.search("javascript:",x,re.I)]
   unique=list(dict.fromkeys(hit))
   print("LINKS",len(links),"interesting",unique[:38],flush=True)
   for marker in ("신청","모집","D-","남음","마감","campaign","체험단"):
    m=re.search(re.escape(marker),doc,re.I)
    if m:
     p=doc[max(0,m.start()-400):m.end()+700]
     print("SAMPLE",marker,repr(p)[:1050],flush=True)
   if source=="ringble" and path=="/":
    chunks=doc.split("store_list_wrap")[1:]
    print("RINGBLE CHUNKS",len(chunks),flush=True)
    for chunk in chunks[:3]:
     raw=chunk[:11500]
     text=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',raw))).strip()
     print("RINGBLE TEXT",repr(text[:1750]),flush=True)
     print("RINGBLE HTML",repr(raw[:7800]),flush=True)
   if source=="assaview":
    sample=re.search(r'(?:href=["\'](?:\./)?campaign\.php\?cp_id=\d+["\'])',doc,re.I)
    if sample:
     li=doc.rfind("<li",0,sample.start())
     en=doc.find("</li>",sample.end())
     start=li if li>0 and sample.start()-li<7000 else max(0,sample.start()-500)
     end=en+5 if en>start and en-start<11000 else sample.end()+6500
     print("ASSA CARD",repr(doc[start:end])[:9500],flush=True)
    print("ASSA distinct campaigns",len(set(re.findall(r"campaign\.php\?cp_id=\d+",doc))),flush=True)

    cards=re.findall(r'<a\s+href="campaign\.php\?cp_id=(\d+)"[^>]*>([\s\S]*?)</a>',doc,re.I)
    print("ASSA LINK CARD COUNT",len(cards),flush=True)
    for cid,fragment in cards[:7]:
     plain=re.sub(r'<[^>]+>',' ',fragment)
     plain=re.sub(r'\s+',' ',html.unescape(plain)).strip()
     print("ASSA CARD TEXT",cid,repr(plain[:700]),flush=True)
     print("ASSA CARD IMAGE",cid,re.findall(r'<img[^>]+src=["\']([^"\']+)',fragment,re.I)[:1],flush=True)
     print("ASSA CARD DATES",cid,re.findall(r'(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|D-\d+|\d+\s*일\s*남음|마감)',fragment,re.I)[:9],flush=True)
    print("ASSA DATE COUNT",len(re.findall(r'\d{4}/\d{1,2}/\d{1,2}',doc)),flush=True)

    for field in ["campaign_list.php","campaign_list?","type=area","cp_id="]:
     print("ASSA",field,doc.find(field),flush=True)
   if source=="dilo" and path=="/trials":
    for pat in [r'"trials"\s*:',r'"applyDeadline"\s*:',r'"applicationDeadline"\s*:',r'"title"\s*:',r'/trials/[0-9a-f-]{10,}',r'"trial_id"',r'"recruitmentEnd"',r'"deadline"']:
     m=re.search(pat,doc,re.I)
     if m:print("DILO DATA",pat,repr(doc[max(0,m.start()-500):m.start()+2000])[:2400],flush=True)
   for link in unique:
    if re.search(r"\d{3,}",link):
     ix=doc.find(link)
     print("CARD-NEAR-HREF",repr(doc[max(0,ix-500):ix+2500])[:3500],flush=True)
     break
  except Exception as ex:print("FETCH FAIL",type(ex).__name__,str(ex)[:200],flush=True)
  time.sleep(.5)

# Probe only public permitted pages; no login or endpoint discovery behind access controls.
