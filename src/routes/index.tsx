import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { queryOptions, useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { searchCampaigns, PAGE_SIZE } from "@/lib/campaigns.functions";
import {
  searchSchema, type SearchParams, TABS, TAB_LABELS, SORTS, SORT_LABELS, CAMPAIGN_TYPES, CHANNELS,
} from "@/lib/search-params";
import { SIDO, CATEGORIES } from "@/lib/collector/normalize";
import { CampaignCard, CampaignRow, type CampaignItem } from "@/components/campaign-card";

const searchQuery = (p: SearchParams) =>
  queryOptions({ queryKey: ["search", p], queryFn: () => searchCampaigns({ data: p }), staleTime: 60_000 });

export const Route = createFileRoute("/")({
  validateSearch: searchSchema,
  loaderDeps: ({ search }) => search,
  loader: ({ context, deps }) => context.queryClient.ensureQueryData(searchQuery(deps)),
  head: () => ({
    meta: [
      { title: "체험단 모아보기 — 전국 체험단 공고 통합 검색" },
      { name: "description", content: "디너의여왕·미블 등 여러 체험단 사이트의 모집 중 공고를 키워드·지역·분야로 한 번에 검색하고, 오늘 마감·경쟁 낮은 공고를 찾아보세요." },
      { property: "og:title", content: "체험단 모아보기 — 전국 체험단 공고 통합 검색" },
      { property: "og:description", content: "여러 체험단 사이트의 모집 중 공고를 한 번에. 오늘 마감, 신청 유리 공고 필터 제공." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const selectCls = "h-10 rounded-lg border border-input bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

function Index() {
  const p = Route.useSearch();
  const navigate = useNavigate({ from: "/" });
  const { data } = useSuspenseQuery(searchQuery(p));
  const [q, setQ] = useState(p.q ?? "");
  const [showFilters, setShowFilters] = useState(false);
  useEffect(() => setQ(p.q ?? ""), [p.q]);

  const set = (patch: Partial<SearchParams>) =>
    navigate({ search: (prev) => {
      const next = { ...prev, ...patch, page: patch.page };
      for (const k of Object.keys(next) as (keyof SearchParams)[]) if (next[k] === "" || next[k] === undefined) delete next[k];
      return next;
    } });

  const connected = data.sources.filter((s) => s.status === "connected" && s.country_code === "KR");
  const lastUpdate = connected.map((s) => s.last_success_at).filter(Boolean).sort().at(-1);
  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const page = p.page ?? 1;
  const view = p.view ?? "card";
  const activeFilters = !!(p.q || p.sido || p.sigungu || p.cat || p.type || p.ch || p.country);
  const intlSources = data.sources.filter((s) => s.country_code !== "KR" && s.status === "connected");

  return (
    <div className="mx-auto max-w-6xl px-4 pb-16">
      <section className="py-6 md:py-10">
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">
          현재 <span className="text-primary tabular-nums">{(data.globalTotal ?? data.total).toLocaleString()}</span>개의 체험이 있어요!
        </h1>
        <p className="mt-2 text-base font-semibold text-foreground md:text-lg">
          <span className="text-primary tabular-nums">{connected.length}</span>개 플랫폼을 한꺼번에 찾아 드릴게요.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          실제 수집된 모집 중 공고 기준 · 중복 원본 링크 제외 · 신청은 각 원본 사이트에서 진행해요.
        </p>
        <form
          role="search"
          className="mt-5 flex flex-col gap-2 rounded-2xl border border-border bg-card p-2 shadow-card md:flex-row"
          onSubmit={(e) => { e.preventDefault(); set({ q: q.trim() || undefined }); }}
        >
          <label htmlFor="q" className="sr-only">검색어</label>
          <input
            id="q" value={q} onChange={(e) => setQ(e.target.value)}
            placeholder='예: 인천 검단 맛집, "속눈썹 펌"'
            className="h-12 flex-1 rounded-xl bg-transparent px-3 text-base outline-none placeholder:text-muted-foreground"
          />
          <div className="flex gap-2">
            <label htmlFor="sido" className="sr-only">시/도</label>
            <select id="sido" className={`${selectCls} h-12 flex-1 md:w-32`} value={p.sido ?? ""}
              onChange={(e) => set({ sido: e.target.value || undefined, sigungu: undefined })}>
              <option value="">전국</option>
              {SIDO.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <button type="submit" className="h-12 rounded-xl bg-primary px-6 font-semibold text-primary-foreground hover:opacity-90">
              검색
            </button>
          </div>
        </form>
        <p className="mt-2 text-xs text-muted-foreground">띄어쓰기는 모든 단어 포함(AND), 따옴표는 문구 그대로 검색해요.</p>
      </section>

      {/* Filters */}
      <section aria-label="필터" className="rounded-2xl border border-border bg-card p-3">
        <div className="flex items-center justify-between md:hidden">
          <button className="text-sm font-medium" onClick={() => setShowFilters((v) => !v)} aria-expanded={showFilters}>
            상세 필터 {showFilters ? "접기" : "열기"}
          </button>
          {activeFilters && <Link to="/" className="text-sm text-primary">초기화</Link>}
        </div>
        <div className={`${showFilters ? "grid" : "hidden"} mt-3 grid-cols-2 gap-2 md:mt-0 md:grid md:grid-cols-6`}>
          <Select label="국가" value={p.country ?? "KR"} onChange={(v) => set({ country: v === "KR" ? undefined : (v as "INTL") })}
            options={[["KR", "대한민국"], ["INTL", intlSources.length ? "해외" : "해외 (준비 중)"]]} />
          <label className="sr-only" htmlFor="sigungu">시군구·동</label>
          <input id="sigungu" placeholder="시군구·동 (입력 후 Enter)" defaultValue={p.sigungu ?? ""} key={p.sigungu ?? ""}
            onBlur={(e) => { const value = e.currentTarget.value.trim(); if(value !== (p.sigungu ?? "")) set({ sigungu: value || undefined }); }}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); (e.currentTarget as HTMLInputElement).blur(); } }}
            className={selectCls} />
          <Select label="분야" value={p.cat ?? ""} onChange={(v) => set({ cat: v || undefined })}
            options={[["", "분야 전체"], ...CATEGORIES.map((c) => [c, c] as [string, string])]} />
          <Select label="유형" value={p.type ?? ""} onChange={(v) => set({ type: v || undefined })}
            options={[["", "유형 전체"], ...CAMPAIGN_TYPES.map((c) => [c, c] as [string, string])]} />
          <Select label="SNS 매체" value={p.ch ?? ""} onChange={(v) => set({ ch: v || undefined })}
            options={[["", "매체 전체"], ...CHANNELS.map((c) => [c, c] as [string, string])]} />
          <Link to="/" className="hidden h-10 items-center justify-center rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground md:flex">
            초기화
          </Link>
        </div>
      </section>

      {/* Tabs */}
      <nav aria-label="빠른 탭" className="-mx-4 mt-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {TABS.map((t) => {
          const active = (p.tab ?? "all") === t;
          const n = data.tabCounts?.[t];
          return (
            <button key={t} onClick={() => set({ tab: t === "all" ? undefined : t })} aria-pressed={active}
              className={`shrink-0 rounded-full border px-3.5 py-1.5 text-sm transition ${active ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-foreground hover:border-primary"}`}>
              {TAB_LABELS[t]}
              {typeof n === "number" && <span className={`ml-1.5 text-xs ${active ? "opacity-90" : "text-muted-foreground"}`}>{n.toLocaleString()}</span>}
            </button>
          );
        })}
      </nav>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
        <p className="text-muted-foreground">
          <strong className="text-foreground">{data.total.toLocaleString()}</strong>건 · 연결된 출처 {connected.map((s) => s.name + " (" + ("record_count" in s && typeof s.record_count === "number" ? s.record_count.toLocaleString() + "건" : "집계 전") + ")").join(", ") || "없음"}
          {lastUpdate && <> · 최근 갱신 {fmtDateTime(lastUpdate)}</>}
        </p>
        <div className="flex items-center gap-2">
          <Select label="정렬" value={p.sort ?? "latest"} onChange={(v) => set({ sort: v === "latest" ? undefined : (v as SearchParams["sort"]) })}
            options={SORTS.map((s) => [s, SORT_LABELS[s]] as [string, string])} />
          <div role="group" aria-label="보기 방식" className="flex rounded-lg border border-border bg-card p-0.5">
            {(["card", "list"] as const).map((v) => (
              <button key={v} aria-pressed={view === v} onClick={() => set({ view: v === "card" ? undefined : v, page: p.page })}
                className={`rounded-md px-2.5 py-1.5 text-xs ${view === v ? "bg-primary-soft font-semibold text-accent-foreground" : "text-muted-foreground"}`}>
                {v === "card" ? "카드" : "리스트"}
              </button>
            ))}
          </div>
        </div>
      </div>
      {(p.sort === "ratio" || p.sort === "remaining" || p.tab === "lowcomp") && (
        <p className="mt-2 text-xs text-muted-foreground">신청자 수 또는 모집 인원이 공개되지 않은 공고는 경쟁률 계산에서 제외되어 맨 뒤에 표시돼요.</p>
      )}

      {data.error && <p className="mt-6 rounded-lg bg-urgent-soft p-4 text-sm text-urgent">{data.error}</p>}

      {data.items.length === 0 ? (
        <EmptyState country={p.country} hasSources={connected.length > 0} filtered={activeFilters || !!p.tab} />
      ) : view === "card" ? (
        <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {data.items.map((c) => <li key={c.id}><CampaignCard c={c as CampaignItem} today={data.today!} sources={data.sources} /></li>)}
        </ul>
      ) : (
        <ul className="mt-4 divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {data.items.map((c) => <li key={c.id}><CampaignRow c={c as CampaignItem} today={data.today!} sources={data.sources} /></li>)}
        </ul>
      )}

      {pages > 1 && (
        <nav aria-label="페이지" className="mt-8 flex items-center justify-center gap-2">
          <button disabled={page <= 1} onClick={() => set({ page: page - 1 > 1 ? page - 1 : undefined })}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm disabled:opacity-40">이전</button>
          <span className="text-sm text-muted-foreground">{page} / {pages}</span>
          <button disabled={page >= pages} onClick={() => set({ page: page + 1 })}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm disabled:opacity-40">다음</button>
        </nav>
      )}
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <select aria-label={label} className={selectCls} value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </select>
  );
}

function EmptyState({ country, hasSources, filtered }: { country?: string; hasSources: boolean; filtered: boolean }) {
  let title = "조건에 맞는 모집 중 공고가 없어요";
  let body = "검색어를 줄이거나 필터를 초기화해 보세요.";
  if (country === "INTL") { title = "해외 공고는 준비 중이에요"; body = "아직 연결된 해외 원본 소스가 없어요. 연결되면 이곳에 현지 공고가 표시됩니다."; }
  else if (!hasSources) { title = "원본 소스 연결이 필요해요"; body = "아직 수집된 공고가 없어요. 가짜 공고는 보여드리지 않아요."; }
  return (
    <div className="mt-6 rounded-2xl border border-dashed border-border bg-card p-10 text-center">
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{body}</p>
      {filtered && <Link to="/" className="mt-4 inline-block text-sm font-medium text-primary">필터 초기화</Link>}
    </div>
  );
}

export function fmtDateTime(iso: string) {
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}