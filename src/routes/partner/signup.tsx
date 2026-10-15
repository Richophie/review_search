import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { supabase } from "@/integrations/supabase/client";

export const Route = createFileRoute("/partner/signup")({ component: PartnerSignup });

type Role = "advertiser" | "creator";
function PartnerSignup() {
  const [role, setRole] = useState<Role>("creator");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage("");
    if (password.length < 8) return setMessage("비밀번호는 최소 8자 이상 입력해 주세요.");
    if (password !== confirm) return setMessage("비밀번호가 일치하지 않아요.");
    if (!agreed) return setMessage("필수 약관을 확인하고 동의해 주세요.");
    setBusy(true);
    try {
      const { error } = await supabase.auth.signUp({
        email: email.trim(), password,
        options: { emailRedirectTo: typeof window !== "undefined" ? `${window.location.origin}/partner/login` : undefined,
          data: { display_name: name.trim(), requested_role: role } },
      });
      if (error) throw error;
      setSuccess(true);
      setMessage("이메일 인증 안내를 확인해 주세요. 인증 후 로그인할 수 있습니다.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "가입 요청을 처리하지 못했어요.");
    } finally { setBusy(false); }
  }

  return <div className="mx-auto max-w-lg px-4 py-12">
    <div className="mb-6"><Link to="/partner" className="text-sm text-muted-foreground hover:text-foreground">← 파트너 홈</Link>
      <h1 className="mt-4 text-3xl font-extrabold">무료 회원가입</h1>
      <p className="mt-2 text-sm text-muted-foreground">광고주와 크리에이터를 위한 별도 계정 등록입니다.</p></div>
    <form onSubmit={submit} className="space-y-5 rounded-2xl border border-border bg-card p-6">
      <fieldset><legend className="mb-2 text-sm font-semibold">가입 유형</legend>
        <div className="grid grid-cols-2 gap-2">
          {([{id:"creator",label:"블로거·크리에이터"},{id:"advertiser",label:"광고주"}] as const).map(x=><button type="button" key={x.id} onClick={()=>setRole(x.id)} aria-pressed={role===x.id} className={`rounded-xl border px-3 py-3 text-sm font-semibold ${role===x.id?"border-primary bg-primary-soft text-primary":"border-border"}`}>{x.label}</button>)}
        </div>
      </fieldset>
      <label className="block text-sm font-semibold">이름 또는 닉네임<input required maxLength={60} value={name} onChange={e=>setName(e.target.value)} className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3" placeholder="표시할 이름"/></label>
      <label className="block text-sm font-semibold">이메일<input required type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3" placeholder="example@email.com"/></label>
      <label className="block text-sm font-semibold">비밀번호<input required minLength={8} type="password" autoComplete="new-password" value={password} onChange={e=>setPassword(e.target.value)} className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3" /></label>
      <label className="block text-sm font-semibold">비밀번호 확인<input required type="password" autoComplete="new-password" value={confirm} onChange={e=>setConfirm(e.target.value)} className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3" /></label>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={agreed} onChange={e=>setAgreed(e.target.checked)} className="mt-1" /><span><Link to="/privacy" className="underline">개인정보 처리방침</Link> 및 서비스 이용 관련 필수 안내를 확인했습니다. <span className="text-muted-foreground">(실서비스 개시 전 별도 가입 약관 확정 필요)</span></span></label>
      {message && <p role="status" className={`rounded-lg px-3 py-2 text-sm ${success?"bg-primary-soft text-foreground":"bg-muted text-foreground"}`}>{message}</p>}
      <button disabled={busy||success} type="submit" className="h-12 w-full rounded-xl bg-primary font-bold text-primary-foreground disabled:opacity-50">{busy?"가입 요청 중…":"무료 가입하기"}</button>
      <p className="text-center text-sm text-muted-foreground">이미 계정이 있나요? <Link to="/partner/login" className="font-semibold text-primary underline">로그인</Link></p>
    </form>
    <p className="mt-4 text-xs leading-5 text-muted-foreground">이메일 인증 여부는 연결된 Supabase Auth 설정에 따릅니다. 광고주 인증과 캠페인 운영 기능은 별도 개발 단계입니다.</p>
  </div>;
}
