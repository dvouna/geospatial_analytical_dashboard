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
    get_map_tile_config,
)
from utils.data_loader_cancer import get_cancer_overall_df, get_cancer_top5_df

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"

TOPICS = [
    "Home",
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

# ── Custom CSS for Premium UX/UI ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }
    
    /* Header banner styling */
    .gradient-title {
        background: linear-gradient(135deg, #1f77b4 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .sub-title {
        text-align: center;
        font-size: 1.05rem;
        color: #6c757d;
        margin-bottom: 25px;
    }
    
    /* Glassmorphic Columns */
    [data-testid="column"] {
        background-color: #ffffff;
        border: 1px solid #eef1f6;
        border-radius: 16px;
        padding: 24px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.015);
    }
    
    /* Sleek metric KPI card */
    .kpi-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.01);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.04);
        border-color: #cbd5e1;
    }
    .kpi-label {
        font-size: 0.82rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.55rem;
        color: #0f172a;
        font-weight: 700;
    }
    .kpi-badge {
        display: inline-block;
        padding: 3px 10px;
        font-size: 0.72rem;
        border-radius: 20px;
        font-weight: 600;
        margin-top: 8px;
    }
    .badge-danger {
        background-color: #fee2e2;
        color: #ef4444;
    }
    .badge-warning {
        background-color: #fef3c7;
        color: #d97706;
    }
    .badge-success {
        background-color: #dcfce7;
        color: #15803d;
    }
    
    /* Horizontal selector styling override */
    div.row-widget.stRadio > div[role="radiogroup"] {
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 30px;
        border: 1px solid #e2e8f0;
        display: flex;
        justify-content: center;
        gap: 8px;
        width: fit-content;
        margin: 0 auto 20px auto;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label {
        background: transparent;
        padding: 8px 20px;
        border-radius: 20px;
        font-weight: 600;
        color: #475569;
        border: none;
        transition: all 0.25s ease;
        cursor: pointer;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        color: #1f77b4;
        background-color: rgba(31, 119, 180, 0.08);
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #1f77b4;
        color: white !important;
        box-shadow: 0 4px 6px rgba(31, 119, 180, 0.15);
    }
    </style>
    """,
    unsafe_allow_html=True
)

def render_kpi_card(label: str, value: str, badge_text: str | None = None, badge_type: str | None = None) -> None:
    badge_html = ""
    if badge_text:
        badge_class = f"badge-{badge_type}" if badge_type in ["danger", "warning", "success"] else "badge-success"
        badge_html = f'<div class="kpi-badge {badge_class}">{badge_text}</div>'
        
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True
    )

# ── Cached data loaders ───────────────────────────────────────────────────────


@st.cache_data
def load_map_data() -> tuple:
    """Load, merge all overlays, and prepare base map data."""
    # 1. Load base GDF
    gdf = load_base_gdf(DATA_DIR)
    
    # 2. Merge Population overlay
    try:
        pop_df = load_overlay_dataframe(DATA_DIR / "population_detail.csv", index_col="fid")
        gdf = merge_overlay(gdf, pop_df, base_key="fid", overlay_key="fid")
    except Exception as exc:
        st.warning(f"⚠️ Failed to merge population data: {exc}")

    # 3. Merge IMD overlay (iod_2025.csv)
    try:
        iod_df = load_overlay_dataframe(DATA_DIR / "iod_2025.csv")
        key_col = "Local Authority District code (2024)"
        if key_col in iod_df.columns:
            iod_df[key_col] = iod_df[key_col].astype(str).str.strip()
            gdf = merge_overlay(gdf, iod_df, base_key="LAD24CD", overlay_key=key_col)
        else:
            st.warning(f"⚠️ '{key_col}' not found in iod_2025.csv")
    except Exception as exc:
        st.warning(f"⚠️ Failed to merge deprivation data: {exc}")

    # 4. Merge Cancer overlay (cancer_2018_2022.csv via get_cancer_overall_df)
    try:
        cancer_df = get_cancer_overall_df(year_filter="all")
        # Prevent duplicate columns (e.g. LAD24NM, total_population) that cause GeoDataFrame validation to fail
        cols_to_keep = ["fid"] + [c for c in cancer_df.columns if c not in gdf.columns]
        cancer_df = cancer_df[cols_to_keep]
        gdf = merge_overlay(gdf, cancer_df, base_key="fid", overlay_key="fid")
    except Exception as exc:
        st.warning(f"⚠️ Failed to merge cancer incidence data: {exc}")

    # 5. Build GeoJSON payload
    geojson_payload, id_field = prepare_geojson_payload(gdf, simplify_tolerance=0.001)
    
    # 6. Build options and lookup dicts
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
        return get_cancer_overall_df(year_filter="all")
    except Exception:
        return pd.DataFrame()


@st.cache_data
def _load_top5_overlay() -> pd.DataFrame:
    try:
        return get_cancer_top5_df(year_filter="all")
    except Exception:
        return pd.DataFrame()


@st.cache_data
def _load_iod_overlay() -> pd.DataFrame:
    try:
        return load_overlay_dataframe(DATA_DIR / "iod_2025.csv")
    except FileNotFoundError:
        return pd.DataFrame()


# ── Panel renderers (right-hand column) ──────────────────────────────────────


def _panel_overview(active_fid: str | None, id_to_props: dict) -> None:
    """Overview panel: authority summary, mission statement, and quick start."""
    
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, rgba(31, 119, 180, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%); 
                    border: 1px solid rgba(31, 119, 180, 0.2); border-radius: 12px; padding: 24px; margin-bottom: 25px;">
            <h3 style="margin-top: 0; color: #1e293b; font-family: 'Outfit', sans-serif;">
                🎯 Platform Mission
            </h3>
            <p style="color: #475569; font-size: 1.05rem; line-height: 1.6; margin-bottom: 0;">
                This geospatial analytical platform integrates population demographics, deprivation subdomains, and cancer incidence datasets. 
                Its primary objective is to assist public health analysts and policymakers in 
                <strong>identifying deprived communities</strong> that would benefit most from targeted campaigns to improve early cancer detection.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("LAD24NM") or props.get("fid", active_fid)
        st.success(f"**Selected District: {name}**")
        
        col1, col2 = st.columns(2)
        with col1:
            pop_val = f"{int(float(props.get('total_population'))):,}" if props.get('total_population') is not None else "N/A"
            render_kpi_card("Total Population", pop_val)
            
            icb_val = str(props.get('ICB', 'N/A'))
            render_kpi_card("NHS ICB Region", icb_val)
        with col2:
            imd_val = f"#{int(float(props.get('imd_rank')))}" if props.get('imd_rank') is not None else "N/A"
            badge_text, badge_type = None, None
            if props.get('imd_rank') is not None:
                rank = int(float(props.get('imd_rank')))
                if rank <= 50:
                    badge_text, badge_type = "High Deprivation (Top 15%)", "danger"
                elif rank <= 150:
                    badge_text, badge_type = "Medium Deprivation", "warning"
                else:
                    badge_text, badge_type = "Low Deprivation", "success"
            render_kpi_card("Deprivation Rank", imd_val, badge_text, badge_type)
            
            code_val = str(props.get('LAD24CD', 'N/A'))
            render_kpi_card("District Code", code_val)
    else:
        st.markdown(
            """
            <div style="background-color: #fef3c7; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px; margin-bottom: 20px; color: #b45309; font-weight: 500;">
                👆 <strong>Click a region on the map</strong> or select one from the dropdown on the left to get started.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### 🚀 Quick-Start Guide")
        st.markdown(
            """
            1. **Select a District**: Click any local authority area on the map or search using the dropdown.
            2. **Analyze Patterns (Choropleths)**: Select a variable (e.g. IMD Rank, Lung Cancer Rate) in the **Color map by metric** dropdown below the authority selector to recolor the map.
            3. **Explore Sub-metrics**: Navigate to the **Population**, **Deprivation**, or **Cancer** tabs above to view specific KPIs and complete district-level tables.
            4. **Conversational AI Analysis**: Head over to the **Research Assistant** tab to ask cross-dataset questions powered by Google Gemini (e.g. *"Which districts have high deprivation and high bowel cancer rates?"*).
            """
        )

        # Show a summary count of the available authorities
        try:
            df = _load_districts_overlay()
            st.metric("Total Districts Analyzed", len(df))
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
        st.success(f"**Selected District: {name}**")

        col1, col2 = st.columns(2)
        with col1:
            pop_val = f"{int(float(props.get('total_population'))):,}" if props.get('total_population') is not None else "N/A"
            render_kpi_card("Total Population", pop_val)
            
            white_val = f"{int(float(props.get('White Sum'))):,}" if props.get('White Sum') is not None else "N/A"
            render_kpi_card("White Group", white_val)
            
            asian_val = f"{int(float(props.get('Asian Sum'))):,}" if props.get('Asian Sum') is not None else "N/A"
            render_kpi_card("Asian Group", asian_val)
        with col2:
            black_val = f"{int(float(props.get('Black Sum'))):,}" if props.get('Black Sum') is not None else "N/A"
            render_kpi_card("Black Group", black_val)
            
            mixed_val = f"{int(float(props.get('Mixed Sum'))):,}" if props.get('Mixed Sum') is not None else "N/A"
            render_kpi_card("Mixed Group", mixed_val)
            
            others_val = f"{int(float(props.get('Others Sum'))):,}" if props.get('Others Sum') is not None else "N/A"
            render_kpi_card("Others Group", others_val)
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
        overlay_df = _load_iod_overlay()
    except FileNotFoundError:
        st.error("❌ `iod_2025.csv` not found in the data directory.")
        return

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("LAD24NM") or active_fid
        st.success(f"**Selected District: {name}**")
        
        col1, col2 = st.columns(2)
        with col1:
            imd_rank = props.get("Index of Multiple Deprivation (IMD) Rank")
            imd_val = f"#{int(float(imd_rank))}" if imd_rank is not None else "N/A"
            
            badge_text, badge_type = None, None
            if imd_rank is not None:
                rank = int(float(imd_rank))
                if rank <= 50:
                    badge_text, badge_type = "High Deprivation (Top 15%)", "danger"
                elif rank <= 150:
                    badge_text, badge_type = "Medium Deprivation", "warning"
                else:
                    badge_text, badge_type = "Low Deprivation", "success"
            render_kpi_card("IMD Overall Rank", imd_val, badge_text, badge_type)
            
            inc_rank = props.get("Income Rank")
            inc_val = f"#{int(float(inc_rank))}" if inc_rank is not None else "N/A"
            render_kpi_card("Income Rank", inc_val)
            
            emp_rank = props.get("Employment Rank")
            emp_val = f"#{int(float(emp_rank))}" if emp_rank is not None else "N/A"
            render_kpi_card("Employment Rank", emp_val)
            
            edu_rank = props.get("Education Skills and Training Rank")
            edu_val = f"#{int(float(edu_rank))}" if edu_rank is not None else "N/A"
            render_kpi_card("Education & Skills Rank", edu_val)
        with col2:
            health_rank = props.get("Health Deprivation and Disability Rank")
            health_val = f"#{int(float(health_rank))}" if health_rank is not None else "N/A"
            render_kpi_card("Health & Disability Rank", health_val)
            
            crime_rank = props.get("Crime Rank")
            crime_val = f"#{int(float(crime_rank))}" if crime_rank is not None else "N/A"
            render_kpi_card("Crime Rank", crime_val)
            
            house_rank = props.get("Barriers to Housing and Services Rank")
            house_val = f"#{int(float(house_rank))}" if house_rank is not None else "N/A"
            render_kpi_card("Housing & Services Rank", house_val)
            
            env_rank = props.get("Living Environment Rank")
            env_val = f"#{int(float(env_rank))}" if env_rank is not None else "N/A"
            render_kpi_card("Living Environment Rank", env_val)
    else:
        st.info("Select an authority on the map to view its deprivation data.")

    st.divider()
    st.subheader("All Authorities — Deprivation Data (IoD 2025)")
    if not overlay_df.empty:
        st.write(f"**{len(overlay_df)} districts**")
        st.dataframe(overlay_df.head(50), use_container_width=True)
    else:
        st.info("Deprivation overlay data is not available.")


def _panel_cancer(active_fid: str | None, id_to_props: dict) -> None:
    """Cancer incidence panel for the selected authority."""
    st.markdown("## 🎗️ Cancer Incidence")


    overall_df = _load_cancer_overlay()
    top5_df = _load_top5_overlay()

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("LAD24NM") or props.get("Geography name ", "") or active_fid
        st.success(f"**Selected District: {name}**")

        col1, col2 = st.columns(2)
        with col1:
            rate_val = props.get("Rate")
            rate_str = f"{float(rate_val):.1f} per 100k" if rate_val is not None else "N/A"
            
            badge_text, badge_type = None, None
            if rate_val is not None:
                rate = float(rate_val)
                if rate >= 600:
                    badge_text, badge_type = "High Incidence", "danger"
                elif rate >= 500:
                    badge_text, badge_type = "Medium Incidence", "warning"
                else:
                    badge_text, badge_type = "Low Incidence", "success"
            render_kpi_card("Overall Cancer Rate", rate_str, badge_text, badge_type)
            
            inc_val = props.get("Total_incidence")
            inc_str = f"{int(float(inc_val)):,}" if inc_val is not None else "N/A"
            render_kpi_card("Total Diagnosed Cases", inc_str)
            
            breast_val = props.get("breast")
            breast_str = f"{float(breast_val):.1f}" if breast_val is not None else "N/A"
            render_kpi_card("Breast Cancer Rate", breast_str)
            
            bowel_val = props.get("bowel")
            bowel_str = f"{float(bowel_val):.1f}" if bowel_val is not None else "N/A"
            render_kpi_card("Bowel Cancer Rate", bowel_str)
        with col2:
            lung_val = props.get("lung")
            lung_str = f"{float(lung_val):.1f}" if lung_val is not None else "N/A"
            render_kpi_card("Lung Cancer Rate", lung_str)
            
            prostate_val = props.get("prostate")
            prostate_str = f"{float(prostate_val):.1f}" if prostate_val is not None else "N/A"
            render_kpi_card("Prostate Cancer Rate", prostate_str)
            
            skin_val = props.get("skin")
            skin_str = f"{float(skin_val):.1f}" if skin_val is not None else "N/A"
            render_kpi_card("Skin Cancer Rate", skin_str)
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
    import importlib
    module = importlib.import_module("pages.5_AI_Research_Assistant")
    module.render_research_assistant_page()


# ── Session state defaults ────────────────────────────────────────────────────

st.session_state.setdefault("active_fid", None)
st.session_state.setdefault("active_topic", TOPICS[0])

# ── Page Header & Topic Navigation (Horizontal Menu Bar) ─────────────────────

# Header title
st.markdown("<div class='gradient-title'>📊 FLC26 Geospatial Analytical Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Public Health, Deprivation and Demographics Explorer — East of England</div>", unsafe_allow_html=True)

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
map_type_val = st.session_state.get("map_type_main", "Satellite (ArcGIS)")
tiles, attr = get_map_tile_config(map_type_val)

# ── Two-column layout ─────────────────────────────────────────────────────────

active_fid = st.session_state.get("active_fid")
active_topic = st.session_state["active_topic"]

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
        active_topic=active_topic,
    )
    
    # Map Type settings inline immediately below the map display
    st.markdown("")  # Spacing
    render_map_settings(key="map_type_main", in_sidebar=False)

    # Dynamic Population Ethnic Group Chart below settings
    if active_topic == "Population" and active_fid:
        try:
            pop_df = _load_population_overlay()
            if not pop_df.empty:
                row = pop_df[pop_df.index.astype(str) == str(active_fid)]
                if not row.empty:
                    props = id_to_props.get(str(active_fid), {})
                    name = props.get("LAD24NM") or active_fid
                    
                    target_cols = {
                        "White": "White Sum",
                        "Asian": "Asian Sum",
                        "Black": "Black Sum",
                        "Mixed": "Mixed Sum",
                        "Others": "Others Sum"
                    }
                    
                    labels = []
                    values = []
                    for label, col in target_cols.items():
                        if col in row.columns:
                            val_str = str(row.iloc[0][col])
                            clean_val = "".join(c for c in val_str if c.isdigit() or c == ".")
                            try:
                                values.append(float(clean_val))
                                labels.append(label)
                            except ValueError:
                                pass
                    
                    if values and sum(values) > 0:
                        import plotly.express as px
                        st.markdown("---")
                        st.markdown(f"#### 👥 Ethnic Group Proportion in {name}")
                        fig = px.pie(
                            names=labels,
                            values=values,
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        fig.update_layout(
                            margin=dict(t=20, b=20, l=10, r=10),
                            height=280,
                            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not render population chart: {exc}")

# ── Right panel: dispatch to the active topic ─────────────────────────────────

with col_panel:
    if active_topic == "Home":
        _panel_overview(active_fid, id_to_props)
    elif active_topic == "Population":
        _panel_population(active_fid, id_to_props)
    elif active_topic == "Index of Multiple Deprivation":
        _panel_imd(active_fid, id_to_props)
    elif active_topic == "Cancer Incidence":
        _panel_cancer(active_fid, id_to_props)
    elif active_topic == "Research Assistant":
        _panel_research()
