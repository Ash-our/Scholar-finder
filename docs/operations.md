# دليل التشغيل

نفّذ الأوامر من جذر المشروع. المتطلبات: Python 3.12/3.13 وNode.js 24 وPowerShell 7 على Windows. يستعمل الإعداد `requirements*.lock.txt` و`frontend/package-lock.json` لتثبيت الاعتماديات.

## التشغيل المحلي

```powershell
.\scripts\Setup-Project.ps1
.\scripts\Start-Project.ps1
```

الإعداد يُنشئ `.venv` ويبني الواجهة وينزّل الخدمات المحمولة داخل `.runtime`. بدء المشروع يتحقق من MongoDB وKafka وينشئ الفهارس والمواضيع، ثم يشغّل المعالجة والجمع والتحليل وAPI في الخلفية. يعيد استخدام عمليات المشروع القائمة. الموقع: http://127.0.0.1:8000. السجلات الجديدة تحت `.runtime/logs/` ومعرّفات العمليات في `.runtime/app-processes.json` و`.runtime/services.json`.

العمليات التي بدأت يدويًا أثناء التطوير قد تكتب سجلاتها مباشرة تحت `.runtime`. للاطلاع على البيانات الفعلية:

```powershell
.\.venv\Scripts\python.exe -m scholarship_map.cli stats
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

لا تشغّل عمليتي streaming على نقطة الاستئناف نفسها. للإيقاف ثم إعادة التشغيل:

```powershell
.\scripts\Stop-Project.ps1
.\scripts\Start-Project.ps1
```

الإيقاف لا يحذف بيانات Mongo أوKafka أوcheckpoints. لا تنقل نقاط الاستئناف بين مواضيع Kafka أو بين التشغيل الحي والعرض.

## أوامر يدوية

```powershell
# إنشاء الفهارس والمواضيع، بعد تشغيل الخدمات
.\.venv\Scripts\python.exe -m scholarship_map.cli init

# جمع حقيقي واحد -> Kafka، مع حفظ لقطة من النتائج
.\.venv\Scripts\python.exe -m scholarship_map.cli collect --snapshot .runtime/new-snapshot.jsonl

# إعادة قراءة الصفحات الرسمية المعروفة دون إعادة جمع كل صفحات الفهرس
.\.venv\Scripts\python.exe -m scholarship_map.cli verify

# معالجة كل الأحداث المتاحة ثم الخروج، فقط عند إيقاف المعالج المستمر
.\.venv\Scripts\python.exe -m scholarship_map.cli stream --available-now

# تحليل Spark SQL وMinHash واحد
.\.venv\Scripts\python.exe -m scholarship_map.cli batch

# تقييم جديد يحافظ على ملف التقييم الأصلي
.\.venv\Scripts\python.exe -m scholarship_map.cli benchmark --snapshot benchmarks/snapshots/initial-50-records.jsonl --output benchmarks/results/new-minhash-results.json
```

الجمع يعالج المحتوى المتغيّر فقط وينتظر إقرار Kafka قبل تسجيل نجاح نشر النسخة. حدود المصدر الافتراضية: Finder400، وIEFA80، وScholarPal150، والبرامج الرسمية30، وScholars4dev20، وAmideast10. يمكن تجاوزها صراحةً باستخدام `--limit` حتى500. تمت فهرسة صفحات Finder الحالية الاثنتي عشرة؛ بقية المواقع تظل محدودة التغطية. المجموع في النوافذ هو **ملاحظات مصدر** وقد يتضمن تكرار الرسالة؛ عداد الأحداث الفريدة والكتالوج لا يتضخمان بسبب إعادة الرسالة نفسها.

يبدأ الجامع عند تشغيل المشروع، ثم كل 6 ساعات أثناء بقاء الجهاز والخدمات شغّالة. يظهر آخر جمع والموعد التالي في نشاط المصادر والبث المباشر. الجدولة لها heartbeat مستقل؛ لا يُعرض الموعد كجدول متصل إذا غابت الإشارة الحديثة. Spark يستمع باستمرار للأحداث ولا ينتظر موعد الجمع التالي لمعالجة ما وصل. وقت الإضافة الأولى من Mongo مستقل عن وقت جلب المصدر، والتحديثات لا تغيّره.

## رابط HTTPS المؤقت

بعد تشغيل المشروع، نفّذ `.\scripts\Start-SharePreview.ps1` وخذ رابط Pinggy الذي يطبعه. الرابط المجاني يعمل 60 دقيقة، ثم أعد الأمر لإنشاء رابط جديد. أول زيارة تعرض صفحة المزود وزر `Enter site`. الخيار `-Provider localhost.run` متاح بديلًا لكنه بطيء في هذا الفحص وقد يغير عنوانه أثناء التشغيل. `.\scripts\Stop-PublicPreview.ps1` يوقف النفق وحده، و`Stop-Project.ps1` يوقفه مع خدمات المشروع. راجع [public-preview.md](public-preview.md) للحدود والتشخيص.

## عرض Replay منفصل

في نافذة PowerShell أولى:

```powershell
.\.venv\Scripts\python.exe -m scholarship_map.cli stream --demo
```

في نافذة ثانية:

```powershell
.\.venv\Scripts\python.exe -m scholarship_map.cli replay --rate 10 --run-id classroom-01
```

الإعادة ترسل إلى `scholarships.raw.demo`، ويحفظ المعالج إلى `scholarshipmap_demo` ونقاط استئناف `data/checkpoints/demo`. نفس `run-id` مع نفس الملف والسرعة يعيد هويات الأحداث نفسها. لا يستبدل الكتالوج الحي ولا يحدّث وقت الدليل الرسمي داخل السجل.

لعرض قاعدة الإعادة في موقع ثانٍ:

```powershell
$env:SM_MONGO_DATABASE='scholarshipmap_demo'
.\.venv\Scripts\python.exe -m scholarship_map.cli serve --port 8001
# عند إيقاف الخادم باستخدام Ctrl+C:
Remove-Item Env:SM_MONGO_DATABASE
```

يعرض الموقع شارة بيانات الإعادة. العرض الافتراضي يستعرض الإعلانات الحالية والمحتملة، مع تمييز الحالة. قد لا تظهر كل السجلات في فلتر «مفتوحة»؛ اختر «كل الحالات» لإضافة المغلقة التاريخية.

اختبار التكرار والتأخر المتكامل ينشئ موضوعًا وقاعدة فريدين للاختبار، ويترك تقريرًا قابلًا للفحص:

```powershell
.\.venv\Scripts\python.exe tests/streaming_scenario.py
```

## تطوير الواجهة

```powershell
cd frontend
npm ci --ignore-scripts
npm run dev -- --host 127.0.0.1
```

خادم Vite على 5173 يمرّر `/api` إلى 8000. بعد التعديل نفّذ `npm run build` ليُحدّث الموقع الذي يخدمه FastAPI. إن بُنيت الواجهة بعد بدء API لأول مرة، أعد تشغيل API حتى يركّب مجلد الملفات الثابتة.

## Docker Compose

```powershell
docker compose up --build -d
docker compose logs -f streaming collectors batch
docker compose --profile demo up -d streaming-demo
docker compose --profile tools run --rm replay
docker compose --profile tools run --rm benchmark
docker compose stop
```

لا تحتاج `.env` المحلية داخل الحاويات؛ إعدادات الاتصال الداخلية محددة في Compose. الواجهة على 8080، وKafka الخارجي على19092 وMongo الخارجي على27018. المجلدات المسماة تحتفظ بالبيانات. ملف Docker أُعدّ، لكن بناءه وتشغيله لم يُختبرا هنا لغياب المحرّك.

## تشخيص مختصر

| العارض | الإجراء |
| --- | --- |
| API يعيد503 | افحص `api/health` وسجل Mongo، ثم شغّل الخدمات |
| لا تظهر منح | أزل فلاتر البلد/المرحلة/الخريطة؛ الافتراضي يعرض الحالية والمحتملة ويستبعد المغلقة |
| لا أحداث جديدة بعد جمع ثانٍ | المحتوى غير المتغير يُتجاوز؛ هذا سلوك مقصود |
| فشل Java أو عامل Python | استعمل JDK21 الكامل والاعتماد المثبت PySpark4.0.3؛ راجع `spark_runtime.py` |
| `failOnDataLoss` من Kafka | بيانات الموضوع المطلوبة حُذفت بسياسة الاحتفاظ؛ افحص السجلات، ولا تمسح checkpoints دون تحديد نقطة بدء جديدة صراحةً |
| عدم ظهور التحليلات | انتظر اكتمال `batch`؛ راجع سجلها، وتاريخ آخر تحليل في الصفحة |
| بلاطات خريطة فارغة | افحص الإنترنت والوصول إلى OpenStreetMap؛ القائمة تبقى متاحة |
| مصدر متعطل | سجل المصدر يبين الخطأ؛ فشل الجمع لا يحذف المنح ولا يثبت انتهاءها |

يفشل بعض تنظيف مجلدات Spark المؤقتة على Windows برسائل عن ملفات JAR قيد الاستخدام عند الإغلاق؛ تحقق من رمز الخروج وتقرير النتيجة قبل تشخيص فشل المعالجة. لا يُعطّل المشروع TLS ولا يتجاوز تسجيل دخول أو منع وصول من المصدر.
