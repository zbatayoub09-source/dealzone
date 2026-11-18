import csv
import json
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from urllib.parse import urlparse

import requests

APP_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = APP_DIR / "settings.json"
GRAPH_VERSION = "v26.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("pages", []), list):
                return data
        except Exception:
            pass
    return {"pages": []}


def save_settings(data):
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_http_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


class PublisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook Image + Auto Comment Publisher")
        self.root.geometry("900x650")
        self.root.minsize(760, 560)
        self.settings = load_settings()
        self.stop_event = threading.Event()
        self.worker = None
        self.csv_path = tk.StringVar()
        self.delay = tk.StringVar(value="30")
        self.status = tk.StringVar(value="Ready")
        self._build()
        self.refresh_pages()

    def _build(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Label(outer, text="Facebook Image + Auto Comment Publisher",
                           font=("Segoe UI", 16, "bold"))
        header.pack(anchor="w")
        ttk.Label(outer, text="1) Add your Facebook Pages  2) Select CSV  3) Start publishing",
                  foreground="#555").pack(anchor="w", pady=(3, 12))

        pages_box = ttk.LabelFrame(outer, text="Facebook Pages (Page ID + Page Access Token)", padding=10)
        pages_box.pack(fill="x", pady=(0, 10))
        self.pages_list = tk.Listbox(pages_box, height=5, exportselection=False)
        self.pages_list.pack(side="left", fill="x", expand=True)
        page_buttons = ttk.Frame(pages_box)
        page_buttons.pack(side="right", padx=(10, 0), fill="y")
        ttk.Button(page_buttons, text="Add Page", command=self.add_page).pack(fill="x", pady=2)
        ttk.Button(page_buttons, text="Edit Selected", command=self.edit_page).pack(fill="x", pady=2)
        ttk.Button(page_buttons, text="Delete Selected", command=self.delete_page).pack(fill="x", pady=2)

        csv_box = ttk.LabelFrame(outer, text="CSV File", padding=10)
        csv_box.pack(fill="x", pady=(0, 10))
        ttk.Entry(csv_box, textvariable=self.csv_path).pack(side="left", fill="x", expand=True)
        ttk.Button(csv_box, text="Browse CSV", command=self.choose_csv).pack(side="left", padx=(8, 0))
        ttk.Label(csv_box, text="Required columns: page_name, image, comment",
                  foreground="#555").pack(anchor="w", pady=(7, 0))

        options = ttk.Frame(outer)
        options.pack(fill="x", pady=(0, 10))
        ttk.Label(options, text="Delay between posts (seconds):").pack(side="left")
        ttk.Entry(options, textvariable=self.delay, width=8).pack(side="left", padx=8)
        ttk.Label(options, text="Use a sensible delay; Facebook applies its own limits.",
                  foreground="#8a4b08").pack(side="left")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(actions, text="START PUBLISHING", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="STOP", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Open CSV Template", command=self.open_template).pack(side="left")

        log_box = ttk.LabelFrame(outer, text="Publishing Log", padding=8)
        log_box.pack(fill="both", expand=True)
        self.log = tk.Text(log_box, height=12, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        bottom = ttk.Label(outer, textvariable=self.status, relief="sunken", anchor="w")
        bottom.pack(fill="x", pady=(8, 0))

    def log_line(self, message):
        def write():
            self.log.configure(state="normal")
            self.log.insert("end", message + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, write)

    def set_status(self, message):
        self.root.after(0, lambda: self.status.set(message))

    def refresh_pages(self):
        self.pages_list.delete(0, "end")
        for page in self.settings.get("pages", []):
            self.pages_list.insert("end", f'{page.get("name", "")}  |  ID: {page.get("page_id", "")}')

    def page_dialog(self, page=None):
        original = page or {}
        win = tk.Toplevel(self.root)
        win.title("Facebook Page Settings")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)
        fields = {}
        for i, (key, label) in enumerate([
            ("name", "Page name (used in CSV)"),
            ("page_id", "Facebook Page ID"),
            ("access_token", "Page Access Token"),
        ]):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=5)
            entry = ttk.Entry(frame, width=58, show="*" if key == "access_token" else "")
            entry.grid(row=i, column=1, sticky="ew", pady=5)
            entry.insert(0, original.get(key, ""))
            fields[key] = entry
        ttk.Label(frame, text="Token is saved only in settings.json on this computer. Never upload or share it.",
                  foreground="#9b1c1c", wraplength=420).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 10))
        result = {}
        def save():
            data = {key: fields[key].get().strip() for key in fields}
            if not all(data.values()):
                messagebox.showerror("Missing information", "Fill in all three fields.", parent=win)
                return
            result.update(data)
            win.destroy()
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancel", command=win.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="Save Page", command=save).pack(side="right")
        win.wait_window()
        return result or None

    def add_page(self):
        data = self.page_dialog()
        if data:
            pages = self.settings.setdefault("pages", [])
            if any(p.get("page_id") == data["page_id"] for p in pages):
                messagebox.showerror("Duplicate Page", "This Page ID is already saved.")
                return
            pages.append(data)
            save_settings(self.settings)
            self.refresh_pages()
            self.log_line(f'Page saved: {data["name"]}')

    def edit_page(self):
        selection = self.pages_list.curselection()
        if not selection:
            messagebox.showinfo("Select Page", "Select a page first.")
            return
        index = selection[0]
        data = self.page_dialog(self.settings["pages"][index])
        if data:
            self.settings["pages"][index] = data
            save_settings(self.settings)
            self.refresh_pages()

    def delete_page(self):
        selection = self.pages_list.curselection()
        if not selection:
            messagebox.showinfo("Select Page", "Select a page first.")
            return
        index = selection[0]
        name = self.settings["pages"][index].get("name", "Page")
        if messagebox.askyesno("Confirm", f"Delete saved settings for {name}?"):
            del self.settings["pages"][index]
            save_settings(self.settings)
            self.refresh_pages()

    def choose_csv(self):
        path = filedialog.askopenfilename(
            title="Choose CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.csv_path.set(path)

    def open_template(self):
        path = APP_DIR / "sample_posts.csv"
        if path.exists():
            try:
                os.startfile(path)
            except Exception:
                messagebox.showinfo("CSV Template", str(path))

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        pages = self.settings.get("pages", [])
        if not pages:
            messagebox.showwarning("Add a Page", "Click Add Page and enter your Page ID and Page Access Token first.")
            return
        path = self.csv_path.get().strip()
        if not path or not Path(path).is_file():
            messagebox.showwarning("Choose CSV", "Choose a valid CSV file first.")
            return
        try:
            delay = int(self.delay.get())
            if delay < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid delay", "Delay must be zero or a positive whole number.")
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                required = {"page_name", "image", "comment"}
                if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                    messagebox.showerror("CSV columns missing", "CSV must contain: page_name, image, comment")
                    return
                rows = list(reader)
        except Exception as exc:
            messagebox.showerror("CSV error", str(exc))
            return
        if not rows:
            messagebox.showwarning("Empty CSV", "The CSV has no data rows.")
            return
        page_map = {p["name"].strip().casefold(): p for p in pages}
        self.stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.worker = threading.Thread(target=self.publish_rows, args=(rows, page_map, delay), daemon=True)
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.log_line("Stop requested. The current request will finish before stopping.")

    def publish_rows(self, rows, page_map, delay):
        success = 0
        failed = 0
        self.log_line(f"Starting: {len(rows)} CSV row(s).")
        for index, row in enumerate(rows, start=1):
            if self.stop_event.is_set():
                break
            page_name = (row.get("page_name") or "").strip()
            image = (row.get("image") or "").strip()
            comment = (row.get("comment") or "").strip()
            page = page_map.get(page_name.casefold())
            if not page or not image or not comment:
                failed += 1
                self.log_line(f"[{index}] SKIPPED: check page_name, image and comment.")
                continue
            try:
                photo_id, post_id = self.publish_one(page, image, comment)
                success += 1
                self.log_line(f'[{index}] OK — {page["name"]} — photo {photo_id} — post {post_id}')
            except Exception as exc:
                failed += 1
                self.log_line(f'[{index}] ERROR — {page_name}: {exc}')
            if index < len(rows) and not self.stop_event.is_set() and delay:
                for _ in range(delay):
                    if self.stop_event.wait(1):
                        break
        self.set_status(f"Finished. Published: {success} | Failed/skipped: {failed}")
        self.log_line(f"Finished. Published: {success} | Failed/skipped: {failed}")
        self.root.after(0, lambda: self.start_button.configure(state="normal"))
        self.root.after(0, lambda: self.stop_button.configure(state="disabled"))

    def publish_one(self, page, image, comment):
        page_id = page["page_id"].strip()
        token = page["access_token"].strip()
        endpoint = f"{GRAPH_BASE}/{page_id}/photos"
        data = {"access_token": token, "published": "true"}
        if is_http_url(image):
            data["url"] = image
            response = requests.post(endpoint, data=data, timeout=90)
        else:
            image_path = Path(image).expanduser()
            if not image_path.is_absolute():
                image_path = APP_DIR / image_path
            if not image_path.is_file():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            with image_path.open("rb") as image_file:
                response = requests.post(
                    endpoint, data=data,
                    files={"source": (image_path.name, image_file)},
                    timeout=120
                )
        payload = response.json()
        if response.status_code >= 400 or payload.get("error"):
            error = payload.get("error", {})
            raise RuntimeError(error.get("message", str(payload)))
        photo_id = payload.get("id")
        post_id = payload.get("post_id")
        if not photo_id:
            raise RuntimeError(f"Facebook did not return a photo ID: {payload}")
        if not post_id:
            raise RuntimeError(
                "Photo was uploaded, but Facebook did not return post_id. "
                "The comment was not sent. Check Page permissions and API response."
            )
        comment_url = f"{GRAPH_BASE}/{post_id}/comments"
        comment_response = requests.post(
            comment_url,
            data={"access_token": token, "message": comment},
            timeout=90
        )
        comment_payload = comment_response.json()
        if comment_response.status_code >= 400 or comment_payload.get("error"):
            error = comment_payload.get("error", {})
            raise RuntimeError(
                f"Photo published (post {post_id}), but comment failed: "
                f"{error.get('message', comment_payload)}"
            )
        return photo_id, post_id


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
