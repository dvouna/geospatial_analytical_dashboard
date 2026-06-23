"""
Cancer Incidence Map Page

Overlays:
  - overall_incidence.csv  : one row per district (all ages / persons),
                             includes per-cancer columns. Merged 1:1 onto the
                             base GeoDataFrame for choropleth and side-panel stats.
  - top_5_cancers.csv      : long format (5 cancer types × 45 districts).
                             Displayed in a filterable data table below the map.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from map_utils import (
    load_geojson,
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
BASE_GEOJSON_PATH = DATA_DIR / "base_gdf_1.geojson"
OVERALL_INCIDENCE_PATH = DATA_DIR / "overall_incidence.csv"
TOP5_CANCERS_PATH = DATA_DIR / "top_5_cancers.csv"

# Columns from overall_incidence to show in the side-panel info box
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


@st.cache_data
def _load_overall_incidence() -> pd.DataFrame:
    """Load and return overall_incidence.csv, normalising the fid column."""
    df = pd.read_csv(OVERALL_INCIDENCE_PATH)
    if "fid" in df.columns:
        df["fid"] = df["fid"].astype(str).str.strip()
    return df


@st.cache_data
def _load_top5() -> pd.DataFrame:
    """Load and return top_5_cancers.csv, normalising the fid column."""
    df = pd.read_csv(TOP5_CANCERS_PATH)
    if "fid" in df.columns:
        df["fid"] = df["fid"].astype(str).str.strip()
    return df


def render_cancer_incidence_page():
    st.title("🎗️ Cancer Incidence Data Profiles")
    st.write("Explore cancer incidence data across East of England local authorities.")

    st.sidebar.header("Data Source")
    st.sidebar.write("**NDRS/Fingertips Cancer Data**")

    # ── Load base GeoJSON ────────────────────────────────────────────────────
    try:
        gdf = load_geojson(BASE_GEOJSON_PATH)
    except FileNotFoundError:
        st.error(f"❌ GeoJSON file not found at: `{BASE_GEOJSON_PATH}`")
        return
    except Exception as exc:
        st.error(f"❌ Error loading GeoJSON: {exc}")
        return

    tiles, attr = render_map_settings(key="map_type_cancer", show_help_text=True)

    # ── Merge overall_incidence overlay (1:1 join) ───────────────────────────
    try:
        overall_df = _load_overall_incidence()
        if "fid" not in gdf.columns:
            st.error("❌ Base GeoJSON is missing required join key: 'fid'")
            return
        gdf = merge_overlay(gdf, overall_df, base_key="fid", overlay_key="fid")
    except FileNotFoundError:
        st.error(f"❌ Overlay file not found: `{OVERALL_INCIDENCE_PATH.name}`")
        return
    except Exception as exc:
        st.warning(f"⚠️ Could not merge overall incidence data: {exc}")
        overall_df = pd.DataFrame()

    # ── Build GeoJSON payload and lookup dicts ───────────────────────────────
    center = compute_center(gdf)
    geojson_payload, id_field = prepare_geojson_payload(gdf)
    options, option_to_id, id_to_display, id_to_props = build_authority_options(
        geojson_payload
    )

    # ── Session state ────────────────────────────────────────────────────────
    if "cancer_select_display" not in st.session_state:
        st.session_state["cancer_select_display"] = options[0] if options else None
    if "cancer_select_version" not in st.session_state:
        st.session_state["cancer_select_version"] = 0

    current_display = st.session_state.get("cancer_select_display")
    if current_display not in option_to_id and options:
        current_display = options[0]
        st.session_state["cancer_select_display"] = current_display

    # ── Layout ───────────────────────────────────────────────────────────────
    col_center, col_info = st.columns([9, 3], gap="medium")

    with col_center:
        selected_index = (
            options.index(current_display) if current_display in options else 0
        )
        selected_display = (
            st.selectbox(
                "Select area/county of interest:",
                options=options,
                index=selected_index,
                key=f"cancer_select_display_{st.session_state['cancer_select_version']}",
            )
            if options
            else None
        )

        if selected_display:
            st.session_state["cancer_select_display"] = selected_display

        active_fid = option_to_id.get(selected_display) if selected_display else None

        m = create_folium_map(center=center, tiles=tiles, attr=attr)
        tooltip_fields = [
            field
            for field in ["fid", "LAD24NM", "Total_incidence", "Rate"]
            if field in gdf.columns
        ]
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

    # ── Click synchronisation ────────────────────────────────────────────────
    clicked_fid = extract_clicked_fid(map_output, option_to_id, id_to_props)
    if clicked_fid and clicked_fid != active_fid and clicked_fid in id_to_display:
        st.session_state["cancer_select_display"] = id_to_display[clicked_fid]
        st.session_state["cancer_select_version"] += 1
        trigger_rerun()

    active_fid = (
        clicked_fid if clicked_fid and clicked_fid in id_to_props else active_fid
    )

    # ── Side panel ───────────────────────────────────────────────────────────
    with col_info:
        st.markdown("### 📍 Authority Summary")
        if active_fid:
            props = id_to_props.get(str(active_fid), {})
            name = (
                props.get("LAD24NM")
                or props.get("Geography name ")
                or props.get(id_field, active_fid)
            )
            st.success(f"**{name}**")

            # Show incidence metrics from the merged overlay
            display_cols = {
                col: props[col]
                for col in SIDE_PANEL_COLS
                if col in props and props[col] not in (None, "")
            }
            if display_cols:
                display_props_as_kv(display_cols)
            else:
                display_props_as_kv(props)
        else:
            st.info(
                "Pick an authority from the selector or click a region on the map "
                "to display cancer incidence data."
            )

    st.divider()

    # ── Data tables ──────────────────────────────────────────────────────────
    tab_overall, tab_top5 = st.tabs(
        ["📊 Overall Incidence by District", "🏆 Top 5 Cancers by Area & Age Group"]
    )

    with tab_overall:
        if not overall_df.empty:
            st.write(
                f"**{len(overall_df)} districts** — all ages, all persons, "
                "age-gender-standardised rates."
            )
            st.dataframe(overall_df, use_container_width=True)
        else:
            st.info("Overall incidence data is not available.")

    with tab_top5:
        try:
            top5_df = _load_top5()
        except FileNotFoundError:
            st.error(f"❌ File not found: `{TOP5_CANCERS_PATH.name}`")
            top5_df = pd.DataFrame()
        except Exception as exc:
            st.error(f"❌ Could not load top-5 cancers data: {exc}")
            top5_df = pd.DataFrame()

        if not top5_df.empty:
            # Filter controls
            filter_col1, filter_col2 = st.columns(2)
            cancer_types = sorted(top5_df["Cancer Type"].unique().tolist())
            selected_cancers = filter_col1.multiselect(
                "Filter by cancer type:",
                options=cancer_types,
                default=cancer_types,
                key="ci_cancer_type_filter",
            )

            area_names = sorted(top5_df["Geography name "].dropna().unique().tolist())
            selected_areas = filter_col2.multiselect(
                "Filter by district:",
                options=area_names,
                default=[],
                placeholder="All districts",
                key="ci_area_filter",
            )

            filtered = top5_df[top5_df["Cancer Type"].isin(selected_cancers)]
            if selected_areas:
                filtered = filtered[filtered["Geography name "].isin(selected_areas)]

            st.write(
                f"**{len(filtered)} rows** ({len(filtered['fid'].unique())} districts, "
                f"{len(filtered['Cancer Type'].unique())} cancer types)"
            )
            st.dataframe(filtered, use_container_width=True)
        else:
            st.info("Top-5 cancers data is not available.")


if __name__ == "__main__":
    render_cancer_incidence_page()
