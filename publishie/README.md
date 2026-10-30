# Publishie — Social Media Publisher

This is the independent social-media workspace for DealZone, served at `/publishie/`.

## Current features
- Local CSV import and preview (no upload).
- Flexible column mapping for Title, Description, Image, Video, Buy Now, Price and Hashtags.
- Post preview with row navigation.
- Select Facebook, Instagram, Threads, TikTok, YouTube and Pinterest.
- Export a normalized CSV using selected mappings.

## Publishing status
This is the frontend preparation stage. Actual account OAuth, token diagnostics/refresh, secure credential storage, scheduling workers and live publishing are not enabled yet. GitHub Pages is static hosting and must not receive platform secrets. Each platform requires its own official authorization and app permissions; Google sign-in is only for identifying the Publishie user, not connecting social accounts.

Never commit access tokens, OAuth client secrets, or private account files.
