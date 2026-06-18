import streamlit as st
from config import get_config, check_environment

# Page configuration: allow full-width layout
st.set_page_config(
    page_title="Future Leaders Innovation Challenge",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Check environment and load config
check_environment()
config = get_config()

# Use Streamlit's built-in multi-page navigation (Pages menu) when available.
st.markdown("## Welcome — use the Streamlit Pages menu (top-left) to navigate to individual pages.")
st.write("Available pages:")
st.markdown(
    "- East of England Local Authorities\n- Population Profiles\n- Index of Multiple Deprivation\n- East of England Cancer Incidence"
)
