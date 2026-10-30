# Backend setup — DealZone Publisher

This is a secure database and Edge Function starting point. The live site remains preview-only until the backend is deployed and tested.

## 1) Supabase project
1. Create a project at https://supabase.com/ and keep the database password private.
2. In the SQL Editor, run `schema.sql` from this folder. The four initial tables are already created in the current project.
3. In Authentication → Providers, enable Google. Configure its OAuth Client ID/Secret and use the exact callback URL shown by Supabase.
4. In Authentication → URL Configuration, set the Site URL to `https://zbatayoub09-source.github.io/dealzone/publisher/` and add that exact URL to the allowed redirect URLs.
5. Keep the Supabase service-role key only in Edge Function secrets. Never add it to GitHub or browser JavaScript.

## 2) Deploy the first Edge Function
The first function validates the signed-in user's Supabase session, initializes their private profile, and returns only their own destination/job metadata. It does not publish posts and does not return provider tokens.

Install the Supabase CLI, open PowerShell in a local clone of this repository, then run:

```powershell
supabase login
supabase link --project-ref aazralaszwzfsfwqgsfg
supabase secrets set SUPABASE_URL=https://aazralaszwzfsfwqgsfg.supabase.co
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_SECRET
supabase functions deploy publisher-workspace
```

Replace `YOUR_SERVICE_ROLE_SECRET` locally with the project's service-role/secret key from Supabase Dashboard → Project Settings → API. Do not paste that key into chat, GitHub, or the website. The function source is at `publisher/backend/supabase/functions/publisher-workspace/index.ts`.

After deployment, the endpoint is:

```
https://aazralaszwzfsfwqgsfg.supabase.co/functions/v1/publisher-workspace
```

It accepts POST with the signed-in user's `Authorization: Bearer <access_token>`. CORS is restricted to the DealZone GitHub Pages origin.

## 3) Provider connections
- Google sign-in identifies the user only. Blogger publishing requires a separate Google OAuth authorization flow requesting the Blogger API scope.
- Facebook sign-in identifies the user only. It does not grant permission to publish to Pages or Instagram. Configure a Meta app, request only the permissions needed, and complete any required app review/business verification.
- Instagram publishing requires an eligible Instagram professional account linked to a Facebook Page and the appropriate Meta permissions/API setup.

## 4) Publishing worker requirements
Before enabling publishing, implement authenticated Edge Functions for:
- OAuth connect/callback and token refresh; encrypt tokens server-side and never return them to the browser.
- CSV upload/validation and enqueueing, with per-user ownership checks and file/row limits.
- A scheduled worker that claims one due queue item atomically, waits for `next_attempt_at`, posts through the correct provider API, and stores the provider post ID.
- Retry policy: never blindly retry an item in `uncertain` status. Check the provider result first because a network timeout can occur after the provider accepted the post.
- Pause/resume/cancel endpoints and a status endpoint that returns only safe metadata.
- Audit logs without access tokens, refresh tokens, secrets, or full sensitive payloads.

## 5) Duplicate protection and resume
The schema's unique key `(user_id, destination_id, product_key)` prevents the same product being queued twice for the same account. Generate `product_key` from a stable source product ID where available; otherwise use a deterministic hash of normalized product URL/ID. Keep the queue row after success and mark it `published`; do not delete it on completion. On reconnect, resume only `pending`/eligible `failed` rows. For ambiguous provider responses, mark `uncertain` and verify before retrying.

## 6) CSV exports
Export queue and history as per-user downloads from an authenticated endpoint. Do not put passwords, OAuth secrets, access tokens, refresh tokens, or session cookies in CSV. Never create a shared public CSV containing users' data.

## Current status
- Supabase schema: created; row-level security is enabled.
- Google sign-in provider: configured in Supabase; test result should be confirmed in the live page.
- `publisher-workspace` Edge Function: source committed; deployment and live test still required.
- GitHub Pages frontend: still preview-only; publishing is not active.
