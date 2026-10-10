import { z } from "zod";

export const TABS = ["all", "new", "today", "soon", "lowcomp", "zero"] as const;
export const SORTS = ["latest", "deadline", "ratio", "remaining"] as const;

export const searchSchema = z.object({
  q: z.string().max(100).optional().catch(undefined),
  country: z.enum(["KR", "INTL"]).optional().catch(undefined),
  sido: z.string().max(10).optional().catch(undefined),
  sigungu: z.string().max(20).optional().catch(undefined),
  cat: z.string().max(10).optional().catch(undefined),
  type: z.string().max(10).optional().catch(undefined),
  ch: z.string().max(10).optional().catch(undefined),
  tab: z.enum(TABS).optional().catch(undefined),
  sort: z.enum(SORTS).optional().catch(undefined),
  view: z.enum(["card", "list"]).optional().catch(undefined),
  page: z.number().int().min(1).max(500).optional().catch(undefined),
});
export type SearchParams = z.infer<typeof searchSchema>;

export const TAB_LABELS: Record<(typeof TABS)[number], string> = {
  all: "전체", new: "오늘 올라옴", today: "오늘 마감", soon: "마감 임박 D-3",
  lowcomp: "경쟁 낮음", zero: "신청자 0명",
};
export const SORT_LABELS: Record<(typeof SORTS)[number], string> = {
  latest: "최신순", deadline: "마감 임박순", ratio: "경쟁률 낮은 순", remaining: "잔여 인원 많은 순",
};
export const CAMPAIGN_TYPES = ["방문형", "배송형", "기자단", "구매평"];
export const CHANNELS = ["블로그", "인스타그램", "유튜브", "쇼츠", "네이버클립", "틱톡"];
