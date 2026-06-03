"""
Streamlit Data Visualization & Gemini Query Application
Main entry point for the multi-page Streamlit app
"""

import streamlit as st
from config import get_config, check_environment
from pages_dashboard import render_index_of_multiple_deprivation_page
from pages_cancer_statistics import render_cancer_statistics_page
from pages_ethnic_composition import render_ethnic_composition_page
from pages_query import render_research_assistant_page
from pages_maps import render_maps_page
from population import render_population_page
from imd import render_imd_page
from cancer_incidence import render_cancer_incidence_page

# Page configuration
st.set_page_config(
    page_title="Future Leaders Innovation Challenge",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check environment on startup
check_environment()

# Get config
config = get_config()

# Navigation
page = st.sidebar.radio(
    "Select page:",
    [
        "East of England Cancer Incidence",
        "Population Profiles",
        "Index of Multiple Deprivation",
        "Cancer Statistics",
        "Research Assistant"
    ]
)

if page == "East of England Local Authorities":
    render_maps_page()
    st.stop()
elif page == "Population Profiles":
    render_population_page()
    st.stop()
elif page == "Index of Multiple Deprivation":
    render_imd_page()
    st.stop()
elif page == "Ethnic Composition":
    render_ethnic_composition_page()
    st.stop()
elif page == "Cancer Statistics":
    render_cancer_statistics_page()
    st.stop()
elif page == "Research Assistant":
    render_research_assistant_page()
    st.stop()

st.error("Invalid page selection. Please choose one of the options from the sidebar.")
