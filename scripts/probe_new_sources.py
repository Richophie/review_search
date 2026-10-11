#!/usr/bin/env python3
"""Read-only discovery of public campaign pages for new platform adapters.

No authentication, no protected endpoints, no campaign snapshot mutations.
Uses the same robots-aware safe_fetch helper as the production collector.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import safe_fetch

SOURCES = {
    "reviewnote": {
        "pages": ["https://www.reviewnote.co.kr/", "https://www.reviewnote.co.kr/campaigns"],
        "detail": r"https?://(?:www\.)?reviewnote\.co\.kr/campaigns/(\d+)|(?:^|[\"'])/campaigns/(\d+)",
    },
    "gangnam": {
        "pages": ["https://gangnam-review.net/cp/", "https://gangnam-review.net/"],
        "detail": r"(?:https?://(?:gangnam-review\.net|xn--939au0g4vj8sq\.net))?/cp/\?id=(\d+)",
    },
    "revu": {
        "pages": ["https://webview.revu.net/"],
        "detail": r"(?:https?://[^\"' ]*revu\.net)?/[^\"' ]*(?:campaign|experience)[^\"' ]*",
    },
}
RESULT = Path("public/data/source_probe.json")
def probe():
    results={}
    for source, cfg in SOURCES.items():
        attempts=[]
        ids=set()
        for url in cfg["pages"]:
            info={"url":url,"status":"unavailable","detail_link_count":0}
            try:
                html=safe_fetch(url)
                if html:
                    matches=re.findall(cfg["detail"],html,re.I)
                    for m in matches:
                        ids.add(next((s for s in m if s), "") if isinstance(m,tuple) else m)
                    info.update(status="public_html",detail_link_count=len(matches),
                                html_bytes=len(html.encode("utf-8")))
                else:
                    info["status"]="blocked_or_empty"
            except Exception as ex:
                info["status"]="fetch_failed"
                info["error_type"]=type(ex).__name__
            attempts.append(info)
        results[source]={"pages":attempts,"distinct_candidate_details":len(ids)}
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=="__main__":
    probe()
