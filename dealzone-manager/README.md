# DealZone Manager

Local desktop dashboard for managing DealZone products, buy/sell prices, orders and CSV files.

## Start
Double-click `run.bat`. It creates a local virtual environment, installs Flask, starts the dashboard and opens the browser at http://127.0.0.1:5055.

## Data
Products and orders are stored locally in `dealzone_manager.db`. Keep this file safe; it contains your business records.

## CSV
Import supports common existing columns such as ProductId, Product Desc, Image/Video Url, Image Url and Origin Price. Imported sell prices default to zero and must be entered manually. Export creates a clean DealZone products CSV with BuyPrice, SellPrice, ShippingCost and calculated Profit.

## Important limitations
- This is a local management dashboard, not a public online checkout.
- No card, wallet, cash collection or supplier payment is processed by this app.
- Direct supplier-to-customer shipping, customs, delivery, returns and payment-provider availability must be confirmed with the supplier/carrier/provider before accepting real orders.
- Do not store card numbers, passwords or payment secrets here.
- Back up `dealzone_manager.db` regularly.
