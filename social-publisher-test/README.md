# Social Publisher — Test Prototype

This folder is an isolated prototype on branch `test/social-publisher-windows`. It does not modify the existing `main` branch or the current Blogger app.

## Run on Windows

1. Install Python 3.10+ from python.org and enable "Add Python to PATH" (Tkinter is included in standard Windows installers).
2. Open PowerShell in this folder.
3. Run:

```powershell
py -3 social_publisher.py
```

## What this prototype does

- Loads and counts rows from a CSV file.
- Lets the user select target platforms.
- Sets a queue interval from 2 minutes upward.
- Provides pause/resume and reset controls.
- Saves the selected CSV path and progress to `publisher_state.json`.

## Important limitations

This is only a UI/queue preview. It does **not** publish content to Facebook, Instagram, Blogger, YouTube, TikTok, Pinterest, or Threads yet. Each platform needs its own supported OAuth/API integration and permission checks. Do not enter real tokens in this prototype. OAuth credentials and tokens must not be committed to GitHub.

The interval is a scheduling preference, not a guarantee that every platform will permit publishing at that rate.
