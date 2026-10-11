#!/usr/bin/env python3
"""Bounded robots-aware diagnostics for publicly listed campaigns."""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

AGENT = "ChehumMoaBot/0.1 (+public listing index; respects robots.txt)"
BASE = "https://www.real-review.kr"
URLS = [BASE + "/", BASE + "/explore/?sort=started", BASE + "/explore/?page=2"]
class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out=[]
    def handle_data(self, t):
        v=" ".join(t.split())
        if v:self.out.append(v)

def get(url):
    with urlopen(Request(url,headers={"User-Agent":AGENT,"Accept-Language":"ko-KR,ko;q=0.9"}),timeout=16) as h:
        return h.read(1_100_000).decode("utf-8","replace")
def main():
    raw=get(BASE+"/robots.txt")
    if not re.search(r"(?im)^\s*user-agent\s*:",raw):
        raise SystemExit("No unambiguous robots policy")
    rp=RobotFileParser();rp.parse(raw.splitlines())
    urls=[]
    for listing in URLS:
        if not rp.can_fetch(AGENT, listing):
            print("SKIP robots",listing,flush=True);continue
        body=get(listing)
        cards=re.findall(r'<div class="l-project-ls__li"[\s\S]*?(?=<div class="l-project-ls__li"|</section>|<div class="c-pagination")',body,re.I)
        ids=list(dict.fromkeys(re.findall(r'data-project-id="(\d+)"',body)))
        links=list(dict.fromkeys(re.findall(r'href="(https://www\.real-review\.kr/project/[A-Za-z0-9_-]+/)"',body)))
        print("LIST",listing,"bytes",len(body),"card ID count",len(ids),"unique links",len(links),"cards",len(cards),flush=True)
        if cards:
            print("FIRST CARD",re.sub(r"\s+"," ",cards[0][:5300])[:5200],flush=True)
            if len(cards)>1: print("SECOND CARD",re.sub(r"\s+"," ",cards[1][:3100]),flush=True)
        urls.extend(links[:2])
    for u in list(dict.fromkeys(urls))[:4]:
        if not rp.can_fetch(AGENT,u):
            print("DETAIL blocked by robots",u,flush=True);continue
        try:
            h=get(u);v=Visible();v.feed(h)
            t=" ".join(v.out)
            terms=("모집 기간","모집기간","모집 마감","모집마감","종료일","모집중","신청 인원","모집 인원","모집인원","캠페인 일정")
            sections={}
            for term in terms:
                p=t.find(term)
                if p>=0: sections[term]=t[max(0,p-90):p+420]
            dates=re.findall(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}",t)
            print("DETAIL",u,"bytes",len(h),"DATES",dates[:18],"DETAIL_SECTIONS",sections,flush=True)
        except Exception as ex: print("DETAIL ERROR",u,type(ex).__name__,str(ex)[:120],flush=True)
if __name__=="__main__":
    main()
