import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { supabase } from "@/integrations/supabase/client";

export const Route = createFileRoute("/partner/login")({ component: PartnerLogin });

function PartnerLogin() {
  const [email,setEmail] = useState("");
  const [password,setPassword] = useState("");
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState("");
  const [signedIn,setSignedIn] = useState(false);
  async function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();setBusy(true);setMessage("");
    try {
      const {error}=await supabase.auth.signInWithPassword({email:email.trim(),password});
      if(error) throw error;
      setSignedIn(true);
      setMessage("로그인되었습니다. 캠페인 관리 기능은 현재 준비 중입니다.");
    } catch(error) {setMessage(error instanceof Error?error.message:"로그인에 실패했어요.");}
    finally {setBusy(false);}
  }
  async function signOut() {
    setBusy(true); const {error}=await supabase.auth.signOut();
    setBusy(false);
    if(error) setMessage(error.message); else {setSignedIn(false);setMessage("로그아웃되었습니다.");}
  }
  return <div className="mx-auto max-w-md px-4 py-12">
    <Link to="/partner" className="text-sm text-muted-foreground">← 파트너 홈</Link>
    <h1 className="mt-5 text-3xl font-extrabold">로그인</h1>
    <p className="mt-2 text-sm text-muted-foreground">체험모아 파트너 계정으로 로그인해요.</p>
    <form onSubmit={submit} className="mt-6 space-y-5 rounded-2xl border border-border bg-card p-6">
      <label className="block text-sm font-semibold">이메일<input required type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3"/></label>
      <label className="block text-sm font-semibold">비밀번호<input required type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3"/></label>
      {message&&<p role="status" className="rounded-lg bg-muted p-3 text-sm">{message}</p>}
      <button disabled={busy} className="h-12 w-full rounded-xl bg-primary font-bold text-primary-foreground disabled:opacity-50" type="submit">{busy?"처리 중…":"로그인"}</button>
      {signedIn&&<button disabled={busy} onClick={signOut} type="button" className="h-10 w-full rounded-xl border border-border text-sm">로그아웃</button>}
      <p className="text-center text-sm text-muted-foreground">계정이 없나요? <Link to="/partner/signup" className="font-semibold text-primary underline">무료 가입</Link></p>
    </form>
  </div>;
}
