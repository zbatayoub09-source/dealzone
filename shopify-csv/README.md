# Shopify import CSVs — EUR store

All product CSVs in this folder are converted from the original AliExpress category exports in the repository root. No Metricool or social-publishing CSVs were used.

## Import
1. In Shopify Admin, open **Products → Import**.
2. Upload one or more `.shopify.csv` files from this folder.
3. Review Shopify's import preview before confirming.
4. Products are set to **Draft**. Check supplier stock, variants, delivery costs, taxes, and final retail margins before publishing.

## EUR price conversion
All `Variant Price` and `Variant Compare At Price` values are EUR:
- EUR source prices: unchanged.
- USD source prices: multiplied by **0.9123 EUR per USD** (indicative rate, 26 Nov 2026).
- MAD source prices: divided by **10.97 MAD per EUR** (indicative reference rate, 26 Nov 2026).

Converted values are rounded to 2 decimals. Original currency is preserved in `product.metafields.custom.source_currency`. Rates are indicative and are not a guarantee of the amount charged by AliExpress at checkout.

## Preserved fields
- AliExpress Product ID → SKU and `custom.source_product_id`
- Promotion URL → `custom.aliexpress_promotion_url`
- Product image URL → Shopify image source
- One default variant per product

Video URLs, commission rates, sales statistics, and supplier code campaigns remain in the original AliExpress CSVs and are not imported as Shopify product fields.

## Important checks
The source category CSVs may contain products that do not perfectly match their category name, and repeated product IDs have been deduplicated in the Shopify exports. Review product titles and category assignments before publishing. Shopify's import preview is the final check for your store's specific setup.
