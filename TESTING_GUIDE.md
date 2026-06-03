# Streamlit App Testing & Setup Guide

## Quick Start

### 1. Verify Python Installation
```bash
python --version  # Should be 3.8+
pip --version
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- **streamlit** - Web framework
- **pandas** - Data processing
- **plotly** - Interactive charts
- **folium** - Maps
- **geopandas** - GeoJSON support
- **google-generativeai** - Gemini API
- **python-dotenv** - Environment variables
- Plus additional dependencies

### 4. Run Setup Test
```bash
python test_setup.py
```

This verifies:
- ✅ Python version (3.8+)
- ✅ All required packages installed
- ✅ Configuration files present
- ✅ Data directory and files
- ✅ Page modules loadable
- ✅ Sample data loading
- ✅ Config module working

### 5. Start the App
```bash
streamlit run app.py
```

The app will start at: **http://localhost:8501**

---

## Project Structure

```
flc26/
├── app.py                    # Main Streamlit app (home page)
├── config.py                 # Configuration & environment
├── test_setup.py             # Setup verification script
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (local dev)
├── .env.example              # Template (commit to git)
├── .env.production           # Production template
├── .gitignore                # Git ignore rules
├── README.md                 # Documentation
│
├── modules/
│   ├── data_loader.py        # CSV/GeoJSON loading & caching
│   ├── visualizer.py         # Plotly chart utilities
│   ├── gemini_queries.py     # Gemini API integration
│   └── utils.py              # Helper functions
│
├── pages/
│   ├── pages_dashboard.py    # Dashboard (charts, filters, exports)
│   ├── pages_maps.py         # Geospatial maps (Folium)
│   ├── pages_query.py        # AI query interface (Gemini)
│   └── pages_localauth.py    # Local authorities GeoJSON
│
├── data/
│   ├── east_england_local_authorities_lower_level.geojson
│   ├── east_england_lauthorities_lower_csv.csv
│   └── ...other data files
│
└── venv/                     # Virtual environment (not committed)
```

---

## Available Pages

### 🏠 Home (app.py)
- Overview of the application
- Quick links to other pages
- Feature highlights
- Configuration info

### 📊 Dashboard
- Load CSV data or sample datasets
- Interactive Plotly charts:
  - Line charts
  - Bar charts
  - Scatter plots
  - Histograms
  - Box plots
  - Heatmaps
- Data filtering
- Data export (CSV)

### 🗺️ Maps
- Interactive Folium maps
- Support for lat/lon data
- Heatmap overlays
- Customizable markers
- Map type selection

### 🗺️ Local Authorities
- East England local authorities GeoJSON
- Interactive boundary maps
- Feature properties display
- Data preview

### 🤖 Query (AI-Powered)
- Natural language data queries via Gemini
- Automatic insights generation
- Visualization suggestions
- Data statistics

---

## Testing Checklist

### Setup Tests
- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (pip install -r requirements.txt)
- [ ] test_setup.py passes all checks
- [ ] .env file exists with configuration

### App Tests
- [ ] Streamlit app starts: `streamlit run app.py`
- [ ] Home page loads and displays correctly
- [ ] All pages appear in sidebar navigation
- [ ] Sample data loads in Dashboard
- [ ] Local authorities GeoJSON loads in Map
- [ ] Charts render without errors
- [ ] No error messages in console

### Feature Tests
- [ ] Load CSV files
- [ ] View sample data
- [ ] Create charts (line, bar, scatter, histogram)
- [ ] Filter data by categorical columns
- [ ] Export data as CSV
- [ ] View local authorities map
- [ ] Customize map styling
- [ ] View feature properties

### Performance Tests
- [ ] App starts in < 10 seconds
- [ ] Charts render smoothly
- [ ] Maps load without lag
- [ ] Data filtering is responsive
- [ ] Page switching is fast

---

## Configuration

### Environment Variables (.env)
```
GEMINI_API_KEY=               # Optional - for AI features
STREAMLIT_SERVER_PORT=8501    # Server port
STREAMLIT_SERVER_ADDRESS=localhost
DEBUG=true                    # Show debug info
MAX_UPLOAD_SIZE_MB=100
DATA_DIR=data
```

### Streamlit Config (streamlit_config.toml)
- Theme colors
- Sidebar state
- Logger settings
- Server configuration

---

## Troubleshooting

### Issue: "Module not found" error
**Solution:** Reinstall dependencies
```bash
pip install -r requirements.txt
```

### Issue: Port 8501 already in use
**Solution:** Use a different port
```bash
streamlit run app.py --server.port 8502
```

### Issue: GeoJSON not loading
**Solution:** Verify file path in data directory
```bash
python -c "from data_loader import get_available_local_files; print(get_available_local_files())"
```

### Issue: Gemini API errors
**Solution:** Add valid API key to .env
1. Get key from: https://makersuite.google.com/app/apikey
2. Add to .env: `GEMINI_API_KEY=your_key_here`
3. Restart streamlit

### Issue: Memory errors with large datasets
**Solution:** Use data sampling or pagination

### Issue: Slow performance
**Solution:** Clear Streamlit cache
```bash
streamlit cache clear
```

---

## Next Steps

1. **Test locally** - Verify app works with current setup
2. **Add more data** - Import additional CSV or GeoJSON files
3. **Customize styling** - Modify colors and themes
4. **Enable Gemini** - Add API key for AI features
5. **Deploy** - Use Docker for production deployment
6. **WordPress Integration** - Set up Nginx reverse proxy

---

## Support

For issues or questions, refer to:
- Streamlit Docs: https://docs.streamlit.io
- Folium Docs: https://folium.readthedocs.io
- GeoPandas Docs: https://geopandas.org
- Gemini API Docs: https://ai.google.dev/docs

---

## Development Commands

```bash
# Run app
streamlit run app.py

# Run tests
python test_setup.py

# Clear cache
streamlit cache clear

# Run specific page
streamlit run pages_dashboard.py

# View logs
streamlit config show

# Install new package
pip install package_name
```
