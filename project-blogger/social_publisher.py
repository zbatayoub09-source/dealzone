import csv
import hashlib
import html
import json
import re
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = APP_DIR / "social_publisher_settings.json"
LOG_FILE = APP_DIR / "social_publisher_log.csv"

PLATFORMS = [
    ("Facebook", "Facebook"),
    ("Instagram", "Instagram"),
    ("TikTok", "TikTok"),
    ("YouTube", "Youtube"),
    ("Pinterest", "Pinterest"),
    ("Threads", "Threads"),
]

def clean(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def field(row, names):
    lookup = {str(k).strip().lower(): k for k in row if k is not None}
    for name in names:
        key = lookup.get(name.lower())
        if key is not None and clean(row.get(key)):
            return clean(row.get(key))
    return ""

def load_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(16000)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("CSV ma fihch row dyal l-headers.")
        rows = list(reader)
        if not rows:
            raise ValueError("CSV ma fih ta product.")
        return rows, reader.fieldnames

def make_item(row, index):
    title = field(row, ["Product Title", "Title", "Product Name", "Name", "Product Desc", "Product Description", "Description", "Product"])
    if not title:
        title = f"DealZone product {index}"
    title = title[:180]
    desc = field(row, ["SEO_Description", "SEO Description", "Product Description", "Product Desc", "Description"])
    if len(desc) < 80:
        desc = f"Discover {title}. Explore product features and details. Check compatibility, customer reviews, current price and delivery information on the seller's page before ordering."
    desc = desc[:2000]
    raw_tags = field(row, ["Hashtags", "SEO_Hashtags", "Tags"])
    tags = re.findall(r"#[A-Za-z0-9_]+", raw_tags)
    if len(tags) < 3:
        stop = {"with", "from", "this", "that", "and", "the", "for", "new", "hot", "best", "sale"}
        words = re.findall(r"[A-Za-z0-9]+", title.lower())
        tags = list(dict.fromkeys(tags + ["#" + w for w in words if len(w) >= 3 and w not in stop]))
        tags += ["#DealZone", "#OnlineShopping", "#ProductFinds"]
    tags = " ".join(list(dict.fromkeys(tags))[:8])
    image = field(row, ["Image Url", "Image URL", "Image", "ImageUrl", "Main Image"])
    link = field(row, ["Promotion Url", "Promotion URL", "Product Url", "Product URL", "Affiliate Link", "Link", "URL"])
    pid = field(row, ["ProductId", "Product ID", "Item ID", "ID"])
    key = hashlib.sha256((pid or link or title).encode("utf-8", errors="ignore")).hexdigest()
    return {"title": title, "description": desc, "hashtags": tags, "image": image, "link": link, "key": key}

def write_csv(path, rows, headers):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

class SocialPublisher:
    def __init__(self, root):
        self.root = root
        root.title("DealZone Social Publisher")
        root.geometry("850x760")
        root.minsize(760, 650)
        self.csv_path = ""
        self.rows = []
        self.selected = {}
        self.csv_var = tk.StringVar(value="Ma khtart ta CSV")
        self.status = tk.StringVar(value="Khtar CSV bach tbda.")
        self.limit = tk.StringVar(value="20")
        self.output_dir = tk.StringVar(value=str(APP_DIR / "output"))
        self.build()

    def build(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="DEALZONE SOCIAL PUBLISHER", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="CSV products • SEO descriptions • hashtags • platform-ready export", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 14))

        ttk.Label(main, text="1. CSV dyal AliExpress").pack(anchor="w")
        r = ttk.Frame(main); r.pack(fill="x", pady=5)
        ttk.Entry(r, textvariable=self.csv_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Choose CSV", command=self.choose_csv).pack(side="left", padx=(8,0))

        ttk.Label(main, text="2. Chno mn platform bghiti? (selection kat7edded fin bghiti tجهز المحتوى)").pack(anchor="w", pady=(12,4))
        pf = ttk.Frame(main); pf.pack(fill="x")
        for i, (label, _) in enumerate(PLATFORMS):
            v = tk.BooleanVar(value=label in ("Facebook", "Instagram", "Pinterest"))
            self.selected[label] = v
            ttk.Checkbutton(pf, text=label, variable=v).grid(row=i//3, column=i%3, sticky="w", padx=(0,22), pady=3)

        ttk.Label(main, text="3. Max products f had l-run").pack(anchor="w", pady=(12,4))
        ttk.Entry(main, textvariable=self.limit, width=10).pack(anchor="w")
        ttk.Label(main, text="4. Output folder").pack(anchor="w", pady=(12,4))
        out = ttk.Frame(main); out.pack(fill="x")
        ttk.Entry(out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(out, text="Browse", command=self.choose_output).pack(side="left", padx=(8,0))

        ttk.Label(main, text="5. Preview").pack(anchor="w", pady=(14,4))
        self.preview = tk.Text(main, height=12, wrap="word", font=("Segoe UI", 9))
        self.preview.pack(fill="both", expand=True)
        buttons = ttk.Frame(main); buttons.pack(fill="x", pady=(12,4))
        ttk.Button(buttons, text="Preview first product", command=self.preview_first).pack(side="left")
        ttk.Button(buttons, text="Generate platform CSV files", command=self.generate).pack(side="left", padx=8)
        ttk.Label(main, textvariable=self.status, wraplength=800).pack(anchor="w", pady=(6,0))
        ttk.Label(main, text="Important: this first version prepares files; it does not publish directly to social accounts. Direct posting needs each platform's approved API and account permissions. Blogger is intentionally not included.", wraplength=800).pack(anchor="w", pady=(8,0))

    def choose_csv(self):
        path = filedialog.askopenfilename(title="Choose AliExpress CSV", filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if not path: return
        try:
            rows, headers = load_csv(path)
            self.csv_path, self.rows, self.headers = path, rows, headers
            self.csv_var.set(path)
            self.status.set(f"CSV wajed: {len(rows)} products.")
            self.preview_first()
        except Exception as e:
            messagebox.showerror("CSV error", str(e))

    def choose_output(self):
        p = filedialog.askdirectory(title="Choose output folder")
        if p: self.output_dir.set(p)

    def preview_first(self):
        if not self.rows:
            messagebox.showwarning("Choose CSV", "Khtar CSV lwl."); return
        item = make_item(self.rows[0], 1)
        self.preview.delete("1.0", "end")
        self.preview.insert("end", f"TITLE\n{item['title']}\n\nSEO DESCRIPTION\n{item['description']}\n\nHASHTAGS\n{item['hashtags']}\n\nIMAGE\n{item['image']}\n\nPRODUCT LINK\n{item['link']}")

    def generate(self):
        if not self.rows:
            messagebox.showwarning("Choose CSV", "Khtar CSV lwl."); return
        platforms = [p for p, v in self.selected.items() if v.get()]
        if not platforms:
            messagebox.showwarning("Choose platform", "Khtar platform wa7da 3la l-a9al."); return
        try:
            limit = int(self.limit.get())
            if limit < 1: raise ValueError()
        except ValueError:
            messagebox.showerror("Limit", "Dkhel ra9m kber men 0."); return
        try:
            out = Path(self.output_dir.get()).expanduser()
            out.mkdir(parents=True, exist_ok=True)
            selected_rows = self.rows[:limit]
            made = []
            for platform in platforms:
                result = []
                for i, row in enumerate(selected_rows, 1):
                    item = make_item(row, i)
                    caption = f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}"
                    result.append({
                        "Platform": platform,
                        "ProductId": field(row, ["ProductId", "Product ID", "Item ID", "ID"]),
                        "Title": item["title"],
                        "Text": caption,
                        "Description": item["description"],
                        "Hashtags": item["hashtags"],
                        "Image Url": item["image"],
                        "Promotion Url": item["link"],
                        "Deduplication Key": item["key"],
                    })
                dest = out / f"{platform.lower()}_ready.csv"
                write_csv(dest, result, ["Platform","ProductId","Title","Text","Description","Hashtags","Image Url","Promotion Url","Deduplication Key"])
                made.append(str(dest))
            self.status.set(f"Saliw {len(selected_rows)} products f {len(platforms)} platform files.")
            messagebox.showinfo("Done", "Tوجدات الملفات:\n\n" + "\n".join(made) + "\n\nHad l-version katوجد CSV, ma katnشرch direct l-accounts.")
        except Exception as e:
            messagebox.showerror("Export error", str(e))

def main():
    root = tk.Tk()
    try: ttk.Style().theme_use("clam")
    except Exception: pass
    SocialPublisher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
