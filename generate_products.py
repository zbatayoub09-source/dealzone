import csv, html, json, re, shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "products"
BASE = "https://zbatayoub09-source.github.io/dealzone"
SKIP_PREFIXES = ("metricool", "malabis rijal", "ملابس رجالية", "ملابس نسائية")

CATEGORY_MAP = {}

def clean(v):
    return re.sub(r"\s+", " ", str(v or "").replace("\x00", " ")).strip()

def val(row, *keys):
    for k in keys:
        if k in row and clean(row[k]):
            return clean(row[k])
    return ""

def slug(s):
    s = clean(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def money(value, currency):
    s = clean(value)
    if currency.upper() == "MAD":
        m = re.search(r"-?[0-9]+(?:[.,][0-9]+)?", s)
        if m:
            try:
                return f"{float(m.group(0).replace(',', '.')) / 11.16:.2f}"
            except ValueError:
                pass
    return s

def esc(s):
    return html.escape(str(s or ""), quote=True)

def image_url(s):
    s = clean(s)
    if s.startswith("//"):
        return "https:" + s
    if s.startswith("http://"):
        return "https://" + s[7:]
    return s

def product_path(pid):
    return f"products/{quote(str(pid), safe='')}/index.html"

def page(row, category, related):
    pid = val(row, "ProductId")
    title = val(row, "Product Desc", "ProductDesc", "Title") or "DealZone Product"
    img = image_url(val(row, "Image Url", "Image URL", "ImageUrl"))
    video = image_url(val(row, "Video Url", "Video URL", "VideoUrl"))
    origin = val(row, "Origin Price", "OriginPrice")
    discount = val(row, "Discount Price", "DiscountPrice", "Price")
    cur = val(row, "Currency") or "USD"
    shown_origin = money(origin, cur)
    shown_discount = money(discount, cur)
    if cur.upper() == "MAD":
        cur = "EUR"
    disc = val(row, "Discount", "Discount %", "Discount Percentage")
    sales = val(row, "Sales180Day")
    feedback = val(row, "Positive Feedback")
    deal = val(row, "Promotion Url", "Promotion URL", "PromotionUrl")
    sales_text = (sales + "+ sold in the last 180 days") if sales else ""
    seo_title = (title[:88] + (" | " + sales + " sold" if sales else "") + " | DealZone")[:120]
    description = title + ((" Popular choice with " + sales + " sales in the last 180 days.") if sales else "") + ((" Positive feedback: " + feedback + ".") if feedback else "") + " Shop on DealZone."
    page_url = f"{BASE}/{product_path(pid)}"

    related_html = "".join(
        f'<a class="related-card" href="../../{esc(product_path(r["ProductId"]))}">'
        f'<img src="{esc(image_url(r.get("Image Url","")))}" loading="lazy" alt="{esc(val(r,"Product Desc")[:90])}">'
        f'<span>{esc(val(r,"Product Desc")[:85])}</span></a>'
        for r in related if val(r, "ProductId") != pid
    )

    schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "image": [img] if img else [],
        "description": description[:300],
        "sku": pid,
        "brand": {"@type": "Brand", "name": "DealZone"},
    }
    if shown_discount:
        schema["offers"] = {
            "@type": "Offer",
            "url": deal or f"{BASE}/{product_path(pid)}",
            "priceCurrency": cur,
            "price": re.sub(r"[^0-9.]", "", shown_discount) or "0",
            "availability": "https://schema.org/InStock",
        }

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(seo_title)}</title>
<meta name="description" content="{esc(description[:155])}">
<link rel="canonical" href="{BASE}/{product_path(pid)}">
<meta property="og:type" content="product">
<meta property="og:title" content="{esc(seo_title)}">
<meta property="og:description" content="{esc(description[:155])}">
<meta property="og:url" content="{BASE}/{product_path(pid)}">
{f'<meta property="og:image" content="{esc(img)}">' if img else ''}
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif;background:#f5f5f5;color:#222}}a{{color:inherit;text-decoration:none}}
.top{{background:#111;color:#fff;padding:8px 5%;font-size:13px}}header{{background:#fff;padding:16px 5%;display:flex;align-items:center;gap:25px;position:sticky;top:0;z-index:5;box-shadow:0 2px 8px #0001}}.logo{{display:flex;align-items:center;width:180px;height:52px}}.logo img{{display:block;width:100%;height:100%;object-fit:contain}}.search{{flex:1;display:flex;max-width:700px}}.search input{{width:100%;padding:12px;border:2px solid #f22;border-radius:8px 0 0 8px}}.search button{{border:0;background:#f22;color:#fff;padding:0 20px;border-radius:0 8px 8px 0}}
nav{{background:#fff;padding:0 5% 13px;display:flex;gap:22px;font-weight:700;border-bottom:1px solid #eee}}main{{max-width:1180px;margin:auto;padding:25px 5% 50px}}.crumb{{color:#777;font-size:13px;margin-bottom:18px}}.product{{background:#fff;border:1px solid #eee;border-radius:14px;padding:24px;display:grid;grid-template-columns:minmax(300px,1fr) minmax(300px,1fr);gap:32px}}.photo{{min-height:430px;display:flex;align-items:center;justify-content:center;background:#fff;border-radius:10px}}.photo img{{max-width:100%;max-height:480px;object-fit:contain}}h1{{font-size:28px;line-height:1.25;margin:0 0 15px}}.title-sold{{display:inline-block;color:#16803d;font-size:14px;font-weight:700;vertical-align:middle;margin-left:6px}}.price{{font-size:30px;font-weight:900;color:#e22;margin:15px 0}}.old{{color:#999;text-decoration:line-through;font-size:15px;margin-left:8px;font-weight:400}}.discount{{display:inline-block;background:#fff0f0;color:#e22;padding:4px 7px;border-radius:5px;font-size:12px;margin-left:8px;vertical-align:middle}}.stats{{display:flex;gap:18px;flex-wrap:wrap;color:#666;font-size:13px;margin:15px 0 20px}}.deal{{display:inline-block;background:#f22;color:#fff;padding:14px 25px;border-radius:9px;font-weight:800}}.desc{{background:#fff;border:1px solid #eee;border-radius:14px;padding:24px;margin-top:20px;line-height:1.7;white-space:pre-wrap}}.video{{margin-top:20px;width:100%;max-height:520px}}.share{{background:#fff;border:1px solid #eee;border-radius:14px;padding:18px 20px;margin-top:20px}}.share h2{{margin:0 0 8px;font-size:20px}}.share p{{margin:0 0 13px;color:#777;font-size:13px}}.share-main{{border:0;background:#f22;color:#fff;padding:12px 20px;border-radius:9px;font-weight:800;cursor:pointer}}.share-main:hover{{background:#d71920}}.share-modal{{display:none;position:fixed;inset:0;background:#0008;z-index:1000;align-items:center;justify-content:center;padding:18px}}.share-box{{width:min(520px,100%);background:#fff;border-radius:18px;padding:22px;box-shadow:0 20px 60px #0006}}.share-box-head{{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px}}.share-box-head h3{{margin:0;font-size:21px}}.share-close{{border:0;background:#f3f4f6;width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:20px}}.share-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}}.share-btn{{display:block;text-align:center;padding:11px 8px;border-radius:9px;font-size:13px;font-weight:800;border:1px solid #ddd;background:#fafafa;cursor:pointer}}.share-btn:hover{{border-color:#f22;color:#f22}}@media(max-width:430px){{.share-grid{{grid-template-columns:repeat(2,1fr)}}}}.related{{margin-top:28px}}.related-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}}.related-card{{background:#fff;border:1px solid #eee;border-radius:10px;padding:8px;font-size:12px;font-weight:600}}.related-card img{{width:100%;height:140px;object-fit:contain}}.related-card span{{display:block;padding:7px 2px}}footer{{background:#111;color:#aaa;text-align:center;padding:30px 5%}}@media(max-width:750px){{.product{{grid-template-columns:1fr;padding:15px}}.photo{{min-height:300px}}h1{{font-size:22px}}}}
</style>
</head>
<body>
<div class="top">🔥 DealZone — Hot Deals & Smart Shopping</div>
<header><a class="logo" href="../../index.html"><img src="../../logo.svg" alt="DealZone"></a><div class="search"><input id="q" placeholder="Search products..."><button onclick="search()">Search</button></div></header>
<nav><a href="../../index.html">Home</a><a href="../../index.html#categories">Categories</a><a href="../../{slug(category)}.html">{esc(category)}</a></nav>
<main>
<div class="crumb"><a href="../../index.html">Home</a> › <a href="../../{slug(category)}.html">{esc(category)}</a> › Product</div>
<section class="product">
<div class="photo">{f'<img src="{esc(img)}" alt="{esc(title[:100])}" loading="eager">' if img else '<span>No image</span>'}</div>
<div>
<h1>{esc(title)}{f'<span class="title-sold"> · {esc(sales)} sold</span>' if sales else ''}</h1>
<div class="price">{esc(shown_discount)} {esc(cur)} {f'<span class="old">{esc(shown_origin)} {esc(cur)}</span>' if shown_origin else ''} {f'<span class="discount">{esc(disc)}</span>' if disc else ''}</div>
<div class="stats">{f'<span>🛒 {esc(sales)} sold</span>' if sales else ''}{f'<span>⭐ {esc(feedback)} positive</span>' if feedback else ''}<span>📦 {esc(category)}</span></div>
{f'<a class="deal" href="{esc(deal)}" target="_blank" rel="nofollow sponsored noopener">View Deal</a>' if deal else ''}
</div>
</section>
<section class="desc"><h2>Product Description</h2><div>{esc(description)}</div></section>
{f'<video class="video" controls preload="metadata" src="{esc(video)}"></video>' if video else ''}
<section class="share"><h2>Share this product</h2><p>Share this product with your friends and social networks.</p><button class="share-main" onclick="openShare()">↗ Share</button></section><div class="share-modal" id="shareModal" onclick="if(event.target===this)closeShare()"><div class="share-box"><div class="share-box-head"><h3>Share this product</h3><button class="share-close" onclick="closeShare()">×</button></div><div class="share-grid">
<a class="share-btn" target="_blank" rel="noopener" href="https://www.facebook.com/sharer/sharer.php?u={quote(page_url, safe='')}">Facebook</a>
<a class="share-btn" target="_blank" rel="noopener" href="https://twitter.com/intent/tweet?url={quote(page_url, safe='')}&text={quote(title[:100], safe='')}">X / Twitter</a>
<a class="share-btn" target="_blank" rel="noopener" href="https://api.whatsapp.com/send?text={quote(title[:100] + ' ' + page_url, safe='')}">WhatsApp</a>
<a class="share-btn" target="_blank" rel="noopener" href="https://t.me/share/url?url={quote(page_url, safe='')}&text={quote(title[:100], safe='')}">Telegram</a>
<a class="share-btn" target="_blank" rel="noopener" href="https://www.linkedin.com/sharing/share-offsite/?url={quote(page_url, safe='')}">LinkedIn</a>
<a class="share-btn" target="_blank" rel="noopener" href="https://www.reddit.com/submit?url={quote(page_url, safe='')}&title={quote(title[:100], safe='')}">Reddit</a>
<a class="share-btn" target="_blank" rel="noopener" href="https://pinterest.com/pin/create/button/?url={quote(page_url, safe='')}&media={quote(img, safe='')}&description={quote(title[:100], safe='')}">Pinterest</a>
<a class="share-btn" href="mailto:?subject={quote(title[:100], safe='')}&body={quote(page_url, safe='')}">Email</a><button class="share-btn" onclick="copyProductLink()">Copy Link</button><button class="share-btn" onclick="nativeShare()">More Apps</button>
</div></div></div>
<section class="related"><h2>Related Products</h2><div class="related-grid">{related_html}</div></section>
</main>
<footer>© DealZone · Product links may be affiliate links.</footer>
<script>const PRODUCT_URL=location.href,PRODUCT_TITLE=document.title.replace(" | DealZone","");function openShare(){document.getElementById("shareModal").style.display="flex"}function closeShare(){document.getElementById("shareModal").style.display="none"}async function copyProductLink(){try{await navigator.clipboard.writeText(PRODUCT_URL);alert("Product link copied!")}catch(e){prompt("Copy this link:",PRODUCT_URL)}}async function nativeShare(){if(navigator.share){try{await navigator.share({title:PRODUCT_TITLE,text:PRODUCT_TITLE,url:PRODUCT_URL})}catch(e){}}else{copyProductLink()}}function search(){{const q=document.getElementById("q").value.trim();if(q)location.href="../../category.html?q="+encodeURIComponent(q)}}document.getElementById("q").addEventListener("keydown",e=>{{if(e.key==="Enter")search()}});</script>
</body></html>'''

def main():
    OUT.mkdir(exist_ok=True)
    all_products = []
    inputs = []
    for csv_path in sorted(ROOT.glob("*.csv")):
        if csv_path.name.lower().startswith(SKIP_PREFIXES):
            continue
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        if rows and "ProductId" in (rows[0].keys() if rows else []) and "Promotion Url" in (rows[0].keys() if rows else []):
            inputs.append((csv_path, rows))
            all_products.extend((CATEGORY_MAP.get(csv_path.stem, csv_path.stem), r) for r in rows if val(r, "ProductId"))
    seen = set()
    sitemap = []
    count = 0
    for category, row in all_products:
        pid = val(row, "ProductId")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        folder = OUT / pid
        folder.mkdir(parents=True, exist_ok=True)
        same_cat = [r for c, r in all_products if c == category and val(r, "ProductId") and val(r, "ProductId") != pid]
        # Rotate the related-products window so every product page gets a different set
        # while keeping all related products inside the same CSV/category.
        if same_cat:
            seed = sum((i + 1) * ord(ch) for i, ch in enumerate(pid))
            start = seed % len(same_cat)
            ordered = same_cat[start:] + same_cat[:start]
            related = ordered[:8]
        else:
            related = []
        (folder / "index.html").write_text(page(row, category, related), encoding="utf-8")
        sitemap.append(f"<url><loc>{BASE}/{product_path(pid)}</loc></url>")
        count += 1

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += f'<url><loc>{BASE}/</loc></url>\n'
    for p in ["category.html","cnc-routers-machinery.html","computer-office.html","deals-offers.html","jewelry.html","motorcycle-accessories.html","motorcycles.html","tools-hardware.html","watches.html"]:
        xml += f"<url><loc>{BASE}/{p}</loc></url>\n"
    xml += "\n".join(sitemap) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    print(f"Generated {count} product pages from {len(inputs)} product CSV files.")

if __name__ == "__main__":
    main()

# Product pages are regenerated automatically by GitHub Actions when CSV files change.
