PROJECT BLOGGER — CHECKPOINT / RESUME NOTES

FILES
- blogger_app.py: Blogger publisher and social sharing.
- published_state.json: local Blogger publish checkpoint.
- social_share_state.json: local per-post, per-platform, per-Facebook-Page share checkpoint.
- RUN_JAIME.bat / jaime_pages.py: separate manual Facebook Page helper.

RESUME AFTER A STOP
1. Reopen the app and connect Blogger.
2. Select the same CSV file from the same computer path and select the same Blogger blog(s).
3. Click START BLOGGER. Posts already recorded in published_state.json are skipped; the next unprocessed CSV rows continue.
4. To resume social sharing for posts already published, reload the Facebook Pages and select the intended Pages, enable the required platform checkboxes, then click:
   RESUME / SELECT POSTS FROM CHECKPOINT & SHARE
5. Select the posts and click Share selected. The app skips each platform/Page target already marked successful and retries targets marked failed or not yet completed.

CHECKPOINT FILES
- Keep published_state.json and social_share_state.json in the project-blogger folder.
- Do not delete or rename these files if you want resume behavior.
- These files are local to the computer; they are not committed to GitHub by this update.
- If you intentionally want to publish/share the same content again, understand that deleting checkpoints can create duplicate posts.

LIMIT
A sudden power/network failure at the exact moment an external service accepts a request but before the app receives and saves its response can leave that one request uncertain. Check the destination before manually retrying that specific item.
