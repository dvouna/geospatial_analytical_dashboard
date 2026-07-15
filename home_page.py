"""
Cancer Health Dashboard — Home Page
------------------------------------
Main dashboard landing page: provides context on the platform, datasets, and other metadata.
This file is loaded by the st.navigation router in app.py.
Global setup (CSS, dark mode) is already applied by the router.
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st

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
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2px;
        margin-top: 2.5rem;
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
        margin-top: 1.5rem;
    ">Public Health and Cancer Risk Explorer — East of England. This geospatial analytical platform integrates population demographics, deprivation subdomains, and cancer incidence datasets. Its primary objective is to assist public health analysts and policymakers in identifying deprived communities that would benefit most from targeted campaigns to improve early cancer detection.</div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

st.markdown("### ℹ️ Platform Overview")
st.markdown(
    """
    Welcome to the Cancer Health Dashboard for the East of England. This platform provides key insights and analytics on:
    - **Districts Profile**: Detailed map-based exploration of local authorities, population demographics, deprivation subdomains, and cancer rates.
    - **Population Demographics**: Playgrounds comparing ethnic subgroup distributions across districts.
    - **Deprivation Analysis**: Exploration of Indices of Multiple Deprivation (IMD) 2025 subdomains and regional distributions.
    - **Cancer Trends**: Statistics and age-standardised rates of various cancer types across the region.
    - **AI Research Assistant**: A conversational assistant powered by Google Gemini to analyze and query the integrated datasets.
    
    Please expand the left navigation menu to explore these analytical tools.
    """
)
