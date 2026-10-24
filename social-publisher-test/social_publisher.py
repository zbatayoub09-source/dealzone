import csv
import json
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / "publisher_state.json"
PLATFORMS = ["Facebook", "Instagram", "Blogger", "YouTube", "TikTok", "Pinterest", "Threads"]

class SocialPublisher:
    def __init__(self, root):
        self.root = root
        self.root.title("Social Publisher - Test")
        self.root.geometry("850x690")
        self.root.minsize(760, 620)
        self.csv_path = None
        self.rows = []
        self.index = 0
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        self.worker = None
        self._build_ui()
        self._load_state()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Social Publisher", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(outer, text="اختار CSV والمنصات، وحدد الوقت بين المنشورات.", font=("Segoe UI", 11)).pack(anchor="w", pady=(2, 14))

        file_box = ttk.LabelFrame(outer, text="1. ملف المنتجات / المنشورات", padding=12)
        file_box.pack(fill="x", pady=5)
        row = ttk.Frame(file_box); row.pack(fill="x")
        self.file_label = ttk.Label(row, text="مازال ما اخترتي حتى ملف CSV")
        self.file_label.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="اختيار CSV", command=self.choose_csv).pack(side="right")
        self.count_label = ttk.Label(file_box, text="عدد السطور: 0")
        self.count_label.pack(anchor="w", pady=(8, 0))

        platform_box = ttk.LabelFrame(outer, text="2. اختار المنصات", padding=12)
        platform_box.pack(fill="x", pady=5)
        self.platform_vars = {}
        grid = ttk.Frame(platform_box); grid.pack(fill="x")
        for i, name in enumerate(PLATFORMS):
            var = tk.BooleanVar(value=name in ("Facebook", "Instagram", "Blogger", "YouTube"))
            self.platform_vars[name] = var
            ttk.Checkbutton(grid, text=name, variable=var).grid(row=i // 4, column=i % 4, sticky="w", padx=8, pady=4)

        settings = ttk.LabelFrame(outer, text="3. توقيت النشر", padding=12)
        settings.pack(fill="x", pady=5)
        line = ttk.Frame(settings); line.pack(fill="x")
        ttk.Label(line, text="المدة بين كل منشور:").pack(side="left")
        self.minutes = tk.IntVar(value=2)
        self.minute_spin = ttk.Spinbox(line, from_=2, to=1440, increment=1, width=8, textvariable=self.minutes)
        self.minute_spin.pack(side="left", padx=8)
        ttk.Label(line, text="دقيقة (الحد الأدنى دقيقتان)").pack(side="left")
        ttk.Label(settings, text="ملاحظة: هاد النسخة كتجرب اختيار CSV والتوقيت وحفظ التقدم؛ النشر الفعلي خاصو ربط API والصلاحيات لكل منصة.", wraplength=760).pack(anchor="w", pady=(8, 0))

        action = ttk.Frame(outer); action.pack(fill="x", pady=12)
        self.start_btn = ttk.Button(action, text="بدا / كمل", command=self.start)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.pause_btn = ttk.Button(action, text="إيقاف مؤقت", command=self.pause, state="disabled")
        self.pause_btn.pack(side="left", padx=(0, 8))
        ttk.Button(action, text="إعادة التقدم للصفر", command=self.reset_progress).pack(side="left")

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(2, 6))
        self.status = ttk.Label(outer, text="الحالة: واجد")
        self.status.pack(anchor="w")
        self.next_label = ttk.Label(outer, text="المنشور التالي: —")
        self.next_label.pack(anchor="w", pady=(4, 0))
        self.log = tk.Text(outer, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, pady=(10, 0))

    def log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def choose_csv(self):
        path = filedialog.askopenfilename(title="اختار ملف CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("الملف ما فيهش أسماء الأعمدة.")
                rows = list(reader)
            self.csv_path = Path(path)
            self.rows = rows
            self.index = 0
            self.file_label.configure(text=self.csv_path.name)
            self.count_label.configure(text=f"عدد السطور: {len(rows)}")
            self._save_state()
            self._refresh_progress()
            self.log_line(f"تم تحميل الملف: {self.csv_path.name} ({len(rows)} سطر)")
        except Exception as exc:
            messagebox.showerror("مشكل في CSV", f"ما قدرناش نقراو الملف. تأكد أنه CSV صالح.\n\n{exc}")

    def _selected_platforms(self):
        return [name for name, var in self.platform_vars.items() if var.get()]

    def start(self):
        if not self.rows:
            messagebox.showwarning("خاصك تختار ملف", "اختار CSV قبل ما تبدا.")
            return
        if not self._selected_platforms():
            messagebox.showwarning("اختار منصة", "اختار منصة وحدة على الأقل.")
            return
        try:
            interval = int(self.minutes.get())
            if interval < 2:
                raise ValueError
        except Exception:
            messagebox.showwarning("التوقيت غير صالح", "أقل مدة مسموح بها هي دقيقتان.")
            return
        if self.running:
            self.paused = False
            self.pause_btn.configure(text="إيقاف مؤقت")
            self.status.configure(text="الحالة: كمل الخدمة")
            return
        self.running = True
        self.paused = False
        self.stop_event.clear()
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal", text="إيقاف مؤقت")
        self.worker = threading.Thread(target=self._run_preview, daemon=True)
        self.worker.start()

    def pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        self.pause_btn.configure(text="استئناف" if self.paused else "إيقاف مؤقت")
        self.status.configure(text="الحالة: موقوف مؤقتاً" if self.paused else "الحالة: كمل الخدمة")

    def _run_preview(self):
        try:
            while self.index < len(self.rows) and not self.stop_event.is_set():
                while self.paused and not self.stop_event.is_set():
                    time.sleep(0.25)
                if self.stop_event.is_set():
                    break
                row = self.rows[self.index]
                self.root.after(0, self._show_current, self.index, row)
                # This prototype only previews the queue. It does NOT publish to any platform.
                self.root.after(0, self.log_line, f"معاينة المنشور {self.index + 1}/{len(self.rows)} — ما تنشرش فعلياً.")
                self.index += 1
                self._save_state()
                self.root.after(0, self._refresh_progress)
                if self.index >= len(self.rows):
                    break
                deadline = time.monotonic() + int(self.minutes.get()) * 60
                while time.monotonic() < deadline and not self.stop_event.is_set():
                    while self.paused and not self.stop_event.is_set():
                        time.sleep(0.25)
                        deadline += 0.25
                    time.sleep(min(0.25, max(0, deadline - time.monotonic())))
            self.root.after(0, self._finished)
        except Exception as exc:
            self.root.after(0, self._worker_error, str(exc))

    def _show_current(self, index, row):
        keys = list(row.keys())
        title = next((str(row.get(k, "") or "").strip() for k in keys if any(s in k.lower() for s in ("title", "name", "product", "desc", "text")) and str(row.get(k, "") or "").strip()), "")
        if not title:
            title = next((str(v).strip() for v in row.values() if str(v or "").strip()), "(سطر فارغ)")
        self.next_label.configure(text=f"المعاينة: {index + 1} — {title[:150]}")

    def _refresh_progress(self):
        total = len(self.rows)
        percent = int((self.index / total) * 100) if total else 0
        self.progress.configure(value=percent)
        self.status.configure(text=f"الحالة: {self.index} من {total} — معاينة فقط")

    def _finished(self):
        self.running = False
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="إيقاف مؤقت")
        self.status.configure(text=f"الحالة: سالات المعاينة ({self.index}/{len(self.rows)})")
        self._save_state()

    def _worker_error(self, message):
        self.running = False
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        messagebox.showerror("خطأ", message)

    def reset_progress(self):
        if self.running:
            messagebox.showwarning("وقف الخدمة", "وقف الخدمة قبل إعادة التقدم.")
            return
        if messagebox.askyesno("تأكيد", "واش متأكد بغيتي ترجع التقدم للصفر؟"):
            self.index = 0
            self._save_state()
            self._refresh_progress()
            self.next_label.configure(text="المنشور التالي: —")
            self.log_line("ترجع التقدم للصفر.")

    def _save_state(self):
        try:
            data = {"csv_path": str(self.csv_path) if self.csv_path else None, "index": self.index}
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _load_state(self):
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            path = data.get("csv_path")
            if path and Path(path).is_file():
                self.csv_path = Path(path)
                with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
                    self.rows = list(csv.DictReader(f))
                self.index = min(max(0, int(data.get("index", 0))), len(self.rows))
                self.file_label.configure(text=self.csv_path.name)
                self.count_label.configure(text=f"عدد السطور: {len(self.rows)}")
                self._refresh_progress()
                self.log_line("ترجع التقدم المحفوظ من آخر مرة.")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    def _close(self):
        self.stop_event.set()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SocialPublisher(root)
    root.mainloop()
