Facebook Page Creator — أداة مستقلة لتجهيز صفحات Facebook من CSV

المجلد مستقل تماماً عن project-blogger وباقي مشاريع DealZone.

التشغيل السريع:
1) فك ضغط/نزّل مجلد Facebook_Page_Creator كاملاً.
2) افتح RUN_PAGE_CREATOR.bat بنقرتين.
3) اضغط «تحميل CSV واختيار الأعمدة».
4) اختر pages_template.csv أو CSV ديالك.
5) راجع ربط الأعمدة (الأداة تتعرف تلقائياً على القالب المرفق).
6) اضغط «تجهيز جميع الصفحات من CSV».
7) ستجد ملف كل صفحة داخل prepared_pages، وفيه page_info.json وabout.txt.

أعمدة CSV المرفق:
Page Name, Username, Bio, Description, Category, Profile Image Prompt, Cover Image Prompt, Keywords

تقدر تزيد أعمدة أخرى أو تستعمل CSV مختلفاً؛ اختَر العمود المناسب لكل خانة من نافذة الربط. اسم الصفحة ضروري، وباقي الخانات اختيارية.

الصور:
- Profile Image Prompt وCover Image Prompt هما وصفان لتوليد الصور، ولا ينشئ البرنامج الصور تلقائياً.
- لإضافة صورة فعلية، استعمل عمود profile_image بمسار الصورة أو اختَر صورة مشتركة من داخل البرنامج.
- يمكن اختيار صورة غلاف مشتركة من داخل البرنامج.

مهم:
- البرنامج يجهز معلومات الصفحات محلياً فقط.
- لا ينشئ صفحات Facebook ولا ينشر أي شيء تلقائياً.
- راجع أسماء الصفحات وتوفرها وسياسات Meta قبل إنشاء الصفحة يدوياً.
- لا يغيّر أي ملف في project-blogger أو إعدادات Facebook.
- يحتاج Python 3 مع Tkinter فقط، ولا يحتاج مكتبات pip إضافية.
