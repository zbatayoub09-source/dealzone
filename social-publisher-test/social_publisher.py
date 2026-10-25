import csv
import json
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / "publisher_state.json"
PLATFORMS = ["Facebook", "Instagram", "Blogger", "TikTok", "Pinterest", "Threads"]
DEFAULT_PLATFORMS = {"Facebook", "Instagram", "Blogger"}
TEXT_HINTS = ("comment", "caption", "description", "title", "name", "product", "text", "message")
IMAGE_HINTS = ("image", "photo", "picture", "img")
VIDEO_HINTS = ("video", "movie", "mp4")


class SocialPublisher:
    def __init__(self, root):
        self.root = root
        self.root.title("DealZone Social Publisher - Test")
        self.root.geometry("900x760")
        self.root.minsize(780, 620)
        self.csv_path = None
        self.rows = []
        self.columns = []
        self.selected_columns = []
        self.index = 0
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        self.worker = None
        self.media_mode = tk.StringVar(value="auto")
        self._build_ui()
        self._load_state()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="DealZone Social Publisher", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="اختار CSV، الأعمدة اللي تدخل فالنص، نوع الميديا والمنصات المستهدفة.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 12))

        file_box = ttk.LabelFrame(outer, text="1. ملف CSV", padding=10)
        file_box.pack(fill="x", pady=4)
        file_row = ttk.Frame(file_box)
        file_row.pack(fill="x")
        self.file_label = ttk.Label(file_row, text="مازال ما اخترتي حتى ملف CSV")
        self.file_label.pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text="اختيار CSV", command=self.choose_csv).pack(side="right")
        self.count_label = ttk.Label(file_box, text="عدد السطور: 0")
        self.count_label.pack(anchor="w", pady=(5, 0))

        content_box = ttk.LabelFrame(outer, text="2. محتوى المنشور والميديا", padding=10)
        content_box.pack(fill="x", pady=4)
        content_row = ttk.Frame(content_box)
        content_row.pack(fill="x")
        ttk.Button(content_row, text="اختيار أعمدة النص / التعليق", command=self.choose_columns).pack(side="left")
        self.columns_label = ttk.Label(content_row, text="الأعمدة: ما تختاروش CSV بعد")
        self.columns_label.pack(side="left", padx=10, fill="x", expand=True)

        media_row = ttk.Frame(content_box)
        media_row.pack(fill="x", pady=(9, 0))
        ttk.Label(media_row, text="نوع الميديا:").pack(side="left")
        for label, value in (("تلقائي حسب CSV", "auto"), ("صورة", "image"), ("فيديو", "video"), ("بلا ميديا", "none")):
            ttk.Radiobutton(media_row, text=label, value=value, variable=self.media_mode).pack(side="left", padx=(8, 0))
        ttk.Label(
            content_box,
            text="التطبيق كيتعرف تلقائياً على أعمدة Image/Photo وVideo. النص المختار (بما فيه Comment/Caption) كيتجمع فمعاينة واحدة.",
            wraplength=820,
        ).pack(anchor="w", pady=(7, 0))

        platform_box = ttk.LabelFrame(outer, text="3. اختار المنصات", padding=10)
        platform_box.pack(fill="x", pady=4)
        self.platform_vars = {}
        grid = ttk.Frame(platform_box)
        grid.pack(fill="x")
        for i, name in enumerate(PLATFORMS):
            var = tk.BooleanVar(value=name in DEFAULT_PLATFORMS)
            self.platform_vars[name] = var
            ttk.Checkbutton(grid, text=name, variable=var).grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=3)

        timing = ttk.LabelFrame(outer, text="4. التوقيت والتحكم", padding=10)
        timing.pack(fill="x", pady=4)
        timing_row = ttk.Frame(timing)
        timing_row.pack(fill="x")
        ttk.Label(timing_row, text="المدة بين المنشورات:").pack(side="left")
        self.minutes = tk.IntVar(value=2)
        ttk.Spinbox(timing_row, from_=2, to=1440, increment=1, width=8, textvariable=self.minutes).pack(side="left", padx=8)
        ttk.Label(timing_row, text="دقيقة").pack(side="left")
        ttk.Label(
            timing,
            text="مهم: هاد الفرع مازال نسخة معاينة وجدولة فقط، وما كينشرش فعلياً. النشر الحقيقي كيحتاج API وصلاحيات منفصلة لكل منصة.",
            wraplength=820,
        ).pack(anchor="w", pady=(7, 0))

        action = ttk.Frame(outer)
        action.pack(fill="x", pady=9)
        self.start_btn = ttk.Button(action, text="بدا المعاينة / كمل", command=self.start)
        self.start_btn.pack(side="left", padx=(0, 7))
        self.pause_btn = ttk.Button(action, text="إيقاف مؤقت", command=self.pause, state="disabled")
        self.pause_btn.pack(side="left", padx=(0, 7))
        ttk.Button(action, text="إعادة التقدم للصفر", command=self.reset_progress).pack(side="left")

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(2, 5))
        self.status = ttk.Label(outer, text="الحالة: واجد")
        self.status.pack(anchor="w")
        self.next_label = ttk.Label(outer, text="المعاينة: —", wraplength=850)
        self.next_label.pack(anchor="w", pady=(4, 0))
        self.log = tk.Text(outer, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, pady=(8, 0))

    def log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def choose_csv(self):
        path = filedialog.askopenfilename(
            title="اختار ملف CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("الملف ما فيهش أسماء الأعمدة.")
                rows = list(reader)
                columns = list(reader.fieldnames)
            self.csv_path = Path(path)
            self.rows = rows
            self.columns = columns
            self.index = 0
            self.selected_columns = self._suggest_text_columns(columns)
            self.file_label.configure(text=self.csv_path.name)
            self.count_label.configure(text=f"عدد السطور: {len(rows)}")
            self._refresh_columns_label()
            self._save_state()
            self._refresh_progress()
            self.log_line(f"تحمّل CSV: {self.csv_path.name} ({len(rows)} سطر، {len(columns)} عمود)")
        except Exception as exc:
            messagebox.showerror("مشكل في CSV", f"ما قدرناش نقراو الملف. تأكد أنه CSV صالح.\n\n{exc}")

    def _suggest_text_columns(self, columns):
        suggested = [col for col in columns if any(hint in col.lower() for hint in TEXT_HINTS)]
        return suggested or list(columns[:1])

    def choose_columns(self):
        if not self.columns:
            messagebox.showwarning("اختار CSV", "خاصك تختار ملف CSV الأول.")
            return
        win = tk.Toplevel(self.root)
        win.title("اختيار أعمدة النص")
        win.geometry("460x540")
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text="اختار الأعمدة اللي بغيتي تدخل فالنص المنشور:", padding=10).pack(anchor="w")
        canvas = tk.Canvas(win, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        list_frame = ttk.Frame(canvas, padding=(10, 0, 10, 10))
        list_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        vars_by_column = {}
        selected = set(self.selected_columns)
        for column in self.columns:
            var = tk.BooleanVar(value=column in selected)
            vars_by_column[column] = var
            ttk.Checkbutton(list_frame, text=column, variable=var).pack(anchor="w", pady=2)

        buttons = ttk.Frame(win, padding=10)
        buttons.pack(fill="x", side="bottom")

        def save_selection():
            self.selected_columns = [col for col in self.columns if vars_by_column[col].get()]
            self._refresh_columns_label()
            self._save_state()
            win.destroy()
            self._update_preview_if_possible()

        ttk.Button(buttons, text="اختيار الكل", command=lambda: [var.set(True) for var in vars_by_column.values()]).pack(side="left")
        ttk.Button(buttons, text="إلغاء الكل", command=lambda: [var.set(False) for var in vars_by_column.values()]).pack(side="left", padx=6)
        ttk.Button(buttons, text="حفظ", command=save_selection).pack(side="right")

    def _refresh_columns_label(self):
        if not self.columns:
            text = "الأعمدة: ما تختاروش CSV بعد"
        elif self.selected_columns:
            text = "الأعمدة: " + ", ".join(self.selected_columns[:3])
            if len(self.selected_columns) > 3:
                text += f" (+{len(self.selected_columns) - 3})"
        else:
            text = "الأعمدة: ما مختار حتى عمود للنص"
        self.columns_label.configure(text=text)

    def _selected_platforms(self):
        return [name for name, var in self.platform_vars.items() if var.get()]

    def _media_url(self, row):
        if self.media_mode.get() == "none":
            return "", "بلا ميديا"
        image_col = next((c for c in self.columns if any(h in c.lower() for h in IMAGE_HINTS)), None)
        video_col = next((c for c in self.columns if any(h in c.lower() for h in VIDEO_HINTS)), None)
        if self.media_mode.get() == "image":
            col = image_col or video_col
            kind = "صورة"
        elif self.media_mode.get() == "video":
            col = video_col or image_col
            kind = "فيديو"
        else:
            if video_col and str(row.get(video_col, "") or "").strip():
                col, kind = video_col, "فيديو"
            elif image_col and str(row.get(image_col, "") or "").strip():
                col, kind = image_col, "صورة"
            else:
                col, kind = None, "بلا ميديا"
        url = str(row.get(col, "") or "").strip() if col else ""
        if not url:
            kind = "بلا ميديا (ما لقا حتى رابط صالح فالعمود)"
        return url, kind

    def _compose_caption(self, row):
        parts = []
        for column in self.selected_columns:
            value = str(row.get(column, "") or "").strip()
            if value and value not in parts:
                parts.append(value)
        return "\n\n".join(parts)

    def _update_preview_if_possible(self):
        if self.rows and self.index < len(self.rows):
            self._show_current(self.index, self.rows[self.index])

    def start(self):
        if not self.rows:
            messagebox.showwarning("خاصك تختار ملف", "اختار CSV قبل ما تبدا.")
            return
        if not self._selected_platforms():
            messagebox.showwarning("اختار منصة", "اختار منصة وحدة على الأقل.")
            return
        if not self.selected_columns:
            messagebox.showwarning("اختار الأعمدة", "اختار عمود واحد على الأقل للنص، أو افتح اختيار الأعمدة.")
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
            self.status.configure(text="الحالة: كمل المعاينة")
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
        self.status.configure(text="الحالة: موقوف مؤقتاً" if self.paused else "الحالة: كمل المعاينة")

    def _run_preview(self):
        try:
            while self.index < len(self.rows) and not self.stop_event.is_set():
                while self.paused and not self.stop_event.is_set():
                    time.sleep(0.25)
                if self.stop_event.is_set():
                    break
                row = self.rows[self.index]
                self.root.after(0, self._show_current, self.index, row)
                platforms = ", ".join(self._selected_platforms())
                self.root.after(0, self.log_line, f"معاينة {self.index + 1}/{len(self.rows)} | المنصات المختارة: {platforms} | ما تنشرش فعلياً.")
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
        caption = self._compose_caption(row) or "(ما كاين حتى نص فالأعمدة المختارة)"
        media_url, media_kind = self._media_url(row)
        platforms = ", ".join(self._selected_platforms()) or "ما مختار حتى منصة"
        preview = f"المنشور {index + 1}\nالمنصات: {platforms}\nنوع الميديا: {media_kind}\nرابط الميديا: {media_url or '—'}\n\nالنص / التعليق:\n{caption}"
        self.next_label.configure(text=preview)

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
            self.next_label.configure(text="المعاينة: —")
            self.log_line("ترجع التقدم للصفر.")

    def _save_state(self):
        try:
            data = {
                "csv_path": str(self.csv_path) if self.csv_path else None,
                "index": self.index,
                "selected_columns": self.selected_columns,
                "media_mode": self.media_mode.get(),
            }
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _load_state(self):
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            path = data.get("csv_path")
            self.media_mode.set(data.get("media_mode", "auto"))
            if path and Path(path).is_file():
                self.csv_path = Path(path)
                with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    self.columns = list(reader.fieldnames or [])
                    self.rows = list(reader)
                saved_columns = data.get("selected_columns", [])
                self.selected_columns = [c for c in saved_columns if c in self.columns] or self._suggest_text_columns(self.columns)
                self.index = min(max(0, int(data.get("index", 0))), len(self.rows))
                self.file_label.configure(text=self.csv_path.name)
                self.count_label.configure(text=f"عدد السطور: {len(self.rows)}")
                self._refresh_columns_label()
                self._refresh_progress()
                self.log_line("ترجع CSV والتقدم المحفوظ من آخر مرة.")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    def _close(self):
        self.stop_event.set()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SocialPublisher(root)
    root.mainloop()
