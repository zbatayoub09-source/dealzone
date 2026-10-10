PROJECT BLOGGER - DEALZONE

This folder contains a desktop interface for selecting a CSV and creating Blogger posts.

FILES
- blogger_app.py: the app and Blogger screen
- RUN.bat: installs required Python packages and starts the app
- requirements.txt: dependencies
- client_secret.json: YOUR Google OAuth Desktop client file (you must add it locally)

FIRST-TIME SETUP
1. Extract the project folder to your computer.
2. In Google Cloud Console, enable the Blogger API for your project.
3. Create an OAuth Client ID of type Desktop app and download its JSON file.
4. Rename that downloaded file to client_secret.json.
5. Put client_secret.json in the same folder as RUN.bat and blogger_app.py.
6. Double-click RUN.bat.
7. Click Connect Blogger. A Google browser window will open. Sign in and approve access.
8. Choose your Blogger blog from the list.
9. Choose a CSV file. Existing SEO_Description and Hashtags columns are used if available; otherwise a basic description is generated.
10. Choose Draft (recommended) first, set Max posts to 3 or 5, and click START BLOGGER to test.
11. Check the posts in Blogger. If everything looks correct, you can choose Publish publicly on a later run.

IMPORTANT SECURITY
- Never upload client_secret.json or blogger_token.json to GitHub or send them in public messages.
- blogger_token.json is created locally after you authorize Google.
- Keep these files private on your computer.
- The app saves published_state.json locally to avoid processing the same products twice from the same CSV path.
- Keep the original CSV unchanged; the app only reads it.

CSV COLUMNS IT TRIES TO READ
Title / Product Title / Product Name / Product Desc, SEO_Description, Hashtags, Image Url, Promotion Url, ProductId.

NOTES
- Test with Draft and a small number of posts before public publishing.
- Posts with missing product links or images can still be created, but may be less useful.
- Blogger API quotas and Google account permissions apply.
