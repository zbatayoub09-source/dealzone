import html
import urllib.parse

# Keep the original DealZone Blogger application unchanged and fix only
# the handling of AliExpress image URLs before Blogger receives the HTML.
import blogger_app as app


def normalize_public_url(value):
    value = str(value or "").strip()
    if not value:
        return ""
    # AliExpress Portal commonly exports protocol-relative image URLs:
    # //ae-pic-a1.aliexpress-media.com/....jpg
    if value.startswith("//"):
        value = "https:" + value
    elif value.startswith("http://"):
        value = "https://" + value[7:]
    return value


def fixed_product_data(row, index, column_map=None):
    item = app._original_product_data(row, index, column_map)
    item["image"] = normalize_public_url(item.get("image"))
    item["video"] = normalize_public_url(item.get("video"))
    item["link"] = normalize_public_url(item.get("link"))
    return item


def fixed_make_html(item):
    image = normalize_public_url(item.get("image"))
    video = normalize_public_url(item.get("video"))
    link = normalize_public_url(item.get("link"))
    title = html.escape(str(item.get("title", "")))
    description = html.escape(str(item.get("description", "")))

    parts = [
        f"<h2>{title}</h2>",
        "<hr>",
        "<h3>Product Details</h3>",
        f"<p>{description}</p>",
    ]

    if video.startswith(("https://", "http://")):
        safe_video = html.escape(video, quote=True)
        parts.append(
            f'<p><a href="{safe_video}" target="_blank" rel="noopener">▶ Watch product video</a></p>'
        )

    # Main fix: accept AliExpress Portal URLs that start with // and turn
    # them into a normal HTTPS URL that Blogger can render in an <img> tag.
    if image.startswith(("https://", "http://")):
        safe_image = html.escape(image, quote=True)
        image_html = (
            f'<img src="{safe_image}" alt="{html.escape(str(item.get("title", "")), quote=True)}" '
            'style="display:block;max-width:100%;height:auto;border:0;margin:0 auto">'
        )
        if link.startswith(("https://", "http://")):
            safe_link = html.escape(link, quote=True)
            parts.append(
                f'<p style="text-align:center"><a href="{safe_link}" rel="nofollow sponsored">{image_html}</a></p>'
            )
        else:
            parts.append(f'<p style="text-align:center">{image_html}</p>')

    if link.startswith(("https://", "http://")):
        safe_link = html.escape(link, quote=True)
        parts.append(
            '<p style="text-align:center;margin:24px 0">'
            f'<a href="{safe_link}" rel="nofollow sponsored" '
            'style="display:inline-block;background-color:#fe4f4f;color:#ffffff;padding:14px 24px;'
            'border-radius:6px;text-decoration:none;font-weight:bold;font-size:16px;border:1px solid #fe4f4f">'
            'CHECK PRICE &amp; DETAILS</a></p>'
        )

    tags = " ".join(
        t for t in str(item.get("hashtags", "")).split() if t.startswith("#")
    )
    if tags:
        parts.extend(["<hr>", "<p><strong>Hashtags</strong></p>", f'<p style="line-height:1.8">{html.escape(tags)}</p>'])

    parts.append(
        "<p><em>Prices, product details and availability may change. Check the seller's listing before ordering.</em></p>"
    )
    return "\n".join(parts)


# Save the originals, then replace the functions used by BloggerApp.
app._original_product_data = app.product_data
app._original_make_html = app.make_html
app.product_data = fixed_product_data
app.make_html = fixed_make_html

if __name__ == "__main__":
    app.main()
