# -*- coding: utf-8 -*-
import csv, json, re, threading, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

HERE=Path(__file__).resolve().parent
USED=HERE/"used_page_names.json"
MODEL="gemini-3.8-flash"
GEMINI="https://generativelanguage.googleapis.com/v1beta/models/"+MODEL+":generateContent"
GRAPH="https://graph.facebook.com/v27.0"
COLS=["Page Name","Username","Bio","Description","Category","Profile Image Prompt","Cover Image Prompt","Keywords","Post Message"]

def api(url,data=None,headers=None,timeout=90):
    req=urllib.request.Request(url,data=data,headers=headers or {},method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg=e.read().decode("utf-8",errors="replace")
        try: msg=json.loads(msg).get("error",{}).get("message",msg)
        except Exception: pass
        raise RuntimeError("API HTTP "+str(e.code)+": "+msg[:1000])

def parse_json(s):
    s=s.strip()
    fence=chr(96)*3
    if s.startswith(fence): s=re.sub(r"^"+re.escape(fence)+r"(?:json)?\s*","",s,flags=re.I)
    if s.endswith(fence): s=s[:-3].strip()
    return json.loads(s)

class App:
    def __init__(self,root):
        self.root=root; root.title("Facebook Page Creator | Gemini + Meta")
        root.geometry("830x650"); root.minsize(740,600)
        self.gemini=tk.StringVar(); self.facebook=tk.StringVar(); self.csv=None
        self.pages=[]; self.page_choice=tk.StringVar(); self.stop_flag=False
        self.status=tk.StringVar(value="دخل مفاتيح API واختار CSV.")
        self.make_ui()

    def make_ui(self):
        m=ttk.Frame(self.root,padding=16); m.pack(fill="both",expand=True)
        ttk.Label(m,text="Facebook Page Creator",font=("Segoe UI",19,"bold")).pack(anchor="w")
        ttk.Label(m,text="Gemini لتجهيز CSV + Meta API لجلب صفحاتك والنشر فيها.").pack(anchor="w",pady=(3,12))
        keys=ttk.LabelFrame(m,text="API Keys — لا تُحفظ في GitHub أو الملفات",padding=10); keys.pack(fill="x",pady=5)
        ttk.Label(keys,text="Gemini API Key").grid(row=0,column=0,sticky="w",pady=5)
        ttk.Entry(keys,textvariable=self.gemini,show="*",width=70).grid(row=0,column=1,sticky="ew",pady=5)
        ttk.Label(keys,text="Facebook User Access Token").grid(row=1,column=0,sticky="w",pady=5)
        ttk.Entry(keys,textvariable=self.facebook,show="*",width=70).grid(row=1,column=1,sticky="ew",pady=5)
        keys.columnconfigure(1,weight=1)
        ttk.Label(keys,text="ما ترسل حتى Token أو API Key فالمحادثة؛ دخلهم غير هنا محلياً.",foreground="#9a4b00").grid(row=2,column=0,columnspan=2,sticky="w",pady=5)
        box=ttk.LabelFrame(m,text="CSV",padding=10); box.pack(fill="x",pady=8)
        rr=ttk.Frame(box); rr.pack(fill="x")
        ttk.Button(rr,text="اختيار CSV",command=self.pick_csv).pack(side="left")
        self.file_label=ttk.Label(rr,text="لم يتم اختيار ملف"); self.file_label.pack(side="left",padx=10)
        ttk.Label(box,text="CSV الناتج فيه 9 أعمدة، ومنها Post Message للنشر.").pack(anchor="w",pady=6)
        gen=ttk.LabelFrame(m,text="Gemini — تجهيز محتوى CSV",padding=10); gen.pack(fill="x",pady=6)
        self.gen_btn=ttk.Button(gen,text="إنشاء CSV بالذكاء الاصطناعي",command=self.start_gen); self.gen_btn.pack(side="left")
        self.stop_btn=ttk.Button(gen,text="إيقاف",command=self.stop,state="disabled"); self.stop_btn.pack(side="left",padx=8)
        fb=ttk.LabelFrame(m,text="Facebook — صفحاتك والنشر",padding=10); fb.pack(fill="x",pady=6)
        row=ttk.Frame(fb); row.pack(fill="x")
        ttk.Button(row,text="جلب صفحاتي",command=self.get_pages).pack(side="left")
        self.combo=ttk.Combobox(row,textvariable=self.page_choice,state="readonly",width=48); self.combo.pack(side="left",padx=8,fill="x",expand=True)
        ttk.Button(row,text="نشر منشورات CSV",command=self.publish).pack(side="left")
        ttk.Label(fb,text="النشر يتطلب صلاحيات pages_show_list وpages_manage_posts وpages_read_engagement ومهمة CREATE_CONTENT.",wraplength=780).pack(anchor="w",pady=7)
        ttk.Separator(m).pack(fill="x",pady=8)
        ttk.Label(m,textvariable=self.status,wraplength=780).pack(anchor="w")
        self.progress=ttk.Progressbar(m,maximum=100); self.progress.pack(fill="x",pady=8)
        ttk.Label(m,text="إنشاء صفحات جديدة عبر API محدود من Meta لحسابات الاختبار أو التطبيقات المسموح لها فقط.",foreground="#9a4b00",wraplength=780).pack(anchor="w",pady=8)

    def pick_csv(self):
        p=filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        if p: self.csv=Path(p); self.file_label.config(text=str(self.csv))

    def stop(self): self.stop_flag=True; self.status.set("غادي يتوقف بعد الطلب الحالي ويحفظ النتائج.")

    def used_names(self):
        try: return set(json.loads(USED.read_text(encoding="utf-8")))
        except Exception: return set()

    def save_name(self,n):
        u=self.used_names(); u.add(n.casefold()); USED.write_text(json.dumps(sorted(u),ensure_ascii=False,indent=2),encoding="utf-8")

    def start_gen(self):
        if not self.gemini.get().strip(): messagebox.showwarning("Gemini","دخل Gemini API Key."); return
        if not self.csv or not self.csv.is_file(): messagebox.showwarning("CSV","اختار ملف CSV."); return
        try:
            with self.csv.open(encoding="utf-8-sig",newline="") as f:
                reader=csv.DictReader(f); headers=reader.fieldnames or []; rows=list(reader)
            if not rows: raise ValueError("CSV فارغ.")
            if len(rows)>500: raise ValueError("الحد الأقصى 500 سطر.")
        except Exception as e: messagebox.showerror("CSV",str(e)); return
        self.stop_flag=False; self.gen_btn.config(state="disabled"); self.stop_btn.config(state="normal")
        threading.Thread(target=self.gen_worker,args=(self.gemini.get().strip(),headers,rows),daemon=True).start()

    def gemini_one(self,key,seed,rowno,used):
        prompt=("Create one original professional Facebook Page record. Return only valid JSON. Exact keys: "+json.dumps(COLS)+
        ". Write in English. Create unique Page Name and Username, concise Bio, useful Description, suitable Category, detailed profile and cover image prompts, keywords, and a ready-to-publish introductory Post Message. Avoid false claims and spam. Do not reuse these names: "+
        json.dumps(sorted(used)[-250:],ensure_ascii=False)+". Input: "+json.dumps(seed,ensure_ascii=False)+". Row "+str(rowno))
        body=json.dumps({"contents":[{"role":"user","parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json","temperature":0.8}}).encode()
        result=api(GEMINI,body,{"Content-Type":"application/json","x-goog-api-key":key})
        try: txt=result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception: raise RuntimeError("Gemini رجع جواب غير مفهوم: "+str(result)[:400])
        obj=parse_json(txt)
        return {c:str(obj.get(c,"")).strip() for c in COLS}

    def gen_worker(self,key,headers,rows):
        aliases={"Page Name":["page name","name","title"],"Username":["username"],"Bio":["bio"],"Description":["description"],"Category":["category"],"Profile Image Prompt":["profile image prompt"],"Cover Image Prompt":["cover image prompt"],"Keywords":["keywords"],"Post Message":["post message","message"]}
        h={x.casefold():x for x in headers if x}; mapping={c:next((h[a] for a in aliases[c] if a in h),None) for c in COLS}
        used=self.used_names(); done=[]; errors=[]
        out=self.csv.with_name(self.csv.stem+"_ready_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".csv")
        for i,row in enumerate(rows,1):
            if self.stop_flag: break
            seed={c:row.get(mapping[c],"") if mapping[c] else "" for c in COLS}
            try:
                item=self.gemini_one(key,seed,i,used); name=item["Page Name"]
                if not name or name.casefold() in used: raise RuntimeError("اسم فارغ أو مكرر.")
                item["Username"]=re.sub(r"[^a-z0-9._]","",item["Username"].replace(" ","").lower())[:30]
                done.append(item); used.add(name.casefold()); self.save_name(name)
            except Exception as e: errors.append("السطر "+str(i)+": "+str(e))
            try:
                with out.open("w",encoding="utf-8-sig",newline="") as f:
                    w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); w.writerows(done)
            except Exception as e: errors.append("حفظ CSV: "+str(e))
            self.root.after(0,lambda v=i/len(rows)*100:self.progress.configure(value=v))
        def finish():
            self.gen_btn.config(state="normal"); self.stop_btn.config(state="disabled")
            self.status.set("تجهز "+str(len(done))+" سجل.")
            if errors: messagebox.showwarning("ملاحظات","\n".join(errors[:8]))
            if done:
                self.csv=out; self.file_label.config(text=str(out))
                messagebox.showinfo("CSV واجد",str(out))
            elif not self.stop_flag: messagebox.showerror("Gemini","ما تجهز حتى سجل.")
        self.root.after(0,finish)

    def get_pages(self):
        token=self.facebook.get().strip()
        if not token: messagebox.showwarning("Facebook","دخل User Access Token. ما ترسلوش هنا."); return
        self.status.set("جاري جلب صفحاتك...")
        threading.Thread(target=self.pages_worker,args=(token,),daemon=True).start()

    def pages_worker(self,token):
        try:
            q=urllib.parse.urlencode({"fields":"id,name,access_token,tasks","access_token":token})
            data=api(GRAPH+"/me/accounts?"+q); self.pages=data.get("data",[])
            if not self.pages: raise RuntimeError("ما لقيتش صفحات. تأكد من pages_show_list وصلاحيات الحساب.")
            labels=[p.get("name","Page")+" | "+p.get("id","") for p in self.pages]
            def done():
                self.combo["values"]=labels; self.combo.current(0); self.status.set("تم جلب "+str(len(labels))+" صفحة.")
            self.root.after(0,done)
        except Exception as e: self.root.after(0,lambda err=str(e):messagebox.showerror("Facebook API",err))

    def publish(self):
        ix=self.combo.current()
        if ix<0 or not self.pages: messagebox.showwarning("Facebook","جلب صفحاتك واختار صفحة."); return
        if not self.csv or not self.csv.is_file(): messagebox.showwarning("CSV","اختار CSV."); return
        page=self.pages[ix]
        if not page.get("access_token"): messagebox.showerror("Facebook","Meta ما رجعاتش Page Access Token."); return
        try:
            with self.csv.open(encoding="utf-8-sig",newline="") as f:
                reader=csv.DictReader(f); rows=list(reader)
                if "Post Message" not in (reader.fieldnames or []): raise ValueError("خاص عمود Post Message.")
        except Exception as e: messagebox.showerror("CSV",str(e)); return
        if not messagebox.askyesno("تأكيد","نشر المنشورات في "+page.get("name","Page")+"؟"): return
        threading.Thread(target=self.publish_worker,args=(page,rows),daemon=True).start()

    def publish_worker(self,page,rows):
        ok=0; errors=[]
        for i,row in enumerate(rows,1):
            msg=(row.get("Post Message") or "").strip()
            if not msg: continue
            try:
                body=urllib.parse.urlencode({"message":msg,"access_token":page["access_token"]}).encode()
                api(GRAPH+"/"+page["id"]+"/feed",body,{"Content-Type":"application/x-www-form-urlencoded"}); ok+=1
            except Exception as e: errors.append("السطر "+str(i)+": "+str(e))
            self.root.after(0,lambda v=i/len(rows)*100:self.progress.configure(value=v))
        def finish():
            self.status.set("نشر ناجح: "+str(ok)+" | فشل: "+str(len(errors)))
            if errors: messagebox.showwarning("نتيجة النشر","\n".join(errors[:8]))
            else: messagebox.showinfo("تم","تم نشر "+str(ok)+" منشور.")
        self.root.after(0,finish)

if __name__=="__main__":
    root=tk.Tk()
    try: ttk.Style().theme_use("clam")
    except Exception: pass
    App(root); root.mainloop()
