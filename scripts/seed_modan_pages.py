#!/usr/bin/env python3
"""Verify additional Modan campaigns from robots-permitted official list pages.

The official RSS covers 50 campaigns; the publicly linked campaign page
provides paginated ItemList schema.org entries. Only original detail-page
Event endDate values are accepted as application deadlines, with a timezone.
No login, challenge bypass, speculative campaign IDs, or closed campaigns.
"""
import html
import json
import re
import time
import urllib.parse
from datetime import datetime,timedelta
from collect import KST,NOW,TODAY,OUT,make,plain,safe_fetch

BASE="https://modan.kr"
def itemlist_candidates(doc):
    ids=[]
    for raw in re.findall(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
        doc,re.I,
    ):
        try:ld=json.loads(html.unescape(raw))
        except (ValueError,TypeError):continue
        for obj in (ld if isinstance(ld,list) else [ld]):
            if not isinstance(obj,dict) or obj.get("@type")!="ItemList":continue
            for item in obj.get("itemListElement") or []:
                if not isinstance(item,dict):continue
                u=item.get("url") or ""
                m=re.fullmatch(r"https://modan\.kr/campaigns/(\d+)",str(u))
                if m:ids.append((m.group(1),plain(str(item.get("name") or ""))))
    return list(dict((cid,title) for cid,title in ids).items())

def verified_detail(cid,fallback_title):
    url=BASE+"/campaigns/"+cid
    raw=safe_fetch(url)
    if not raw:return None
    scripts=re.findall(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
        raw,re.I
    )
    events=[]
    for script in scripts:
        try:obj=json.loads(html.unescape(script))
        except (TypeError,ValueError):continue
        for node in (obj if isinstance(obj,list) else [obj]):
            if isinstance(node,dict) and node.get("@type")=="Event":events.append(node)
    for event in events:
        end=event.get("endDate")
        if not isinstance(end,str):continue
        try:
            at=datetime.fromisoformat(end.replace("Z","+00:00"))
            if at.tzinfo is None:continue
            deadline=at.astimezone(KST).date().isoformat()
        except ValueError:continue
        if deadline<TODAY.isoformat():continue
        # Event title may differ from original listing; preserve listing
        # label as canonical because it came from an official ItemList.
        title=fallback_title or plain(event.get("name") or "")
        if len(title)<5 or len(title)>240:continue
        reg=re.match(r"^\[([^\]]{2,65})\]",title)
        region=reg.group(1) if reg and re.match(
            r"(서울|인천|경기|부산|대구|대전|광주|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)",reg.group(1)) else None
        offer=event.get("offers") or {}
        benefit=plain(offer.get("name") or "") if isinstance(offer,dict) else ""
        photo=event.get("image")
        photo=photo if isinstance(photo,str) else photo[0] if isinstance(photo,list) and photo and isinstance(photo[0],str) else None
        image=photo if photo and photo.startswith("https://") else None
        channels=[]
        for token,medium in (("인스타그램","인스타그램"),("블로그","블로그"),("유튜브","유튜브"),("클립","네이버클립")):
            if token in title and medium not in channels:channels.append(medium)
        kind="기자단" if "기자단" in title else "배송형" if "배송" in title or "제품 체험" in title else "방문형" if region else None
        return make(
            "modan",cid,title,url,region=region,benefit=benefit,
            image=image,channels=channels,ctype=kind,exact_deadline=deadline
        )
    return None

def main():
    existing=json.loads(OUT.read_text(encoding="utf-8"))
    byid={c["id"]:c for c in existing}
    # Always revisit the newest four pages. Rotate a bounded older page.
    rotation=int(NOW.timestamp()//(12*3600))%8
    pages=[1,2,3,4,5+rotation]
    candidates={}
    for page in pages:
        url=BASE+"/campaigns?page="+str(page)
        try:
            doc=safe_fetch(url)
            if not doc:continue
            cards=itemlist_candidates(doc)
            for cid,title in cards:
                candidates[cid]=title
            print("Modan official page",page,"schema campaign cards",len(cards),flush=True)
        except Exception as e:print("Modan public page error",page,type(e).__name__,str(e)[:110],flush=True)
        time.sleep(0.6)
    if not candidates:
        raise SystemExit("No permitted public Modan ItemList cards; refusing changes.")
    checked=0
    verified=0
    fresh=0
    for cid,title in candidates.items():
        prev=byid.get("modan:"+cid)
        if prev:
            try:
                seen=datetime.fromisoformat(prev["last_seen_at"].replace("Z","+00:00"))
                if seen.tzinfo and seen>=NOW-timedelta(hours=20):
                    continue
            except (ValueError,TypeError,KeyError):pass
        if checked>=100:break
        checked+=1
        try:
            row=verified_detail(cid,title)
            if not row:continue
            if prev:
                row["first_seen_at"]=prev.get("first_seen_at",row["first_seen_at"])
                if not row.get("image_url") and prev.get("image_url"):row["image_url"]=prev["image_url"]
                if not row.get("published_at") and prev.get("published_at"):row["published_at"]=prev["published_at"]
            else:fresh+=1
            byid[row["id"]]=row
            verified+=1
        except Exception as e:
            print("Modan detail skipped",cid,type(e).__name__,str(e)[:110],flush=True)
        time.sleep(0.35)
    if not verified and fresh==0:
        print("No newly verified Modan rows; preserving existing snapshot",flush=True)
        return
    rows=sorted(byid.values(),key=lambda r:(r["source_id"],r["id"]))
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=0)+"\n",encoding="utf-8")
    print("Modan verified detail",verified,"new",fresh,"listed",len(candidates),"snapshot",len(rows),flush=True)
if __name__=="__main__":main()
