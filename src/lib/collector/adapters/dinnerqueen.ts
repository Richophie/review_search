import type { SourceAdapter } from "../types";
import type { RawCampaign } from "../normalize";
import { cleanText } from "../normalize";
import { politeFetch } from "../http";

const BASE = "https://dinnerqueen.net";
const KNOWN_BADGES = ["맛집", "뷰티", "여행", "숙박", "식품", "배송", "기자단", "반려동물", "생활", "릴스", "클립", "유튜브", "쇼츠"];

// robots.txt (checked): "User-agent: *  Allow: /". Only the public /taste listing is read.
export const dinnerqueen: SourceAdapter = {
  id: "dinnerqueen",
  name: "디너의여왕",
  async collect() {
    const out: RawCampaign[] = [];
    for (let page = 1; page <= 4; page++) {
      const html = await politeFetch(`${BASE}/taste${page > 1 ? `?page=${page}` : ""}`, { delayMs: 2000 });
      const cards = html.split('class="qz-dq-card campaign').slice(1);
      if (!cards.length) break;
      for (const c of cards) {
        const href = c.match(/href="\/taste\/(\d+)"/);
        if (!href) continue;
        const id = href[1];
        const titleAttr = c.match(/title="([^"]+?)\s*신청하기"/)?.[1] ?? "";
        const img = c.match(/<img[^>]+src="([^"]+)"/)?.[1] ?? null;
        const desc = c.match(/color-placeholder[^"]*">([\s\S]*?)<\/p>/)?.[1] ?? null;
        const plain = cleanText(c) ?? "";
        const days = plain.match(/(\d+)\s*일 남음/);
        const today = /오늘\s*마감|D-?day/i.test(plain);
        const stats = plain.match(/신청\s*([\d,]+)\s*\/\s*([\d,]+)/);
        const badges = KNOWN_BADGES.filter((b) => new RegExp(`(^|\\s)${b}(\\s|$)`).test(plain.slice(0, 400)));
        const region = titleAttr.match(/^\[([^\]]+)\]/)?.[1];
        const regionText = region && !/릴스|클립|배송|기자단|유튜브|쇼츠/.test(region) ? region : null;
        const channels: string[] = [];
        if (badges.includes("릴스")) channels.push("인스타그램");
        if (badges.includes("클립")) channels.push("네이버클립");
        if (badges.includes("유튜브")) channels.push("유튜브");
        if (badges.includes("쇼츠")) channels.push("쇼츠");
        if (!channels.length) channels.push("블로그");
        out.push({
          sourceId: "dinnerqueen",
          externalId: id,
          url: `${BASE}/taste/${id}`,
          title: titleAttr.replace(/^(\[[^\]]+\]\s*)+/, "").trim() || titleAttr,
          description: desc,
          imageUrl: img,
          regionText,
          badges,
          channels,
          applicants: stats ? Number(stats[1].replace(/,/g, "")) : null,
          slots: stats ? Number(stats[2].replace(/,/g, "")) : null,
          daysLeft: days ? Number(days[1]) : today ? 0 : null,
        });
      }
    }
    return out;
  },
};
