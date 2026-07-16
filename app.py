"""
Cancer Health Dashboard - East of England
-------------------------------------------
Single entrypoint / router.

Responsibilities:
  1. st.set_page_config  (must be first Streamlit call)
  2. Environment validation
  3. Dynamic light/dark theme CSS variables injection (defaulting to Light Mode)
  4. Custom horizontal navigation layout under the title, with bottom border accents
  5. SPA state-based routing between dashboard page modules
"""

from __future__ import annotations

import importlib
import streamlit as st

from config import check_environment, get_config

# -- Page config (must be the very first Streamlit call) ----------------------

st.set_page_config(
    page_title="Cancer Health Dashboard - East of England",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -- Environment & config -----------------------------------------------------

check_environment()
get_config()

# -- Theme & Navigation State -------------------------------------------------

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

# -- Theme Color Palettes (CSS variables) -------------------------------------

if st.session_state["theme"] == "dark":
    theme_vars = """
    :root {
        --color-bg:             #0F1117;
        --color-surface:        #1E2130;
        --color-surface-alt:    #262C40;
        --color-border:         #2D3348;
        --color-border-hover:   #3F4865;
        --color-primary:        #4FA8E0;
        --color-primary-light:  #1E3A5F;
        --color-primary-dark:   #6BBCF0;
        --color-accent:         #9B7EE8;
        --color-accent-light:   #2D1F5E;
        --color-text-heading:   #F1F5F9;
        --color-text-body:      #CBD5E1;
        --color-text-muted:     #94A3B8;
        --color-text-subtle:    #64748B;
        --color-success-bg:     #052E16;
        --color-warning-bg:     #451A03;
        --color-danger-bg:      #450A0A;
        --radius-sm:  8px;
        --radius-md:  12px;
        --radius-lg:  16px;
        --shadow-sm:  0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08);
        --shadow-md:  0 4px 12px rgba(0,0,0,0.16);
        --shadow-lg:  0 8px 24px rgba(0,0,0,0.20);
    }
    """
else:
    theme_vars = """
    :root {
        --color-bg:             #FFFFFF;
        --color-surface:        #FFFFFF;
        --color-surface-alt:    #F1F5F9;
        --color-border:         #E2E8F0;
        --color-border-hover:   #CBD5E1;
        --color-primary:        #1F77B4;
        --color-primary-light:  #DBEAFE;
        --color-primary-dark:   #1558A0;
        --color-accent:         #6941C6;
        --color-accent-light:   #EDE9FE;
        --color-text-heading:   #0F172A;
        --color-text-body:      #334155;
        --color-text-muted:     #64748B;
        --color-text-subtle:    #94A3B8;
        --color-success:        #15803D;
        --color-success-bg:     #DCFCE7;
        --color-warning:        #D97706;
        --color-warning-bg:     #FEF3C7;
        --color-danger:         #DC2626;
        --color-danger-bg:      #FEE2E2;
        --radius-sm:  8px;
        --radius-md:  12px;
        --radius-lg:  16px;
        --shadow-sm:  0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md:  0 4px 12px rgba(0,0,0,0.08);
        --shadow-lg:  0 8px 24px rgba(0,0,0,0.10);
    }
    """

# -- Global CSS Override (enforcing 'Inter' font and custom horizontal menu styling) --

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

{theme_vars}

html, body, [data-testid="stAppViewContainer"], .stButton button, p, span, div, label, h1, h2, h3, h4, select, textarea, input {{
    font-family: 'Inter', sans-serif !important;
}}

html, body, [data-testid="stAppViewContainer"] {{
    background-color: var(--color-bg) !important;
    color: var(--color-text-body);
}}

.block-container {{
    padding-top: 3.5rem !important;
    padding-left: 14rem !important;
    padding-right: 14rem !important;
    padding-bottom: 4rem !important;
    max-width: 100% !important;
}}

/* Hide Streamlit default sidebar completely */
[data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"] {{
    display: none !important;
}}

h1, h2, h3, h4 {{
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--color-text-heading);
}}

code, pre, .monospace {{ font-family: 'JetBrains Mono', monospace; }}
*:focus-visible {{ outline: 2px solid var(--color-primary); outline-offset: 2px; }}

.gradient-title {{
    background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: left;
    font-size: 2.0rem;
    font-weight: 800;
    margin-bottom: 4px;
    letter-spacing: -0.03em;
}}
.sub-title {{
    text-align: left;
    font-size: 1.05rem;
    color: var(--color-text-muted);
    margin-bottom: 28px;
    font-weight: 400;
}}

[data-testid="column"] {{
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 24px !important;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.2s ease;
}}
[data-testid="column"]:hover {{ box-shadow: var(--shadow-md); }}

.kpi-card {{
    background-color: var(--color-surface-alt);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: var(--shadow-sm);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}
.kpi-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--color-border-hover); }}
.kpi-label {{
    font-size: 0.78rem;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    margin-bottom: 6px;
}}
.kpi-value {{
    font-size: 1.6rem;
    color: var(--color-text-heading);
    font-weight: 600;
    line-height: 1.2;
    letter-spacing: -0.02em;
}}
.kpi-badge {{
    display: inline-block;
    padding: 3px 10px;
    font-size: 0.72rem;
    border-radius: 20px;
    font-weight: 600;
    margin-top: 8px;
    letter-spacing: 0.02em;
}}
.badge-danger  {{ background-color: var(--color-danger-bg);  color: var(--color-danger);  }}
.badge-warning {{ background-color: var(--color-warning-bg); color: var(--color-warning); }}
.badge-success {{ background-color: var(--color-success-bg); color: var(--color-success); }}

div[data-testid="stTabs"] > div:first-child button {{
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--color-text-muted);
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    transition: color 0.2s ease, background-color 0.2s ease;
}}
div[data-testid="stTabs"] > div:first-child button[aria-selected="true"] {{ color: var(--color-primary); border-bottom-color: var(--color-primary) !important; }}
div[data-testid="stTabs"] > div:first-child button:hover {{ color: var(--color-primary); background-color: var(--color-primary-light); }}

div.row-widget.stRadio > div[role="radiogroup"] {{
    background-color: var(--color-surface-alt);
    padding: 5px;
    border-radius: 30px;
    border: 1px solid var(--color-border);
    display: flex;
    justify-content: center;
    gap: 4px;
    width: fit-content;
    margin: 0 auto 20px auto;
}}
div.row-widget.stRadio > div[role="radiogroup"] > label {{
    background: transparent;
    padding: 7px 18px;
    border-radius: 24px;
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--color-text-muted);
    border: none;
    transition: all 0.2s ease;
    cursor: pointer;
}}
div.row-widget.stRadio > div[role="radiogroup"] > label:hover {{ color: var(--color-primary); background-color: var(--color-primary-light); }}
div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {{ background-color: var(--color-primary); color: #FFFFFF !important; box-shadow: 0 3px 8px rgba(31,119,180,0.25); }}

[data-testid="stMetric"] {{ background-color: var(--color-surface-alt); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 14px 18px; }}
[data-testid="stMetricLabel"] p {{ font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--color-text-muted) !important; }}
[data-testid="stMetricValue"] {{ font-weight: 700; letter-spacing: -0.01em; color: var(--color-text-heading) !important; }}

[data-testid="stAlert"] {{ border-radius: var(--radius-md); border-left-width: 4px; }}

::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: var(--color-surface-alt); }}
::-webkit-scrollbar-thumb {{ background: var(--color-border-hover); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--color-text-subtle); }}

/* ── Custom Navigation Button Styling (Horizontal Menu) ── */
.nav-btn-home, .nav-btn-districts, .nav-btn-population, .nav-btn-deprivation, .nav-btn-cancer, .nav-btn-insights, .nav-btn-assistant {{
    display: none !important;
}}

/* Base style for all buttons in the navigation row */
div[data-testid="column"] button,
div.stColumn button {{
    text-align: center !important;
    justify-content: center !important;
    border: none !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    padding: 6px 8px !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
    white-space: nowrap !important;
}}

/* Active Tab Style */
div[data-testid="column"]:has(.active-nav-btn) button,
div.stColumn:has(.active-nav-btn) button {{
    background: var(--color-primary-light) !important;
    color: var(--color-primary) !important;
    border-bottom: 3px solid var(--color-primary) !important;
    box-shadow: none !important;
}}

/* Inactive Tab Style */
div[data-testid="column"]:has(.inactive-nav-btn) button,
div.stColumn:has(.inactive-nav-btn) button {{
    background-color: var(--color-surface-alt) !important;
    color: var(--color-text-muted) !important;
    border-bottom: 3px solid transparent !important;
}}

/* Hover effect on Inactive Tabs */
div[data-testid="column"]:has(.inactive-nav-btn) button:hover,
div.stColumn:has(.inactive-nav-btn) button:hover {{
    background-color: var(--color-border) !important;
    color: var(--color-text-heading) !important;
}}

/* ── Responsive Styling (Screen width < 768px) ── */
@media (max-width: 768px) {{
    .divider-col {{
        display: none !important;
    }}
    div[data-testid="column"] {{
        width: 100% !important;
        max-width: 100% !important;
    }}
}}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# -- SPA Navigation Configurations --------------------------------------------

PAGES_CONFIG = {
    "Home": {"module": "home_page", "render": "render_home_page", "badge": None},
    "Districts Profile": {
        "module": "pages.Districts_Profile",
        "render": "render_districts_profile_page",
        "badge": None,
    },
    "Population Demographics": {
        "module": "pages.1_Population_Demographics",
        "render": "render_population_playground",
        "badge": None,
    },
    "Deprivation Analysis": {
        "module": "pages.2_Deprivation_Analysis",
        "render": "render_deprivation_playground",
        "badge": None,
    },
    "Cancer Trends": {
        "module": "pages.3_Cancer_Trends",
        "render": "render_cancer_trends",
        "badge": None,
    },
    "General Insights": {
        "module": "pages.4_General_Insights",
        "render": "render_general_insights_page",
        "badge": None,
    },
    "Research Assistant": {
        "module": "pages.5_AI_Research_Assistant",
        "render": "render_research_assistant_page",
        "badge": None,
    },
}

key_map = {
    "Home": "home",
    "Districts Profile": "districts",
    "Population Demographics": "population",
    "Deprivation Analysis": "deprivation",
    "Cancer Trends": "cancer",
    "General Insights": "insights",
    "Research Assistant": "assistant",
}

# -- Page Layout Rendering ----------------------------------------------------

# Header section
st.markdown(
    "<div class='gradient-title'>Cancer Health Dashboard</div>", unsafe_allow_html=True
)
st.markdown(
    "<div class='sub-title'>Public Health and Cancer Risk Explorer — East of England</div>",
    unsafe_allow_html=True,
)

# Navigation row structure
cols = st.columns([6, 17, 23, 20, 13, 16, 18])

pages_keys = list(PAGES_CONFIG.keys())
for i, page_name in enumerate(pages_keys):
    info = PAGES_CONFIG[page_name]
    is_active = st.session_state["current_page"] == page_name
    sibling_class = "active-nav-btn" if is_active else "inactive-nav-btn"
    btn_key = key_map[page_name]

    with cols[i]:
        st.markdown(
            f"<div class='nav-btn-{btn_key} {sibling_class}'></div>",
            unsafe_allow_html=True,
        )

        # Build text label with status badges
        label = page_name
        if info["badge"] == "New":
            label += " :orange[[New]]"
        elif info["badge"] == "AI":
            label += " :violet[[AI]]"

        if st.button(
            label, key=f"btn_{btn_key}", use_container_width=True, type="secondary"
        ):
            st.session_state["current_page"] = page_name
            st.rerun()

# Active page content rendering
page_info = PAGES_CONFIG[st.session_state["current_page"]]
try:
    mod = importlib.import_module(page_info["module"])
    render_func = getattr(mod, page_info["render"])
    render_func()
except Exception as e:
    st.error(f"❌ Error loading page '{st.session_state['current_page']}': {e}")
    if st.checkbox("Show error traceback"):
        st.exception(e)

# Bottom layout: horizontal divider & theme switcher
st.markdown(
    """
    <hr style="
        border: 0;
        border-top: 1.5px solid var(--color-border);
        margin: 40px 0 20px 0;
        opacity: 0.8;
    ">
    """,
    unsafe_allow_html=True,
)

col_foot_left, col_foot_right = st.columns([10, 2])
with col_foot_right:
    theme_toggle = st.toggle(
        "Dark Mode",
        value=(st.session_state["theme"] == "dark"),
        key="theme_switcher_toggle",
    )
    if theme_toggle != (st.session_state["theme"] == "dark"):
        st.session_state["theme"] = "dark" if theme_toggle else "light"
        st.rerun()
