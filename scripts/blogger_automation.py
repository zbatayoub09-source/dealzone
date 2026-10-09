import csv, hashlib, html, json, os, re, sys, time
from pathlib import Path
import requests

ROOT=Path(".")
OUT=ROOT/"generated"
STATE=ROOT/".automation"/"blogger_state.json"
BLOG_ID=os.getenv("BLOGGER_BLOG_ID","1419305768199826334")
BATCH=max(1,int(os.getenv("BLOGGER_BATCH_SIZE","5")))
API="https://www.googleapis.com/blogger/v3"

def get(row,*names):
    data={str(k).strip().lower():(v or "").strip() for k,v in row.items() if k}
    for n in names:
        if data.get(n.lower()): return data[n.lower()]
    return ""

def csv_files():
    files=[p for p in ROOT.glob("*.csv") if p.is_file() and not p.stem.lower().endswith("_seo")]
    for folder in (ROOT/"data",ROOT/"csv"):
        if folder.exists(): files += [p for p in folder.glob("*.csv") if not p.stem.lower().endswith("_seo")]
    return sorted(set(files),key=lambda p:p.as_posix().lower())

def read_csv(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        sample=f.read(8192); f.seek(0)
        try: dialect=csv.Sniffer().sniff(sample,delimiters=",;\t|")
        except csv.Error: dialect=csv.excel
        reader=csv.DictReader(f,dialect=dialect)
        return list(reader.fieldnames or []),list(reader)

def pid(row,path,n):
    return get(row,"ProductId","Product ID","Item ID","product_id","id") or f"{path.stem}-{n}"

def seo(row,path):
    title=get(row,"SEO_Title","Product Desc","Title","Product Title","Name","Product Name") or "AliExpress product"
    title=re.sub(r"\s+"," ",title).strip()[:150]
    category=path.stem.replace("_"," ").replace("-"," ")
    price=get(row,"Discount Price","Sale Price","Price")
    currency=get(row,"Currency")
    link=get(row,"Promotion Url","Product Url","Product URL","Affiliate Link","Link","URL")
    price_text=f"Check the current listed price ({currency} {price})" if price and currency else (f"Check the current listed price ({price})" if price else "Check the current listed price")
    desc=f"Discover {title} in our {category} collection. {price_text}; review product specifications, shipping options, and seller information before ordering. Prices, availability, offers, and delivery times can change, so confirm the latest details on the seller's page."
    if link: desc+=" View the current offer using the product link."
    stop={"with","from","for","and","the","new","hot","sale","free","set","pcs","piece"}
    tags=[]
    for w in re.findall(r"[A-Za-z0-9]+",title.lower()):
        if len(w)>=3 and w not in stop and "#"+w not in tags: tags.append("#"+w)
        if len(tags)>=4: break
    for t in ("#AliExpress","#OnlineShopping","#"+re.sub(r"[^A-Za-z0-9]","",category.title())):
        if t!="#" and t.lower() not in [x.lower() for x in tags]: tags.append(t)
    keywords=", ".join(dict.fromkeys([title]+[w for w in re.findall(r"[A-Za-z0-9]+",title) if len(w)>2][:8]+[category]))
    return {"SEO_Title":title,"SEO_Description":desc[:1000],"SEO_Keywords":keywords[:500],"Hashtags":" ".join(tags[:7])}

def generate_seo():
    OUT.mkdir(parents=True,exist_ok=True); total=0
    for path in csv_files():
        fields,rows=read_csv(path)
        if not fields: continue
        added=["SEO_Title","SEO_Description","SEO_Keywords","Hashtags"]
        out_fields=fields+[x for x in added if x not in fields]
        target=OUT/(path.stem+"_SEO.csv")
        with target.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=out_fields,extrasaction="ignore"); writer.writeheader()
            for row in rows:
                for k,v in seo(row,path).items():
                    if not (row.get(k) or "").strip(): row[k]=v
                writer.writerow(row); total+=1
        print(f"SEO generated: {target} ({len(rows)} rows)")
    print(f"SEO complete: {total} rows")

def state_read():
    STATE.parent.mkdir(parents=True,exist_ok=True)
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {"published":{}}

def state_save(state):
    STATE.parent.mkdir(parents=True,exist_ok=True)
    state["last_updated"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

def token():
    keys=["BLOGGER_CLIENT_ID","BLOGGER_CLIENT_SECRET","BLOGGER_REFRESH_TOKEN"]
    missing=[k for k in keys if not os.getenv(k)]
    if missing: raise RuntimeError("Missing GitHub Actions secrets: "+", ".join(missing))
    r=requests.post("https://oauth2.googleapis.com/token",data={"client_id":os.environ[keys[0]],"client_secret":os.environ[keys[1]],"refresh_token":os.environ[keys[2]],"grant_type":"refresh_token"},timeout=30)
    if not r.ok: raise RuntimeError(f"Google OAuth refresh failed ({r.status_code}): {r.text[:400]}")
    return r.json()["access_token"]

def api(method,url,bearer,**kwargs):
    headers=kwargs.pop("headers",{})
    headers["Authorization"]="Bearer "+bearer
    headers.setdefault("Content-Type","application/json")
    r=requests.request(method,url,headers=headers,timeout=45,**kwargs)
    if r.status_code==429 or r.status_code>=500:
        time.sleep(8); r=requests.request(method,url,headers=headers,timeout=45,**kwargs)
    if not r.ok: raise RuntimeError(f"Blogger API {method} {r.status_code}: {r.text[:400]}")
    return r.json() if r.text.strip() else {}

def fingerprint(row,seo_data):
    return hashlib.sha256(json.dumps({"row":row,"seo":seo_data},sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def body_html(row,s,pid_value):
    title=s["SEO_Title"]
    image=get(row,"Image Url","Image URL","Image","ImageURL","Product Image")
    link=get(row,"Promotion Url","Product Url","Product URL","Affiliate Link","Link","URL")
    video=get(row,"Video Url","Video URL","Video")
    price=get(row,"Discount Price","Sale Price","Price"); currency=get(row,"Currency")
    desc=get(row,"Product Desc","Description","Product Description")
    out=[f'<p>{html.escape(s["SEO_Description"])}</p>']
    if image.startswith("https://"):
        target=link if link.startswith("http") else image
        out.append(f'<p><a href="{html.escape(target,quote=True)}" rel="nofollow sponsored"><img src="{html.escape(image,quote=True)}" alt="{html.escape(title,quote=True)}" style="max-width:100%;height:auto"></a></p>')
    if desc and desc.lower()!=title.lower(): out.append(f'<h2>Product details</h2><p>{html.escape(desc[:1500])}</p>')
    if price: out.append(f'<p><strong>Listed price:</strong> {html.escape((currency+" ") if currency else "")}{html.escape(price)}. Check the seller page for current details.</p>')
    if link.startswith("http"): out.append(f'<p><a href="{html.escape(link,quote=True)}" rel="nofollow sponsored noopener" target="_blank">Check price and availability on AliExpress ↗</a></p>')
    if video.startswith("https://"): out.append(f'<p><a href="{html.escape(video,quote=True)}" rel="nofollow noopener" target="_blank">Watch product video ↗</a></p>')
    out += [f'<p><strong>Keywords:</strong> {html.escape(s["SEO_Keywords"])}</p>',f'<p>{html.escape(s["Hashtags"])}</p>','<hr><p><small>Disclosure: This page may contain affiliate links. If you buy through them, we may earn a commission at no extra cost to you. Product prices, availability, shipping, and specifications are controlled by the seller and may change.</small></p>',f'<!-- DEALZONE_PRODUCT_ID:{html.escape(str(pid_value))} -->']
    return "\n".join(out)

def publish():
    bearer=token(); state=state_read(); published=state.setdefault("published",{}); queue=[]
    for path in csv_files():
        _,rows=read_csv(path)
        for n,row in enumerate(rows,start=2):
            product=pid(row,path,n)
            title=get(row,"SEO_Title","Product Desc","Title","Product Title","Name","Product Name")
            link=get(row,"Promotion Url","Product Url","Product URL","Affiliate Link","Link","URL")
            if not title or not link.startswith("http"): continue
            s=seo(row,path); fp=fingerprint(row,s); old=published.get(str(product),{})
            if old.get("fingerprint")==fp and old.get("post_id"): continue
            queue.append((path,n,row,product,s,fp,old))
            if len(queue)>=BATCH: break
        if len(queue)>=BATCH: break
    if not queue: print("No new or changed products to publish."); state_save(state); return
    for path,n,row,product,s,fp,old in queue:
        category=re.sub(r"[^A-Za-z0-9 -]","",path.stem.replace("_"," ")).strip()[:50] or "Products"
        post={"kind":"blogger#post","blog":{"id":BLOG_ID},"title":s["SEO_Title"][:150],"content":body_html(row,s,product),"labels":[category,"AliExpress","DealZone"]}
        if old.get("post_id"):
            result=api("PUT",f"{API}/blogs/{BLOG_ID}/posts/{old['post_id']}",bearer,json=post); action="Updated"
        else:
            result=api("POST",f"{API}/blogs/{BLOG_ID}/posts/",bearer,json=post,params={"isDraft":"false"}); action="Published"
        published[str(product)]={"post_id":result.get("id") or old.get("post_id"),"title":s["SEO_Title"],"source":path.name,"fingerprint":fp,"updated":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
        state_save(state)
        print(f"{action}: {product} — {s['SEO_Title']}")
        time.sleep(2)
    print(f"Processed {len(queue)} products.")

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "all"
    if mode in ("seo","all"): generate_seo()
    if mode in ("publish","all"): publish()
    if mode not in ("seo","publish","all"): raise SystemExit("Use seo, publish, or all")
