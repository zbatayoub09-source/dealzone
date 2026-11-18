# -*- coding: utf-8 -*-
"""Facebook Page CSV Publisher - independent DealZone tool."""
import csv, json, re, threading, urllib.request, urllib.parse, urllib.error, uuid, mimetypes
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

HERE = Path(__file__).resolve().parent
GRAPH = "https://graph.facebook.com/v27.0"
GEMINI_MODEL = "gemini-2.5-flash"
SETTINGS = HERE / "local_settings.json"
ALIASES = {
    "message": ["post message", "message", "caption", "النص", "المنشور", "محتوى المنشور"],
    "image": ["image url", "image_url", "image", "image path", "image_path", "photo", "رابط الصورة", "الصورة", "مسار الصورة"],
    "comment": ["comment", "first comment", "comment text", "التعليق", "تعليق"],
}

def http_json(url, data=None, headers=None, timeout=90):
    req = urllib.request.Request(url, data=data, headers=headers or {},
                                 method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            obj = json.loads(raw)
            err = obj.get("error", {})
            detail = err.get("message", raw)
            if err.get("error_user_title"):
                detail += " | " + err["error_user_title"]
        except Exception:
            detail = raw
        raise RuntimeError("Facebook/API HTTP " + str(exc.code) + ": " + detail[:1200])

def post_form(url, fields, headers=None):
    body = urllib.parse.urlencode(fields).encode("utf-8")
    return http_json(url, body, {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})})

def post_local_photo(page_id, token, path, message):
    path = Path(path)
    if not path.is_file():
        raise RuntimeError("الصورة المحلية غير موجودة: " + str(path))
    boundary = "----DealZone" + uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    chunks = []
    def field(name, value):
        chunks.append(("--" + boundary + "\r\n").encode())
        chunks.append(('Content-Disposition: form-data; name="' + name + '"\r\n\r\n').encode())
        chunks.append(str(value).encode("utf-8") + b"\r\n")
    field("access_token", token)
    field("message", message)
    chunks.append(("--" + boundary + "\r\n").encode())
    chunks.append(('Content-Disposition: form-data; name="source"; filename="' + path.name.replace('"', '') + '"\r\n').encode())
    chunks.append(("Content-Type: " + mime + "\r\n\r\n").encode())
    with path.open("rb") as stream:
        chunks.append(stream.read())
    chunks.append(b"\r\n--" + boundary + b"--\r\n")
    data = b"".join(chunks)
    return http_json(GRAPH + "/" + page_id + "/photos", data,
                     {"Content-Type": "multipart/form-data; boundary=" + boundary})

def norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip().casefold())

def get_col(headers, aliases):
    lookup = {norm(h): h for h in headers if h}
    for alias in aliases:
        if norm(alias) in lookup:
            return lookup[norm(alias)]
    return None

def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        if not headers:
            raise ValueError("CSV فارغ أو ما فيهش عناوين الأعمدة.")
        message_col = get_col(headers, ALIASES["message"])
        image_col = get_col(headers, ALIASES["image"])
        comment_col = get_col(headers, ALIASES["comment"])
        if not message_col:
            raise ValueError("خاص CSV يحتوي عمود Post Message أو Message.")
        rows = list(reader)
    if not rows:
        raise ValueError("CSV ما فيه حتى سطر.")
    return rows, message_col, image_col, comment_col

class App:
    def __init__(self, root):
        self.root = root
        root.title("DealZone | Facebook CSV Publisher")
        root.geometry("900x720")
        root.minsize(780, 650)
        self.user_token = tk.StringVar()
        self.csv_path = None
        self.pages = []
        self.busy = False
        self.status = tk.StringVar(value="1) دخل Facebook User Access Token  2) جلب الصفحات  3) اختار CSV")
        self._build()

    def _build(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Facebook CSV Publisher", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(main, text="نشر الصور أو الروابط + النص + التعليق، في صفحة واحدة أو عدة صفحات.").pack(anchor="w", pady=(2, 12))

        api_box = ttk.LabelFrame(main, text="Facebook API — هنا تدخل Token ديالك", padding=10)
        api_box.pack(fill="x", pady=5)
        ttk.Label(api_box, text="Facebook User Access Token").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(api_box, textvariable=self.user_token, show="*", width=75).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(api_box, text="اختبار Token وجلب الصفحات", command=self.load_pages).grid(row=0, column=2, padx=4)
        api_box.columnconfigure(1, weight=1)
        ttk.Label(api_box, text="دخل User Token هنا فقط. البرنامج ما كيحفظوش وما ترسلوش لأي واحد.",
                  foreground="#9a4b00").grid(row=1, column=0, columnspan=3, sticky="w", pady=4)

        pages_box = ttk.LabelFrame(main, text="صفحات Facebook — تقدر تختار أكثر من صفحة (Ctrl أو Shift)", padding=8)
        pages_box.pack(fill="both", expand=True, pady=7)
        self.page_list = tk.Listbox(pages_box, selectmode=tk.EXTENDED, height=7, exportselection=False)
        self.page_list.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(pages_box, orient="vertical", command=self.page_list.yview)
        scroll.pack(side="right", fill="y")
        self.page_list.configure(yscrollcommand=scroll.set)
        page_buttons = ttk.Frame(main)
        page_buttons.pack(fill="x")
        ttk.Button(page_buttons, text="اختيار جميع الصفحات", command=self.select_all).pack(side="left")
        ttk.Button(page_buttons, text="إلغاء الاختيار", command=lambda: self.page_list.selection_clear(0, "end")).pack(side="left", padx=6)

        csv_box = ttk.LabelFrame(main, text="ملف CSV", padding=10)
        csv_box.pack(fill="x", pady=7)
        row = ttk.Frame(csv_box); row.pack(fill="x")
        ttk.Button(row, text="اختيار CSV", command=self.pick_csv).pack(side="left")
        self.file_label = ttk.Label(row, text="مازال ما اخترتي حتى CSV")
        self.file_label.pack(side="left", padx=10)
        ttk.Label(csv_box, text="الأعمدة: Post Message (إجباري)، Image URL أو Image Path (اختياري)، Comment (اختياري).").pack(anchor="w", pady=(7, 0))

        actions = ttk.Frame(main); actions.pack(fill="x", pady=8)
        self.publish_btn = ttk.Button(actions, text="START PUBLISHING", command=self.start_publish)
        self.publish_btn.pack(side="left")
        ttk.Button(actions, text="فتح مجلد البرنامج", command=lambda: __import__("os").startfile(HERE)).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(main, maximum=100)
        self.progress.pack(fill="x", pady=5)
        ttk.Label(main, textvariable=self.status, wraplength=850).pack(anchor="w", pady=5)
        ttk.Label(main, text="النتائج كتتحفظ في ملف جديد بجانب CSV باسم *_facebook_results.csv. ما كاين حتى تعديل على CSV الأصلي.",
                  foreground="#555", wraplength=850).pack(anchor="w", pady=4)
        ttk.Label(main, text="ملاحظة: خاص صلاحيات pages_show_list و pages_manage_posts و pages_read_engagement ومهمة CREATE_CONTENT. النشر الفعلي يتطلب موافقة Meta وصلاحيات الصفحة.",
                  foreground="#9a4b00", wraplength=850).pack(anchor="w", pady=5)

    def pick_csv(self):
        name = filedialog.askopenfilename(title="اختار ملف CSV", filetypes=[("CSV files", "*.csv")])
        if name:
            try:
                rows, _, _, _ = read_csv(name)
                self.csv_path = Path(name)
                self.file_label.config(text=self.csv_path.name + " (" + str(len(rows)) + " سطر)")
                self.status.set("CSV صالح. اختار الصفحات واضغط START PUBLISHING.")
            except Exception as exc:
                messagebox.showerror("CSV", str(exc))

    def load_pages(self):
        token = self.user_token.get().strip()
        if not token:
            messagebox.showwarning("Facebook API", "لسق Facebook User Access Token في الخانة اللي فوق.")
            return
        self.status.set("كنختبرو Token وكنجيبو الصفحات...")
        threading.Thread(target=self._pages_worker, args=(token,), daemon=True).start()

    def _pages_worker(self, token):
        try:
            url = GRAPH + "/me/accounts?" + urllib.parse.urlencode({
                "fields": "id,name,access_token,tasks", "limit": 100, "access_token": token
            })
            pages = []
            while url:
                data = http_json(url)
                pages.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
            if not pages:
                raise RuntimeError("Token خدام ولكن ما رجع حتى Page. راجع pages_show_list واختيار الحساب والمهام.")
            valid = [p for p in pages if p.get("id") and p.get("access_token")]
            if not valid:
                raise RuntimeError("ما رجعوش Page Access Tokens. راجع صلاحيات التطبيق والحساب.")
            self.pages = valid
            def done():
                self.page_list.delete(0, "end")
                for p in self.pages:
                    self.page_list.insert("end", p.get("name", "Facebook Page") + " | " + str(p["id"]))
                self.page_list.selection_set(0, "end")
                self.status.set("نجح الاتصال: لقينا " + str(len(self.pages)) + " صفحة. اختار الصفحات المطلوبة.")
            self.root.after(0, done)
        except Exception as exc:
            self.root.after(0, lambda e=str(exc): (self.status.set("فشل الاتصال."), messagebox.showerror("Facebook API", e)))

    def select_all(self):
        if self.pages:
            self.page_list.selection_set(0, "end")

    def start_publish(self):
        if self.busy:
            return
        indices = list(self.page_list.curselection())
        if not indices:
            messagebox.showwarning("الصفحات", "جبد الصفحات واختار صفحة واحدة على الأقل.")
            return
        if not self.csv_path or not self.csv_path.is_file():
            messagebox.showwarning("CSV", "اختار ملف CSV صحيح.")
            return
        try:
            rows, msg_col, image_col, comment_col = read_csv(self.csv_path)
        except Exception as exc:
            messagebox.showerror("CSV", str(exc)); return
        selected = [self.pages[i] for i in indices]
        total = len(rows) * len(selected)
        if not messagebox.askyesno("تأكيد النشر",
                "غادي يتنشر " + str(len(rows)) + " منشور فـ " + str(len(selected)) +
                " صفحة (المجموع حتى " + str(total) + "). واش نبدأ؟"):
            return
        self.busy = True
        self.publish_btn.config(state="disabled")
        self.progress["value"] = 0
        threading.Thread(target=self._publish_worker,
            args=(rows, msg_col, image_col, comment_col, selected), daemon=True).start()

    def _publish_worker(self, rows, msg_col, image_col, comment_col, pages):
        results = []
        total = max(1, len(rows) * len(pages))
        completed = 0
        for page in pages:
            pid = str(page["id"])
            pname = page.get("name", pid)
            token = page["access_token"]
            for row_no, row in enumerate(rows, 1):
                message = str(row.get(msg_col, "") or "").strip()
                image = str(row.get(image_col, "") or "").strip() if image_col else ""
                comment = str(row.get(comment_col, "") or "").strip() if comment_col else ""
                record = {"Page Name": pname, "Page ID": pid, "CSV Row": row_no,
                          "Post ID": "", "Status": "", "Error": ""}
                try:
                    if not message and not image:
                        raise RuntimeError("السطر فارغ: لا يوجد نص أو صورة.")
                    if image:
                        parsed = urllib.parse.urlparse(image)
                        if parsed.scheme in ("http", "https"):
                            response = post_form(GRAPH + "/" + pid + "/photos",
                                {"url": image, "caption": message, "access_token": token})
                        else:
                            local = Path(image)
                            if not local.is_absolute():
                                local = self.csv_path.parent / local
                            response = post_local_photo(pid, token, local, message)
                        post_id = response.get("post_id") or response.get("id")
                    else:
                        response = post_form(GRAPH + "/" + pid + "/feed",
                            {"message": message, "access_token": token})
                        post_id = response.get("id")
                    if not post_id:
                        raise RuntimeError("Meta ما رجعاتش Post ID: " + json.dumps(response, ensure_ascii=False)[:500])
                    record["Post ID"] = str(post_id)
                    if comment:
                        comment_response = post_form(GRAPH + "/" + str(post_id) + "/comments",
                            {"message": comment, "access_token": token})
                        record["Comment ID"] = str(comment_response.get("id", ""))
                    record["Status"] = "PUBLISHED"
                except Exception as exc:
                    record["Status"] = "FAILED"
                    record["Error"] = str(exc)
                results.append(record)
                completed += 1
                self.root.after(0, lambda v=completed/total*100: self.progress.configure(value=v))
        out = self.csv_path.with_name(self.csv_path.stem + "_facebook_results.csv")
        fields = ["Page Name", "Page ID", "CSV Row", "Post ID", "Comment ID", "Status", "Error"]
        try:
            with out.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for item in results:
                    writer.writerow({k: item.get(k, "") for k in fields})
            save_error = ""
        except Exception as exc:
            save_error = str(exc)
        ok = sum(1 for x in results if x["Status"] == "PUBLISHED")
        failed = len(results) - ok
        def finish():
            self.busy = False
            self.publish_btn.config(state="normal")
            self.status.set("سالينا. ناجح: " + str(ok) + " | فاشل: " + str(failed))
            msg = "نشر ناجح: " + str(ok) + "\nفشل: " + str(failed)
            if not save_error:
                msg += "\nملف النتائج: " + str(out)
            else:
                msg += "\nتعذر حفظ النتائج: " + save_error
            messagebox.showinfo("نتيجة النشر", msg)
        self.root.after(0, finish)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    App(root)
    root.mainloop()
