# Facebook Comment Publisher

برنامج Windows مستقل للتعليق على روابط منشورات Facebook باستعمال Meta Graph API. لا يغيّر Blogger أو Partage Social أو أي مشروع آخر.

## التشغيل
1. نزّل المجلد كاملاً.
2. شغّل `RUN.bat`.
3. أدخل User Access Token ثم اضغط **اختبار Token وجلب الصفحات**.
4. اختَر صفحة واحدة أو عدة صفحات (Ctrl أو Shift). يمكن إضافة Page ID وPage Access Token يدوياً.
5. اختَر CSV واضغط **START COMMENTING**.

## CSV — ثلاثة أعمدة فقط
```csv
Photo_Link,Facebook_Link,Comment
https://example.com/photo.jpg,https://www.facebook.com/...,تعليق تجريبي
```
- `Photo_Link`: اختياري؛ رابط صورة عام يمكن إرفاقه بالتعليق إذا قبلته Meta.
- `Facebook_Link`: رابط منشور Facebook المستهدف.
- `Comment`: نص التعليق.

## استقلال الصفحات
- كل صفحة عندها ملف حالة مستقل داخل `data/state/<PAGE_ID>.json` لمنع إعادة إرسال نفس السطر بعد نجاحه.
- نتائج كل صفحة تحفظ مستقلة داخل `output`.
- اختيار عدة صفحات يعني أن البرنامج يحاول تنفيذ أسطر CSV نفسها لكل صفحة مختارة.
- إعدادات الصفحات والتوكنات تحفظ محلياً داخل `data/settings.json` على حاسوبك. لا ترفع هذا الملف إلى GitHub ولا تشاركه.

## صلاحيات Meta وحدودها
- جلب الصفحات يتطلب User Access Token مع صلاحية مثل `pages_show_list`.
- التعليق يتطلب Page Access Token وصلاحيات Meta المناسبة، وغالباً `pages_manage_engagement` وصلاحيات قراءة/وصول مناسبة للصفحة.
- Meta قد ترفض التعليق على منشورات لا تديرها الصفحة أو لا تسمح بها الصلاحيات أو نوع المنشور. وجود Token لا يضمن قبول كل تعليق.
- البرنامج يتعامل مع روابط المنشورات التي يمكن استخراج Graph object ID منها. بعض روابط `pfbid` والروابط المختصرة لا تكشف ID رقمي، وقد تحتاج رابطاً آخر.
- `Photo_Link` يُرسل كـ `attachment_url`؛ إذا رفضته Meta سيظهر سبب الفشل في ملف النتائج.

## الملفات
- `RUN.bat`: تشغيل البرنامج.
- `comments_template.csv`: نموذج CSV.
- `data/settings.json`: إعدادات الصفحات محلياً (حساس).
- `data/state`: سجل مستقل لكل صفحة.
- `output`: نتائج كل صفحة.

استعمله للتعليقات الملائمة فقط، وتجنب التكرار والإزعاج واحترم قيود Meta.
