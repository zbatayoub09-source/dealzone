import csv
import hashlib
import json
import queue
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
STATE_DIR = DATA_DIR / "state"
OUTPUT_DIR = APP_DIR / "output"
SETTINGS_FILE = DATA_DIR / "settings.json"
GRAPH_VERSION = "v26.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
TIMEOUT = 45


def load_settings():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("pages", []), list):
                return value
        except Exception:
            pass
    return {"pages": []}


def save_settings(settings):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def graph_request(method, path, params):
    url = f"{GRAPH_BASE}/{path.lstrip('/')}"
    try:
        response = requests.request(method, url, params=params if method == "GET" else None,
                                    data=params if method == "POST" else None, timeout=TIMEOUT)
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError(f"Meta رجعات جواب غير مفهوم (HTTP {response.status_code}).")
        if response.status_code >= 400 or payload.get("error"):
            error = payload.get("error", {})
            code = error.get("code", "")
            subcode = error.get("error_subcode", "")
            message = error.get("message", str(payload))
            raise RuntimeError(f"Meta API {code}/{subcode}: {message}")
        return payload
    except requests.RequestException as exc:
        raise RuntimeError(f"تعذر الاتصال بـ Meta: {exc}")


def fetch_managed_pages(user_token):
    pages = []
    url = f"{GRAPH_BASE}/me/accounts"
    params = {"fields": "id,name,access_token,tasks", "limit": 100, "access_token": user_token}
    while url:
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"تعذر جلب الصفحات: {exc}")
        if response.status_code >= 400 or payload.get("error"):
            error = payload.get("error", {})
            raise RuntimeError(f"Meta API {error.get('code','')}: {error.get('message', payload)}")
        pages.extend(payload.get("data", []))
        url = payload.get("paging", {}).get("next")
        params = None
    return [p for p in pages if p.get("id") and p.get("access_token")]


def extract_post_id(link):
    link = (link or "").strip()
    if re.fullmatch(r"\d+_\d+|\d+", link):
        return link
    parsed = urlparse(link)
    host = (parsed.netloc or "").lower()
    if not (host == "facebook.com" or host.endswith(".facebook.com") or host == "fb.watch"):
        raise ValueError("رابط المنشور خاصو يكون من Facebook.")
    query = parse_qs(parsed.query)
    if query.get("story_fbid") and query.get("id"):
        return f'{query["id"][0]}_{query["story_fbid"][0]}'
    for pattern in (r"/posts/(\d+)", r"/videos/(\d+)", r"/permalink/(\d+)", r"/reel/(\d+)"):
        match = re.search(pattern, parsed.path)
        if match:
            return match.group(1)
    if query.get("fbid"):
        return query["fbid"][0]
    # Facebook short links and pfbid links do not expose a Graph object ID in a stable way.
    raise ValueError("ما قدرتش نستخرج ID من الرابط. استعمل رابط منشور فيه ID رقمي أو رابط فيه story_fbid و id.")


def read_csv_headers(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t")
        except csv.Error:
            dialect = csv.excel
        headers = next(csv.reader(handle, dialect), [])
    headers = [str(value).strip() for value in headers]
    if not headers or not any(headers):
        raise ValueError("CSV فارغ أو ما فيهش عناوين الأعمدة.")
    return headers


def load_csv(path, column_map):
    headers = read_csv_headers(path)
    if not all(column_map.get(key) in headers for key in ("Facebook_Link", "Comment")):
        raise ValueError("اختار عمود رابط المنشور وعمود التعليق.")
    photo_column = column_map.get("Photo_Link", "")
    if photo_column and photo_column not in headers:
        raise ValueError("عمود الصورة المختار غير موجود.")
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        rows = []
        for line_number, item in enumerate(reader, start=2):
            row = {
                "Photo_Link": str(item.get(photo_column, "") or "").strip() if photo_column else "",
                "Facebook_Link": str(item.get(column_map["Facebook_Link"], "") or "").strip(),
                "Comment": str(item.get(column_map["Comment"], "") or "").strip(),
            }
            if any(row.values()):
                rows.append((line_number, row))
    if not rows:
        raise ValueError("ما كاين حتى سطر فيه بيانات فـ CSV.")
    return rows

def make_row_key(csv_path, line_number, row):
    source = json.dumps([str(Path(csv_path).resolve()), line_number, row],
                        ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class PublisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook Comment Publisher | DealZone")
        self.root.geometry("940x720")
        self.root.minsize(800, 620)
        self.settings = load_settings()
        self.pages = self.settings.get("pages", [])
        self.csv_file = None
        saved_columns = self.settings.get("csv_columns", {})
        self.column_vars = {key: tk.StringVar(value=saved_columns.get(key, "")) for key in ("Photo_Link", "Facebook_Link", "Comment")}
        self.column_boxes = {}
        self.events = queue.Queue()
        self.worker = None
        self.stop_event = threading.Event()
        self.user_token = tk.StringVar()
        self.delay = tk.StringVar(value="30")
        self.status = tk.StringVar(value="جاهز.")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.build_ui()
        self.refresh_pages()
        self.root.after(150, self.poll_events)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Facebook Comment Publisher", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="تعليق على روابط منشورات Facebook باستعمال CSV وMeta API.",
                  foreground="#555").pack(anchor="w", pady=(2, 10))

        api_box = ttk.LabelFrame(outer, text="1) Facebook API — جلب الصفحات", padding=10)
        api_box.pack(fill="x", pady=(0, 9))
        ttk.Label(api_box, text="User Access Token:").pack(anchor="w")
        token_row = ttk.Frame(api_box)
        token_row.pack(fill="x", pady=4)
        ttk.Entry(token_row, textvariable=self.user_token, show="•").pack(side="left", fill="x", expand=True)
        self.fetch_button = ttk.Button(token_row, text="اختبار Token وجلب الصفحات", command=self.fetch_pages)
        self.fetch_button.pack(side="left", padx=(8, 0))
        ttk.Label(api_box, text="يمكنك كذلك إضافة Page ID وPage Access Token يدوياً. Token ما تشاركوش مع أي واحد.",
                  foreground="#8a4b08").pack(anchor="w")

        pages_box = ttk.LabelFrame(outer, text="2) اختار الصفحة أو الصفحات (Ctrl / Shift)", padding=10)
        pages_box.pack(fill="both", expand=True, pady=(0, 9))
        list_frame = ttk.Frame(pages_box)
        list_frame.pack(fill="both", expand=True)
        self.pages_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=7, exportselection=False)
        self.pages_list.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.pages_list.yview)
        scroll.pack(side="right", fill="y")
        self.pages_list.configure(yscrollcommand=scroll.set)
        buttons = ttk.Frame(pages_box)
        buttons.pack(fill="x", pady=(7, 0))
        ttk.Button(buttons, text="إضافة صفحة يدوياً", command=self.add_page).pack(side="left")
        ttk.Button(buttons, text="تعديل الصفحة", command=self.edit_page).pack(side="left", padx=6)
        ttk.Button(buttons, text="حذف الصفحة", command=self.delete_page).pack(side="left")

        csv_box = ttk.LabelFrame(outer, text="3) CSV", padding=10)
        csv_box.pack(fill="x", pady=(0, 9))
        row = ttk.Frame(csv_box)
        row.pack(fill="x")
        self.csv_label = ttk.Label(row, text="مازال ما اخترتيش CSV")
        self.csv_label.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="اختيار CSV", command=self.choose_csv).pack(side="right")
        mapping = ttk.Frame(csv_box)
        mapping.pack(fill="x", pady=(8, 0))
        for index, (key, label) in enumerate([
            ("Photo_Link", "عمود رابط الصورة (اختياري):"),
            ("Facebook_Link", "عمود رابط منشور Facebook:"),
            ("Comment", "عمود نص التعليق:"),
        ]):
            ttk.Label(mapping, text=label).grid(row=index, column=0, sticky="w", padx=(0, 10), pady=3)
            combo = ttk.Combobox(mapping, textvariable=self.column_vars[key], state="readonly", width=48)
            combo.grid(row=index, column=1, sticky="ew", pady=3)
            self.column_boxes[key] = combo
        mapping.columnconfigure(1, weight=1)
        ttk.Label(csv_box, text="اختار أسماء الأعمدة من CSV؛ ما ضروريش تكون بنفس الأسماء.",
                  foreground="#555").pack(anchor="w", pady=(6, 0))

        options = ttk.Frame(outer)
        options.pack(fill="x", pady=(0, 8))
        ttk.Label(options, text="الانتظار بين التعليقات (ثانية):").pack(side="left")
        ttk.Entry(options, textvariable=self.delay, width=7).pack(side="left", padx=8)
        ttk.Label(options, text="الافتراضي 30 ثانية.").pack(side="left")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 8))
        self.start_button = ttk.Button(actions, text="START COMMENTING", command=self.start)
        self.start_button.pack(side="left", fill="x", expand=True)
        self.stop_button = ttk.Button(actions, text="STOP", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))

        log_box = ttk.LabelFrame(outer, text="النتائج والأخطاء", padding=8)
        log_box.pack(fill="both", expand=True)
        self.log = tk.Text(log_box, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        ttk.Label(outer, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", pady=(8, 0))
        ttk.Label(outer, text="مهم: Meta قد تمنع التعليق على بعض منشورات الآخرين حسب الصلاحيات ونوع المنشور.",
                  foreground="#9b1c1c", wraplength=900).pack(anchor="w", pady=(7, 0))

    def log_line(self, text):
        def write():
            self.log.configure(state="normal")
            self.log.insert("end", text + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, write)

    def refresh_pages(self):
        self.pages_list.delete(0, "end")
        for page in self.pages:
            self.pages_list.insert("end", f'{page.get("name", "Page")}  |  ID: {page.get("page_id", "")}')

    def persist_pages(self):
        self.settings["pages"] = self.pages
        save_settings(self.settings)

    def fetch_pages(self):
        token = self.user_token.get().strip()
        if not token:
            messagebox.showwarning("Token ناقص", "دخل User Access Token الأول.")
            return
        self.fetch_button.configure(state="disabled")
        self.status.set("كنجيب الصفحات من Meta...")
        def task():
            try:
                found = fetch_managed_pages(token)
                self.events.put(("fetched_pages", found))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=task, daemon=True).start()

    def page_dialog(self, existing=None):
        original = existing or {}
        win = tk.Toplevel(self.root)
        win.title("إعدادات Facebook Page")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)
        fields = {}
        for index, (key, label, secret) in enumerate([
            ("name", "اسم الصفحة", False),
            ("page_id", "Page ID", False),
            ("access_token", "Page Access Token", True),
        ]):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", padx=(0, 12), pady=6)
            entry = ttk.Entry(frame, width=58, show="•" if secret else "")
            entry.grid(row=index, column=1, sticky="ew", pady=6)
            entry.insert(0, original.get(key, ""))
            fields[key] = entry
        ttk.Label(frame, text="Token كيتخزن محلياً فـ data/settings.json على هاد الحاسوب فقط. ما ترفعوش لـ GitHub.",
                  foreground="#9b1c1c", wraplength=440).grid(row=3, column=0, columnspan=2, sticky="w", pady=8)
        result = {}
        def save():
            value = {key: entry.get().strip() for key, entry in fields.items()}
            if not all(value.values()):
                messagebox.showerror("معلومات ناقصة", "عمر اسم الصفحة وPage ID وPage Access Token.", parent=win)
                return
            result.update(value)
            win.destroy()
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="إلغاء", command=win.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="حفظ", command=save).pack(side="right")
        win.wait_window()
        return result or None

    def add_page(self):
        value = self.page_dialog()
        if not value:
            return
        if any(p.get("page_id") == value["page_id"] for p in self.pages):
            messagebox.showerror("موجودة", "هاد الصفحة مضافة من قبل.")
            return
        self.pages.append(value)
        self.persist_pages()
        self.refresh_pages()

    def edit_page(self):
        selection = self.pages_list.curselection()
        if not selection:
            messagebox.showinfo("اختيار الصفحة", "اختار صفحة أولاً.")
            return
        index = selection[0]
        value = self.page_dialog(self.pages[index])
        if value:
            self.pages[index] = value
            self.persist_pages()
            self.refresh_pages()
            self.pages_list.selection_set(index)

    def delete_page(self):
        selection = self.pages_list.curselection()
        if not selection:
            messagebox.showinfo("اختيار الصفحة", "اختار صفحة أولاً.")
            return
        index = selection[0]
        name = self.pages[index].get("name", "Page")
        if messagebox.askyesno("تأكيد", f"واش بغيتي تحذف إعدادات {name} من البرنامج؟"):
            del self.pages[index]
            self.persist_pages()
            self.refresh_pages()

    def choose_csv(self):
        path = filedialog.askopenfilename(title="اختار CSV", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            headers = read_csv_headers(path)
            aliases = {
                "Photo_Link": ("photo_link", "photo", "image", "image_url", "photo_url", "رابط الصورة", "الصورة"),
                "Facebook_Link": ("facebook_link", "post_link", "facebook_url", "post_url", "رابط المنشور", "رابط فيسبوك"),
                "Comment": ("comment", "comments", "text", "message", "التعليق", "نص التعليق"),
            }
            for key, combo in self.column_boxes.items():
                combo["values"] = headers
                current = self.column_vars[key].get()
                if current not in headers:
                    match = next((h for h in headers if h.casefold() in aliases[key]), "")
                    self.column_vars[key].set(match)
            self.csv_file = Path(path)
            self.csv_label.configure(text=f"{self.csv_file.name} — اختار الأعمدة من الخانات")
        except Exception as exc:
            messagebox.showerror("CSV غير صالح", str(exc))

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        selected = list(self.pages_list.curselection())
        if not selected:
            messagebox.showwarning("اختار الصفحة", "اختار صفحة وحدة على الأقل.")
            return
        if not self.csv_file or not self.csv_file.is_file():
            messagebox.showwarning("CSV ناقص", "اختار ملف CSV.")
            return
        try:
            column_map = {key: var.get() for key, var in self.column_vars.items()}
            rows = load_csv(self.csv_file, column_map)
            self.settings["csv_columns"] = column_map
            save_settings(self.settings)
            delay = int(self.delay.get())
            if delay < 0:
                raise ValueError()
        except Exception as exc:
            messagebox.showerror("خطأ", str(exc))
            return
        pages = [self.pages[i].copy() for i in selected]
        self.stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status.set("بدات الخدمة...")
        self.worker = threading.Thread(target=self.run_comments, args=(pages, rows, self.csv_file, delay), daemon=True)
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.log_line("طلبتي التوقيف؛ غادي يوقف من بعد الطلب الحالي.")

    def run_comments(self, pages, rows, csv_path, delay):
        succeeded = failed = skipped = 0
        for page in pages:
            if self.stop_event.is_set():
                break
            page_id = str(page["page_id"])
            state_path = STATE_DIR / f"{page_id}.json"
            try:
                completed = set(json.loads(state_path.read_text(encoding="utf-8"))) if state_path.exists() else set()
            except Exception:
                completed = set()
            results = []
            self.log_line(f'--- الصفحة: {page.get("name", page_id)} ---')
            for line_number, row in rows:
                if self.stop_event.is_set():
                    break
                key = make_row_key(csv_path, line_number, row)
                result = {"Page": page.get("name", page_id), "Page_ID": page_id,
                          "CSV_Row": line_number, "Photo_Link": row["Photo_Link"],
                          "Facebook_Link": row["Facebook_Link"], "Comment": row["Comment"],
                          "Status": "", "Comment_ID": "", "Error": ""}
                if key in completed:
                    result["Status"] = "SKIPPED_ALREADY_DONE"
                    skipped += 1
                elif not row["Facebook_Link"] or not row["Comment"]:
                    result["Status"] = "SKIPPED_MISSING_LINK_OR_COMMENT"
                    skipped += 1
                else:
                    try:
                        post_id = extract_post_id(row["Facebook_Link"])
                        params = {"message": row["Comment"], "access_token": page["access_token"]}
                        if row["Photo_Link"]:
                            params["attachment_url"] = row["Photo_Link"]
                        response = graph_request("POST", f"{post_id}/comments", params)
                        result["Status"] = "COMMENTED"
                        result["Comment_ID"] = response.get("id", "")
                        completed.add(key)
                        state_path.write_text(json.dumps(sorted(completed), ensure_ascii=False, indent=2), encoding="utf-8")
                        succeeded += 1
                    except Exception as exc:
                        result["Status"] = "FAILED"
                        result["Error"] = str(exc)[:1000]
                        failed += 1
                results.append(result)
                self.log_line(f'[{page.get("name", page_id)}] CSV row {line_number}: {result["Status"]}' +
                              (f' — {result["Error"]}' if result["Error"] else ""))
                if delay and (line_number != rows[-1][0]) and not self.stop_event.is_set():
                    if self.stop_event.wait(delay):
                        break
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = OUTPUT_DIR / f"{page_id}_results_{stamp}.csv"
            with output.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "Page", "Page_ID", "CSV_Row", "Photo_Link", "Facebook_Link",
                    "Comment", "Status", "Comment_ID", "Error"
                ])
                writer.writeheader()
                writer.writerows(results)
            self.log_line(f"نتائج الصفحة محفوظة: output/{output.name}")
        self.events.put(("finished", (succeeded, failed, skipped)))

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "fetched_pages":
                    count_added = 0
                    for item in value:
                        page = {"name": item.get("name", "Facebook Page"),
                                "page_id": str(item["id"]),
                                "access_token": item["access_token"]}
                        existing = next((i for i, p in enumerate(self.pages) if p.get("page_id") == page["page_id"]), None)
                        if existing is None:
                            self.pages.append(page)
                        else:
                            self.pages[existing] = page
                        count_added += 1
                    self.persist_pages()
                    self.refresh_pages()
                    if self.pages:
                        self.pages_list.selection_set(0, "end")
                    self.fetch_button.configure(state="normal")
                    self.status.set(f"تم جلب {count_added} صفحة. اختار الصفحة أو الصفحات.")
                    self.log_line(f"تم جلب {count_added} صفحة من Meta.")
                elif kind == "error":
                    self.fetch_button.configure(state="normal")
                    self.status.set("وقع خطأ.")
                    messagebox.showerror("Facebook API", value)
                elif kind == "finished":
                    ok, bad, skipped = value
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.status.set(f"سالات العملية — ناجح: {ok} | فشل: {bad} | متجاوز: {skipped}")
                    messagebox.showinfo("انتهى", f"ناجح: {ok}\nفشل: {bad}\nمتجاوز: {skipped}\n\nالنتائج فمجلد output.")
        except queue.Empty:
            pass
        self.root.after(150, self.poll_events)


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    PublisherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
