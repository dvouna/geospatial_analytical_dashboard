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
    """
    active_fid = st.session_state.get("active_fid")

    # ── Authority selectbox ───────────────────────────────────────────────────
    # Determine which index to show based on the currently active feature.
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
    )

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
    )
    map_output = render_map_st_folium(
        m,
        width="100%",
        height=620,
        returned_objects=["last_object_clicked", "last_object_clicked_tooltip"],
    )

    # ── Map click → update session state, refresh right panel ────────────────
    clicked_fid = extract_clicked_fid(map_output, option_to_id, id_to_props)
    if clicked_fid and clicked_fid != active_fid:
        st.session_state["active_fid"] = clicked_fid
        st.rerun(scope="app")
