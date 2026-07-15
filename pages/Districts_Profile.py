"""
Cancer Health Dashboard — Districts Profile
-------------------------------------------
District profile details: persistent map + topic panels + detailed data tables.
This file is loaded by the st.navigation router in app.py.
Global setup (CSS, dark mode) is already applied by the router.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from config import Config

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

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"

TOPICS = [
    "East of England",
    "Population",
    "Index of Multiple Deprivation",
    "Cancer Incidence",
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
        # Drop columns already in gdf (except the join key) to avoid duplicates
        cols_to_drop = [c for c in pop_df.columns if c in gdf.columns and c != "fid"]
        pop_df = pop_df.drop(columns=cols_to_drop, errors="ignore")
        gdf = merge_overlay(gdf, pop_df, base_key="fid", overlay_key="fid")
    except Exception as exc:
        st.warning(f"⚠️ Failed to merge population data: {exc}")

    try:
        iod_df = load_overlay_dataframe(DATA_DIR / "iod_2025.csv")
        if "District Code" in iod_df.columns:
            iod_df["District Code"] = iod_df["District Code"].astype(str).str.strip()
            # Drop columns already in gdf (except the join key) to avoid duplicates
            cols_to_drop = [
                c for c in iod_df.columns if c in gdf.columns and c != "District Code"
            ]
            iod_df = iod_df.drop(columns=cols_to_drop, errors="ignore")
            gdf = merge_overlay(
                gdf, iod_df, base_key="District Code", overlay_key="District Code"
            )
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
    st.markdown("#### District Population Profile")

    try:
        overlay_df = _load_population_overlay()
    except FileNotFoundError:
        st.error("❌ `population_detail.csv` not found in the data directory.")
        return

    if active_fid:
        props = id_to_props.get(str(active_fid), {})
        name = props.get("District Name") or active_fid
        st.success(f"**Selected District: {name}**")

        col1, stat_col2 = st.columns(2)
        with col1:
            pop_val = _get_clean_kpi_value(props, "Total Population")
            render_kpi_card("Total Population", pop_val)
            white_val = _get_clean_kpi_value(props, "All White Groups (Total)")
            render_kpi_card("White", white_val)
            asian_val = _get_clean_kpi_value(props, "All Asians (Total)")
            render_kpi_card("Asian", asian_val)
        with stat_col2:
            black_val = _get_clean_kpi_value(props, "All Balcks (Total)")
            render_kpi_card("Black", black_val)
            mixed_val = _get_clean_kpi_value(props, "All Mixed Ethnic Groups (Total)")
            render_kpi_card("Mixed Group", mixed_val)
            others_val = _get_clean_kpi_value(props, "Other Ethnic Groups (Total)")
            render_kpi_card("Others Group", others_val)

        # AI Research Assistant widget under KPI cards
        st.markdown("---")
        st.subheader("🤖 AI Research Assistant")
        import importlib

        module = importlib.import_module("pages.5_AI_Research_Assistant")
        module.render_research_assistant_widget(key_suffix="districts_population_panel")

    else:
        st.info("Select an authority on the map to view its population profile.")


def _panel_imd(active_fid: str | None, id_to_props: dict) -> None:
    """IMD panel: deprivation data for the selected authority."""
    st.markdown("#### Index of Multiple Deprivation")

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
            imd_rank = props.get("Overall IMD Rank")
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


def _panel_cancer(active_fid: str | None, id_to_props: dict) -> None:
    """Cancer incidence panel for the selected authority."""
    st.markdown("#### Cancer Incidence Profile")

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


# ── Session state defaults ────────────────────────────────────────────────────


def render_districts_profile_page() -> None:
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
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 2px;
            margin-top: 0.2rem;
            line-height: 1.15;
        ">Geospatial Visualization for East of England Districts</div>
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
            margin-top: 1.5rem;
        ">District profile details: persistent map + topic panels + detailed data tables. Analyze and inspect local authority attributes across population demographics, deprivation subdomains, and cancer incidence datasets.</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        **How to Explore this page:**
        - **Select a Topic**: Use the radio buttons below (e.g., *Population*, *Cancer Incidence*) to explore different domains.
        - **Select a District**: Click any region on the map or select one from the dropdown below to display its metrics.
        - **Visual Highlights**: A colored map will display showing overall counts. 
        - **Note**: The darker the color the higher the count. Hover over the map to see the different names of districts and their values. 
        """
    )

    active_topic_val = st.session_state.get("active_topic")
    if active_topic_val not in TOPICS:
        active_topic_val = TOPICS[0]

    active_topic = st.radio(
        "Navigate to:",
        TOPICS,
        index=TOPICS.index(active_topic_val),
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
        print(f"[home] Failed to load base map data: {exc}", file=sys.stderr)
        st.error(
            "❌ Failed to load base map data. Please contact the administrator."
            if not Config.DEBUG
            else f"❌ Failed to load base map data: {exc}"
        )
        st.stop()

    # ── Resolve map tiles ─────────────────────────────────────────────────────────

    map_type_val = st.session_state.get("map_type_main", "Satellite (ArcGIS)")
    tiles, attr = get_map_tile_config(map_type_val)

    # ── Two-column layout ─────────────────────────────────────────────────────────

    active_fid = st.session_state.get("active_fid")
    active_topic = st.session_state["active_topic"]

    st.markdown(
        """
        <style>
        /* Sidebar separator: left border + padding on the right panel column */
        div[data-testid="stHorizontalBlock"]:has(.sidebar-marker) > div[data-testid="stColumn"]:last-child {
            border-left: 2px solid var(--color-border, #E2E8F0) !important;
            padding-left: 1.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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

        # Dynamic tables rendering under the map display based on selection
        if active_fid:
            props = id_to_props.get(str(active_fid), {})
            name = props.get("District Name") or active_fid

            if active_topic == "Population":
                try:
                    total_pop_val = props.get("Total Population") or props.get(
                        "total_population"
                    )
                    try:
                        total_pop = float(str(total_pop_val).replace(",", "").strip())
                    except (ValueError, TypeError):
                        total_pop = None

                    subgroup_definitions = [
                        # White Group
                        (
                            "White British",
                            "White Group",
                            "White: English, Welsh, Scottish, Northern Irish or British (number)",
                        ),
                        ("White Irish", "White Group", "White: Irish (number)"),
                        (
                            "Gypsy or Irish Traveller",
                            "White Group",
                            "White: Gypsy or Irish Traveller (number)",
                        ),
                        ("White Roma", "White Group", "White: Roma (number)"),
                        ("Other White", "White Group", "White: Other White (number)"),
                        # Asian Group
                        (
                            "Indian",
                            "Asian Group",
                            "Asian, Asian British or Asian Welsh: Indian (number)",
                        ),
                        (
                            "Pakistani",
                            "Asian Group",
                            "Asian, Asian British or Asian Welsh: Pakistani (number)",
                        ),
                        (
                            "Bangladeshi",
                            "Asian Group",
                            "Asian, Asian British or Asian Welsh: Bangladeshi (number)",
                        ),
                        (
                            "Chinese",
                            "Asian Group",
                            "Asian, Asian British or Asian Welsh: Chinese (number)",
                        ),
                        (
                            "Other Asian",
                            "Asian Group",
                            "Asian, Asian British or Asian Welsh: Other Asian (number)",
                        ),
                        # Black Group
                        (
                            "African",
                            "Black Group",
                            "Black, Black British, Black Welsh, Caribbean or African: African (number)",
                        ),
                        (
                            "Caribbean",
                            "Black Group",
                            "Black, Black British, Black Welsh, Caribbean or African: Caribbean (number)",
                        ),
                        (
                            "Other Black",
                            "Black Group",
                            "Black, Black British, Black Welsh, Caribbean or African: Other Black (number)",
                        ),
                        # Mixed Group
                        (
                            "White & Asian",
                            "Mixed Group",
                            "Mixed or Multiple ethnic groups: White and Asian (number)",
                        ),
                        (
                            "White & Black African",
                            "Mixed Group",
                            "Mixed or Multiple ethnic groups: White and Black African (number)",
                        ),
                        (
                            "White & Black Caribbean",
                            "Mixed Group",
                            "Mixed or Multiple ethnic groups: White and Black Caribbean (number)",
                        ),
                        (
                            "Other Mixed",
                            "Mixed Group",
                            "Mixed or Multiple ethnic groups: Other Mixed or Multiple ethnic groups (number)",
                        ),
                        # Others Group
                        ("Arab", "Others Group", "Other ethnic group: Arab (number)"),
                        (
                            "Any other ethnic group",
                            "Others Group",
                            "Other ethnic group: Any other ethnic group (number)",
                        ),
                    ]

                    table_rows = []
                    for display_name, parent_group, key in subgroup_definitions:
                        val = props.get(key)
                        try:
                            clean_val = int(float(str(val).replace(",", "").strip()))
                        except (ValueError, TypeError):
                            clean_val = 0
                        pct = (clean_val / total_pop) * 100 if total_pop else 0.0
                        table_rows.append(
                            {
                                "Subgroup": display_name,
                                "Broad Group": parent_group,
                                "Count": clean_val,
                                "Percentage": pct,
                            }
                        )

                    df_subgroups = pd.DataFrame(table_rows)
                    st.markdown("---")
                    st.markdown(f"#### 👥 Detailed Ethnic Composition for {name}")
                    st.dataframe(
                        df_subgroups.style.format(
                            {"Count": "{:,}", "Percentage": "{:.2f}%"}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.subheader("📋 Subgroup Breakdown")

                    subgroups = {
                        "White Group": [
                            (
                                "White British",
                                "White: English, Welsh, Scottish, Northern Irish or British (number)",
                            ),
                            ("White Irish", "White: Irish (number)"),
                            (
                                "Gypsy or Irish Traveller",
                                "White: Gypsy or Irish Traveller (number)",
                            ),
                            ("White Roma", "White: Roma (number)"),
                            ("Other White", "White: Other White (number)"),
                        ],
                        "Asian Group": [
                            (
                                "Indian",
                                "Asian, Asian British or Asian Welsh: Indian (number)",
                            ),
                            (
                                "Pakistani",
                                "Asian, Asian British or Asian Welsh: Pakistani (number)",
                            ),
                            (
                                "Bangladeshi",
                                "Asian, Asian British or Asian Welsh: Bangladeshi (number)",
                            ),
                            (
                                "Chinese",
                                "Asian, Asian British or Asian Welsh: Chinese (number)",
                            ),
                            (
                                "Other Asian",
                                "Asian, Asian British or Asian Welsh: Other Asian (number)",
                            ),
                        ],
                        "Black Group": [
                            (
                                "African",
                                "Black, Black British, Black Welsh, Caribbean or African: African (number)",
                            ),
                            (
                                "Caribbean",
                                "Black, Black British, Black Welsh, Caribbean or African: Caribbean (number)",
                            ),
                            (
                                "Other Black",
                                "Black, Black British, Black Welsh, Caribbean or African: Other Black (number)",
                            ),
                        ],
                        "Mixed Group": [
                            (
                                "White and Asian",
                                "Mixed or Multiple ethnic groups: White and Asian (number)",
                            ),
                            (
                                "White and Black African",
                                "Mixed or Multiple ethnic groups: White and Black African (number)",
                            ),
                            (
                                "White and Black Caribbean",
                                "Mixed or Multiple ethnic groups: White and Black Caribbean (number)",
                            ),
                            (
                                "Other Mixed",
                                "Mixed or Multiple ethnic groups: Other Mixed or Multiple ethnic groups (number)",
                            ),
                        ],
                        "Others Group": [
                            ("Arab", "Other ethnic group: Arab (number)"),
                            (
                                "Any other ethnic group",
                                "Other ethnic group: Any other ethnic group (number)",
                            ),
                        ],
                    }

                    for group_name, sub_list in subgroups.items():
                        with st.expander(f"🔍 {group_name} Subgroup Details"):
                            for label, col_key in sub_list:
                                formatted_val = _get_clean_kpi_value(props, col_key)
                                st.write(f"• **{label}**: {formatted_val}")

                    try:
                        pop_df = _load_population_overlay()
                        st.markdown("---")
                        st.subheader("📋 All Authorities — Population Data")
                        st.write(f"**{len(pop_df)} districts**")
                        st.dataframe(pop_df.head(50), use_container_width=True)
                    except Exception as exc:
                        st.warning(
                            f"⚠️ Failed to load all authorities population table: {exc}"
                        )
                except Exception as exc:
                    print(
                        f"[districts_profile] Could not render population table: {exc}",
                        file=sys.stderr,
                    )

            elif active_topic == "Index of Multiple Deprivation":
                try:
                    import math

                    subdomain_definitions = [
                        ("Overall IMD", "Overall IMD Rank"),
                        ("Income", "Income Rank"),
                        ("Employment", "Employment Rank"),
                        ("Education & Skills", "Education Skills and Training Rank"),
                        (
                            "Health & Disability",
                            "Health Deprivation and Disability Rank",
                        ),
                        ("Crime", "Crime Rank"),
                        ("Housing & Services", "Barriers to Housing and Services Rank"),
                        ("Living Environment", "Living Environment Rank"),
                        (
                            "IDACI (Children)",
                            "Income Deprivation Affecting Children Index (IDACI) Rank",
                        ),
                        (
                            "IDAOPI (Older)",
                            "Income Deprivation Affecting Older People (IDAOPI) Rank",
                        ),
                    ]

                    table_rows = []
                    for label, key in subdomain_definitions:
                        val = props.get(key)
                        try:
                            rank_val = int(float(str(val).replace(",", "").strip()))
                            decile_val = math.ceil(rank_val / 29.6)
                            decile_str = f"Decile {decile_val}"
                        except (ValueError, TypeError):
                            rank_val = "N/A"
                            decile_str = "N/A"
                        table_rows.append(
                            {
                                "IMD Subdomain": label,
                                "Rank": rank_val,
                                "Decile": decile_str,
                            }
                        )

                    df_imd = pd.DataFrame(table_rows)
                    st.markdown("---")
                    st.markdown(f"#### 📊 IMD Rankings & Deciles for {name}")
                    st.dataframe(df_imd, use_container_width=True, hide_index=True)

                    try:
                        imd_df = _load_iod_overlay()
                        if not imd_df.empty:
                            st.markdown("---")
                            st.subheader(
                                "📋 All Authorities — Deprivation Data (IoD 2025)"
                            )
                            st.write(f"**{len(imd_df)} districts**")
                            st.dataframe(imd_df.head(50), use_container_width=True)
                    except Exception as exc:
                        st.warning(
                            f"⚠️ Failed to load all authorities deprivation table: {exc}"
                        )
                except Exception as exc:
                    print(
                        f"[districts_profile] Could not render IMD table: {exc}",
                        file=sys.stderr,
                    )

            elif active_topic == "Cancer Incidence":
                try:
                    cancer_definitions = [
                        ("Overall Cancer Rate", "Rate", "per 100k"),
                        ("Total Diagnosed Cases", "Total_incidence", "cases"),
                        ("Bladder Cancer Rate", "bladder", "per 100k"),
                        ("Blood Cancer Rate", "blood cancer", "per 100k"),
                        ("Bowel Cancer Rate", "bowel", "per 100k"),
                        ("Brain Cancer Rate", "brain", "per 100k"),
                        ("Breast Cancer Rate", "breast", "per 100k"),
                        ("Head & Neck Cancer Rate", "head and neck", "per 100k"),
                        ("Kidney Cancer Rate", "kidney", "per 100k"),
                        (
                            "Liver & Biliary Cancer Rate",
                            "liver and biliary tract",
                            "per 100k",
                        ),
                        ("Lung Cancer Rate", "lung", "per 100k"),
                        ("Ovarian Cancer Rate", "ovary", "per 100k"),
                        ("Pancreatic Cancer Rate", "pancreas", "per 100k"),
                        ("Prostate Cancer Rate", "prostate", "per 100k"),
                        ("Skin Cancer Rate", "skin", "per 100k"),
                        ("Uterine Cancer Rate", "uterus", "per 100k"),
                    ]

                    table_rows = []
                    for label, key, unit in cancer_definitions:
                        val = props.get(key)
                        try:
                            float_val = float(str(val).replace(",", "").strip())
                            if key == "Total_incidence":
                                value_str = f"{int(float_val):,}"
                            else:
                                value_str = f"{float_val:.1f}"
                        except (ValueError, TypeError):
                            value_str = "N/A"
                        table_rows.append(
                            {"Cancer Type": label, "Value": value_str, "Unit": unit}
                        )

                    df_cancer = pd.DataFrame(table_rows)
                    st.markdown("---")
                    st.markdown(f"#### 🎗️ Cancer Incidence Profile for {name}")
                    st.dataframe(df_cancer, use_container_width=True, hide_index=True)

                    try:
                        overall_df = _load_cancer_overlay()
                        top5_df = _load_top5_overlay()

                        st.markdown("---")
                        tab_overall, tab_top5 = st.tabs(
                            [
                                "📊 Overall Incidence by District",
                                "🏆 Top 5 Cancers by Area & Age Group",
                            ]
                        )

                        with tab_overall:
                            if not overall_df.empty:
                                st.write(
                                    f"**{len(overall_df)} districts** — age-standardised rates."
                                )
                                st.dataframe(overall_df, use_container_width=True)
                            else:
                                st.info("Overall incidence data is not available.")

                        with tab_top5:
                            if not top5_df.empty:
                                filter_col1, filter_col2 = st.columns(2)
                                cancer_types = sorted(
                                    top5_df["Cancer Type"].unique().tolist()
                                )
                                selected_cancers = filter_col1.multiselect(
                                    "Filter by cancer type:",
                                    options=cancer_types,
                                    default=cancer_types,
                                    key="districts_cancer_type_filter",
                                )
                                area_names = sorted(
                                    top5_df["District Name"].dropna().unique().tolist()
                                )
                                selected_areas = filter_col2.multiselect(
                                    "Filter by district:",
                                    options=area_names,
                                    default=[],
                                    placeholder="All districts",
                                    key="districts_area_filter",
                                )
                                filtered = top5_df[
                                    top5_df["Cancer Type"].isin(selected_cancers)
                                ]
                                if selected_areas:
                                    filtered = filtered[
                                        filtered["District Name"].isin(selected_areas)
                                    ]
                                st.write(f"**{len(filtered)} rows**")
                                st.dataframe(filtered, use_container_width=True)
                            else:
                                st.info("Top-5 cancers data is not available.")
                    except Exception as exc:
                        st.warning(f"⚠️ Failed to load cancer comparison tables: {exc}")
                except Exception as exc:
                    print(
                        f"[districts_profile] Could not render cancer table: {exc}",
                        file=sys.stderr,
                    )

    # ── Right panel: dispatch to the active topic ─────────────────────────────────

    with col_panel:
        st.markdown("<div class='sidebar-marker'></div>", unsafe_allow_html=True)
        if active_topic == "East of England":
            _panel_overview(active_fid, id_to_props)
        elif active_topic == "Population":
            _panel_population(active_fid, id_to_props)
        elif active_topic == "Index of Multiple Deprivation":
            _panel_imd(active_fid, id_to_props)
        elif active_topic == "Cancer Incidence":
            _panel_cancer(active_fid, id_to_props)


if __name__ == "__main__":
    render_districts_profile_page()
