# Facebook Image + Auto Comment Publisher

A separate Windows desktop app inside the DealZone repository. It does not modify Blogger, Partage Social, or other existing projects.

## What it does

1. Save one or more Facebook Pages in the app (Page name, Page ID, Page Access Token).
2. Choose a CSV file.
3. For each CSV row, upload/publish the image first, then create a separate comment under the resulting Facebook post.
4. Keep a local publishing log and stop the run between rows.

## CSV format

Required column names:

- \`page_name\`: must match the saved Page name in the app (case-insensitive).
- \`image\`: either a public HTTP/HTTPS image URL or a local image path.
- \`comment\`: the text to publish as a separate comment.

Example:

\`\`\`csv
page_name,image,comment
My Facebook Page,images/photo1.jpg,"Check the details in the first comment."
\`\`\`

The sample file is \`sample_posts.csv\`. Local image paths can be absolute paths or relative to this app folder.

## Run on Windows

Double-click \`RUN.BAT\`. It creates a local virtual environment and installs the required package automatically.

## Facebook API setup

Use a valid **Page Access Token** for each Page, with the permissions and app review/access required by Meta for the intended Page publishing and engagement actions. Add the Page ID and token inside the app.

The app uses the Graph API version configured in \`main.py\` (\`v26.0\`). Change \`GRAPH_VERSION\` if your Meta app is configured for a different currently supported version.

## Important safety and limits

- Facebook/Meta enforces rate limits, content policies, and anti-spam restrictions. There is no guaranteed unlimited publishing.
- Use a sensible delay between rows; the default is 30 seconds. A larger delay may be appropriate for your Pages.
- The app does not bypass Meta limits or automate account creation.
- Tokens are saved in local \`settings.json\`, which is excluded from Git by \`.gitignore\`. Do not share this file or commit tokens to GitHub.
- A photo can be published even if the follow-up comment fails. The log reports that case so you do not unknowingly republish the image.

## Troubleshooting

- If Facebook rejects the request, read the exact API error in the Publishing Log.
- Confirm the token belongs to the selected Page and has the required permissions.
- If the photo is published but no \`post_id\` is returned, the app stops before attempting the comment.
- For URL images, the image must be publicly reachable by Meta. Local image files are uploaded directly by the app.
