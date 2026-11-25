# Shopify CSV exports

Ten Shopify product-import CSV copies generated from the product CSVs in the repository root. The original source CSVs are unchanged.

## Import
In Shopify Admin, open Products > Import, select one `.shopify.csv` file from this folder, review the preview, then import. Import one category file at a time.

## Important: currency
The source files contain mixed currencies (USD, EUR and MAD). Shopify's Variant Price is a number interpreted in your store's base currency. The original currency is preserved in the product metafield `custom.source_currency`, but prices have NOT been converted. Convert the amounts to your Shopify store currency before publishing. All products are imported as drafts, with inventory tracking off. Promotion URLs are preserved in `custom.aliexpress_promotion_url`; source product IDs are preserved in `custom.source_product_id`.

Images are imported from the source Image Url. The exports include one default variant per product; video URLs and affiliate commission fields remain in the original CSVs.
