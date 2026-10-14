#!/usr/bin/env python3
"""Interpret only verifiable public Ohmyblog / Chvu campaign card fields."""
import re
from urllib.parse import urlsplit
from collect import make,plain

def media_labels(card,source):
    result=[]
    mapping=({"NAVER_BLOG_POST":"블로그","INSTAGRAM_REELS":"인스타그램",
              "INSTAGRAM_POST":"인스타그램","NAVER_CLIP":"네이버클립",
              "YOUTUBE_SHORTS":"쇼츠","YOUTUBE":"유튜브"}
             if source=="ohmyblog" else
             {"blog":"블로그","insta":"인스타그램","instagram":"인스타그램",
              "youtube":"유튜브","shorts":"쇼츠","reels":"인스타그램",
              "clip":"네이버클립","tiktok":"틱톡"})
    for raw in card.get("media") or []:
        value=mapping.get(str(raw).strip().upper() if source=="ohmyblog" else str(raw).strip().lower())
        if value and value not in result:result.append(value)
    return result

def safe_image(value,source):
    if not isinstance(value,str) or not value:return None
    if source=="ohmyblog" and value.startswith("/UPLOAD/CAMPAIGNS/"):
        return "https://www.ohmyblog.co.kr"+value
    p=urlsplit(value)
    permitted=(("www.ohmyblog.co.kr","ohmyblog.co.kr") if source=="ohmyblog"
               else ("chvu.co.kr","api.media.smiledragon.co.kr"))
    return value if p.scheme=="https" and p.hostname in permitted else None

def parse_card(card,source):
    u=str(card.get("url") or "")
    pattern=(r"https://www\.ohmyblog\.co\.kr/(?:user/)?productDetail\.apsl\?app_seq=(\d+)"
             if source=="ohmyblog" else r"https://chvu\.co\.kr/campaign/(\d+)")
    m=re.fullmatch(pattern,u)
    if not m:return None
    title=plain(card.get("title") or "")
    benefit=plain(card.get("benefit") or "")
    if len(title)<5 or len(title)>240:return None
    if source=="ohmyblog" and benefit and benefit not in title and "오디데이" in title:
        title=title+" — "+benefit[:80]
    status=plain(card.get("status") or "")
    if re.search(r"모집\s*마감|신청\s*마감(?!\s*임박)|마감\s*완료|종료|선정\s*완료",status):
        return None
    if source=="ohmyblog":
        daysmatch=re.search(r"(?<!\d)(\d{1,3})\s*일\s*남음",status)
        days=int(daysmatch.group(1)) if daysmatch else 0 if "오늘 마감" in status else None
    else:
        daysmatch=re.search(r"D\s*[-–]\s*(\d{1,3})(?!\d)",status,re.I)
        days=int(daysmatch.group(1)) if daysmatch else 0 if re.search(r"D\s*[-–]\s*day",status,re.I) else None
    open_verified=bool(days is None and "상시모집" in status)
    if days is None and not open_verified:return None
    count=str(card.get("count") or "")
    if source=="chvu":
        counts=re.search(r"신청\s*([\d,]+)\s*/\s*([\d,]+)",count)
        if not counts:return None
        applicants=int(counts.group(1).replace(",",""))
        slots=int(counts.group(2).replace(",",""))
    else:
        amounts=re.search(r"([\d,]+)\s*명\s*모집",str(card.get("slots") or ""))
        if not amounts:return None
        slots=int(amounts.group(1).replace(",",""))
        applicants=None
    if slots<1:return None
    cardtype=str(card.get("type") or "")
    kind=next((x for x in ("방문형","배송형","기자단","구매형") if x in cardtype),None)
    if source=="ohmyblog":
        if "기자단" in cardtype:kind="기자단"
        elif "제품체험" in cardtype:kind="배송형"
        elif "방문체험" in cardtype:kind="방문형"
    elif "기자단" in title:kind="기자단"
    prefix=re.match(r"^\[([^\]]{1,65})\]",title)
    region=prefix.group(1).replace("/"," ") if prefix and prefix.group(1)!="기자단" and "제품" not in prefix.group(1) else None
    media=media_labels(card,source)
    row=make(source,m.group(1),title,u,region=region,desc=benefit,benefit=benefit,
             image=safe_image(card.get("image"),source),applicants=applicants,slots=slots,
             days=days,channels=media,ctype=kind,open_verified=open_verified)
    if row and media:row["media_evidence"]=source+":public_card_badge"
    return row
