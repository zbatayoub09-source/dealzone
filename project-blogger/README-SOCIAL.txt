DEALZONE SOCIAL PUBLISHER

RUN
1. Download/extract the latest repository ZIP.
2. Open project-blogger.
3. Double-click RUN_SOCIAL.bat. It creates a private .venv and installs the required YouTube API libraries automatically on first run.
4. Choose your AliExpress CSV and select the platforms.
5. For Facebook/Instagram, enter the Facebook User Access Token, click Load Facebook Pages and select the page(s).
6. For YouTube, click "Upload / Choose token file" and select your existing youtube_token.json from your computer.
7. Start with a limit of 1 product and click "Publish selected + Generate CSV".

YOUTUBE TOKEN
- Choose the OAuth token JSON file, normally youtube_token.json. Do NOT select client_secret.json.
- The file is selected locally; it is not uploaded to GitHub or any server.
- The token must include YouTube upload permission (https://www.googleapis.com/auth/youtube.upload) and normally a refresh_token.
- A YouTube product row must contain a direct, publicly downloadable video URL. An image URL or an ordinary product webpage is not a video file.
- Uploaded videos are set to Public and use the product title, description, hashtags and product link.
- If the existing token lacks upload permission or is expired without a refresh token, create a new OAuth token with YouTube upload scope.
- Keep youtube_token.json private. It is ignored by Git.

CHECKPOINT / RESUMING
Successful posts/uploads are saved in output/social_checkpoint.json. The app skips products already completed for the same platform/page or YouTube token file. Keep the checkpoint to resume; deleting it may allow duplicate posts.

OTHER PLATFORMS
Facebook and Instagram use the official Meta Graph API and require the correct account/page permissions. Threads requires a Threads User ID and token. TikTok and Pinterest currently produce ready-to-import CSV files rather than publishing directly.

GEMINI
Gemini AI is optional. Enter your API key in the app only; do not commit it to GitHub. AI copy may consume API quota.

SAFETY
Tokens stay in local fields/files and are not intentionally written into checkpoints. Test with one product first. Facebook/Instagram/YouTube publishing can fail if tokens, permissions, video URLs or platform requirements are not correct. The app has not been live-tested with your personal tokens.
