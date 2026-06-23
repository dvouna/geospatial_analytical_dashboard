"""
Cancer Incidence Page — data-only view.

The interactive map with authority selection now lives in the main dashboard
(``app.py``).  This page shows cancer incidence data tables for direct access
or standalone use.

Overlays:
  - overall_incidence.csv  : one row per district (all ages / persons).
  - top_5_cancers.csv      : long format (5 cancer types x 45 districts).
"""

import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OVERALL_INCIDENCE_PATH = DATA_DIR / "overall_incidence.csv"
TOP5_CANCERS_PATH = DATA_DIR / "top_5_cancers.csv"


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

    st.info(
        "💡 **Interactive map** with clickable authority selection is available on the "
        "**main dashboard** — navigate there using the sidebar."
    )

    # Sidebar info
    st.sidebar.header("Data Source")
    st.sidebar.write("**NDRS/Fingertips Cancer Data**")

    # Load data
    try:
        overall_df = _load_overall_incidence()
    except FileNotFoundError:
        st.error(f"❌ File not found: `{OVERALL_INCIDENCE_PATH.name}`")
        overall_df = pd.DataFrame()
    except Exception as exc:
        st.error(f"❌ Could not load overall incidence data: {exc}")
        overall_df = pd.DataFrame()

    # Data tables
    st.divider()
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
