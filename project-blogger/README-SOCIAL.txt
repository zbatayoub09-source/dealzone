DEALZONE SOCIAL PUBLISHER

WHAT IS NEW
- Keeps the AliExpress Video Url field in each platform CSV as "Video Url".
- Optional Gemini AI mode improves product title, SEO description and hashtags.
- The Gemini API key is entered in the app and is not saved to a settings file.
- Blogger files and credentials are not changed by this tool.

RUN
1. Extract the repository ZIP.
2. Open the project-blogger folder.
3. Double-click RUN_SOCIAL.bat.
4. Choose your AliExpress CSV.
5. If you want AI copy, tick "Improve ... with Gemini AI" and enter your Gemini API key.
6. Choose platforms, set product limit, then click Generate platform CSV files.
7. Output files are in the selected output folder (default: project-blogger\output).

VIDEO
The app copies Video Url from the source CSV into the output CSV. If the source row has no video URL, the output field stays blank. This does not download or upload video files, and the generated CSV files do not automatically publish posts.

GEMINI API
AI use needs a valid Gemini API key and may consume API quota. Do not share your key or commit it to GitHub. If AI mode is off, the app uses a simple local description and hashtags.

LIMITATION
This app prepares CSV files only. Direct posting requires separate official API access, authentication, permissions, and platform-specific media requirements for each social network. Blogger is intentionally not included while the Blogger account review is pending.
