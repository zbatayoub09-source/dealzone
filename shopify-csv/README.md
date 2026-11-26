# Shopify CSV exports — AliExpress sources only

These Shopify import CSVs were converted from the original AliExpress product-export category files in the repository root. They were NOT generated from Metricool files, Google Drive/Metricool publishing templates, or the `metricool*.csv` files.

The source AliExpress exports contain fields such as `ProductId`, `Image Url`, `Video Url`, `Product Desc`, `Origin Price`, `Discount Price`, `Currency`, commission rates, `Sales180Day`, `Positive Feedback`, and `Promotion Url`.

## Import
In Shopify Admin, open Products > Import, select one `.shopify.csv` file from this folder, review the preview, then import. Import one category file at a time.

## Important: currency
The source files contain mixed currencies (USD, EUR and MAD). Shopify's Variant Price is a number interpreted in your store's base currency. The original currency is preserved in `custom.source_currency`, but prices have NOT been converted. Convert amounts to your Shopify store currency before publishing.

## Metafield setup
Before importing, create these product metafield definitions in Shopify Admin > Settings > Custom data > Products:
- `custom.source_currency` — Single line text
- `custom.aliexpress_promotion_url` — URL
- `custom.source_product_id` — Single line text

All products are imported as drafts, with inventory tracking off. Promotion URLs and AliExpress product IDs are preserved in their metafields. Images are sourced from AliExpress image URLs. The exports include one default variant per product; video URLs and commission/statistics fields remain in the original AliExpress CSVs.
