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
        try:limit=max(1,int(self.limit.get()))
        except ValueError:
            messagebox.showerror("Limit","Dkhel ra9m sahih.");return
        key=self.gemini_key.get().strip() if self.use_ai.get() else ""
        out=Path(self.output_dir.get()).expanduser();out.mkdir(parents=True,exist_ok=True)
        prepared=[(row,make_item(row,i,key)) for i,row in enumerate(self.rows[:limit],1)]
        state_path=out/"social_checkpoint.json";state=load_json(state_path)
        fb_done=state.setdefault("facebook",{});ig_done=state.setdefault("instagram",{});th_done=state.setdefault("threads",{})
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
                    caption=f"{item['title']}\n\n{item['description']}\n\n{item['hashtags']}"[:2200]
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

        # For platforms without a direct API configured in this app, always produce ready CSVs.
        for p in platforms:
            if p in ("Facebook","Instagram","Threads"):continue
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
