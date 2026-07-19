# Geospatial Cancer Health Dashboard (East of England)

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=Streamlit&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75C2?style=flat-square&logo=googlegemini&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-28%20Passed-brightgreen?style=flat-square&logo=pytest&logoColor=white)
![Linter](https://img.shields.io/badge/Linter-Ruff-black?style=flat-square&logo=ruff&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

A Streamlit-based geospatial analytical platform for exploring demographics, deprivation indices, and cancer incidence rates across the 45 local authority districts in the East of England.

This dashboard is designed to assist public health analysts and policymakers in identifying vulnerable or deprived communities that would benefit most from targeted early detection campaigns.

---

## Key Features

* **Interactive Geospatial Mapping**: High-performance choropleth maps powered by Folium and `streamlit-folium` displaying overall and subdomain deprivation ranks, cancer rates, and ethnic group populations.
* **Demographic & Deprivation Analysis**: In-depth profiling of ethnic subgroups and Index of Multiple Deprivation (IoD 2025) rankings (income, employment, health, housing, etc.) for selected districts.
* **Conversational AI Research Assistant**: 
  * Powered by Google Gemini (`gemini-2.5-flash` or `gemini-2.0-flash`).
  * Analyzes questions across multiple tables (demographics, deprivation, cancer).
  * Implements a **Semantic Code Cache** to store and retrieve previously verified analytical query results for instantaneous responses.
  * Runs analytical code in a restricted execution sandbox for safe, local data processing.

---

## Repository Structure

```text
├── app.py                  # Entrypoint & multi-page navigation layout
├── config.py               # Environment configuration and validation
├── map_fragment.py         # Leaflet/Folium map rendering component
├── map_utils.py            # GIS, GeoJSON, and data-merge helpers
├── visualizer.py           # Shared Plotly charts and layout configurations
├── gemini_queries.py       # Core Gemini prompt generation and query logic
├── data/                   # Local authority GeoJSON and CSV datasets
├── pages/                  # Dashboard analytical playgrounds
│   ├── 1_Population_Demographics.py
│   ├── 2_Deprivation_Analysis.py
│   ├── 3_Cancer_Trends.py
│   ├── 4_General_Insights.py
│   ├── 5_AI_Research_Assistant.py
│   └── Districts_Profile.py
├── utils/                  # Shared backend utilities
│   ├── code_cache.py       # Semantic code cache manager
│   ├── data_loader_cancer.py # Public health & cancer dataset loader
│   └── profile_generator.py # Context profile builder for Gemini
└── tests/                  # Pytest verification suite
```

---

## Quick Start (Windows)

### 1. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and configure your API credentials:
```env
# Gemini API Key (required for AI Assistant)
GEMINI_API_KEY="your_api_key_here"

# Model name configuration (defaults to gemini-2.5-flash)
GEMINI_MODEL="gemini-2.5-flash"
```

### 4. Run the Streamlit Dashboard
```powershell
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## Quick Start (Docker)

You can also run the application fully containerised using Docker Compose. This ensures a consistent environment and automatic port mapping.

### 1. Configure Environment
Copy `.env.production.example` to `.env` and fill in your `GEMINI_API_KEY`.

### 2. Build and Run
```powershell
docker compose up -d
```
Open **`http://localhost:8501`** in your browser.

---

## Running the Test Suite

Run the full suite of unit tests to verify data loading, profile generation, semantic caching, and the sandbox compiler:
```powershell
pytest -v
```

---

## Configuration Parameters

Supported variables in `.env`:
* `GEMINI_API_KEY`: API Key for Google Generative AI.
* `GEMINI_MODEL`: Model version to query (e.g. `gemini-2.5-flash`).
* `DATA_DIR`: Directory where data files are located (default: `data`).
* `STREAMLIT_SERVER_PORT`: Port to bind the server to (default: `8501`).
