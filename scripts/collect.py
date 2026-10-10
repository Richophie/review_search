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
    return next((short for long, short in aliases.items() if region.startswith(long)), None)

def make(source, ext_id, title, url, region=None, desc=None, benefit=None,
         image=None, applicants=None, slots=None, days=None, channels=None, ctype=None,
         exact_deadline=None, published_at=None, category_override=None):
    if not title or not url.startswith("https://") or (exact_deadline is None and (days is None or days < 0)):
        return None
    deadline = exact_deadline or (TODAY + timedelta(days=days)).isoformat()
    if deadline < TODAY.isoformat():
        return None
    channels = ["블로그"] if channels is None else channels
    cat = category_override or infer_category(title + " " + (desc or ""))
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
        "search_text": " ".join(filter(None, [cleaned_title, plain(desc), region or "", cat] + channels)).lower(),
    }

def dinnerqueen():
    records = {}
    for page in range(1, 25):
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
    for idx, item in enumerate(items):
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
        if idx < len(items)-1:
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

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(OUT.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        current = []
    stored = {item["id"]: item for item in current if isinstance(item, dict) and "id" in item}
    found = 0
    for name, collect in [("dinnerqueen", dinnerqueen), ("mrblog", mrblog), ("modan", modan), ("modootogether", modootogether)]:
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
