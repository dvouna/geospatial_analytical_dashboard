"""
Geospatial Maps Page
Interactive map visualization for location-based data
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from map_utils import (
    load_base_gdf,
    build_authority_options,
    extract_clicked_fid,
    trigger_rerun,
    display_props_as_kv,
    prepare_geojson_payload,
    compute_center,
    create_folium_map,
    render_map_settings,
    add_geojson_layer,
    render_map_st_folium,
    load_overlay_dataframe,
    merge_overlay,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def render_maps_page():
    st.title("🗺️ East of England Local Authorities Interactive Map")
    st.subheader("Local Authority, Deprivation and Population Summaries")
    st.write("Visualize East of England authorities data on an interactive map.")

    # Sidebar Data Source Info + page toggle
    st.sidebar.header("Data Source")
    st.sidebar.write("**East of England Local Authorities Data**")
    show_page = st.sidebar.checkbox(
        "Display this page", value=True, key="show_maps_page"
    )
    if not show_page:
        st.info("Page hidden via sidebar toggle.")
        return

    # Load shared base data
    gdf = load_base_gdf(DATA_DIR)
    if gdf is None:
        st.error(
            "❌ Unable to load base boundaries GeoJSON data. Please check the data directory."
        )
        return

    tiles, attr = render_map_settings(key="map_type_maps")

    # Try to find a sensible overlay (population) file and merge if present
    overlay_candidates = [
        DATA_DIR / "local_districts.csv",
    ]
    overlay_df = None
    for p in overlay_candidates:
        if p.exists():
            try:
                overlay_df = load_overlay_dataframe(p, index_col="fid")
                # Ensure fid exists in both before merging
                if "fid" not in gdf.columns:
                    st.error("❌ Base GeoJSON is missing required join key: 'fid'")
                    return
                if "fid" not in overlay_df.columns:
                    st.error(
                        f"❌ Overlay CSV {p.name} is missing required join key: 'fid'"
                    )
                    return
                gdf = merge_overlay(gdf, overlay_df, base_key="fid", overlay_key="fid")
                break
            except Exception as e:
                st.warning(f"⚠️ Failed to merge overlay from {p.name}: {str(e)}")

    # Prepare payload and center
    center = compute_center(gdf)
    geojson_payload, id_field = prepare_geojson_payload(gdf)

    # Build selectbox options
    options, option_to_id, id_to_display, id_to_props = build_authority_options(
        geojson_payload
    )

    # Initialize state keys
    if "maps_select_display" not in st.session_state:
        st.session_state["maps_select_display"] = options[0] if options else None
    if "maps_select_version" not in st.session_state:
        st.session_state["maps_select_version"] = 0

    current_display = st.session_state.get("maps_select_display")
    if current_display not in option_to_id and options:
        current_display = options[0]
        st.session_state["maps_select_display"] = current_display

    # Layout: left map/selector + right info box
    col_center, col_info = st.columns([9, 3], gap="medium")

    with col_center:
        selected_index = (
            options.index(current_display) if current_display in options else 0
        )
        selected_display = (
            st.selectbox(
                "Select an authority:",
                options=options,
                index=selected_index,
                key=f"maps_select_display_{st.session_state['maps_select_version']}",
            )
            if options
            else None
        )

        if selected_display:
            st.session_state["maps_select_display"] = selected_display

        active_fid = option_to_id.get(selected_display) if selected_display else None

        m = create_folium_map(center=center, tiles=tiles, attr=attr)
        tooltip_fields = [field for field in ["fid", "LAD24NM"] if field in gdf.columns]
        add_geojson_layer(
            m,
            geojson_payload,
            gdf.columns,
            selected_id=active_fid,
            tooltip_fields=tooltip_fields or None,
        )
        map_output = render_map_st_folium(
            m,
            width="100%",
            height=500,
            returned_objects=["last_object_clicked", "last_object_clicked_tooltip"],
        )

    # Click synchronization
    clicked_fid = extract_clicked_fid(map_output, option_to_id, id_to_props)
    if clicked_fid and clicked_fid != active_fid and clicked_fid in id_to_display:
        st.session_state["maps_select_display"] = id_to_display[clicked_fid]
        st.session_state["maps_select_version"] += 1
        trigger_rerun()

    active_fid = (
        clicked_fid if clicked_fid and clicked_fid in id_to_props else active_fid
    )

    with col_info:
        st.markdown("### Authority Information")
        if active_fid:
            props = id_to_props.get(str(active_fid), {})
            display_columns = [
                "LAD24CD",
                "LAD24NM",
                "imd_rank",
                "total_population",
                "ICB",
            ]
            filtered_props = {
                col: props[col] for col in display_columns if col in props
            }
            name = props.get("LAD24NM") or props.get(id_field, active_fid)
            st.success(f"**Active Selection: {name}**")
            display_props_as_kv(filtered_props)
        else:
            st.info(
                "Click a region on the map or pick one from the selector to display its public health and demographic data."
            )

    st.subheader("Local Authorities Data Table")
    if overlay_df is not None:
        st.write(f"**Total Local Authorities/Districts:** {len(overlay_df)}")
        st.dataframe(pd.DataFrame(overlay_df), use_container_width=True)
    else:
        st.info(
            "ℹ️ No overlay data available — the local_districts.csv file could not be loaded."
        )


if __name__ == "__main__":
    render_maps_page()
