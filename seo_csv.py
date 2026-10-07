import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "seo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_RULES = {
    "cnc": ["CNC", "CNCRouter", "CNCmachine", "Woodworking", "Engraving", "Machining", "DIY"],
    "jewelry": ["Jewelry", "FashionJewelry", "Accessories", "GiftIdeas", "Style", "Fashion"],
    "motorcycle": ["Motorcycle", "MotorcycleAccessories", "BikeGear", "Motorbike", "Rider", "Moto"],
    "watch": ["Watches", "Watch", "Fashion", "Accessories", "GiftIdeas", "Style"],
    "tool": ["Tools", "HandTools", "PowerTools", "Workshop", "DIY", "Hardware"],
    "deal": ["Deals", "OnlineShopping", "BestDeals", "Shopping", "Savings", "Finds"],
    "computer": ["Computer", "Technology", "Gadgets", "Electronics", "Tech", "Accessories"],
}

def clean(text):
    text = str(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def detect_category(filename, row_text):
    s = (filename + " " + row_text).lower()
    if "cnc" in s or "router" in s:
        return "cnc"
    if "jewelry" in s or "jewellery" in s or "bracelet" in s or "necklace" in s:
        return "jewelry"
    if "motorcycle" in s or "motorbike" in s:
        return "motorcycle"
    if "watch" in s:
        return "watch"
    if "tool" in s or "hardware" in s:
        return "tool"
    if "computer" in s or "office" in s or "electronic" in s:
        return "computer"
    return "deal"

def get_product_text(row):
    preferred = [
        "Product Desc", "Product Description", "Title", "Product Title",
        "Product Name", "Name", "Description"
    ]
    parts = []
    for key in preferred:
        if key in row and row[key]:
            parts.append(clean(row[key]))
    if not parts:
        for key, value in row.items():
            if value and key not in {"Image Url", "Video Url", "Promotion Url"}:
                parts.append(clean(value))
    return " ".join(parts)[:900]

def make_title(text):
    return re.sub(r"\s+", " ", clean(text))[:180].rstrip(" .,-")

def make_description(title, category):
    names = {
        "cnc": "CNC and workshop projects",
        "jewelry": "fashion and everyday styling",
        "motorcycle": "motorcycle and riding needs",
        "watch": "everyday style and accessories",
        "tool": "workshop, repair and DIY projects",
        "computer": "technology and everyday use",
        "deal": "everyday shopping and useful finds",
    }
    templates = {
        "cnc": f"Explore {title}. This product is designed for CNC and workshop projects, with practical features for makers, DIY users and professionals. A useful choice for engraving, cutting, fabrication or workshop tasks where the right equipment matters. Check the product details, available options and current offer before ordering.",
        "jewelry": f"Discover {title}, a versatile choice for {names[category]}. Its design makes it easy to pair with different looks and occasions, whether for everyday wear or as a gift. Check the product details, available styles and current offer before ordering.",
        "motorcycle": f"Check out {title}, a practical option for {names[category]}. Designed to complement your bike setup and riding needs, it can be a useful addition for riders looking for functionality and value. Review compatibility, specifications and available options before ordering.",
        "watch": f"Discover {title}, a stylish choice for {names[category]}. It is suitable for everyday outfits, casual looks and gifting. Check the product specifications, available designs and current offer to find the option that fits your style.",
        "tool": f"Explore {title}, a practical option for {names[category]}. It can help with everyday repairs, maintenance, workshop tasks and DIY projects. Review the specifications, compatibility and available options before ordering.",
        "computer": f"Discover {title}, a useful choice for {names[category]}. It is designed to support practical everyday tasks and can be a convenient addition to your setup. Check specifications, compatibility, available options and the current offer before ordering.",
        "deal": f"Discover {title}, a useful find for {names[category]}. Review the product details, available options and current offer to see whether it matches what you need. Check specifications and compatibility before ordering.",
    }
    return templates[category]

def make_hashtags(title, category):
    tags = []
    for word in re.findall(r"[A-Za-z0-9]+", title):
        if len(word) >= 4 and word.lower() not in {"with", "this", "that", "from", "for", "and", "the"}:
            tags.append("#" + word)
        if len(tags) >= 2:
            break
    for tag in CATEGORY_RULES[category]:
        h = "#" + tag
        if h.lower() not in {x.lower() for x in tags}:
            tags.append(h)
        if len(tags) >= 8:
            break
    return " ".join(tags)

def process_file(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(10000)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not fieldnames:
        return 0

    for row in rows:
        source = get_product_text(row)
        title = make_title(source)
        category = detect_category(path.name, source)
        row["SEO_Description"] = make_description(title, category)
        row["Hashtags"] = make_hashtags(title, category)

    out = OUTPUT_DIR / path.name
    output_fields = fieldnames + [x for x in ["SEO_Description", "Hashtags"] if x not in fieldnames]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="all")
    args = parser.parse_args()

    files = sorted(ROOT.glob("*.csv"))
    if args.file != "all":
        target = ROOT / args.file
        files = [target] if target.exists() else []

    if not files:
        raise SystemExit("No CSV files found.")

    total = 0
    for path in files:
        count = process_file(path)
        total += count
        print(f"Processed {path.name}: {count} rows")

    print(f"TOTAL: {total} rows")
    print(f"OUTPUT: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
