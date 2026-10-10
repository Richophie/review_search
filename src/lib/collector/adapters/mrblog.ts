import type { SourceAdapter } from "../types";
import type { RawCampaign } from "../normalize";
import { cleanText } from "../normalize";
import { politeFetch } from "../http";

const BASE = "https://www.mrblog.net";
const ICON_MAP: Record<string, string> = {
  blog: "블로그", insta: "인스타그램", instagram: "인스타그램", youtube: "유튜브",
  shorts: "쇼츠", reels: "인스타그램", clip: "네이버클립", tiktok: "틱톡",
};

// robots.txt (checked): "User-agent: *  Disallow:" (everything allowed). Reads the public home listing only.
export const mrblog: SourceAdapter = {
  id: "mrblog",
  name: "미블",
  async collect() {
    const html = await politeFetch(`${BASE}/`, { delayMs: 1000 });
    const out = new Map<string, RawCampaign>();
    // Parse by anchor so href and body stay together
    const re = /<a href="https:\/\/www\.mrblog\.net\/campaigns\/(\d+)" class="campaign_item">([\s\S]*?)<\/a>/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(html))) {
      const [, id, body] = m;
      if (out.has(id)) continue;
      const img = body.match(/<img[^>]+src="([^"]+)"/)?.[1] ?? null;
      const icon = body.match(/sns_icon\s+([a-z]+)/)?.[1];
      const area = cleanText(body.match(/<span class="area">([\s\S]*?)<\/span>\s*<strong/)?.[1]);
      const subject = cleanText(body.match(/<strong class="subject">([\s\S]*?)<\/strong>/)?.[1]);
      const desc = cleanText(body.match(/<p class="desc">([\s\S]*?)<\/p>/)?.[1]);
      const dday = cleanText(body.match(/<span class="d_day">([\s\S]*?)<\/span>/)?.[1]) ?? "";
      const cur = body.match(/신청\s*<strong>([\d,]+)명/);
      const slots = body.match(/모집\s*([\d,]+)명/);
      const days = dday.match(/(\d+)\s*일 남음/);
      if (!subject) continue;
      out.set(id, {
        sourceId: "mrblog",
        externalId: id,
        url: `${BASE}/campaigns/${id}`,
        title: subject,
        description: desc,
        benefit: desc,
        imageUrl: img && !img.includes("no-image") ? img : null,
        regionText: area && !/배송|기자단|구매/.test(area) ? area : null,
        badges: area && /배송|기자단|구매/.test(area) ? [area] : [],
        channels: icon ? [ICON_MAP[icon] ?? icon] : [],
        applicants: cur ? Number(cur[1].replace(/,/g, "")) : null,
        slots: slots ? Number(slots[1].replace(/,/g, "")) : null,
        daysLeft: days ? Number(days[1]) : /오늘/.test(dday) ? 0 : null,
      });
    }
    return [...out.values()];
  },
};
