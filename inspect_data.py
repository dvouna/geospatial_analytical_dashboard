#!/usr/bin/env python
"""
Inspect GeoJSON structure to find the linking field
"""
import json
import pandas as pd

# Load GeoJSON
with open('data/east_england_local_authorities_lower_level.geojson', 'r') as f:
    geojson = json.load(f)

# Get first feature
first_feature = geojson['features'][0]
print("First feature ID:", first_feature['id'])
print("First feature properties:", first_feature.get('properties', 'No properties'))

# Load CSV
csv = pd.read_csv('data/east_england_lauthorities_lower_csv.csv')
print("\nCSV columns:", csv.columns.tolist())
print("\nFirst few rows:")
print(csv.head())

# Check if we can match by the 'id' field
print(f"\nGeoJSON has {len(geojson['features'])} features")
print(f"CSV has {len(csv)} rows")

# Check for matching ID values
geojson_ids = [f['id'] for f in geojson['features']]
csv_fids = csv['fid'].tolist()

print(f"\nGeometries IDs: {sorted(set(geojson_ids))[:5]}... (showing first 5)")
print(f"CSV fid values: {sorted(set(csv_fids))[:5]}... (showing first 5)")

# Check if they match
if set(geojson_ids) == set(csv_fids):
    print("\n✅ IDs MATCH! Can merge on 'id' (GeoJSON) and 'fid' (CSV)")
else:
    print("\n❌ IDs don't match exactly, need to investigate further")
