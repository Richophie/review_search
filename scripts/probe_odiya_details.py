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
            for mark in ("리뷰어신청", "신청&nbsp;", "모집인원", "신청\u00a0", "리뷰어발표"):
                hit=body.find(mark)
                if hit>=0:
                    print("CARD_CONTEXT",mark,re.sub(r"\\s+"," ",body[max(0,hit-1300):hit+2700])[:3800],flush=True)
            for keyword in ("리뷰어신청","신청","모집","detail.php","D-"):
                print("COUNT",keyword,body.count(keyword),flush=True)
        except Exception as e:print("ERROR",u,type(e).__name__,str(e)[:130],flush=True)
if __name__=="__main__":main()
