# Quick Start Guide - Streamlit App

## 🚀 Fast Setup (5 minutes)

### Option 1: Windows (Click & Run)
1. Double-click: `run_app.bat`
2. Wait for "Starting Streamlit App"
3. Browser opens to: http://localhost:8501

### Option 2: Command Line
```bash
cd c:\Users\davic\flc26
venv\Scripts\activate
streamlit run app.py
```

---

## 📋 Verification Steps

### Before Running App:
```bash
# Check Python
python --version

# Activate virtual environment
venv\Scripts\activate

# Install dependencies (if first time)
pip install -r requirements.txt

# Verify setup
python test_setup.py

# Check syntax
python verify_syntax.py
```

### Run the App:
```bash
streamlit run app.py
```

---

## 🌐 Access the App

**Local:** http://localhost:8501

Once running, you should see:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501

  Press CTRL+C to quit
```

---

## 📱 What You'll See

### Home Page
- Welcome message
- Feature overview (Dashboard, Maps, Query)
- Navigation sidebar

### Dashboard Page  
- Load sample data or CSV
- Interactive charts
- Data filtering
- Export as CSV

### Maps Page
- Interactive Folium maps
- Location markers
- Customizable styling

### Local Authorities Page
- East England boundaries GeoJSON
- Interactive map with properties
- Feature data table

### Query Page (AI)
- Natural language queries (requires API key)
- Data insights
- Visualization suggestions

---

## 🛠️ Troubleshooting

### App won't start
```bash
# Check Python version (needs 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt

# Clear cache
streamlit cache clear
```

### Port 8501 in use
```bash
# Use different port
streamlit run app.py --server.port 8502
```

### Missing modules
```bash
pip install -r requirements.txt
```

### GeoJSON not loading
- File: `data/east_england_local_authorities_lower_level.geojson`
- Should be in data/ folder

---

## 📚 Documentation Files

- **README.md** - Project overview
- **TESTING_GUIDE.md** - Detailed testing instructions
- **TEST_REPORT.md** - Testing checklist & scenarios
- **config.py** - Configuration documentation

---

## 🔑 Optional: Enable Gemini AI

1. Get API key: https://makersuite.google.com/app/apikey
2. Edit `.env` file:
   ```
   GEMINI_API_KEY=your_key_here
   ```
3. Restart app
4. Go to "Query" page for AI features

---

## ✅ Testing Checklist

- [ ] App starts without errors
- [ ] Home page displays correctly
- [ ] Can navigate to all pages
- [ ] Sample data loads in Dashboard
- [ ] Charts render
- [ ] Local authorities map displays
- [ ] Can export data as CSV
- [ ] No console errors

---

## 📞 Support

If something doesn't work:
1. Check console for error messages
2. Review TESTING_GUIDE.md
3. Verify dependencies: `pip list`
4. Try clearing cache: `streamlit cache clear`
5. Restart the app

---

**Status:** ✅ Ready to Test  
**Last Updated:** 2026-05-23
