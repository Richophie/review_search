#!/usr/bin/env python3
"""Collect public campaign listings for the Review Search snapshot.

Only fetch publicly accessible pages permitted by robots.txt. No logins, no
CAPTCHA bypass, no hidden endpoints. Keep verified attribution and original URLs.
"""
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
TODAY = NOW.date()
OUT = Path("public/data/campaigns.json")
AGENT = "ChehumMoaBot/0.1 (+public listing index; respects robots.txt)"
HOMES = {
    "dinnerqueen": "https://dinnerqueen.net/",
    "mrblog": "https://www.mrblog.net/",
    "modan": "https://modan.kr/",
}
SPLIT = re.compile(r"\s+")

def plain(value):
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    return SPLIT.sub(" ", html.unescape(value)).strip()

def request(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": AGENT,
        "Accept": "text/html",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError("HTTP %s" % resp.status)
        data = resp.read(4_000_000)
        text = data.decode("utf-8", "replace")
        if re.search(r"captcha|cf-challenge|접근이 차단", text[:5000], re.I):
            raise RuntimeError("Anti-bot challenge, skipping")
        return text

ROBOTS = {}
def robots_permit(url):
    host = urllib.parse.urlsplit(url).netloc
    if host not in ROBOTS:
        robots_url = "https://" + host + "/robots.txt"
        try:
            raw = request(robots_url)
            if not re.search(r"(?im)^\s*User-agent\s*:", raw):
                raise RuntimeError("No valid robots.txt directives")
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(raw.splitlines())
            ROBOTS[host] = rp
        except Exception as ex:
            print("No reliable robots decision for", host, str(ex))
            ROBOTS[host] = False
    rule = ROBOTS[host]
    return rule is not False and rule.can_fetch(AGENT, url)

def safe_fetch(url):
    if not robots_permit(url):
        print("Robots policy unavailable or disallows", url)
        return ""
    return request(url)

def one(pattern, value, flags=0):
    m = re.search(pattern, value, flags)
    return m.group(1) if m else None

def number(s):
    return int(s.replace(",", "")) if s is not None else None

def infer_category(text):
    for cat, pat in [
        ("카페", r"카페|커피|베이커리|디저트|케이크"),
        ("숙박·여행", r"호텔|숙박|펜션|리조트|캠핑|여행|풀빌라"),
        ("뷰티", r"네일|속눈썹|피부|미용|헤어|뷰티|마사지"),
        ("반려", r"강아지|애견|고양이|반려|펫"),
        ("키즈", r"키즈|어린이|유아|육아"),
        ("문화", r"공연|전시|뮤지컬|문화|체험관"),
        ("디지털", r"가전|전자제품|이어폰|충전기|스마트"),
        ("맛집", r"맛집|식당|고기|초밥|치킨|식사권|파스타|피자|쌀국수|국밥"),
        ("식품", r"식품|밀키트|건강식품|음료|간편식"),
        ("생활", r"생활|수납|세제|청소|방향제|향초|침구|주방|가구|세탁|리빙|인테리어"),
    ]:
        if re.search(pat, text, re.I):
            return cat
    return "기타"

def sido(region):
    if not region:
        return None
    aliases = {"서울특별시": "서울", "인천광역시": "인천", "부산광역시": "부산",
               "대구광역시": "대구", "광주광역시": "광주", "경기도": "경기",
               "강원도": "강원", "제주특별자치도": "제주"}
    for name in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
                 "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
        if region.startswith(name):
            return name
    found = next((short for long, short in aliases.items() if region.startswith(long)), None)
    if found:
        return found
    city_provinces = {
        "경북": ("포항", "경주", "구미", "안동", "김천", "영주", "상주", "문경", "영천", "경산"),
        "경남": ("창원", "김해", "진주", "양산", "통영", "거제", "밀양", "사천"),
        "경기": ("수원", "성남", "부천", "안양", "안산", "용인", "화성", "평택", "시흥",
                 "군포", "의왕", "과천", "광명", "광주", "하남", "고양", "파주", "김포", "광명", "남양주", "구리"),
        "충북": ("청주", "충주", "제천", "증평", "음성"),
        "충남": ("천안", "아산", "공주", "논산", "당진", "서산", "보령"),
        "전북": ("전주", "군산", "익산", "정읍", "남원"),
        "전남": ("목포", "여수", "순천", "광양", "나주"),
        "강원": ("춘천", "원주", "강릉", "속초", "동해", "삼척"),
        "제주": ("제주시", "서귀포"),
    }
    return next((province for province, cities in city_provinces.items()
                 if any(region.startswith(city) for city in cities)), None)

def make(source, ext_id, title, url, region=None, desc=None, benefit=None,
         image=None, applicants=None, slots=None, days=None, channels=None, ctype=None,
         exact_deadline=None, published_at=None, category_override=None):
    if not title or not url.startswith("https://") or (exact_deadline is None and (days is None or days < 0)):
        return None
    deadline = exact_deadline or (TODAY + timedelta(days=days)).isoformat()
    if deadline < TODAY.isoformat():
        return None
    channels = ["블로그"] if channels is None else channels
    cat = category_override or infer_category(title + " " + (desc or "") + " " + (benefit or ""))
    if not ctype:
        ctype = "기자단" if "기자단" in title else "배송형" if re.search("배송|택배|제품 체험", title) else "방문형" if region and region != "전국" else None
    ratio = applicants / slots if applicants is not None and slots and slots > 0 else None
    remaining = max(slots - applicants, 0) if applicants is not None and slots and slots > 0 else None
    now = NOW.isoformat()
    cleaned_title = plain(title)
    return {
        "id": source + ":" + str(ext_id), "source_id": source,
        "original_url": url, "title": cleaned_title,
        "description": plain(desc) or None, "benefit": plain(benefit) or plain(desc) or None,
        "image_url": image, "country_code": "KR", "region_sido": sido(region),
        "region_text": plain(region) or None, "category": cat, "campaign_type": ctype,
        "channels": channels, "slots": slots, "applicants": applicants,
        "apply_deadline": deadline, "deadline_precision": "exact" if exact_deadline else "days_left",
        "first_seen_at": published_at or now, "last_seen_at": now, "timezone": "Asia/Seoul",
        "competition_ratio": ratio, "remaining_slots": remaining,
        "dedupe_key": re.sub(r"[^\w]", "", (region or "") + cleaned_title).lower(),
        "search_text": " ".join(filter(None, [cleaned_title, plain(desc), plain(benefit), region or "", cat] + channels)).lower(),
    }

def dinnerqueen():
    records = {}
    # Scan fresh pages every run and rotate older pages across twice-daily jobs.
    # All 48 page groups are revisited within three refreshes.
    window = int(NOW.timestamp() // (12*3600)) % 3
    pages = list(range(1,13)) + list(range(13 + window*12,25 + window*12))
    for page in pages:
        url = "https://dinnerqueen.net/taste" + ("?page=" + str(page) if page > 1 else "")
        body = safe_fetch(url)
        if not body:
            break
        cards = body.split('class="qz-dq-card campaign')[1:]
        if not cards:
            break
        added = 0
        for card in cards:
            cid = one(r'href="/taste/(\d+)"', card)
            if not cid or cid in records:
                continue
            title = plain(one(r'title="([^"]+?)\s*신청하기"', card))
            title = re.sub(r"^(\[[^\]]+\]\s*)+", "", title).strip() or title
            region = one(r'title="\[([^\]]+)\]', card)
            if region and re.search(r"릴스|클립|배송|기자단|쇼츠", region):
                region = None
            desc = one(r'color-placeholder[^"]*">([\s\S]*?)</p>', card)
            body_text = plain(card)
            days = one(r"(\d+)\s*일 남음", body_text)
            days = int(days) if days is not None else 0 if re.search("오늘\\s*(?:마감|까지)|D-?day", body_text, re.I) else None
            stats = re.search(r"신청\s*([\d,]+)\s*/\s*([\d,]+)", body_text)
            channels = []
            for marker, channel in [("릴스", "인스타그램"), ("클립", "네이버클립"),
                                    ("유튜브", "유튜브"), ("쇼츠", "쇼츠")]:
                if marker in plain(card[:450]):
                    channels.append(channel)
            item = make("dinnerqueen", cid, title, "https://dinnerqueen.net/taste/" + cid,
                        region, desc, image=one(r'<img[^>]+src="([^"]+)"', card),
                        applicants=number(stats.group(1)) if stats else None,
                        slots=number(stats.group(2)) if stats else None, days=days,
                        channels=channels or ["블로그"])
            if item:
                records[cid] = item
                added += 1
        print("디너의여왕 page", page, "new", added)
        if added == 0:
            break
        time.sleep(1.5)
    return list(records.values())

def mrblog():
    body = safe_fetch("https://www.mrblog.net/")
    out = {}
    expression = r'<a href="https://www\.mrblog\.net/campaigns/(\d+)" class="campaign_item">([\s\S]*?)</a>'
    for cid, part in re.findall(expression, body):
        if cid in out:
            continue
        subject = plain(one(r'<strong class="subject">([\s\S]*?)</strong>', part))
        area = plain(one(r'<span class="area">([\s\S]*?)</span>\s*<strong', part))
        desc = plain(one(r'<p class="desc">([\s\S]*?)</p>', part))
        dday = plain(one(r'<span class="d_day">([\s\S]*?)</span>', part))
        days = one(r"(\d+)\s*일 남음", dday)
        days = int(days) if days is not None else 0 if "오늘" in dday else None
        icon = one(r"sns_icon\s+([a-z]+)", part)
        medium = {"blog": "블로그", "insta": "인스타그램", "instagram": "인스타그램",
                  "reels": "인스타그램", "youtube": "유튜브", "shorts": "쇼츠",
                  "clip": "네이버클립", "tiktok": "틱톡"}.get(icon, "블로그")
        slots = number(one(r"모집\s*([\d,]+)명", part))
        applicants = number(one(r"신청\s*<strong>([\d,]+)명", part))
        item = make("mrblog", cid, subject, "https://www.mrblog.net/campaigns/" + cid,
                    region=area if not re.search("배송|기자단|구매", area) else None,
                    desc=desc, benefit=desc, image=one(r'<img[^>]+src="([^"]+)"', part),
                    applicants=applicants, slots=slots, days=days, channels=[medium],
                    ctype="배송형" if "배송" in area else "기자단" if "기자단" in area else None)
        if item:
            out[cid] = item
    print("미블 public home", len(out))
    return list(out.values())

def modan():
    """Consume the official publicly advertised 50-item RSS feed.

    Only confirm exact recruitment deadlines from the linked public campaign
    detail pages. No login, private API, or challenge bypass.
    """
    url = "https://modan.kr/rss/campaigns.xml"
    rss = safe_fetch(url)
    if not rss:
        raise RuntimeError("Official Modan RSS unavailable or disallowed")
    root = ET.fromstring(rss)
    items = root.findall("./channel/item")
    if not items:
        raise RuntimeError("Official Modan RSS is empty")
    output = {}
    # Preserve new RSS entries and rotate the rest; avoid fetching 50 detail
    # pages on every scheduled execution.
    window = int(NOW.timestamp() // (12*3600)) % 3
    selected = items[:10] + items[10 + 14*window : 10 + 14*(window+1)]
    for idx, item in enumerate(selected):
        link = (item.findtext("link") or "").strip()
        if not re.fullmatch(r"https://modan\.kr/campaigns/\d+", link):
            continue
        cid = link.rsplit("/",1)[-1]
        title = (item.findtext("title") or "").strip()
        category = (item.findtext("category") or "").strip()
        region = (item.findtext("{http://purl.org/dc/elements/1.1/}creator") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        published_at = None
        if pub:
            try:
                published_at = parsedate_to_datetime(pub).isoformat()
            except (ValueError, TypeError):
                pass
        try:
            detail = safe_fetch(link)
            if not detail:
                continue
            matches = re.findall(
                r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
                detail, re.I,
            )
            exact_deadline = None
            offer = None
            image = None
            for raw_script in matches:
                try:
                    ld = json.loads(html.unescape(raw_script))
                except (ValueError, TypeError):
                    continue
                nodes = ld if isinstance(ld,list) else [ld]
                for node in nodes:
                    if not isinstance(node,dict):
                        continue
                    if node.get("@type") != "Event":
                        continue
                    ending = node.get("endDate")
                    if ending:
                        try:
                            instant = datetime.fromisoformat(ending.replace("Z","+00:00"))
                            exact_deadline = instant.astimezone(KST).date().isoformat()
                        except (ValueError, AttributeError):
                            pass
                    offers = node.get("offers") or {}
                    if isinstance(offers,dict):
                        offer = offers.get("name")
                    pic = node.get("image")
                    if isinstance(pic, str) and pic.startswith("https://"):
                        image = pic
                    elif isinstance(pic,list) and pic:
                        if isinstance(pic[0],str) and pic[0].startswith("https://"):
                            image = pic[0]
            # Never assign a fictional deadline when the original gives none.
            if not exact_deadline:
                continue
            # The RSS exposes publisher dates; do not treat discovery time as
            # publication time for the "new" tab.
            title_clean = re.sub(r"^(\[[^\]]+\]\s*)+", "", title).strip() or title
            campaign_type = (
                "기자단" if "기자단" in title else
                "배송형" if "배송" in title or category in ("제품","배송") else
                "방문형" if region and region != "전국" else None
            )
            c = make(
                "modan", cid, title_clean, link, region=region,
                desc=description, benefit=offer or description, image=image,
                applicants=None, slots=None, exact_deadline=exact_deadline,
                published_at=published_at, category_override=category or None,
                channels=[], ctype=campaign_type,
            )
            if c:
                output[cid] = c
        except Exception as exc:
            print("모두의체험단 detail skipped",cid,str(exc)[:140])
        # Be considerate to the source, and run well below rate limits.
        if idx < len(selected)-1:
            time.sleep(0.55)
    print("모두의체험단 RSS confirmed",len(output),"of",len(items))
    return list(output.values())

def modootogether():
    """Index the public category LIST pages only; no campaign detail pages."""
    base = "https://www.modootogether.com/"
    pages = [
        "", "campaign_list.php",
        "campaign_list.php?category_id=047A",  # 맛집
        "campaign_list.php?category_id=051A",  # 뷰티
        "campaign_list.php?category_id=001A",  # 지역
        "campaign_list.php?category_id=002A",  # 제품
        "campaign_list.php?category_id=003A",  # 서비스
    ]
    out = {}
    for rel in pages:
        url = urllib.parse.urljoin(base, rel)
        try:
            body = safe_fetch(url)
            if not body:
                continue
        except Exception as exc:
            print("모두모여 public listing failure", rel, str(exc)[:130])
            continue
        # Only match <li> cards with a direct campaign link, never nav items.
        cards = re.findall(r'<li>\s*<div class="box">([\s\S]*?)</li>', body, re.I)
        added = 0
        for card in cards:
            cid = one(r'campaign\.php\?cp_id=(\d+)', card)
            if not cid or cid in out:
                continue
            title = plain(one(r'<span class="it_name">([\s\S]*?)</span>', card))
            if not title:
                continue
            dday_tag = plain(one(r'<span[^>]*class="[^"]*\bdday\b[^"]*"[^>]*>([\s\S]*?)</span>', card))
            if "모집마감" in dday_tag:
                continue
            days = one(r'D-?\s*[Dd]ay\s*(\d+)', dday_tag, re.I)
            if days is None:
                continue
            applicants = number(one(r'<b[^>]*>([\d,]+)</b>\s*명\s*신청',card))
            slots = number(one(r'<b[^>]*>([\d,]+)</b>\s*명\s*모집중',card))
            # Both quantities must be present for reliable competition calculations.
            badges = plain(one(r'<div class="top_info">([\s\S]*?)</div>', card))
            channels = [
                channel for keyword, channel in [
                    ("블로그","블로그"),("인스타그램","인스타그램"),
                    ("유튜브","유튜브"),("클립","네이버클립"),
                    ("릴스","인스타그램"),("틱톡","틱톡"),
                ] if keyword in badges
            ]
            channels = list(dict.fromkeys(channels))
            # The shop-only medium is not among the requested review media.
            if not channels and "쇼핑몰" in badges:
                continue
            desc = plain(one(r'<span class="it_description">([\s\S]*?)</span>', card))
            point = plain(one(r'<span class="txt_num point_color4">(\+\s*[\d,]+P)</span>', card))
            benefit = desc + ((" · " if desc else "") + point if point else "")
            kind = plain(one(r'<div class="option2">([\s\S]*?)</div>', card))
            ctype = next((k for k in ("방문형","배송형","기자단") if k in kind), None)
            prefix = one(r'^\[([^\]]+)\]', title)
            region = None
            if prefix and re.match(r'^(서울|경기|인천|부산|대전|대구|광주|울산|세종|충북|충남|전북|전남|경북|경남|강원|제주)',prefix):
                region = prefix.replace("/"," ")
            image = one(r'<img[^>]+src="([^"]+)"', card)
            image = urllib.parse.urljoin(base,html.unescape(image)) if image else None
            item = make(
                "modootogether",cid,title,
                base + "campaign.php?cp_id=" + cid,
                region=region, desc=desc, benefit=benefit,
                image=image, applicants=applicants, slots=slots,
                days=int(days), channels=channels, ctype=ctype
            )
            if item:
                out[cid]=item
                added+=1
        print("모두모여 public listing",rel or "/",len(cards),"cards",added,"new")
        time.sleep(1.2)
    return list(out.values())

def fourblog():
    """Collect 4blog's public, robot-permitted all-campaign listing."""
    base="https://4blog.net"
    body=safe_fetch(base + "/list/all")
    if not body:
        raise RuntimeError("4blog public all-list unavailable")
    cards=re.findall(
        r'<a\s+class="nounderline"\s+href="/campaign/(\d+)/">([\s\S]*?)</a>',
        body, re.I
    )
    output={}
    for cid, fragment in cards:
        title=plain(one(r'<span class="camp-name">([\s\S]*?)</span>',fragment))
        if not title:
            continue
        region=one(r'^\[([^\]]+)\]',title)
        if region:
            region=region.replace("/"," ")
        benefit=plain(one(r'<div class="emphasize">([\s\S]*?)</div>',fragment))
        recruits=number(one(r'<span class="remainCnt">모집\s*([\d,]+)명</span>',fragment))
        ctype=plain(one(r'<span[^>]*class="[^"]*campaign-type-badge[^"]*"[^>]*>([\s\S]*?)</span>',fragment))
        if ctype not in ("방문형","배송형","기자단","구매평"):
            ctype=None
        src=one(r'<img[^>]+src="(https://[^"]+)"',fragment)
        days_raw=one(r'<span class="fontcolor">D-(\d+)</span>',fragment)
        days=int(days_raw) if days_raw is not None else 0 if re.search(r'D-Day',fragment,re.I) else None
        if days is None:
            continue
        # Optional: verify the published recruitment END against the live D-day.
        exact_deadline=None
        m=re.search(r'모집\s+\d{1,2}\.\d{1,2}\s*~\s*(\d{1,2})\.(\d{1,2})',plain(fragment))
        if m:
            predicted=TODAY+timedelta(days=days)
            try:
                candidate=predicted.replace(month=int(m.group(1)),day=int(m.group(2)))
                if abs((candidate-predicted).days) <= 1:
                    exact_deadline=candidate.isoformat()
            except ValueError:
                pass
        badges=re.findall(r'<span[^>]*class="[^"]*label[^"]*"[^>]*>([\s\S]*?)</span>',fragment)
        badges=[plain(b) for b in badges]
        channels=[]
        for label in badges:
            if label in ("블로그","blog"):
                channels.append("블로그")
            elif label in ("인스타","인스타그램","릴스"):
                channels.append("인스타그램")
            elif label in ("네이버클립","클립"):
                channels.append("네이버클립")
            elif label in ("유튜브",):
                channels.append("유튜브")
            elif label in ("쇼츠","숏츠"):
                channels.append("쇼츠")
            elif label=="틱톡":
                channels.append("틱톡")
            elif label=="스레드":
                channels.append("스레드")
        channels=list(dict.fromkeys(channels))
        item=make(
            "fourblog",cid,title,base+"/campaign/"+cid+"/",
            region=region,desc=benefit,benefit=benefit,image=src,
            applicants=None,slots=recruits,days=days,exact_deadline=exact_deadline,
            channels=channels,ctype=ctype
        )
        if item:
            output[cid]=item
    print("포블로그 public all",len(cards),"cards",len(output),"verified",flush=True)
    return list(output.values())


def assaview():
    """Index public Assaview campaign listing cards with exact stated deadline.

    Do not index FCFS/recurring cards lacking a fixed application deadline,
    and do not follow login- or account-restricted requests.
    """
    base="https://www.assaview.co.kr/"
    paths=[
        "campaign_list.php",
        "campaign_list.php?type=area",
        "campaign_list.php?type=product",
        "campaign_list.php?type=reporter",
        "campaign_list.php?type=assaview",
        "campaign_list.php?type=custom",
    ]
    out={}
    for path in paths:
        url=urllib.parse.urljoin(base,path)
        try:
            body=safe_fetch(url)
            if not body:
                continue
        except Exception as exc:
            print("아싸뷰 listing skipped",path,repr(exc)[:140],flush=True)
            continue
        cards=re.findall(
            r'<a\s+href="campaign\.php\?cp_id=(\d+)"[^>]*>([\s\S]*?)</a>',
            body,re.I
        )
        added=0
        for cid, fragment in cards:
            if cid in out:
                continue
            # Public card lists the actual application deadline, not
            # selection/review completion date.
            date=re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})\s+23:59:59',fragment)
            if not date:
                continue
            try:
                deadline=datetime(int(date.group(1)),int(date.group(2)),
                                  int(date.group(3)),tzinfo=KST).date().isoformat()
            except ValueError:
                continue
            rawtitle=one(r'<div class="subject">([\s\S]*?)</div>',fragment)
            title=plain(rawtitle)
            if not title:
                continue
            ctype=plain(one(r'<span class="rs_cp_type_chip">([\s\S]*?)</span>',fragment))
            ctype={"구매형":"구매평","지역형":"방문형"}.get(ctype,ctype)
            if ctype not in ("방문형","배송형","기자단","구매평"):
                ctype=None
            desc=plain(one(r'<span class="opt_name">([\s\S]*?)</span>',fragment))
            reg=one(r'^\[([^\]]+)\]',title)
            if reg and not re.search(r'서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주',reg):
                reg=None
            stat=re.search(r'신청\s*</span>\s*<b>([\d,]+)</b>\s*<span>/</span>\s*<span>([\d,]+)명',fragment)
            applicant=number(stat.group(1)) if stat else None
            slots=number(stat.group(2)) if stat else None
            point=one(r'\+?\s*([\d,]+)\s*P\b',plain(fragment))
            benefit=desc
            if point:
                benefit=(desc+" · " if desc else "")+"+"+point+"P"
            img=one(r'<img\s+src="([^"]+)"',fragment)
            img=urllib.parse.urljoin(base,html.unescape(img)) if img else None
            media=plain(fragment)
            channels=[]
            for marker,ch in (("블로그","블로그"),("인스타그램","인스타그램"),
                ("유튜브","유튜브"),("네이버클립","네이버클립"),
                ("클립","네이버클립"),("릴스","인스타그램"),
                ("쇼츠","쇼츠"),("틱톡","틱톡"),("스레드","스레드")):
                if marker in media and ch not in channels:
                    channels.append(ch)
            campaign=make(
                "assaview",cid,title,
                urllib.parse.urljoin(base,"campaign.php?cp_id="+cid),
                region=reg,desc=desc,benefit=benefit,image=img,
                slots=slots,applicants=applicant,channels=channels,
                exact_deadline=deadline,ctype=ctype
            )
            if campaign:
                out[cid]=campaign
                added+=1
        print("아싸뷰",path,len(cards),"cards",added,"new",flush=True)
        time.sleep(1.2)
    print("아싸뷰 confirmed",len(out),"unique exact-deadline campaigns",flush=True)
    return list(out.values())


def ringble():
    """Index homepage-listed campaign cards only.

    Ringble's robots.txt disallows /detail.php: never visit its detail
    pages. Public homepage already exposes a campaign's title, applicants,
    slots, relative application deadline and original link.
    """
    base="https://www.ringble.co.kr/"
    html_page=safe_fetch(base)
    if not html_page:
        raise RuntimeError("Ringble public homepage blocked or not permitted")
    out={}
    fragments=html_page.split("store_list_wrap")[1:]
    for fragment in fragments:
        # A card terminates before the next store_list_wrap marker.
        cid=one(r"detail\.php\?number=(\d+)&category=",fragment)
        if not cid or cid in out:
            continue
        title=plain(one(r'<a\s+href=[\'"]detail\.php\?number=\d+&category=[\'"]\s+class="list_title"\s+style="font-size:14px;">([\s\S]*?)</a>',fragment))
        if not title:
            # A source update must not result in unlabelled results.
            continue
        days=one(r'class="list_title"[^>]*>\s*(\d+)\s*일\s*남음',fragment)
        if days is None:
            continue
        stats=re.search(r'신청\s*([\d,]+)\s*</font>\s*/\s*<font[^>]*>\s*모집\s*([\d,]+)',fragment)
        applicants=number(stats.group(1)) if stats else None
        slots=number(stats.group(2)) if stats else None
        description=plain(one(r'<td\s+style="padding-top:5px[^"]*">([\s\S]*?)</td>',fragment))
        img=one(r'<img\s+src="([^"]+)"',fragment)
        img=urllib.parse.urljoin(base,img) if img else None
        channel=one(r'(블로그|인스타그램|인스타|유튜브|릴스|틱톡|클립|쇼츠)\s*</div>',fragment)
        channel={"인스타":"인스타그램","릴스":"인스타그램","클립":"네이버클립"}.get(channel,channel) if channel else None
        region=one(r'^\[([^\]]+)\]',title)
        if region and not sido(region):
            region=None
        item=make(
            "ringble",cid,title,
            base+"detail.php?number="+cid+"&category=",
            region=region,desc=description,
            benefit=description,image=img,
            applicants=applicants,slots=slots,days=int(days),
            channels=[channel] if channel else [],
            ctype="배송형" if "배송" in fragment[:950] else None
        )
        if item:
            out[cid]=item
    print("링블 public homepage",len(fragments),"segments",len(out),"campaigns",flush=True)
    return list(out.values())


def cometoplay():
    """Read only ComeToPlay's public homepage campaign summaries."""
    base="https://www.cometoplay.kr/"
    body=safe_fetch(base)
    if not body:
        raise RuntimeError("ComeToPlay public homepage unavailable")
    out={}
    fragments=re.findall(r'<li>\s*<div class="thumb">([\s\S]*?)</li>',body,re.I)
    for f in fragments:
        cid=one(r'item\.php\?it_id=(\d+)',f)
        if not cid or cid in out:
            continue
        title=plain(one(r'<span class="it_name">([\s\S]*?)</span>',f))
        if not title:
            continue
        desc=plain(one(r'<span class="it_description">([\s\S]*?)</span>',f))
        days=one(r'D-?day\s*(\d+)',f,re.I)
        if days is None:
            continue
        stats=re.search(r'신청\s*<b[^>]*>([\d,]+)</b>\s*명\s*/\s*모집\s*<b[^>]*>([\d,]+)</b>\s*명',f,re.I)
        applicants=number(stats.group(1)) if stats else None
        slots=number(stats.group(2)) if stats else None
        region=one(r'^\[([^\]]+)\]',title)
        if region and not sido(region):
            region=None
        image=one(r'<img\s+src="([^"]+)"',f)
        image=urllib.parse.urljoin(base,html.unescape(image)) if image else None
        channels=[]
        for media,normalized in (
            ("blog","블로그"),("instagram","인스타그램"),
            ("insta","인스타그램"),("youtube","유튜브"),
            ("reels","인스타그램"),("clip","네이버클립"),
            ("shorts","쇼츠"),("tiktok","틱톡")):
            if re.search(r'<i\s+class="[^"]*\b'+media+r'\b',f,re.I) and normalized not in channels:
                channels.append(normalized)
        item=make(
            "cometoplay",cid,title,
            base+"item.php?it_id="+cid+"&category_id=",
            region=region,desc=desc,benefit=desc,image=image,
            applicants=applicants,slots=slots,days=int(days),
            channels=channels,ctype="기자단" if "기자단" in title else None
        )
        if item:
            out[cid]=item
    print("놀러와체험단 public homepage",len(fragments),"cards",len(out),"campaigns",flush=True)
    return list(out.values())

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(OUT.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        current = []
    stored = {item["id"]: item for item in current if isinstance(item, dict) and "id" in item}
    found = 0
    for name, collect in [("dinnerqueen", dinnerqueen), ("mrblog", mrblog), ("modan", modan), ("modootogether", modootogether), ("fourblog", fourblog), ("assaview", assaview), ("ringble", ringble), ("cometoplay", cometoplay)]:
        try:
            items = collect()
            for item in items:
                previous = stored.get(item["id"])
                if previous:
                    item["first_seen_at"] = previous.get("first_seen_at", item["first_seen_at"])
                stored[item["id"]] = item
            found += len(items)
        except Exception as ex:
            print("Collection failure, existing data preserved:", name, repr(ex))
    if found == 0:
        print("No verified new listings. Existing snapshot remains unchanged.")
        return
    cutoff = NOW - timedelta(days=21)
    rows = [x for x in stored.values() if x.get("apply_deadline") and
            x["apply_deadline"] >= TODAY.isoformat() and
            datetime.fromisoformat(x["last_seen_at"]) >= cutoff]
    rows.sort(key=lambda x: (x["source_id"], x["id"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print("Snapshot saved: %s unique live campaigns (%s observed this run)" % (len(rows), found))

if __name__ == "__main__":
    main()
