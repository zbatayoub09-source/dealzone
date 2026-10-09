# Blogger + GitHub automation

This workflow reads the original CSV files, creates separate SEO copies, and publishes/updates product posts through Blogger API.

## Features
- Reads CSV files from the repository root, data/ or csv/ folders.
- Creates generated/<CSV name>_SEO.csv with SEO_Title, SEO_Description, SEO_Keywords and Hashtags.
- Runs every 6 hours, when a source CSV changes, or manually from Actions.
- Processes at most 5 new or changed products per run (up to 20 per day).
- Stores ProductId-to-Blogger-post mappings in .automation/blogger_state.json to avoid duplicate posts and update changed products.
- Original CSV files are not edited.

## Required GitHub Actions secrets
Open Settings → Secrets and variables → Actions → New repository secret and add:
- BLOGGER_CLIENT_ID — OAuth client ID.
- BLOGGER_CLIENT_SECRET — matching OAuth client secret.
- BLOGGER_REFRESH_TOKEN — refresh token for the Google account that owns the blog.

Never commit OAuth credentials or tokens in the repository. The default target is Blogger blog ID 1419305768199826334 (cncrouterdesign.xyz).

## First run
1. Add all three secrets.
2. Open Actions → Blogger and CSV Automation → Run workflow.
3. Check the run logs, generated SEO copies, and the Blogger blog before relying on scheduled publishing.

SEO is generated using a deterministic template from CSV values and does not invent specifications. Review generated descriptions before using them for important claims.

## Blogger theme
Blogger API supports posts/pages, but does not provide a general theme/template update endpoint. Export the current theme XML from Blogger Theme settings, store it separately in GitHub for version history, then use Theme → Restore/Upload to apply a reviewed template. The content automation does not automatically replace the live theme.
