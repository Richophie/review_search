#!/usr/bin/env python3
"""Inspect official Gangnam Matzip numbered links without crawling pages."""
import re, html
from urllib.parse import urlparse, parse_qs, urljoin
from urllib.request import Request,urlopen
from urllib.robotparser import RobotFileParser
AGENT="ChehumMoaBot/0.1 (+public listing index; respects robots.txt)"
BASE="https://gangnam-review.net"
def get(url):
    with urlopen(Request(url,headers={"User-Agent":AGENT,"Accept-Language":"ko-KR,ko;q=0.9"}),timeout=18) as h:
        return h.read(700_000).decode("utf-8","replace")
def main():
    p=RobotFileParser();p.parse(get(BASE+"/robots.txt").splitlines())
    for rel in ["/cp/", "/cp/?ca=20","/cp/?ca=30","/cp/?ca=40","/cp/?ch=clip"]:
        u=BASE+rel
        if not p.can_fetch(AGENT,u):continue
        body=get(u)
        links=[html.unescape(a) for a in re.findall(r'href\s*=\s*["\x27]([^"\x27]+)',body,re.I)]
        page_urls=[]
        for link in links:
            v=urljoin(u,link)
            if urlparse(v).hostname!="gangnam-review.net" or urlparse(v).path.rstrip("/")!="/cp":continue
            qs=parse_qs(urlparse(v).query)
            if any(k in qs for k in ("page","pg","p")):page_urls.append(v)
        ids=list(dict.fromkeys(re.findall(r'data-product=["\x27](\d+)',body)))
        print("PAGE",u,"verified list IDs",len(ids),"PAGINATION LINKS",list(dict.fromkeys(page_urls))[:30],flush=True)
        for mark in ("pagination","pg_wrap","pg_page","page=", "data-page","load_more","more_view"):
            print("MARKER",mark,body.lower().count(mark.lower()),flush=True)
        for m in re.finditer(r'(?:\bpage=|pg_wrap|pg_page)',body,re.I):
            print("CONTEXT",re.sub(r"\s+"," ",body[max(0,m.start()-140):m.start()+240])[:380],flush=True)
            break
if __name__=="__main__":main()
