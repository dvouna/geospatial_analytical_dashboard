"""
Cancer Health Dashboard — Home Page
------------------------------------
Main dashboard content: persistent map + topic panels.
This file is loaded by the st.navigation router in app.py.
Global setup (CSS, dark mode) is already applied by the router.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from map_fragment import render_persistent_map
from map_utils import (
    build_authority_options,
    compute_center,
    get_map_tile_config,
    load_base_gdf,
    load_overlay_dataframe,
    merge_overlay,
    prepare_geojson_payload,
    render_map_settings,
)
from utils.data_loader_cancer import get_cancer_overall_df, get_cancer_top5_df
from visualizer import FLC26_QUALITATIVE

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"

TOPICS = [
    "Home",
    "Population",
    "Index of Multiple Deprivation",
    "Cancer Incidence",
    "Research Assistant",
]

# ── KPI Card renderer ─────────────────────────────────────────────────────────


def render_kpi_card(
    label: str,
    value: str,
    badge_text: str | None = None,
    badge_type: str | None = None,
) -> None:
    badge_html = ""
    if badge_text:
        badge_class = (
            f"badge-{badge_type}"
            if badge_type in ["danger", "warning", "success"]
            else "badge-success"
        )
        badge_html = f'<div class="kpi-badge {badge_class}">{badge_text}</div>'

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Cached data loaders ───────────────────────────────────────────────────────


@st.cache_data
def load_map_data() -> tuple:
    """Load, merge all overlays, and prepare base map data."""
    gdf = load_base_gdf(DATA_DIR)

    try:
        pop_df = load_overlay_dataframe(
            DATA_DIR / "population_detail.csv", index_col="fid"
        )
        gdf = merge_overlay(gdf, pop_df, base_key="fid", overlay_key="fid")
    except Exception as exc:
        st.warning(f"⚠️ Failed to merge population data: {exc}")

    try:
        iod_df = load_overlay_dataframe(DATA_DIR / "iod_2025.csv")
        if "District Code" in iod_df.columns:
            iod_df["District Code"] = iod_df["District Code"].astype(str).str.strip()
            gdf = merge_overlay(gdf, iod_df, base_key="District Code", overlay_key="District Code")
        else:
            st.warning("⚠️ 'District Code' not found in iod_2025.csv")
    except Exception as exc:
        st.warning(f"⚠️ Failed to merge deprivation data: {exc}")

    try:
        cancer_df = get_cancer_overall_df(year_filter="all")
        cols_to_keep = ["fid"] + [c for c in cancer_df.columns if c not in gdf.columns]
        cancer_df = cancer_df[cols_to_keep]
        gdf = merge_overlay(gdf, cancer_df, base_key="fid", overlay_key="fid")
    except Exception as exc:
        st.warning(f"⚠️ Failed to merge cancer incidence data: {exc}")

    geojson_payload, id_field = prepare_geojson_payload(gdf, simplify_tolerance=0.001)
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
    """Load base district attributes from the GeoJSON (no geometry)."""
    import geopandas as gpd
    gdf = gpd.read_file(str(DATA_DIR / "base_gdf_1.geojson"))
    return pd.DataFrame(gdf.drop(columns="geometry"))


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


def _get_clean_kpi_value(props: dict, key: str) -> str:
    """Safely retrieve, clean (commas/spaces/newlines), and format numeric KPI values from geojson properties."""
    val = None
    cleaned_target_key = key.replace("\n", " ").replace("\r", "").strip()
    for pk, pv in props.items():
        if pk.replace("\n", " ").replace("\r", "").strip() == cleaned_target_key:
            val = pv
            break
            
    if val is not None:
        try:
            clean_str = str(val).replace(",", "").strip()
            return f"{int(float(clean_str)):,}"
        except ValueError:
            return str(val)
    return "N/A"


# ── Panel renderers ───────────────────────────────────────────────────────────


def _panel_overview(active_fid: str | None, id_to_props: dict) -> None:
    """Overview panel: authority summary, mission statement, and quick start."""
    with st.popover("💡 Guide: Using the Home Page", use_container_width=True):
        st.markdown(
            """
            **How to Explore the Dashboard:**
            - **Select a Topic**: Use the radio buttons above (e.g., *Population*, *Cancer Incidence*) to explore different domains.
            - **Select a District**: Click any region on the map or select one from the dropdown to display its metrics.
            - **Visual Highlights**: The selected district is highlighted by a thick boundary on the map, and its details display in the right-hand panel.
            """
        )

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("District Name") or props.get("fid", active_fid)
        st.success(f"**Selected District: {name}**")

        col1, col2 = st.columns(2)
        with col1:
            pop_val = _get_clean_kpi_value(props, "Total Population")
            if pop_val == "N/A":
                pop_val = _get_clean_kpi_value(props, "total_population")
            render_kpi_card("Total Population", pop_val)

            icb_val = str(props.get("ICB", "N/A"))
            render_kpi_card("NHS ICB Region", icb_val)
        with col2:
            imd_val = (
                f"#{int(float(props.get('imd_rank')))}"
                if props.get("imd_rank") is not None
                else "N/A"
            )
            badge_text, badge_type = None, None
            if props.get("imd_rank") is not None:
                rank = int(float(props.get("imd_rank")))
                if rank <= 50:
                    badge_text, badge_type = "High Deprivation (Top 15%)", "danger"
                elif rank <= 150:
                    badge_text, badge_type = "Medium Deprivation", "warning"
                else:
                    badge_text, badge_type = "Low Deprivation", "success"
            render_kpi_card("Deprivation Rank", imd_val, badge_text, badge_type)

            code_val = str(props.get("District Code", "N/A"))
            render_kpi_card("District Code", code_val)
    else:
        st.markdown(
            """
            <div style="background-color: #fef3c7; border: 1px dashed #f59e0b; border-radius: 8px;
                        padding: 15px; margin-bottom: 20px; color: #b45309; font-weight: 500;">
                👆 <strong>Click a region on the map</strong> or select one from the dropdown on the left to get started.
            </div>
            """,
            unsafe_allow_html=True,
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

        try:
            df = _load_districts_overlay()
            st.metric("Total Districts Analyzed", len(df))
        except FileNotFoundError:
            pass


def _panel_population(active_fid: str | None, id_to_props: dict) -> None:
    """Population panel: demographic breakdown for the selected authority."""
    st.markdown("## 👥 Population Profiles")
    with st.popover("💡 Guide: Analyzing Demographics", use_container_width=True):
        st.markdown(
            """
            **How to Analyze Population Data:**
            1. Select the **Population** tab using the radio buttons above.
            2. Choose a district on the map or search using the dropdown.
            3. Choose which ethnic group to color the map by in the **Color map by metric** dropdown (under the map).
            4. The map will display a spectrum: **the darker the shade, the higher the count/value of the metric**.
            5. The selected district stands out with a thick bold boundary, and its ethnic proportion pie chart appears below the map settings.
            """
        )

    try:
        overlay_df = _load_population_overlay()
    except FileNotFoundError:
        st.error("❌ `population_detail.csv` not found in the data directory.")
        return

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("District Name") or active_fid
        st.success(f"**Selected District: {name}**")

        col1, col2 = st.columns(2)
        with col1:
            pop_val = _get_clean_kpi_value(props, "Total Population")
            render_kpi_card("Total Population", pop_val)
            white_val = _get_clean_kpi_value(props, "Total - All White Groups")
            render_kpi_card("White Group", white_val)
            asian_val = _get_clean_kpi_value(props, "Total - All Asian Groups")
            render_kpi_card("Asian Group", asian_val)
        with col2:
            black_val = _get_clean_kpi_value(props, "Total - All Black Groups")
            render_kpi_card("Black Group", black_val)
            mixed_val = _get_clean_kpi_value(props, "Total - All Mixed Groups")
            render_kpi_card("Mixed Group", mixed_val)
            others_val = _get_clean_kpi_value(props, "Total - Other Ethnic Groups")
            render_kpi_card("Others Group", others_val)

        # ── Detailed Subgroup Breakdowns ──────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Subgroup Breakdown")
        
        subgroups = {
            "White Group": [
                ("White British", "White: English, Welsh, Scottish, Northern Irish or British (number)"),
                ("White Irish", "White: Irish (number)"),
                ("Gypsy or Irish Traveller", "White: Gypsy or Irish Traveller (number)"),
                ("White Roma", "White: Roma (number)"),
                ("Other White", "White: Other White (number)")
            ],
            "Asian Group": [
                ("Indian", "Asian, Asian British or Asian Welsh: Indian (number)"),
                ("Pakistani", "Asian, Asian British or Asian Welsh: Pakistani (number)"),
                ("Bangladeshi", "Asian, Asian British or Asian Welsh: Bangladeshi (number)"),
                ("Chinese", "Asian, Asian British or Asian Welsh: Chinese (number)"),
                ("Other Asian", "Asian, Asian British or Asian Welsh: Other Asian (number)")
            ],
            "Black Group": [
                ("African", "Black, Black British, Black Welsh, Caribbean or African: African (number)"),
                ("Caribbean", "Black, Black British, Black Welsh, Caribbean or African: Caribbean (number)"),
                ("Other Black", "Black, Black British, Black Welsh, Caribbean or African: Other Black (number)")
            ],
            "Mixed Group": [
                ("White and Asian", "Mixed or Multiple ethnic groups: White and Asian (number)"),
                ("White and Black African", "Mixed or Multiple ethnic groups: White and Black African (number)"),
                ("White and Black Caribbean", "Mixed or Multiple ethnic groups: White and Black Caribbean (number)"),
                ("Other Mixed", "Mixed or Multiple ethnic groups: Other Mixed or Multiple ethnic groups (number)")
            ],
            "Others Group": [
                ("Arab", "Other ethnic group: Arab (number)"),
                ("Any other ethnic group", "Other ethnic group: Any other ethnic group (number)")
            ]
        }

        for group_name, sub_list in subgroups.items():
            with st.expander(f"🔍 {group_name} Subgroup Details"):
                for label, col_key in sub_list:
                    formatted_val = _get_clean_kpi_value(props, col_key)
                    st.write(f"• **{label}**: {formatted_val}")
    else:
        st.info("Select an authority on the map to view its population profile.")

    st.divider()
    st.subheader("All Authorities — Population Data")
    st.write(f"**{len(overlay_df)} districts**")
    st.dataframe(overlay_df.head(50), width="stretch")


def _panel_imd(active_fid: str | None, id_to_props: dict) -> None:
    """IMD panel: deprivation data for the selected authority."""
    st.markdown("## 📊 Index of Multiple Deprivation")
    with st.popover("💡 Guide: Deprivation Ranks", use_container_width=True):
        st.markdown(
            """
            **How to Analyze Deprivation Data:**
            1. Select the **Index of Multiple Deprivation** tab above.
            2. Choose a district to view its rankings across the 8 subdomains (Income, Employment, Education, etc.) in the cards below.
            3. Use the **Color map by metric** dropdown under the map to color by overall IMD Rank or subdomains.
            4. **Remember**: Ranks range from 1 (most deprived) to 296 (least deprived). Lower rank numbers represent higher deprivation.
            """
        )

    try:
        overlay_df = _load_iod_overlay()
    except FileNotFoundError:
        st.error("❌ `iod_2025.csv` not found in the data directory.")
        return

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("District Name") or active_fid
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
            render_kpi_card(
                "Income Rank",
                f"#{int(float(inc_rank))}" if inc_rank is not None else "N/A",
            )
            emp_rank = props.get("Employment Rank")
            render_kpi_card(
                "Employment Rank",
                f"#{int(float(emp_rank))}" if emp_rank is not None else "N/A",
            )
            edu_rank = props.get("Education Skills and Training Rank")
            render_kpi_card(
                "Education & Skills Rank",
                f"#{int(float(edu_rank))}" if edu_rank is not None else "N/A",
            )
        with col2:
            health_rank = props.get("Health Deprivation and Disability Rank")
            render_kpi_card(
                "Health & Disability Rank",
                f"#{int(float(health_rank))}" if health_rank is not None else "N/A",
            )
            crime_rank = props.get("Crime Rank")
            render_kpi_card(
                "Crime Rank",
                f"#{int(float(crime_rank))}" if crime_rank is not None else "N/A",
            )
            house_rank = props.get("Barriers to Housing and Services Rank")
            render_kpi_card(
                "Housing & Services Rank",
                f"#{int(float(house_rank))}" if house_rank is not None else "N/A",
            )
            env_rank = props.get("Living Environment Rank")
            render_kpi_card(
                "Living Environment Rank",
                f"#{int(float(env_rank))}" if env_rank is not None else "N/A",
            )
    else:
        st.info("Select an authority on the map to view its deprivation data.")

    st.divider()
    st.subheader("All Authorities — Deprivation Data (IoD 2025)")
    if not overlay_df.empty:
        st.write(f"**{len(overlay_df)} districts**")
        st.dataframe(overlay_df.head(50), width="stretch")
    else:
        st.info("Deprivation overlay data is not available.")


def _panel_cancer(active_fid: str | None, id_to_props: dict) -> None:
    """Cancer incidence panel for the selected authority."""
    st.markdown("## 🎗️ Cancer Incidence")
    with st.popover("💡 Guide: Cancer Incidence Rates", use_container_width=True):
        st.markdown(
            """
            **How to Explore Cancer Rates:**
            1. Select the **Cancer Incidence** tab above.
            2. Select a district to display its age-standardised rate (per 100k) and total diagnosed cases.
            3. Choose a specific cancer type or overall rate in the **Color map by metric** dropdown under the map to dynamically color the tiles.
            4. Darker shades indicate higher incidence rates.
            """
        )

    overall_df = _load_cancer_overlay()
    top5_df = _load_top5_overlay()

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("District Name") or active_fid
        st.success(f"**Selected District: {name}**")

        col1, col2 = st.columns(2)
        with col1:
            rate_val = props.get("Rate")
            rate_str = (
                f"{float(rate_val):.1f} per 100k" if rate_val is not None else "N/A"
            )
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
            render_kpi_card(
                "Total Diagnosed Cases",
                f"{int(float(inc_val)):,}" if inc_val is not None else "N/A",
            )
            breast_val = props.get("breast")
            render_kpi_card(
                "Breast Cancer Rate",
                f"{float(breast_val):.1f}" if breast_val is not None else "N/A",
            )
            bowel_val = props.get("bowel")
            render_kpi_card(
                "Bowel Cancer Rate",
                f"{float(bowel_val):.1f}" if bowel_val is not None else "N/A",
            )
        with col2:
            lung_val = props.get("lung")
            render_kpi_card(
                "Lung Cancer Rate",
                f"{float(lung_val):.1f}" if lung_val is not None else "N/A",
            )
            prostate_val = props.get("prostate")
            render_kpi_card(
                "Prostate Cancer Rate",
                f"{float(prostate_val):.1f}" if prostate_val is not None else "N/A",
            )
            skin_val = props.get("skin")
            render_kpi_card(
                "Skin Cancer Rate",
                f"{float(skin_val):.1f}" if skin_val is not None else "N/A",
            )
    else:
        st.info("Select an authority on the map to view cancer incidence data.")

    st.divider()

    tab_overall, tab_top5 = st.tabs(
        ["📊 Overall Incidence by District", "🏆 Top 5 Cancers by Area & Age Group"]
    )

    with tab_overall:
        if not overall_df.empty:
            st.write(f"**{len(overall_df)} districts** — age-standardised rates.")
            st.dataframe(overall_df, width="stretch")
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
            area_names = sorted(top5_df["District Name"].dropna().unique().tolist())
            selected_areas = filter_col2.multiselect(
                "Filter by district:",
                options=area_names,
                default=[],
                placeholder="All districts",
                key="app_area_filter",
            )
            filtered = top5_df[top5_df["Cancer Type"].isin(selected_cancers)]
            if selected_areas:
                filtered = filtered[filtered["District Name"].isin(selected_areas)]
            st.write(f"**{len(filtered)} rows**")
            st.dataframe(filtered, width="stretch")
        else:
            st.info("Top-5 cancers data is not available.")


def _panel_research() -> None:
    """Research assistant panel — delegates to the existing page renderer."""
    import importlib

    with st.popover("💡 Guide: Conversational AI Analysis", use_container_width=True):
        st.markdown(
            """
            **How to use the AI Assistant:**
            1. Ask questions in plain English in the query input (e.g., *"Which districts have high deprivation and high bowel cancer rates?"*).
            2. Click **Ask Gemini** to get data-backed insights combining population, deprivation, and cancer datasets.
            3. Pro tip: Use the automatic insights generator and scatter plots below to explore cross-dataset relationships.
            """
        )

    module = importlib.import_module("pages.5_AI_Research_Assistant")
    module.render_research_assistant_page()


# ── Session state defaults ────────────────────────────────────────────────────

st.session_state.setdefault("active_fid", None)
st.session_state.setdefault("active_topic", TOPICS[0])

# Tighten the top gap and left-align the hero title for the home page.
st.markdown(
    """
    <style>
    /* Reduce Streamlit's default top block padding on the home page */
    .block-container { padding-top: 1rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2px;
        margin-top: 0;
        line-height: 1.15;
    ">Cancer Health Dashboard — East of England</div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div style="
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: var(--color-text-muted, #64748B);
        font-weight: 400;
        margin-bottom: 17px;
        margin-top: 2px;
    ">Public Health and Cancer Risk Explorer — East of England. This geospatial analytical platform integrates population demographics, deprivation subdomains, and cancer incidence datasets. Its primary objective is to assist public health analysts and policymakers in identifying deprived communities that would benefit most from targeted campaigns to improve early cancer detection.</div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div style="
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: var(--color-text-muted, #64748B);
        font-weight: 400;
        margin-bottom: 15px;
        margin-top: 2px;
    ">How to use this page
    - Use the radio buttons below to navigate between the different topics.
    - Use the select district dropdown to filter the data to a specific district.
    - Use color map by metric dropdown to color by a selected feature
    - The map will display a spectrum: the darker the shade, the higher the count/value of the metric.
    - The selected district stands out with a thick bold boundary.
    </div>.
    """,
    unsafe_allow_html=True,
)

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

# ── Resolve map tiles ─────────────────────────────────────────────────────────

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

    st.markdown("")  # spacing
    render_map_settings(key="map_type_main", in_sidebar=False)

    # Dynamic Population Ethnic Group Chart below map settings
    if active_topic == "Population" and active_fid:
        try:
            pop_df = _load_population_overlay()
            if not pop_df.empty:
                row = pop_df[pop_df.index.astype(str) == str(active_fid)]
                if not row.empty:
                    props = id_to_props.get(str(active_fid), {})
                    name = props.get("District Name") or active_fid

                    target_cols = {
                        "White": "Total - All White Groups",
                        "Asian": "Total - All Asian Groups",
                        "Black": "Total - All Black Groups",
                        "Mixed": "Total - All Mixed Groups",
                        "Others": "Total - Other Ethnic Groups",
                    }
                    labels, values = [], []
                    for label, col in target_cols.items():
                        if col in row.columns:
                            val_str = str(row.iloc[0][col])
                            clean_val = "".join(
                                c for c in val_str if c.isdigit() or c == "."
                            )
                            try:
                                values.append(float(clean_val))
                                labels.append(label)
                            except ValueError:
                                pass

                    if values and sum(values) > 0:
                        st.markdown("---")
                        st.markdown(f"#### 👥 Ethnic Group Proportion in {name}")
                        fig = px.pie(
                            names=labels,
                            values=values,
                            hole=0.4,
                            color_discrete_sequence=FLC26_QUALITATIVE,
                        )
                        fig.update_layout(
                            margin=dict(t=20, b=20, l=10, r=10),
                            height=280,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.2,
                                xanchor="center",
                                x=0.5,
                            ),
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
