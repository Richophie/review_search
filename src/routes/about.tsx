import { createFileRoute } from "@tanstack/react-router";
import { queryOptions, useSuspenseQuery } from "@tanstack/react-query";
import { searchCampaigns } from "@/lib/campaigns.functions";

const q = queryOptions({ queryKey: ["search", {}], queryFn: () => searchCampaigns({ data: {} }) });

export const Route = createFileRoute("/about")({
  loader: ({ context }) => context.queryClient.ensureQueryData(q),
  head: () => ({
    meta: [
      { title: "서비스 안내·데이터 출처 — 체험단 모아보기" },
      { name: "description", content: "체험단 모아보기의 이용 안내와 연결된 원본 체험단 사이트, 수집 상태를 확인하세요." },
      { property: "og:title", content: "서비스 안내·데이터 출처 — 체험단 모아보기" },
      { property: "og:description", content: "연결된 원본 사이트와 최근 수집 상태를 공개합니다." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: About,
});

const STATUS: Record<string, string> = { connected: "연동됨", not_connected: "미연동", blocked: "수집 불가" };

function About() {
  const { data } = useSuspenseQuery(q);
  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-10">
      <section>
        <h1 className="text-2xl font-bold">서비스 안내</h1>
        <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-secondary-foreground">
          <li>로그인 없이 무료로 누구나 사용할 수 있는 체험단 공고 통합 검색 서비스입니다.</li>
          <li>각 사이트의 공개 목록 페이지만 이용약관·robots.txt 범위에서 읽어옵니다. 로그인·CAPTCHA·차단을 우회하지 않습니다.</li>
          <li>신청·선정·리뷰는 모두 원본 사이트에서 진행됩니다. 이 서비스는 신청을 대행하지 않습니다.</li>
          <li>마감일은 <strong>신청 모집 마감일</strong> 기준이며(선정 발표일 아님), 한국 공고는 한국 시간(Asia/Seoul)으로 계산합니다. 목록에 "N일 남음"만 표시하는 사이트는 수집 시점 기준으로 날짜를 계산하므로 하루 정도 차이가 날 수 있어요.</li>
          <li>신청자 수나 모집 인원이 공개되지 않으면 경쟁률은 "미공개"로 표시합니다.</li>
        </ul>
      </section>
      <section>
        <h2 className="text-xl font-bold">데이터 출처와 수집 상태</h2>
        <ul className="mt-3 divide-y divide-border rounded-2xl border border-border bg-card">
          {data.sources.map((s) => (
            <li key={s.id} className="flex flex-col gap-1 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <a href={s.homepage_url} target="_blank" rel="noopener noreferrer" className="font-semibold underline-offset-2 hover:underline">{s.name}</a>
                <p className="text-xs text-muted-foreground">{s.status_note}</p>
              </div>
              <div className="text-right text-xs">
                <span className={`rounded-full px-2 py-0.5 font-semibold ${s.status === "connected" ? "bg-primary-soft text-accent-foreground" : "bg-muted text-muted-foreground"}`}>
                  {STATUS[s.status] ?? s.status}
                </span>
                {s.last_success_at && (
                  <p className="mt-1 text-muted-foreground">
                    최근 수집 {new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "short", timeStyle: "short" }).format(new Date(s.last_success_at))}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-muted-foreground">해외(예: 베트남) 원본 소스는 아직 연결되지 않았어요.</p>
      </section>
    </div>
  );
}
