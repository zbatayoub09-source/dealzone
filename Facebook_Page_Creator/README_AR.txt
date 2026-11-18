Facebook Page Creator — Gemini CSV + Facebook Pages API

هذا المجلد مستقل داخل DealZone ولا يغيّر project-blogger أو Partage Social أو أي مشروع آخر.

التشغيل:
1) نزّل المجلد Facebook_Page_Creator كاملاً.
2) افتح RUN_PAGE_CREATOR.bat.
3) أدخل Gemini API Key إذا بغيت تولّد محتوى CSV.
4) أدخل Facebook User Access Token إذا بغيت تجلب صفحاتك وتنشر فيها.
5) اختر ملف CSV. تقدر تبدأ بـ pages_template.csv.
6) اضغط "إنشاء CSV بالذكاء الاصطناعي" لإنشاء ملف جديد بجانب الملف الأصلي.
7) للنشر: اضغط "جلب صفحاتي"، اختَر الصفحة، ثم "نشر منشورات CSV". سيطلب البرنامج تأكيداً قبل النشر.

أعمدة CSV الناتج:
Page Name, Username, Bio, Description, Category, Profile Image Prompt, Cover Image Prompt, Keywords, Post Message

Gemini:
- يستعمل Gemini REST generateContent مع نموذج gemini-3.8-flash.
- إنشاء المحتوى يحفظ النتائج تدريجياً.
- يحتفظ بأسماء الصفحات التي سبق توليدها في used_page_names.json لمنع تكرارها على نفس الكمبيوتر.
- مفتاح Gemini يبقى في ذاكرة البرنامج فقط.

Facebook / Meta:
- يستعمل Graph API v27.0.
- "جلب صفحاتي" يقرأ /me/accounts ويعرض الصفحات التي يسمح بها User Access Token.
- النشر يستعمل Page Access Token على /{page-id}/feed.
- يلزم عادة pages_show_list وpages_manage_posts وpages_read_engagement، وأن تكون عندك مهمة CREATE_CONTENT على الصفحة. إتاحة الصلاحيات مرتبطة بإعدادات ومراجعة تطبيق Meta.
- أدخل User Access Token بنفسك محلياً في البرنامج. لا ترسله في المحادثة ولا تضفه إلى GitHub.
- لا يتم تخزين أي Facebook Token أو Gemini Key على القرص.

حدود إنشاء صفحات جديدة:
Meta توضح أن إنشاء Page عبر Graph API متاح فقط لمستخدم اختبار أو لتطبيق تمت إضافته إلى قائمة السماح (allowlisted). لذلك هذا البرنامج يجهز CSV ولا يدّعي أنه يستطيع إنشاء صفحات جديدة لكل حساب.

مفاتيح وروابط:
Gemini API Key: https://aistudio.google.com/app/apikey
Meta Graph API Explorer: https://developers.facebook.com/tools/explorer/
توثيق صفحات Meta: https://developers.facebook.com/docs/graph-api/reference/user/accounts/
توثيق النشر: https://developers.facebook.com/docs/graph-api/reference/page/feed/

ملاحظة أمنية:
لا ترفع API Keys أو Access Tokens إلى GitHub. ملف .gitignore يستثني ملف أسماء الصفحات المحلية.
