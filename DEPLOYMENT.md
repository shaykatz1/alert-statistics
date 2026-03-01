# 🚀 מדריך פריסה ל-GitHub Pages

## ✅ רשימת בדיקות

### קבצים נדרשים (הכל קיים ✓)
- [x] `docs/index.html` - עמוד ראשי
- [x] `docs/app.js` - קוד JavaScript
- [x] `docs/styles.css` - עיצוב
- [x] `docs/data/alerts_history.json` - נתוני התרעות
- [x] `docs/data/metadata.json` - מטא-דאטה
- [x] `docs/.nojekyll` - למניעת עיבוד Jekyll
- [x] `.github/workflows/update-data.yml` - עדכון אוטומטי

---

## 📋 שלבי הפריסה

### שלב 1: יצירת רפוזיטורי GitHub
```bash
# אתחול Git (אם לא קיים)
git init

# הוספת כל הקבצים
git add .

# יצירת commit ראשון
git commit -m "🎉 Initial commit - Home Front Alert Analysis"

# שינוי שם הענף לmain
git branch -M main
```

### שלב 2: חיבור ל-GitHub
```bash
# יצירת רפוזיטורי חדש ב-GitHub (דרך האתר)
# לאחר מכן, חיבור הרפוזיטורי המקומי:

git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### שלב 3: הפעלת GitHub Pages
1. כנס להגדרות הרפוזיטורי: `Settings` → `Pages`
2. תחת **Source**: בחר `Deploy from a branch`
3. תחת **Branch**: 
   - בחר `main`
   - בחר `/docs` כתיקייה
   - לחץ `Save`
4. המתן 1-3 דקות
5. האתר יופיע בכתובת: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

---

## 🔄 עדכון אוטומטי של נתונים

ה-GitHub Action מוגדר לרוץ:
- **אוטומטית**: כל שעתיים
- **ידנית**: Actions → "Update Alert Data" → "Run workflow"

### אישור הרשאות ל-Actions
1. `Settings` → `Actions` → `General`
2. תחת **Workflow permissions**: בחר `Read and write permissions`
3. לחץ `Save`

---

## 🧪 בדיקה מקומית

לפני פריסה ל-GitHub Pages, בדוק מקומית:

```bash
# הרצת שרת מקומי
cd docs
python3 -m http.server 8080

# פתח בדפדפן:
# http://localhost:8080
```

אם הכל עובד מקומית, זה יעבוד גם ב-GitHub Pages! ✅

---

## 🔍 פתרון בעיות

### האתר לא נטען
- ודא שהענף הוא `main` והתיקייה היא `/docs`
- בדוק שהקובץ `docs/.nojekyll` קיים
- המתן 2-3 דקות אחרי שינויים

### הנתונים לא מתעדכנים
- ודא ש-Actions מאופשר בהגדרות
- בדוק ב-Actions אם יש שגיאות
- ודא שהרשאות Write מאופשרות

### JavaScript לא עובד
- פתח Developer Tools בדפדפן (F12)
- בדוק שגיאות ב-Console
- ודא שהנתיבים ל-CSS/JS נכונים

---

## 📝 עדכון ידני של נתונים (מקומי)

```bash
# הרצת סקריפט העדכון
python3 scripts/fetch_alerts_snapshot.py

# commit ו-push
git add docs/data/
git commit -m "🔄 Update alert data"
git push
```

---

## 🎨 התאמה אישית

### שינוי כותרת
ערוך את [docs/index.html](docs/index.html#L6):
```html
<title>הכותרת שלך כאן</title>
```

### שינוי צבעים
ערוך את [docs/styles.css](docs/styles.css#L1):
```css
:root {
  --accent: #0f8b4c;  /* צבע ראשי */
  --bg: #f4f7f1;     /* רקע */
}
```

---

## 📊 מה האתר כולל

- ✅ ניתוח שבוע אחרון של התרעות
- ✅ סינון לפי תאריכים, שעות, יישובים
- ✅ חישוב זמן שהייה במרחב מוגן
- ✅ גרפים אינטראקטיביים
- ✅ השוואה בין יישובים
- ✅ יצוא CSV
- ✅ עדכון אוטומטי כל שעתיים

---

**בהצלחה! 🚀**
