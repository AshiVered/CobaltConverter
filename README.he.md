<div dir="rtl">

# CobaltConverter

[English](README.md)

**CobaltConverter** היא תוכנת המרת קבצים חוצת-פלטפורמות המבוססת על **[FFmpeg](https://ffmpeg.org/)**.
FFmpeg הוא כלי מולטימדיה עוצמתי, אך חסר לו ממשק גרפי — לכן **CobaltConverter** מספקת אחד באמצעות **[WxPython](https://github.com/wxWidgets/Phoenix)**, עם עיצוב גמיש שמתאים את עצמו למערכת ההפעלה (Windows, Linux, macOS).

---

## תכונות

- ממשק גרפי נקי ופשוט ל-FFmpeg
- המרת קבצים בכמויות (Batch)
- חוצת-פלטפורמות (Windows, macOS, Linux)
- הורדת FFmpeg אוטומטית אם לא נמצא במערכת
- תמיכה במספר שפות (אנגלית, עברית)
- פריסטים לאיכות (נמוך / בינוני / גבוה / מקסימום) + מצב מותאם אישית
- תמיכה בפורמט WMA
- מצב Debug לאבחון בעיות

---

## התקנה

### גרסאות מוכנות (מומלץ)

הורידו את הגרסה האחרונה עבור הפלטפורמה שלכם מעמוד ה-[Releases](../../releases).

כל גרסה כוללת שתי חלופות:
- **רגילה** — דורשת FFmpeg מותקן במערכת (או תוריד אוטומטית)
- **with-ffmpeg** — FFmpeg מצורף בפנים, עובד מהקופסה

### macOS — הפעלה ראשונה

macOS חוסם אפליקציות ממפתחים לא מזוהים כברירת מחדל. כדי לפתוח את CobaltConverter:

1. חלצו את קובץ ה-`.zip` שהורדתם
2. לחצו דאבל-קליק על `CobaltConverter.app` — macOS יציג אזהרת אבטחה
3. פתחו **הגדרות מערכת > פרטיות ואבטחה** (System Settings > Privacy & Security)
4. גללו למטה — תראו הודעה על CobaltConverter שנחסם
5. לחצו **פתח בכל זאת** (Open Anyway) ואשרו

צריך לעשות את זה רק פעם אחת. אחרי זה האפליקציה תיפתח רגיל.

### הרצה מקוד מקור (Python)

אם אתם מעדיפים להריץ מקוד מקור (כל פלטפורמה):

#### דרישות
- [Python 3.12+](https://www.python.org/downloads/)
- [wxPython](https://github.com/wxWidgets/Phoenix)

#### התקנה

    pip install wxPython

#### הרצה

    python CobaltConverter.py

### התקנת FFmpeg ידנית (ללא אינטרנט)

CobaltConverter מוריד FFmpeg אוטומטית בעת הצורך. אם אין לכם גישה לאינטרנט, ניתן להתקין ידנית:

1. הורידו את ארכיון FFmpeg עבור הפלטפורמה שלכם:

   | פלטפורמה | קישור |
   |:----------|:-------|
   | Windows x64 | [ffmpeg-win64-gpl.zip](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip) |
   | macOS | [ffmpeg-mac.zip](https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip) |
   | Linux x64 | [ffmpeg-linux64-gpl.tar.xz](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz) |
   | Linux ARM64 | [ffmpeg-linuxarm64-gpl.tar.xz](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz) |

2. פתחו את הארכיון ומצאו את הקובץ `ffmpeg.exe` (Windows) או `ffmpeg` (macOS/Linux). ייתכן שהוא בתיקיית `bin/`.

3. העתיקו אותו לתיקיית `bin/` בתוך תיקיית הפרויקט. אם התיקייה לא קיימת, צרו אותה.

4. **macOS/Linux בלבד:** פתחו טרמינל בתיקיית הפרויקט והריצו:
   ```
   chmod +x bin/ffmpeg
   ```

---

## מצב Debug

אם משהו לא עובד כצפוי, ניתן להפעיל מצב Debug ליצירת קובץ לוג מפורט לאבחון בעיות.

### מתוך האפליקציה
בשורת התפריט: **Settings > Debug Mode**. ההגדרה נשמרת אוטומטית ותישאר פעילה גם בהפעלה הבאה.

### משורת הפקודה (למפתחים)
    python CobaltConverter.py --debug

כשמצב Debug פעיל:
- כותרת החלון מציגה **[DEBUG]** והפוטר מציג **DEBUG**
- דוח אבחון מלא של המערכת נכתב ללוג (מערכת הפעלה, Python, גרסת FFmpeg וכו')
- כל פקודות FFmpeg והפלט שלהן מתועדים שורה-שורה
- קובץ הלוג נשמר כ-`CobaltConverter.log` ליד האפליקציה

---

## רשימת משימות

| סטטוס | תכונה |
|:------:|--------|
| ✅ | תמיכה במספר שפות *(v0.6)* |
| ✅ | המרת קבצים בכמויות *(v0.4.2)* |
| ✅ | הורדת FFmpeg אוטומטית |
| ✅ | פריסטים לאיכות + בקרת איכות מותאמת אישית |
| ✅ | תמיכה בפורמט WMA |
| ✅ | מצב Debug עם אבחון מערכת |
| ⏳ | חיתוך אודיו/וידאו |
| ⏳ | מיזוג קבצים |
| ⏳ | הוספת אפשרות שימוש דרך תפריט קליק ימני |
| ⏳ | הוספת המרת מסמכים |
| ⏳ | תמיכה בכל הפורמטים שנתמכים ע"י FFmpeg |
| ✅ | בחירת תיקיית שמירה לקבצים מומרים *(v0.5.0)* |
| ✅ | טיפול ב-GIF כווידאו *(v0.4.3)* |
| ✅ | כפתור עצירה *(v0.5.0)* |

---

### רישיון

**CobaltConverter** מופצת תחת רישיון **GNU General Public License v3.0 (GPL-3.0)**.
**FFmpeg** הוא תלות חיצונית שפותחה ע"י פרויקט FFmpeg ומופצת תחת הרישיון שלה.

ראו [LICENSE](LICENSE) לפרטים.

---

## קרדיטים

- **מפתח ראשי:** [Ashi Vered](https://github.com/AshiVered)
- **תורמים:** [Yisroel Tech](https://github.com/YisroelTech), [cfopuser](https://github.com/cfopuser)

</div>
