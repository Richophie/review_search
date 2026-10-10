import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "@/integrations/supabase/types";
import type { SourceAdapter } from "./types";
import { normalizeCampaign, todayIn, addDays } from "./normalize";
import { dinnerqueen } from "./adapters/dinnerqueen";
import { mrblog } from "./adapters/mrblog";

// Registered connectors. reviewnote is intentionally absent: robots.txt disallows /campaigns/.
export const ADAPTERS: SourceAdapter[] = [dinnerqueen, mrblog];

const MIN_INTERVAL_MIN = 20;

export async function runCollection(db: SupabaseClient<Database>, only?: string) {
  const results: Record<string, unknown>[] = [];
  for (const adapter of ADAPTERS.filter((a) => !only || a.id === only)) {
    const { data: last } = await db.from("collection_runs").select("started_at")
      .eq("source_id", adapter.id).order("started_at", { ascending: false }).limit(1).maybeSingle();
    if (last && Date.now() - new Date(last.started_at).getTime() < MIN_INTERVAL_MIN * 60_000) {
      results.push({ source: adapter.id, skipped: "rate-limited" });
      continue;
    }
    const { data: run } = await db.from("collection_runs").insert({ source_id: adapter.id }).select("id").single();
    const startedAt = new Date().toISOString();
    try {
      const raws = await adapter.collect();
      const rows = [...new Map(raws.map((r) => [r.url, normalizeCampaign(r)])).values()];
      let upserted = 0;
      for (let i = 0; i < rows.length; i += 200) {
        const chunk = rows.slice(i, i + 200);
        // first_seen_at is preserved by omitting it from the upsert payload
        const { error } = await db.from("campaigns").upsert(chunk, { onConflict: "id" });
        if (error) throw new Error(error.message);
        upserted += chunk.length;
      }
      // Listings not seen in this run, or whose apply deadline passed, are inactive.
      if (rows.length) {
        await db.from("campaigns").update({ is_active: false })
          .eq("source_id", adapter.id).lt("last_seen_at", startedAt);
      }
      await db.from("campaigns").update({ is_active: false }).lt("apply_deadline", todayIn());
      await db.from("campaigns").delete().lt("apply_deadline", addDays(todayIn(), -30));
      await db.from("collection_runs").update({
        status: rows.length ? "success" : "empty", finished_at: new Date().toISOString(),
        items_found: raws.length, items_upserted: upserted,
      }).eq("id", run!.id);
      if (rows.length) {
        await db.from("sources").update({
          status: "connected", last_success_at: new Date().toISOString(),
          status_note: "공개 목록 페이지에서 수집 중",
        }).eq("id", adapter.id);
      }
      results.push({ source: adapter.id, found: raws.length, upserted });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      await db.from("collection_runs").update({ status: "error", error: msg, finished_at: new Date().toISOString() }).eq("id", run!.id);
      results.push({ source: adapter.id, error: msg });
    }
  }
  return results;
}
