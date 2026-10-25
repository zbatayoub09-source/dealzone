# DealZone Social Publisher — Test Prototype

This is an isolated prototype on branch `test/social-publisher-windows`. It does not modify the `main` branch or the existing Blogger app.

## Run on Windows

1. Install Python 3.10+ from python.org and enable "Add Python to PATH" (Tkinter is included in standard Windows installers).
2. Open PowerShell in this folder.
3. Run:

```powershell
py -3 social_publisher.py
```

## Current prototype features

- Loads a CSV and shows the number of rows and columns.
- Lets the user choose which CSV columns are combined into the post text/caption/comment.
- Auto-detects common image and video URL column names; allows Auto, Image, Video, or No media preview.
- Lets the user select Facebook, Instagram, Blogger, TikTok, Pinterest, and Threads. YouTube is intentionally excluded from this test UI.
- Supports a queue interval from 2 minutes upward, pause/resume, and saved progress.
- Keeps CSV selection, selected text columns, media mode, and progress in local `publisher_state.json`.

## Important limitation

This remains a **preview-only prototype**. It does not publish to any platform yet. Real cross-posting requires implementing and testing each platform's official API/OAuth flow, media upload requirements, account/page selection, and permissions. Selecting several platforms here only affects the preview; it does not post to them. Do not enter or commit real tokens in this prototype. The interval is a scheduling preference, not a guarantee that every platform will permit publishing at that rate.
