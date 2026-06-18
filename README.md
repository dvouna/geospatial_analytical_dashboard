# Geospatial Analytical Dashboard

A Streamlit application for exploring tabular and geospatial data (East of England Local Authorities). The project focuses on interactive mapping with Folium, dataset overlays, and simple AI-assisted query features.

Key points
- Interactive maps using Folium and `streamlit_folium`
- Centralized map helpers in `map_utils.py`
- Pages grouped under the `pages/` package
- Data stored in the `data/` folder (GeoJSON + CSV overlays)
- Small `utils/` package for I/O and path helpers

Repository layout (top-level):

```
app.py                  # Streamlit entrypoint and navigation
map_utils.py            # Map helpers (load, prepare, render)
utils/                  # Small helper package (io, paths)
pages/                  # UI pages (maps, population, imd, cancer)
data/                   # GeoJSON and CSV data used by the app
.gitignore
requirements.txt
```

Quick start (Windows)

1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Run the app

```powershell
streamlit run app.py
```

Open http://localhost:8501 in your browser.

Configuration
- Copy `.env.example` to `.env` and set required variables (e.g. Gemini API key) if you use AI features.
- `streamlit_config.toml` holds Streamlit-specific settings.

Development notes
- Pages live in the `pages/` package (e.g. `pages/maps.py`, `pages/population.py`).
- Use helpers in `utils` for consistent paths: `from utils.paths import data_path; p = data_path() / 'population_detail.csv'`.
- Map utilities are in `map_utils.py` to keep folium integration centralized.

Contributing
- Create a branch, add tests where relevant, open a PR.

License
- MIT

If you'd like, I can:
- Add examples for running tests or basic unit tests for `utils`.
- Create a small CONTRIBUTING.md and DEVELOPMENT.md.
