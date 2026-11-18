# DealZone — Facebook CSV Publisher

برنامج Windows مستقل لنشر CSV في صفحة Facebook واحدة أو عدة صفحات باستعمال Meta Graph API.

## التشغيل
1. نزّل مجلد `Facebook_Page_Creator` كاملاً من GitHub.
2. شغّل `RUN.bat`.
3. ضع **Facebook User Access Token** في الخانة الأولى.
4. اضغط **اختبار Token وجلب الصفحات**.
5. اختَر صفحة أو عدة صفحات (Ctrl/Shift).
6. اختَر CSV واضغط **START PUBLISHING**.

## أعمدة CSV
- `Post Message` (أو `Message`) — نص المنشور.
- `Image URL` — رابط صورة مباشر، اختياري.
- `Image Path` — مسار صورة محلية، اختياري. يمكن أن يكون المسار نسبياً من نفس مجلد CSV.
- `Comment` — تعليق يُنشر بعد نجاح المنشور، اختياري.

يمكن استعمال `Image` كاسم بديل لعمود الصورة. إذا كانت الصورة موجودة، ينشر البرنامج الصورة مع النص في ألبوم/منشور الصور؛ إذا لم توجد صورة ينشر النص في Feed.

## النتائج
ينشئ ملفاً جديداً بجانب CSV الأصلي باسم `*_facebook_results.csv` ويكتب لكل صفحة ولكل سطر حالة النشر وPost ID وأي خطأ. لا يغيّر CSV الأصلي.

## صلاحيات Meta
يحتاج User Access Token إلى صلاحية `pages_show_list`، ويحتاج النشر عادةً `pages_manage_posts` و`pages_read_engagement`، مع مهمة مناسبة مثل `CREATE_CONTENT` على الصفحة. إتاحة الصلاحيات تعتمد على وضع تطبيق Meta ومراجعته وإعدادات الصفحة. قد يرفض Meta النشر حتى مع Token صالح إذا كانت الصلاحيات أو المهام غير كافية.

## الأمان
- Token يُدخل محلياً في واجهة البرنامج ولا يُحفظ في GitHub أو ملف إعدادات.
- لا ترسل Token في المحادثة ولا تضعه داخل CSV.
- لا يطلب البرنامج كلمة مرور Facebook.
- هذا البرنامج ينشر في الصفحات التي يتيحها Token؛ لا ينشئ صفحات Facebook جديدة تلقائياً.

Graph API Explorer: https://developers.facebook.com/tools/explorer/
