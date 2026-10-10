import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "개인정보처리방침 — 체험단 모아보기" },
      { name: "description", content: "체험단 모아보기는 회원가입이 없으며 이용자의 개인정보를 수집하지 않습니다." },
      { property: "og:title", content: "개인정보처리방침 — 체험단 모아보기" },
      { property: "og:description", content: "회원가입 없음, 개인정보 수집 없음." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: () => (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-10 text-sm leading-relaxed text-secondary-foreground">
      <h1 className="text-2xl font-bold text-foreground">개인정보처리방침</h1>
      <p>체험단 모아보기는 회원가입·로그인 기능이 없으며, 이름·연락처·SNS 계정 등 이용자의 개인정보를 수집·저장하지 않습니다.</p>
      <p>수집하는 데이터는 각 체험단 사이트에 공개된 캠페인 공고 정보(제목, 지역, 모집 인원, 신청자 수, 마감일, 원문 링크)뿐입니다.</p>
      <p>원본 사이트로 이동한 이후의 개인정보 처리는 해당 사이트의 방침을 따릅니다.</p>
      <p>공고 노출 중단 요청은 서비스 운영자에게 문의해 주세요.</p>
    </div>
  ),
});
