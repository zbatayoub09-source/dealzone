import csv
import hashlib
import html
import json
import os
import re
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
PLATFORMS = ["Facebook", "Instagram", "Threads", "TikTok", "YouTube", "Pinterest"]
GRAPH_BASE = "https://graph.facebook.com/v26.0"
THREADS_BASE = "https://graph.threads.net/v1.0"


def api_post(base, endpoint, params, label="API"):
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(f"{base}/{endpoint.lstrip('/')}", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
            err = data.get("error", {})
            raise RuntimeError(f"{label} ({err.get('code')}): {err.get('message', 'API error')}")
        except (ValueError, json.JSONDecodeError):
            raise RuntimeError(f"{label} HTTP error: {e.code}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connexion {label}: {e.reason}")
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        raise RuntimeError(f"{label} ({err.get('code')}): {err.get('message', 'API error')}")
    return data


def api_get(base, endpoint, params, label="API"):
    url = f"{base}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
            err = data.get("error", {})
            raise RuntimeError(f"{label} ({err.get('code')}): {err.get('message', 'API error')}")
        except (ValueError, json.JSONDecodeError):
            raise RuntimeError(f"{label} HTTP error: {e.code}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connexion {label}: {e.reason}")
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        raise RuntimeError(f"{label} ({err.get('code')}): {err.get('message', 'API error')}")
    return data


def publish_youtube(item, token_path):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    token_value = (token_path or "").strip()
    token_file = Path(token_value).expanduser()
    token_file_exists = token_file.is_file()
    if token_file_exists:
        try:
            creds = Credentials.from_authorized_user_file(str(token_file))
        except Exception as e:
            raise RuntimeError(f"YouTube token JSON ma tqrachch: {e}")
    elif token_value.startswith("ya29."):
        # Pasted Google OAuth access tokens work only until they expire.
        creds = Credentials(token=token_value, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    else:
        raise RuntimeError("Dkhel Google OAuth access token (ghaliban kaybda ya29.) ola khtar youtube_token.json.")
    upload_scopes = {"https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"}
    if creds.scopes and not upload_scopes.intersection(set(creds.scopes)):
        raise RuntimeError("Token ma fihch YouTube upload permission. Khass OAuth token b youtube.upload ola youtube scope.")
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                if token_file_exists:
                    token_file.write_text(creds.to_json(), encoding="utf-8")
            except Exception as e:
                raise RuntimeError(f"YouTube token expired w refresh failed: {e}")
        else:
            raise RuntimeError("YouTube token ma validch ola ma fihch refresh_token. Khass OAuth token jdida.")

    video_url = (item.get("video") or "").strip()
    if not video_url.startswith(("https://", "http://")):
        raise RuntimeError("Product ma fihch Video URL direct. Upload YouTube khas video file, machi image.")
    suffix = Path(urllib.parse.urlparse(video_url).path).suffix.lower()
    if suffix not in (".mp4", ".mov", ".mpeg", ".mpg", ".avi", ".wmv", ".flv", ".webm", ".3gp", ".m4v"):
        suffix = ".mp4"
    tmp_path = None
    try:
        request = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type.lower():
                raise RuntimeError("Video URL kay7ell page HTML, machi direct video link.")
            with tempfile.NamedTemporaryFile(prefix="dealzone_youtube_", suffix=suffix, delete=False) as tmp:
                tmp_path = tmp.name
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
        if os.path.getsize(tmp_path) < 1024:
            raise RuntimeError("Video download khawi ola sghir بزاف.")
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        description = (item.get("description", "") + "\n\n" + item.get("hashtags", "") +
                       ("\n\nProduct link: " + item["link"] if item.get("link") else ""))
        body = {
            "snippet": {
                "title": (item.get("title") or "DealZone video")[:100],
                "description": description[:5000],
                "tags": re.findall(r"[A-Za-z0-9_]+", item.get("hashtags", ""))[:30],
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(tmp_path, mimetype=content_type if content_type.startswith("video/") else "video/mp4",
                                chunksize=8 * 1024 * 1024, resumable=True)
        upload = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        result = None
        while result is None:
            status, result = upload.next_chunk()
        return result.get("id", "OK")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def publish_threads(item, user_id, token):
    caption = f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}"[:500]
    image = item.get("image", "").strip()
    params = {"access_token": token, "text": caption}
    if image.startswith("https://"):
        params.update({"media_type": "IMAGE", "image_url": image})
    else:
        params["media_type"] = "TEXT"
    c = api_post(THREADS_BASE, f"{user_id}/threads", params, "Threads API")
    cid = c.get("id")
    if not cid:
        raise RuntimeError("Threads ma rje3ch creation ID.")
    p = api_post(THREADS_BASE, f"{user_id}/threads_publish",
                 {"creation_id": cid, "access_token": token}, "Threads API")
    return p.get("id") or "OK"


def clean(v):
    v = html.unescape(str(v or ""))
    v = re.sub(r"<[^>]*>", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def field(row, names):
    lookup = {str(k).strip().lower(): k for k in row if k is not None}
    for name in names:
        k = lookup.get(name.lower())
        if k is not None and clean(row.get(k)):
            return clean(row.get(k))
    return ""


def load_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(16000); f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("CSV ma fihch headers.")
        rows = list(reader)
        if not rows:
            raise ValueError("CSV ma fih ta product.")
        return rows, reader.fieldnames


def gemini_copy(title, key):
    prompt = ("Create accurate social-commerce copy in English. Do not invent specs. "
              "Return ONLY JSON with title, description, hashtags. Title under 140 chars; "
              "description 2 useful sentences; hashtags 5-8. Product: " + title)
    payload = json.dumps({"contents":[{"parts":[{"text":prompt}]}],
        "generationConfig":{"temperature":0.3,"responseMimeType":"application/json"}}).encode()
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + key,
        data=payload, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    tags = result.get("hashtags", [])
    if isinstance(tags, str):
        tags = re.findall(r"#[A-Za-z0-9_]+", tags)
    tags = " ".join(list(dict.fromkeys(
        "#" + re.sub(r"[^A-Za-z0-9_]", "", str(x).lstrip("#")) for x in tags))[:8])
    return clean(result.get("title"))[:180] or title, clean(result.get("description"))[:2000], tags


def make_item(row, index, gemini_key=""):
    title = field(row, ["Product Title","Title","Product Name","Name","Product Desc","Product Description","Description","Product"])
    title = (title or f"DealZone product {index}")[:180]
    desc = field(row, ["SEO_Description","SEO Description","Product Description","Product Desc","Description"])
    tags = " ".join(re.findall(r"#[A-Za-z0-9_]+", field(row, ["Hashtags","SEO_Hashtags","Tags"])))
    if gemini_key:
        title, desc, tags = gemini_copy(title, gemini_key)
    else:
        if len(desc) < 80:
            desc = f"Discover {title}. Check the listing for exact options, price, reviews and delivery information before ordering."
        if len(re.findall(r"#[A-Za-z0-9_]+", tags)) < 3:
            words = re.findall(r"[A-Za-z0-9]+", title.lower())
            words = [w for w in words if len(w) >= 3]
            tags = " ".join("#" + w for w in list(dict.fromkeys(words))[:5] + ["DealZone","ProductFinds"])
    tags = " ".join(list(dict.fromkeys(re.findall(r"#[A-Za-z0-9_]+", tags)))[:8])
    image = field(row, ["Image Url","Image URL","Image","ImageUrl","Main Image"])
    video = field(row, ["Video Url","Video URL","Video","VideoUrl","Product Video"])
    link = field(row, ["Promotion Url","Promotion URL","Product Url","Product URL","Affiliate Link","Link","URL"])
    pid = field(row, ["ProductId","Product ID","Item ID","ID"])
    key = hashlib.sha256((pid or link or title).encode("utf-8", errors="ignore")).hexdigest()
    return {"title":title,"description":desc[:2000],"hashtags":tags,"image":image,"video":video,"link":link,"key":key,"pid":pid}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_csv(path, rows):
    headers = ["Platform","ProductId","Title","Text","Description","Hashtags","Image Url","Video Url","Promotion Url","Deduplication Key"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers); w.writeheader(); w.writerows(rows)


class SocialPublisher:
    def __init__(self, root):
        self.root = root
        root.title("DealZone Social Publisher")
        root.geometry("980x760")
        root.minsize(760, 500)
        self.rows=[]; self.headers=[]; self.facebook_pages=[]; self.pages_list=None
        self.selected={p:tk.BooleanVar(value=p in ("Facebook","Instagram","Pinterest")) for p in PLATFORMS}
        self.csv_var=tk.StringVar(value="Ma khtart ta CSV")
        self.status=tk.StringVar(value="Khtar CSV bach tbda.")
        self.limit=tk.StringVar(value="20")
        self.output_dir=tk.StringVar(value=str(APP_DIR/"output"))
        self.facebook_token=tk.StringVar(); self.facebook_page_id=tk.StringVar()
        self.threads_user_id=tk.StringVar(); self.threads_token=tk.StringVar()
        default_youtube_token = APP_DIR / "youtube_token.json"
        self.youtube_token_path=tk.StringVar(value=str(default_youtube_token) if default_youtube_token.exists() else "")
        self.links_page_url=tk.StringVar(value="")
        self.use_ai=tk.BooleanVar(value=False); self.gemini_key=tk.StringVar()
        self.build()

    def build(self):
        # Scrollable main area: the complete form can now be reached by the long bar on the right.
        shell=ttk.Frame(self.root); shell.pack(fill="both", expand=True)
        canvas=tk.Canvas(shell, highlightthickness=0)
        scrollbar=ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        main=ttk.Frame(canvas, padding=16)
        window=canvas.create_window((0,0), window=main, anchor="nw")
        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        def wheel(e):
            canvas.yview_scroll(int(-e.delta/120), "units")
        canvas.bind_all("<MouseWheel>", wheel)

        ttk.Label(main,text="DEALZONE SOCIAL PUBLISHER",font=("Segoe UI",18,"bold")).pack(anchor="w")
        ttk.Label(main,text="CSV → SEO → Social publishing",font=("Segoe UI",10)).pack(anchor="w",pady=(0,12))
        ttk.Label(main,text="1. CSV dyal AliExpress").pack(anchor="w")
        r=ttk.Frame(main); r.pack(fill="x",pady=4)
        ttk.Entry(r,textvariable=self.csv_var,state="readonly").pack(side="left",fill="x",expand=True)
        ttk.Button(r,text="Choose CSV",command=self.choose_csv).pack(side="left",padx=(8,0))

        ttk.Label(main,text="2. Khtar fin bghiti tnشر",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(12,4))
        pf=ttk.Frame(main); pf.pack(fill="x")
        for i,p in enumerate(PLATFORMS):
            ttk.Checkbutton(pf,text=p,variable=self.selected[p]).grid(row=i//3,column=i%3,sticky="w",padx=(0,35),pady=4)

        ttk.Label(main,text="Facebook User Access Token (secret)").pack(anchor="w",pady=(12,3))
        fr=ttk.Frame(main); fr.pack(fill="x")
        ttk.Entry(fr,textvariable=self.facebook_token,show="*").pack(side="left",fill="x",expand=True)
        ttk.Button(fr,text="Load Facebook Pages",command=self.load_pages).pack(side="left",padx=(8,0))
        ttk.Label(main,text="Facebook Page ID ou Page link:").pack(anchor="w",pady=(7,2))
        ir=ttk.Frame(main); ir.pack(fill="x")
        ttk.Entry(ir,textvariable=self.facebook_page_id).pack(side="left",fill="x",expand=True)
        ttk.Button(ir,text="Select Page",command=self.select_page).pack(side="left",padx=(8,0))
        ttk.Label(main,text="Pages li l9iti: (Ctrl/Shift bach tkhtar aktar mn wa7da)").pack(anchor="w",pady=(7,2))
        self.pages_list=tk.Listbox(main,height=5,selectmode=tk.EXTENDED,exportselection=False)
        self.pages_list.pack(fill="x")
        ttk.Label(main,text="Instagram kayt3amar automatiquement ila Page Facebook مربوطة بـ Instagram Professional.",wraplength=900).pack(anchor="w",pady=(5,2))

        ttk.Label(main,text="Threads User ID:").pack(anchor="w",pady=(10,2))
        ttk.Entry(main,textvariable=self.threads_user_id).pack(fill="x")
        ttk.Label(main,text="Threads Access Token:").pack(anchor="w",pady=(6,2))
        ttk.Entry(main,textvariable=self.threads_token,show="*").pack(fill="x")

        ttk.Label(main,text="YouTube OAuth token (paste access token ola khtar token JSON file)").pack(anchor="w",pady=(12,3))
        yr=ttk.Frame(main); yr.pack(fill="x")
        ttk.Entry(yr,textvariable=self.youtube_token_path,show="*").pack(side="left",fill="x",expand=True)
        ttk.Button(yr,text="Choose token JSON",command=self.choose_youtube_token).pack(side="left",padx=(8,0))
        ttk.Label(main,text="T9der tlssa9 Google OAuth access token (ghaliban kaybda ya29.) ola tkhtar youtube_token.json. Token kayb9a ghir f PC dyalek. Access token li tlssa9 kay9der ysali; token JSON li fih refresh_token afdal.",wraplength=900).pack(anchor="w",pady=(3,2))

        ttk.Label(main,text="YouTube: khtar product w raje3 Title / Description / Affiliate Link",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(10,4))
        self.youtube_product_var=tk.StringVar(value="")
        self.youtube_title_var=tk.StringVar()
        self.youtube_link_var=tk.StringVar()
        self.youtube_description_widget=None
        self.youtube_video_var=tk.StringVar()
        self.youtube_product_combo=ttk.Combobox(main,textvariable=self.youtube_product_var,state="readonly")
        self.youtube_product_combo.pack(fill="x",pady=3)
        self.youtube_product_combo.bind("<<ComboboxSelected>>",self.select_youtube_product)
        ttk.Label(main,text="YouTube Title").pack(anchor="w",pady=(5,2))
        ttk.Entry(main,textvariable=self.youtube_title_var).pack(fill="x")
        ttk.Label(main,text="YouTube Description").pack(anchor="w",pady=(5,2))
        self.youtube_description_widget=tk.Text(main,height=5,wrap="word")
        self.youtube_description_widget.pack(fill="x")
        ttk.Label(main,text="Affiliate Link (Promotion Url)").pack(anchor="w",pady=(5,2))
        ttk.Entry(main,textvariable=self.youtube_link_var).pack(fill="x")
        ttk.Label(main,text="Video URL (direct video file)").pack(anchor="w",pady=(5,2))
        ttk.Entry(main,textvariable=self.youtube_video_var).pack(fill="x")
        ttk.Button(main,text="Publish this YouTube product",command=self.publish_youtube_edited).pack(anchor="w",pady=(8,3))
        ttk.Label(main,text="Had lزر kaynشر ghir product li khtarti, b Title/Description/Link li 3deltihom. Video URL khas ykoun direct.",wraplength=900).pack(anchor="w",pady=(2,4))

        ttk.Label(main,text="Instagram bio link page URL (optional)").pack(anchor="w",pady=(10,3))
        ttk.Entry(main,textvariable=self.links_page_url).pack(fill="x")
        ttk.Label(main,text="Instagram links f caption ma kaykounouch clickable. Dkhel URL public dyal page dyal products; l-app ghadi ygeneri HTML page b links dyal CSV f output.",wraplength=900).pack(anchor="w",pady=(3,2))

        ttk.Label(main,text="Gemini AI (ikhtiyari)").pack(anchor="w",pady=(12,3))
        ttk.Checkbutton(main,text="Generate SEO title + description + hashtags",variable=self.use_ai).pack(anchor="w")
        ttk.Entry(main,textvariable=self.gemini_key,show="*").pack(fill="x",pady=4)

        ttk.Label(main,text="3. Max products f had l-run").pack(anchor="w",pady=(10,3))
        ttk.Entry(main,textvariable=self.limit,width=10).pack(anchor="w")
        ttk.Label(main,text="4. Output folder").pack(anchor="w",pady=(10,3))
        orow=ttk.Frame(main); orow.pack(fill="x")
        ttk.Entry(orow,textvariable=self.output_dir).pack(side="left",fill="x",expand=True)
        ttk.Button(orow,text="Browse",command=self.choose_output).pack(side="left",padx=(8,0))

        ttk.Label(main,text="5. Preview").pack(anchor="w",pady=(12,3))
        self.preview=tk.Text(main,height=10,wrap="word",font=("Segoe UI",9)); self.preview.pack(fill="x")
        buttons=ttk.Frame(main); buttons.pack(fill="x",pady=(10,5))
        ttk.Button(buttons,text="Preview first product",command=self.preview_first).pack(side="left")
        ttk.Button(buttons,text="Publish selected + Generate CSV",command=self.generate).pack(side="left",padx=8)
        ttk.Label(main,textvariable=self.status,wraplength=900).pack(anchor="w",pady=(5,0))
        ttk.Label(main,text="⬇ Hna t9der thbet lta7t b scrollbar li f jnab bach twsel lزر ديال النشر.",font=("Segoe UI",10,"bold"),wraplength=900).pack(anchor="w",pady=(12,20))

    def choose_csv(self):
        p=filedialog.askopenfilename(title="Choose AliExpress CSV",filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if not p:return
        try:
            self.rows,self.headers=load_csv(p); self.csv_var.set(p); self.status.set(f"CSV wajed: {len(self.rows)} products."); self.preview_first()
        except Exception as e: messagebox.showerror("CSV error",str(e))

    def choose_output(self):
        p=filedialog.askdirectory(title="Choose output folder")
        if p:self.output_dir.set(p)

    def choose_youtube_token(self):
        p=filedialog.askopenfilename(title="Choose YouTube OAuth token JSON",filetypes=[("JSON files","*.json"),("All files","*.*")])
        if not p:return
        try:
            data=json.loads(Path(p).read_text(encoding="utf-8"))
            if not isinstance(data,dict) or not (data.get("refresh_token") or data.get("token")):
                raise ValueError("Had JSON ma kaybanch OAuth token. Khtar youtube_token.json, machi client_secret.json.")
            self.youtube_token_path.set(p)
            self.status.set("YouTube token file selected.")
        except Exception as e:
            messagebox.showerror("YouTube token file",str(e))

    def choose_csv(self):
        p=filedialog.askopenfilename(title="Choose AliExpress CSV",filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if not p:return
        try:
            self.rows,self.headers=load_csv(p); self.csv_var.set(p); self.status.set(f"CSV wajed: {len(self.rows)} products."); self.preview_first()
            if hasattr(self,"youtube_product_combo"):
                self.youtube_product_combo["values"]=[f"{i+1}. {make_item(row,i+1,'')['title'][:100]}" for i,row in enumerate(self.rows)]
                if self.rows:
                    self.youtube_product_combo.current(0)
                    self.select_youtube_product()
        except Exception as e: messagebox.showerror("CSV error",str(e))

    def select_youtube_product(self, event=None):
        if not self.rows:return
        idx=self.youtube_product_combo.current()
        if idx < 0:
            try: idx=int(self.youtube_product_var.get().split(".",1)[0])-1
            except Exception: idx=0
        if not 0 <= idx < len(self.rows):return
        item=make_item(self.rows[idx],idx+1,"")
        self.youtube_title_var.set(item["title"])
        self.youtube_link_var.set(item["link"])
        self.youtube_video_var.set(item["video"])
        self.youtube_description_widget.delete("1.0","end")
        self.youtube_description_widget.insert("1.0",item["description"])

    def publish_youtube_edited(self):
        if not self.rows:
            messagebox.showwarning("CSV","Khtar CSV lwl.");return
        if not self.youtube_token_path.get().strip():
            messagebox.showwarning("YouTube token","Khtar youtube_token.json lwl.");return
        idx=self.youtube_product_combo.current()
        if idx < 0 or idx >= len(self.rows):
            messagebox.showwarning("YouTube product","Khtar product mn list.");return
        item=make_item(self.rows[idx],idx+1,"")
        item["title"]=self.youtube_title_var.get().strip() or item["title"]
        item["description"]=self.youtube_description_widget.get("1.0","end").strip()
        item["link"]=self.youtube_link_var.get().strip()
        item["video"]=self.youtube_video_var.get().strip()
        if not item["video"]:
            messagebox.showwarning("Video URL","Had product ma fihch Video URL. Dkhel lien direct dial video.");return
        try:
            video_id=publish_youtube(item,self.youtube_token_path.get().strip())
            out=Path(self.output_dir.get()).expanduser()
            state_path=out/"social_checkpoint.json"
            state=load_json(state_path)
            done=state.setdefault("youtube",{})
            token_key=str(Path(self.youtube_token_path.get().strip()).expanduser().resolve())
            done=done.setdefault(token_key,{})
            done[item["key"]]=video_id
            save_json(state_path,state)
            self.status.set("YouTube published: " + video_id)
            messagebox.showinfo("YouTube",f"Video tpublacha b najah.\nVideo ID: {video_id}\nTitle: {item['title']}")
        except Exception as e:
            messagebox.showerror("YouTube publish error",str(e))

    def preview_first(self):
        if not self.rows:
            messagebox.showwarning("CSV","Khtar CSV lwl.");return
        try:
            key=self.gemini_key.get().strip() if self.use_ai.get() else ""
            item=make_item(self.rows[0],1,key)
            self.preview.delete("1.0","end")
            self.preview.insert("end",f"TITLE\n{item['title']}\n\nDESCRIPTION\n{item['description']}\n\nHASHTAGS\n{item['hashtags']}\n\nIMAGE\n{item['image']}\n\nVIDEO\n{item['video'] or '(none)'}\n\nLINK\n{item['link']}")
        except Exception as e: messagebox.showerror("Preview error",str(e))

    def load_pages(self):
        token=self.facebook_token.get().strip()
        if not token:
            messagebox.showwarning("Facebook Token","Dkhel Facebook User Access Token lwl.");return
        try:
            pages=[]; after=None
            while True:
                params={"fields":"id,name,access_token,tasks,instagram_business_account{id,username}","limit":"100","access_token":token}
                if after:params["after"]=after
                data=api_get(GRAPH_BASE,"me/accounts",params,"Facebook API")
                pages.extend(data.get("data",[])); after=(data.get("paging",{}).get("cursors",{}) or {}).get("after")
                if not after or not data.get("data"):break
            pages=list({str(p.get("id")):p for p in pages if p.get("id")}.values())
            self.facebook_pages=pages; self.pages_list.delete(0,"end")
            for p in pages:
                ig=(p.get("instagram_business_account") or {}).get("username","not linked")
                self.pages_list.insert("end",f"{p.get('name','Page')} | ID: {p.get('id')} | Instagram: {ig}")
            if not pages:raise RuntimeError("Ma ban ta Page. T2ekked men permissions dyal User Access Token.")
            self.status.set(f"Facebook: l9ina {len(pages)} pages.")
            messagebox.showinfo("Facebook Pages",f"L9ina {len(pages)} pages. Khtar li bghiti.")
        except Exception as e:messagebox.showerror("Facebook API error",str(e))

    def select_page(self):
        raw=self.facebook_page_id.get().strip()
        if not raw:
            messagebox.showwarning("Page ID","Paste Page ID ola Page link.");return
        m=re.search(r"(?:[?&]id=|/pages/[^/?#]+/|/)([0-9]{6,})(?:[/?#&]|$)",raw)
        pid=raw if raw.isdigit() else (m.group(1) if m else "")
        if not pid:
            messagebox.showerror("Page ID","Ma qdrtch nخرج Page ID men lien. Jarrab ra9m Page ID.");return
        for i,p in enumerate(self.facebook_pages):
            if str(p.get("id"))==pid:
                self.pages_list.selection_clear(0,"end");self.pages_list.selection_set(i);self.pages_list.see(i);return
        messagebox.showwarning("Page","Had Page ma kaynach f list. Klik Load Facebook Pages lwl.")

    def generate(self):
        platforms=[p for p in PLATFORMS if self.selected[p].get()]
        if not self.rows:
            messagebox.showwarning("CSV","Khtar CSV lwl.");return
        if not platforms:
            messagebox.showwarning("Platform","Khtar platform wa7da 3la l-a9al.");return
        selected=[]
        if "Facebook" in platforms or "Instagram" in platforms:
            if not self.facebook_token.get().strip():
                messagebox.showwarning("Facebook Token","Dkhel User Access Token w klik Load Facebook Pages.");return
            chosen=list(self.pages_list.curselection())
            if not chosen:
                messagebox.showwarning("Pages","Khtar Page mn list.");return
            selected=[self.facebook_pages[i] for i in chosen]
        if "Threads" in platforms and (not self.threads_user_id.get().strip() or not self.threads_token.get().strip()):
            messagebox.showwarning("Threads","Dkhel Threads User ID w Access Token.");return
        if "YouTube" in platforms and not self.youtube_token_path.get().strip():
            messagebox.showwarning("YouTube token","Paste Google OAuth access token ola khtar youtube_token.json.");return
        try:limit=max(1,int(self.limit.get()))
        except ValueError:
            messagebox.showerror("Limit","Dkhel ra9m sahih.");return
        key=self.gemini_key.get().strip() if self.use_ai.get() else ""
        out=Path(self.output_dir.get()).expanduser();out.mkdir(parents=True,exist_ok=True)
        prepared=[(row,make_item(row,i,key)) for i,row in enumerate(self.rows[:limit],1)]
        # Generate a link-in-bio landing page for all CSV products, not just this run's limit.
        html_cards=[]
        for i,row in enumerate(self.rows,1):
            it=make_item(row,i,"")
            if not it.get("link"):
                continue
            image_html = ""
            if it.get("image","").startswith(("https://","http://")):
                image_html = '<img src="' + html.escape(it["image"], quote=True) + '" alt="' + html.escape(it["title"], quote=True) + '">'
            html_cards.append('<article class="product">' + image_html + '<h2>' + html.escape(it["title"]) + '</h2><p>' + html.escape(it["description"]) + '</p><a rel="sponsored nofollow" href="' + html.escape(it["link"], quote=True) + '" target="_blank">View deal</a></article>')
        landing = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DealZone — Product Deals</title><style>body{font-family:Arial,sans-serif;max-width:1000px;margin:auto;padding:20px;background:#f6f7fb;color:#202124}header{text-align:center;padding:20px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.product{background:white;border-radius:14px;padding:14px;box-shadow:0 2px 12px #0001}.product img{width:100%;height:190px;object-fit:contain}.product a{display:inline-block;background:#fe4f4f;color:white;padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:bold}.product h2{font-size:17px}.product p{line-height:1.5}footer{font-size:12px;color:#666;margin:25px 0}</style></head><body><header><h1>DealZone</h1><p>Product finds and current deals</p></header><main>""" + "".join(html_cards) + """</main><footer>Some links may be affiliate links. Price and availability can change; check the retailer listing.</footer></body></html>"""
        (out/"dealzone-links.html").write_text(landing,encoding="utf-8")
        state_path=out/"social_checkpoint.json";state=load_json(state_path)
        fb_done=state.setdefault("facebook",{});ig_done=state.setdefault("instagram",{});th_done=state.setdefault("threads",{});yt_done=state.setdefault("youtube",{})
        counts={p:0 for p in PLATFORMS};errors=[]

        if "Facebook" in platforms:
            for page in selected:
                pid=str(page["id"]);done=fb_done.setdefault(pid,{})
                for row,item in prepared:
                    if item["key"] in done:continue
                    caption=f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}"
                    if item["link"]:caption+=f"\n\nShop link: {item['link']}"
                    try:
                        if item["image"].startswith(("https://","http://")):
                            api_post(GRAPH_BASE,f"{pid}/photos",{"url":item["image"],"caption":caption,"access_token":page.get("access_token","")},"Facebook API")
                        else:
                            api_post(GRAPH_BASE,f"{pid}/feed",{"message":caption,"access_token":page.get("access_token","")},"Facebook API")
                        done[item["key"]]=1;counts["Facebook"]+=1;save_json(state_path,state)
                    except Exception as e:errors.append(f"Facebook / {page.get('name')}: {e}")

        if "Instagram" in platforms:
            for page in selected:
                ig=page.get("instagram_business_account") or {};iid=str(ig.get("id", ""));
                if not iid:errors.append(f"Instagram / {page.get('name')}: Instagram Professional ma mrboutach b Page.");continue
                done=ig_done.setdefault(iid,{})
                for row,item in prepared:
                    if item["key"] in done:continue
                    if not item["image"].startswith("https://"):
                        errors.append(f"Instagram / {page.get('name')}: Image URL public HTTPS khas.");continue
                    bio_url=self.links_page_url.get().strip()
                    cta=(f"\n\n🛍️ Shop this and more: {bio_url}" if bio_url.startswith(("https://","http://")) else "\n\n🛍️ Shop this and more — link in bio.")
                    caption=f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}{cta}"[:2200]
                    try:
                        c=api_post(GRAPH_BASE,f"{iid}/media",{"image_url":item["image"],"caption":caption,"access_token":page.get("access_token","")},"Instagram API")
                        api_post(GRAPH_BASE,f"{iid}/media_publish",{"creation_id":c["id"],"access_token":page.get("access_token","")},"Instagram API")
                        done[item["key"]]=1;counts["Instagram"]+=1;save_json(state_path,state)
                    except Exception as e:errors.append(f"Instagram / {page.get('name')}: {e}")

        if "Threads" in platforms:
            uid=self.threads_user_id.get().strip();token=self.threads_token.get().strip();done=th_done.setdefault(uid,{})
            for row,item in prepared:
                if item["key"] in done:continue
                try:
                    done[item["key"]]=publish_threads(item,uid,token);counts["Threads"]+=1;save_json(state_path,state)
                except Exception as e:errors.append(f"Threads: {e}")

        if "YouTube" in platforms:
            token_path=self.youtube_token_path.get().strip()
            done=yt_done.setdefault(str(Path(token_path).expanduser().resolve()),{})
            for row,item in prepared:
                if item["key"] in done:continue
                try:
                    video_id=publish_youtube(item,token_path)
                    done[item["key"]]=video_id;counts["YouTube"]+=1;save_json(state_path,state)
                except Exception as e:errors.append("YouTube / " + item["title"][:45] + ": " + str(e))

        # Platforms without direct publishing support produce ready CSV files.
        for p in platforms:
            if p in ("Facebook","Instagram","Threads","YouTube"):continue
            rows=[]
            for row,item in prepared:
                rows.append({"Platform":p,"ProductId":item["pid"],"Title":item["title"],"Text":f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}","Description":item["description"],"Hashtags":item["hashtags"],"Image Url":item["image"],"Video Url":item["video"],"Promotion Url":item["link"],"Deduplication Key":item["key"]})
            write_csv(out/f"{p.lower()}_ready.csv",rows);counts[p]=len(rows)

        self.status.set("Done: " + " | ".join(f"{p} {counts[p]}" for p in platforms))
        msg=" | ".join(f"{p}: {counts[p]}" for p in platforms)
        if errors:msg += "\n\nErrors:\n"+"\n".join(errors[:8])
        messagebox.showinfo("DealZone - Done",msg+f"\n\nCheckpoint: {state_path}")


def main():
    root=tk.Tk();
    try:ttk.Style().theme_use("clam")
    except Exception:pass
    SocialPublisher(root);root.mainloop()

if __name__=="__main__":main()
