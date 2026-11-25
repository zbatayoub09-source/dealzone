# Shopify CSV exports

Ten Shopify product-import CSV copies generated from the product CSVs in the repository root. The original source CSVs are unchanged.

## Import
In Shopify Admin, open Products > Import, select one `.shopify.csv` file from this folder, review the preview, then import. Import one category file at a time. Each file is under Shopify's 15 MB import limit.

## Important: currency
The source files contain mixed currencies (USD, EUR and MAD). Shopify's Variant Price is a number interpreted in your store's base currency. The original currency is preserved in the product metafield `custom.source_currency`, but prices have NOT been converted. Convert the amounts to your Shopify store currency before publishing.

## Metafield setup
Before importing, create these three product metafield definitions in Shopify Admin > Settings > Custom data > Products:
- `custom.source_currency` — Single line text
- `custom.aliexpress_promotion_url` — URL
- `custom.source_product_id` — Single line text

All products are imported as drafts, with inventory tracking off. Promotion URLs and source product IDs are preserved in their metafields.

Images are imported from the source Image Url. The exports include one default variant per product; video URLs and affiliate commission fields remain in the original CSVs.
