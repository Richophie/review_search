import { createFileRoute } from "@tanstack/react-router";
import { authenticateCronRequest } from "@/integrations/supabase/cron-auth";

// Scheduled collector endpoint. Requires the project's cron secret as bearer token.
export const Route = createFileRoute("/api/public/hooks/collect")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const denied = await authenticateCronRequest(request);
        if (denied) return denied;
        const only = new URL(request.url).searchParams.get("source") ?? undefined;
        const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
        const { runCollection } = await import("@/lib/collector/run.server");
        const results = await runCollection(supabaseAdmin, only);
        return Response.json({ ok: true, results });
      },
    },
  },
});
