import csv
import re
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "metricool.csv"

# Find the first AliExpress CSV containing ProductId.
candidates = [p for p in ROOT.glob("*.csv") if p.name.lower() != "metricool.csv"]
INPUT = None
for p in candidates:
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if "ProductId" in headers and "Promotion Url" in headers:
                INPUT = p
                break
    except Exception:
        pass

if INPUT is None:
    raise SystemExit("No AliExpress CSV found. Put the AliExpress CSV in the repository root.")

HEADERS = """Text,Date,Time,Draft,Facebook,Twitter/X,LinkedIn,GBP,Instagram,Pinterest,TikTok,Youtube,Threads,Bluesky,Picture Url 1,Picture Url 2,Picture Url 3,Picture Url 4,Picture Url 5,Picture Url 6,Picture Url 7,Picture Url 8,Picture Url 9,Picture Url 10,Alt text picture 1,Alt text picture 2,Alt text picture 3,Alt text picture 4,Alt text picture 5,Alt text picture 6,Alt text picture 7,Alt text picture 8,Alt text picture 9,Alt text picture 10,Document title,Shortener,Video Thumbnail Url,Video Cover Frame,Twitter/X Can reply,Twitter/X Type,Twitter/X Poll Duration minutes,Twitter/X Poll Option 1,Twitter/X Poll Option 2,Twitter/X Poll Option 3,Twitter/X Poll Option 4,Pinterest Board,Pinterest Pin Title,Pinterest Pin Link,Pinterest Pin New Format,Instagram Post Type,Instagram Show Reel On Feed,Instagram Trial Reel Share Automatically,Youtube Video Title,Youtube Video Type,Youtube Video Privacy,Youtube video for kids,Youtube AI generated content,Youtube notify subscribers,Youtube Video Category,Youtube Video Tags,Youtube playlist,GBP Post Type,Facebook Post Type,Facebook Title,First Comment Text,TikTok Title,TikTok disable comments,TikTok disable duet,TikTok disable stitch,TikTok Post Privacy,TikTok Branded Content,TikTok Your Brand,TikTok Auto Add Music,TikTok Photo Cover Index,TikTok musicId,TikTok music title,TikTok music author,TikTok music previewUrl,TikTok music thumbnailUrl,TikTok music soundVolume,TikTok music originalVolume,TikTok music startMillis,TikTok music endMillis,TikTok Ai generated content,LinkedIn Type,LinkedIn Poll Question,LinkedIn Poll Option 1,LinkedIn Poll Option 2,LinkedIn Poll Option 3,LinkedIn Poll Option 4,LinkedIn Poll Duration,LinkedIn Show link preview,LinkedIn Images as Carousel,Threads Reply Control,Threads Is Spoiler,Threads Post Type,Brand name""".split(",")

def clean(s):
    s = (s or "").strip()
    s = re.sub(r"\\s+", " ", s)
    return s

def short_title(desc):
    desc = clean(desc)
    if len(desc) <= 95:
        return desc
    return desc[:92].rsplit(" ", 1)[0] + "..."

def tags(desc):
    words = re.findall(r"[A-Za-z0-9]+", desc.lower())
    stop = {"the","and","for","with","from","portable","new","hot","sale","free","mini"}
    words = [w for w in words if len(w) >= 3 and w not in stop]
    return ",".join(words[:8] + ["AliExpress","Deals","Shopping"])

def make_text(desc, link):
    title = short_title(desc)
    text = f"🔥 {title}\n\n🛒 Check the deal: {link}\n\n#AliExpress #Deals #Shopping"
    return text

rows_out = []
start = datetime.now().replace(second=0, microsecond=0) + timedelta(days=1)
slot = 0

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        desc = clean(row.get("Product Desc"))
        image = clean(row.get("Image Url"))
        link = clean(row.get("Promotion Url"))
        video = clean(row.get("Video Url"))
        if not desc or not image or not link:
            continue

        dt = start + timedelta(hours=slot * 4)
        slot += 1

        # Metricool's CSV template supplied by the user has no Video URL/source column.
        # Therefore the safe import is image-based. Video Url is preserved in a comment
        # field only when present; it is not falsely mapped as an image.
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
            "Youtube": "true",
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
            "Youtube Video Title": title[:100],
            "Youtube Video Type": "SHORT",
            "Youtube Video Privacy": "PUBLIC",
            "Youtube video for kids": "false",
            "Youtube AI generated content": "false",
            "Youtube notify subscribers": "true",
            "Youtube Video Category": "SHOPPING",
            "Youtube Video Tags": tags(desc),
            "GBP Post Type": "PUBLICATION",
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
            "LinkedIn Type": "POST",
            "LinkedIn Show link preview": "true",
            "LinkedIn Images as Carousel": "false",
            "Threads Reply Control": "EVERYONE",
            "Threads Is Spoiler": "false",
            "Threads Post Type": "POST",
        })

        # Keep the original video URL in the first comment when available.
        if video:
            out["First Comment Text"] = f"{link}\n🎥 Video: {video}"

        rows_out.append(out)

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows_out)

print(f"Input: {INPUT.name}")
print(f"Output: {OUTPUT.name}")
print(f"Products exported: {len(rows_out)}")
