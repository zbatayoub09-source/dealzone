# Publish Python + Google Sheets

Windows desktop app to read news from Google Sheets, select a Facebook Page, and publish a title, article text, and optional image. Blogger may be added after this flow is tested.

## Setup (Windows)
1. Download this folder and extract it.
2. In Google Cloud, enable **Google Sheets API**.
3. Create an OAuth Client ID with application type **Desktop app** and download its JSON file. Rename it to `client_secret.json` and place it beside `app.py` and `RUN.bat`.
4. In the Google Auth Platform / OAuth consent screen, configure the app and add your Google account as a test user if the app is in Testing mode.
5. Double-click `RUN.bat`. The first run creates `.env` from `.env.example` and opens it in Notepad.
6. Set `SPREADSHEET_ID` to the long ID between `/d/` and `/edit` in your Google Sheets URL. Set `SHEET_NAME` to the worksheet tab name (default `News`, not the file title).
7. Save `.env`, close Notepad, and run `RUN.bat` again. Click **Charger les actualités**. A Google sign-in browser window should open on first use; choose the account that can access the sheet and approve read-only access.
8. If the sheet is not shared with that Google account, share it with that account as Viewer.

Never upload `.env`, `client_secret.json`, `token.json`, Facebook tokens, or `published_state.json` to GitHub.

The sheet expects columns A:D: Date, Image URL, Title, Full Article. The first row is treated as the header. The app does not publish automatically: select a page and a news item, then confirm Publish.

## Facebook
Set `FACEBOOK_USER_ACCESS_TOKEN` in `.env` to a user access token that can list the Pages you manage. The app reads each returned Page Access Token for publishing. Required Meta permissions and Page task access depend on your Meta app setup; commonly needed permissions include `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts`. Never share or commit tokens.

## Publication state
Successful posts are stored locally in `published_state.json`, separately per page.

## Blogger
Blogger is not implemented yet; first verify Google Sheets reading and Facebook publishing.
