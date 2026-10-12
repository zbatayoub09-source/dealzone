import csv
import hashlib
import html
import json
import re
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
PLATFORMS = [
    ("Facebook", "Facebook"),
    ("Instagram", "Instagram"),
    ("TikTok", "TikTok"), ("YouTube", "Youtube"),
    ("Pinterest", "Pinterest"), ("Threads", "Threads"),
]

GRAPH_VERSION = "v26.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

def facebook_api(method, endpoint, params):
    params = dict(params)
    url = f"{GRAPH_BASE}/{endpoint.lstrip('/')}"
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, method="GET")
    else:
        body = urllib.parse.urlencode(params).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
            err = data.get("error", {})
            detail = err.get("message", "Facebook API error")
            code = err.get("code")
            raise RuntimeError(f"Facebook API ({code}): {detail}")
        except (ValueError, json.JSONDecodeError):
            raise RuntimeError(f"Facebook API HTTP error: {exc.code}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ma t9drch tconnecta l-Facebook: {exc.reason}")
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        raise RuntimeError(f"Facebook API ({err.get('code')}): {err.get('message', 'Error')}")
    return data

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
        sample = f.read(16000); f.seek(0)
        try: dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error: dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames: raise ValueError("CSV ma fihch headers.")
        rows = list(reader)
        if not rows: raise ValueError("CSV ma fih ta product.")
        return rows, reader.fieldnames

def improve_with_gemini(title, api_key):
    prompt = (
        "Create accurate social-commerce copy in English for this product title. "
        "Do not invent material, sizes, certifications, benefits, discounts or specifications. "
        "Correct obvious spelling errors. Return ONLY valid JSON with keys title, description, hashtags. "
        "Title: concise SEO title under 140 characters. Description: natural useful description, 2 sentences, "
        "tell buyer to check listing for exact options. Hashtags: array of 5 to 8 relevant hashtags, each starting #. "
        "Product title: " + title
    )
    payload = json.dumps({"contents":[{"parts":[{"text":prompt}]}],
                          "generationConfig":{"temperature":0.3,"responseMimeType":"application/json"}}).encode("utf-8")
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + api_key,
        data=payload, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    new_title = clean(result.get("title"))[:180] or title
    description = clean(result.get("description"))[:2000]
    tags = result.get("hashtags", [])
    if isinstance(tags, str): tags = re.findall(r"#[A-Za-z0-9_]+", tags)
    tags = " ".join(dict.fromkeys(("#" + re.sub(r"[^A-Za-z0-9_]", "", str(t)).lstrip("#")) for t in tags if re.sub(r"[^A-Za-z0-9_]", "", str(t).lstrip("#"))))[:8]
    return new_title, description, tags

def make_item(row, index, api_key=""):
    title = field(row, ["Product Title", "Title", "Product Name", "Name", "Product Desc", "Product Description", "Description", "Product"])
    if not title: title = f"DealZone product {index}"
    title = title[:180]
    desc = field(row, ["SEO_Description", "SEO Description", "Product Description", "Product Desc", "Description"])
    raw_tags = field(row, ["Hashtags", "SEO_Hashtags", "Tags"])
    tags = " ".join(re.findall(r"#[A-Za-z0-9_]+", raw_tags))
    if api_key:
        try:
            title, desc, tags = improve_with_gemini(title, api_key)
        except Exception as e:
            raise RuntimeError(f"Gemini API ma khdamch: {e}")
    else:
        if len(desc) < 80:
            desc = f"Discover {title}. Explore the product details and intended use, and check the seller's page for exact options, customer reviews, current price and delivery information before ordering."
        if len(re.findall(r"#[A-Za-z0-9_]+", tags)) < 3:
            stop = {"with","from","this","that","and","the","for","new","hot","best","sale","women","summer"}
            words = re.findall(r"[A-Za-z0-9]+", title.lower())
            words = [w for w in words if len(w) >= 3 and w not in stop]
            tags = " ".join("#" + w for w in list(dict.fromkeys(words))[:5] + ["DealZone","ProductFinds"])
    tags = " ".join(list(dict.fromkeys(re.findall(r"#[A-Za-z0-9_]+", tags)))[:8])
    image = field(row, ["Image Url", "Image URL", "Image", "ImageUrl", "Main Image"])
    video = field(row, ["Video Url", "Video URL", "Video", "VideoUrl", "Product Video"])
    link = field(row, ["Promotion Url", "Promotion URL", "Product Url", "Product URL", "Affiliate Link", "Link", "URL"])
    pid = field(row, ["ProductId", "Product ID", "Item ID", "ID"])
    key = hashlib.sha256((pid or link or title).encode("utf-8", errors="ignore")).hexdigest()
    return {"title": title, "description": desc[:2000], "hashtags": tags, "image": image, "video": video, "link": link, "key": key}

def write_csv(path, rows, headers):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)

def load_facebook_checkpoint(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"published": {}}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"published": {}}

def save_facebook_checkpoint(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)

class SocialPublisher:
    def __init__(self, root):
        self.root = root
        root.title("DealZone Social Publisher")
        root.geometry("900x820"); root.minsize(780, 680)
        self.csv_path = ""; self.rows = []; self.selected = {}
        self.csv_var = tk.StringVar(value="Ma khtart ta CSV")
        self.status = tk.StringVar(value="Khtar CSV bach tbda.")
        self.limit = tk.StringVar(value="20")
        self.output_dir = tk.StringVar(value=str(APP_DIR / "output"))
        self.use_ai = tk.BooleanVar(value=False)
        self.api_key = tk.StringVar(value="")
        self.facebook_token = tk.StringVar(value="")
        self.facebook_pages = []
        self.pages_list = None
        self.build()

    def build(self):
        main = ttk.Frame(self.root, padding=16); main.pack(fill="both", expand=True)
        ttk.Label(main, text="DEALZONE SOCIAL PUBLISHER", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="SEO • Hashtags • Image URL • Video URL • Platform CSV", font=("Segoe UI", 10)).pack(anchor="w", pady=(0,10))
        ttk.Label(main, text="1. CSV dyal AliExpress").pack(anchor="w")
        r = ttk.Frame(main); r.pack(fill="x", pady=4)
        ttk.Entry(r, textvariable=self.csv_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Choose CSV", command=self.choose_csv).pack(side="left", padx=(8,0))
        ttk.Label(main, text="2. Platforms").pack(anchor="w", pady=(8,3))
        pf = ttk.Frame(main); pf.pack(fill="x")
        for i, (label, _) in enumerate(PLATFORMS):
            v = tk.BooleanVar(value=label in ("Facebook", "Instagram", "Pinterest")); self.selected[label] = v
            ttk.Checkbutton(pf, text=label, variable=v).grid(row=i//3, column=i%3, sticky="w", padx=(0,22), pady=2)
        ttk.Label(main, text="Facebook: Access Token dyal user (ma kayt7fedch)").pack(anchor="w", pady=(10,3))
        fr = ttk.Frame(main); fr.pack(fill="x")
        ttk.Entry(fr, textvariable=self.facebook_token, show="*").pack(side="left", fill="x", expand=True)
        ttk.Button(fr, text="Load Facebook Pages", command=self.load_facebook_pages).pack(side="left", padx=(8,0))
        ttk.Label(main, text="Khtar page wa7da ola kter (Ctrl/Shift bach tkhtar kter):").pack(anchor="w", pady=(6,2))
        self.pages_list = tk.Listbox(main, height=4, selectmode=tk.EXTENDED, exportselection=False)
        self.pages_list.pack(fill="x")
        ttk.Checkbutton(main, text="Improve title, SEO description and hashtags with Gemini AI (uses API quota)", variable=self.use_ai).pack(anchor="w", pady=(10,3))
        kr = ttk.Frame(main); kr.pack(fill="x")
        ttk.Label(kr, text="Gemini API key (ma kayt7fedch f file):").pack(side="left")
        ttk.Entry(kr, textvariable=self.api_key, show="*", width=48).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Label(main, text="3. Max products f had l-run").pack(anchor="w", pady=(9,3))
        ttk.Entry(main, textvariable=self.limit, width=10).pack(anchor="w")
        ttk.Label(main, text="4. Output folder").pack(anchor="w", pady=(8,3))
        out = ttk.Frame(main); out.pack(fill="x")
        ttk.Entry(out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(out, text="Browse", command=self.choose_output).pack(side="left", padx=(8,0))
        ttk.Label(main, text="5. Preview").pack(anchor="w", pady=(10,3))
        self.preview = tk.Text(main, height=12, wrap="word", font=("Segoe UI", 9)); self.preview.pack(fill="both", expand=True)
        buttons = ttk.Frame(main); buttons.pack(fill="x", pady=(10,3))
        ttk.Button(buttons, text="Preview first product", command=self.preview_first).pack(side="left")
        ttk.Button(buttons, text="Publish to Facebook", command=self.publish_facebook).pack(side="left", padx=8)
        ttk.Button(buttons, text="Generate platform CSV files", command=self.generate).pack(side="left")
        ttk.Label(main, textvariable=self.status, wraplength=850).pack(anchor="w", pady=(5,0))
        ttk.Label(main, text="Facebook: t9der tdkhel Access Token, tloadi pages, tkhtar pages, w tnشر direct. Platforms l-akhra kaywjed lihom CSV. Blogger mab9ach dakhel f had l-version.", wraplength=850).pack(anchor="w", pady=(7,0))

    def load_facebook_pages(self):
        token = self.facebook_token.get().strip()
        if not token:
            messagebox.showwarning("Facebook Access Token", "Dkhel Access Token lwl.")
            return
        try:
            pages = []
            after = None
            while True:
                params = {"fields": "id,name,access_token,tasks", "limit": "100", "access_token": token}
                if after:
                    params["after"] = after
                data = facebook_api("GET", "me/accounts", params)
                pages.extend(data.get("data", []))
                after = (data.get("paging", {}).get("cursors", {}) or {}).get("after")
                if not after or not data.get("data"):
                    break
            # Deduplicate pages if Graph API repeats an item between pages.
            pages = list({str(p.get("id")): p for p in pages if p.get("id")}.values())
            if not pages:
                self.facebook_pages = []
                self.pages_list.delete(0, "end")
                messagebox.showwarning(
                    "Ma ban ta page",
                    "Facebook ma rje3 ta page. T2ekked belli had token user access token fih pages_show_list, w 3andek access l-pages."
                )
                return
            self.facebook_pages = pages
            self.pages_list.delete(0, "end")
            for page in pages:
                self.pages_list.insert("end", f"{page.get('name', 'Page')}  |  ID: {page.get('id', '')}")
            self.status.set(f"Facebook: l9ina {len(pages)} pages. Khtar li bghiti.")
            messagebox.showinfo("Facebook Pages", f"L9ina {len(pages)} pages. T9der t7edded pages li bghiti mn list.")
        except Exception as e:
            messagebox.showerror("Facebook API error", str(e))

    def choose_csv(self):
        path = filedialog.askopenfilename(title="Choose AliExpress CSV", filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if not path: return
        try:
            rows, headers = load_csv(path)
            self.csv_path, self.rows, self.headers = path, rows, headers
            self.csv_var.set(path); self.status.set(f"CSV wajed: {len(rows)} products.")
            self.preview_first()
        except Exception as e: messagebox.showerror("CSV error", str(e))

    def choose_output(self):
        p = filedialog.askdirectory(title="Choose output folder")
        if p: self.output_dir.set(p)

    def preview_first(self):
        if not self.rows:
            messagebox.showwarning("Choose CSV", "Khtar CSV lwl."); return
        try:
            key = self.api_key.get().strip() if self.use_ai.get() else ""
            if self.use_ai.get() and not key:
                messagebox.showwarning("Gemini API key", "Dkhel Gemini API key ola 7yed l-option AI."); return
            item = make_item(self.rows[0], 1, key)
            self.preview.delete("1.0", "end")
            self.preview.insert("end", f"TITLE\n{item['title']}\n\nSEO DESCRIPTION\n{item['description']}\n\nHASHTAGS\n{item['hashtags']}\n\nIMAGE\n{item['image']}\n\nVIDEO\n{item['video'] or '(ma kaynach Video Url f had row)'}\n\nPRODUCT LINK\n{item['link']}")
        except Exception as e: messagebox.showerror("Preview error", str(e))

    def publish_facebook(self):
        # Dedicated Facebook action: ensure Facebook is selected, then use the
        # existing validation, selected-page confirmation, and publishing flow.
        self.selected["Facebook"].set(True)
        self.generate()

    def generate(self):
        if not self.rows:
            messagebox.showwarning("Choose CSV", "Khtar CSV lwl."); return
        platforms = [p for p, v in self.selected.items() if v.get()]
        if not platforms:
            messagebox.showwarning("Choose platform", "Khtar platform wa7da 3la l-a9al."); return
        selected_pages = []
        if "Facebook" in platforms:
            if not self.facebook_token.get().strip():
                messagebox.showwarning("Facebook Token", "Dkhel Access Token w klik Load Facebook Pages.")
                return
            chosen = list(self.pages_list.curselection()) if self.pages_list else []
            if not chosen:
                messagebox.showwarning("Facebook Pages", "Klik Load Facebook Pages, w khtar page wa7da 3la l-a9al.")
                return
            selected_pages = [self.facebook_pages[i] for i in chosen]
        try:
            limit = int(self.limit.get())
            if limit < 1: raise ValueError()
        except ValueError:
            messagebox.showerror("Limit", "Dkhel ra9m kber men 0."); return
        api_key = self.api_key.get().strip() if self.use_ai.get() else ""
        if self.use_ai.get() and not api_key:
            messagebox.showerror("Gemini API key", "Dkhel Gemini API key ola 7yed l-option AI."); return
        try:
            out = Path(self.output_dir.get()).expanduser(); out.mkdir(parents=True, exist_ok=True)
            selected_rows = self.rows[:limit]; prepared = []
            for i, row in enumerate(selected_rows, 1):
                self.status.set(f"Kanwjed product {i}/{len(selected_rows)}...")
                self.root.update_idletasks()
                prepared.append((row, make_item(row, i, api_key)))
            checkpoint_path = out / "facebook_checkpoint.json"
            checkpoint = load_facebook_checkpoint(checkpoint_path)
            published = checkpoint.setdefault("published", {})
            pending_posts = 0
            if "Facebook" in platforms:
                for page in selected_pages:
                    page_id = str(page.get("id", ""))
                    for row, item in prepared:
                        if not published.get(page_id, {}).get(item["key"]):
                            pending_posts += 1
                if pending_posts == 0:
                    messagebox.showinfo("Facebook checkpoint", "Had products kamlin tsb9o tnchro f had pages. Ma ghadi n3awd n نشر حتى post.")
                else:
                    names = "\n".join(p.get("name", "Page") for p in selected_pages)
                    if not messagebox.askyesno("Confirm Facebook publishing",
                        f"Ghadi ynشر ghir {pending_posts} new posts (duplicates skipped).\n\nPages:\n{names}\n\nBghiti tkمل?"):
                        return
            fb_success = 0
            fb_skipped = 0
            fb_errors = []
            if "Facebook" in platforms and pending_posts > 0:
                for page in selected_pages:
                    page_id = str(page.get("id", ""))
                    page_token = page.get("access_token", "")
                    page_name = page.get("name", page_id)
                    if not page_token:
                        fb_errors.append(f"{page_name}: page token ma kaynach")
                        continue
                    page_published = published.setdefault(page_id, {})
                    for i, (row, item) in enumerate(prepared, 1):
                        if page_published.get(item["key"]):
                            fb_skipped += 1
                            continue
                        caption = f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}"
                        try:
                            image_url = str(item.get("image", "") or "").strip()
                            if image_url.startswith(("https://", "http://")):
                                # Publish the product image as a real Facebook Page photo.
                                # Keep the product/promotion URL in the caption so buyers can open it.
                                photo_caption = caption
                                if item.get("link"):
                                    photo_caption += "\\n\\nShop link: " + item["link"]
                                facebook_api("POST", f"{page_id}/photos", {
                                    "url": image_url,
                                    "caption": photo_caption,
                                    "access_token": page_token,
                                })
                            else:
                                # If the CSV has no usable image URL, publish a link/text post.
                                params = {"message": caption, "access_token": page_token}
                                if item.get("link"):
                                    params["link"] = item["link"]
                                facebook_api("POST", f"{page_id}/feed", params)
                            fb_success += 1
                            page_published[item["key"]] = {
                                "product_id": field(row, ["ProductId", "Product ID", "Item ID", "ID"]),
                                "title": item["title"],
                                "post_key": item["key"],
                            }
                            save_facebook_checkpoint(checkpoint_path, checkpoint)
                        except Exception as exc:
                            fb_errors.append(f"{page.get('name', page_id)} / product {i}: {exc}")
                        self.status.set(f"Facebook: {fb_success}/{len(prepared) * len(selected_pages)} posts...")
                        self.root.update_idletasks()
            made = []
            headers = ["Platform","ProductId","Title","Text","Description","Hashtags","Image Url","Video Url","Promotion Url","Deduplication Key"]
            for platform in platforms:
                result = []
                for row, item in prepared:
                    caption = f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}"
                    result.append({
                        "Platform": platform, "ProductId": field(row, ["ProductId","Product ID","Item ID","ID"]),
                        "Title": item["title"], "Text": caption, "Description": item["description"],
                        "Hashtags": item["hashtags"], "Image Url": item["image"], "Video Url": item["video"],
                        "Promotion Url": item["link"], "Deduplication Key": item["key"],
                    })
                dest = out / f"{platform.lower()}_ready.csv"; write_csv(dest, result, headers); made.append(str(dest))
            self.status.set(f"Saliw CSV files. Facebook posts: {fb_success} success, {fb_skipped} duplicates skipped, {len(fb_errors)} errors.")
            summary = "Tوجدات CSV files:\n\n" + "\n".join(made)
            if "Facebook" in platforms:
                summary += f"\n\nFacebook: {fb_success} posts successful; {fb_skipped} duplicates skipped; {len(fb_errors)} errors.\nCheckpoint: {checkpoint_path}"
                if fb_errors:
                    summary += "\n\nFirst errors:\n" + "\n".join(fb_errors[:5])
            summary += "\n\nFacebook checkpoint kayt7fed f output/facebook_checkpoint.json. Token ma t7fedch f file."
            messagebox.showinfo("Done", summary)
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            self.status.set("Wa9e3 error f generation.")

def main():
    root = tk.Tk()
    try: ttk.Style().theme_use("clam")
    except Exception: pass
    SocialPublisher(root); root.mainloop()

if __name__ == "__main__":
    main()
