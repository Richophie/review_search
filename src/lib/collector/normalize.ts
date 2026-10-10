// Shared normalization for all source adapters. Pure functions, safe anywhere.

export type RawCampaign = {
  sourceId: string;
  externalId: string;
  url: string;
  title: string;
  description?: string | null;
  benefit?: string | null;
  imageUrl?: string | null;
  regionText?: string | null;
  badges?: string[];
  channels?: string[];
  slots?: number | null;
  applicants?: number | null;
  daysLeft?: number | null; // from "N일 남음" on listing
  exactDeadline?: string | null; // YYYY-MM-DD when the source exposes it
  countryCode?: string;
  timezone?: string;
  language?: string;
  currency?: string;
};

export const SIDO = [
  "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
  "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
] as const;

const SIDO_ALIASES: Record<string, string> = {
  서울특별시: "서울", 부산광역시: "부산", 대구광역시: "대구", 인천광역시: "인천",
  광주광역시: "광주", 대전광역시: "대전", 울산광역시: "울산", 세종특별자치시: "세종",
  경기도: "경기", 강원도: "강원", 강원특별자치도: "강원", 충청북도: "충북", 충청남도: "충남",
  전라북도: "전북", 전북특별자치도: "전북", 전라남도: "전남", 경상북도: "경북", 경상남도: "경남",
  제주도: "제주", 제주특별자치도: "제주",
};

export const CATEGORIES = [
  "맛집", "카페", "숙박·여행", "뷰티", "생활", "식품", "디지털", "키즈", "반려", "문화", "기타",
] as const;

const CATEGORY_RULES: [string, RegExp][] = [
  ["카페", /카페|커피|디저트|베이커리|빵|케이크|브런치/],
  ["숙박·여행", /숙박|호텔|펜션|리조트|글램핑|캠핑|여행|투어|스테이|풀빌라/],
  ["뷰티", /뷰티|헤어|네일|속눈썹|피부|에스테틱|왁싱|화장품|메이크업|미용|두피|필라테스|요가|마사지/],
  ["반려", /반려|펫|강아지|애견|고양이|애묘/],
  ["키즈", /키즈|아이|유아|아기|육아|어린이/],
  ["디지털", /디지털|전자|가전|앱|IT|스마트|이어폰|충전/],
  ["문화", /공연|전시|문화|클래스|공방|체험관|뮤지컬|영화/],
  ["식품", /식품|밀키트|간편식|건강식품|영양제|음료|과자|소스/],
  ["맛집", /맛집|식당|고기|갈비|국밥|떡볶이|치킨|통닭|횟집|초밥|파스타|피자|술집|포차|이자카야|식사권|정식|막창|곱창|삼겹|찌개|냉면|쌀국수|족발|보쌈/],
  ["생활", /생활|청소|세탁|인테리어|가구|이사|렌탈|자동차|세차|학원|교육/],
];

export function inferCategory(text: string, badges: string[] = []): string {
  for (const b of badges) {
    if (b === "맛집") return "맛집";
    if (b === "뷰티") return "뷰티";
    if (b === "여행" || b === "숙박") return "숙박·여행";
    if (b === "식품") return "식품";
    if (b === "반려동물") return "반려";
  }
  for (const [cat, re] of CATEGORY_RULES) if (re.test(text)) return cat;
  return "기타";
}

export function parseRegion(regionText: string | null | undefined) {
  if (!regionText) return { sido: null as string | null, sigungu: null as string | null };
  const parts = regionText.trim().split(/\s+/);
  const first = SIDO_ALIASES[parts[0]] ?? parts[0];
  if ((SIDO as readonly string[]).includes(first)) {
    return { sido: first, sigungu: parts[1] ?? null };
  }
  return { sido: null, sigungu: parts[0] ?? null };
}

export function inferType(raw: RawCampaign): string | null {
  const t = `${raw.title} ${(raw.badges ?? []).join(" ")} ${raw.regionText ?? ""}`;
  if (/기자단/.test(t)) return "기자단";
  if (/구매평|구매형|페이백/.test(t)) return "구매평";
  if (/배송|택배/.test(t)) return "배송형";
  if (raw.regionText && raw.regionText.trim()) return "방문형";
  return null;
}

/** Today's calendar date in a given IANA timezone, as YYYY-MM-DD. */
export function todayIn(tz = "Asia/Seoul", base = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(base);
}

export function addDays(ymd: string, days: number): string {
  const d = new Date(`${ymd}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function cleanText(s: string | null | undefined): string | null {
  if (!s) return null;
  const v = s.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#0?39;/g, "'")
    .replace(/\*\*/g, "").replace(/\s+/g, " ").trim();
  return v || null;
}

export function dedupeKey(title: string, region: string | null) {
  const norm = (s: string) => s.replace(/\[[^\]]*\]/g, "").replace(/[^\p{L}\p{N}]/gu, "").toLowerCase();
  return `${norm(region ?? "")}|${norm(title)}`;
}

export function normalizeCampaign(raw: RawCampaign) {
  const tz = raw.timezone ?? "Asia/Seoul";
  const today = todayIn(tz);
  const region = parseRegion(raw.regionText);
  const title = cleanText(raw.title) ?? "(제목 없음)";
  const description = cleanText(raw.description);
  const deadline = raw.exactDeadline ?? (raw.daysLeft != null ? addDays(today, raw.daysLeft) : null);
  const category = inferCategory(`${title} ${description ?? ""}`, raw.badges);
  const slots = raw.slots != null && raw.slots >= 0 ? raw.slots : null;
  const applicants = raw.applicants != null && raw.applicants >= 0 ? raw.applicants : null;
  return {
    id: `${raw.sourceId}:${raw.externalId}`,
    source_id: raw.sourceId,
    external_id: raw.externalId,
    original_url: raw.url,
    title,
    description,
    benefit: cleanText(raw.benefit) ?? description,
    image_url: raw.imageUrl ?? null,
    country_code: raw.countryCode ?? "KR",
    region_sido: region.sido,
    region_sigungu: region.sigungu,
    region_text: cleanText(raw.regionText),
    city: region.sigungu,
    language: raw.language ?? "ko",
    original_currency: raw.currency ?? "KRW",
    timezone: tz,
    category,
    campaign_type: inferType(raw),
    channels: raw.channels ?? [],
    slots,
    applicants,
    apply_deadline: deadline,
    deadline_precision: raw.exactDeadline ? "exact" : "days_left",
    last_seen_at: new Date().toISOString(),
    is_active: true,
    dedupe_key: dedupeKey(title, cleanText(raw.regionText)),
    search_text: [title, description, raw.regionText, category, ...(raw.channels ?? [])]
      .filter(Boolean).join(" ").toLowerCase(),
  };
}

export type NormalizedCampaign = ReturnType<typeof normalizeCampaign>;
