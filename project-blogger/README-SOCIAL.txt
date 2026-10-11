DEALZONE SOCIAL PUBLISHER - FIRST CLEAN VERSION

This is a separate app inside project-blogger. It does not replace or edit blogger_app.py or RUN.bat.

START
1. Extract the repository ZIP.
2. Open project-blogger.
3. Double-click RUN_SOCIAL.bat.
4. Choose an AliExpress product CSV.
5. Select the platforms for which you want prepared CSV files.
6. Click "Generate platform CSV files".
7. Files are written to project-blogger/output by default.

CURRENT CAPABILITIES
- Reads common AliExpress CSV formats (comma, semicolon, or tab separated).
- Builds a product title, SEO description, hashtags, image URL, product URL, and a stable deduplication key.
- Exports a separate CSV for each selected platform.
- Does not modify the source CSV.
- Does not publish to accounts yet. Direct publishing needs approved API access, tokens, and platform-specific handling. Never place tokens or client secrets in GitHub.
- Blogger is intentionally excluded while the blog review is pending.

This app is isolated in new files:
social_publisher.py
RUN_SOCIAL.bat
requirements-social.txt
README-SOCIAL.txt

Existing Blogger files are left unchanged.
