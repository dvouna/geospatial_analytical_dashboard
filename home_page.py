"""
Cancer Health Dashboard — Home Page
------------------------------------
Main dashboard landing page: provides context on the platform, datasets, and other metadata.
This file is loaded by the st.navigation router in app.py.
Global setup (CSS, dark mode) is already applied by the router.
"""

from __future__ import annotations

import streamlit as st


def render_home_page() -> None:

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
        ">Cancer Health Equity Dashboard For East of England</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            color: var(--color-text-muted, #64748B);
            font-weight: 500;
            margin-bottom: 10px;
            margin-top: 1.5rem;
        ">Welcome to the East of England Cancer Health Equity Explorer. This analytical dashboard integrates geospatial and statistical data on population, deprivation subdomains, and cancer incidence. Its primary objective is to assist public health analysts, researchers and policymakers in identifying deprived communities that would benefit from targeted interventions to improve cancer outcomes.</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("#### Platform Overview")
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


if __name__ == "__main__":
    render_home_page()
