#!/usr/bin/env python3
"""Extract only explicitly visible public Cherivu campaign information."""
import re
from urllib.parse import urlsplit
from collect import make,plain

def parse_card(card):
    url=str(card.get("url") or "")
    match=re.fullmatch(r"https://cherivu\.co\.kr/campaigns/(\d+)",url)
    if not match:return None
    title=plain(card.get("title") or "")
    if len(title)<5 or len(title)>240:return None
    status=plain(card.get("status") or "")
    if re.search(r"마감\s*완료|모집\s*종료|신청\s*마감|선정\s*완료",status):return None
    daysmatch=re.fullmatch(r"D\s*-\s*(\d{1,3})",status,re.I)
    days=int(daysmatch.group(1)) if daysmatch else 0 if re.fullmatch(r"D\s*-\s*day",status,re.I) else None
    open_verified=days is None and status=="마감임박"
    if days is None and not open_verified:return None
    photo=str(card.get("image") or "")
    parsed=urlsplit(photo)
    image=photo if parsed.scheme=="https" and parsed.hostname=="d6ctpjljlg7e8.cloudfront.net" else None
    channel_icons={
        "blog.svg":"블로그",
        "instagram.svg":"인스타그램",
        "insta.svg":"인스타그램",
        "reels.svg":"인스타그램",
        "clip.svg":"네이버클립",
        "youtube.svg":"유튜브",
        "shorts.svg":"쇼츠",
    }
    channels=[]
    for path in card.get("icons") or []:
        icon=urlsplit(str(path)).path.rsplit("/",1)[-1].lower()
        ch=channel_icons.get(icon)
        if ch and ch not in channels:channels.append(ch)
    region=None
    bracket=re.match(r"^\[([^\]]{1,75})\]",title)
    if bracket and not re.search(r"기자단|기프트인포|스페셜|플씨드|애플백|MOCO",bracket.group(1),re.I):
        region=bracket.group(1).replace("/"," ")
    ctype="기자단" if "기자단" in title else None
    row=make("cherivu",match.group(1),title,url,region=region,
             desc=card.get("benefit") or "",benefit=card.get("benefit") or "",
             image=image,channels=channels,ctype=ctype,
             days=days,open_verified=open_verified)
    if row and channels:row["media_evidence"]="cherivu_public_media_icon"
    return row
