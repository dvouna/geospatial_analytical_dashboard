"""
Persistent map fragment for the FLC26 single-page dashboard.

``@st.fragment`` isolates this component so it only re-runs when its own
widgets interact (map click, authority selectbox).  Changing the topic in
the sidebar — or any other part of the right-hand panel — does NOT cause
the map to reload or re-render.

Flow
----
1. Fragment renders the selectbox + folium map from cached GeoJSON payload.
2. On click or selectbox change:
   - ``st.session_state["active_fid"]`` is updated.
   - ``st.rerun(scope="app")`` refreshes only the right panel (not the map).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import streamlit as st

from map_utils import (
    add_geojson_layer,
    create_folium_map,
    extract_clicked_fid,
    render_map_st_folium,
)


MAP_METRICS = {
    "Home": {
        "None (Simple Outline)": (None, None)
    },
    "Population": {
        "Total Population": ("Total Population", "YlGn"),
        "White Groups Total": ("Total - All White Groups", "YlGn"),
        "Asian Groups Total": ("Total - All Asian Groups", "YlGn"),
        "Black Groups Total": ("Total - All Black Groups", "YlGn"),
        "Mixed Groups Total": ("Total - All Mixed Groups", "YlGn"),
        "Other Ethnic Groups Total": ("Total - Other Ethnic Groups", "YlGn")
    },
    "Index of Multiple Deprivation": {
        "IMD Rank": ("Index of Multiple Deprivation (IMD) Rank", "PuOr"),
        "Income Rank": ("Income Rank", "PuOr"),
        "Employment Rank": ("Employment Rank", "PuOr"),
        "Education & Skills Rank": ("Education Skills and Training Rank", "PuOr"),
        "Health & Disability Rank": ("Health Deprivation and Disability Rank", "PuOr"),
        "Crime Rank": ("Crime Rank", "PuOr"),
        "Housing & Services Rank": ("Barriers to Housing and Services Rank", "PuOr"),
        "Living Environment Rank": ("Living Environment Rank", "PuOr")
    },
    "Cancer Incidence": {
        "Overall Rate": ("Rate", "YlOrRd"),
        "Total Incidence Count": ("Total_incidence", "YlOrRd"),
        "Bladder Cancer": ("bladder", "RdPu"),
        "Blood Cancer": ("blood cancer", "RdPu"),
        "Bowel Cancer": ("bowel", "RdPu"),
        "Brain Cancer": ("brain", "RdPu"),
        "Breast Cancer": ("breast", "RdPu"),
        "Head & Neck Cancer": ("head and neck", "RdPu"),
        "Kidney Cancer": ("kidney", "RdPu"),
        "Liver & Biliary Cancer": ("liver and biliary tract", "RdPu"),
        "Lung Cancer": ("lung", "RdPu"),
        "Ovarian Cancer": ("ovary", "RdPu"),
        "Pancreatic Cancer": ("pancreas", "RdPu"),
        "Prostate Cancer": ("prostate", "RdPu"),
        "Skin Cancer": ("skin", "RdPu"),
        "Uterine Cancer": ("uterus", "RdPu")
    }
}


@st.fragment
def render_persistent_map(
    geojson_payload: dict,
    options: List[str],
    option_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    id_to_props: Dict[str, dict],
    center: Tuple[float, float],
    tiles: str,
    attr: Optional[str],
    active_topic: str = "Home",
) -> None:
    """
    Render the persistent map panel.

    This function is decorated with ``@st.fragment``, meaning Streamlit
    re-runs only this block when its internal widgets change — not the whole
    page.  The map therefore survives topic navigation on the right panel.

    Parameters
    ----------
    geojson_payload : dict
        Prepared GeoJSON feature collection (output of ``prepare_geojson_payload``).
    options : list[str]
        Display names for the authority selectbox.
    option_to_id : dict
        Maps display name → feature ID.
    id_to_display : dict
        Maps feature ID → display name (inverse of ``option_to_id``).
    id_to_props : dict
        Maps feature ID → properties dict.
    center : tuple[float, float]
        (lat, lon) centre of the map viewport.
    tiles : str
        Folium tile layer string or URL template.
    attr : str or None
        Attribution string for custom tile layers.
    active_topic : str
        The active dashboard topic (drives choropleth selectors).
    """
    active_fid = st.session_state.get("active_fid")

    # ── Choropleth & Authority selectors ──────────────────────────────────────
    if active_topic == "Home":
        selected_index = 0
        if active_fid and active_fid in id_to_display:
            display_name = id_to_display[active_fid]
            if display_name in options:
                selected_index = options.index(display_name)

        selected_display = st.selectbox(
            "Select an authority:",
            options=options,
            index=selected_index,
            key="map_authority_select",
            help="Select a district in the East of England to highlight on the map and display details below. You can also click directly on the map.",
        )
        metric_field, colormap_name = None, None
    else:
        col_sel1, col_sel2 = st.columns([1, 1])
        with col_sel1:
            selected_index = 0
            if active_fid and active_fid in id_to_display:
                display_name = id_to_display[active_fid]
                if display_name in options:
                    selected_index = options.index(display_name)

            selected_display = st.selectbox(
                "Select an authority:",
                options=options,
                index=selected_index,
                key="map_authority_select",
                help="Select a district in the East of England to zoom in and view specific data. You can also click directly on the map.",
            )

        with col_sel2:
            topic_metrics = MAP_METRICS.get(active_topic, {"None (Simple Outline)": (None, None)})
            selected_metric_label = st.selectbox(
                "Color map by metric:",
                options=list(topic_metrics.keys()),
                key="choropleth_metric_select",
                help="Choose which variable colors the map. The darker the shade, the higher the value. The selected district stands out with a thick boundary.",
            )
            metric_field, colormap_name = topic_metrics[selected_metric_label]

    # Selectbox change → propagate to session state and refresh right panel.
    if selected_display:
        new_fid = option_to_id.get(selected_display)
        if new_fid != active_fid:
            st.session_state["active_fid"] = new_fid
            st.rerun(scope="app")
            return
        active_fid = new_fid

    # ── Build feature column list for tooltip ─────────────────────────────────
    features = geojson_payload.get("features", [])
    if features:
        prop_keys = list(features[0].get("properties", {}).keys())
        tooltip_fields = [f for f in ["fid", "LAD24NM"] if f in prop_keys] or prop_keys[:2]
    else:
        tooltip_fields = []

    # ── Render folium map ─────────────────────────────────────────────────────
    m = create_folium_map(center=center, tiles=tiles, attr=attr)
    add_geojson_layer(
        m,
        geojson_payload,
        gdf_columns=tooltip_fields,
        selected_id=active_fid,
        tooltip_fields=tooltip_fields or None,
        choropleth_metric=metric_field,
        colormap_name=colormap_name or "YlOrRd",
    )
    map_output = render_map_st_folium(
        m,
        width="100%",
        height=620,
        returned_objects=["last_object_clicked", "last_object_clicked_tooltip", "last_active_drawing"],
    )

    # ── Map click → update session state, refresh right panel ────────────────
    clicked_fid = extract_clicked_fid(map_output, option_to_id, id_to_props)
    if clicked_fid and clicked_fid != active_fid:
        st.session_state["active_fid"] = clicked_fid
        st.rerun(scope="app")
