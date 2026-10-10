import type { SearchParams } from "./search-params";
import { todayIn, addDays } from "./collector/normalize";
import archive from "../../public/data/campaigns.json";

type Campaign = {
  id:string; source_id:string; original_url:string; title:string;
  description:string|null; benefit:string|null; image_url:string|null;
  country_code:string; region_sido:string|null; region_text:string|null;
  category:string; campaign_type:string|null; channels:string[];
  slots:number|null; applicants:number|null; apply_deadline:string|null;
  deadline_precision:string; open_verified?:boolean; first_seen_at:string; last_seen_at:string;
  timezone:string; competition_ratio:number|null; remaining_slots:number|null;
  dedupe_key:string; search_text:string;
};
const campaigns = archive as Campaign[];
const PLATFORM: Record<string, [string,string]> = {
  dinnerqueen:["디너의여왕","https://dinnerqueen.net/"],
  mrblog:["미블","https://www.mrblog.net/"],
  modan:["모두의체험단","https://modan.kr/"],
  modootogether:["모두모여체험단","https://www.modootogether.com/"],
  fourblog:["포블로그","https://4blog.net/"],
  assaview:["아싸뷰","https://www.assaview.co.kr/"],
  ringble:["링블","https://www.ringble.co.kr/"],
  cometoplay:["놀러와체험단","https://www.cometoplay.kr/"],
  cherrycook:["체리쿡","https://cherry-cook.com/"],
  gaboja:["가보자체험단","https://xn--o39a04kpnjo4k9hgflp.com/"],
  bqueens:["뷰티의여왕","https://bqueens.net/"],
  huki:["후키","https://huki.co.kr/"],
  openreview:["오픈리뷰","https://openreview.kr/"],
  pavlovu:["파블로체험단","https://pavlovu.com/"]
};
const TABS = ["all","new","today","soon","lowcomp","zero"] as const;
const DAY_MS = 86400000;
function searchTerms(q?:string) {
  return Array.from((q || "").matchAll(/"([^"]+)"|(\S+)/g))
    .map(m => (m[1] || m[2] || "").toLowerCase()).filter(Boolean).slice(0,8);
}
export function searchCollected(p:SearchParams) {
  if (!campaigns.length) return null;
  const today = todayIn("Asia/Seoul");
  const firstToday = Date.parse(today+"T00:00:00+09:00");
  const cutoff = Date.now()-21*DAY_MS;
  const active = campaigns.filter(c=>c && c.title &&
    c.original_url?.startsWith("https://") &&
    ((c.apply_deadline !== null && c.apply_deadline>=today &&
      Date.parse(c.last_seen_at)>=cutoff) ||
     (c.apply_deadline === null && c.deadline_precision==="unknown" &&
      c.open_verified===true && Date.parse(c.last_seen_at)>=Date.now()-48*60*60*1000)));
  const matching = active.filter(c=>{
    if (p.country === "INTL" ? c.country_code === "KR" : c.country_code !== "KR") return false;
    const haystack = [c.search_text, PLATFORM[c.source_id]?.[0]].filter(Boolean).join(" ").toLowerCase();
    if (!searchTerms(p.q).every(t=>haystack.includes(t))) return false;
    if (p.sido && c.region_sido !== p.sido && !(c.region_text||"").includes(p.sido)) return false;
    // Some providers omit a separate region field but include the location in the
    // listing title. Include that public title as a location fallback.
    if (p.sigungu && ![c.region_text || "",c.title].some(x => x.includes(p.sigungu))) return false;
    if (p.cat && c.category!==p.cat) return false;
    if (p.type && c.campaign_type!==p.type) return false;
    if (p.ch && !c.channels.includes(p.ch)) return false;
    return true;
  });
  function inTab(c:Campaign,t:typeof TABS[number]):boolean {
    switch(t) {
      case "new":return Date.parse(c.first_seen_at)>=firstToday;
      case "today":return c.apply_deadline===today;
      case "soon":return c.apply_deadline!==null && c.apply_deadline<=addDays(today,3);
      case "lowcomp":return c.competition_ratio!==null && c.competition_ratio<1;
      case "zero":return c.slots!==null && c.slots>0 && c.applicants===0;
      default:return true;
    }
  }
  const tabCounts = Object.fromEntries(TABS.map(t=>[t,matching.filter(c=>inTab(c,t)).length])) as Record<typeof TABS[number],number>;
  const filtered=matching.filter(c=>inTab(c,p.tab||"all"));
  const latest=(a:Campaign,b:Campaign)=>b.first_seen_at.localeCompare(a.first_seen_at);
  const deadline=(a:Campaign,b:Campaign)=>(a.apply_deadline||"9999").localeCompare(b.apply_deadline||"9999");
  switch(p.sort) {
    case "deadline":filtered.sort((a,b)=>deadline(a,b)||latest(a,b));break;
    case "ratio":filtered.sort((a,b)=>(a.competition_ratio??Infinity)-(b.competition_ratio??Infinity)||deadline(a,b));break;
    case "remaining":filtered.sort((a,b)=>(b.remaining_slots??-1)-(a.remaining_slots??-1)||deadline(a,b));break;
    default:filtered.sort(latest);
  }
  const byKey=new Map<string,Campaign[]>();
  for(const c of active) if(c.dedupe_key) {
    const arr=byKey.get(c.dedupe_key)||[]; arr.push(c); byKey.set(c.dedupe_key,arr);
  }
  const start=((p.page||1)-1)*24;
  const items=filtered.slice(start,start+24).map(c=>({
    ...c,related:(byKey.get(c.dedupe_key)||[]).filter(x=>x.source_id!==c.source_id)
      .map(x=>({source_id:x.source_id,original_url:x.original_url}))
  }));
  const sources=Object.entries(PLATFORM).map(([id,[name,homepage_url]])=>{
    const subset=active.filter(c=>c.source_id===id);
    const last_success_at=subset.length?subset.map(c=>c.last_seen_at).sort().at(-1)??null:null;
    return {id,name,homepage_url,country_code:"KR",
      status:subset.length?"connected":"not_connected",
      status_note:subset.length?"공개 모집 목록 자동 수집":"수집 데이터 없음",last_success_at};
  });
  return {items,total:filtered.length,globalTotal:active.length,tabCounts,sources,today,error:null as string|null};
}
