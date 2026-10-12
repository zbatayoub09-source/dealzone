# Project1_Zbatayoub09

Organized workspace for Blogger, YouTube, and social media automation.

## Folders
- `csv/` — source CSV files for workflows that explicitly support repository CSVs.
- `blogger/` — Blogger automation notes and configuration (never commit OAuth tokens).
- `youtube/` — YouTube publishing code and checkpoint design.
- `social-media/` — platform-specific publishing code and status tracking.
- `logs/` — documentation for run logs; Actions artifacts should be used for temporary logs.

## Current status
This folder is an organizer, not a claim that every platform is already automated. The repository already contains a Gemini SEO workflow at `.github/workflows/generate-seo-ai.yml` and Blogger automation documentation in `README-blogger-automation.md`. Check each workflow under the repository's **Actions** tab.

## Run SEO generation
1. Upload a CSV to the repository root (the existing workflow input expects a path such as `Jewelry.csv`), or update the workflow to use the chosen path.
2. Add `GEMINI_API_KEY` under Settings → Secrets and variables → Actions.
3. Open Actions → Generate SEO with Gemini → Run workflow.
4. Start with 20 products and inspect the changed CSV before processing more.

## Important
- GitHub Actions cannot safely use desktop-only login sessions. Add required API credentials as repository secrets.
- Never commit `client_secret.json`, `blogger_token.json`, `youtube_token.json`, OAuth refresh tokens, API keys, or passwords.
- YouTube video files need to be accessible to the workflow at runtime. Large videos and persistent checkpoints require a deliberate storage strategy.
- Social posting requires working APIs, permissions, and separate credentials for each platform.
- Scheduled workflows may be delayed or limited by GitHub Actions quotas. Verify every run in Actions logs.
