"""
FLC26 Geospatial Analytical Dashboard — single-page entry point.

Architecture (Option A — persistent map)
-----------------------------------------
The page is split into two permanent columns:

  Left  (col_map)   : @st.fragment-isolated folium map.
                       Re-runs only on map click / selectbox change.
                       Never reloads when the user switches topics.

  Right (col_panel)  : Topic-specific data panel.
                       Re-renders on topic change or region selection.
                       Swaps content without touching the map.

Topic navigation is driven by a sidebar radio button that writes to
``st.session_state["active_topic"]``.  The currently selected map region
is stored in ``st.session_state["active_fid"]`` and shared between the
map fragment and all topic panels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from config import check_environment, get_config
from map_fragment import render_persistent_map
from map_utils import (
    build_authority_options,
    compute_center,
    load_base_gdf,
    load_overlay_dataframe,
    merge_overlay,
    prepare_geojson_payload,
    render_map_settings,
    display_props_as_kv,
)

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"

TOPICS = [
    "Overview",
    "Population",
    "Index of Multiple Deprivation",
    "Cancer Incidence",
    "Research Assistant",
]

# ── Page config (must be the very first Streamlit call) ───────────────────────

st.set_page_config(
    page_title="Future Leaders Innovation Challenge",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Environment & config ──────────────────────────────────────────────────────

check_environment()
get_config()

# ── Cached data loaders ───────────────────────────────────────────────────────


@st.cache_data
def load_map_data() -> tuple:
    """Load and prepare all base map data. Runs once per session lifetime."""
    gdf = load_base_gdf(DATA_DIR)
    geojson_payload, id_field = prepare_geojson_payload(gdf)
    options, option_to_id, id_to_display, id_to_props = build_authority_options(
        geojson_payload
    )
    center = compute_center(gdf)
    return geojson_payload, options, option_to_id, id_to_display, id_to_props, center


@st.cache_data
def _load_population_overlay() -> pd.DataFrame:
    return load_overlay_dataframe(DATA_DIR / "population_detail.csv", index_col="fid")


@st.cache_data
def _load_districts_overlay() -> pd.DataFrame:
    return load_overlay_dataframe(DATA_DIR / "local_districts.csv", index_col="fid")


@st.cache_data
def _load_cancer_overlay() -> pd.DataFrame:
    try:
        return load_overlay_dataframe(DATA_DIR / "overall_incidence.csv", index_col="fid")
    except FileNotFoundError:
        return pd.DataFrame()


@st.cache_data
def _load_top5_overlay() -> pd.DataFrame:
    try:
        return load_overlay_dataframe(DATA_DIR / "top_5_cancers.csv", index_col="fid")
    except FileNotFoundError:
        return pd.DataFrame()


# ── Panel renderers (right-hand column) ──────────────────────────────────────


def _panel_overview(active_fid: str | None, id_to_props: dict) -> None:
    """Overview panel: authority summary and quick stats."""
    st.markdown("## 🗺️ East of England Dashboard")
    st.write(
        "Select a local authority on the map or from the dropdown to explore "
        "population, deprivation, and cancer incidence data."
    )

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("LAD24NM") or props.get("fid", active_fid)
        st.success(f"**Selected: {name}**")
        display_cols = {
            col: props[col]
            for col in ["LAD24CD", "LAD24NM", "imd_rank", "total_population", "ICB"]
            if col in props
        }
        if display_cols:
            display_props_as_kv(display_cols)
        else:
            display_props_as_kv(props)
    else:
        st.info("👆 Click a region on the map or use the selector to get started.")

        # Show a summary count of the available authorities
        try:
            df = _load_districts_overlay()
            st.metric("Local Authorities / Districts", len(df))
        except FileNotFoundError:
            pass


def _panel_population(active_fid: str | None, id_to_props: dict) -> None:
    """Population panel: demographic breakdown for the selected authority."""
    st.markdown("## 👥 Population Profiles")

    try:
        overlay_df = _load_population_overlay()
    except FileNotFoundError:
        st.error("❌ `population_detail.csv` not found in the data directory.")
        return

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("LAD24NM") or active_fid
        st.success(f"**{name}**")

        # Find the matching row in the overlay by fid
        if "fid" in overlay_df.columns:
            row = overlay_df[overlay_df["fid"].astype(str) == str(active_fid)]
        else:
            row = pd.DataFrame()

        if not row.empty:
            row_dict = row.iloc[0].to_dict()
            display_props_as_kv(
                {k: v for k, v in row_dict.items() if k not in ("fid", "geometry")}
            )
        else:
            st.info("No detailed population data available for this authority.")
    else:
        st.info("Select an authority on the map to view its population profile.")

    st.divider()
    st.subheader("All Authorities — Population Data")
    st.write(f"**{len(overlay_df)} districts**")
    st.dataframe(overlay_df.head(50), use_container_width=True)


def _panel_imd(active_fid: str | None, id_to_props: dict) -> None:
    """IMD panel: deprivation data for the selected authority."""
    st.markdown("## 📊 Index of Multiple Deprivation")

    try:
        overlay_df = _load_districts_overlay()
    except FileNotFoundError:
        st.error("❌ `local_districts.csv` not found in the data directory.")
        return

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("LAD24NM") or active_fid
        st.success(f"**{name}**")
        display_props_as_kv(
            {k: v for k, v in props.items() if k not in ("fid", "geometry", "LAD24CD")}
        )
    else:
        st.info("Select an authority on the map to view its deprivation data.")

    st.divider()
    st.subheader("All Authorities — Deprivation Data")
    st.write(f"**{len(overlay_df)} districts**")
    st.dataframe(overlay_df.head(50), use_container_width=True)


def _panel_cancer(active_fid: str | None, id_to_props: dict) -> None:
    """Cancer incidence panel for the selected authority."""
    st.markdown("## 🎗️ Cancer Incidence")

    SIDE_PANEL_COLS = [
        "Geography name ",
        "Total_incidence",
        "Rate",
        "breast",
        "bowel",
        "lung",
        "prostate",
        "skin",
    ]

    overall_df = _load_cancer_overlay()
    top5_df = _load_top5_overlay()

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("LAD24NM") or props.get("Geography name ", "") or active_fid
        st.success(f"**{name}**")

        display_cols = {
            col: props[col]
            for col in SIDE_PANEL_COLS
            if col in props and props[col] not in (None, "")
        }
        if display_cols:
            display_props_as_kv(display_cols)
        else:
            st.info("No cancer incidence data merged for this authority.")
    else:
        st.info("Select an authority on the map to view cancer incidence data.")

    st.divider()

    tab_overall, tab_top5 = st.tabs(
        ["📊 Overall Incidence by District", "🏆 Top 5 Cancers by Area & Age Group"]
    )

    with tab_overall:
        if not overall_df.empty:
            st.write(f"**{len(overall_df)} districts** — age-standardised rates.")
            st.dataframe(overall_df, use_container_width=True)
        else:
            st.info("Overall incidence data is not available.")

    with tab_top5:
        if not top5_df.empty:
            filter_col1, filter_col2 = st.columns(2)
            cancer_types = sorted(top5_df["Cancer Type"].unique().tolist())
            selected_cancers = filter_col1.multiselect(
                "Filter by cancer type:",
                options=cancer_types,
                default=cancer_types,
                key="app_cancer_type_filter",
            )
            area_names = sorted(top5_df["Geography name "].dropna().unique().tolist())
            selected_areas = filter_col2.multiselect(
                "Filter by district:",
                options=area_names,
                default=[],
                placeholder="All districts",
                key="app_area_filter",
            )
            filtered = top5_df[top5_df["Cancer Type"].isin(selected_cancers)]
            if selected_areas:
                filtered = filtered[filtered["Geography name "].isin(selected_areas)]
            st.write(f"**{len(filtered)} rows**")
            st.dataframe(filtered, use_container_width=True)
        else:
            st.info("Top-5 cancers data is not available.")


def _panel_research() -> None:
    """Research assistant panel — delegates to the existing page renderer."""
    from pages.research_assistant import render_research_assistant_page
    render_research_assistant_page()


# ── Session state defaults ────────────────────────────────────────────────────

st.session_state.setdefault("active_fid", None)
st.session_state.setdefault("active_topic", TOPICS[0])

# ── Page Header & Topic Navigation (Horizontal Menu Bar) ─────────────────────

# Header title
st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>📊 FLC26 Geospatial Analytical Dashboard</h1>", unsafe_allow_html=True)

# Render horizontal page navigation across full width of the screen
active_topic = st.radio(
    "Navigate to:",
    TOPICS,
    index=TOPICS.index(st.session_state["active_topic"]),
    key="topic_radio",
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state["active_topic"] = active_topic

st.markdown("---")

# ── Load base map data (cached) ───────────────────────────────────────────────

try:
    (
        geojson_payload,
        options,
        option_to_id,
        id_to_display,
        id_to_props,
        center,
    ) = load_map_data()
except Exception as exc:
    st.error(f"❌ Failed to load base map data: {exc}")
    st.stop()

# ── Resolve map tiles from session state ──────────────────────────────────────
from map_utils import get_map_tile_config
map_type_val = st.session_state.get("map_type_main", "Satellite (ArcGIS)")
tiles, attr = get_map_tile_config(map_type_val)

# ── Two-column layout ─────────────────────────────────────────────────────────

col_map, col_panel = st.columns([6, 4], gap="medium")

with col_map:
    render_persistent_map(
        geojson_payload=geojson_payload,
        options=options,
        option_to_id=option_to_id,
        id_to_display=id_to_display,
        id_to_props=id_to_props,
        center=center,
        tiles=tiles,
        attr=attr,
    )
    
    # Map Type settings inline immediately below the map display
    st.markdown("")  # Spacing
    render_map_settings(key="map_type_main", in_sidebar=False)

# ── Right panel: dispatch to the active topic ─────────────────────────────────

active_fid = st.session_state.get("active_fid")
active_topic = st.session_state["active_topic"]

with col_panel:
    if active_topic == "Overview":
        _panel_overview(active_fid, id_to_props)
    elif active_topic == "Population":
        _panel_population(active_fid, id_to_props)
    elif active_topic == "Index of Multiple Deprivation":
        _panel_imd(active_fid, id_to_props)
    elif active_topic == "Cancer Incidence":
        _panel_cancer(active_fid, id_to_props)
    elif active_topic == "Research Assistant":
        _panel_research()
