"""
Cancer Health Dashboard - East of England
-------------------------------------------
Single entrypoint / router.

Responsibilities:
  1. st.set_page_config  (must be first Streamlit call)
  2. Environment validation
  3. Global CSS + design-token injection (Inter font, light/dark tokens)
  4. Dark-mode sidebar toggle + JS attribute injection
  5. st.navigation -- controls sidebar page labels and routing

All dashboard content lives in home_page.py and pages/*.py.
"""

from __future__ import annotations

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

# -- Global CSS -- FLC26 Design System ----------------------------------------

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --color-bg:             #F8FAFC;
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

[data-theme="dark"] {
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
}

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--color-bg) !important;
    color: var(--color-text-body);
}
h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--color-text-heading);
}
code, pre, .monospace { font-family: 'JetBrains Mono', monospace; }
*:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }

.gradient-title {
    background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    font-family: 'Inter', sans-serif;
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 4px;
    letter-spacing: -0.03em;
}
.sub-title {
    text-align: center;
    font-size: 1.05rem;
    color: var(--color-text-muted);
    margin-bottom: 28px;
    font-weight: 400;
}

[data-testid="column"] {
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 24px !important;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.2s ease;
}
[data-testid="column"]:hover { box-shadow: var(--shadow-md); }

.kpi-card {
    background-color: var(--color-surface-alt);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: var(--shadow-sm);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--color-border-hover); }
.kpi-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    margin-bottom: 6px;
}
.kpi-value {
    font-family: 'Inter', sans-serif;
    font-size: 1.6rem;
    color: var(--color-text-heading);
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.02em;
}
.kpi-badge {
    display: inline-block;
    padding: 3px 10px;
    font-size: 0.72rem;
    border-radius: 20px;
    font-weight: 600;
    margin-top: 8px;
    letter-spacing: 0.02em;
}
.badge-danger  { background-color: var(--color-danger-bg);  color: var(--color-danger);  }
.badge-warning { background-color: var(--color-warning-bg); color: var(--color-warning); }
.badge-success { background-color: var(--color-success-bg); color: var(--color-success); }

div[data-testid="stTabs"] > div:first-child button {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--color-text-muted);
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    transition: color 0.2s ease, background-color 0.2s ease;
}
div[data-testid="stTabs"] > div:first-child button[aria-selected="true"] { color: var(--color-primary); border-bottom-color: var(--color-primary) !important; }
div[data-testid="stTabs"] > div:first-child button:hover { color: var(--color-primary); background-color: var(--color-primary-light); }

div.row-widget.stRadio > div[role="radiogroup"] {
    background-color: var(--color-surface-alt);
    padding: 5px;
    border-radius: 30px;
    border: 1px solid var(--color-border);
    display: flex;
    justify-content: center;
    gap: 4px;
    width: fit-content;
    margin: 0 auto 20px auto;
}
div.row-widget.stRadio > div[role="radiogroup"] > label {
    background: transparent;
    padding: 7px 18px;
    border-radius: 24px;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--color-text-muted);
    border: none;
    transition: all 0.2s ease;
    cursor: pointer;
}
div.row-widget.stRadio > div[role="radiogroup"] > label:hover { color: var(--color-primary); background-color: var(--color-primary-light); }
div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] { background-color: var(--color-primary); color: #FFFFFF !important; box-shadow: 0 3px 8px rgba(31,119,180,0.25); }

[data-testid="stSidebar"] { background-color: var(--color-surface); border-right: 1px solid var(--color-border); }
[data-testid="stSidebarNav"] a {
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    font-weight: 500;
    color: var(--color-text-body);
    border-radius: var(--radius-sm);
    transition: background-color 0.15s ease, color 0.15s ease;
}
[data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebarNav"] a[aria-selected="true"] { background-color: var(--color-primary-light); color: var(--color-primary); font-weight: 600; }

[data-testid="stMetric"] { background-color: var(--color-surface-alt); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 14px 18px; }
[data-testid="stMetricLabel"] p { font-family: 'Inter', sans-serif; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--color-text-muted) !important; }
[data-testid="stMetricValue"] { font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: -0.01em; color: var(--color-text-heading) !important; }

[data-testid="stAlert"] { border-radius: var(--radius-md); border-left-width: 4px; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--color-surface-alt); }
::-webkit-scrollbar-thumb { background: var(--color-border-hover); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--color-text-subtle); }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# -- Page routing via st.navigation ------------------------------------------
# Defines sidebar labels explicitly -- "Home" replaces the legacy "App" label.

pg = st.navigation(
    [
        st.Page("home_page.py", title="Home", icon="🏠", default=True),
        st.Page("pages/1_Population_Demographics.py", title="Population Demographics", icon="👥"),
        st.Page("pages/2_Deprivation_Analysis.py", title="Deprivation Analysis", icon="📊"),
        st.Page("pages/3_Cancer_Trends.py", title="Cancer Trends", icon="🎗️"),
        st.Page("pages/5_AI_Research_Assistant.py", title="Research Assistant", icon="🤖"),
    ]
)
pg.run()