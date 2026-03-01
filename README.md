# אתר ניתוח התרעות - פיקוד העורף 🚨

אתר סטטי לניתוח התרעות מפיקוד העורף, מתארח ב-GitHub Pages.

## 🌐 צפייה באתר
האתר זמין בכתובת: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

(החלף `YOUR_USERNAME` ו-`YOUR_REPO_NAME` בערכים המתאימים)

## 📊 יכולות
- ניתוח נתונים משבוע אחרון של התרעות
- סוגי התרעות: שיגורים, כניסה/יציאה ממרחב מוגן, חדירת כלי טיס
- סינון לפי טווח תאריכים, שעות, ויישובים
- חישוב זמן שהייה במרחב מוגן
- גרפים אינטראקטיביים לפי שעות היום
- השוואה בין יישובים
- יצוא נתונים ל-CSV

## 🚀 הגדרת GitHub Pages

### 1. העלאה ל-GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 2. הפעלת GitHub Pages
1. עבור להגדרות הרפוזיטורי (Settings)
2. לחץ על **Pages** בתפריט הצד
3. תחת **Source**, בחר **Deploy from a branch**
4. תחת **Branch**, בחר `main` ו-`/docs` ולחץ Save
5. האתר יהיה זמין תוך מספר דקות

### 3. עדכון אוטומטי של הנתונים
הנתונים מתעדכנים אוטומטית כל שעתיים באמצעות GitHub Actions.
לעדכון ידני:
1. עבור ל-Actions בגיטהאב
2. בחר את ה-workflow "Update Alert Data"
3. לחץ על "Run workflow"

## 🔧 פיתוח מקומי

### הרצת שרת מקומי
```bash
cd docs
python3 -m http.server 8000
```
ואז פתח: `http://localhost:8000`

### עדכון נתונים מקומי
```bash
python3 scripts/fetch_alerts_snapshot.py
```

## 📁 מבנה הפרויקט
```
├── docs/               # קבצי GitHub Pages
│   ├── index.html     # עמוד ראשי
│   ├── app.js         # לוגיקת האפליקציה
│   ├── styles.css     # עיצוב
│   └── data/          # נתוני התרעות (מתעדכן אוטומטית)
├── scripts/           # סקריפטים לעדכון נתונים
└── .github/workflows/ # אוטומציה של GitHub Actions
```

## 📝 מקור נתונים
`https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json`

## ⚙️ עקרון ספירה
כאשר בוחרים כמה יישובים יחד, אירוע שמופיע באותה שנייה ובאותה כותרת בכמה יישובים נספר כאירוע ייחודי אחד (דה-דופליקציה).
