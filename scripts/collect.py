#!/usr/bin/env python3
"""Collect public campaign listings for the Review Search snapshot.

Only fetch publicly accessible pages permitted by robots.txt. No logins, no
CAPTCHA bypass, no hidden endpoints. Keep verified attribution and original URLs.
"""
import html
import json
import os
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
        if re.search(r"cf-challenge|<title>\s*(?:Just a moment|Access denied)|verify you are human|captcha challenge|접근이 차단", text[:8000], re.I):
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
         exact_deadline=None, published_at=None, category_override=None, open_verified=False):
    if not title or not url.startswith("https://"):
        return None
    if days is not None and days < 0:
        return None
    if exact_deadline is None and days is None and not open_verified:
        return None
    deadline = exact_deadline or ((TODAY + timedelta(days=days)).isoformat() if days is not None else None)
    if deadline is not None and deadline < TODAY.isoformat():
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
        "apply_deadline": deadline, "deadline_precision": "exact" if exact_deadline else "days_left" if days is not None else "unknown",
        "open_verified": bool(open_verified and deadline is None),
        "first_seen_at": now, "published_at": published_at, "last_seen_at": now, "timezone": "Asia/Seoul",
        "competition_ratio": ratio, "remaining_slots": remaining,
        "dedupe_key": re.sub(r"[^\w]", "", (region or "") + cleaned_title).lower(),
        "search_text": " ".join(filter(None, [cleaned_title, plain(desc), plain(benefit), region or "", cat] + channels)).lower(),
    }

def dinnerqueen():
    records = {}
    # Public page 250 has live listing cards, while page 300 does not.
    # A one-time, rate-limited backfill can select an explicit page interval.
    # Regular refresh revisits 12 newest pages plus 48 older pages per run.
    explicit_start = os.environ.get("DQ_PAGE_START")
    explicit_end = os.environ.get("DQ_PAGE_END")
    if explicit_start is not None and explicit_end is not None:
        start = max(1, int(explicit_start))
        end = min(299, int(explicit_end))
        pages = range(start, end + 1)
    else:
        window = (int(NOW.timestamp() // (12*3600)) + 1) % 6
        start = 13 + window * 48
        pages = list(range(1, 13)) + list(range(start, min(start + 48, 300)))
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
            raw_title = plain(one(r'title="([^"]+?)\s*신청하기"', card))
            title = re.sub(r"^(\[[^\]]+\]\s*)+", "", raw_title).strip() or raw_title
            region = one(r'title="\[([^\]]+)\]', card)
            if region and re.search(r"릴스|클립|배송|기자단|쇼츠", region):
                region = None
            desc = one(r'color-placeholder[^"]*">([\s\S]*?)</p>', card)
            body_text = plain(card)
            days = one(r"(\d+)\s*일 남음", body_text)
            days = int(days) if days is not None else 0 if re.search("오늘\\s*(?:마감|까지)|D-?day", body_text, re.I) else None
            stats = re.search(r"신청\s*([\d,]+)\s*/\s*([\d,]+)", body_text)
            # Explicit provider media markers only. Never silently label a clip/reel as blog.
            # The original listing contains [클립]/[릴스] markers in the title.
            # Use the original listing title before removing [클립]/[릴스] prefixes.
            # Reading whole card text can pick up unrelated UI labels.
            media_text = raw_title
            channels = []
            if re.search(r"\[클립\]|클립형|네이버\s*클립", media_text):
                channels.append("네이버클립")
            if re.search(r"\[릴스\]|릴스형|인스타\s*릴스", media_text):
                channels.append("인스타그램")
            if re.search(r"\[쇼츠\]|유튜브\s*쇼츠", media_text):
                channels.append("쇼츠")
            if re.search(r"\[유튜브\]|유튜브\s*영상", media_text):
                channels.append("유튜브")
            if re.search(r"\[블로그\]|블로그형|블로그\s*포스팅", media_text):
                channels.append("블로그")
            item = make("dinnerqueen", cid, title, "https://dinnerqueen.net/taste/" + cid,
                        region, desc, image=one(r'<img[^>]+src="([^"]+)"', card),
                        applicants=number(stats.group(1)) if stats else None,
                        slots=number(stats.group(2)) if stats else None, days=days,
                        channels=channels)
            if item:
                records[cid] = item
                added += 1
        print("디너의여왕 page", page, "new", added)
        # Repeated IDs on a page do not mean later pages are empty.
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
        # Never silently assume Blog when the medium badge is missing.
        # Keep each original campaign ID so different media stay distinct.
        medium = {"blog": "블로그", "insta": "인스타그램", "instagram": "인스타그램",
                  "reels": "인스타그램", "reel": "인스타그램",
                  "youtube": "유튜브", "shorts": "쇼츠", "short": "쇼츠",
                  "clip": "네이버클립", "tiktok": "틱톡", "threads": "스레드"}.get(icon)
        if not medium:
            explicit = (area + " " + subject)
            medium = next((label for pattern, label in [
                (r"클립", "네이버클립"), (r"릴스", "인스타그램"),
                (r"쇼츠", "쇼츠"), (r"틱톡", "틱톡"),
                (r"스레드", "스레드"), (r"유튜브", "유튜브"),
                (r"인스타", "인스타그램"), (r"블로그", "블로그")
            ] if re.search(pattern, explicit, re.I)), None)
        slots = number(one(r"모집\s*([\d,]+)명", part))
        applicants = number(one(r"신청\s*<strong>([\d,]+)명", part))
        item = make("mrblog", cid, subject, "https://www.mrblog.net/campaigns/" + cid,
                    region=area if not re.search("배송|기자단|구매", area) else None,
                    desc=desc, benefit=desc, image=one(r'<img[^>]+src="([^"]+)"', part),
                    applicants=applicants, slots=slots, days=days, channels=[medium] if medium else [],
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
        *[f"campaign_list.php?page={page}" for page in range(2,21)],
        "campaign_list.php?category_id=047A&page=2",
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
    """Index distinct, publicly available campaign pages without protected APIs."""
    base="https://4blog.net"
    output={}
    # Revisit the newest 10 pages on every run, and rotate older public pages.
    # Merge-by-ID in main() retains still-live previously indexed pages.
    window = int(NOW.timestamp() // (12 * 3600)) % 4
    pages = list(range(1, 11)) + list(range(11 + window * 10, 21 + window * 10))
    for page in pages:
        rel="/list/all"+("?pg="+str(page) if page>1 else "")
        try:
            body=safe_fetch(base+rel)
        except Exception as exc:
            print("포블로그 public page skipped",page,repr(exc)[:140],flush=True)
            # A transient error on one page must not hide later public pages.
            continue
        if not body:
            continue
        cards=re.findall(
            r'<a\s+class="nounderline"\s+href="/campaign/(\d+)/">([\s\S]*?)</a>',
            body,re.I
        )
        if not cards:
            break
        before=len(output)
        for cid, fragment in cards:
            if cid in output:
                continue
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
        print("포블로그 public page",page,"cards",len(cards),"new",len(output)-before,flush=True)
        time.sleep(1.0)
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
        *[f"campaign_list.php?page={page}" for page in range(2,26)],
        # Probe a small rotating public tail without adding excessive requests.
        *[f"campaign_list.php?page={page}" for page in range(26 + (int(NOW.timestamp() // (12 * 3600)) % 4) * 5, 31 + (int(NOW.timestamp() // (12 * 3600)) % 4) * 5)],
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


def cherrycook():
    """F&B campaign summaries on CherryCook public homepage (no protected APIs)."""
    base="https://cherry-cook.com/"
    out={}
    for page in range(0,10):
        path="mission"+("?page="+str(page) if page>0 else "")
        try:
            body=safe_fetch(urllib.parse.urljoin(base,path))
        except Exception as exc:
            print("체리쿡 list error",page,repr(exc)[:150],flush=True)
            break
        if not body:
            break
        cards=re.findall(r'<a\s+href="/item/(\d+)"[^>]*>([\s\S]*?)</a>',body,re.I)
        if not cards:
            break
        before=len(out)
        for cid,fragment in cards:
            if cid in out:
                continue
            title=plain(one(r'<div class="item-product">([\s\S]*?)</div>',fragment))
            if not title:
                continue
            remain=one(r'<div class="item-deadline">\s*(\d+)\s*일\s*남음',fragment)
            if remain is None:
                continue
            applicants=number(one(r'<span class="campaign-visit">\s*([\d,]+)\s*</span>',fragment))
            slots=number(one(r'<span class="item-visit">\s*([\d,]+)\s*</span>',fragment))
            image=one(r'<div class="image-box"[^>]*><img src="([^"]+)"',fragment)
            image=urllib.parse.urljoin(base,html.unescape(image)) if image else None
            cash=one(r'<div class="item-point">([\s\S]*?)</div>',fragment)
            region=one(r'^\[([^\]]+)\]',title)
            if region and region=="전체":
                region=None
            # Only map verified platform badges; never assume a review medium.
            channels=[]
            if re.search(r'class="item-blog"',fragment):
                channels.append("블로그")
            if re.search(r'class="item-instagram"',fragment):
                channels.append("인스타그램")
            if re.search(r'class="item-youtube"',fragment):
                channels.append("유튜브")
            benefit=plain(cash) or None
            item=make(
                "cherrycook",cid,title,base+"item/"+cid,
                region=region,desc=None,benefit=benefit,
                image=image,applicants=applicants,slots=slots,
                days=int(remain),channels=channels,
                ctype="배송형" if "배송" in title else "방문형" if region else None
            )
            if item:
                out[cid]=item
        print("체리쿡 public page",page,"cards",len(cards),"new",len(out)-before,flush=True)
        time.sleep(0.9)
    print("체리쿡 public homepage",len(cards),"cards",len(out),"campaigns",flush=True)
    return list(out.values())


def gaboja():
    """Use Gaboja homepage only: its /cmp/ detail path is robots-disallowed."""
    base="https://xn--o39a04kpnjo4k9hgflp.com/"
    body=safe_fetch(base)
    if not body:
        raise RuntimeError("Gaboja public homepage unavailable")
    out={}
    pattern=r'<a\s+href="https://xn--o39a04kpnjo4k9hgflp\.com/cmp/\?id=(\d+)"[^>]*>([\s\S]*?)</a>'
    cards=re.findall(pattern,body,re.I)
    for cid,fragment in cards:
        if cid in out:
            continue
        title=plain(one(r'<dt>([\s\S]*?)</dt>',fragment))
        days=one(r'(\d+)\s*일\s*남음',fragment)
        if not title or days is None:
            continue
        desc=plain(one(r'<dd>([\s\S]*?)</dd>',fragment))
        stats=re.search(r'신청\s*([\d,]+)\s*</span>\s*/\s*모집\s*([\d,]+)',fragment,re.I)
        applicants=number(stats.group(1)) if stats else None
        slots=number(stats.group(2)) if stats else None
        ctype=plain(one(r'<li[^>]*>\s*<i[^>]*></i>\s*<span>([^<]+)</span>',fragment))
        if ctype not in ("방문형","배송형","기자단","구매평"):
            ctype=None
        region=one(r'^\[([^\]]+)\]',title)
        if region and not sido(region):
            region=None
        image=one(r'<img\s+src="([^"]+)"',fragment)
        image=urllib.parse.urljoin(base,html.unescape(image)) if image else None
        media=[]
        for marker,label in (("class=\"blog","블로그"),("class=\"insta","인스타그램"),
                             ("class=\"youtube","유튜브"),("class=\"tiktok","틱톡")):
            if marker in fragment:
                media.append(label)
        item=make(
            "gaboja",cid,title,base+"cmp/?id="+cid,
            region=region,desc=desc,benefit=desc,
            image=image,applicants=applicants,slots=slots,days=int(days),
            channels=media,ctype=ctype
        )
        if item:
            out[cid]=item
    print("가보자체험단 public homepage",len(cards),"cards",len(out),"campaigns",flush=True)
    return list(out.values())


def bqueens():
    """Read only openly listed recruitment cards of the Beauty Queen site."""
    base="https://bqueens.net/"
    out={}
    for path in ("taste", *[f"taste?page={page}" for page in range(2,8)]):
        body=safe_fetch(urllib.parse.urljoin(base,path))
        if not body:
            continue
        cards=body.split('<div class="item">')[1:]
        added=0
        for fragment in cards:
            cid=one(r'<a\s+href="/taste/(\d+)"',fragment)
            if not cid or cid in out:
                continue
            title=plain(one(r'<h5\s+class="ellipsis[^"]*"[^>]*>([\s\S]*?)</h5>',fragment))
            days=one(r'신청\s*기간이\s*<span[^>]*>\s*(\d+)\s*일',fragment)
            if days is None:
                days=one(r'<h5>\s*<b>D\s*-\s*(\d+)</b>',fragment)
            if not title or days is None:
                continue
            img=one(r'<div class="item-content-img">[\s\S]*?<img\s+src="([^"]+)"',fragment)
            if img and not img.startswith("https://"):
                img=None
            item=make(
                "bqueens",cid,title,base+"taste/"+cid,
                region=None,benefit=None,desc=None,image=img,
                days=int(days),channels=[],
                ctype="배송형"
            )
            if item:
                out[cid]=item
                added+=1
        print("뷰티의여왕 public",path,len(cards),"cards",added,"new",flush=True)
    return list(out.values())


def huki():
    """Collect Huki's publicly listed campaigns without using private endpoints."""
    base="https://huki.co.kr/"
    pages=[
        ("", None),
        ("theme/huki/skin/board/gallery/productCampaign.php","배송형"),
        ("theme/huki/skin/board/gallery/localCampaign.php","방문형"),
        ("theme/huki/skin/board/gallery/reviewCampaign.php","구매평"),
        ("theme/huki/skin/board/gallery/newsCampaign.php","기자단"),
    ]
    out={}
    for rel, page_type in pages:
        try:
            doc=safe_fetch(urllib.parse.urljoin(base,rel))
        except Exception as exc:
            print("후키 public listing unavailable",rel,repr(exc)[:130],flush=True)
            continue
        if not doc:
            continue
        doc=re.sub(r"<!--[\s\S]*?-->","",doc)
        cards=re.findall(
            r'<a\b[^>]*href="([^"]*/bbs/board\.php\?[^"]*wr_id=(\d+)[^"]*)"[^>]*>([\s\S]*?)</a>',
            doc,re.I
        )
        added=0
        for link,cid,card in cards:
            if not re.search(r'\b모집중\b',plain(card)):
                continue
            dday=one(r'D-\s*(\d+)',card)
            # The card explicitly says 모집중. When no deadline is shown,
            # retain it only briefly with an unknown deadline.
            title=plain(one(r'<p\s+class="t_tit">([\s\S]*?)</p>',card))
            if not title:
                continue
            desc=plain(one(r'<p\s+class="t_sub">([\s\S]*?)</p>',card))
            bottom=plain(one(r'<p\s+class="t_bottom">([\s\S]*?)</p>',card))
            stat=re.search(r'신청\s*([\d,]+)\s*/\s*([\d,]+)\s*명',bottom)
            apps=number(stat.group(1)) if stat else None
            slots=number(stat.group(2)) if stat else None
            media=[]
            for key,chan in [("blog","블로그"),("instagram","인스타그램"),
                             ("insta","인스타그램"),("youtube","유튜브"),
                             ("reels","인스타그램"),("clip","네이버클립"),
                             ("tiktok","틱톡")]:
                if re.search(r'<span\s+class="'+key+r'">',card,re.I) and chan not in media:
                    media.append(chan)
            region=one(r'^\[([^\]]+)\]',title)
            if region and not sido(region):
                region=None
            image=one(r'<div\s+class="img">[\s\S]*?<img\s+src="([^"]+)"',card)
            if image and not image.startswith("https://"):
                image=None
            typ="기자단" if "원고형" in title else page_type
            item=make(
                "huki",cid,title,urllib.parse.urljoin(base,html.unescape(link)),
                region=region,desc=desc,benefit=desc,image=image,
                applicants=apps,slots=slots,days=int(dday) if dday is not None else None,
                channels=media,ctype=typ,open_verified=dday is None
            )
            if item and (cid not in out or (out[cid]["campaign_type"] is None and typ)):
                out[cid]=item
                added+=1
        print("후키 listing",rel or "/",len(cards),"cards",added,"new",flush=True)
        time.sleep(0.8)
    print("후키 public",len(out),"unique open campaigns",flush=True)
    return list(out.values())


def openreview():
    """Read OpenReview's public homepage recruitment cards only."""
    base="https://openreview.kr/"
    doc=safe_fetch(base)
    if not doc:
        raise RuntimeError("OpenReview homepage unavailable")
    out={}
    cards=doc.split('<div class="horizontal-card">')[1:]
    for card in cards:
        url_match=re.search(r'href="([^"]*exp_view\.php\?ex_idx=(\d+)[^"]*)"',card)
        if not url_match:
            continue
        link,cid=url_match.groups()
        if cid in out:
            continue
        title=plain(one(r'<div\s+class="card-title[^"]*">\s*<p[^>]*>([\s\S]*?)</p>',card))
        if not title:
            continue
        dday=one(r'<div\s+class="dday-area">[\s\S]*?D-\s*<span>(\d+)</span>',card)
        if dday is None:
            continue
        desc=plain(one(r'<div\s+class="card-text">[\s\S]*?<p[^>]*>([\s\S]*?)</p>',card))
        applicants=number(one(r'<p\s+class="apply-num">신청\s*<span>([\d,]+)</span>',card))
        slots=number(one(r'<p\s+class="apply-limit">\s*/\s*([\d,]+)\s*명',card))
        image=one(r'<a\s+href="[^"]*exp_view\.php[^"]*"\s+class="campaign-img">[\s\S]*?<img[^>]*src="([^"]+)"',card)
        image=urllib.parse.urljoin(base,html.unescape(image)) if image else None
        media=[]
        for key,channel in [("sns_blog.svg","블로그"),("sns_insta.svg","인스타그램"),
                            ("sns_youtube.svg","유튜브"),("sns_tiktok.svg","틱톡")]:
            if key in card:
                media.append(channel)
        region=one(r'^\[([^\]]+)\]',title)
        if region and not sido(region):
            region=None
        item=make(
            "openreview",cid,title,urllib.parse.urljoin(base,html.unescape(link)),
            region=region,desc=desc,benefit=desc,image=image,
            applicants=applicants,slots=slots,days=int(dday),
            channels=media,ctype=None
        )
        if item:
            out[cid]=item
    print("오픈리뷰 public homepage",len(cards),"cards",len(out),"campaigns",flush=True)
    return list(out.values())



def pavlovu():
    """Use only publicly listed Pavlovu campaigns; ignore login-only details."""
    base="https://pavlovu.com/"
    paths=[
        "review_campaign_list.php",
        "review_campaign_list.php?category_id=001A",
        "review_campaign_list.php?category_id=002A",
        "review_campaign_list.php?category_id=003A",
        "review_campaign_list.php?category_id=004A",
        *[f"review_campaign_list.php?page={page}" for page in range(2,13)],
    ]
    out={}
    for path in paths:
        try:
            body=safe_fetch(urllib.parse.urljoin(base,path))
        except Exception as exc:
            print("파블로 public list unavailable",path,repr(exc)[:140],flush=True)
            continue
        if not body:
            continue
        # Only the explicit campaign cards; don't index nav links or adverts.
        cards=re.findall(r'<li\s+class="pvli">([\s\S]*?)</li>',body,re.I)
        added=0
        for card in cards:
            link_match=re.search(r'<a\s+href="(review_campaign\.php\?cp_id=(\d+))"\s+class="pvc_tx">([\s\S]*?)</a>',card,re.I)
            if not link_match:
                continue
            link,cid,detail=link_match.groups()
            if cid in out:
                continue
            dday=one(r'<span\s+class="pvc_deadline">\s*D-\s*(\d+)',detail)
            if dday is None:
                continue
            store=plain(one(r'<span\s+class="pvc_store">([\s\S]*?)</span>',detail))
            benefit=plain(one(r'<strong>([\s\S]*?)</strong>',detail))
            title=" · ".join(x for x in (store,benefit) if x)
            if not title:
                continue
            summary=plain(one(r'<span\s+class="pvc_pn">([\s\S]*?)</span>',detail))
            region_part,_,cat_part=summary.partition("·")
            region=region_part.strip() if region_part.strip()!="배송" else None
            channel=plain(one(r'<span\s+class="pvc_pl">\s*<i[^>]*>([\s\S]*?)</i>',detail))
            channel={"인스타":"인스타그램","릴스":"인스타그램",
                     "클립":"네이버클립","숏츠":"쇼츠"}.get(channel,channel)
            media=[channel] if channel in ("블로그","인스타그램","유튜브","네이버클립","쇼츠","틱톡","스레드") else []
            slots=number(one(r'<span\s+class="pvc_mt">\s*모집\s*([\d,]+)\s*명',detail))
            img=one(r'<a\s+class="pvc_im"[^>]*><img\s+src="([^"]+)"',card)
            img=urllib.parse.urljoin(base,html.unescape(img)) if img else None
            ctype="배송형" if region is None else "방문형"
            item=make(
                "pavlovu",cid,title,urllib.parse.urljoin(base,link),
                region=region,desc=cat_part.strip() or None,benefit=benefit,
                image=img,applicants=None,slots=slots,days=int(dday),
                channels=media,ctype=ctype
            )
            if item:
                out[cid]=item
                added+=1
        print("파블로 public",path,len(cards),"cards",added,"new",flush=True)
        time.sleep(0.7)
    print("파블로 public campaigns",len(out),flush=True)
    return list(out.values())



def tqueens():
    """Index only publicly exposed Parcel Queen /taste listing cards.

    Original campaign URLs and deadline labels are public, but the source
    does not expose applicant counts on these cards. Never invent them.
    """
    base="https://tqueens.net/"
    out={}
    # Newer pages are checked on every run; older public pages are rotated.
    # Verify page availability and card markup before treating any result as live.
    window = int(NOW.timestamp() // (12 * 3600)) % 4
    pages = list(range(1, 10)) + list(range(10 + window * 5, 15 + window * 5))
    for page in pages:
        url=base+"taste"+("?page="+str(page) if page>1 else "")
        try:
            body=safe_fetch(url)
        except Exception as exc:
            print("택배의여왕 public listing unavailable",page,repr(exc)[:160],flush=True)
            break
        if not body:
            break
        cards=body.split('class="qz-dq-card qz-button fluid hover"')[1:]
        if not cards:
            break
        added=0
        for c in cards:
            cid=one(r'href="/taste/(\d+)"',c)
            if not cid or cid in out:
                continue
            title=plain(one(r'title="([^"]+?)\s*신청하기"',c))
            if not title:
                continue
            days=one(r'<strong>\s*D-\s*(\d+)\s*</strong>',c,re.I)
            if days is None and re.search(r'<strong>\s*D-Day\s*</strong>',c,re.I):
                days="0"
            if days is None:
                continue
            benefit=plain(one(r'<p\s+class="qz-body2-kr--line[^"]*"[^>]*>([\s\S]*?)</p>',c))
            img=one(r'<img\s+src="(https://[^"]+)"',c)
            region=one(r'^\[([^\]]+)\]',title)
            if region and not sido(region):
                region=None
            channels=[]
            if "릴스" in title or "인스타그램" in title:
                channels.append("인스타그램")
            elif "쇼츠" in title:
                channels.append("쇼츠")
            elif "클립" in title:
                channels.append("네이버클립")
            elif "틱톡" in title:
                channels.append("틱톡")
            item=make(
                "tqueens",cid,title,base+"taste/"+cid,
                region=region,desc=benefit or None,benefit=benefit or None,
                image=img,applicants=None,slots=None,days=int(days),
                channels=channels,ctype="방문형" if region else "배송형"
            )
            if item:
                out[cid]=item
                added+=1
        print("택배의여왕 public page",page,"cards",len(cards),"new",added,flush=True)
        # A page can contain only IDs already seen on an earlier page.
        # Do not confuse zero *new* IDs with end-of-pagination; the empty
        # card-list condition above is the actual stopping signal.
        time.sleep(1.5)
    print("택배의여왕 verified",len(out),flush=True)
    return list(out.values())



def storyn():
    """Only publicly visible StoryN homepage recruitment cards.

    The site's non-home pages may have separate robots rules. This adapter
    never fetches campaign detail/listing paths or requires login.
    """
    base="https://storyn.kr/"
    body=safe_fetch(base)
    if not body:
        raise RuntimeError("StoryN public homepage unavailable")
    cards=re.findall(r'<li>\s*<div class="box">([\s\S]*?)</li>',body,re.I)
    out={}
    for card in cards:
        cid=one(r'href="review_campaign\.php\?cp_id=(\d+)"',card)
        if not cid or cid in out:
            continue
        title=plain(one(r'<span class="it_name">([\s\S]*?)</span>',card))
        if not title:
            continue
        dday=one(r'<span class="dday">\s*D-Day\s*(\d+)\s*</span>',card)
        if dday is None:
            continue
        desc=plain(one(r'<span class="it_description">([\s\S]*?)</span>',card))
        status=one(r'<span>\s*신청\s*([\d,]+)\s*/\s*모집\s*<b[^>]*>([\d,]+)</b>',card)
        counts=re.search(r'신청\s*([\d,]+)\s*/\s*모집\s*<b[^>]*>([\d,]+)</b>',card)
        applicants=number(counts.group(1)) if counts else None
        slots=number(counts.group(2)) if counts else None
        meta=plain(one(r'<div class="sns_info">([\s\S]*?)</div>',card))
        channels=[]
        for marker,normalized in [
            ("N클립","네이버클립"),("클립","네이버클립"),
            ("블로그","블로그"),("인스타그램","인스타그램"),
            ("유튜브","유튜브"),("쇼츠","쇼츠"),("틱톡","틱톡")
        ]:
            if marker in meta and normalized not in channels:
                channels.append(normalized)
        ctype=plain(one(r'<div class="option2">([\s\S]*?)</div>',card))
        ctype=next((typ for typ in ("방문형","배송형","기자단") if typ in ctype),None)
        reg=one(r'^\[([^\]]+)\]',title)
        region=reg if reg and sido(reg) else None
        point=plain(one(r'<span class="point_box[^"]*">([\s\S]*?)</span>',card))
        benefit=(desc or "")+((" · "+point) if point else "")
        image=one(r'<div class="thumb">[\s\S]*?<img src="([^"]+)"\s+class="it_img"',card)
        image=urllib.parse.urljoin(base,html.unescape(image)) if image else None
        item=make(
            "storyn",cid,title,base+"review_campaign.php?cp_id="+cid,
            region=region,desc=desc,benefit=benefit or None,
            image=image,applicants=applicants,slots=slots,
            days=int(dday),channels=channels,ctype=ctype
        )
        if item:
            out[cid]=item
    print("스토리앤미디어 public homepage",len(cards),"cards",len(out),"verified",flush=True)
    return list(out.values())


def reviewnote():
    """Index verifiable cards from Reviewnote's public HTML only.

    Each accepted card must contain one unique /campaigns/<id> link, a
    public days-left label, and its own applicant/recruitment count.
    Missing fields cause a skip rather than invented data.
    """
    from html.parser import HTMLParser

    class CardParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack=[]
            self.candidates=[]

        def handle_starttag(self, tag, attrs):
            attrs=dict(attrs)
            if tag in ("div", "li", "article", "section", "a"):
                self.stack.append({"tag":tag,"text":[],"links":set(),
                                   "images":[],"labels":[]})
            href=attrs.get("href","")
            match=re.search(r"(?:^|/)campaigns/(\d+)(?:[/?#]|$)",href)
            if match:
                for node in self.stack:
                    node["links"].add(match.group(1))
            if tag=="img":
                alt=attrs.get("alt","")
                src=(attrs.get("src") or attrs.get("data-src") or
                     attrs.get("data-original") or "")
                if not src and attrs.get("srcset"):
                    src=attrs["srcset"].split(",")[0].strip().split(" ")[0]
                for node in self.stack:
                    if alt: node["labels"].append(alt)
                    if src and not node["images"]: node["images"].append(src)

        def handle_data(self, data):
            for node in self.stack:
                node["text"].append(data)

        def handle_endtag(self, tag):
            if tag not in ("div","li","article","section","a"):
                return
            if not self.stack: return
            # HTML cards can contain nested div/a nodes; only close a matching
            # top-level element, rather than corrupting the nested stack.
            if self.stack[-1]["tag"]!=tag: return
            node=self.stack.pop()
            value=plain(" ".join(node["text"]))
            if len(node["links"])==1 and re.search(r"\d+\s*일\s*남음",value) and re.search(r"(?:신청|선착순)\s*[\d,]+\s*/\s*[\d,]+",value):
                self.candidates.append(node)

    # Public user-facing filter variants expose different candidate sets.
    # Never assume that the first listing is an exhaustive index.
    # Only use regular browser listing URLs; no internal APIs or auth bypass.
    base_url = "https://www.reviewnote.co.kr/campaigns"
    queries = [
        {},
        {"channel": "BLOG"},
        {"channel": "INSTAGRAM"},
        {"channel": "ETC"},
        {"sort": "VISIT"},
        {"channel": "BLOG", "sort": "VISIT"},
        {"channel": "INSTAGRAM", "sort": "VISIT"},
        {"channel": "ETC", "sort": "VISIT"},
    ]
    urls = [base_url + ("?" + urllib.parse.urlencode(q) if q else "") for q in queries]
    # Public URL variations observed in ordinary browser listings.
    # These may overlap; campaign IDs provide the final deduplication.
    urls.extend([
        base_url + "?" + urllib.parse.urlencode({"city": "서울", "location": "135"}),
        base_url + "?" + urllib.parse.urlencode({"city": "인천"}),
    ])
    # Probe ordinary paginated listing URLs conservatively. Stop probing
    # after two consecutive pages add no verified unique campaign IDs.
    page_urls = [base_url + "?" + urllib.parse.urlencode({"page": p}) for p in range(2, 16)]
    urls.extend(page_urls)
    missing_page_progress = 0
    # Optional browser-backed expansion: public rendered listing cards are
    # accumulated as HTML after each real page scroll. No private API calls.
    browser_pages = {}
    if os.environ.get("REVIEWNOTE_BROWSER") == "1":
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(locale="ko-KR", timezone_id="Asia/Seoul")
                try:
                    for url in urls[:8]:
                        # safe_fetch enforces the same robots/access rules as
                        # every other source before the browser is opened.
                        if not safe_fetch(url):
                            continue
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(1000)
                        fragments=[]
                        ids=set()
                        stalled=0
                        for step in range(36):
                            snapshot=page.content()
                            current=set(re.findall(r'/campaigns/(\\d+)', snapshot))
                            if len(current - ids)==0:
                                stalled+=1
                            else:
                                stalled=0
                            ids.update(current)
                            fragments.append(snapshot)
                            if stalled>=5:
                                break
                            # Scroll the viewport AND any independently scrollable
                            # listing containers (the page may use an inner scroller).
                            page.evaluate("""() => {
                              window.scrollTo(0, document.documentElement.scrollHeight);
                              for (const el of document.querySelectorAll('main, section, div, ul')) {
                                const s = getComputedStyle(el);
                                if (el.scrollHeight > el.clientHeight + 250 &&
                                    /(auto|scroll)/.test(s.overflowY)) {
                                  el.scrollTop = el.scrollHeight;
                                }
                              }
                            }""")
                            page.mouse.wheel(0, 1400)
                            page.wait_for_timeout(750)
                        # Reviewnote also has numbered pagination (1–10 and
                        # subsequent page groups). Scroll alone misses it.
                        # Click visible page numbers in the normal public UI,
                        # verifying that campaign IDs actually change.
                        page_number = 1
                        repeated = 0
                        for _ in range(75):
                            next_number = page_number + 1
                            candidates = page.locator("button, a").filter(
                                has_text=re.compile(r"^\\s*" + str(next_number) + r"\\s*$"))
                            clicked = False
                            for j in range(min(candidates.count(), 12)):
                                candidate = candidates.nth(j)
                                if not candidate.is_visible():
                                    continue
                                try:
                                    candidate.click(timeout=1800)
                                    clicked = True
                                    break
                                except Exception:
                                    continue
                            if not clicked:
                                # Page groups often show 1-10 then a > arrow.
                                # Use a visibly named Next control only; never
                                # synthesize or call a private endpoint.
                                nav_next = page.get_by_role("button",name=re.compile(
                                    r"^(다음|다음 페이지|Next|›|»|>)$"))
                                try:
                                    nav_next.first.click(timeout=1800)
                                    page.wait_for_timeout(700)
                                    candidates = page.locator("button, a").filter(
                                        has_text=re.compile(r"^\\s*" + str(next_number) + r"\\s*$"))
                                    for j in range(min(candidates.count(), 12)):
                                        if candidates.nth(j).is_visible():
                                            candidates.nth(j).click(timeout=1800)
                                            clicked=True
                                            break
                                except Exception:
                                    pass
                            if not clicked:
                                print("리뷰노트 numbered pagination ended",url,"at",page_number,flush=True)
                                break
                            page.wait_for_timeout(850)
                            snapshot = page.content()
                            current = set(re.findall(r'/campaigns/(\\d+)',snapshot))
                            new_ids = current - ids
                            fragments.append(snapshot)
                            if not new_ids:
                                repeated += 1
                            else:
                                repeated = 0
                            ids.update(current)
                            page_number = next_number
                            print("리뷰노트 page",url,"number",page_number,
                                  "new",len(new_ids),"unique total",len(ids),flush=True)
                            if repeated >= 2:
                                break
                        browser_pages[url]="\n".join(fragments)
                        print("리뷰노트 browser",url,"visible IDs",len(ids),"scroll snapshots",len(fragments),flush=True)
                    # Discover additional listings using the actual public
                    # region selector, not speculative ?city= query strings.
                    # If the site changes its UI, skip that region gracefully.
                    regions = ["서울", "경기", "인천", "부산", "대구", "대전",
                               "광주", "울산", "세종", "강원", "충북", "충남",
                               "전북", "전남", "경북", "경남", "제주"]
                    regional_html = []
                    for region_name in regions:
                        try:
                            page.goto(base_url, wait_until="domcontentloaded", timeout=35000)
                            page.wait_for_timeout(700)
                            before_ids=set(re.findall(r'/campaigns/(\\d+)', page.content()))
                            page.get_by_text("지역", exact=True).first.click(timeout=2500)
                            page.get_by_text(region_name, exact=True).last.click(timeout=2500)
                            page.wait_for_timeout(1100)
                            after_ids=set(re.findall(r'/campaigns/(\\d+)', page.content()))
                            print("리뷰노트 region click audit",region_name,
                                  "current URL",page.url,"initial IDs",len(before_ids),
                                  "filtered IDs",len(after_ids),
                                  "changed",before_ids!=after_ids,flush=True)
                            region_fragments=[]
                            regional_ids=set()
                            no_growth=0
                            for step in range(16):
                                snap=page.content()
                                ids_now=set(re.findall(r'/campaigns/(\\d+)', snap))
                                no_growth = no_growth + 1 if not (ids_now-regional_ids) else 0
                                regional_ids.update(ids_now)
                                region_fragments.append(snap)
                                if no_growth>=4:
                                    break
                                page.evaluate("""() => {
                                  window.scrollTo(0, document.documentElement.scrollHeight);
                                  for (const el of document.querySelectorAll('main, section, div, ul')) {
                                    const s = getComputedStyle(el);
                                    if (el.scrollHeight > el.clientHeight + 250 &&
                                        /(auto|scroll)/.test(s.overflowY)) el.scrollTop = el.scrollHeight;
                                  }
                                }""")
                                page.mouse.wheel(0, 1200)
                                page.wait_for_timeout(700)
                            regional_html.extend(region_fragments)
                            print("리뷰노트 UI region",region_name,"IDs",len(regional_ids),flush=True)
                        except Exception as region_exc:
                            print("리뷰노트 region selector unavailable",region_name,
                                  type(region_exc).__name__,flush=True)
                    if regional_html:
                        # Join with a previously validated, accessible listing;
                        # the CardParser still validates each record independently.
                        browser_pages[base_url] += "\n" + "\n".join(regional_html)
                finally:
                    browser.close()
        except Exception as exc:
            print("리뷰노트 browser unavailable; continuing public HTML only",repr(exc)[:200],flush=True)
    out={}
    for url in urls:
        try:
            body=browser_pages.get(url) or safe_fetch(url)
            if not body: continue
        except Exception as ex:
            print("리뷰노트 public page unavailable",url,repr(ex)[:150],flush=True)
            continue
        parser=CardParser()
        parser.feed(body)
        public_detail_links = set(re.findall(r'/campaigns/(\d+)', body))
        print("리뷰노트 HTML audit",url,"bytes",len(body),"detail links",len(public_detail_links),"candidate cards",len(parser.candidates),flush=True)
        # Prefer smallest nested subtree for a given ID; this avoids mixing
        # adjacent cards and their independent media/application counters.
        candidates=sorted(parser.candidates,key=lambda n:len("".join(n["text"])))
        added=0
        for card in candidates:
            cid=next(iter(card["links"]))
            if cid in out: continue
            line=plain(" ".join(card["text"]))
            stats=re.search(r"(?:신청|선착순)\s*([\d,]+)\s*/\s*([\d,]+)",line)
            dday=re.search(r"(\d+)\s*일\s*남음",line)
            if not stats or not dday: continue
            # A card title must explicitly carry a location/recruitment marker.
            title_match=re.search(r"(\[(?:[^\]]{1,35})\]\s*[^\[\]]{2,110})",line)
            if not title_match: continue
            title=title_match.group(1).strip()
            if title.startswith("[재택]"):
                region=None
            else:
                region=one(r"^\[([^\]]+)\]",title)
            labels=" ".join(card["labels"])
            channels=[]
            for marker,ch in (("블로그","블로그"),("클립","네이버클립"),
                ("릴스","인스타그램"),("인스타그램","인스타그램"),
                ("쇼츠","쇼츠"),("유튜브","유튜브"),("틱톡","틱톡"),
                ("스레드","스레드")):
                if marker in labels and ch not in channels: channels.append(ch)
            # An image alt/name alone is not a sufficient basis for guessing
            # Instagram feed vs reels; both are mapped to existing broad filter.
            ctype=next((t for t in ("방문형","배송형","기자단","구매평") if t in line),None)
            # Preserve the public card's actual thumbnail, not the large
            # category/logo images from adjacent cards.
            image_url=None
            for candidate_image in card["images"]:
                resolved=urllib.parse.urljoin("https://www.reviewnote.co.kr/",html.unescape(candidate_image))
                if resolved.startswith("https://") and not re.search(r"/(?:logo|favicon|icon)[./_-]",resolved,re.I):
                    image_url=resolved
                    break
            item=make("reviewnote",cid,title,
                "https://www.reviewnote.co.kr/campaigns/"+cid,
                region=region,image=image_url,slots=number(stats.group(2)),
                applicants=number(stats.group(1)),days=int(dday.group(1)),
                channels=channels,ctype=ctype)
            if item:
                out[cid]=item
                added+=1
        print("리뷰노트 public listing",url,"candidate cards",len(parser.candidates),"new",added,flush=True)
        if url in page_urls:
            missing_page_progress = missing_page_progress + 1 if added == 0 else 0
            if missing_page_progress >= 2:
                print("리뷰노트 page probe halted: repeated/no additional verified IDs",flush=True)
                break
        time.sleep(1.0)
    return list(out.values())



def reviewplace():
    """Only public, verifiable ReviewPlace listing cards; no private endpoints."""
    from html.parser import HTMLParser

    class Anchors(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.active = []
            self.cards = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "a":
                href = html.unescape(attrs.get("href") or "")
                url = urllib.parse.urljoin("https://www.reviewplace.co.kr/", href)
                pu = urllib.parse.urlparse(url)
                cid = urllib.parse.parse_qs(pu.query).get("id", [])
                valid = (pu.hostname in ("www.reviewplace.co.kr", "reviewplace.co.kr")
                         and pu.path.rstrip("/") == "/pr"
                         and cid and cid[0].isdigit())
                self.active.append({"id": cid[0] if valid else None,
                                    "text": [], "image": None})
            elif tag == "img" and self.active:
                img = (attrs.get("data-src") or attrs.get("src") or
                       attrs.get("data-original"))
                if img and not self.active[-1]["image"]:
                    self.active[-1]["image"] = urllib.parse.urljoin(
                        "https://www.reviewplace.co.kr/", html.unescape(img))
        def handle_data(self, data):
            if self.active:
                self.active[-1]["text"].append(data)
        def handle_endtag(self, tag):
            if tag == "a" and self.active:
                node = self.active.pop()
                if node["id"]:
                    self.cards.append(node)
                if self.active:
                    self.active[-1]["text"].extend(node["text"])

    base = "https://www.reviewplace.co.kr/"
    paths = ["/pr/?ct1=제품", "/pr/?ct1=지역",
             "/pr/?ct1=기자단", "/pr/?ct1=구매평", "/"]
    out = {}
    for path in paths:
        url = urllib.parse.urljoin(base, path)
        try:
            doc = safe_fetch(url)
            if not doc:
                continue
        except Exception as exc:
            print("reviewplace fetch failed", url, repr(exc)[:120], flush=True)
            continue
        parser = Anchors()
        parser.feed(doc)
        added = 0
        for node in parser.cards:
            cid = node["id"]
            if cid in out:
                continue
            raw = plain(" ".join(node["text"]))
            match = re.search(r"(?:D\s*[-–]\s*(\d+)|오늘\s*마감)", raw, re.I)
            stat = re.search(r"신청\s*([\d,]+)\s*/\s*([\d,]+)\s*명?", raw)
            if not match or not stat:
                continue
            days = int(match.group(1)) if match.group(1) else 0
            title = raw[:match.start()].strip()
            if len(title) < 6 or len(title) > 280:
                continue
            label = re.search(r"^\[([^\]]{1,60})\]", title)
            chtext = label.group(1) if label else ""
            channels = []
            for marker, value in (("블로그", "블로그"), ("클립", "네이버클립"),
                                  ("인스타", "인스타그램"), ("릴스", "인스타그램"),
                                  ("유튜브", "유튜브"), ("쇼츠", "쇼츠")):
                if marker in chtext and value not in channels:
                    channels.append(value)
            typ = ("기자단" if "기자단" in path else
                   "구매평" if ("구매평" in path or "쿠팡" in chtext or "스마트스토어" in chtext) else
                   "방문형" if "지역" in path else "배송형")
            if path == "/" and typ == "배송형":
                typ = None  # Homepage card type is not independently verified.
            img = node["image"]
            if img and not img.startswith("https://"):
                img = None
            item = make("reviewplace", cid, title, base + "pr/?id=" + cid,
                        image=img, applicants=number(stat.group(1)),
                        slots=number(stat.group(2)), days=days,
                        channels=channels, ctype=typ)
            if item:
                out[cid] = item
                added += 1
        print("reviewplace",path,"verified",added,"total",len(out),flush=True)
        time.sleep(0.5)
    return list(out.values())


def gangnammat():
    """Read robots-permitted, public Gangnam Matzip campaign LIST cards only.

    The site's visible /cp/ page contains li.list_item cards with an original
    /cp/?id=<integer> link, D-day, applicant/slot counts, and a thumbnail.
    No login, private APIs, speculative pagination, or detail-page traversal.
    """
    base = "https://gangnam-review.net/"
    body = safe_fetch(base + "cp/")
    if not body:
        return []
    cards = re.findall(
        r"<li\b(?=[^>]*\bclass\s*=\s*['\"]list_item\b)[^>]*>[\s\S]*?</li>",
        body, re.I,
    )
    out = {}
    for card in cards:
        cid = one(r"\bdata-product\s*=\s*['\"](\d+)['\"]", card, re.I)
        if not cid or cid in out or not re.search(
            r"href\s*=\s*['\"]/cp/\?id=" + re.escape(cid) + r"['\"]",
            card, re.I,
        ):
            continue
        title = plain(one(
            r"<dt\b[^>]*class\s*=\s*['\"]tit['\"][^>]*>\s*"
            r"<a\b[^>]*>([\s\S]*?)</a>", card, re.I,
        ))
        benefit = plain(one(
            r"<dd\b[^>]*class\s*=\s*['\"]sub_tit['\"][^>]*>([\s\S]*?)</dd>",
            card, re.I,
        ))
        if len(title) < 3 or len(title) > 200:
            continue
        dday = plain(one(
            r"<em\b[^>]*class\s*=\s*['\"]day_c['\"][^>]*>([\s\S]*?)</em>",
            card, re.I,
        ))
        remain = one(r"(\d+)\s*일\s*남음", dday)
        days = int(remain) if remain is not None else 0 if re.search(
            r"D\s*[-–]?\s*Day|오늘\s*(?:마감|까지)", dday, re.I,
        ) else None
        if days is None:
            continue
        counts = re.search(
            r"신청\s*([\d,]+)\s*</b>\s*/\s*모집\s*([\d,]+)",
            card, re.I,
        )
        if not counts:
            continue
        applicants = number(counts.group(1))
        slots = number(counts.group(2))
        if slots is None or slots <= 0 or applicants is None:
            continue
        image = one(r"<img\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", card, re.I)
        if image:
            image = urllib.parse.urljoin(base, html.unescape(image))
            if not image.startswith("https://"):
                image = None
        typ = plain(one(
            r"<em\b[^>]*class\s*=\s*['\"]type['\"][^>]*>([\s\S]*?)</em>",
            card, re.I,
        ))
        ctype = (
            "기자단" if "기자단" in typ else
            "배송형" if "배송형" in typ else
            "방문형" if "방문형" in typ else None
        )
        channels = []
        # Only derive channel from the publicly visible badge, not title text.
        for pattern, label in (
            (r"<em\b[^>]*class\s*=\s*['\"]blog['\"]", "블로그"),
            (r"<em\b[^>]*class\s*=\s*['\"]clip['\"]", "네이버클립"),
            (r"<em\b[^>]*class\s*=\s*['\"](?:insta|instagram|reels)['\"]", "인스타그램"),
            (r"<em\b[^>]*class\s*=\s*['\"](?:youtube|yt)['\"]", "유튜브"),
            (r"<em\b[^>]*class\s*=\s*['\"](?:shorts|short)['\"]", "쇼츠"),
        ):
            if re.search(pattern, card, re.I) and label not in channels:
                channels.append(label)
        region = one(r"^\[([^\]]{2,35})\]", title)
        if region and region in ("재택", "배송", "페이백", "기자단"):
            region = None
        item = make(
            "gangnammat", cid, title, base + "cp/?id=" + cid,
            region=region, benefit=benefit, image=image,
            applicants=applicants, slots=slots, days=days,
            channels=channels, ctype=ctype,
        )
        if item:
            out[cid] = item
    print("강남맛집 public cards", len(cards), "verified", len(out), flush=True)
    return list(out.values())


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(OUT.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        current = []
    stored = {item["id"]: item for item in current if isinstance(item, dict) and "id" in item}
    found = 0
    collectors = [("dinnerqueen", dinnerqueen), ("mrblog", mrblog), ("modan", modan), ("modootogether", modootogether), ("fourblog", fourblog), ("assaview", assaview), ("ringble", ringble), ("cometoplay", cometoplay), ("cherrycook", cherrycook), ("gaboja", gaboja), ("bqueens", bqueens), ("huki", huki), ("openreview", openreview), ("pavlovu", pavlovu), ("tqueens", tqueens), ("storyn", storyn), ("reviewnote", reviewnote), ("reviewplace", reviewplace), ("gangnammat", gangnammat)]
    if os.environ.get("DQ_ONLY") == "1":
        collectors = [("dinnerqueen", dinnerqueen)]
    if os.environ.get("REVIEWNOTE_ONLY") == "1":
        collectors = [("reviewnote", reviewnote)]
    for name, collect in collectors:
        try:
            items = collect()
            for item in items:
                previous = stored.get(item["id"])
                if previous:
                    item["first_seen_at"] = previous.get("first_seen_at", item["first_seen_at"])
                    # Do not erase a previously captured photo if this run
                    # encounters a card with no publicly exposed image.
                    if not item.get("image_url") and previous.get("image_url"):
                        item["image_url"] = previous["image_url"]
                stored[item["id"]] = item
            found += len(items)
        except Exception as ex:
            print("Collection failure, existing data preserved:", name, repr(ex))
    if found == 0:
        print("No verified new listings. Existing snapshot remains unchanged.")
        return
    cutoff = NOW - timedelta(days=21)
    unknown_cutoff = NOW - timedelta(hours=48)
    rows = [
        x for x in stored.values()
        if (
            (x.get("apply_deadline") and x["apply_deadline"] >= TODAY.isoformat()
             and datetime.fromisoformat(x["last_seen_at"]) >= cutoff)
            or
            (x.get("apply_deadline") is None and x.get("deadline_precision") == "unknown"
             and x.get("open_verified") is True
             and datetime.fromisoformat(x["last_seen_at"]) >= unknown_cutoff)
        )
    ]
    rows.sort(key=lambda x: (x["source_id"], x["id"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print("Snapshot saved: %s unique live campaigns (%s observed this run)" % (len(rows), found))

if __name__ == "__main__":
    main()
