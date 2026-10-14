#!/usr/bin/env python3
"""Parse only public rendered Popomon / Revu campaign cards.

No hidden endpoints or private detail pages. Unknown '마감 임박' dates are
preserved as unknown and require fresh public-page verification within 48h.
"""
import re
from urllib.parse import urlsplit, parse_qs
from collect import make, plain, media_from_bracketed_title

REGIONS = r"^(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)"
RECRUIT = re.compile(r"신청\s*([\d,]+)\s*/\s*([\d,]+)\s*명?")
COUNTDAYS = re.compile(r"(?<!\d)(\d{1,3})\s*일\s*남음")
CLOSED = re.compile(r"모집\s*마감|신청\s*마감(?!\s*임박)|모집\s*종료|신청\s*종료|오픈\s*예정|종료된\s*캠페인")

def original_image(url, provider):
    if not isinstance(url,str) or not url:
        return None
    if provider == "popomon" and url.startswith("/next/_next/image?"):
        raw=parse_qs(urlsplit(url).query).get("url",[""])[0]
        if urlsplit(raw).hostname=="d17jwiodubhsh2.cloudfront.net" and raw.startswith("https://"):
            return raw
        return None
    if provider == "revu" and url.startswith("https://files.weble.net/campaign/"):
        return url
    return None

def extracted_channels(card, provider):
    names = {
        "블로그":"블로그", "릴스":"인스타그램", "인스타":"인스타그램",
        "인스타그램":"인스타그램", "유튜브":"유튜브", "쇼츠":"쇼츠",
        "클립":"네이버클립", "네이버클립":"네이버클립", "틱톡":"틱톡",
        "스레드":"스레드",
    }
    vals=[]
    if provider=="popomon":
        for label in card.get("badges") or []:
            chan=names.get(str(label).strip())
            if chan and chan not in vals:
                vals.append(chan)
    else:
        icons={
            "naver-color.svg":"블로그", "blog-color.svg":"블로그",
            "instagram-color.svg":"인스타그램", "reels-color.svg":"인스타그램",
            "clip-color.svg":"네이버클립","youtube-color.svg":"유튜브",
            "shorts-color.svg":"쇼츠","tiktok-color.svg":"틱톡",
        }
        for path in card.get("mediaIcons") or []:
            icon=urlsplit(str(path)).path.rsplit("/",1)[-1].lower()
            chan=icons.get(icon)
            if chan and chan not in vals:
                vals.append(chan)
        # Do not infer "blog" from a generic restaurant/product category.
        for ch in media_from_bracketed_title(card.get("title") or ""):
            if ch not in vals: vals.append(ch)
    return vals

def parse_card(card,provider):
    raw_url=str(card.get("url") or "")
    expected = (r"https://popomon\.com/next/campaign/(\d+)" if provider=="popomon"
                else r"https://(?:webview|www)\.revu\.net/campaign/(\d+)")
    m=re.fullmatch(expected,raw_url)
    if not m: return None
    cid=m.group(1)
    title=plain(str(card.get("title") or ""))
    status=plain(str(card.get("status") or ""))
    rawtext=plain(str(card.get("text") or ""))
    benefit=plain(str(card.get("benefit") or ""))
    if len(title)<5 or len(title)>200 or CLOSED.search(status) or CLOSED.search(rawtext):
        return None
    applicants_slots=RECRUIT.search(rawtext)
    if not applicants_slots:
        return None
    applicants=int(applicants_slots.group(1).replace(",",""))
    slots=int(applicants_slots.group(2).replace(",",""))
    if slots<1: return None
    remaining=COUNTDAYS.search(status)
    days=int(remaining.group(1)) if remaining else 0 if "오늘 마감" in status else None
    open_verified=bool(days is None and re.search(r"마감\s*임박|모집\s*중|신청\s*가능",status))
    if days is None and not open_verified: return None
    if re.search(r"상품평\s*전용|구매평\s*전용",title): return None
    media=extracted_channels(card,provider)
    first=re.match(r"^\[([^\]]{2,80})\]",title)
    region=first.group(1) if first and re.match(REGIONS,first.group(1)) else None
    rawctype=card.get("type") or ""
    ctype=next((t for t in ("방문형","배송형","기자단") if t in rawctype),None)
    # No browser link rewrite. For Revu only canonicalize returned site-host
    # variation of the same official campaign ID.
    image=original_image(card.get("image"),provider)
    row=make(provider,cid,title,raw_url,region=region,desc=benefit,benefit=benefit,
             image=image,applicants=applicants,slots=slots,
             days=days,channels=media,ctype=ctype,open_verified=open_verified)
    if row:
        row["media_evidence"]=provider+"_public_card" if media else None
    return row
