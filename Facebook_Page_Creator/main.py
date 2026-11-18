import csv, json, re, urllib.request, urllib.error, webbrowser
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

BASE=Path(__file__).resolve().parent
OUT=BASE/'output'; DATA=BASE/'data'; USED=DATA/'used_names.json'
FIELDS=['PageName','Category','Description','UsernameSuggestion','ProfileImagePrompt','CoverImagePrompt','Website','Status','PageURL','CreatedAt']
MODEL='gemini-2.5-flash'

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
    raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip())
    items=json.loads(raw[raw.find('['):raw.rfind(']')+1])
    used=set(json.loads(USED.read_text(encoding='utf-8'))); rows=[]
    for x in items:
        name=str(x.get('PageName','')).strip()
        if not name or name.casefold() in used: continue
        row={k:str(x.get(k,'') or '') for k in FIELDS}
        row.update(Status='Pending',PageURL='',CreatedAt=''); rows.append(row); used.add(name.casefold())
    if not rows: raise RuntimeError('No new unique names returned. Try another niche.')
    USED.write_text(json.dumps(sorted(used),ensure_ascii=False,indent=2),encoding='utf-8')
    path=OUT/('pages_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.csv')
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    return path,rows

class App:
 def __init__(self,root):
    self.root=root; root.title('Facebook Page Creator | DealZone'); root.geometry('1050x700'); self.rows=[]; self.path=None
    box=ttk.Frame(root,padding=14); box.pack(fill='both',expand=True)
    ttk.Label(box,text='Facebook Page Creator',font=('Segoe UI',18,'bold')).pack(anchor='w')
    form=ttk.Frame(box); form.pack(fill='x',pady=12)
    ttk.Label(form,text='Gemini API Key').grid(row=0,column=0,sticky='w'); self.key=tk.StringVar(); ttk.Entry(form,textvariable=self.key,show='*',width=52).grid(row=0,column=1,sticky='ew',padx=6)
    ttk.Label(form,text='Count').grid(row=0,column=2); self.count=tk.StringVar(value='5'); ttk.Spinbox(form,from_=1,to=20,textvariable=self.count,width=5).grid(row=0,column=3)
    ttk.Label(form,text='Niche').grid(row=1,column=0,sticky='w',pady=8); self.niche=tk.StringVar(value='Online shopping and useful products'); ttk.Entry(form,textvariable=self.niche).grid(row=1,column=1,sticky='ew',padx=6,pady=8)
    ttk.Label(form,text='Language').grid(row=1,column=2); self.lang=tk.StringVar(value='English'); ttk.Combobox(form,textvariable=self.lang,values=['English','Arabic','French'],state='readonly',width=10).grid(row=1,column=3)
    form.columnconfigure(1,weight=1)
    bar=ttk.Frame(box); bar.pack(fill='x')
    ttk.Button(bar,text='Generate CSV',command=self.make).pack(side='left'); ttk.Button(bar,text='Open Facebook Page Creation',command=lambda:webbrowser.open('https://www.facebook.com/pages/create/')).pack(side='left',padx=8)
    self.status=tk.StringVar(value='Ready'); ttk.Label(box,textvariable=self.status).pack(anchor='w',pady=8)
    self.tree=ttk.Treeview(box,columns=('name','category','status','url'),show='headings',height=12)
    for c,t,w in [('name','Page name',250),('category','Category',180),('status','Status',90),('url','Page URL',400)]: self.tree.heading(c,text=t); self.tree.column(c,width=w)
    self.tree.pack(fill='both',expand=True); self.tree.bind('<<TreeviewSelect>>',self.show)
    self.details=tk.Text(box,height=8,wrap='word'); self.details.pack(fill='x',pady=8)
    row=ttk.Frame(box); row.pack(fill='x'); ttk.Label(row,text='Created Page URL').pack(side='left'); self.url=tk.StringVar(); ttk.Entry(row,textvariable=self.url).pack(side='left',fill='x',expand=True,padx=8); ttk.Button(row,text='Mark Created',command=self.mark).pack(side='left')
    ttk.Label(box,text='You complete creation in Facebook yourself. This tool does not automate login or bypass Meta restrictions.').pack(anchor='w',pady=8)
 def make(self):
    try:
        if not self.key.get().strip(): raise ValueError('Enter Gemini API key.')
        n=int(self.count.get())
        if n<1 or n>20: raise ValueError('Count must be 1–20.')
        self.status.set('Generating with Gemini...'); self.root.update_idletasks()
        self.path,self.rows=generate(self.key.get().strip(),self.niche.get().strip(),n,self.lang.get()); self.refresh(); self.status.set('CSV saved: '+str(self.path))
    except Exception as e: self.status.set('Generation failed'); messagebox.showerror('Error',str(e))
 def refresh(self):
    self.tree.delete(*self.tree.get_children())
    for i,r in enumerate(self.rows): self.tree.insert('','end',iid=str(i),values=(r['PageName'],r['Category'],r['Status'],r['PageURL']))
 def show(self,event=None):
    sel=self.tree.selection()
    if not sel:return
    r=self.rows[int(sel[0])]; self.url.set(r.get('PageURL',''))
    self.details.delete('1.0','end'); self.details.insert('1.0','NAME: '+r['PageName']+'\nCATEGORY: '+r['Category']+'\nDESCRIPTION: '+r['Description']+'\nUSERNAME: '+r['UsernameSuggestion']+'\n\nPROFILE IMAGE PROMPT:\n'+r['ProfileImagePrompt']+'\n\nCOVER IMAGE PROMPT:\n'+r['CoverImagePrompt'])
 def mark(self):
    sel=self.tree.selection(); url=self.url.get().strip()
    if not sel: messagebox.showinfo('Select','Select a page first.'); return
    if not url.startswith(('https://','http://')): messagebox.showwarning('URL','Enter the new Facebook Page URL.'); return
    i=int(sel[0]); self.rows[i].update(Status='Created',PageURL=url,CreatedAt=datetime.now().isoformat(timespec='minutes'))
    with self.path.open('w',newline='',encoding='utf-8-sig') as f: w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(self.rows)
    self.refresh(); self.tree.selection_set(str(i)); self.status.set('CSV updated.')

if __name__=='__main__':
 setup(); root=tk.Tk(); App(root); root.mainloop()
