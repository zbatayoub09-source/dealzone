DealZone — Facebook CSV Publisher

البرنامج مستقل داخل Facebook_Page_Creator. لا يغيّر project-blogger أو Partage Social أو أي مشروع قديم.

طريقة التشغيل:
1) نزّل مجلد Facebook_Page_Creator كاملاً.
2) شغّل RUN.bat.
3) إذا عندك User Access Token، ضعه في الخانة الأولى واضغط "اختبار Token وجلب الصفحات".
4) أو دخل Page ID و Page Access Token في الخانات اليدوية واضغط "إضافة الصفحة يدوياً". كرر العملية لإضافة عدة صفحات.
5) اختَر صفحة أو عدة صفحات باستعمال Ctrl أو Shift.
6) اختَر CSV.
7) اضغط START PUBLISHING وأكد العملية.

أعمدة CSV:
- Post Message أو Message: نص المنشور.
- Image URL: رابط الصورة المباشر (اختياري).
- Image Path: مسار صورة محلية (اختياري). المسار النسبي يُحسب انطلاقاً من مجلد CSV.
- Comment: التعليق الذي سينشر بعد نجاح المنشور (اختياري).

يمكن استعمال Image كاسم بديل لعمود الصورة. إذا كانت هناك صورة، ينشرها البرنامج مع النص. إذا لم توجد صورة، ينشر النص في Feed. بعد النجاح ينشر Comment إن كان موجوداً.

النتائج:
ينشئ ملفاً جديداً بجانب CSV الأصلي باسم *_facebook_results.csv. يحتوي اسم الصفحة وPage ID ورقم سطر CSV وPost ID والحالة والخطأ. CSV الأصلي لا يتغير.

الصلاحيات:
يلزم User Access Token بصلاحية pages_show_list لجلب الصفحات. أما Page Access Token فيحتاج عادة pages_manage_posts وpages_read_engagement ومهمة CREATE_CONTENT أو مهمة نشر مناسبة على الصفحة. صلاحيات Meta مرتبطة بإعداد التطبيق ومراجعته، وقد يرفض Meta الطلب إذا لم تكن الصلاحيات متاحة.

الأمان:
- Token يبقى في ذاكرة البرنامج ولا يُحفظ في GitHub أو ملف.
- لا ترسل Token في المحادثة أو CSV.
- لا تدخل كلمة مرور Facebook.
- البرنامج لا ينشئ صفحات جديدة؛ ينشر فقط في الصفحات التي عندك صلاحية النشر فيها.

Graph API Explorer: https://developers.facebook.com/tools/explorer/
