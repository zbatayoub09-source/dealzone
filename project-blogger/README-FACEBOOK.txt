PROJECT FACEBOOK PUBLISHER

This is a separate Facebook CSV publisher. It does not replace Blogger files.

START
1. Download/extract the project-blogger folder.
2. Double-click RUN_FACEBOOK.bat.
3. Choose a CSV file and match Title, Description, Image URL, Video URL, Link and Hashtags.
4. Choose Automatic, Image only, Video only or Text only.
5. Paste a Facebook User Access Token, click Load Facebook Pages and select Page(s).
6. Start with limit 1 and verify the result before using a larger batch.

HASHTAGS
- CSV column: uses the selected CSV hashtags column.
- Automatic: uses CSV hashtags if present, otherwise creates simple tags from the title.
- Gemini: enter a Gemini API key; it is not saved to a settings file.

CHECKPOINT
facebook_checkpoint.json records successful posts by CSV path, Page ID and product key. Successful rows are skipped on later runs. Keep it to resume. To intentionally repost the same rows, close the app and rename/delete this file.

IMPORTANT
- Image/video URLs must be public and fetchable by Facebook.
- Meta token must list Pages and include the required publishing permissions. Code cannot bypass Meta restrictions or app review.
- Tokens are not written to checkpoint/config files.
- Python 3.10+ recommended; uses standard library and Tkinter only.
