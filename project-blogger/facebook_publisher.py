import csv, hashlib, html, json, re, threading, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent
GRAPH = "https://graph.facebook.com/v26.0"
CHECKPOINT = ROOT / "facebook_checkpoint.json"

def clean(v):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", html.unescape(str(v or "")))).strip()

def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample=f.read(16000); f.seek(0)
        try: dialect=csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error: dialect=csv.excel
        reader=csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames: raise ValueError("CSV ma fihch headers.")
        headers=[str(x or "").strip() for x in reader.fieldnames]
        rows=[{str(k or "").strip():clean(v) for k,v in r.items() if k is not None} for r in reader]
        rows=[r for r in rows if any(r.values())]
        if not rows: raise ValueError("CSV ma fih ta rows.")
        return rows,headers

def api(method,url,params=None,label="Facebook API",json_body=False):
    params=params or {}; data=None; headers={}
    if method=="POST":
        data=json.dumps(params).encode("utf-8") if json_body else urllib.parse.urlencode(params).encode("utf-8")
        headers["Content-Type"]="application/json" if json_body else "application/x-www-form-urlencoded"
    elif params: url += ("&" if "?" in url else "?")+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=90) as r: result=json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err=json.loads(e.read().decode("utf-8")).get("error",{})
            raise RuntimeError(f"{label} ({err.get('code',e.code)}): {err.get('message','API error')}")
        except (ValueError,json.JSONDecodeError): raise RuntimeError(f"{label} HTTP error: {e.code}")
    except urllib.error.URLError as e: raise RuntimeError(f"{label}: connection failed: {e.reason}")
    if isinstance(result,dict) and result.get("error"):
        err=result["error"]; raise RuntimeError(f"{label} ({err.get('code')}): {err.get('message','API error')}")
    return result

def value(row, chosen, aliases=()):
    if chosen and chosen!="(Auto-detect)" and clean(row.get(chosen)): return clean(row[chosen])
    lookup={str(k).strip().lower():k for k in row}
    for name in aliases:
        k=lookup.get(name.lower())
        if k is not None and clean(row.get(k)): return clean(row[k])
    return ""

def gemini_tags(title,desc,key):
    prompt="Create 5-8 relevant, non-spam product hashtags. Return only hashtags separated by spaces; do not invent product features.\nTitle: "+title[:300]+"\nDescription: "+desc[:700]
    body={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.2,"maxOutputTokens":120}}
    url="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?"+urllib.parse.urlencode({"key":key})
    data=api("POST",url,body,"Gemini API",True)
    cs=data.get("candidates",[])
    txt=" ".join(p.get("text","") for p in cs[0].get("content",{}).get("parts",[])) if cs else ""
    tags=list(dict.fromkeys(re.findall(r"#[A-Za-z0-9_]+",txt)))
    if not tags: raise RuntimeError("Gemini ma rje3 ta hashtag صالح.")
    return " ".join(tags[:8])

def make_item(row,i,cols,tagmode,gkey):
    title=value(row,cols["title"],("Title","Product Title","Product Name","Name","Product Desc","Product Description")) or f"Product {i}"
    desc=value(row,cols["description"],("Description","SEO_Description","SEO Description","Product Description","Product Desc"))
    image=value(row,cols["image"],("Image Url","Image URL","ImageUrl","Image","Main Image","Image/Video Url"))
    video=value(row,cols["video"],("Video Url","Video URL","VideoUrl","Video","Product Video","Video Link"))
    link=value(row,cols["link"],("Promotion Url","Promotion URL","Product URL","Buy Link","Affiliate Link","Link","URL"))
    raw=value(row,cols["hashtags"],("Hashtags","SEO_Hashtags","Tags"))
    tags=list(dict.fromkeys(re.findall(r"#[A-Za-z0-9_]+",raw)))
    if tagmode=="Gemini":
        if not gkey: raise ValueError("Dkhel Gemini API key ola khtar source akhor.")
        hashtags=gemini_tags(title,desc,gkey)
    elif tagmode=="CSV column" and tags: hashtags=" ".join(tags[:8])
    else:
        words=[w for w in re.findall(r"[A-Za-z0-9]+",title.lower()) if len(w)>2]
        hashtags=" ".join(tags[:8] if tags else ["#"+w for w in list(dict.fromkeys(words))[:5]+["DealZone"]])
    caption=title + (("\n\n"+desc) if desc else "") + (("\n\n"+hashtags) if hashtags else "") + (("\n\nProduct link: "+link) if link else "")
    pid=value(row,"",("ProductId","Product ID","Item ID","ID"))
    stable=pid or link or f"{title}|row:{i}"
    return {"title":title,"description":desc,"image":image,"video":video,"link":link,"hashtags":hashtags,
            "caption":caption[:5000],"key":hashlib.sha256(stable.encode("utf-8",errors="ignore")).hexdigest()}

def load_state():
    try:
        d=json.loads(CHECKPOINT.read_text(encoding="utf-8")); return d if isinstance(d,dict) else {}
    except Exception: return {}

def save_state(d):
    temp=CHECKPOINT.with_suffix(".tmp"); temp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(CHECKPOINT)

def suggest(headers,names):
    low={h.lower():h for h in headers}
    return next((low[n.lower()] for n in names if n.lower() in low),"(Auto-detect)")

class App:
 def __init__(self,root):
    self.root=root; root.title("Project Facebook Publisher"); root.geometry("900x820"); root.minsize(720,620)
    self.rows=[]; self.headers=[]; self.pages=[]
    self.path=tk.StringVar(value="Ma khtart ta CSV"); self.token=tk.StringVar(); self.limit=tk.StringVar(value="20")
    self.media=tk.StringVar(value="Automatic"); self.tagmode=tk.StringVar(value="CSV column"); self.gemini=tk.StringVar()
    self.status=tk.StringVar(value="Khtar CSV, dkhel token, w loadi Facebook Pages.")
    self.cols={k:tk.StringVar(value="(Auto-detect)") for k in ("title","description","image","video","link","hashtags")}
    self.build()
 def build(self):
    shell=ttk.Frame(self.root); shell.pack(fill="both",expand=True); cv=tk.Canvas(shell,highlightthickness=0); sb=ttk.Scrollbar(shell,orient="vertical",command=cv.yview)
    cv.configure(yscrollcommand=sb.set); sb.pack(side="right",fill="y"); cv.pack(side="left",fill="both",expand=True)
    main=ttk.Frame(cv,padding=16); win=cv.create_window((0,0),window=main,anchor="nw")
    main.bind("<Configure>",lambda e:cv.configure(scrollregion=cv.bbox("all"))); cv.bind("<Configure>",lambda e:cv.itemconfigure(win,width=e.width))
    cv.bind_all("<MouseWheel>",lambda e:cv.yview_scroll(int(-e.delta/120),"units"))
    ttk.Label(main,text="PROJECT FACEBOOK PUBLISHER",font=("Segoe UI",18,"bold")).pack(anchor="w")
    ttk.Label(main,text="CSV → choose columns → image/video/text → Facebook Pages").pack(anchor="w",pady=(0,12))
    ttk.Label(main,text="1. CSV file").pack(anchor="w"); r=ttk.Frame(main); r.pack(fill="x",pady=4)
    ttk.Entry(r,textvariable=self.path,state="readonly").pack(side="left",fill="x",expand=True); ttk.Button(r,text="Choose CSV",command=self.choose).pack(side="left",padx=6)
    ttk.Label(main,text="2. CSV column mapping",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(12,4)); self.combos={}
    for label,k in [("Title","title"),("Description","description"),("Image URL","image"),("Video URL","video"),("Product / promotion link","link"),("Hashtags","hashtags")]:
        r=ttk.Frame(main); r.pack(fill="x",pady=2); ttk.Label(r,text=label,width=24).pack(side="left")
        c=ttk.Combobox(r,textvariable=self.cols[k],values=["(Auto-detect)"],state="readonly"); c.pack(side="left",fill="x",expand=True); self.combos[k]=c
    ttk.Label(main,text="3. Media mode").pack(anchor="w",pady=(12,3))
    ttk.Combobox(main,textvariable=self.media,values=["Automatic","Image only","Video only","Text only"],state="readonly").pack(fill="x")
    ttk.Label(main,text="Automatic = video first, then image, otherwise text.").pack(anchor="w",pady=(2,0))
    ttk.Label(main,text="4. Hashtags source").pack(anchor="w",pady=(10,3))
    ttk.Combobox(main,textvariable=self.tagmode,values=["CSV column","Gemini","Automatic"],state="readonly").pack(fill="x")
    ttk.Label(main,text="Gemini API key (only when Gemini selected)").pack(anchor="w",pady=(6,3)); ttk.Entry(main,textvariable=self.gemini,show="*").pack(fill="x")
    ttk.Label(main,text="5. Facebook User Access Token").pack(anchor="w",pady=(12,3)); r=ttk.Frame(main); r.pack(fill="x")
    ttk.Entry(r,textvariable=self.token,show="*").pack(side="left",fill="x",expand=True); ttk.Button(r,text="Load Facebook Pages",command=self.load_pages).pack(side="left",padx=6)
    ttk.Label(main,text="6. Pages (Ctrl/Shift to select multiple)").pack(anchor="w",pady=(8,3))
    self.pagebox=tk.Listbox(main,height=6,selectmode=tk.EXTENDED,exportselection=False); self.pagebox.pack(fill="x")
    ttk.Label(main,text="Max posts per run").pack(anchor="w",pady=(10,3)); ttk.Entry(main,textvariable=self.limit,width=10).pack(anchor="w")
    ttk.Label(main,text="Preview first row").pack(anchor="w",pady=(10,3)); self.preview=tk.Text(main,height=6,wrap="word"); self.preview.pack(fill="x")
    r=ttk.Frame(main); r.pack(fill="x",pady=10); ttk.Button(r,text="Preview",command=self.preview_first).pack(side="left")
    ttk.Button(r,text="Start publishing",command=self.start).pack(side="left",padx=8)
    ttk.Label(main,textvariable=self.status,wraplength=830).pack(anchor="w",pady=4)
 def choose(self):
    p=filedialog.askopenfilename(title="Choose CSV",filetypes=[("CSV files","*.csv"),("All files","*.*")])
    if not p:return
    try:
        self.rows,self.headers=read_csv(p); self.path.set(p); choices=["(Auto-detect)"]+self.headers
        for c in self.combos.values(): c["values"]=choices
        defaults={"title":("Product Title","Title","Product Name","Name","Product Desc"),"description":("SEO_Description","SEO Description","Description","Product Description","Product Desc"),"image":("Image Url","Image URL","Image","ImageUrl","Image/Video Url"),"video":("Video Url","Video URL","Video","VideoUrl","Product Video"),"link":("Promotion Url","Promotion URL","Product URL","Buy Link","Link"),"hashtags":("Hashtags","SEO_Hashtags","Tags")}
        for k,names in defaults.items():self.cols[k].set(suggest(self.headers,names))
        self.status.set(f"CSV ready: {len(self.rows)} rows / {len(self.headers)} columns."); self.preview_first()
    except Exception as e:messagebox.showerror("CSV error",str(e))
 def item(self,row,i):
    return make_item(row,i,{k:v.get() for k,v in self.cols.items()},self.tagmode.get(),self.gemini.get().strip())
 def preview_first(self):
    if not self.rows:messagebox.showwarning("CSV","Khtar CSV lwl.");return
    try:
        it=self.item(self.rows[0],1); self.preview.delete("1.0","end")
        self.preview.insert("end",f"TITLE\n{it['title']}\n\nCAPTION\n{it['caption']}\n\nIMAGE\n{it['image'] or '(none)'}\nVIDEO\n{it['video'] or '(none)'}")
    except Exception as e:messagebox.showerror("Preview",str(e))
 def load_pages(self):
    token=self.token.get().strip()
    if not token:messagebox.showwarning("Token","Dkhel Facebook User Access Token lwl.");return
    try:
        pages=[]; after=None
        while True:
            params={"fields":"id,name,access_token,tasks","limit":"100","access_token":token}
            if after:params["after"]=after
            data=api("GET",GRAPH+"/me/accounts",params); pages.extend(data.get("data",[])); after=(data.get("paging",{}).get("cursors",{}) or {}).get("after")
            if not after or not data.get("data"):break
        self.pages=list({str(p["id"]):p for p in pages if p.get("id") and p.get("access_token")}.values());self.pagebox.delete(0,"end")
        for p in self.pages:self.pagebox.insert("end",f"{p.get('name','Page')} | ID: {p.get('id')}")
        if not self.pages:raise RuntimeError("Ma ban ta Page Access Token. Chouf token permissions w Page access.")
        self.status.set(f"L9ina {len(self.pages)} Pages.");messagebox.showinfo("Pages",f"L9ina {len(self.pages)} Pages. Khtar li bghiti.")
    except Exception as e:messagebox.showerror("Facebook API",str(e))
 def start(self):
    if not self.rows:messagebox.showwarning("CSV","Khtar CSV lwl.");return
    selected=list(self.pagebox.curselection())
    if not selected:messagebox.showwarning("Pages","Load Facebook Pages w khtar wa7da 3la l-a9al.");return
    try:
        limit=int(self.limit.get())
        if limit<1:raise ValueError()
    except ValueError:messagebox.showerror("Limit","Dkhel ra9m kber men 0.");return
    if self.tagmode.get()=="Gemini" and not self.gemini.get().strip():messagebox.showwarning("Gemini","Dkhel Gemini API key.");return
    if not messagebox.askyesno("Confirm",f"Publishing max {limit} rows to {len(selected)} Page(s). Continue?"):return
    self.status.set("Publishing started...");threading.Thread(target=self.worker,args=(selected,limit),daemon=True).start()
 def worker(self,selected,limit):
    try:
        filekey=str(Path(self.path.get()).resolve());state=load_state();fs=state.setdefault(filekey,{})
        cols={k:v.get() for k,v in self.cols.items()};pages=[self.pages[i] for i in selected];mode=self.media.get()
        done=skipped=0;errors=[]
        for page in pages:
            pid=str(page["id"]);ps=fs.setdefault(pid,{});page_done=0
            for idx,row in enumerate(self.rows,1):
                try:
                    it=make_item(row,idx,cols,self.tagmode.get(),self.gemini.get().strip());ck=it["key"]
                    if ck in ps:skipped+=1;continue
                    image=it["image"].strip();video=it["video"].strip()
                    media=("video" if mode=="Video only" else "image" if mode=="Image only" else "text" if mode=="Text only" else "video" if video.startswith(("https://","http://")) else "image" if image.startswith(("https://","http://")) else "text")
                    token=page["access_token"]
                    if media=="video":
                        if not video.startswith(("https://","http://")):raise RuntimeError("Had row ma fihch Video URL.")
                        result=api("POST",f"{GRAPH}/{pid}/videos",{"file_url":video,"description":it["caption"],"access_token":token},"Facebook video publish")
                    elif media=="image":
                        if not image.startswith(("https://","http://")):raise RuntimeError("Had row ma fihch Image URL.")
                        result=api("POST",f"{GRAPH}/{pid}/photos",{"url":image,"caption":it["caption"],"access_token":token},"Facebook image publish")
                    else:result=api("POST",f"{GRAPH}/{pid}/feed",{"message":it["caption"],"access_token":token},"Facebook text publish")
                    postid=result.get("id") or result.get("post_id")
                    if not postid:raise RuntimeError("Facebook ma rje3ch post ID; checkpoint ma tsajelch.")
                    ps[ck]={"post_id":postid,"row":idx,"time":time.strftime("%Y-%m-%d %H:%M:%S"),"media":media,"title":it["title"]}
                    save_state(state);done+=1;page_done+=1;self.root.after(0,lambda d=done,pn=page.get("name",pid):self.status.set(f"Published {d}; Page: {pn}"));time.sleep(.4)
                    if page_done>=limit:break
                except Exception as e:errors.append(f"{page.get('name',pid)} / row {idx}: {str(e)[:220]}")
        summary=f"Finished. Published: {done}. Already checkpointed: {skipped}. Errors: {len(errors)}."
        if errors:summary+="\n\n"+"\n".join(errors[:12])
        self.root.after(0,lambda s=summary:self.finished(s))
    except Exception as e:self.root.after(0,lambda m=str(e):self.finished("App error: "+m))
 def finished(self,summary):
    self.status.set(summary.replace("\n"," | ")[:1100]);messagebox.showinfo("Facebook Publisher",summary+f"\n\nCheckpoint: {CHECKPOINT}")

def main():
    root=tk.Tk()
    try:ttk.Style().theme_use("clam")
    except Exception:pass
    App(root);root.mainloop()
if __name__=="__main__":main()
