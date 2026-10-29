# Backend setup — DealZone Publisher

This is a secure database starting point, not a deployed service. The live site remains preview-only until these steps are completed and tested.

## 1) Create a Supabase project
1. Create a project at https://supabase.com/ and keep the database password private.
2. In the SQL Editor, run `schema.sql` from this folder.
3. In Authentication → Providers, enable Google and Facebook. Configure each provider's OAuth Client ID/Secret in the Supabase dashboard, and use the exact callback URL shown by Supabase in the provider console.
4. In Authentication → URL Configuration, set the Site URL to `https://zbatayoub09-source.github.io/dealzone/publisher/` and add that exact URL to the allowed redirect URLs.
5. Keep the Supabase service-role key only in Edge Function secrets. Never add it to GitHub or browser JavaScript.

## 2) Configure provider applications
- Google sign-in is for identifying the user. Blogger publishing requires a separate Google OAuth consent flow requesting Blogger API scope; sign-in alone does not authorize Blogger publishing.
- Facebook sign-in is for identifying the user. It does not grant permission to publish to Pages or Instagram. Configure a Meta app, request only the permissions needed, and complete any required app review/business verification.
- Instagram publishing requires an eligible Instagram professional account linked to a Facebook Page and the appropriate Meta permissions/API setup.

## 3) Publishing worker requirements
Before enabling publishing, implement authenticated Edge Functions for:
- OAuth connect/callback and token refresh; encrypt tokens server-side and never return them to the browser.
- CSV upload/validation and enqueueing, with per-user ownership checks and file/row limits.
- A scheduled worker that claims one due queue item atomically, waits for `next_attempt_at`, posts through the correct provider API, and stores the provider post ID.
- Retry policy: never blindly retry an item in `uncertain` status. Check the provider result first because a network timeout can occur after the provider accepted the post.
- Pause/resume/cancel endpoints and a status endpoint that returns only safe metadata.
- Audit logs without access tokens, refresh tokens, secrets, or full sensitive payloads.

## 4) Duplicate protection and resume
The schema's unique key `(user_id, destination_id, product_key)` prevents the same product being queued twice for the same account. Generate `product_key` from a stable source product ID where available; otherwise use a deterministic hash of normalized product URL/ID. Keep the queue row after success and mark it `published`; do not delete it on completion. On reconnect, resume only `pending`/eligible `failed` rows. For ambiguous provider responses, mark `uncertain` and verify before retrying.

## 5) CSV exports
Export queue and history as per-user downloads from an authenticated endpoint. Do not put passwords, OAuth secrets, access tokens, refresh tokens, or session cookies in CSV. Never create a shared public CSV containing users' data.

## Current status
- `schema.sql`: committed initial schema with row-level security and a per-user/per-destination product uniqueness constraint.
- GitHub Pages frontend: still a preview; publishing is not active.
- No OAuth app credentials, Supabase project, tokens, or provider permissions have been configured by this commit.
