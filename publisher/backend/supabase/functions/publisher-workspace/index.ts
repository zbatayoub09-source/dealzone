// DealZone Publisher workspace API
// Deploy as: supabase functions deploy publisher-workspace
// Required function secrets: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "https://zbatayoub09-source.github.io",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" },
  });
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin");
  if (origin && origin !== "https://zbatayoub09-source.github.io") {
    return json({ error: "Origin not allowed" }, 403);
  }
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const authorization = req.headers.get("authorization") || "";
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
  if (!token) return json({ error: "Sign-in required" }, 401);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !serviceRoleKey) {
    return json({ error: "Backend is not configured" }, 503);
  }

  const admin = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const { data: authData, error: authError } = await admin.auth.getUser(token);
  if (authError || !authData.user) return json({ error: "Invalid or expired session" }, 401);

  const user = authData.user;
  const displayName =
    user.user_metadata?.full_name ||
    user.user_metadata?.name ||
    user.email ||
    "DealZone user";

  const { error: profileError } = await admin
    .from("publisher_profiles")
    .upsert({ user_id: user.id, display_name: displayName }, { onConflict: "user_id" });
  if (profileError) {
    console.error("Profile upsert failed:", profileError.message);
    return json({ error: "Could not initialize workspace" }, 500);
  }

  const [destinationsResult, jobsResult] = await Promise.all([
    admin.from("publisher_destinations")
      .select("id,platform,external_account_id,account_label,status,created_at")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false }),
    admin.from("publisher_jobs")
      .select("id,status,max_posts_per_run,interval_seconds,created_at,updated_at")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(50),
  ]);

  if (destinationsResult.error || jobsResult.error) {
    console.error("Workspace read failed:", destinationsResult.error?.message, jobsResult.error?.message);
    return json({ error: "Could not load workspace" }, 500);
  }

  return json({
    user: { id: user.id, email: user.email ?? null, display_name: displayName },
    destinations: destinationsResult.data ?? [],
    jobs: jobsResult.data ?? [],
  });
});
