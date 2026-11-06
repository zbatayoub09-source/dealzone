import json
import re
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

GRAPH = "https://graph.facebook.com/v26.0"


def fetch_pages(user_token):
    pages = []
    after = None
    while True:
        params = {
            "fields": "id,name,tasks",
            "limit": "100",
            "access_token": user_token,
        }
        if after:
            params["after"] = after
        url = GRAPH + "/me/accounts?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": "DealZone-Page-Helper/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                detail = payload.get("error", {}).get("message", "Facebook API error")
            except Exception:
                detail = "Facebook returned HTTP " + str(exc.code)
            raise RuntimeError(detail)
        if data.get("error"):
            raise RuntimeError(data["error"].get("message", "Facebook API error"))
        pages.extend(data.get("data", []))
        after = (data.get("paging", {}).get("cursors", {}) or {}).get("after")
        if not after or not data.get("data"):
            break
    unique = {}
    for page in pages:
        if page.get("id"):
            unique[str(page["id"])] = {
                "id": str(page["id"]),
                "name": str(page.get("name") or page["id"]),
            }
    return list(unique.values())


class JaimePagesApp:
    def __init__(self, root):
        self.root = root
        root.title("DealZone | Facebook Page Like Helper")
        root.geometry("760x650")
        root.minsize(620, 520)
        self.pages = []
        self.token_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Dkhel Facebook User Access Token, w loadi Pages.")
        self.build()

    def build(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DEALZONE — PAGE LIKE HELPER", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="اختار الصفحات اللي كتدير ليها التسيير، ومن بعد حل صفحة الهدف باش تدير التفاعل يدوياً.",
            wraplength=700,
        ).pack(anchor="w", pady=(3, 12))

        ttk.Label(outer, text="1. Facebook User Access Token").pack(anchor="w")
        token_row = ttk.Frame(outer)
        token_row.pack(fill="x", pady=(3, 8))
        ttk.Entry(token_row, textvariable=self.token_var, show="*").pack(side="left", fill="x", expand=True)
        ttk.Button(token_row, text="Load my Pages", command=self.load).pack(side="left", padx=(8, 0))
        ttk.Label(
            outer,
            text="Token kaytsta3mel ghir bach nجيب أسماء الصفحات؛ ما كيتحفظش فالجهاز ولا ف GitHub.",
            wraplength=700,
        ).pack(anchor="w")

        ttk.Label(outer, text="2. Select managed Pages (Ctrl/Shift for multiple)").pack(anchor="w", pady=(12, 4))
        list_frame = ttk.Frame(outer)
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, exportselection=False, height=13)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        select_row = ttk.Frame(outer)
        select_row.pack(fill="x", pady=7)
        ttk.Button(select_row, text="Select All", command=self.select_all).pack(side="left")
        ttk.Button(select_row, text="Select None", command=self.clear).pack(side="left", padx=7)
        self.count_var = tk.StringVar(value="0 pages loaded | 0 selected")
        ttk.Label(select_row, textvariable=self.count_var).pack(side="right")
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self.update_count())

        ttk.Label(outer, text="3. Target Facebook Page URL (the page you want to like)").pack(anchor="w", pady=(10, 3))
        ttk.Entry(outer, textvariable=self.target_var).pack(fill="x")
        ttk.Button(
            outer,
            text="OPEN TARGET PAGE IN FACEBOOK",
            command=self.open_target,
        ).pack(anchor="w", pady=(10, 8))
        ttk.Label(
            outer,
            text=(
                "Manual step: f Facebook, bdel profile l-page wa7da b wa7da (See all profiles), "
                "w dir Like/Follow ila mazal ma mتابعاش. Had l-tool ma katdirch likes automatiquement."
            ),
            wraplength=700,
        ).pack(anchor="w")
        ttk.Separator(outer).pack(fill="x", pady=10)
        ttk.Label(outer, textvariable=self.status_var, wraplength=700).pack(anchor="w")

    def load(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Token", "Paste Facebook User Access Token first.")
            return
        self.status_var.set("Loading Facebook Pages...")
        self.root.update_idletasks()
        try:
            self.pages = fetch_pages(token)
            self.listbox.delete(0, "end")
            for page in self.pages:
                self.listbox.insert("end", f"{page['name']} | ID: {page['id']}")
            if self.pages:
                self.select_all()
                self.status_var.set(f"Loaded {len(self.pages)} Pages. Select the pages you want to use.")
            else:
                self.status_var.set("No Pages returned. Check token access and pages_show_list permission.")
                messagebox.showwarning("No Pages", "Facebook ma rje3 ta Page l had token.")
        except Exception as exc:
            self.status_var.set("Could not load Pages.")
            messagebox.showerror("Facebook API", str(exc))

    def select_all(self):
        if self.pages:
            self.listbox.selection_set(0, "end")
        self.update_count()

    def clear(self):
        self.listbox.selection_clear(0, "end")
        self.update_count()

    def update_count(self):
        self.count_var.set(f"{len(self.pages)} pages loaded | {len(self.listbox.curselection())} selected")

    def open_target(self):
        selected = list(self.listbox.curselection())
        if not selected:
            messagebox.showwarning("Select Pages", "Load Pages and select at least one managed Page.")
            return
        url = self.target_var.get().strip()
        if not url:
            messagebox.showwarning("Target URL", "Paste the Facebook Page URL you want to like.")
            return
        if not url.startswith("https://"):
            url = "https://" + url.lstrip("/")
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.com", "www.fb.com", "fb.me"}:
            messagebox.showerror("Invalid URL", "Dkhel lien dyal Facebook Page (facebook.com / fb.me).")
            return
        names = [self.pages[i]["name"] for i in selected]
        webbrowser.open(url, new=2)
        self.status_var.set(
            f"Opened target page. Selected managed Pages: {len(names)}. Switch profiles manually in Facebook to interact."
        )
        messagebox.showinfo(
            "Target page opened",
            "Target page opened in your browser.\n\nSelected managed Pages:\n"
            + "\n".join(names[:25])
            + ("\n..." if len(names) > 25 else "")
            + "\n\nSwitch to each Page profile yourself and click Like/Follow if available.",
        )


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    JaimePagesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
