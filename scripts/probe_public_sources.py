#!/usr/bin/env python3
"""Read-only, bounded investigation of official public source listing pages.

Does not save campaign data, follow hidden endpoints, or bypass blocked access.
Run from the GitHub runner to distinguish robots denial, unavailable HTML,
rendered-only listings, and public list/detail link structures.
"""
from html.parser import HTMLParser
from collections import Counter
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
import re
import time

AGENT = "ChehumMoaBot/0.1 (+public listing index; respects robots.txt)"
SITES = {
    "cloudreview": [
        "https://www.cloudreview.co.kr/",
        "https://www.cloudreview.co.kr/campaign/blog",
        "https://www.cloudreview.co.kr/campaign/instagram",
    ],
    "gangnammat": [
        "https://gangnam-review.net/",
        "https://gangnam-review.net/cp/",
    ],
    "revu": ["https://webview.revu.net/"],
}
MAX_BYTES = 1_300_000


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            props = dict(attrs)
            self.stack.append({"href": props.get("href", ""), "text": []})

    def handle_data(self, data):
        if self.stack:
            self.stack[-1]["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.stack:
            node = self.stack.pop()
            self.links.append(node)
            if self.stack:
                self.stack[-1]["text"].extend(node["text"])


def read_public(url):
    req = Request(url, headers={"User-Agent": AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    with urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            raise ValueError("status " + str(resp.status))
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read(MAX_BYTES).decode(charset, errors="replace")


def main():
    for name, urls in SITES.items():
        origin = urlparse(urls[0])
        robots_url = f"{origin.scheme}://{origin.netloc}/robots.txt"
        print(f"\n=== {name}: robots {robots_url} ===", flush=True)
        try:
            robots_text = read_public(robots_url)
            if not re.search(r"(?im)^\s*User-agent\s*:", robots_text):
                print("No valid robots directives - do not fetch", flush=True)
                continue
            rp = RobotFileParser()
            rp.parse(robots_text.splitlines())
            print("robots content (first 850 chars):", robots_text[:850].replace("\n", " | "), flush=True)
        except Exception as exc:
            print("Robots unavailable - fail closed:", type(exc).__name__, str(exc)[:120], flush=True)
            continue
        for url in urls:
            if not rp.can_fetch(AGENT, url):
                print("BLOCKED:", url, flush=True)
                continue
            try:
                html = read_public(url)
                if re.search(r"cf-challenge|verify you are human|captcha challenge|Just a moment", html[:9000], re.I):
                    print("Challenge page - skip", url, flush=True)
                    continue
                p = Links()
                p.feed(html)
                normalized = []
                for entry in p.links:
                    href = urljoin(url, entry["href"])
                    if urlparse(href).netloc != origin.netloc:
                        continue
                    text = " ".join(" ".join(entry["text"]).split())[:75]
                    normalized.append((href, text))
                listing = [(href, label) for href, label in normalized
                           if re.search(r"/(?:campaign/detail/\d+|cp/\?id=\d+|campaign/\d+)", href)]
                prefixes = Counter(urlparse(link).path.split("/")[1] for link, _ in normalized)
                print("PUBLIC", url, "bytes", len(html), "internal links", len(normalized),
                      "campaign detail links", len(set(x[0] for x in listing)),
                      "prefixes", prefixes.most_common(8), flush=True)
                print("DETAIL SAMPLES:", list(dict.fromkeys(listing))[:8], flush=True)
                if not listing:
                    print("OTHER INTERNAL LINKS:", normalized[:12], flush=True)
                # No full raw HTML; indicate only known campaign structural hints.
                print("STRUCTURE:", {key: len(re.findall(re.escape(key), html, re.I))
                      for key in ("campaign/detail/", "cp/?id=", "일남음", "D-Day",
                                  "인 모집", "신청자", "pagination", "__NEXT_DATA__")},
                      flush=True)
            except Exception as exc:
                print("PUBLIC PAGE FAILED", url, type(exc).__name__, str(exc)[:160], flush=True)
            time.sleep(1.2)


if __name__ == "__main__":
    main()
