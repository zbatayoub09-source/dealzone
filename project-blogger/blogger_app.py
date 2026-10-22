import csv
import hashlib
import html
import json
import re
import threading
import time
import webbrowser
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
CLIENT_FILE = APP_DIR / "client_secret.json"
TOKEN_FILE = APP_DIR / "blogger_token.json"
STATE_FILE = APP_DIR / "published_state.json"
FACEBOOK_CONFIG_FILE = APP_DIR / "facebook_config.json"
SCOPES = ["https://www.googleapis.com/auth/blogger"]
CSV_PATH = None
BLOGS = []
SERVICE = None
STOP_REQUESTED = False
GRAPH_BASE = "https://graph.facebook.com/v26.0"
THREADS_BASE = "https://graph.threads.net/v1.0"
GEMINI_MODEL = "gemini-2.5-flash"

def meta_post(endpoint, params, base=GRAPH_BASE):
    payload = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(f"{base}/{endpoint.lstrip('/')}", data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
            err = data.get("error", {})
            raise RuntimeError(f"Meta API ({err.get('code')}): {err.get('message', 'API error')}")
        except (ValueError, json.JSONDecodeError):
            raise RuntimeError(f"Meta API HTTP error: {exc.code}")
    if data.get("error"):
        err = data["error"]
        raise RuntimeError(f"Meta API ({err.get('code')}): {err.get('message', 'API error')}")
    return data

def publish_instagram(item, page, caption):
    image_url = str(item.get("image", "") or "").strip()
    if not image_url.startswith("https://"):
        raise RuntimeError("Instagram kay7taj Image URL public b HTTPS f had l-version.")
    ig_id = str((page.get("instagram_business_account") or {}).get("id", "")).strip()
    page_token = str(page.get("access_token", "")).strip()
    if not ig_id or not page_token:
        raise RuntimeError("Had Facebook Page ma مربوطةش b Instagram Professional, ola token ma fihch access.")
    container = meta_post(f"{ig_id}/media", {"image_url": image_url, "caption": caption[:2200], "access_token": page_token})
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError("Instagram ma rje3ch media container ID.")
    published = meta_post(f"{ig_id}/media_publish", {"creation_id": creation_id, "access_token": page_token})
    if not published.get("id"):
        raise RuntimeError("Instagram ma أكدش النشر.")
    return published["id"]

def publish_threads(item, user_id, token, caption):
    image_url = str(item.get("image", "") or "").strip()
    params = {"access_token": token, "text": caption[:500]}
    if image_url.startswith("https://"):
        params.update({"media_type": "IMAGE", "image_url": image_url})
    else:
        params.update({"media_type": "TEXT"})
    container = meta_post(f"{user_id}/threads", params, base=THREADS_BASE)
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError("Threads ma rje3ch creation ID.")
    published = meta_post(f"{user_id}/threads_publish", {"creation_id": creation_id, "access_token": token}, base=THREADS_BASE)
    if not published.get("id"):
        raise RuntimeError("Threads ma أكدش النشر.")
    return published["id"]

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

def gemini_hashtags(title, description, api_key):
    """Generate product-specific social hashtags with Gemini; never log or persist the API key."""
    prompt = (
        "Create 6 to 8 useful hashtags for this shopping product. "
        "Use relevant English keywords, CamelCase for multiword tags, include #DealZone, "
        "avoid spam and duplicates. Return ONLY the hashtags separated by spaces, no explanation.\n"
        f"Product title: {title[:300]}\nProduct details: {description[:900]}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 120}
    }
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + GEMINI_MODEL + ":generateContent?" + urllib.parse.urlencode({"key": api_key})
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_data = json.loads(exc.read().decode("utf-8"))
            message = error_data.get("error", {}).get("message", "Gemini API error")
        except Exception:
            message = "Gemini API HTTP error " + str(exc.code)
        raise RuntimeError("Gemini API: " + str(message)[:240])
    candidates = data.get("candidates", [])
    text_out = ""
    if candidates:
        text_out = " ".join(part.get("text", "") for part in candidates[0].get("content", {}).get("parts", []))
    tags = re.findall(r"#[A-Za-z0-9_]+", text_out)
    tags = list(dict.fromkeys(tags))
    if not tags:
        raise RuntimeError("Gemini ma rje3 ta hashtag صالح.")
    if "#DealZone" not in tags:
        tags.append("#DealZone")
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
    # If an old token lacks the Blogger scope, request consent again instead of
    # silently reusing credentials that cannot list or publish Blogger posts.
    if creds and creds.valid:
        try:
            if not creds.has_scopes(SCOPES):
                creds = None
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds or not creds.valid:
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
        self.root.geometry("780x760")
        self.root.minsize(700, 680)
        self.blog_var = tk.StringVar()
        self.csv_var = tk.StringVar(value="Mazal ma khtart ta CSV")
        self.mode_var = tk.StringVar(value="draft")
        self.status_var = tk.StringVar(value="Connecti Blogger bach tbda.")
        self.limit_var = tk.StringVar(value="20")
        self.blog_map = {}
        self.rows = []
        self.connected = False
        fb_config = self.load_facebook_config()
        self.facebook_user_token_var = tk.StringVar(value="")
        self.facebook_page_id_var = tk.StringVar(value="")
        self.facebook_pages = []
        self.facebook_enabled_var = tk.BooleanVar(value=bool(fb_config.get("facebook", fb_config.get("enabled", False))))
        self.instagram_enabled_var = tk.BooleanVar(value=bool(fb_config.get("instagram", False)))
        self.threads_enabled_var = tk.BooleanVar(value=bool(fb_config.get("threads", False)))
        self.threads_user_id_var = tk.StringVar(value="")
        self.threads_token_var = tk.StringVar(value="")
        self.gemini_api_key_var = tk.StringVar(value="")
        self.build_ui()

    def build_ui(self):
        # Scrollable main window: keeps the Start button reachable on smaller screens.
        shell = ttk.Frame(self.root)
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        outer = ttk.Frame(canvas, padding=18)
        window_id = canvas.create_window((0, 0), window=outer, anchor="nw")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_inner(event):
            canvas.itemconfigure(window_id, width=event.width)

        outer.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", resize_inner)

        def mousewheel(event):
            if getattr(event, "delta", 0):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", mousewheel)
        canvas.bind_all("<Button-4>", mousewheel)
        canvas.bind_all("<Button-5>", mousewheel)
        ttk.Label(outer, text="PROJECT BLOGGER", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Blogger → اختار المنصات اللي بغيتي تشارك فيها", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 16))
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

        ttk.Label(outer, text="5. Share public Blogger posts (select only what you want)").pack(anchor="w", pady=(14, 4))
        fbrow = ttk.Frame(outer)
        fbrow.pack(fill="x", pady=2)
        ttk.Checkbutton(fbrow, text="Facebook", variable=self.facebook_enabled_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(fbrow, text="Instagram", variable=self.instagram_enabled_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(fbrow, text="Threads", variable=self.threads_enabled_var).pack(side="left")
        ttk.Label(outer, text="Facebook User Access Token (with pages_show_list and Page posting permissions):").pack(anchor="w", pady=(5, 2))
        tokenrow = ttk.Frame(outer); tokenrow.pack(fill="x")
        ttk.Entry(tokenrow, textvariable=self.facebook_user_token_var, show="*").pack(side="left", fill="x", expand=True)
        ttk.Button(tokenrow, text="Load all Facebook Pages", command=self.load_facebook_pages).pack(side="left", padx=(8, 0))
        ttk.Label(outer, text="Paste Facebook Page ID or Facebook Page link, then click Select Page:").pack(anchor="w", pady=(5, 2))
        manual_page_row = ttk.Frame(outer); manual_page_row.pack(fill="x", pady=(0, 4))
        ttk.Entry(manual_page_row, textvariable=self.facebook_page_id_var).pack(side="left", fill="x", expand=True)
        ttk.Button(manual_page_row, text="Select Page by ID/link", command=self.select_facebook_page_by_id).pack(side="left", padx=(8, 0))
        ttk.Label(outer, text="Or select one or more loaded Pages below (Ctrl/Shift for multiple):").pack(anchor="w", pady=(5, 2))
        self.facebook_pages_list = tk.Listbox(outer, height=4, selectmode=tk.EXTENDED, exportselection=False)
        self.facebook_pages_list.pack(fill="x")
        ttk.Label(outer, text="Instagram kaykhdem b Facebook Page token, khas Instagram Professional mrbout b Page w Image URL public b HTTPS.", wraplength=700).pack(anchor="w", pady=(3, 0))
        ttk.Label(outer, text="Threads User ID:").pack(anchor="w", pady=(8, 2))
        ttk.Entry(outer, textvariable=self.threads_user_id_var).pack(fill="x")
        ttk.Label(outer, text="Threads Access Token (ila khtarti Threads):").pack(anchor="w", pady=(5, 2))
        ttk.Entry(outer, textvariable=self.threads_token_var, show="*").pack(fill="x")
        ttk.Label(outer, text="Tokens ma kayt7fedouch f GitHub w kayb9aw ghir f had session.", wraplength=700).pack(anchor="w", pady=(4, 0))
        ttk.Label(outer, text="6. Gemini API — optional: generate better hashtags per product").pack(anchor="w", pady=(14, 3))
        gemini_row = ttk.Frame(outer)
        gemini_row.pack(fill="x")
        ttk.Entry(gemini_row, textvariable=self.gemini_api_key_var, show="*").pack(side="left", fill="x", expand=True)
        ttk.Button(gemini_row, text="Get Gemini API key", command=lambda: webbrowser.open("https://aistudio.google.com/apikey")).pack(side="left", padx=(8, 0))
        ttk.Label(outer, text="API key kayb9a ghir f had session; ila khlitiha khawya, l-app ghadi تستعمل hashtags العادية.", wraplength=700).pack(anchor="w", pady=(3, 0))

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
        ttk.Label(outer, text="Note: CSV, Google credentials, and Facebook Page token stay on this computer. Original CSV is not changed.", wraplength=700).pack(anchor="w", pady=(8, 0))

    def load_facebook_config(self):
        try:
            return json.loads(FACEBOOK_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_facebook_config(self):
        # OAuth tokens are intentionally not saved in this settings file.
        selected = self.selected_facebook_pages()
        config = {"facebook": bool(self.facebook_enabled_var.get()),
                  "instagram": bool(self.instagram_enabled_var.get()),
                  "threads": bool(self.threads_enabled_var.get()),
                  "page_ids": [str(p.get("id", "")) for p in selected]}
        FACEBOOK_CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_facebook_pages(self):
        token = self.facebook_user_token_var.get().strip()
        if not token:
            messagebox.showwarning("Facebook token", "Dkhel User Access Token lwl.")
            return
        try:
            pages, after = [], None
            while True:
                params = {"fields": "id,name,access_token,tasks,instagram_business_account", "limit": "100", "access_token": token}
                if after:
                    params["after"] = after
                url = "https://graph.facebook.com/v26.0/me/accounts?" + urllib.parse.urlencode(params)
                request = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(request, timeout=35) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if data.get("error"):
                    raise RuntimeError(data["error"].get("message", "Facebook API error"))
                pages.extend(data.get("data", []))
                after = (data.get("paging", {}).get("cursors", {}) or {}).get("after")
                if not after or not data.get("data"):
                    break
            unique = {}
            for page in pages:
                if page.get("id") and page.get("access_token"):
                    # Instagram accounts linked to each Facebook Page are returned here
                    # when the token has the required permissions and the account is eligible.
                    page["instagram_business_account"] = page.get("instagram_business_account") or {}
                    unique[str(page["id"])] = page
            self.facebook_pages = list(unique.values())
            self.facebook_pages_list.delete(0, "end")
            old_ids = set(str(x) for x in self.load_facebook_config().get("page_ids", []))
            linked_count = 0
            for page in self.facebook_pages:
                ig = page.get("instagram_business_account") or {}
                ig_id = str(ig.get("id", "")).strip()
                if ig_id and page.get("access_token"):
                    try:
                        detail_params = urllib.parse.urlencode({
                            "fields": "id,username,name",
                            "access_token": page["access_token"],
                        })
                        detail_url = "https://graph.facebook.com/v26.0/" + urllib.parse.quote(ig_id, safe="") + "?" + detail_params
                        with urllib.request.urlopen(urllib.request.Request(detail_url, method="GET"), timeout=15) as response:
                            detail = json.loads(response.read().decode("utf-8"))
                        if not detail.get("error"):
                            ig.update(detail)
                        linked_count += 1
                    except Exception:
                        # Keep the linked IG ID even if username lookup is not permitted.
                        pass
                label = f"{page.get('name', 'Page')} | FB ID: {page.get('id', '')}"
                if ig_id:
                    label += f" | Instagram: @{ig.get('username')}" if ig.get("username") else f" | Instagram linked (ID: {ig_id})"
                else:
                    label += " | No Instagram linked"
                self.facebook_pages_list.insert("end", label)
                if str(page.get("id")) in old_ids:
                    self.facebook_pages_list.selection_set("end")
            self.status_var.set(f"Facebook: {len(self.facebook_pages)} Pages; Instagram linked: {linked_count}.")
            if not self.facebook_pages:
                messagebox.showwarning("No Pages", "Ma ban ta Page. T2ekked men permissions dyal token w access dyalek l-Pages.")
            else:
                messagebox.showinfo("Facebook & Instagram", f"L9ina {len(self.facebook_pages)} Facebook Pages. {linked_count} Pages 3andhom Instagram linked li ban l-API. Khtar Pages li bghiti.")
        except Exception as e:
            messagebox.showerror("Facebook error", str(e))

    def select_facebook_page_by_id(self):
        raw = self.facebook_page_id_var.get().strip()
        if not raw:
            messagebox.showwarning("Facebook Page ID", "Paste Page ID or Facebook Page link first.")
            return
        match = re.search(r"(?:[?&]id=|/pages/[^/?#]+/|/)([0-9]{6,})(?:[/?#&]|$)", raw)
        page_id = raw if raw.isdigit() else (match.group(1) if match else "")
        if not page_id:
            messagebox.showerror("Facebook Page ID", "Ma qdrtch nخرج Page ID men had lien. Paste numeric Page ID (ra9m) li f lien.")
            return
        for i, page in enumerate(self.facebook_pages):
            if str(page.get("id", "")) == page_id and page.get("access_token"):
                self.facebook_pages_list.selection_clear(0, "end")
                self.facebook_pages_list.selection_set(i)
                self.facebook_pages_list.see(i)
                self.status_var.set("Facebook Page selected: " + str(page.get("name", page_id)) + " (" + page_id + ")")
                return
        # If the page did not appear in /me/accounts, try resolving the supplied ID directly.
        try:
            token = self.facebook_user_token_var.get().strip()
            params = urllib.parse.urlencode({"fields": "id,name,access_token,tasks,instagram_business_account", "access_token": token})
            url = "https://graph.facebook.com/v26.0/" + urllib.parse.quote(page_id, safe="") + "?" + params
            request = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(request, timeout=30) as response:
                page = json.loads(response.read().decode("utf-8"))
            if page.get("id") and page.get("access_token"):
                self.facebook_pages.append(page)
                i = len(self.facebook_pages) - 1
                self.facebook_pages_list.insert("end", str(page.get("name", "Page")) + " | ID: " + str(page.get("id")))
                self.facebook_pages_list.selection_clear(0, "end")
                self.facebook_pages_list.selection_set(i)
                self.facebook_pages_list.see(i)
                self.status_var.set("Facebook Page selected: " + str(page.get("name", page_id)) + " (" + page_id + ")")
                return
        except Exception:
            pass
        messagebox.showerror("Page not available", "Facebook ma rje3ch Page Access Token l had ID. T2ekked belli user token 3ando access l Page w permissions dyal publishing. Ma ymkench n نشر b ID bo7do bla Page Access Token.")

    def selected_facebook_pages(self):
        if not hasattr(self, "facebook_pages_list"):
            return []
        return [self.facebook_pages[i] for i in self.facebook_pages_list.curselection()
                if 0 <= i < len(self.facebook_pages)]

    def share_to_facebook(self, item, post_url):
        if not self.facebook_enabled_var.get():
            return "disabled"
        pages = self.selected_facebook_pages()
        if not pages:
            raise ValueError("Facebook sharing enabled, but no Pages selected. Load Facebook Pages and select at least one.")
        message = f"{item['title']}\\n\\n{item['description']}\\n\\n{item['hashtags']}".strip()
        posted, errors = [], []
        for page in pages:
            page_id = str(page.get("id", ""))
            page_token = str(page.get("access_token", ""))
            payload = urllib.parse.urlencode({
                "message": message[:5000], "link": post_url, "access_token": page_token,
            }).encode("utf-8")
            request = urllib.request.Request(
                f"https://graph.facebook.com/v26.0/{urllib.parse.quote(page_id, safe='')}/feed",
                data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    result = json.loads(response.read().decode("utf-8"))
                if result.get("id"):
                    posted.append(f"{page.get('name', page_id)}: {result['id']}")
                else:
                    errors.append(f"{page.get('name', page_id)}: Facebook did not return a post ID")
            except Exception as e:
                errors.append(f"{page.get('name', page_id)}: {str(e)[:240]}")
        if errors:
            raise RuntimeError("Posted: " + "; ".join(posted) + " | Failed: " + "; ".join(errors))
        return "; ".join(posted)

    def connect(self):
        self.connect_btn.configure(state="disabled")
        self.status_var.set("Kanrbt m3a Google Blogger...")
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        try:
            service = auth_service()
            # Use the supported listByUser argument only. Some installed
            # Blogger API discovery clients reject maxResults for this method.
            result = service.blogs().listByUser(userId="self").execute()
            blogs = result.get("items", [])
            if not blogs:
                raise RuntimeError("Ma ban 7ta blog f had Google account. T2ekked belli dkhleti b nafs Google account li fih blogs.")
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
        try:
            self.save_facebook_config()
        except Exception as e:
            messagebox.showerror("Facebook settings", f"Could not save Facebook settings locally: {e}")
            return
        if (self.facebook_enabled_var.get() or self.instagram_enabled_var.get() or self.threads_enabled_var.get()) and mode != "publish":
            messagebox.showwarning("Social sharing", "Social sharing kaykhdem ghir mlli tkhtar Publish publicly. Drafts ma kaytpartagawch.")
            return
        if (self.facebook_enabled_var.get() or self.instagram_enabled_var.get()) and not self.selected_facebook_pages():
            messagebox.showwarning("Social settings", "Dkhel Facebook User Access Token, klik Load all Facebook Pages, w khtar Page.")
            return
        if self.threads_enabled_var.get() and (not self.threads_user_id_var.get().strip() or not self.threads_token_var.get().strip()):
            messagebox.showwarning("Threads settings", "Dkhel Threads User ID w Access Token, ola 7yed check dyal Threads.")
            return
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
                gemini_key = self.gemini_api_key_var.get().strip()
                if gemini_key:
                    try:
                        item["hashtags"] = gemini_hashtags(item["title"], item["description"], gemini_key)
                    except Exception as gemini_error:
                        self.root.after(0, lambda msg=str(gemini_error): self.status_var.set("Gemini failed; using fallback hashtags. " + msg[:150]))
                body = {"kind": "blogger#post", "blog": {"id": blog["id"]}, "title": item["title"], "content": make_html(item)}
                result = SERVICE.posts().insert(blogId=blog["id"], body=body, isDraft=(mode == "draft")).execute()
                social_notes = []
                caption = f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}\n\n{result.get('url', '')}".strip()
                if mode == "publish" and self.facebook_enabled_var.get():
                    try:
                        fb_result = self.share_to_facebook(item, result.get("url", ""))
                        social_notes.append(f"Facebook OK: {fb_result}")
                    except Exception as social_error:
                        social_notes.append(f"Facebook FAILED: {str(social_error)[:260]}")
                        errors += 1
                if mode == "publish" and self.instagram_enabled_var.get():
                    ig_ok, ig_errors = [], []
                    selected_ig_pages = [
                        page for page in self.selected_facebook_pages()
                        if str((page.get("instagram_business_account") or {}).get("id", "")).strip()
                    ]
                    if not selected_ig_pages:
                        ig_errors.append("No selected Facebook Page has a linked Instagram Professional account. Click Load all Facebook Pages and select a Page marked Instagram.")
                    for page in selected_ig_pages:
                        try:
                            ig_id = publish_instagram(item, page, caption)
                            ig_name = (page.get("instagram_business_account") or {}).get("username") or page.get("name", page.get("id"))
                            ig_ok.append(f"@{ig_name}: {ig_id}")
                        except Exception as social_error:
                            ig_errors.append(f"{page.get('name', page.get('id'))}: {str(social_error)[:220]}")
                    if ig_ok:
                        social_notes.append("Instagram OK: " + "; ".join(ig_ok))
                    if ig_errors:
                        social_notes.append("Instagram FAILED: " + "; ".join(ig_errors))
                        errors += len(ig_errors)
                if mode == "publish" and self.threads_enabled_var.get():
                    try:
                        th_id = publish_threads(item, self.threads_user_id_var.get().strip(), self.threads_token_var.get().strip(), caption)
                        social_notes.append(f"Threads OK: {th_id}")
                    except Exception as social_error:
                        social_notes.append(f"Threads FAILED: {str(social_error)[:260]}")
                        errors += 1
                social_note = " | ".join(social_notes)
                file_state[item["key"]] = {"post_id": result.get("id"), "url": result.get("url"), "mode": mode, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "social": social_note}
                save_state(state)
                done += 1
                display_title = item["title"] + (f" | {social_note}" if social_note else "")
                self.root.after(0, lambda n=n, total=total, title=display_title: self._update_progress(n, total, title))
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
