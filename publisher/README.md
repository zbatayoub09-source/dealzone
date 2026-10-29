# DealZone Publisher — deployment notes

This folder adds a static, browser-only preview page at `/publisher/`. CSV and token JSON parsing happens locally; credentials are not persisted to localStorage, IndexedDB, or the repository. The Publish button is deliberately disabled until a private backend is configured.

## Why a backend is required
GitHub Pages only serves static files. It cannot safely store per-user secrets, refresh Blogger OAuth credentials, or securely run publishing jobs. Never commit `blogger_token.json`, social access tokens, OAuth client secrets, or CSV files containing credentials.

## Recommended production architecture
- Frontend: this GitHub Pages folder.
- Authentication: Supabase Auth (email/Google sign-in) or an equivalent identity provider.
- Backend: Supabase Edge Functions or Cloudflare Workers, requiring a verified user session on every request.
- Credentials: encrypted server-side at rest, isolated by user ID; never returned in API responses or written to logs.
- CSV: size-limited upload, strict CSV parsing, header mapping, preview, duplicate protection, per-user rate limits, and audit status without token values.
- Blogger: prefer Google OAuth authorization flow with least privilege instead of accepting long-lived refresh-token files. If token-file import is retained, process it only over HTTPS, validate its structure, encrypt secrets at rest, and provide a delete/revoke option.
- Meta platforms: validate permissions and account/page IDs with the platform API; do not treat a pasted token as proof of ownership.
- Production safeguards: HTTPS, CSRF/origin checks, rate limiting, request-size limits, safe error messages, dependency updates, and secret rotation.

## Current status
The page is a functional import-and-preview UI, not a live publisher. Publishing remains disabled by design. To enable it, deploy and configure the authenticated backend and OAuth providers first, then wire the frontend to its API. Do not ask users to paste tokens into a public/demo page until that backend is ready.
