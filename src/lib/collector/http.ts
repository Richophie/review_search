// Polite HTTP fetching: identifiable UA, per-request delay, retry with exponential backoff.
export const USER_AGENT =
  "Mozilla/5.0 (compatible; ChehumMoaBot/0.1; public listing aggregator; respects robots.txt)";

export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function politeFetch(url: string, opts: { retries?: number; delayMs?: number } = {}) {
  const retries = opts.retries ?? 2;
  let wait = 1500;
  for (let attempt = 0; ; attempt++) {
    try {
      const res = await fetch(url, {
        headers: { "User-Agent": USER_AGENT, Accept: "text/html", "Accept-Language": "ko-KR,ko;q=0.9" },
        redirect: "follow",
      });
      if (res.status === 429 || res.status >= 500) throw new Error(`HTTP ${res.status}`);
      if (!res.ok) throw Object.assign(new Error(`HTTP ${res.status}`), { fatal: true });
      const text = await res.text();
      if (/captcha|cf-challenge|접근이 차단/i.test(text.slice(0, 5000))) {
        throw Object.assign(new Error("차단/CAPTCHA 감지 — 수집 중단"), { fatal: true });
      }
      if (opts.delayMs) await sleep(opts.delayMs);
      return text;
    } catch (e) {
      if ((e as { fatal?: boolean }).fatal || attempt >= retries) throw e;
      await sleep(wait);
      wait *= 2;
    }
  }
}
