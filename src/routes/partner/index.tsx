import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowRight, BriefcaseBusiness, CheckCircle2, ClipboardList, LayoutDashboard, Megaphone, Search, ShieldCheck, Users, X } from "lucide-react";

export const Route = createFileRoute("/partner/")({
  head: () => ({ meta: [
    { title: "무료 체험단 모집 | 체험모아 파트너" },
    { name: "description", content: "광고주와 크리에이터가 만나는 무료 체험단 모집 서비스. 체험모아 파트너를 소개합니다." },
  ] }),
  component: PartnerHome,
});

const advertiserSteps = [
  { number: "01", name: "캠페인 등록", body: "체험 혜택과 모집 조건을 입력해요." },
  { number: "02", name: "지원자 선정", body: "신청자를 확인하고 직접 선정해요." },
  { number: "03", name: "후기 관리", body: "체험 일정과 후기 제출 현황을 확인해요." },
];
const creatorSteps = [
  { number: "01", name: "캠페인 발견", body: "내 지역과 관심사에 맞는 체험을 찾아요." },
  { number: "02", name: "무료 신청", body: "내 채널로 원하는 캠페인에 신청해요." },
  { number: "03", name: "체험과 후기", body: "선정되면 체험한 뒤 진솔한 후기를 남겨요." },
];

function PartnerHome() {
  const [audience, setAudience] = useState<"advertiser" | "creator">("advertiser");
  const steps = audience === "advertiser" ? advertiserSteps : creatorSteps;
  return (
    <div className="mx-auto max-w-6xl px-4 pb-20 text-foreground">
      <div className="flex items-center gap-2 py-5 text-sm text-muted-foreground">
        <Link to="/" className="hover:text-foreground">체험단 통합검색</Link><span aria-hidden="true">/</span><span className="font-semibold text-foreground">무료 체험단 모집</span>
      </div>
      <section className="relative overflow-hidden rounded-3xl border border-border bg-card px-6 py-14 md:px-14 md:py-20">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-primary/5" aria-hidden="true" />
        <div className="relative max-w-2xl">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary"><Megaphone size={14}/> 체험모아 파트너 · 신규 서비스 준비 중</p>
          <h1 className="text-3xl font-extrabold leading-tight tracking-tight md:text-5xl">체험단 모집도, 참여도<br/><span className="text-primary">간편하고 부담 없이.</span></h1>
          <p className="mt-5 max-w-xl break-keep text-base leading-7 text-muted-foreground">광고주와 블로거를 직접 연결하는 무료 체험단 플랫폼을 만들고 있어요. 기존 통합검색 서비스는 그대로 이용할 수 있습니다.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-primary-foreground hover:opacity-90">현재 모집 중인 체험단 찾기 <ArrowRight size={16}/></Link>
            <a href="#how-it-works" className="inline-flex min-h-11 items-center justify-center rounded-xl border border-border bg-card px-5 py-3 text-sm font-semibold hover:bg-muted">서비스 이용 방법</a>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">현재는 사전 안내 페이지이며, 회원가입과 자체 캠페인 신청은 개발 중입니다.</p>
        </div>
      </section>
      <section className="grid gap-4 py-10 md:grid-cols-3" aria-label="서비스 주요 특징">
        {[
          { icon: Megaphone, title: "광고주 무료 모집", body: "광고비 없이 체험단을 모집할 수 있는 기능을 준비하고 있어요." },
          { icon: Users, title: "블로거 무료 신청", body: "관심 있는 캠페인을 찾아 직접 신청하는 기능을 준비하고 있어요." },
          { icon: LayoutDashboard, title: "하나로 관리", body: "선정부터 일정, 후기 제출까지 간편하게 관리할 수 있도록 설계합니다." },
        ].map((item) => <article key={item.title} className="rounded-2xl border border-border bg-card p-6">
          <item.icon className="mb-4 text-primary" size={24}/><h2 className="font-bold">{item.title}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{item.body}</p>
        </article>)}
      </section>
      <section id="how-it-works" className="scroll-mt-8 rounded-3xl bg-muted/60 px-5 py-9 md:px-10 md:py-12">
        <div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-bold text-primary">HOW IT WORKS</p><h2 className="mt-1 text-2xl font-extrabold">이렇게 이용할 수 있어요</h2></div>
          <div className="inline-flex rounded-xl border border-border bg-card p-1" role="group" aria-label="이용자 유형">
            <button type="button" onClick={() => setAudience("advertiser")} aria-pressed={audience === "advertiser"} className={`rounded-lg px-4 py-2 text-sm font-semibold ${audience === "advertiser" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>광고주</button>
            <button type="button" onClick={() => setAudience("creator")} aria-pressed={audience === "creator"} className={`rounded-lg px-4 py-2 text-sm font-semibold ${audience === "creator" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>블로거</button>
          </div></div>
        <div className="mt-6 grid gap-3 md:grid-cols-3">{steps.map((s) => <div className="rounded-xl border border-border bg-card p-5" key={s.number}><span className="text-sm font-bold text-primary">{s.number}</span><h3 className="mt-3 font-bold">{s.name}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{s.body}</p></div>)}</div>
      </section>
      <section className="mt-12 grid gap-5 md:grid-cols-2">
        <div className="rounded-2xl border border-border bg-card p-7"><BriefcaseBusiness className="text-primary" size={24}/><h2 className="mt-4 text-xl font-bold">가게와 브랜드를 운영한다면</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">캠페인을 등록하고, 신청자를 직접 선정하며 후기를 관리할 수 있는 기능이 추가될 예정이에요.</p><p className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground"><ClipboardList size={16}/> 광고주 전용 관리 페이지 준비 중</p></div>
        <div className="rounded-2xl border border-border bg-card p-7"><Search className="text-primary" size={24}/><h2 className="mt-4 text-xl font-bold">블로그나 SNS를 운영한다면</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">기존 체험단 통합검색에서 다양한 플랫폼의 공고를 지금 바로 찾아볼 수 있어요.</p><Link to="/" className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-primary">통합검색 이용하기 <ArrowRight size={16}/></Link></div>
      </section>
      <section className="mt-10 rounded-2xl border border-border bg-card p-6"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 shrink-0 text-primary" size={22}/><div><h2 className="font-bold">솔직한 후기와 투명한 광고 표시</h2><p className="mt-1 text-sm leading-6 text-muted-foreground">체험 후기에는 경제적 이해관계를 명확히 표시해야 합니다. 좋은 평가나 특정 별점을 강요하지 않는 운영 원칙을 적용할 예정입니다.</p></div></div></section>
      <p className="mt-8 text-center text-xs text-muted-foreground">이 페이지는 신규 서비스 소개용 첫 버전입니다. 가입·모집·신청·관리 기능은 아직 제공하지 않습니다.</p>
    </div>
  );
}
