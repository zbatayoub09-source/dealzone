import csv, json, re, urllib.request, urllib.error, webbrowser
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

BASE=Path(__file__).resolve().parent
OUT=BASE/'output'; DATA=BASE/'data'; USED=DATA/'used_names.json'
FIELDS=['PageName','Category','Description','UsernameSuggestion','ProfileImagePrompt','CoverImagePrompt','Website','Status','PageURL','CreatedAt']
MODEL='gemini-2.5-flash'

ALIASES={
 'pagename':['pagename','page name','اسم الصفحة','اسم الصفحه','name','title'],
 'category':['category','التصنيف','الفئة','الفئه'],
 'description':['description','bio','about','الوصف','نبذة','نبذه'],
 'usernamesuggestion':['usernamesuggestion','username','اسم المستخدم'],
 'profileimageprompt':['profileimageprompt','profile image prompt','profile prompt','وصف صورة البروفايل','صورة البروفايل'],
 'coverimageprompt':['coverimageprompt','cover image prompt','cover prompt','وصف صورة الغلاف','صورة الغلاف'],
 'website':['website','site','الموقع'],
 'status':['status','الحالة','الحاله'],
 'pageurl':['pageurl','page url','رابط الصفحة','رابط الصفحه'],
 'createdat':['createdat','created at','تاريخ الإنشاء','تاريخ الانشاء']
}

def setup():
    OUT.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)
    if not USED.exists(): USED.write_text('[]',encoding='utf-8')

def generate(key,niche,count,language):
    prompt=('Generate exactly '+str(count)+' distinct Facebook business Page concepts for niche: '+niche+'. Language: '+language+'. Return ONLY a JSON array of objects with keys: '+', '.join(FIELDS[:7])+'. Use original brand names, concise descriptions, and detailed prompts for a square profile image and wide cover image. No famous trademarks or fake claims.')
    body={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.85,'responseMimeType':'application/json'}}
    url='https://generativelanguage.googleapis.com/v1beta/models/'+MODEL+':generateContent?key='+key
    req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=90) as res: data=json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError('Gemini API '+str(e.code)+': '+e.read().decode(errors='replace')[:600])
    raw=''.join(p.get('text','') for p in data['candidates'][0]['content']['parts'])
    raw=re.sub(r'^\x60\x60\x60(?:json)?\s*|\s*\x60\x60\x60$','',raw.strip())
    items=json.loads(raw[raw.find('['):raw.rfind(']')+1])
    used=set(json.loads(USED.read_text(encoding='utf-8'))); rows=[]
    for x in items:
        name=str(x.get('PageName','')).strip()
        if not name or name.casefold() in used: continue
        row={k:str(x.get(k,'') or '') for k in FIELDS}
        row.update(Status='Pending',PageURL='',CreatedAt=''); rows.append(row); used.add(name.casefold())
    if not rows: raise RuntimeError('لم يتم العثور على أسماء جديدة غير مكررة. جرّب مجالاً آخر.')
    USED.write_text(json.dumps(sorted(used),ensure_ascii=False,indent=2),encoding='utf-8')
    path=OUT/('pages_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.csv')
    save_csv(path,rows)
    return path,rows

def save_csv(path,rows):
    with Path(path).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

def load_csv(path):
    rows=[]
    with Path(path).open('r',newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames: raise ValueError('ملف CSV فارغ أو بدون عناوين أعمدة.')
        mapping={}
        for field in reader.fieldnames:
            key=str(field).strip().casefold()
            for canonical,aliases in ALIASES.items():
                if key in [a.casefold() for a in aliases]: mapping[field]=next(x for x in FIELDS if x.casefold()==canonical); break
        if 'PageName' not in mapping.values():
            raise ValueError('خاص CSV يحتوي على عمود PageName أو اسم الصفحة.')
        for source in reader:
            row={k:'' for k in FIELDS}
            for old,new in mapping.items(): row[new]=str(source.get(old,'') or '').strip()
            if row['PageName']:
                row['Status']=row['Status'] or 'Pending'
                rows.append(row)
    if not rows: raise ValueError('ما لقيتش صفحات داخل CSV.')
    return rows

class App:
 def __init__(self,root):
    self.root=root; root.title('منشئ صفحات Facebook - DealZone'); root.geometry('1080x720'); self.rows=[]; self.path=None
    box=ttk.Frame(root,padding=14); box.pack(fill='both',expand=True)
    ttk.Label(box,text='منشئ صفحات Facebook',font=('Segoe UI',18,'bold')).pack(anchor='w')
    template=BASE/'pages_template.csv'
    if template.exists():
        try:
            self.rows=load_csv(template); self.path=template
        except Exception:
            pass
    ttk.Label(box,text='اختار CSV ديالك، اختار الصفحة، وخدم مباشرة. ما محتاجش Gemini باش تستعمل CSV موجود.',font=('Segoe UI',10)).pack(anchor='w',pady=(3,12))
    bar=ttk.Frame(box); bar.pack(fill='x',pady=4)
    ttk.Button(bar,text='📂 اختيار ملف CSV',command=self.open_csv).pack(side='left')
    ttk.Button(bar,text='فتح Facebook لإنشاء الصفحة',command=lambda:webbrowser.open('https://www.facebook.com/pages/create/')).pack(side='left',padx=8)
    ttk.Button(bar,text='توليد CSV جديد بـ Gemini (اختياري)',command=self.show_generator).pack(side='left')
    self.status=tk.StringVar(value='مرحبا! اختار ملف CSV للبدء.')
    ttk.Label(box,textvariable=self.status).pack(anchor='w',pady=8)
    self.tree=ttk.Treeview(box,columns=('name','category','status','url'),show='headings',height=12)
    for c,t,w in [('name','اسم الصفحة',260),('category','التصنيف',180),('status','الحالة',100),('url','رابط الصفحة',420)]: self.tree.heading(c,text=t); self.tree.column(c,width=w)
    self.tree.pack(fill='both',expand=True); self.tree.bind('<<TreeviewSelect>>',self.show)
    self.details=tk.Text(box,height=10,wrap='word'); self.details.pack(fill='x',pady=8)
    actions=ttk.Frame(box); actions.pack(fill='x')
    ttk.Button(actions,text='نسخ الاسم',command=lambda:self.copy_field('PageName')).pack(side='left')
    ttk.Button(actions,text='نسخ الوصف',command=lambda:self.copy_field('Description')).pack(side='left',padx=6)
    ttk.Button(actions,text='نسخ وصف صورة البروفايل',command=lambda:self.copy_field('ProfileImagePrompt')).pack(side='left')
    ttk.Button(actions,text='نسخ وصف صورة الغلاف',command=lambda:self.copy_field('CoverImagePrompt')).pack(side='left',padx=6)
    row=ttk.Frame(box); row.pack(fill='x',pady=8)
    ttk.Label(row,text='رابط الصفحة بعد الإنشاء:').pack(side='left')
    self.url=tk.StringVar(); ttk.Entry(row,textvariable=self.url).pack(side='left',fill='x',expand=True,padx=8)
    ttk.Button(row,text='حفظ: تم الإنشاء',command=self.mark).pack(side='left')
    ttk.Label(box,text='ملاحظة: إنشاء الصفحة يتم من حسابك على Facebook. البرنامج لا يطلب كلمة السر ولا ينشئ الصفحة وحده.',foreground='#555').pack(anchor='w',pady=4)
    if self.rows:
        self.refresh()
        self.status.set('وجدنا CSV جاهزاً فيه '+str(len(self.rows))+' صفحات. اختار صفحة وابدأ.')

 def open_csv(self):
    name=filedialog.askopenfilename(title='اختار ملف CSV',filetypes=[('CSV files','*.csv'),('All files','*.*')])
    if not name:return
    try:
        self.rows=load_csv(name); self.path=Path(name); self.refresh()
        self.status.set('تم تحميل '+str(len(self.rows))+' صفحة من: '+str(self.path))
    except Exception as e: messagebox.showerror('خطأ في CSV',str(e))

 def show_generator(self):
    win=tk.Toplevel(self.root); win.title('توليد CSV جديد'); win.geometry('620x230'); win.transient(self.root)
    frame=ttk.Frame(win,padding=14); frame.pack(fill='both',expand=True)
    key=tk.StringVar(); niche=tk.StringVar(value='Online shopping and useful products'); count=tk.StringVar(value='5'); lang=tk.StringVar(value='Arabic')
    ttk.Label(frame,text='Gemini API Key').grid(row=0,column=0,sticky='w',pady=5); ttk.Entry(frame,textvariable=key,show='*',width=48).grid(row=0,column=1,sticky='ew')
    ttk.Label(frame,text='المجال').grid(row=1,column=0,sticky='w',pady=5); ttk.Entry(frame,textvariable=niche).grid(row=1,column=1,sticky='ew')
    ttk.Label(frame,text='العدد').grid(row=2,column=0,sticky='w',pady=5); ttk.Spinbox(frame,from_=1,to=20,textvariable=count,width=6).grid(row=2,column=1,sticky='w')
    ttk.Label(frame,text='اللغة').grid(row=3,column=0,sticky='w',pady=5); ttk.Combobox(frame,textvariable=lang,values=['Arabic','English','French'],state='readonly',width=12).grid(row=3,column=1,sticky='w')
    frame.columnconfigure(1,weight=1)
    def run():
        try:
            if not key.get().strip(): raise ValueError('دخل Gemini API Key.')
            n=int(count.get())
            if n<1 or n>20: raise ValueError('العدد خاصو يكون بين 1 و20.')
            self.status.set('كنوجد CSV...'); win.update_idletasks()
            self.path,self.rows=generate(key.get().strip(),niche.get().strip(),n,lang.get())
            self.refresh(); self.status.set('توجد CSV وتحمل مباشرة: '+str(self.path)); win.destroy()
        except Exception as e: messagebox.showerror('خطأ',str(e))
    ttk.Button(frame,text='توليد وتحميل CSV',command=run).grid(row=4,column=1,sticky='e',pady=12)

 def selected(self):
    sel=self.tree.selection()
    if not sel: messagebox.showinfo('اختيار الصفحة','اختار صفحة من اللائحة أولا.'); return None
    return self.rows[int(sel[0])]

 def copy_field(self,field):
    r=self.selected()
    if r is None:return
    value=r.get(field,'')
    self.root.clipboard_clear(); self.root.clipboard_append(value); self.status.set('تنسخ النص. دابا لصقو فـ Facebook.')

 def refresh(self):
    self.tree.delete(*self.tree.get_children())
    for i,r in enumerate(self.rows): self.tree.insert('','end',iid=str(i),values=(r['PageName'],r['Category'],r['Status'],r['PageURL']))
    if self.rows:self.tree.selection_set('0'); self.show()

 def show(self,event=None):
    sel=self.tree.selection()
    if not sel:return
    r=self.rows[int(sel[0])]; self.url.set(r.get('PageURL',''))
    self.details.delete('1.0','end')
    self.details.insert('1.0','اسم الصفحة: '+r['PageName']+'\nالتصنيف: '+r['Category']+'\nالوصف: '+r['Description']+'\nاسم المستخدم المقترح: '+r['UsernameSuggestion']+'\n\nوصف صورة البروفايل:\n'+r['ProfileImagePrompt']+'\n\nوصف صورة الغلاف:\n'+r['CoverImagePrompt'])

 def mark(self):
    r=self.selected()
    if r is None:return
    url=self.url.get().strip()
    if not url.startswith(('https://','http://')): messagebox.showwarning('الرابط','دخل رابط صفحة Facebook الصحيح.'); return
    i=self.rows.index(r); r.update(Status='Created',PageURL=url,CreatedAt=datetime.now().isoformat(timespec='minutes'))
    try: save_csv(self.path,self.rows)
    except Exception as e: messagebox.showerror('الحفظ','ما قدرتش نحفظ CSV: '+str(e)); return
    self.refresh(); self.tree.selection_set(str(i)); self.status.set('تسجلات الصفحة وتحدّث نفس ملف CSV.')

if __name__=='__main__':
 setup(); root=tk.Tk(); App(root); root.mainloop()
