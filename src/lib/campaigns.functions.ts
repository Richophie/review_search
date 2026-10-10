import { createServerFn } from "@tanstack/react-start";
import { createClient } from "@supabase/supabase-js";
import type { Database } from "@/integrations/supabase/types";
import { searchSchema, type SearchParams } from "./search-params";
import { todayIn, addDays } from "./collector/normalize";
import { searchCollected } from "./collected-search";

export const PAGE_SIZE = 24;

function publicClient() {
  const key = process.env["SUPABASE_PUBLISHABLE_KEY"]!;
  return createClient<Database>(process.env["SUPABASE_URL"]!, key, {
    auth: { persistSession: false, autoRefreshToken: false, storage: undefined },
    global: {
      fetch: (input, init) => {
        const h = new Headers(init?.headers);
        if (key.startsWith("sb_") && h.get("Authorization") === `Bearer ${key}`) h.delete("Authorization");
        h.set("apikey", key);
        return fetch(input, { ...init, headers: h });
      },
    },
  });
}

/** Split into AND terms; "quoted phrases" stay together. */
function terms(q?: string) {
  if (!q) return [];
  const out: string[] = [];
  const re = /"([^"]+)"|(\S+)/g;
  let m;
  while ((m = re.exec(q))) out.push((m[1] ?? m[2]).toLowerCase().replace(/[%_,()\\]/g, ""));
  return out.filter(Boolean).slice(0, 8);
}

const COLS = "id,source_id,original_url,title,description,benefit,image_url,country_code,region_text,region_sido,category,campaign_type,channels,slots,applicants,apply_deadline,deadline_precision,first_seen_at,last_seen_at,timezone,competition_ratio,remaining_slots,dedupe_key";

export const searchCampaigns = createServerFn({ method: "GET" })
  .inputValidator((d: unknown) => searchSchema.parse(d))
  .handler(async ({ data: p }) => {
    // Prefer the real-source public snapshot once collection has succeeded.
    const collected = searchCollected(p);
    if (collected) return collected;
    const db = publicClient();
    const today = todayIn("Asia/Seoul");
    // Seoul midnight as UTC instant for "오늘 올라옴"
    const todayStartUtc = new Date(`${today}T00:00:00+09:00`).toISOString();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const base = (sel: string, head = false): any => {
      let q = db.from("campaigns").select(sel, { count: "exact", head }).eq("is_active", true).gte("apply_deadline", today);
      if (p.country === "INTL") q = q.neq("country_code", "KR");
      else q = q.eq("country_code", "KR");
      for (const t of terms(p.q)) q = q.ilike("search_text", `%${t}%`);
      if (p.sido) q = q.or(`region_sido.eq.${p.sido},region_text.ilike.%${p.sido.replace(/[,()%]/g, "")}%`);
      if (p.sigungu) q = q.ilike("region_text", `%${p.sigungu.replace(/[,()%]/g, "")}%`);
      if (p.cat) q = q.eq("category", p.cat);
      if (p.type) q = q.eq("campaign_type", p.type);
      if (p.ch) q = q.contains("channels", [p.ch]);
      return q;
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const applyTab = (q: any, tab: SearchParams["tab"]) => {
      switch (tab) {
        case "new": return q.gte("first_seen_at", todayStartUtc);
        case "today": return q.eq("apply_deadline", today);
        case "soon": return q.lte("apply_deadline", addDays(today, 3));
        case "lowcomp": return q.lt("competition_ratio", 1); // only known applicants & slots>0
        case "zero": return q.eq("applicants", 0).gt("slots", 0);
        default: return q;
      }
    };

    const page = p.page ?? 1;
    let q = applyTab(base(COLS), p.tab);
    switch (p.sort) {
      case "deadline": q = q.order("apply_deadline", { ascending: true }).order("first_seen_at", { ascending: false }); break;
      case "ratio": q = q.order("competition_ratio", { ascending: true, nullsFirst: false }); break;
      case "remaining": q = q.order("remaining_slots", { ascending: false, nullsFirst: false }); break;
      default: q = q.order("first_seen_at", { ascending: false }).order("id");
    }
    q = q.range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);

    const tabs = ["all", "new", "today", "soon", "lowcomp", "zero"] as const;
    const [res, allCount, sources, ...counts] = await Promise.all([
      q,
      db.from("campaigns").select("id", { count: "exact", head: true }).eq("is_active", true).gte("apply_deadline", today)[p.country === "INTL" ? "neq" : "eq"]("country_code", "KR"),
      db.from("sources").select("id,name,homepage_url,status,status_note,last_success_at,country_code").order("name"),
      ...tabs.map((t) => applyTab(base("id", true), t)),
    ]);
    if (res.error) {
      console.error(res.error);
      return { items: [], total: 0, globalTotal: 0, tabCounts: null, sources: sources.data ?? [], error: "검색 중 오류가 발생했어요." };
    }
    type Row = Database["public"]["Tables"]["campaigns"]["Row"];
    const items = (res.data ?? []) as Row[];

    // Cross-platform "possibly same campaign" hints (unique per original URL; never merged)
    const keys = [...new Set(items.map((i) => i.dedupe_key).filter(Boolean))] as string[];
    const dupMap: Record<string, { source_id: string; original_url: string }[]> = {};
    if (keys.length) {
      const { data: dups } = await db.from("campaigns").select("dedupe_key,source_id,original_url")
        .in("dedupe_key", keys).eq("is_active", true);
      for (const d of dups ?? []) (dupMap[d.dedupe_key!] ??= []).push(d);
    }
    const tabCounts = Object.fromEntries(
      tabs.map((t, i) => [t, (counts[i] as { count: number | null }).count]),
    ) as Record<(typeof tabs)[number], number | null>;

    return {
      items: items.map((i) => ({
        ...i,
        related: (dupMap[i.dedupe_key ?? ""] ?? []).filter((d) => d.original_url !== i.original_url && d.source_id !== i.source_id),
      })),
      total: (counts.find((_, i) => tabs[i] === (p.tab ?? "all")) as { count: number | null } | undefined)?.count ?? 0,
      globalTotal: allCount.count ?? 0,
      tabCounts,
      sources: sources.data ?? [],
      today,
      error: null as string | null,
    };
  });
