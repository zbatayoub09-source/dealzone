# -*- coding: utf-8 -*-
"""Facebook Page Creator — Gemini CSV writer."""
import csv
import json
import re
import threading
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_DIR = Path(__file__).resolve().parent
USED_NAMES_FILE = APP_DIR / "used_page_names.json"
MODEL = "gemini-3.8-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
COLUMNS = ["Page Name", "Username", "Bio", "Description", "Category",
           "Profile Image Prompt", "Cover Image Prompt", "Keywords"]

ALIASES = {
    "Page Name": ["page name", "page_name", "name", "title", "اسم الصفحة", "الاسم"],
    "Username": ["username", "user name", "handle", "اسم المستخدم"],
    "Bio": ["bio", "short bio", "short description", "نبذة", "نبذة قصيرة"],
    "Description": ["description", "full description", "الوصف", "وصف"],
    "Category": ["category", "type", "التصنيف", "الفئة"],
    "Profile Image Prompt": ["profile image prompt", "profile_image_prompt", "profile prompt"],
    "Cover Image Prompt": ["cover image prompt", "cover_image_prompt", "cover prompt"],
    "Keywords": ["keywords", "tags", "الكلمات المفتاحية", "كلمات مفتاحية"],
}

def clean_json(text):
    text = text.strip()
    text = re.sub(r"^\`\`\`(?:json)?\\s*", "", text, flags=re.I)
    text = re.sub(r"\\s*\`\`\`$", "", text)
    return json.loads(text)

def extract_output(data):
    parts = []
    for step in data.get("steps", []):
        if step.get("type") == "model_output":
            for item in step.get("content", []):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
    if parts:
        return "\\n".join(parts)
    if data.get("output_text"):
        return data["output_text"]
    raise ValueError("Gemini رجع جواباً بلا نص. جرّب مرة أخرى.")

class App:
    def __init__(self, root):
        self.root = root
        root.title("Facebook Page Creator | Gemini CSV")
        root.geometry("720x500")
        root.minsize(620, 440)
        self.api_key = tk.StringVar()
        self.csv_path = None
        self.stop_event = threading.Event()
        self.worker = None
        self.status = tk.StringVar(value="دخل Gemini API Key واختار CSV.")
        self.progress = tk.StringVar(value="0 / 0")
        self.build()

    def build(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Facebook Page Creator", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="تعمير أعمدة CSV بالذكاء الاصطناعي Gemini", font=("Segoe UI", 11)).pack(anchor="w", pady=(2, 16))

        ttk.Label(main, text="Gemini API Key").pack(anchor="w")
        keyrow = ttk.Frame(main); keyrow.pack(fill="x", pady=(5, 14))
        self.key_entry = ttk.Entry(keyrow, textvariable=self.api_key, show="*", font=("Segoe UI", 10))
        self.key_entry.pack(side="left", fill="x", expand=True)
        self.show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(keyrow, text="إظهار", variable=self.show_key, command=self.toggle_key).pack(side="left", padx=8)

        ttk.Label(main, text="ملف CSV").pack(anchor="w")
        csvrow = ttk.Frame(main); csvrow.pack(fill="x", pady=(5, 8))
        ttk.Button(csvrow, text="اختيار CSV", command=self.choose_csv).pack(side="left")
        self.file_label = ttk.Label(csvrow, text="ما تختار حتى ملف", wraplength=480)
        self.file_label.pack(side="left", padx=10)

        ttk.Label(main, text="البرنامج كيستعمل نفس 8 أعمدة: Page Name, Username, Bio, Description, Category, Profile Image Prompt, Cover Image Prompt, Keywords.", wraplength=660).pack(anchor="w", pady=(8, 16))
        buttons = ttk.Frame(main); buttons.pack(fill="x", pady=8)
        self.start_btn = ttk.Button(buttons, text="إنشاء CSV بالذكاء الاصطناعي", command=self.start)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(buttons, text="إلغاء / إيقاف", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left")
        ttk.Separator(main).pack(fill="x", pady=14)
        ttk.Label(main, textvariable=self.status, wraplength=660).pack(anchor="w")
        ttk.Label(main, textvariable=self.progress).pack(anchor="w", pady=(5, 6))
        self.bar = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.bar.pack(fill="x")
        ttk.Label(main, text="ملاحظة: المفتاح كيبقى غير فهاد التشغيل وما كيتكتبش فـ CSV ولا فـ GitHub.", foreground="#555").pack(anchor="w", pady=(18, 0))

    def toggle_key(self):
        self.key_entry.config(show="" if self.show_key.get() else "*")

    def choose_csv(self):
        path = filedialog.askopenfilename(title="اختيار ملف CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.csv_path = Path(path)
            self.file_label.config(text=self.csv_path.name)
            self.status.set("تم اختيار CSV. دخل API Key واضغط إنشاء CSV.")

    def stop(self):
        self.stop_event.set()
        self.status.set("طلبتي الإيقاف… غادي نوقف من بعد الطلب الحالي ونحفظ اللي تجهز.")

    def start(self):
        key = self.api_key.get().strip()
        if not key:
            messagebox.showwarning("API Key", "دخل Gemini API Key أولاً."); return
        if not self.csv_path or not self.csv_path.exists():
            messagebox.showwarning("CSV", "اختار ملف CSV أولاً."); return
        try:
            with self.csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                rows = list(reader)
            if not rows:
                messagebox.showwarning("CSV", "الملف ما فيه حتى سطر."); return
            if len(rows) > 500:
                messagebox.showwarning("CSV", "اختار ملف فيه 500 سطر أو أقل."); return
        except Exception as e:
            messagebox.showerror("CSV", str(e)); return
        self.stop_event.clear()
        self.start_btn.config(state="disabled"); self.stop_btn.config(state="normal")
        self.worker = threading.Thread(target=self.generate, args=(key, headers, rows), daemon=True)
        self.worker.start()

    def existing_names(self):
        if USED_NAMES_FILE.exists():
            try:
                data = json.loads(USED_NAMES_FILE.read_text(encoding="utf-8"))
                return {str(x).strip().casefold() for x in data}
            except Exception:
                return set()
        return set()

    def save_names(self, names):
        old = self.existing_names()
        old.update(x.strip().casefold() for x in names if x.strip())
        USED_NAMES_FILE.write_text(json.dumps(sorted(old), ensure_ascii=False, indent=2), encoding="utf-8")

    def request_gemini(self, key, seed, row_number, used):
        prompt = f"""
You create professional Facebook business page CSV content.
Return ONLY one valid JSON object, no markdown and no extra text.
Required exact keys: {json.dumps(COLUMNS)}.
Create a distinct, natural, brandable Facebook Page Name and unique lowercase Username.
Write a short Bio, useful Description, suitable Facebook Category, detailed Profile Image Prompt,
detailed wide Cover Image Prompt, and comma-separated Keywords.
Use English. Do not claim official affiliation, guarantees, or fake discounts.
Keep Bio concise, Description informative and original.
The row's current CSV data is inspiration only; improve or replace it.
Never use any of these existing page names: {json.dumps(sorted(list(used))[-250:], ensure_ascii=False)}.
Source row number: {row_number}
Source row data: {json.dumps(seed, ensure_ascii=False)}
"""
        body = json.dumps({"model": MODEL, "input": prompt}).encode("utf-8")
        req = urllib.request.Request(API_URL, data=body, headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key
        }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:900]
            raise RuntimeError(f"Gemini API HTTP {e.code}: {detail}")
        except Exception as e:
            raise RuntimeError(f"تعذر الاتصال بـ Gemini: {e}")
        result = clean_json(extract_output(payload))
        if isinstance(result, list):
            result = result[0]
        return {col: str(result.get(col, "")).strip() for col in COLUMNS}

    def ui(self, message, done, total):
        def update():
            self.status.set(message)
            self.progress.set(f"{done} / {total}")
            self.bar["value"] = (done / total * 100) if total else 0
        self.root.after(0, update)

    def generate(self, key, headers, rows):
        header_lookup = {h.strip().casefold(): h for h in headers if h}
        aliases = {col: next((header_lookup[a.casefold()] for a in ALIASES[col] if a.casefold() in header_lookup), None) for col in COLUMNS}
        used = self.existing_names()
        results = []
        errors = []
        total = len(rows)
        output = self.csv_path.with_name(self.csv_path.stem + "_gemini_filled_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
        for i, row in enumerate(rows, 1):
            if self.stop_event.is_set():
                break
            seed = {col: (row.get(aliases[col], "") if aliases[col] else "") for col in COLUMNS}
            try:
                data = self.request_gemini(key, seed, i, used)
                name = data.get("Page Name", "").strip()
                if not name:
                    raise ValueError("Gemini ما عطاش اسم الصفحة.")
                if name.casefold() in used:
                    raise ValueError(f"اسم مكرر: {name}")
                data["Username"] = re.sub(r"[^a-zA-Z0-9._]", "", data["Username"].replace(" ", "").lower())[:30]
                if not data["Username"]:
                    data["Username"] = re.sub(r"[^a-z0-9]", "", name.lower())[:30]
                results.append(data)
                used.add(name.casefold())
                self.save_names([name])
            except Exception as e:
                errors.append(f"السطر {i}: {e}")
            self.ui(f"جاري تجهيز CSV… {i} من {total}", i, total)
            # Save progress continuously, so Stop does not lose completed rows.
            with output.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=COLUMNS)
                writer.writeheader(); writer.writerows(results)
        stopped = self.stop_event.is_set()
        def finish():
            self.start_btn.config(state="normal"); self.stop_btn.config(state="disabled")
            self.status.set(("توقف بناءً على طلبك. " if stopped else "اكتمل العمل. ") + f"تجهز {len(results)} صفحة.")
            if errors:
                messagebox.showwarning("ملاحظات", "\n".join(errors[:8]))
            if results:
                messagebox.showinfo("تم إنشاء CSV", f"الملف:\n{output}\n\nعدد الصفحات: {len(results)}")
            elif not stopped:
                messagebox.showerror("لم يتم إنشاء CSV", "ما تجهز حتى سطر. راجع API Key والاتصال.")
        self.root.after(0, finish)

if __name__ == "__main__":
    root = tk.Tk()
    try: ttk.Style().theme_use("clam")
    except Exception: pass
    App(root)
    root.mainloop()
