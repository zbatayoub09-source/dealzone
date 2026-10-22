PROJECT BLOGGER - DEALZONE

This desktop app creates Blogger posts from a CSV and can share newly published posts to selected social platforms.

FILES
- blogger_app.py: main app
- RUN.bat: installs dependencies and starts the app
- requirements.txt: Python packages
- client_secret.json: add your Google OAuth Desktop client file locally (never upload it)

FIRST-TIME BLOGGER SETUP
1. Download/extract the project-blogger folder.
2. In Google Cloud Console, enable Blogger API.
3. Create OAuth Client ID -> Desktop app, download the JSON, rename it client_secret.json, and put it beside RUN.bat.
4. Double-click RUN.bat, then click Connect Blogger and approve Google access.
5. Choose your Blogger blog and the product CSV.
6. Start with Draft and 3–5 posts. Check Blogger before switching to Publish publicly.

SHARE TO FACEBOOK / INSTAGRAM / THREADS
1. Choose Publish publicly. Social sharing does not run for Blogger drafts.
2. Under social sharing, tick only the platforms you want: Facebook, Instagram and/or Threads. Untick a platform to skip it.
3. For Facebook and/or Instagram, paste a Facebook User Access Token and click Load all Facebook Pages. Select the Page(s) you want to post to.
4. Facebook requires a token with permission to list Pages and publish posts to the selected Page.
5. Instagram requires an Instagram Professional account linked to the selected Facebook Page, suitable Meta permissions, and a publicly accessible HTTPS Image URL in the CSV. This version publishes image posts; it does not upload local files.
6. For Threads, enter your Threads User ID and Threads Access Token. The token must have the required Threads publishing permissions.
7. Test with one product first. Check the app status and each platform after publishing.

TOKEN AND ACCOUNT SAFETY
- Tokens are entered into the app and are not intentionally written to settings files or committed to GitHub.
- Never share access tokens, client_secret.json, blogger_token.json, or screenshots showing secrets.
- If a token fails, check the app permissions, token expiry, Page access, and whether Meta has granted the required permissions. Code cannot bypass Meta's access rules or app-review requirements.
- This tool uses the official APIs. Posting can fail when an account, media URL, token or permission does not meet platform requirements.

CSV FIELDS
Title / Product Title / Product Name / Product Desc, SEO_Description, Hashtags, Image Url, Promotion Url, ProductId.

NOTES
- The app does not automatically share old Blogger posts; it shares a post created and published during the current run.
- The original CSV is only read, not changed.
- Blogger token and published_state.json are stored locally to support Blogger login and avoid duplicate posts.
