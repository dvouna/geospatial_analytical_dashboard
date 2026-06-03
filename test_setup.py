#!/usr/bin/env python
"""
Test script to verify Streamlit app setup and dependencies
"""

import sys
import subprocess
from pathlib import Path

print("=" * 60)
print("STREAMLIT APP SETUP TEST")
print("=" * 60)

# Test 1: Check Python version
print("\n[1/7] Checking Python version...")
print(f"Python {sys.version}")
if sys.version_info < (3, 8):
    print("❌ Python 3.8+ required")
    sys.exit(1)
print("✅ Python version OK")

# Test 2: Check required dependencies
print("\n[2/7] Checking required packages...")
required_packages = [
    'streamlit',
    'pandas',
    'numpy',
    'plotly',
    'folium',
    'geopandas',
    'dotenv'
]

missing_packages = []
for package in required_packages:
    try:
        __import__(package if package != 'dotenv' else 'dotenv')
        print(f"  ✅ {package}")
    except ImportError:
        print(f"  ❌ {package} - MISSING")
        missing_packages.append(package)

if missing_packages:
    print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
    print("\nTo install missing packages, run:")
    print(f"  pip install -r requirements.txt")
    sys.exit(1)
print("✅ All required packages installed")

# Test 3: Check config files
print("\n[3/7] Checking configuration files...")
config_files = {
    'app.py': 'Main application',
    'config.py': 'Configuration module',
    '.env.example': 'Environment template',
    'requirements.txt': 'Dependencies',
}

for file, desc in config_files.items():
    if Path(file).exists():
        print(f"  ✅ {file} ({desc})")
    else:
        print(f"  ❌ {file} ({desc}) - NOT FOUND")

# Test 4: Check data directory
print("\n[4/7] Checking data directory...")
data_dir = Path('data')
if data_dir.exists():
    files = list(data_dir.glob('*'))
    print(f"  ✅ Data directory exists with {len(files)} files:")
    for f in files[:5]:
        print(f"    - {f.name}")
    if len(files) > 5:
        print(f"    ... and {len(files) - 5} more")
else:
    print(f"  ❌ Data directory not found")

# Test 5: Check page files
print("\n[5/7] Checking page files...")
page_files = [
    'pages_dashboard.py',
    'pages_maps.py',
    'pages_query.py',
    'pages_localauth.py',
]

for page_file in page_files:
    if Path(page_file).exists():
        print(f"  ✅ {page_file}")
    else:
        print(f"  ❌ {page_file} - NOT FOUND")

# Test 6: Check data loader
print("\n[6/7] Testing data loader module...")
try:
    from data_loader import load_sample_dataset, get_available_local_files
    df = load_sample_dataset('sample_sales')
    print(f"  ✅ Sample data loaded: {len(df)} rows")
    
    available = get_available_local_files('data')
    print(f"  ✅ Found {len(available['geojson'])} GeoJSON files")
    print(f"  ✅ Found {len(available['csv'])} CSV files")
except Exception as e:
    print(f"  ❌ Error loading data: {str(e)}")

# Test 7: Check config module
print("\n[7/7] Testing config module...")
try:
    from config import Config, check_environment
    check_environment()
    print(f"  ✅ App Name: {Config.APP_NAME}")
    print(f"  ✅ App Version: {Config.APP_VERSION}")
    print(f"  ✅ Debug Mode: {Config.DEBUG}")
    print(f"  ✅ Streamlit Port: {Config.STREAMLIT_SERVER_PORT}")
except Exception as e:
    print(f"  ❌ Config error: {str(e)}")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nTo start the Streamlit app, run:")
print("  streamlit run app.py")
print("\nThe app will be available at:")
print("  http://localhost:8501")
print("=" * 60)
