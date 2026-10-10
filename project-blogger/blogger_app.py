import csv
import hashlib
import html
import json
import re
import threading
import time
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
CLIENT_FILE = APP_DIR / "client_secret.json"
TOKEN_FILE = APP_DIR / "blogger_token.json"
STATE_FILE = APP_DIR / "published_state.json"
SCOPES = ["https://www.googleapis.com/auth/blogger"]
CSV_PATH = None
BLOGS = []
SERVICE = None
STOP_REQUESTED = False

def clean(value):
    value = str(value or "")
    value = re.sub(r"<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def get_value(row, names):
    lowered = {str(k).strip().lower(): k for k in row.keys() if k is not None}
    for name in names:
        key = lowered.get(name.lower())
        if key is not None and clean(row.get(key)):
            return clean(row.get(key))
    return ""

def load_rows(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(12000)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("CSV ma fihch header row.")
        return list(reader)

def make_seo_description(title, existing=""):
    existing = clean(existing)
    if len(existing) >= 80:
        return existing[:2000]
    base = f"Discover {title}. Explore key features, product details and available options. Check compatibility, customer reviews, current price and delivery information on the product page before ordering."
    return base[:2000]

def make_hashtags(title, existing=""):
    existing = clean(existing)
    found = re.findall(r"#[A-Za-z0-9_]+", existing)
    if len(found) >= 3:
        return " ".join(dict.fromkeys(found))[:500]
    stop = {"with", "from", "this", "that", "and", "the", "for", "new", "hot", "best", "sale", "set"}
    words = re.findall(r"[A-Za-z0-9]+", title.lower())
    tags = []
    for word in words:
        if len(word) >= 3 and word not in stop:
            tag = "#" + word
            if tag not in tags:
                tags.append(tag)
    tags += ["#DealZone", "#OnlineShopping", "#ProductFinds"]
    return " ".join(tags[:8])

def product_data(row, index):
    title = get_value(row, ["Product Title", "Title", "Product Name", "Name", "Product Desc", "Product Description", "Description", "Product"])
    if not title:
        title = "DealZone product " + str(index)
    title = title[:180]
    description = get_value(row, ["SEO_Description", "SEO Description", "Product Description", "Product Desc", "Description"])
    description = make_seo_description(title, description if description != title else "")
    hashtags = make_hashtags(title, get_value(row, ["Hashtags", "SEO_Hashtags", "Tags"]))
    image = get_value(row, ["Image Url", "Image URL", "Image", "ImageUrl", "Main Image"])
    link = get_value(row, ["Promotion Url", "Promotion URL", "Product Url", "Product URL", "Affiliate Link", "Link", "URL"])
    product_id = get_value(row, ["ProductId", "Product ID", "Item ID", "ID"])
    stable = product_id or link or title
    fingerprint = hashlib.sha256(stable.encode("utf-8", errors="ignore")).hexdigest()
    return {"title": title, "description": description, "hashtags": hashtags, "image": image, "link": link, "key": fingerprint}

def make_html(item):
    # Blogger post body: readable description, visible hashtags, and a styled CTA button.
    parts = [
        f"<h2>{html.escape(item['title'])}</h2>",
        "<hr>",
        "<h3>Product Details</h3>",
        f"<p>{html.escape(item['description'])}</p>",
    ]
    if item["image"].startswith(("https://", "http://")):
        image_html = f'<img src="{html.escape(item["image"], quote=True)}" alt="{html.escape(item["title"], quote=True)}" style="max-width:100%;height:auto;border:0">'
        if item["link"].startswith(("https://", "http://")):
            parts.append(f'<p><a href="{html.escape(item["link"], quote=True)}" rel="nofollow sponsored">{image_html}</a></p>')
        else:
            parts.append(f"<p>{image_html}</p>")
    if item["link"].startswith(("https://", "http://")):
        parts.append(
            '<p style="text-align:center;margin:24px 0">'
            f'<a href="{html.escape(item["link"], quote=True)}" rel="nofollow sponsored" '
            'style="display:inline-block;background-color:#fe4f4f;color:#ffffff;'
            'padding:14px 24px;border-radius:6px;text-decoration:none;font-weight:bold;'
            'font-size:16px;border:1px solid #fe4f4f">'
            'CHECK PRICE &amp; DETAILS</a></p>'
        )
    tags = " ".join(t for t in item["hashtags"].split() if t.startswith("#"))
    if tags:
        parts.append("<hr>")
        parts.append("<p><strong>Hashtags</strong></p>")
        parts.append(f'<p style="line-height:1.8">{html.escape(tags)}</p>')
    parts.append("<p><em>Prices, product details and availability may change. Check the seller's listing before ordering.</em></p>")
    return "\n".join(parts)

def auth_service():
    global SERVICE
    if not CLIENT_FILE.exists():
        raise FileNotFoundError("Ma l9itch client_secret.json. 7etto f nafs folder dyal RUN.bat.")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    SERVICE = build("blogger", "v3", credentials=creds, cache_discovery=False)
    return SERVICE

def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

class BloggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Blogger | DealZone")
        self.root.geometry("760x600")
        self.root.minsize(680, 520)
        self.blog_var = tk.StringVar()
        self.csv_var = tk.StringVar(value="Mazal ma khtart ta CSV")
        self.mode_var = tk.StringVar(value="draft")
        self.status_var = tk.StringVar(value="Connecti Blogger bach tbda.")
        self.limit_var = tk.StringVar(value="20")
        self.blog_map = {}
        self.rows = []
        self.connected = False
        self.build_ui()

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="PROJECT BLOGGER", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="CSV  →  SEO Description + Hashtags  →  Blogger", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 16))
        style = ttk.Style()
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9))
        style.configure("TButton", padding=(8, 5))

        top = ttk.Frame(outer)
        top.pack(fill="x", pady=5)
        self.connect_btn = ttk.Button(top, text="1. Connect Blogger", command=self.connect)
        self.connect_btn.pack(side="left")
        self.connection_label = ttk.Label(top, text="Not connected")
        self.connection_label.pack(side="left", padx=12)

        ttk.Label(outer, text="2. Choose your Blogger blog").pack(anchor="w", pady=(14, 4))
        blogrow = ttk.Frame(outer)
        blogrow.pack(fill="x")
        self.blog_combo = ttk.Combobox(blogrow, textvariable=self.blog_var, state="readonly")
        self.blog_combo.pack(side="left", fill="x", expand=True)

        ttk.Label(outer, text="3. Choose a CSV file").pack(anchor="w", pady=(14, 4))
        csvrow = ttk.Frame(outer)
        csvrow.pack(fill="x")
        ttk.Entry(csvrow, textvariable=self.csv_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(csvrow, text="Browse CSV", command=self.choose_csv).pack(side="left", padx=(8, 0))

        ttk.Label(outer, text="4. Publishing mode").pack(anchor="w", pady=(14, 4))
        modes = ttk.Frame(outer)
        modes.pack(anchor="w")
        ttk.Radiobutton(modes, text="Draft (recommended)", variable=self.mode_var, value="draft").pack(side="left", padx=(0, 16))
        ttk.Radiobutton(modes, text="Publish publicly", variable=self.mode_var, value="publish").pack(side="left")

        limits = ttk.Frame(outer)
        limits.pack(fill="x", pady=(14, 4))
        ttk.Label(limits, text="Max posts this run:").pack(side="left")
        ttk.Entry(limits, textvariable=self.limit_var, width=8).pack(side="left", padx=8)
        ttk.Label(limits, text="(start with 5–20 to test)").pack(side="left")

        self.start_btn = ttk.Button(outer, text="🚀  START BLOGGER", style="Primary.TButton", command=self.start_publish)
        self.start_btn.pack(anchor="w", pady=(16, 10))
        self.progress = ttk.Progressbar(outer, mode="determinate")
        self.progress.pack(fill="x", pady=3)
        ttk.Label(outer, textvariable=self.status_var, wraplength=700).pack(anchor="w", pady=(5, 6))
        ttk.Label(outer, text="Note: CSV and client_secret.json stay on this computer. Original CSV is not changed.", wraplength=700).pack(anchor="w", pady=(8, 0))

    def connect(self):
        self.connect_btn.configure(state="disabled")
        self.status_var.set("Kanrbt m3a Google Blogger...")
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        try:
            service = auth_service()
            result = service.blogs().listByUser(userId="self").execute()
            blogs = result.get("items", [])
            if not blogs:
                raise RuntimeError("Ma ban 7ta blog f had Google account.")
            self.root.after(0, lambda: self._connected(blogs))
        except Exception as e:
            self.root.after(0, lambda err=str(e): self._connect_error(err))

    def _connected(self, blogs):
        global BLOGS
        BLOGS = blogs
        self.blog_map = {f"{b.get('name','Blogger')} — {b.get('url','')}": b for b in blogs}
        self.blog_combo["values"] = list(self.blog_map.keys())
        self.blog_combo.current(0)
        self.connection_label.configure(text="Connected ✓")
        self.status_var.set(f"Connected. L9ina {len(blogs)} blog(s).")
        self.connect_btn.configure(state="normal", text="Reconnect Blogger")
        self.connected = True

    def _connect_error(self, message):
        self.connect_btn.configure(state="normal")
        self.status_var.set("Connection failed.")
        messagebox.showerror("Blogger connection error", message + "\n\nT2akked men client_secret.json w Blogger API.")
    
    def choose_csv(self):
        filename = filedialog.askopenfilename(title="Choose product CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not filename:
            return
        try:
            self.rows = load_rows(filename)
            if not self.rows:
                raise ValueError("Had CSV ma fih ta product rows.")
            self.csv_var.set(filename)
            self.status_var.set(f"CSV ready: {len(self.rows)} products. SEO descriptions and hashtags will be generated when missing.")
        except Exception as e:
            messagebox.showerror("CSV error", str(e))

    def start_publish(self):
        if not self.connected or not SERVICE:
            messagebox.showwarning("Connect first", "Klik 3la Connect Blogger lwl.")
            return
        if not self.rows:
            messagebox.showwarning("Choose CSV", "Khtar CSV lwl.")
            return
        blog_key = self.blog_var.get()
        if blog_key not in self.blog_map:
            messagebox.showwarning("Choose blog", "Khtar blog men l-list.")
            return
        try:
            limit = int(self.limit_var.get())
            if limit < 1:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid limit", "Max posts khas ykon ra9m kber men 0.")
            return
        blog = self.blog_map[blog_key]
        mode = self.mode_var.get()
        if mode == "publish":
            ok = messagebox.askyesno("Confirm public publishing", f"Ghadi tnشر max {limit} posts مباشرة للعموم f:\n{blog.get('name')}\n\nWash met2akked?")
            if not ok:
                return
        self.start_btn.configure(state="disabled")
        self.progress["maximum"] = min(limit, len(self.rows))
        self.progress["value"] = 0
        threading.Thread(target=self._publish_worker, args=(blog, mode, limit), daemon=True).start()

    def _publish_worker(self, blog, mode, limit):
        state = load_state()
        file_key = str(Path(self.csv_var.get()).resolve())
        file_state = state.setdefault(file_key, {})
        done = 0
        skipped = 0
        errors = 0
        candidates = []
        for i, row in enumerate(self.rows, start=1):
            item = product_data(row, i)
            if item["key"] in file_state:
                skipped += 1
                continue
            candidates.append((i, item))
            if len(candidates) >= limit:
                break
        total = len(candidates)
        if not total:
            self.root.after(0, lambda: self._publish_finished(0, skipped, errors, "No new products left in this CSV."))
            return
        for n, (i, item) in enumerate(candidates, start=1):
            try:
                body = {"kind": "blogger#post", "blog": {"id": blog["id"]}, "title": item["title"], "content": make_html(item)}
                result = SERVICE.posts().insert(blogId=blog["id"], body=body, isDraft=(mode == "draft")).execute()
                file_state[item["key"]] = {"post_id": result.get("id"), "url": result.get("url"), "mode": mode, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_state(state)
                done += 1
                self.root.after(0, lambda n=n, total=total, item=item: self._update_progress(n, total, item["title"]))
            except Exception as e:
                errors += 1
                self.root.after(0, lambda msg=str(e), title=item["title"]: self.status_var.set(f"Error on {title[:50]}: {msg[:180]}"))
            time.sleep(0.3)
        self.root.after(0, lambda: self._publish_finished(done, skipped, errors, f"Finished: {done} new posts. Mode: {mode.upper()}."))

    def _update_progress(self, n, total, title):
        self.progress["maximum"] = total
        self.progress["value"] = n
        self.status_var.set(f"{n}/{total}: {title[:100]}")

    def _publish_finished(self, done, skipped, errors, message):
        self.start_btn.configure(state="normal")
        self.status_var.set(f"{message} Previously processed/skipped: {skipped}. Errors: {errors}.")
        messagebox.showinfo("Blogger run finished", f"{message}\nSkipped already recorded: {skipped}\nErrors: {errors}\n\nCheck Blogger Posts to confirm.")

def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    BloggerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
