#!/usr/bin/env python3
"""Collect public campaign listings for the Review Search snapshot.

Only fetch publicly accessible pages permitted by robots.txt. No logins, no
CAPTCHA bypass, no hidden endpoints. Keep verified attribution and original URLs.
"""
import html
import json
import re
import time
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
         image=None, applicants=None, slots=None, days=None, channels=None, ctype=None):
    if not title or not url.startswith("https://") or days is None or days < 0:
        return None
    deadline = (TODAY + timedelta(days=days)).isoformat()
    channels = channels or ["블로그"]
    cat = infer_category(title + " " + (desc or ""))
    if not ctype:
        ctype = "방문형" if region else "배송형" if re.search("배송|택배", title) else None
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
        "apply_deadline": deadline, "deadline_precision": "days_left",
        "first_seen_at": now, "last_seen_at": now, "timezone": "Asia/Seoul",
        "competition_ratio": ratio, "remaining_slots": remaining,
        "dedupe_key": re.sub(r"[^\w]", "", (region or "") + cleaned_title).lower(),
        "search_text": " ".join(filter(None, [cleaned_title, plain(desc), region or "", cat] + channels)).lower(),
    }

def dinnerqueen():
    records = {}
    for page in range(1, 13):
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
            days = int(days) if days is not None else 0 if re.search("오늘\\s*마감|D-?day", body_text, re.I) else None
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

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(OUT.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        current = []
    stored = {item["id"]: item for item in current if isinstance(item, dict) and "id" in item}
    found = 0
    for name, collect in [("dinnerqueen", dinnerqueen), ("mrblog", mrblog)]:
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
