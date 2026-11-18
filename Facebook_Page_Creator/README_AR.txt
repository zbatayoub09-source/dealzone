Facebook Page Creator — تجهيز CSV باستعمال Gemini API

المجلد مستقل عن project-blogger وباقي مشاريع DealZone.

التشغيل:
1) نزّل مجلد Facebook_Page_Creator كاملاً.
2) افتح RUN_PAGE_CREATOR.bat.
3) دخل Gemini API Key في الخانة الأولى.
4) اضغط «اختيار CSV» واختَر الملف الذي تريد تعمير بياناته.
5) اضغط «إنشاء CSV بالذكاء الاصطناعي».
6) انتظر حتى يكمل؛ تقدر تضغط «إلغاء / إيقاف» لإيقاف المعالجة بعد الطلب الجاري.
7) تلقى ملفاً جديداً بجانب CSV الأصلي، اسمه فيه _gemini_filled_ والتاريخ.

الأعمدة التي ينتجها الملف:
Page Name, Username, Bio, Description, Category, Profile Image Prompt, Cover Image Prompt, Keywords

مهم:
- يمكنك اختيار CSV القالب pages_template.csv الذي يحتوي على 100 سطر.
- Gemini يعيد إنشاء محتوى كل سطر اعتماداً على المعلومات الموجودة فيه كموضوع/إلهام.
- يتم حفظ النتيجة تدريجياً بعد كل سطر، حتى لا تضيع الصفحات التي تم تجهيزها إذا أوقفت العمل.
- يحفظ البرنامج أسماء الصفحات المستعملة في used_page_names.json داخل هذا المجلد لمنع تكرارها في التشغيلات التالية على نفس الكمبيوتر.
- مفتاح API يبقى في ذاكرة البرنامج أثناء التشغيل فقط، ولا يكتب داخل CSV أو ملفات GitHub.
- استعمال Gemini API قد يخضع للحصة المجانية أو الفوترة وحدود السرعة حسب حساب Google؛ راجع لوحة AI Studio.
- الأداة تجهز محتوى CSV فقط؛ لا تنشئ صفحات Facebook ولا تنشرها تلقائياً.
- لا ترفع API Key إلى GitHub ولا ترسله لأي شخص.

إنشاء API Key:
https://aistudio.google.com/app/apikey

معلومات Gemini API الرسمية:
https://ai.google.dev/gemini-api/docs/get-started
