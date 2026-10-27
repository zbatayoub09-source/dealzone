import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import gspread
import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
STATE_FILE = BASE_DIR / "published_state.json"

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "").strip()
SHEET_NAME = os.getenv("SHEET_NAME", "News").strip() or "News"
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json").strip()
FB_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
GRAPH_VERSION = os.getenv("GRAPH_API_VERSION", "v26.0").strip()
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"


def read_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def sheets_client():
    credentials_path = BASE_DIR / GOOGLE_CREDENTIALS_FILE
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google credentials file not found: {credentials_path}\n"
            "Download the Google service-account JSON and save it as credentials.json."
        )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(credentials_path), scopes=scopes)
    return gspread.authorize(creds)


def fetch_news():
    if not SPREADSHEET_ID or SPREADSHEET_ID == "PUT_GOOGLE_SHEETS_ID_HERE":
        raise ValueError("Set SPREADSHEET_ID in the local .env file first.")
    client = sheets_client()
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
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


def fetch_pages():
    if not FB_TOKEN or FB_TOKEN == "PUT_PAGE_ACCESS_TOKEN_HERE":
        raise ValueError("Set FACEBOOK_PAGE_ACCESS_TOKEN in the local .env file first.")
    response = requests.get(
        f"{GRAPH_ROOT}/me/accounts",
        params={"fields": "id,name,access_token,tasks", "access_token": FB_TOKEN},
        timeout=30,
    )
    data = response.json()
    if response.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        raise RuntimeError(f"Meta API: {err.get('message', response.text)}")
    return data.get("data", [])


def publish_to_page(page, news_item):
    page_token = page.get("access_token") or FB_TOKEN
    page_id = page["id"]
    title = news_item["title"]
    article = news_item["article"]
    message = (title + "\n\n" + article).strip()
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
        self.root.title("DealZone — Google Sheets Publisher")
        self.root.geometry("850x600")
        self.news = []
        self.pages = []
        self.state = read_state()

        outer = ttk.Frame(root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DealZone Publisher", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Google Sheets → Facebook | Blogger peut être ajouté ensuite").pack(anchor="w", pady=(0, 12))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=5)
        ttk.Button(controls, text="Charger les actualités", command=self.load_news).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Charger mes pages Facebook", command=self.load_pages).pack(side="left")

        ttk.Label(outer, text="Page Facebook").pack(anchor="w", pady=(12, 3))
        self.page_box = ttk.Combobox(outer, state="readonly")
        self.page_box.pack(fill="x")
        self.page_map = {}

        ttk.Label(outer, text="Actualité à publier").pack(anchor="w", pady=(12, 3))
        self.news_box = ttk.Combobox(outer, state="readonly")
        self.news_box.pack(fill="x")
        self.news_map = {}

        ttk.Button(outer, text="Publier l’actualité sélectionnée", command=self.publish_selected).pack(anchor="w", pady=12)
        ttk.Label(outer, text="Journal").pack(anchor="w")
        self.log_box = tk.Text(outer, height=14, wrap="word")
        self.log_box.pack(fill="both", expand=True)
        self.log("Prêt. Configurez .env et credentials.json avant de charger les actualités.")

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def load_news(self):
        try:
            self.news = fetch_news()
            self.news_map = {
                f"Ligne {item['row']} — {item['title'] or '(sans titre)'}": item
                for item in self.news
            }
            self.news_box["values"] = list(self.news_map.keys())
            if self.news_map:
                self.news_box.current(0)
            self.log(f"{len(self.news)} actualité(s) chargée(s) depuis Google Sheets.")
        except Exception as exc:
            messagebox.showerror("Erreur Google Sheets", str(exc))
            self.log(f"ERREUR Sheets: {exc}")

    def load_pages(self):
        try:
            self.pages = fetch_pages()
            self.page_map = {f"{p.get('name', 'Page sans nom')} ({p.get('id')})": p for p in self.pages}
            self.page_box["values"] = list(self.page_map.keys())
            if self.page_map:
                self.page_box.current(0)
            self.log(f"{len(self.pages)} page(s) accessible(s) trouvée(s).")
            if not self.pages:
                self.log("Aucune page retournée. Vérifiez le token et les autorisations Meta.")
        except Exception as exc:
            messagebox.showerror("Erreur Facebook", str(exc))
            self.log(f"ERREUR Facebook: {exc}")

    def publish_selected(self):
        page_key = self.page_box.get()
        news_key = self.news_box.get()
        if page_key not in self.page_map:
            messagebox.showwarning("Page manquante", "Chargez et sélectionnez une page Facebook.")
            return
        if news_key not in self.news_map:
            messagebox.showwarning("Actualité manquante", "Chargez et sélectionnez une actualité.")
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
            write_state(self.state)
            self.log(f"PUBLIÉ: {item['title']} → {page.get('name')} | ID: {post_id}")
            messagebox.showinfo("Succès", f"Publication confirmée.\nPost ID: {post_id}")
        except Exception as exc:
            self.log(f"ÉCHEC publication: {exc}")
            messagebox.showerror("Échec publication", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    PublisherApp(root)
    root.mainloop()
