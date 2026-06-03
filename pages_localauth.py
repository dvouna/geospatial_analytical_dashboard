"""
Local Authorities Map Page
Visualize local authorities GeoJSON data with CSV authority names and deprivation data
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from data_loader import load_geojson_file, validate_geodataframe, get_available_local_files, load_csv_file
import os
import json

st.set_page_config(page_title="Local Authorities", page_icon="🗺️", layout="wide")

st.title("🗺️ Local Authorities Map")
st.write("Visualize East England local authorities boundaries with names and deprivation data")

# Get available GeoJSON files
available_files = get_available_local_files('data')

if not available_files['geojson']:
    st.warning("No GeoJSON files found in data directory")
else:
    # Select GeoJSON file
    st.sidebar.header("📁 Data Source")
    
    geojson_files = available_files['geojson']
    geojson_names = [os.path.basename(f) for f in geojson_files]
    selected_file_idx = st.sidebar.selectbox("Select GeoJSON file:", range(len(geojson_names)), 
                                             format_func=lambda x: geojson_names[x])
    selected_file = geojson_files[selected_file_idx]
    
    # Load GeoJSON
    gdf = load_geojson_file(selected_file)
    
    if gdf is not None and validate_geodataframe(gdf):
        # Try to load and merge CSV data
        csv_df = None
        csv_files = available_files['csv']
        if csv_files:
            # Look for the matching CSV file (east_england_lauthorities_lower_csv.csv)
            csv_file = None
            for f in csv_files:
                if 'lauthorities_lower' in f.lower() or 'local_authorities' in f.lower():
                    csv_file = f
                    break
            
            if csv_file:
                try:
                    csv_df = load_csv_file(csv_file)
                    if csv_df is not None:
                        # Extract the feature IDs from the GeoJSON
                        with open(selected_file, 'r') as f:
                            geojson_raw = json.load(f)
                        
                        feature_ids = [feat['id'] for feat in geojson_raw['features']]
                        gdf['feature_id'] = feature_ids
                        
                        # Merge on matching ID
                        gdf = gdf.merge(csv_df, left_on='feature_id', right_on='fid', how='left')
                        st.success(f"✅ Merged GeoJSON with authority names from CSV")
                except Exception as e:
                    st.warning(f"Could not merge CSV data: {str(e)}")
        
        # Map configuration
        st.sidebar.subheader("🗺️ Map Settings")
        
        # Calculate bounds for centering
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        
        # Map type selection
        map_type = st.sidebar.selectbox(
            "Map type:",
            ["OpenStreetMap", "CartoDB Positron", "CartoDB Voyager"],
            key="map_type"
        )
        
        map_style = {
            "OpenStreetMap": "OpenStreetMap",
            "CartoDB Positron": "CartoDB positron",
            "CartoDB Voyager": "CartoDB voyager",
        }
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles=map_style.get(map_type, "OpenStreetMap")
        )
        
        # Add GeoJSON features
        st.sidebar.subheader("📍 Feature Settings")
        
        # Color options
        fill_color = st.sidebar.color_picker("Fill color:", "#3388ff")
        outline_color = st.sidebar.color_picker("Outline color:", "#000000")
        outline_weight = st.sidebar.slider("Outline weight:", 1, 5, 2)
        fill_opacity = st.sidebar.slider("Fill opacity:", 0.0, 1.0, 0.3)
        
        # Show/hide properties
        show_properties = st.sidebar.checkbox("Show feature properties on hover", value=True)
        
        # Prepare display columns
        display_cols = gdf.columns.tolist()
        if 'geometry' in display_cols:
            display_cols.remove('geometry')
        
        # Get the authority name column if it exists
        auth_name_col = None
        for col in ['LAD24NM', 'name', 'Name', 'AUTHORITY', 'Authority']:
            if col in gdf.columns:
                auth_name_col = col
                break
        
        # Add GeoJSON to map with authority names
        if show_properties:
            # Create custom popups with authority names
            for idx, row in gdf.iterrows():
                # Get authority name
                auth_name = row.get(auth_name_col, f'Feature {idx}') if auth_name_col else f'Feature {idx}'
                
                # Create popup content
                popup_content = f"<b>{auth_name}</b><br>"
                
                # Add relevant properties
                for col in ['LAD24CD', 'RAvgRankLTLA', 'RAvgScorLTLA']:
                    if col in row.index and pd.notna(row[col]):
                        popup_content += f"{col}: {row[col]}<br>"
                
                # Add geometry to map with popup
                folium.GeoJson(
                    json.loads(row.geometry.to_json()),
                    style_function=lambda x: {
                        'fillColor': fill_color,
                        'color': outline_color,
                        'weight': outline_weight,
                        'fillOpacity': fill_opacity,
                    },
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=folium.Tooltip(f"<b>{auth_name}</b>")
                ).add_to(m)
        else:
            folium.GeoJson(
                gdf,
                style_function=lambda x: {
                    'fillColor': fill_color,
                    'color': outline_color,
                    'weight': outline_weight,
                    'fillOpacity': fill_opacity,
                }
            ).add_to(m)
        
        # Display map
        st.subheader("Interactive Map")
        st_folium(m, width=1400, height=600)
        
        # Data summary
        st.divider()
        st.subheader("📊 Data Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Features", len(gdf))
        with col2:
            st.metric("Bounds", f"({bounds[0]:.2f}, {bounds[1]:.2f}) to ({bounds[2]:.2f}, {bounds[3]:.2f})")
        with col3:
            st.metric("CRS", str(gdf.crs) if gdf.crs else "Not set")
        
        # Data preview
        st.subheader("📋 Feature Data")
        
        # Drop geometry column for display, keep authority name if available
        df_display = gdf.drop(columns=['geometry'], errors='ignore')
        
        # Reorder columns to put authority name first
        if auth_name_col and auth_name_col in df_display.columns:
            cols = [auth_name_col] + [c for c in df_display.columns if c != auth_name_col]
            df_display = df_display[cols]
        
        st.dataframe(df_display, use_container_width=True)
        
        # Column info
        st.subheader("📝 Column Information")
        col_info = []
        for col in gdf.columns:
            if col != 'geometry':
                col_info.append({
                    'Column': col,
                    'Type': str(gdf[col].dtype),
                    'Non-Null Count': gdf[col].count(),
                    'Null Count': gdf[col].isnull().sum()
                })
        
        if col_info:
            st.dataframe(pd.DataFrame(col_info), use_container_width=True)
        
    else:
        st.error("Could not load or validate GeoJSON file")
