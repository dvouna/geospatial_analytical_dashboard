"""
Geospatial Maps Page
Interactive map visualization for location-based data
"""

import streamlit as st
import pandas as pd
import folium
import json
import geopandas as gpd
from streamlit_folium import st_folium
from pathlib import Path
from map_utils import load_geojson, prepare_geojson_payload, compute_center

# Page config is set in the main app; avoid calling set_page_config here when imported.

@st.cache_data
def load_base_gdf():
    data_path = Path(__file__).parent / "data" / "base_gdf.geojson"
    try:
        return load_geojson(data_path)
    except FileNotFoundError:
        st.error(f"❌ GeoJSON file not found at: `{data_path}`")
        return None
    except Exception as e:
        st.error(f"❌ Error loading GeoJSON: {str(e)}")
        return None


def render_click_analytics_page(gdf, geojson_payload):
    # Bidirectional map: info selection updates map and map clicks update info
    col_map, col_info = st.columns([7, 3], gap="medium")

    # Prepare lookup maps for UI
    display_names = []
    id_to_props = {}
    id_field_candidates = ["LAD24CD", "LAD13CD", "LAD19CD", "LAD20CD", "code", "id"]
    # Determine name and id fields
    name_field = None
    for c in ["LAD24NM", "name", "NAME", "LA_Name"]:
        if c in gdf.columns:
            name_field = c
            break

    for feat in geojson_payload.get("features", []):
        fid = feat.get("id")
        props = feat.get("properties", {})
        id_to_props[str(fid)] = props
        display = props.get(name_field) if name_field and props.get(name_field) else str(props.get(id_field_candidates[0], fid))
        display_names.append((display, str(fid)))

    # Sidebar-style info column: selection box and details
    with col_info:
        st.markdown("### 📋 Authority Information")

        # Build a friendly select box. Use session state to persist selection.
        options = [d[0] for d in display_names]
        option_to_id = {d[0]: d[1] for d in display_names}

        selected_display = st.selectbox("Select an authority:", options=options, index=0, key="maps_select_display")
        selected_code = option_to_id.get(selected_display)

    # Map column: highlight selected feature
    with col_map:
        # compute map center quickly
        bounds = gdf.total_bounds
        avg_lat = (bounds[1] + bounds[3]) / 2
        avg_lon = (bounds[0] + bounds[2]) / 2

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=8, tiles="CartoDB positron")

        def style_fn(feature):
            if str(feature.get("id")) == str(selected_code):
                return {"fillColor": "#ff7800", "color": "orange", "weight": 3, "fillOpacity": 0.7}
            return {"fillColor": "#318dcc", "color": "black", "weight": 1, "fillOpacity": 0.4}

        geo_layer = folium.GeoJson(
            geojson_payload,
            style_function=style_fn,
            highlight_function=lambda x: {"weight": 3, "color": "orange", "fillOpacity": 0.6},
            tooltip=folium.GeoJsonTooltip(fields=[c for c in gdf.columns if c != 'geometry'][:3], localize=True)
        ).add_to(m)

        map_output = st_folium(m, width="100%", height=600, returned_objects=["last_object_clicked"])

    # After rendering map we can process clicks and sync selection
    clicked_feature = map_output.get("last_object_clicked") if map_output else None

    # If user clicked the map, update the selectbox selection and rerun to reflect change
    if clicked_feature and "id" in clicked_feature:
        clicked_la_code = str(clicked_feature["id"])
        # Find matching display text
        matching = [disp for (disp, cid) in display_names if cid == clicked_la_code]
        if matching:
            # Set the selectbox value by storing into session state and rerunning
            st.session_state["maps_select_display"] = matching[0]
            st.experimental_rerun()

    # Finally render details for the currently selected code
    with col_info:
        # Re-read the selected code from selectbox (may have come from session state)
        sel_display = st.session_state.get("maps_select_display", display_names[0][0] if display_names else None)
        sel_code = option_to_id.get(sel_display) if sel_display else None

        if sel_code and sel_code in id_to_props:
            props = id_to_props[sel_code]
            la_name = props.get(name_field, sel_display)
            icb = props.get("ICB_Name", "Unknown ICB")
            imd = props.get("IMD_National_Score", "N/A")
            pop = props.get("Total_Population", "Unknown")
            cancer_rate = props.get("Cancer_Incidence_Rate", "N/A")

            st.success(f"📍 **Active Selection: {la_name}**")
            try:
                st.metric(label="Total Population", value=f"{int(pop):,}")
            except Exception:
                st.metric(label="Total Population", value=f"{pop}")
            st.metric(label="National IMD Score", value=f"{imd}")
            st.markdown("---")
            st.markdown(f"**ICB Jurisdiction:**\n`{icb}`")
            st.markdown(f"**Cancer Incidence Rate:**\n`{cancer_rate} per 100k`")
        else:
            st.info("💡 Click a region on the map or pick one from the selector to display its data.")

        
def render_imd_page():
    st.title("🗺️ East of England Local Authorities Interactive Map")
    st.subheader("Local Authority, Deprivation and Population Summaries")
    st.write("Visualize East of England authorities data on an interactive map.")

    # Sidebar Data Source Info
    st.sidebar.header("Data Source")
    st.sidebar.write("**East of England Local Authorities Data**")
    
    # Load shared base data
    gdf = load_base_gdf()
    
    if gdf is not None:
        st.sidebar.success("✅ Loaded local authorities GeoJSON data")
        
        # Map Settings
        st.sidebar.subheader("🗺️ Map Settings")
        map_type = st.sidebar.radio(
            "Map type:",
            ["Basic (OpenStreetMap)", "Light Streets (CartoDB)", "Satellite (ArcGIS)"],
            key="map_type",
            index=2
        )
        
        # Determine map tile and attribution based on selection
        if map_type == "Basic (OpenStreetMap)":
            tiles = "OpenStreetMap"
            attr = None
        elif map_type == "Light Streets (CartoDB)":
            tiles = "https://{s}.basemaps.cartocdn.com/positron/{z}/{x}/{y}{r}.png"
            attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        else:
            tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attr = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'

        # Calculate map center and prepare GeoJSON payload with stable ids
        avg_lat, avg_lon = compute_center(gdf)
        geojson_payload, id_field = prepare_geojson_payload(gdf)

        # Offer the new bidirectional click-analytics UI as an option
        bidir = st.sidebar.checkbox("Enable bidirectional click analytics", value=True)

        if bidir:
            render_click_analytics_page(gdf, geojson_payload)
        else:
            # Create Folium Map
            m = folium.Map(location=[avg_lat, avg_lon], zoom_start=8, tiles=tiles, attr=attr)

            # Add GeoJSON to the map with clean styling
            folium.GeoJson(
                gdf,
                name="East England Local Authorities",
                style_function=lambda x: {
                    'fillColor': '#318dcc',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.5,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[col for col in gdf.columns if col != 'geometry'][:3], 
                    localize=True
                )
            ).add_to(m)

            # Display the Map in Streamlit
            st_folium(m, width=800, height=600, returned_objects=[])

        # Raw Data Display Below the Map
        st.subheader("📍 Local Authorities GeoJSON Data Table")
        st.write(f"**Total features:** {len(gdf)}")
        
        # Safely drop geometry for the tabular preview
        df_preview = pd.DataFrame(gdf.drop(columns='geometry', errors='ignore'))
        st.dataframe(df_preview.head(50), use_container_width=True)

        st.sidebar.markdown("---")
        st.sidebar.caption("Using geopandas & folium to render local authorities.")
    else:
        st.info("⚠️ Unable to load GeoJSON data. Please check the data file and try again.")

if __name__ == "__main__":
    render_imd_page()