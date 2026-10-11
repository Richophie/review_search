#!/usr/bin/env python3
"""Audit directly linked, robots-permitted Odiya campaigns without writing data."""
import re,html
from urllib.parse import urljoin,urlparse,parse_qs
from urllib.request import Request,urlopen
from urllib.robotparser import RobotFileParser
AGENT="ChehumMoaBot/0.1 (+public listing index; respects robots.txt)"
BASE="https://odiya.kr/"
PAGES=[BASE,BASE+"category.php?category=829",BASE+"category.php?category=832",BASE+"category.php?category=834",BASE+"category.php?category=1016"]
def get(url):
    with urlopen(Request(url,headers={"User-Agent":AGENT,"Accept-Language":"ko-KR,ko;q=0.9"}),timeout=20) as h:return h.read(600_000).decode("utf-8","replace")
def main():
    rp=RobotFileParser();rp.parse(get(BASE+"robots.txt").splitlines())
    for u in PAGES:
        if not rp.can_fetch(AGENT,u):print("blocked",u,flush=True);continue
        try:
            body=get(u)
            links=[html.unescape(s) for s in re.findall(r'href\s*=\s*["\x27]([^"\x27]+)',body,re.I)]
            details=list(dict.fromkeys(urljoin(u,l) for l in links if "detail.php" in l and "odiya.kr" in urljoin(u,l)))
            print("PAGE",u,"bytes",len(body),"detail links",len(details),"samples",details[:12],flush=True)
            for v in details[:2]:
                m=body.find(v[len(BASE):])
                if m<0:m=body.find(v.replace(BASE,""))
                if m<0:m=body.find(v)
                print("ANCHOR_CONTEXT",re.sub(r"\s+"," ",body[max(m-1200,0):m+1200])[:2600],flush=True)
            if u==BASE:
                dm=re.search(r'onclick=location.href=["\x27](detail\.php\?number=\d+[^"\x27]*)',body)
                if dm:
                    du=urljoin(BASE,html.unescape(dm.group(1)))
                    if rp.can_fetch(AGENT,du):
                        db=get(du)
                        for key,pat in (("og:title",r'<meta[^>]+property=["\x27]og:title["\x27][^>]+content=["\x27]([^"\x27]+)'),("page title",r'<title[^>]*>([\s\S]*?)</title>'),("h1",r'<h1[^>]*>([\s\S]*?)</h1>')):
                            m=re.search(pat,db,re.I)
                            print("DETAIL_FIELD",key,html.unescape(m.group(1)[:250]) if m else "MISSING",flush=True)
                        for marker in ("리뷰어신청","모집인원","신청","캠페인 기간"):
                            p=db.find(marker)
                            if p>=0: print("DETAIL_CONTEXT",marker,re.sub(r"\\s+"," ",db[max(0,p-550):p+700])[:1100],flush=True)
            for mark in ("리뷰어신청", "신청&nbsp;", "모집인원", "신청\u00a0", "리뷰어발표"):
                hit=body.find(mark)
                if hit>=0:
                    print("CARD_CONTEXT",mark,re.sub(r"\\s+"," ",body[max(0,hit-1300):hit+2700])[:3800],flush=True)
            blocks=re.findall(r'<div[^>]*\bclass\s*=\s*["\x27][^"\x27]*rows_margin[^"\x27]*["\x27]',body,re.I)
            click_links=re.findall(r'onclick\s*=\s*location\.href=["\x27](detail\.php\?number=\d+[^"\x27]*)',body,re.I)
            print("CARD AUDIT",u,"rows_margin attrs",len(blocks),"samples",blocks[:12],
                  "onclick unique",len(set(click_links)),"onclick first",click_links[:10],flush=True)
            for keyword in ("리뷰어신청","신청","모집","detail.php","D-"):
                print("COUNT",keyword,body.count(keyword),flush=True)
        except Exception as e:print("ERROR",u,type(e).__name__,str(e)[:130],flush=True)
if __name__=="__main__":main()
