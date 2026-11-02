import json, re, html, threading, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

HERE=Path(__file__).resolve().parent
STATE=HERE/"published_state.json"
SHARES=HERE/"social_share_state.json"
GRAPH="https://graph.facebook.com/v26.0"
THREADS="https://graph.threads.net/v1.0"

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 DealZoneSocial/1.0"})
    with urllib.request.urlopen(req,timeout=35) as r: return json.loads(r.read().decode("utf-8"))

def post_api(base,path,data):
    req=urllib.request.Request(base+"/"+path.lstrip("/"),data=urllib.parse.urlencode(data).encode(),headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=60) as r: out=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: out=json.loads(e.read().decode()); raise RuntimeError(out.get("error",{}).get("message",str(e)))
        except (ValueError,json.JSONDecodeError): raise RuntimeError("API HTTP "+str(e.code))
    if out.get("error"): raise RuntimeError(out["error"].get("message","API error"))
    return out

def plain(s):
    s=re.sub(r"<(script|style)\b.*?</\1>"," ",s,flags=re.I|re.S)
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",html.unescape(s)).strip()

def page_data(url,title):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=35) as r: source=r.read().decode("utf-8","replace")
    def meta(*names):
        for name in names:
            m=re.search(r'<meta[^>]+(?:property|name)=["\']'+re.escape(name)+r'["\'][^>]+content=["\']([^"\']*)',source,re.I)
            if m:return html.unescape(m.group(1))
            m=re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']'+re.escape(name)+r'["\']',source,re.I)
            if m:return html.unescape(m.group(1))
        return ""
    desc=meta("og:description","description")
    image=meta("og:image","twitter:image")
    video=meta("og:video","og:video:url")
    if not desc:
        m=re.search(r"<article\b.*?</article>",source,re.I|re.S)
        desc=plain(m.group(0))[:1800] if m else title
    return {"title":title,"description":desc[:1800],"image":image,"video":video,"url":url}

class App:
 def __init__(self,root):
    self.root=root; root.title("Blogger Checkpoint → Social Media"); root.geometry("760x690")
    self.token=tk.StringVar(); self.threads_id=tk.StringVar(); self.threads_token=tk.StringVar()
    self.fb=tk.BooleanVar(value=True); self.ig=tk.BooleanVar(value=False); self.th=tk.BooleanVar(value=False)
    self.pages=[]; self.status=tk.StringVar(value="Khtar Facebook token, load pages, w qra checkpoint.")
    f=ttk.Frame(root,padding=16); f.pack(fill="both",expand=True)
    ttk.Label(f,text="BLOGGER CHECKPOINT SOCIAL SHARING",font=("Segoe UI",16,"bold")).pack(anchor="w",pady=(0,12))
    ttk.Label(f,text="Facebook User Access Token").pack(anchor="w")
    ttk.Entry(f,textvariable=self.token,show="*",width=90).pack(fill="x",pady=4)
    ttk.Button(f,text="Load Facebook Pages",command=self.load_pages).pack(anchor="w",pady=5)
    self.lst=tk.Listbox(f,selectmode="extended",height=7,exportselection=False); self.lst.pack(fill="x",pady=5)
    ttk.Label(f,text="Platforms").pack(anchor="w",pady=(8,2))
    for label,var in [("Facebook",self.fb),("Instagram linked to selected Facebook Pages",self.ig),("Threads",self.th)]:
        ttk.Checkbutton(f,text=label,variable=var).pack(anchor="w")
    ttk.Label(f,text="Threads User ID").pack(anchor="w",pady=(8,0))
    ttk.Entry(f,textvariable=self.threads_id,width=70).pack(fill="x")
    ttk.Label(f,text="Threads Access Token").pack(anchor="w",pady=(5,0))
    ttk.Entry(f,textvariable=self.threads_token,show="*",width=70).pack(fill="x")
    ttk.Button(f,text="1. Read Blogger checkpoint",command=self.read_checkpoint).pack(anchor="w",pady=(14,5))
    ttk.Button(f,text="2. SHARE CHECKPOINT TO SELECTED SOCIAL MEDIA",command=self.start).pack(anchor="w",pady=5)
    self.info=ttk.Label(f,text=""); self.info.pack(anchor="w",pady=4)
    self.bar=ttk.Progressbar(f,mode="determinate"); self.bar.pack(fill="x",pady=5)
    ttk.Label(f,textvariable=self.status,wraplength=700).pack(anchor="w",pady=5)
    ttk.Label(f,text="Blogger token/login is not used. Successful shares are remembered in social_share_state.json.",wraplength=700).pack(anchor="w",pady=8)
 def entries(self):
    if not STATE.exists(): raise RuntimeError("Ma l9itch published_state.json f nafs dossier.")
    state=json.loads(STATE.read_text(encoding="utf-8"))
    out=[]
    for posts in state.values():
     if not isinstance(posts,dict): continue
     for rec in posts.values():
      if isinstance(rec,dict) and rec.get("mode")=="publish" and rec.get("url"):
       out.append(rec)
    unique={str(x.get("url")):x for x in out}
    return list(unique.values())
 def read_checkpoint(self):
    try:
     self.records=self.entries(); self.info.config(text=f"Checkpoint: {len(self.records)} published posts found.")
     self.status.set("Checkpoint qri. Blogger login/token ma khassnach.")
    except Exception as e: messagebox.showerror("Checkpoint",str(e))
 def load_pages(self):
    token=self.token.get().strip()
    if not token: messagebox.showwarning("Token","Dkhel Facebook User Access Token."); return
    try:
     data=get_json(GRAPH+"/me/accounts?"+urllib.parse.urlencode({"fields":"id,name,access_token,instagram_business_account","limit":100,"access_token":token}))
     self.pages=[p for p in data.get("data",[]) if p.get("id") and p.get("access_token")]
     self.lst.delete(0,"end")
     for p in self.pages:
      ig=p.get("instagram_business_account") or {}
      self.lst.insert("end",p.get("name","Page")+" | "+str(p["id"])+(" | Instagram linked" if ig.get("id") else " | no Instagram"))
     self.status.set(f"{len(self.pages)} Facebook pages loaded.")
    except Exception as e: messagebox.showerror("Facebook",str(e))
 def start(self):
    try:
     records=getattr(self,"records",None) or self.entries()
     if not records: raise RuntimeError("Checkpoint khawi: ma kaynach posts published.")
     selected=[self.pages[i] for i in self.lst.curselection()]
     if (self.fb.get() or self.ig.get()) and not selected: raise RuntimeError("Load w khtar Facebook Page wa7da 3la l-a9al.")
     if self.th.get() and (not self.threads_id.get().strip() or not self.threads_token.get().strip()): raise RuntimeError("Threads User ID w token daroriyin.")
     count=len(records)*(len(selected)*(int(self.fb.get())+int(self.ig.get()))+int(self.th.get()))
     if not messagebox.askyesno("Confirm",f"Ghadi tpartaji {len(records)} post mn Blogger checkpoint.\\nTargets: {count}.\\nPosts li ma kaynach f social_share_state ghadi ytnchro. Nkmlo?"): return
     self.bar["maximum"]=max(1,count); self.bar["value"]=0
     threading.Thread(target=self.worker,args=(records,selected),daemon=True).start()
    except Exception as e: messagebox.showerror("Sharing",str(e))
 def worker(self,records,pages):
    try: state=json.loads(SHARES.read_text(encoding="utf-8")) if SHARES.exists() else {}
    except Exception: state={}
    targets=[]
    for rec in records:
     for p in pages:
      if self.fb.get(): targets.append((rec,"Facebook",p))
      if self.ig.get(): targets.append((rec,"Instagram",p))
     if self.th.get(): targets.append((rec,"Threads",None))
    done=skip=errors=0
    for n,(rec,platform,page) in enumerate(targets,1):
     url=rec["url"]; pid=str(rec.get("post_id") or url); target=str(page.get("id")) if page else self.threads_id.get().strip()
     key=f"{pid}:{platform}:{target}"
     if state.get(key,{}).get("status")=="success": skip+=1
     else:
      try:
       item=page_data(url,rec.get("title") or "Blogger post")
       caption=(item["title"]+"\\n\\n"+item["description"]+"\\n\\n"+url)[:2200]
       if platform=="Facebook":
        result=post_api(GRAPH,f"{target}/feed",{"message":caption[:5000],"link":url,"access_token":page["access_token"]})
       elif platform=="Instagram":
        igid=str((page.get("instagram_business_account") or {}).get("id",""))
        if not igid or not item["image"].startswith("https://"): raise RuntimeError("Instagram kay7taj Instagram Professional linked w og:image HTTPS.")
        c=post_api(GRAPH,f"{igid}/media",{"image_url":item["image"],"caption":caption,"access_token":page["access_token"]})
        result=post_api(GRAPH,f"{igid}/media_publish",{"creation_id":c["id"],"access_token":page["access_token"]})
       else:
        p={"access_token":self.threads_token.get().strip(),"text":caption[:500]}
        if item["image"].startswith("https://"): p.update({"media_type":"IMAGE","image_url":item["image"]})
        c=post_api(THREADS,f"{target}/threads",p)
        result=post_api(THREADS,f"{target}/threads_publish",{"creation_id":c["id"],"access_token":self.threads_token.get().strip()})
       state[key]={"status":"success","result_id":result.get("id","OK"),"url":url,"platform":platform,"target_id":target}
       done+=1
      except Exception as e:
       state[key]={"status":"failed","error":str(e)[:500],"url":url,"platform":platform,"target_id":target}; errors+=1
      SHARES.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
     self.root.after(0,lambda n=n,d=done,s=skip,e=errors,t=len(targets): (self.bar.configure(value=n),self.status.set(f"{n}/{t} | Success {d} | Skipped {s} | Errors {e}")))
     time.sleep(2)
    self.root.after(0,lambda:messagebox.showinfo("Finished",f"Success: {done}\\nAlready shared: {skip}\\nErrors: {errors}\\nDetails: social_share_state.json"))
if __name__=="__main__":
 root=tk.Tk(); App(root); root.mainloop()
