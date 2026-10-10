import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

CATEGORY_RULES = {
    "cnc": ["#CNC", "#CNCRouter", "#Woodworking", "#Engraving", "#Machining", "#DIY"],
    "jewelry": ["#Jewelry", "#FashionJewelry", "#Accessories", "#GiftIdeas", "#Style", "#Fashion"],
    "motorcycle": ["#Motorcycle", "#MotorcycleAccessories", "#BikeGear", "#Motorbike", "#Rider", "#Moto"],
    "watch": ["#Watches", "#Watch", "#Fashion", "#Accessories", "#GiftIdeas", "#Style"],
    "tool": ["#Tools", "#HandTools", "#PowerTools", "#Workshop", "#DIY", "#Hardware"],
    "computer": ["#Computer", "#Technology", "#Gadgets", "#Electronics", "#Tech", "#Accessories"],
    "clothing_men": ["#MensFashion", "#MensClothing", "#MensStyle", "#OutfitIdeas", "#Fashion"],
    "clothing_women": ["#WomensFashion", "#WomensClothing", "#WomensStyle", "#OutfitIdeas", "#Fashion"],
    "deal": ["#Deals", "#OnlineShopping", "#BestDeals", "#Shopping", "#Savings", "#Finds"],
}

def clean(value):
    value = str(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def detect_category(filename, text):
    s = (filename + " " + text).lower()
    if any(x in s for x in ("ملابس نسائية", "women", "woman", "womens", "ladies", "female")):
        return "clothing_women"
    if any(x in s for x in ("ملابس رجالية", "men's", "mens", "men clothing", "male")):
        return "clothing_men"
    if "cnc" in s or "router" in s or "woodworking" in s or "engraving" in s:
        return "cnc"
    if any(x in s for x in ("jewelry", "jewellery", "bracelet", "necklace", "earring", "ring")):
        return "jewelry"
    if "motorcycle" in s or "motorbike" in s or "motorcycle accessories" in s:
        return "motorcycle"
    if "watch" in s or "watches" in s:
        return "watch"
    if any(x in s for x in ("tool", "hardware", "drill", "screwdriver")):
        return "tool"
    if any(x in s for x in ("computer", "office", "electronic", "laptop", "keyboard", "gadget")):
        return "computer"
    return "deal"

def product_title(row):
    preferred = [
        "Product Desc", "Product Description", "Title", "Product Title",
        "Product Name", "Name", "Description", "商品名称", "Product"
    ]
    for key in preferred:
        if key in row and clean(row.get(key)):
            return clean(row[key])[:220]
    for key, value in row.items():
        if value and key not in {"Image Url", "Video Url", "Promotion Url"}:
            return clean(value)[:220]
    return "Useful product find"

def make_description(title, category):
    templates = {
        "cnc": f"Discover {title}. A useful option for CNC machining, woodworking, engraving and workshop projects. Review the product specifications, supported materials, dimensions and compatibility before ordering. Check the latest price and available options.",
        "jewelry": f"Discover {title}, a versatile accessory for everyday outfits, special occasions or gifting. Explore the available styles and details to find an option that suits your look. Check product information, materials and the latest offer before ordering.",
        "motorcycle": f"Explore {title}, an option for motorcycle owners and riders. Before purchasing, check the specifications, fitment and compatibility with your motorcycle model, along with the available options and current offer.",
        "watch": f"Discover {title}, an accessory for everyday style, work or gifting. Review the product details, dimensions, materials and available designs to choose the option that fits your needs. Check the latest offer before ordering.",
        "tool": f"Explore {title}, a practical option for workshop tasks, repairs and DIY projects. Review the specifications, size, included accessories and compatibility before ordering, and check the current offer and available options.",
        "computer": f"Discover {title}, a useful technology or computer accessory for everyday tasks. Check the technical specifications, connection type, dimensions and compatibility with your devices before ordering. Review available options and the latest offer.",
        "clothing_men": f"Discover {title}, an option for men's everyday style, casual outfits or special occasions. Check the size chart, measurements, fabric details and available colours before ordering to help choose the right fit. Review the current offer and product options.",
        "clothing_women": f"Discover {title}, a fashion option for women's everyday outfits, occasions or seasonal styling. Check the size chart, measurements, fabric details and available colours before ordering to help choose the right fit. Review the current offer and product options.",
        "deal": f"Discover {title}, a useful find to consider for everyday needs or gifting. Review the product specifications, dimensions, compatibility and available options to see whether it fits your requirements. Check the latest price and offer before ordering.",
    }
    return templates[category]

def hashtags(title, category):
    result = []
    ignored = {"with", "this", "that", "from", "for", "and", "the", "your", "best", "new"}
    for word in re.findall(r"[A-Za-z0-9]+", title):
        if len(word) >= 4 and word.lower() not in ignored:
            tag = "#" + word
            if tag.lower() not in {x.lower() for x in result}:
                result.append(tag)
        if len(result) >= 2:
            break
    for tag in CATEGORY_RULES[category]:
        if tag.lower() not in {x.lower() for x in result}:
            result.append(tag)
        if len(result) >= 8:
            break
    return " ".join(result)

def process_csv(source):
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(12000)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("The selected CSV has no header row.")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # Keep every original column and value; only add/update the two SEO columns.
    output_fields = fieldnames[:]
    for name in ("SEO_Description", "Hashtags"):
        if name not in output_fields:
            output_fields.append(name)

    for row in rows:
        title = product_title(row)
        category = detect_category(source.name, title)
        row["SEO_Description"] = make_description(title, category)
        row["Hashtags"] = hashtags(title, category)

    target = source.with_name(source.stem + "_SEO.csv")
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return target, len(rows)

def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo(
        "DealZone CSV SEO",
        "اختار CSV اللي بغيتي نعالجو. غادي يتصاوب ملف جديد باسم _SEO.csv، والأصل غادي يبقى بلا تغيير.",
        parent=root
    )
    chosen = filedialog.askopenfilename(
        title="Choose a CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if not chosen:
        messagebox.showinfo("Cancelled", "ما اخترتي حتى ملف.", parent=root)
        root.destroy()
        return
    source = Path(chosen)
    try:
        target, count = process_csv(source)
        messagebox.showinfo(
            "Done",
            f"سالينا بنجاح!\n\nProducts processed: {count}\n\nOutput file:\n{target}",
            parent=root
        )
    except Exception as exc:
        messagebox.showerror("Error", f"ما قدرناش نعالجو الملف:\n{exc}", parent=root)
    finally:
        root.destroy()

if __name__ == "__main__":
    main()
