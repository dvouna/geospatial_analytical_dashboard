"""
Population Profiles Page
"""

import streamlit as st
import pandas as pd
import folium
import json
import geopandas as gpd
from streamlit_folium import st_folium
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


def render_population_page():
    st.title("Population Profiles")
    st.write("Population data for East of England local authorities.")

    st.sidebar.header("Data Source")
    st.sidebar.write("**East of England Local Authorities Population Data**")

    # Load shared base data
    gdf = load_base_gdf(DATA_DIR)
    if gdf is None:
        st.error("Unable to load base GeoJSON data. Please check the data directory.")
        return

    tiles, attr = render_map_settings(key="map_type_population")

    # Overlay Population data
    overlay_candidate = load_overlay_dataframe(
        DATA_DIR / "population_detail.csv", index_col="fid"
    )
    # ensure fid is string
    if "fid" in overlay_candidate.columns:
        overlay_candidate["fid"] = overlay_candidate["fid"].astype(str)
    gdf = merge_overlay(gdf, overlay_candidate, base_key="fid", overlay_key="fid")

    # Payload
    centre = compute_center(gdf)
    geojson_payload, id_field = prepare_geojson_payload(gdf)

    # Select box options
    options, option_to_id, id_to_display, id_to_props = build_authority_options(
        geojson_payload
    )

    # State initialization
    if "pop_select_display" not in st.session_state:
        st.session_state["pop_select_display"] = options[0] if options else None
    if "pop_select_version" not in st.session_state:
        st.session_state["pop_select_version"] = 0

    current_display = st.session_state.get("pop_select_display")
    if current_display not in option_to_id and options:
        current_display = options[0]
        st.session_state["pop_select_display"] = current_display

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
                key=f"pop_select_display_{st.session_state['pop_select_version']}",
            )
            if options
            else None
        )

        if selected_display:
            st.session_state["pop_select_display"] = selected_display

        active_fid = option_to_id.get(selected_display) if selected_display else None

        m = create_folium_map(center=centre, tiles=tiles, attr=attr)
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
        st.session_state["pop_select_display"] = id_to_display[clicked_fid]
        st.session_state["pop_select_version"] += 1
        trigger_rerun()

    active_fid = (
        clicked_fid if clicked_fid and clicked_fid in id_to_props else active_fid
    )

    with col_info:
        st.markdown("### Authority Information")
        if active_fid:
            props = id_to_props.get(str(active_fid), {})
            name = props.get("LAD24NM") or props.get(id_field, active_fid)
            st.success(f"**Active Selection: {name}**")
            display_props_as_kv(props)
        else:
            st.info(
                "Click a region on the map or pick one from the selector to display its public health and demographic data."
            )

    st.subheader("Local Authorities Data Table")
    st.write(f"**Total Local Authorities/Districts:** {len(overlay_candidate)}")
    df_preview = pd.DataFrame(overlay_candidate)
    st.dataframe(df_preview.head(50), use_container_width=True)


if __name__ == "__main__":
    render_population_page()
