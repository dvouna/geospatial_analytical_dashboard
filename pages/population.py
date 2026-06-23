"""
Population Profiles Page — data-only view.

The interactive map with authority selection now lives in the main dashboard
(``app.py``).  This page shows the population data table for direct access
or standalone use.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from map_utils import (
    load_base_gdf,
    load_overlay_dataframe,
    merge_overlay,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def render_population_page():
    st.title("👥 Population Profiles")
    st.write("Population data for East of England local authorities.")

    st.info(
        "💡 **Interactive map** with clickable authority selection is available on the "
        "**main dashboard** — navigate there using the sidebar."
    )

    # Sidebar info
    st.sidebar.header("Data Source")
    st.sidebar.write("**East of England Local Authorities Population Data**")

    # Load base GeoDataFrame (cached)
    gdf = load_base_gdf(DATA_DIR)
    if gdf is None:
        st.error("❌ Unable to load base GeoJSON data.")
        return

    # Load population overlay
    try:
        overlay_df = load_overlay_dataframe(
            DATA_DIR / "population_detail.csv", index_col="fid"
        )
        if "fid" in overlay_df.columns:
            overlay_df["fid"] = overlay_df["fid"].astype(str)
        gdf = merge_overlay(gdf, overlay_df, base_key="fid", overlay_key="fid")
    except FileNotFoundError:
        st.error("❌ `population_detail.csv` not found in the data directory.")
        return
    except Exception as exc:
        st.error(f"❌ Error loading population data: {exc}")
        return

    # Data table
    st.subheader("Local Authorities — Population Data")
    st.write(f"**Total Local Authorities/Districts:** {len(overlay_df)}")
    st.dataframe(pd.DataFrame(overlay_df).head(50), use_container_width=True)


if __name__ == "__main__":
    render_population_page()
