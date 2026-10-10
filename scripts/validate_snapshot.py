#!/usr/bin/env python3
"""Validate collected public campaign data before automatic publication."""
from datetime import date, datetime, timezone, timedelta
import json
import urllib.parse
from pathlib import Path

path = Path("public/data/campaigns.json")
campaigns = json.loads(path.read_text(encoding="utf-8"))
assert isinstance(campaigns, list), "Campaign index must be a list"
seen_ids, seen_urls = set(), set()
allowed_domains = {
    "dinnerqueen.net", "www.mrblog.net", "modan.kr", "www.modootogether.com", "4blog.net", "www.assaview.co.kr", "www.ringble.co.kr", "www.cometoplay.kr", "cherry-cook.com", "xn--o39a04kpnjo4k9hgflp.com", "bqueens.net", "huki.co.kr", "openreview.kr", "pavlovu.com", "tqueens.net", "storyn.kr"
}
today = datetime.now(timezone(timedelta(hours=9))).date()
for item in campaigns:
    assert isinstance(item,dict)
    cid = item.get("id")
    url = item.get("original_url")
    assert cid and cid not in seen_ids, f"Duplicate or missing id: {cid}"
    assert isinstance(url,str) and url not in seen_urls, f"Missing/duplicate URL: {url}"
    u=urllib.parse.urlparse(url)
    assert u.scheme == "https" and u.hostname in allowed_domains, f"Unexpected URL: {url}"
    assert item.get("title") and item.get("source_id"), f"Missing title or source: {cid}"
    if item.get("apply_deadline") is None:
        assert item.get("deadline_precision") == "unknown" and item.get("open_verified") is True, f"Unverified no-date campaign: {cid}"
        last_seen = datetime.fromisoformat(item["last_seen_at"].replace("Z","+00:00"))
        assert last_seen > datetime.now(timezone.utc)-timedelta(hours=48), f"Stale unknown-deadline campaign: {cid}"
    else:
        deadline = date.fromisoformat(item["apply_deadline"])
        assert deadline >= today, f"Expired campaign in active snapshot: {cid}"
    assert item.get("country_code") == "KR"
    slots, applicants = item.get("slots"), item.get("applicants")
    ratio, remaining = item.get("competition_ratio"), item.get("remaining_slots")
    if slots is None or slots <= 0 or applicants is None:
        assert ratio is None and remaining is None, f"Invented ratio: {cid}"
    else:
        assert slots > 0 and applicants >= 0
        assert ratio is not None and abs(ratio-applicants/slots)<1e-6
        assert remaining == max(slots-applicants,0)
    first = datetime.fromisoformat(item["first_seen_at"].replace("Z","+00:00"))
    last = datetime.fromisoformat(item["last_seen_at"].replace("Z","+00:00"))
    assert first.tzinfo is not None and last.tzinfo is not None, f"Missing timestamps: {cid}"
    seen_ids.add(cid)
    seen_urls.add(url)
print(f"Validated {len(campaigns)} real campaigns across {len(set(c['source_id'] for c in campaigns))} sources")
