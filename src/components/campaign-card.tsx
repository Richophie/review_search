import { todayIn } from "@/lib/collector/normalize";

export type CampaignItem = {
  id: string; source_id: string; original_url: string; title: string; description: string | null; benefit: string | null;
  image_url: string | null; country_code: string; region_text: string | null; category: string; campaign_type: string | null;
  channels: string[]; slots: number | null; applicants: number | null; apply_deadline: string | null;
  deadline_precision: string | null; last_seen_at: string; timezone: string; competition_ratio: number | null;
  related: { source_id: string; original_url: string }[];
};
type Src = { id: string; name: string };

function dday(deadline: string | null, tz: string, today: string) {
  if (!deadline) return { label: "마감일 미상", urgent: false };
  const t = tz === "Asia/Seoul" ? today : todayIn(tz);
  const diff = Math.round((Date.parse(deadline) - Date.parse(t)) / 86_400_000);
  if (diff === 0) return { label: "오늘 마감", urgent: true };
  return { label: `D-${diff}`, urgent: diff <= 3 };
}

function ratio(c: CampaignItem) {
  if (c.competition_ratio == null) return "미공개";
  return `${Number(c.competition_ratio).toFixed(1)} : 1`;
}

function updated(iso: string) {
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

function Meta({ c, srcName }: { c: CampaignItem; srcName: string }) {
  return (
    <div className="flex flex-wrap gap-1 text-[11px]">
      <span className="rounded bg-primary-soft px-1.5 py-0.5 font-semibold text-accent-foreground">{srcName}</span>
      <span className="rounded bg-muted px-1.5 py-0.5 text-muted-foreground">{c.category}</span>
      {c.campaign_type && <span className="rounded bg-muted px-1.5 py-0.5 text-muted-foreground">{c.campaign_type}</span>}
      {c.channels.map((ch) => <span key={ch} className="rounded bg-muted px-1.5 py-0.5 text-muted-foreground">{ch}</span>)}
    </div>
  );
}

function Stats({ c }: { c: CampaignItem }) {
  return (
    <dl className="grid grid-cols-3 gap-2 text-xs">
      <div><dt className="text-muted-foreground">모집</dt><dd className="font-semibold">{c.slots != null && c.slots > 0 ? `${c.slots}명` : "미공개"}</dd></div>
      <div><dt className="text-muted-foreground">신청</dt><dd className="font-semibold">{c.applicants != null ? `${c.applicants}명` : "미공개"}</dd></div>
      <div><dt className="text-muted-foreground">경쟁률</dt><dd className="font-semibold">{ratio(c)}</dd></div>
    </dl>
  );
}

export function CampaignCard({ c, today, sources }: { c: CampaignItem; today: string; sources: Src[] }) {
  const d = dday(c.apply_deadline, c.timezone, today);
  const name = (id: string) => sources.find((s) => s.id === id)?.name ?? id;
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-card">
      <div className="relative aspect-[16/9] bg-muted">
        {c.image_url && <img src={c.image_url} alt="" loading="lazy" className="h-full w-full object-cover" referrerPolicy="no-referrer" />}
        <span className={`absolute left-2 top-2 rounded-md px-2 py-0.5 text-xs font-bold ${d.urgent ? "bg-urgent text-primary-foreground" : "bg-card text-foreground"}`}>
          {d.label}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3.5">
        <Meta c={c} srcName={name(c.source_id)} />
        <h3 className="line-clamp-2 font-semibold leading-snug">{c.title}</h3>
        <p className="text-xs text-muted-foreground">{c.region_text ?? (c.country_code === "KR" ? "지역 무관 / 미기재" : c.country_code)}</p>
        {c.benefit && <p className="line-clamp-2 text-sm text-secondary-foreground">{c.benefit}</p>}
        <div className="mt-auto space-y-2.5 pt-1">
          <Stats c={c} />
          {c.related.length > 0 && (
            <p className="text-[11px] text-muted-foreground">
              다른 사이트에도 비슷한 공고: {c.related.map((r) => (
                <a key={r.original_url} href={r.original_url} target="_blank" rel="noopener noreferrer" className="underline">{name(r.source_id)}</a>
              ))}
            </p>
          )}
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              신청마감 {c.apply_deadline?.slice(5).replace("-", ".")}{c.deadline_precision === "days_left" ? " (남은 일수 기준)" : ""} · 갱신 {updated(c.last_seen_at)}
            </span>
            <a href={c.original_url} target="_blank" rel="noopener noreferrer"
              className="shrink-0 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90"
              aria-label={`${name(c.source_id)}에서 ${c.title} 원본 공고 보기`}>
              원본 보기 ↗
            </a>
          </div>
        </div>
      </div>
    </article>
  );
}

export function CampaignRow({ c, today, sources }: { c: CampaignItem; today: string; sources: Src[] }) {
  const d = dday(c.apply_deadline, c.timezone, today);
  const name = sources.find((s) => s.id === c.source_id)?.name ?? c.source_id;
  return (
    <article className="flex gap-3 p-3">
      <div className="h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-muted">
        {c.image_url && <img src={c.image_url} alt="" loading="lazy" className="h-full w-full object-cover" referrerPolicy="no-referrer" />}
      </div>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold ${d.urgent ? "text-urgent" : "text-foreground"}`}>{d.label}</span>
          <Meta c={c} srcName={name} />
        </div>
        <h3 className="truncate font-semibold">{c.title}</h3>
        <p className="truncate text-xs text-muted-foreground">
          {c.region_text ?? "지역 무관 / 미기재"} · 모집 {c.slots ?? "미공개"} · 신청 {c.applicants ?? "미공개"} · 경쟁률 {ratio(c)}
        </p>
        {c.benefit && <p className="truncate text-xs text-secondary-foreground">{c.benefit}</p>}
      </div>
      <a href={c.original_url} target="_blank" rel="noopener noreferrer" aria-label={`${name}에서 ${c.title} 원본 공고 보기`}
        className="self-center shrink-0 rounded-lg border border-primary px-3 py-2 text-xs font-semibold text-primary">원본 ↗</a>
    </article>
  );
}
