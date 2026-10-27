# DealZone Publisher — Google Sheets to Facebook

Windows desktop application. Configuration is entered in the app window: Google Sheet ID, tab name, and Facebook User Access Token. No `.env` and no `RUN.bat` are required.

## Files needed
- `app.py`
- `requirements.txt`
- `client_secret.json` — downloaded OAuth Client JSON for a **Desktop app**, placed beside `app.py`. Never upload it to GitHub.
- Python 3.10+ recommended.

## One-time setup (Windows)
1. Install Python and select **Add Python to PATH** during installation.
2. Open the project folder in File Explorer, click the address bar, type `powershell`, and press Enter.
3. Run these commands one by one:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```
4. In the app window, paste the long Google Spreadsheet ID (the part between `/d/` and `/edit` in the sheet URL), enter the worksheet tab name (usually `News`), and paste your Facebook **User Access Token**. Click **7fed l-i3dadat**. The app saves these settings only on your PC.
5. Click **Charger les actualités**. On first use, a Google sign-in window opens. Sign in with an account that has access to the spreadsheet and approve read-only access. Enable **Google Sheets API** in Google Cloud and add your account as a test user if the OAuth app is in Testing mode.
6. Click **Charger mes pages Facebook**, select a page and a news item, then click Publish and confirm.

## Google Sheet format
Columns A:D: Date, Image URL, Title, Full Article. First row is treated as column headings. The Google Sheet must be accessible to the Google account used in the OAuth browser login.

## Facebook
The token must be a Facebook User Access Token that can list pages you manage. Meta permissions and Page access/tasks must allow listing pages and publishing. Never paste tokens into GitHub or send them in chat. If Meta returns an API-version error, use a currently supported Graph API version.

## Local private files
`client_secret.json`, `settings.json`, `token.json`, and `published_state.json` are local/private files and are excluded by `.gitignore`.

## Blogger
Blogger publishing is not implemented yet.
