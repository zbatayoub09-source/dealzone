DEALZONE SOCIAL PUBLISHER

START
1. Download/extract the latest repository ZIP.
2. Open the project-blogger folder.
3. Double-click RUN_SOCIAL.bat. It launches social_publisher.py using the project .venv when available, otherwise Python 3.
4. Choose the AliExpress CSV and verify the column mapping, especially Title, Description, Image URL, Video URL, Promotion URL, Hashtags and Commentaire.
5. Select the platforms and start with a small limit (for example 1-3 products) while checking the first results.

DIRECT PUBLISHING
- Facebook: uses the selected Facebook Page and its Page Access Token returned by "Load Facebook Pages".
- Instagram: works only when the selected Facebook Page is linked to an Instagram Professional account. Public HTTPS media is required.
- Threads: requires Threads User ID and Access Token.
- TikTok and Pinterest: this app creates ready-to-import CSV files; it does not publish directly to those platforms.

PACING AND LIMITS
- "Max products in this run" is a cap on attempted products per selected Page/platform, not just successful posts. A failed Page will not cause the app to run through the entire CSV.
- The default delay is 5 minutes between successful/failed publishing attempts where applicable. Keep a conservative delay and test with a small batch. Do not use repeated runs to bypass a Meta restriction.

CHECKPOINT AND DIAGNOSTICS
- Successful social posts are saved in output/social_checkpoint.json. Keep this file to resume without duplicate posts.
- API failures and run summaries are appended to output/social_publisher.log. This log does not intentionally include access tokens or request parameters.
- If one Facebook Page fails, open the log and inspect its exact API error. Check Meta Page Status, Page access and token permissions; changing API versions or tokens will not bypass a Page restriction.
- The checkpoint and log are local runtime files and are excluded from Git.

GEMINI
Gemini AI is optional. Enter the API key in the app only; do not commit it to GitHub. AI copy may consume API quota.

SAFETY
Tokens are entered locally and are not intentionally written into checkpoints or logs. Test with one product first. Publishing can fail if tokens, Page permissions, media URLs, platform requirements or Meta restrictions are not satisfied.
