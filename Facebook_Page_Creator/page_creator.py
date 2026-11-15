# -*- coding: utf-8 -*-
"""Facebook Page Creator: map CSV columns and prepare one or all page folders."""
import csv, json, shutil, tkinter as tk, webbrowser, re, os
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "prepared_pages"
FIELDS = [
    ("page_name", "اسم الصفحة"), ("username", "اسم المستخدم المقترح"),
    ("category", "التصنيف"), ("description", "الوصف"),
    ("bio", "نبذة قصيرة"), ("website", "الموقع الإلكتروني"),
    ("email", "البريد الإلكتروني"), ("phone", "الهاتف"),
    ("city", "المدينة"), ("language", "اللغة"),
]

def slugify(value):
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value).strip()).strip("-").lower()
    return s or "facebook-page"

class App:
    def __init__(self, root):
        self.root = root
        root.title("Facebook Page Creator | تجهيز الصفحات من CSV")
        root.geometry("980x790")
        root.minsize(800, 650)
        self.entries, self.rows, self.headers = {}, [], []
        self.mapping, self.index = {}, 0
        self.profile = self.cover = self.csv_path = None
        self.status = tk.StringVar(value="جاهز. حمّل CSV ثم اختَر الأعمدة.")
        self.build()

    def build(self):
        outer = ttk.Frame(self.root, padding=12); outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="أداة تجهيز صفحات Facebook", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(outer, text="حمّل CSV بأي أسماء أعمدة، واربط كل خانة بالعمود المناسب مثل طريقة Blogger.", wraplength=930).pack(anchor="w", pady=(4,10))
        bar = ttk.LabelFrame(outer, text="ملف CSV وربط الأعمدة", padding=8); bar.pack(fill="x")
        row = ttk.Frame(bar); row.pack(fill="x")
        ttk.Button(row, text="تحميل CSV واختيار الأعمدة", command=self.load_csv).pack(side="left", padx=4)
        ttk.Button(row, text="تغيير ربط الأعمدة", command=self.mapping_window).pack(side="left", padx=4)
        ttk.Button(row, text="تجهيز جميع الصفحات من CSV", command=self.save_all).pack(side="left", padx=4)
        self.csv_label = ttk.Label(bar, text="لم يتم تحميل CSV بعد"); self.csv_label.pack(anchor="w", pady=(6,0))
        nav = ttk.Frame(outer); nav.pack(fill="x", pady=8)
        ttk.Button(nav, text="◀ السابق", command=self.prev).pack(side="left")
        self.nav_label = ttk.Label(nav, text="لا توجد بيانات CSV"); self.nav_label.pack(side="left", padx=12)
        ttk.Button(nav, text="التالي ▶", command=self.next).pack(side="left")
        form = ttk.LabelFrame(outer, text="معلومات الصفحة الحالية", padding=9); form.pack(fill="both", expand=True)
        for i,(key,label) in enumerate(FIELDS):
            r,c = divmod(i,2); cell=ttk.Frame(form); cell.grid(row=r,column=c,sticky="ew",padx=7,pady=5)
            ttk.Label(cell,text=label).pack(anchor="w")
            ent=ttk.Entry(cell); ent.pack(fill="x",pady=(2,0)); self.entries[key]=ent
        form.columnconfigure(0,weight=1); form.columnconfigure(1,weight=1)
        assets=ttk.LabelFrame(outer,text="صور اختيارية مشتركة للصفحات",padding=8); assets.pack(fill="x",pady=(8,0))
        a=ttk.Frame(assets); a.pack(fill="x")
        self.profile_label=ttk.Label(a,text="Profile: لم يتم الاختيار"); self.profile_label.pack(side="left",expand=True,anchor="w")
        ttk.Button(a,text="اختيار Profile",command=self.pick_profile).pack(side="right")
        b=ttk.Frame(assets); b.pack(fill="x",pady=(5,0))
        self.cover_label=ttk.Label(b,text="Cover: لم يتم الاختيار"); self.cover_label.pack(side="left",expand=True,anchor="w")
        ttk.Button(b,text="اختيار Cover",command=self.pick_cover).pack(side="right")
        actions=ttk.Frame(outer); actions.pack(fill="x",pady=10)
        ttk.Button(actions,text="حفظ الصفحة الحالية",command=self.save_current).pack(side="left",padx=4)
        ttk.Button(actions,text="فتح إنشاء صفحة Facebook",command=lambda:webbrowser.open("https://www.facebook.com/pages/create/")).pack(side="left",padx=4)
        ttk.Button(actions,text="فتح مجلد النتائج",command=self.open_output).pack(side="left",padx=4)
        ttk.Label(outer,textvariable=self.status,wraplength=930).pack(anchor="w",pady=(6,0))

    def load_csv(self):
        path=filedialog.askopenfilename(title="اختيار CSV",filetypes=[("CSV files","*.csv")])
        if not path: return
        try:
            with open(path,"r",encoding="utf-8-sig",newline="") as f:
                reader=csv.DictReader(f)
                self.headers=[h.strip() for h in (reader.fieldnames or []) if h and h.strip()]
                self.rows=[{str(k).strip():(v or "").strip() for k,v in r.items() if k is not None} for r in reader]
            if not self.headers or not self.rows: raise ValueError("CSV فارغ أو لا يحتوي على عناوين وأسطُر.")
            self.csv_path=Path(path); self.mapping={k:"" for k,_ in FIELDS}
            self.csv_label.config(text=f"{self.csv_path.name} — {len(self.rows)} صف، {len(self.headers)} عمود")
            self.guess_mapping(); self.mapping_window()
        except Exception as e: messagebox.showerror("خطأ CSV",str(e))

    def guess_mapping(self):
        aliases={
          "page_name":["page_name","page name","name","title","اسم الصفحة","الاسم"],
          "username":["username","user name","handle","اسم المستخدم"],
          "category":["category","type","التصنيف","الفئة"],
          "description":["description","full description","وصف","الوصف","article"],
          "bio":["bio","short description","short bio","نبذة","نبذة قصيرة"],
          "website":["website","url","site","الموقع"],"email":["email","البريد"],
          "phone":["phone","telephone","الهاتف"],"city":["city","location","المدينة"],
          "language":["language","lang","اللغة"]}
        lower={h.lower():h for h in self.headers}
        for key,names in aliases.items():
            for name in names:
                if name.lower() in lower: self.mapping[key]=lower[name.lower()]; break

    def mapping_window(self):
        if not self.headers:
            messagebox.showinfo("CSV","حمّل ملف CSV أولاً."); return
        win=tk.Toplevel(self.root); win.title("اختيار أعمدة CSV"); win.geometry("600x610"); win.transient(self.root)
        ttk.Label(win,text="اختَر العمود المناسب لكل معلومة. الاختيار اختياري ما عدا اسم الصفحة.",wraplength=560).pack(anchor="w",padx=12,pady=10)
        vars_={}; frame=ttk.Frame(win,padding=10); frame.pack(fill="both",expand=True)
        for i,(key,label) in enumerate(FIELDS):
            ttk.Label(frame,text=label).grid(row=i,column=0,sticky="w",padx=5,pady=5)
            v=tk.StringVar(value=self.mapping.get(key) or "(بدون ربط)")
            ttk.Combobox(frame,textvariable=v,values=["(بدون ربط)"]+self.headers,state="readonly",width=34).grid(row=i,column=1,sticky="ew",padx=5,pady=5)
            vars_[key]=v
        frame.columnconfigure(1,weight=1)
        def apply():
            self.mapping={k:(v.get() if v.get()!="(بدون ربط)" else "") for k,v in vars_.items()}
            if not self.mapping.get("page_name"):
                messagebox.showwarning("اختيار ضروري","خاصك تربط خانة اسم الصفحة بعمود من CSV.",parent=win); return
            self.index=0; self.show_row(); win.destroy()
            self.status.set("تم ربط الأعمدة. تقدر تتنقل أو تجهز جميع الصفحات.")
        ttk.Button(win,text="تطبيق الاختيارات",command=apply).pack(pady=12)

    def mapped(self,row):
        return {k:(row.get(self.mapping.get(k,""),"").strip() if self.mapping.get(k) else "") for k,_ in FIELDS}

    def show_row(self):
        if not self.rows:return
        data=self.mapped(self.rows[self.index])
        for k,_ in FIELDS:
            self.entries[k].delete(0,"end"); self.entries[k].insert(0,data.get(k,""))
        self.nav_label.config(text=f"الصفحة {self.index+1} من {len(self.rows)}")

    def next(self):
        if self.rows and self.index<len(self.rows)-1:self.index+=1;self.show_row()
    def prev(self):
        if self.rows and self.index>0:self.index-=1;self.show_row()

    def pick_profile(self):
        p=filedialog.askopenfilename(title="اختيار Profile",filetypes=[("Images","*.png *.jpg *.jpeg *.webp")])
        if p:self.profile=Path(p);self.profile_label.config(text=f"Profile: {self.profile.name}")
    def pick_cover(self):
        p=filedialog.askopenfilename(title="اختيار Cover",filetypes=[("Images","*.png *.jpg *.jpeg *.webp")])
        if p:self.cover=Path(p);self.cover_label.config(text=f"Cover: {self.cover.name}")

    def save_data(self,data):
        name=data.get("page_name","").strip()
        if not name:raise ValueError("اسم الصفحة فارغ")
        folder=OUTPUT_DIR/slugify(name);folder.mkdir(parents=True,exist_ok=True)
        (folder/"page_info.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        text=(f"اسم الصفحة: {name}\nاسم المستخدم المقترح: {data.get('username','')}\nالتصنيف: {data.get('category','')}\n\nالوصف:\n{data.get('description','')}\n\nالنبذة:\n{data.get('bio','')}\nالموقع: {data.get('website','')}\nالبريد: {data.get('email','')}\nالهاتف: {data.get('phone','')}\nالمدينة: {data.get('city','')}\nاللغة: {data.get('language','')}\n")
        (folder/"about.txt").write_text(text,encoding="utf-8")
        if self.profile and self.profile.exists():shutil.copy2(self.profile,folder/("profile"+self.profile.suffix.lower()))
        if self.cover and self.cover.exists():shutil.copy2(self.cover,folder/("cover"+self.cover.suffix.lower()))

    def save_current(self):
        try:
            data={k:e.get().strip() for k,e in self.entries.items()};self.save_data(data)
            self.status.set("تم تجهيز الصفحة: "+data["page_name"])
            messagebox.showinfo("تم","تم تجهيز الصفحة داخل prepared_pages.")
        except Exception as e:messagebox.showerror("تعذر الحفظ",str(e))

    def save_all(self):
        if not self.rows or not self.mapping.get("page_name"):
            messagebox.showinfo("CSV","حمّل CSV واربط عمود اسم الصفحة أولاً.");return
        done,errors=0,[]
        for i,row in enumerate(self.rows,1):
            try:self.save_data(self.mapped(row));done+=1
            except Exception as e:errors.append(f"السطر {i+1}: {e}")
        self.status.set(f"اكتمل التجهيز: {done} صفحة من أصل {len(self.rows)}.")
        msg=f"تم تجهيز {done} صفحة من أصل {len(self.rows)}."
        if errors:msg+="\n\nالأخطاء:\n"+"\n".join(errors[:12])
        messagebox.showinfo("نتيجة التجهيز",msg)

    def open_output(self):
        OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
        try:os.startfile(str(OUTPUT_DIR))
        except Exception:messagebox.showinfo("مجلد النتائج",str(OUTPUT_DIR))

if __name__=="__main__":
    root=tk.Tk()
    try:ttk.Style().theme_use("clam")
    except Exception:pass
    App(root);root.mainloop()
