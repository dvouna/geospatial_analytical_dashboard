"""
Index of Multiple Deprivation Page — data-only view.

The interactive map with authority selection now lives in the main dashboard
(``app.py``).  This page shows the deprivation data table for direct access
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


def render_imd_page():
    st.title("📊 Index of Multiple Deprivation")
    st.write("Explore deprivation data across East Anglia.")

    st.info(
        "💡 **Interactive map** with clickable authority selection is available on the "
        "**main dashboard** — navigate there using the sidebar."
    )

    # Sidebar info
    st.sidebar.header("Data Source")
    st.sidebar.write("**Index of Multiple Deprivation (2025)**")

    # Load base GeoDataFrame (cached)
    gdf = load_base_gdf(DATA_DIR)
    if gdf is None:
        st.error("❌ Unable to load base boundaries GeoJSON data.")
        return

    # Merge overlay if available
    overlay_candidates = [DATA_DIR / "local_districts.csv"]
    overlay_df = None
    for p in overlay_candidates:
        if p.exists():
            try:
                overlay_df = load_overlay_dataframe(p, index_col="fid")
                if "fid" in gdf.columns and "fid" in overlay_df.columns:
                    gdf = merge_overlay(gdf, overlay_df, base_key="fid", overlay_key="fid")
                break
            except Exception as e:
                st.warning(f"⚠️ Failed to merge overlay from {p.name}: {str(e)}")

    # Data table
    st.subheader("Local Authorities — Deprivation Data")
    if overlay_df is not None:
        st.write(f"**Total Local Authorities/Districts:** {len(overlay_df)}")
        st.dataframe(pd.DataFrame(overlay_df).head(50), use_container_width=True)
    else:
        st.info("ℹ️ No overlay data available — local_districts.csv could not be loaded.")


if __name__ == "__main__":
    render_imd_page()
