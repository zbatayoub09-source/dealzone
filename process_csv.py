import csv
import re
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "metricool.csv"

INPUTS = []
for p in sorted(ROOT.glob("*.csv")):
    if p.name.lower() == "metricool.csv":
        continue
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            headers = csv.DictReader(f).fieldnames or []
            if "ProductId" in headers and "Promotion Url" in headers:
                INPUTS.append(p)
    except Exception:
        pass

if not INPUTS:
    raise SystemExit("No AliExpress CSV files found.")

HEADERS = """Text,Date,Time,Draft,Facebook,Twitter/X,LinkedIn,GBP,Instagram,Pinterest,TikTok,Youtube,Threads,Bluesky,Picture Url 1,Picture Url 2,Picture Url 3,Picture Url 4,Picture Url 5,Picture Url 6,Picture Url 7,Picture Url 8,Picture Url 9,Picture Url 10,Alt text picture 1,Alt text picture 2,Alt text picture 3,Alt text picture 4,Alt text picture 5,Alt text picture 6,Alt text picture 7,Alt text picture 8,Alt text picture 9,Alt text picture 10,Document title,Shortener,Video Thumbnail Url,Video Cover Frame,Twitter/X Can reply,Twitter/X Type,Twitter/X Poll Duration minutes,Twitter/X Poll Option 1,Twitter/X Poll Option 2,Twitter/X Poll Option 3,Twitter/X Poll Option 4,Pinterest Board,Pinterest Pin Title,Pinterest Pin Link,Pinterest Pin New Format,Instagram Post Type,Instagram Show Reel On Feed,Instagram Trial Reel Share Automatically,Youtube Video Title,Youtube Video Type,Youtube Video Privacy,Youtube video for kids,Youtube AI generated content,Youtube notify subscribers,Youtube Video Category,Youtube Video Tags,Youtube playlist,GBP Post Type,Facebook Post Type,Facebook Title,First Comment Text,TikTok Title,TikTok disable comments,TikTok disable duet,TikTok disable stitch,TikTok Post Privacy,TikTok Branded Content,TikTok Your Brand,TikTok Auto Add Music,TikTok Photo Cover Index,TikTok musicId,TikTok music title,TikTok music author,TikTok music previewUrl,TikTok music thumbnailUrl,TikTok music soundVolume,TikTok music originalVolume,TikTok music startMillis,TikTok music endMillis,TikTok Ai generated content,LinkedIn Type,LinkedIn Poll Question,LinkedIn Poll Option 1,LinkedIn Poll Option 2,LinkedIn Poll Option 3,LinkedIn Poll Option 4,LinkedIn Poll Duration,LinkedIn Show link preview,LinkedIn Images as Carousel,Threads Reply Control,Threads Is Spoiler,Threads Post Type,Brand name""".split(",")

def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def short_title(desc):
    desc = clean(desc)
    return desc if len(desc) <= 95 else desc[:92].rsplit(" ", 1)[0] + "..."

def make_text(desc, link):
    return f"🔥 {short_title(desc)}\n\n🛒 Check the deal: {link}\n\n#AliExpress #Deals #Shopping"

rows_out = []
start = datetime.now().replace(second=0, microsecond=0) + timedelta(days=1)
slot = 0

for INPUT in INPUTS:
    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            desc = clean(row.get("Product Desc"))
            image = clean(row.get("Image Url"))
            link = clean(row.get("Promotion Url"))
            video = clean(row.get("Video Url"))
            if not desc or not image or not link:
                continue

            dt = start + timedelta(hours=slot * 4)
            slot += 1
            title = short_title(desc)
            out = {h: "" for h in HEADERS}
            out.update({
                "Text": make_text(desc, link),
                "Date": dt.strftime("%Y-%m-%d"),
                "Time": dt.strftime("%H:%M:%S"),
                "Draft": "false",
                "Facebook": "true",
                "Twitter/X": "false",
                "LinkedIn": "false",
                "GBP": "false",
                "Instagram": "true",
                "Pinterest": "true",
                "TikTok": "true",
                "Youtube": "false",
                "Threads": "false",
                "Bluesky": "false",
                "Picture Url 1": image,
                "Alt text picture 1": title,
                "Pinterest Pin Title": title[:100],
                "Pinterest Pin Link": link,
                "Pinterest Pin New Format": "false",
                "Instagram Post Type": "POST",
                "Instagram Show Reel On Feed": "false",
                "Instagram Trial Reel Share Automatically": "false",
                "Facebook Post Type": "POST",
                "Facebook Title": title,
                "First Comment Text": link,
                "TikTok Title": title[:90],
                "TikTok disable comments": "false",
                "TikTok disable duet": "false",
                "TikTok disable stitch": "false",
                "TikTok Post Privacy": "PUBLIC_TO_EVERYONE",
                "TikTok Branded Content": "false",
                "TikTok Your Brand": "false",
                "TikTok Auto Add Music": "false",
                "TikTok Photo Cover Index": "0",
                "TikTok Ai generated content": "false",
            })
            if video:
                out["First Comment Text"] = f"{link}\n🎥 Video: {video}"
            rows_out.append(out)

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows_out)

print("Input CSV files:")
for p in INPUTS:
    print(f" - {p.name}")
print(f"Output: {OUTPUT.name}")
print(f"Products exported: {len(rows_out)}")
