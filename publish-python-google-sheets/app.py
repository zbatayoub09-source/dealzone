import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import gspread
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.json"
STATE_FILE = BASE_DIR / "published_state.json"
GOOGLE_TOKEN_FILE = BASE_DIR / "token.json"
OAUTH_FILE = BASE_DIR / "client_secret.json"
GRAPH_VERSION = "v25.0"
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings():
    data = read_json(SETTINGS_FILE, {})
    return {
        "spreadsheet_id": str(data.get("spreadsheet_id", "")),
        "sheet_name": str(data.get("sheet_name", "News") or "News"),
        "facebook_user_access_token": str(data.get("facebook_user_access_token", "")),
    }


def sheets_client():
    if not OAUTH_FILE.exists():
        raise FileNotFoundError(
            "Ma l9it-ch client_secret.json. 7etto f nafs dossier m3a app.py."
        )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = None
    if GOOGLE_TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), scopes)
        except (ValueError, OSError):
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_FILE), scopes)
            creds = flow.run_local_server(port=0)
        GOOGLE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return gspread.authorize(creds)


def fetch_news(settings):
    spreadsheet_id = settings["spreadsheet_id"].strip()
    sheet_name = settings["sheet_name"].strip() or "News"
    if not spreadsheet_id:
        raise ValueError("3mer ID dyal Google Sheet f l-khana lfo9, w dghat 7fed.")
    client = sheets_client()
    worksheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    rows = worksheet.get("A:D")
    news = []
    for row_number, row in enumerate(rows[1:], start=2):
        row = row + [""] * (4 - len(row))
        date, image_url, title, article = [str(x).strip() for x in row[:4]]
        if title or article:
            news.append({
                "row": row_number,
                "date": date,
                "image": image_url,
                "title": title,
                "article": article,
            })
    return news


def fetch_pages(settings):
    token = settings["facebook_user_access_token"].strip()
    if not token:
        raise ValueError("7et Facebook User Access Token f l-khana dyalo, w dghat 7fed.")
    response = requests.get(
        f"{GRAPH_ROOT}/me/accounts",
        params={"fields": "id,name,access_token,tasks", "access_token": token},
        timeout=30,
    )
    data = response.json()
    if response.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        raise RuntimeError(f"Meta API: {err.get('message', response.text)}")
    return data.get("data", [])


def publish_to_page(page, news_item):
    page_token = page.get("access_token")
    if not page_token:
        raise RuntimeError("Meta ma rj3ch Page Access Token lhad page. Raje3 permissions dyal token.")
    page_id = page["id"]
    message = (news_item["title"] + "\n\n" + news_item["article"]).strip()
    image_url = news_item["image"]
    if image_url:
        endpoint = f"{GRAPH_ROOT}/{page_id}/photos"
        payload = {"url": image_url, "caption": message, "access_token": page_token}
    else:
        endpoint = f"{GRAPH_ROOT}/{page_id}/feed"
        payload = {"message": message, "access_token": page_token}
    response = requests.post(endpoint, data=payload, timeout=60)
    data = response.json()
    if response.status_code >= 400 or "error" in data or not data.get("id"):
        err = data.get("error", {})
        raise RuntimeError(f"Facebook API: {err.get('message', response.text)}")
    return data["id"]


class PublisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DealZone — Google Sheets → Facebook")
        self.root.geometry("920x760")
        self.root.minsize(760, 620)
        self.settings = get_settings()
        self.news = []
        self.pages = []
        self.state = read_json(STATE_FILE, {})
        self.page_map = {}
        self.news_map = {}

        outer = ttk.Frame(root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DealZone Publisher", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Dkhel ID dyal Google Sheet w Facebook token hna — bla .env w bla RUN.bat.").pack(anchor="w", pady=(0, 12))

        config = ttk.LabelFrame(outer, text="1) Configuration", padding=10)
        config.pack(fill="x", pady=(0, 10))
        ttk.Label(config, text="Google Spreadsheet ID").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        self.sheet_id_var = tk.StringVar(value=self.settings["spreadsheet_id"])
        ttk.Entry(config, textvariable=self.sheet_id_var).grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Label(config, text="اسم التبويب (Sheet name)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=5)
        self.sheet_name_var = tk.StringVar(value=self.settings["sheet_name"])
        ttk.Entry(config, textvariable=self.sheet_name_var).grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(config, text="Facebook User Access Token").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=5)
        self.fb_token_var = tk.StringVar(value=self.settings["facebook_user_access_token"])
        ttk.Entry(config, textvariable=self.fb_token_var, show="*").grid(row=2, column=1, sticky="ew", pady=5)
        ttk.Label(config, text="OAuth JSON: client_secret.json khaso ykoun f nafs dossier m3a app.py.").grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 2))
        ttk.Button(config, text="7fed l-i3dadat", command=self.save_settings).grid(row=4, column=0, sticky="w", pady=(8, 0))
        config.columnconfigure(1, weight=1)

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=4)
        ttk.Button(controls, text="2) Charger les actualités", command=self.load_news).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="3) Charger mes pages Facebook", command=self.load_pages).pack(side="left")

        ttk.Label(outer, text="Page Facebook").pack(anchor="w", pady=(12, 3))
        self.page_box = ttk.Combobox(outer, state="readonly")
        self.page_box.pack(fill="x")

        ttk.Label(outer, text="Actualité à publier").pack(anchor="w", pady=(12, 3))
        self.news_box = ttk.Combobox(outer, state="readonly")
        self.news_box.pack(fill="x")
        ttk.Button(outer, text="Publier l’actualité sélectionnée", command=self.publish_selected).pack(anchor="w", pady=12)

        ttk.Label(outer, text="Journal").pack(anchor="w")
        self.log_box = tk.Text(outer, height=12, wrap="word")
        self.log_box.pack(fill="both", expand=True)
        self.log("Prêt. 7fed l-i3dadat. 3and awel chargement dyal Sheets, Google ghadi y7ell login f browser.")
        self.log("Ma tsift l7ed client_secret.json wla Facebook token.")

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def save_settings(self, quiet=False):
        self.settings = {
            "spreadsheet_id": self.sheet_id_var.get().strip(),
            "sheet_name": self.sheet_name_var.get().strip() or "News",
            "facebook_user_access_token": self.fb_token_var.get().strip(),
        }
        write_json(SETTINGS_FILE, self.settings)
        self.log("L-i3dadat t7fedat localement f settings.json.")
        if not quiet:
            messagebox.showinfo("تم الحفظ", "T7fedat l-i3dadat f PC dyalek.")

    def load_news(self):
        try:
            self.save_settings(quiet=True)
            self.news = fetch_news(self.settings)
            self.news_map = {
                f"Ligne {item['row']} — {item['title'] or '(sans titre)'}": item
                for item in self.news
            }
            self.news_box["values"] = list(self.news_map.keys())
            if self.news_map:
                self.news_box.current(0)
            self.log(f"{len(self.news)} actualité(s) chargée(s) depuis Google Sheets.")
            if not self.news:
                self.log("Ma l9it 7ta khbar. T2ekked men A:D w smit tab (News).")
        except Exception as exc:
            messagebox.showerror("Erreur Google Sheets", str(exc))
            self.log(f"ERREUR Sheets: {exc}")

    def load_pages(self):
        try:
            self.save_settings(quiet=True)
            self.pages = fetch_pages(self.settings)
            self.page_map = {f"{p.get('name', 'Page sans nom')} ({p.get('id')})": p for p in self.pages}
            self.page_box["values"] = list(self.page_map.keys())
            if self.page_map:
                self.page_box.current(0)
            self.log(f"{len(self.pages)} page(s) accessible(s) trouvée(s).")
            if not self.pages:
                self.log("Aucune page. Raje3 Facebook token w permissions Meta.")
        except Exception as exc:
            messagebox.showerror("Erreur Facebook", str(exc))
            self.log(f"ERREUR Facebook: {exc}")

    def publish_selected(self):
        page_key = self.page_box.get()
        news_key = self.news_box.get()
        if page_key not in self.page_map:
            messagebox.showwarning("Page manquante", "Charger et choisir une page Facebook.")
            return
        if news_key not in self.news_map:
            messagebox.showwarning("Actualité manquante", "Charger et choisir une actualité.")
            return
        page = self.page_map[page_key]
        item = self.news_map[news_key]
        state_key = f"{page['id']}:{item['row']}"
        if self.state.get(state_key):
            messagebox.showinfo("Déjà publiée", "Cette ligne est déjà enregistrée comme publiée sur cette page.")
            return
        if not messagebox.askyesno("Confirmer", f"Publier « {item['title']} » sur {page.get('name')} ?"):
            return
        try:
            post_id = publish_to_page(page, item)
            self.state[state_key] = {"post_id": post_id, "title": item["title"]}
            write_json(STATE_FILE, self.state)
            self.log(f"PUBLIÉ: {item['title']} → {page.get('name')} | ID: {post_id}")
            messagebox.showinfo("Succès", f"Publication confirmée.\nPost ID: {post_id}")
        except Exception as exc:
            self.log(f"ÉCHEC publication: {exc}")
            messagebox.showerror("Échec publication", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    PublisherApp(root)
    root.mainloop()
