from flask import Flask, request, redirect, url_for, render_template_string, flash, send_file
import sqlite3, csv, io, os, webbrowser, threading, time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "dealzone_manager.db"
app = Flask(__name__)
app.secret_key = "change-this-local-key"

STATUSES = ["جديد", "تم التأكيد", "تم الشراء من المورد", "تم الشحن", "تم التسليم", "ملغى", "مرتجع"]

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT, title TEXT NOT NULL,
            image_url TEXT, description TEXT, buy_price REAL DEFAULT 0, sell_price REAL DEFAULT 0,
            shipping_cost REAL DEFAULT 0, supplier_url TEXT, category TEXT, active INTEGER DEFAULT 1,
            created_at TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, customer_name TEXT NOT NULL,
            phone TEXT NOT NULL, city TEXT, address TEXT, quantity INTEGER DEFAULT 1,
            sell_price REAL DEFAULT 0, supplier_cost REAL DEFAULT 0, delivery_cost REAL DEFAULT 0,
            status TEXT DEFAULT 'جديد', tracking TEXT, notes TEXT, created_at TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id))""")

def money(v):
    try: return float(str(v or "0").replace(",", ".").replace(" ", ""))
    except: return 0.0

PAGE = r"""
<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DealZone Manager</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f9;color:#172033;font-family:Tahoma,Arial,sans-serif}
header{background:#172033;color:white;padding:18px 5%;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
header b{font-size:23px;color:#ff665e}.wrap{max-width:1200px;margin:24px auto;padding:0 16px}
nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}a.btn,button,.btn{border:0;background:#ff665e;color:white;padding:10px 15px;border-radius:9px;text-decoration:none;cursor:pointer;font-weight:bold}
a.secondary,.secondary{background:#e5e9f1;color:#243047}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:13px;margin:15px 0}
.card{background:white;border-radius:14px;padding:17px;box-shadow:0 3px 15px #18243a0b}.num{font-size:25px;font-weight:bold;margin-top:8px}
table{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden}th,td{padding:11px;border-bottom:1px solid #edf0f4;text-align:right;font-size:13px}th{background:#edf1f7}
input,textarea,select{width:100%;padding:10px;border:1px solid #d9deea;border-radius:8px;background:white;font:inherit;margin:5px 0 12px}
label{font-size:13px;font-weight:bold}.formgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
h2{margin-top:8px}.muted{color:#718096;font-size:12px}.flash{background:#fff1d6;padding:12px;border-radius:9px;margin:10px 0}
.profit{color:#13834d;font-weight:bold}.danger{background:#b83d48}.actions{display:flex;gap:6px;flex-wrap:wrap}
img.thumb{width:48px;height:48px;object-fit:cover;border-radius:7px} .scroll{overflow:auto}
</style></head><body><header><b>DealZone Manager</b><span>لوحة تسيير المتجر — محلياً على حاسوبك</span></header>
<div class="wrap"><nav><a class="btn" href="/">الرئيسية</a><a class="btn secondary" href="/products">المنتجات</a><a class="btn secondary" href="/orders">الطلبات</a><a class="btn secondary" href="/import">استيراد CSV</a><a class="btn secondary" href="/export">تصدير CSV</a></nav>
{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}
{{body|safe}}</div></body></html>
"""

def page(body, **ctx):
    return render_template_string(PAGE, body=render_template_string(body, **ctx))

@app.route("/")
def home():
    with db() as con:
        p=con.execute("SELECT COUNT(*) n FROM products").fetchone()["n"]
        o=con.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
        pending=con.execute("SELECT COUNT(*) n FROM orders WHERE status NOT IN ('تم التسليم','ملغى','مرتجع')").fetchone()["n"]
        rows=con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 8").fetchall()
        totals=con.execute("SELECT COALESCE(SUM((sell_price-supplier_cost-delivery_cost)*quantity),0) v FROM orders WHERE status='تم التسليم'").fetchone()["v"]
    body="""<h2>ملخص المتجر</h2><div class="grid">
    <div class="card">عدد المنتجات<div class="num">{{p}}</div></div><div class="card">مجموع الطلبات<div class="num">{{o}}</div></div>
    <div class="card">طلبات قيد المعالجة<div class="num">{{pending}}</div></div><div class="card">الربح المحسوب للطلبات المسلمة<div class="num profit">{{'%.2f'|format(totals)}} DH</div></div></div>
    <h2>آخر الطلبات</h2><div class="scroll"><table><tr><th>#</th><th>الزبون</th><th>الهاتف</th><th>المدينة</th><th>الحالة</th><th></th></tr>
    {% for r in rows %}<tr><td>{{r.id}}</td><td>{{r.customer_name}}</td><td>{{r.phone}}</td><td>{{r.city or ''}}</td><td>{{r.status}}</td><td><a href="/orders/{{r.id}}">فتح</a></td></tr>{% else %}<tr><td colspan="6">لا توجد طلبات بعد</td></tr>{% endfor %}</table></div>
    <p class="muted">الربح هنا تقديري: ثمن البيع ناقص تكلفة المورد والتوصيل، ولا يشمل رسوم الأداء أو الجمارك أو المرتجعات إلا إذا أضفتها في المصاريف.</p>"""
    return page(body,p=p,o=o,pending=pending,totals=totals,rows=rows)

@app.route("/products")
def products():
    with db() as con: rows=con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    body="""<div class="actions"><h2 style="flex:1">المنتجات</h2><a class="btn" href="/products/new">+ إضافة منتج</a></div><div class="scroll"><table>
    <tr><th>الصورة</th><th>المنتج</th><th>شراء</th><th>بيع</th><th>ربح قبل المصاريف</th><th>المورد</th><th></th></tr>
    {% for r in rows %}<tr><td>{% if r.image_url %}<img class="thumb" src="{{r.image_url}}">{% endif %}</td><td>{{r.title}}</td><td>{{'%.2f'|format(r.buy_price)}} DH</td><td>{{'%.2f'|format(r.sell_price)}} DH</td><td class="profit">{{'%.2f'|format(r.sell_price-r.buy_price-r.shipping_cost)}} DH</td><td>{% if r.supplier_url %}<a target="_blank" href="{{r.supplier_url}}">رابط المورد</a>{% endif %}</td><td><a href="/products/{{r.id}}/edit">تعديل</a></td></tr>{% else %}<tr><td colspan="7">مازال ما ضفتي حتى منتج.</td></tr>{% endfor %}</table></div>"""
    return page(body,rows=rows)

PRODUCT_FORM = """<h2>{{heading}}</h2><form method="post"><div class="formgrid">
<div><label>اسم المنتج *</label><input name="title" required value="{{r.title or ''}}"></div>
<div><label>ProductId</label><input name="product_id" value="{{r.product_id or ''}}"></div>
<div><label>رابط الصورة</label><input name="image_url" value="{{r.image_url or ''}}"></div>
<div><label>التصنيف</label><input name="category" value="{{r.category or ''}}"></div>
<div><label>ثمن الشراء (DH)</label><input name="buy_price" type="number" step="0.01" value="{{r.buy_price or 0}}"></div>
<div><label>ثمن البيع (DH)</label><input name="sell_price" type="number" step="0.01" value="{{r.sell_price or 0}}"></div>
<div><label>مصاريف التوصيل المقدرة (DH)</label><input name="shipping_cost" type="number" step="0.01" value="{{r.shipping_cost or 0}}"></div>
<div><label>رابط المورد</label><input name="supplier_url" value="{{r.supplier_url or ''}}"></div></div>
<label>الوصف</label><textarea name="description" rows="4">{{r.description or ''}}</textarea>
<button type="submit">حفظ المنتج</button> <a class="btn secondary" href="/products">رجوع</a></form>"""

@app.route("/products/new", methods=["GET","POST"])
def new_product():
    if request.method=="POST":
        f=request.form
        with db() as con: con.execute("""INSERT INTO products(product_id,title,image_url,description,buy_price,sell_price,shipping_cost,supplier_url,category,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (f.get("product_id"),f["title"],f.get("image_url"),f.get("description"),money(f.get("buy_price")),money(f.get("sell_price")),money(f.get("shipping_cost")),f.get("supplier_url"),f.get("category"),datetime.now().isoformat(timespec="seconds")))
        flash("تم حفظ المنتج.")
        return redirect(url_for("products"))
    return page(PRODUCT_FORM,heading="إضافة منتج",r={})

@app.route("/products/<int:pid>/edit", methods=["GET","POST"])
def edit_product(pid):
    with db() as con: r=con.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    if not r: return "Product not found",404
    if request.method=="POST":
        f=request.form
        with db() as con: con.execute("""UPDATE products SET product_id=?,title=?,image_url=?,description=?,buy_price=?,sell_price=?,shipping_cost=?,supplier_url=?,category=? WHERE id=?""",
        (f.get("product_id"),f["title"],f.get("image_url"),f.get("description"),money(f.get("buy_price")),money(f.get("sell_price")),money(f.get("shipping_cost")),f.get("supplier_url"),f.get("category"),pid))
        flash("تم تحديث المنتج.")
        return redirect(url_for("products"))
    return page(PRODUCT_FORM,heading="تعديل المنتج",r=r)

@app.route("/orders")
def orders():
    with db() as con: rows=con.execute("SELECT orders.*, products.title product_title FROM orders LEFT JOIN products ON products.id=orders.product_id ORDER BY orders.id DESC").fetchall()
    body="""<div class="actions"><h2 style="flex:1">الطلبات</h2><a class="btn" href="/orders/new">+ تسجيل طلب</a></div><div class="scroll"><table>
    <tr><th>#</th><th>الزبون</th><th>المنتج</th><th>الهاتف</th><th>المدينة</th><th>الكمية</th><th>الحالة</th><th></th></tr>
    {% for r in rows %}<tr><td>{{r.id}}</td><td>{{r.customer_name}}</td><td>{{r.product_title or 'غير محدد'}}</td><td>{{r.phone}}</td><td>{{r.city or ''}}</td><td>{{r.quantity}}</td><td>{{r.status}}</td><td><a href="/orders/{{r.id}}">إدارة</a></td></tr>{% else %}<tr><td colspan="8">لا توجد طلبات.</td></tr>{% endfor %}</table></div>"""
    return page(body,rows=rows)

@app.route("/orders/new", methods=["GET","POST"])
def new_order():
    with db() as con: products=con.execute("SELECT * FROM products ORDER BY title").fetchall()
    if request.method=="POST":
        f=request.form
        with db() as con: con.execute("""INSERT INTO orders(product_id,customer_name,phone,city,address,quantity,sell_price,supplier_cost,delivery_cost,status,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (int(f["product_id"]) if f.get("product_id") else None,f["customer_name"],f["phone"],f.get("city"),f.get("address"),max(1,int(f.get("quantity") or 1)),money(f.get("sell_price")),money(f.get("supplier_cost")),money(f.get("delivery_cost")),f.get("status","جديد"),f.get("notes"),datetime.now().isoformat(timespec="seconds")))
        flash("تم تسجيل الطلب.")
        return redirect(url_for("orders"))
    body="""<h2>تسجيل طلب زبون</h2><form method="post"><div class="formgrid">
    <div><label>المنتج</label><select name="product_id" id="prod"><option value="">اختياري</option>{% for p in products %}<option value="{{p.id}}" data-sell="{{p.sell_price}}" data-buy="{{p.buy_price}}" data-ship="{{p.shipping_cost}}">{{p.title}}</option>{% endfor %}</select></div>
    <div><label>اسم الزبون *</label><input name="customer_name" required></div><div><label>الهاتف *</label><input name="phone" required></div>
    <div><label>المدينة</label><input name="city"></div><div><label>العنوان</label><input name="address"></div><div><label>الكمية</label><input name="quantity" type="number" min="1" value="1"></div>
    <div><label>ثمن البيع للزبون (DH)</label><input name="sell_price" id="sell" type="number" step=".01" value="0"></div>
    <div><label>تكلفة المورد (DH)</label><input name="supplier_cost" id="buy" type="number" step=".01" value="0"></div>
    <div><label>التوصيل (DH)</label><input name="delivery_cost" id="ship" type="number" step=".01" value="0"></div>
    <div><label>الحالة</label><select name="status">{% for s in statuses %}<option>{{s}}</option>{% endfor %}</select></div></div>
    <label>ملاحظات</label><textarea name="notes"></textarea><button>حفظ الطلب</button> <a class="btn secondary" href="/orders">رجوع</a></form>
    <script>document.getElementById('prod').addEventListener('change',e=>{let o=e.target.selectedOptions[0];if(o.dataset.sell!==undefined){document.getElementById('sell').value=o.dataset.sell;document.getElementById('buy').value=o.dataset.buy;document.getElementById('ship').value=o.dataset.ship}})</script>"""
    return page(body,products=products,statuses=STATUSES)

@app.route("/orders/<int:oid>", methods=["GET","POST"])
def edit_order(oid):
    with db() as con: r=con.execute("SELECT orders.*,products.title product_title FROM orders LEFT JOIN products ON products.id=orders.product_id WHERE orders.id=?",(oid,)).fetchone()
    if not r: return "Order not found",404
    if request.method=="POST":
        f=request.form
        with db() as con: con.execute("UPDATE orders SET status=?,tracking=?,sell_price=?,supplier_cost=?,delivery_cost=?,notes=? WHERE id=?",
        (f.get("status"),f.get("tracking"),money(f.get("sell_price")),money(f.get("supplier_cost")),money(f.get("delivery_cost")),f.get("notes"),oid))
        flash("تم تحديث الطلب.")
        return redirect(url_for("edit_order",oid=oid))
    profit=(r["sell_price"]-r["supplier_cost"]-r["delivery_cost"])*r["quantity"]
    body="""<h2>طلب رقم #{{r.id}}</h2><div class="card"><b>{{r.customer_name}}</b> — {{r.phone}}<p>{{r.product_title or ''}} | {{r.city or ''}} | {{r.address or ''}}</p><p>الكمية: {{r.quantity}} | الربح المتوقع: <b class="profit">{{'%.2f'|format(profit)}} DH</b></p></div>
    <form method="post"><div class="formgrid"><div><label>الحالة</label><select name="status">{% for s in statuses %}<option {% if s==r.status %}selected{% endif %}>{{s}}</option>{% endfor %}</select></div>
    <div><label>رقم التتبع</label><input name="tracking" value="{{r.tracking or ''}}"></div>
    <div><label>ثمن البيع</label><input name="sell_price" type="number" step=".01" value="{{r.sell_price}}"></div>
    <div><label>تكلفة المورد</label><input name="supplier_cost" type="number" step=".01" value="{{r.supplier_cost}}"></div>
    <div><label>التوصيل</label><input name="delivery_cost" type="number" step=".01" value="{{r.delivery_cost}}"></div></div>
    <label>ملاحظات</label><textarea name="notes">{{r.notes or ''}}</textarea><button>تحديث الطلب</button> <a class="btn secondary" href="/orders">رجوع</a></form>"""
    return page(body,r=r,profit=profit,statuses=STATUSES)

@app.route("/import", methods=["GET","POST"])
def import_csv():
    if request.method=="POST":
        f=request.files.get("file")
        if not f: flash("اختار ملف CSV."); return redirect(url_for("import_csv"))
        try:
            raw=f.stream.read().decode("utf-8-sig")
            sample=raw[:4096]
            try: dialect=csv.Sniffer().sniff(sample,delimiters=",;\t")
            except: dialect=csv.excel
            reader=csv.DictReader(io.StringIO(raw),dialect=dialect)
            count=0
            def pick(row,*names):
                low={str(k).strip().lower():v for k,v in row.items() if k}
                for n in names:
                    if n.lower() in low and low[n.lower()] not in (None,""): return low[n.lower()]
                return ""
            with db() as con:
                for row in reader:
                    title=pick(row,"Product Desc","title","name","product name","ProductName")
                    if not title: continue
                    con.execute("""INSERT INTO products(product_id,title,image_url,description,buy_price,sell_price,shipping_cost,supplier_url,category,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (pick(row,"ProductId","product_id","id"),title,pick(row,"Image/Video Url","Image Url","Image","image_url"),pick(row,"description","Product Desc"),money(pick(row,"BuyPrice","Buy Price","Origin Price","buy_price")),money(pick(row,"SellPrice","Sell Price","sell_price")),money(pick(row,"ShippingCost","Shipping Cost")),pick(row,"SupplierUrl","Supplier URL","Promotion Url"),pick(row,"Category","category"),datetime.now().isoformat(timespec="seconds")))
                    count+=1
            flash(f"تم استيراد {count} منتج. راجع أثمنة الشراء والبيع قبل النشر.")
        except Exception as e: flash("تعذر قراءة الملف: "+str(e))
        return redirect(url_for("products"))
    body="""<h2>استيراد CSV</h2><div class="card"><p>يمكن استيراد ملف CSV قديم. التطبيق يحاول قراءة ProductId وProduct Desc وImage/Video Url أو Image Url.</p>
    <p><b>مهم:</b> Origin Price قد يكون ثمن المورد، لكن SellPrice لن يُخمن. بعد الاستيراد راجع وأدخل ثمن البيع الصحيح لكل منتج.</p>
    <form method="post" enctype="multipart/form-data"><input type="file" name="file" accept=".csv" required><button>استيراد المنتجات</button></form></div>"""
    return page(body)

@app.route("/export")
def export_csv():
    with db() as con: rows=con.execute("SELECT * FROM products ORDER BY id").fetchall()
    output=io.StringIO()
    fields=["ProductId","Product Desc","Image Url","BuyPrice","SellPrice","ShippingCost","Profit","SupplierUrl","Category"]
    w=csv.DictWriter(output,fieldnames=fields); w.writeheader()
    for r in rows:
        w.writerow({"ProductId":r["product_id"],"Product Desc":r["title"],"Image Url":r["image_url"],"BuyPrice":r["buy_price"],"SellPrice":r["sell_price"],"ShippingCost":r["shipping_cost"],"Profit":r["sell_price"]-r["buy_price"]-r["shipping_cost"],"SupplierUrl":r["supplier_url"],"Category":r["category"]})
    data=io.BytesIO(output.getvalue().encode("utf-8-sig")); data.seek(0)
    return send_file(data,mimetype="text/csv",as_attachment=True,download_name="dealzone_products.csv")

if __name__ == "__main__":
    init_db()
    url="http://127.0.0.1:5055"
    threading.Timer(1.2,lambda:webbrowser.open(url)).start()
    print("DealZone Manager: "+url)
    app.run(host="127.0.0.1",port=5055,debug=False)
