"""
Research Assistant Page
Multi-dataset natural language querying with Google Gemini API.

Datasets loaded at startup:
  - Cancer Incidence (Overall)
  - Cancer Incidence (Top 5 by Area)
  - Population by Ethnicity
  - Deprivation (Index of Multiple Deprivation 2025)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from gemini_queries import GeminiQueryEngine
from visualizer import get_numeric_columns, PLOTLY_LIGHT_LAYOUT
from utils.data_loader_cancer import get_cancer_overall_df, get_cancer_top5_df

DATA_DIR = Path(__file__).parent.parent / "data"

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


@st.cache_data
def _load(path: Path) -> pd.DataFrame:
    """Load a CSV, returning an empty DataFrame on failure."""
    try:
        return pd.read_csv(path)
    except Exception as exc:
        st.warning(f"⚠️ Could not load {path.name}: {exc}")
        return pd.DataFrame()


@st.cache_data
def load_all_datasets() -> dict[str, pd.DataFrame]:
    try:
        overall_df = get_cancer_overall_df(year_filter="all")
    except Exception:
        overall_df = pd.DataFrame()

    try:
        top5_df = get_cancer_top5_df(year_filter="all")
    except Exception:
        top5_df = pd.DataFrame()

    return {
        "Cancer Incidence (Overall)": overall_df,
        "Cancer Incidence (Top 5 by Area)": top5_df,
        "Population by Ethnicity": _load(DATA_DIR / "population_detail.csv"),
        "Index of Multiple Deprivation 2025": _load(DATA_DIR / "iod_2025.csv"),
    }


# ---------------------------------------------------------------------------
# Prompt builder — combines schema summaries from all four datasets
# ---------------------------------------------------------------------------


def _build_context(datasets: dict[str, pd.DataFrame]) -> str:
    """Produce a concise schema + sample summary for every loaded dataset."""
    parts = [
        "You are a public-health data analyst assistant.\n"
        "You have access to the following East of England datasets:\n"
    ]
    for name, df in datasets.items():
        if df.empty:
            parts.append(f"### {name}\n(Dataset unavailable)\n")
            continue
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        parts.append(
            f"### {name}\n"
            f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
            f"Columns: {', '.join(str(c) for c in df.columns)}\n"
            f"Numeric columns: {', '.join(numeric_cols[:10])}\n"
            f"Sample rows (first 3):\n{df.head(3).to_string(max_colwidth=40)}\n"
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Example queries (health / deprivation focused)
# ---------------------------------------------------------------------------

EXAMPLE_QUERIES = [
    "Which district in the East of England has the highest overall cancer incidence rate?",
    "Which area has the worst IMD rank combined with the highest lung cancer incidence?",
    "Compare deprivation ranks across districts — which are in the top 10 most deprived?",
    "What is the relationship between total population size and cancer incidence?",
    "Which districts have the highest proportion of Black ethnic groups in their population?",
    "Summarise the top 5 cancers by age group across all districts.",
    "Are there any districts where both employment deprivation and health deprivation ranks are poor?",
]


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------


def render_research_assistant_page():
    try:
        st.set_page_config(
            page_title="Research Assistant",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="collapsed",
        )
    except Exception:
        pass

    st.markdown(
        """
        <style>
        /* Reduce Streamlit's default top block padding */
        .block-container { padding-top: 1rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            font-family: 'Inter', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 2px;
            margin-top: 0;
            line-height: 1.15;
        ">Research Assistant</div>
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
            margin-bottom: 18px;
            margin-top: 2px;
        ">Ask questions across the East of England cancer, population, and deprivation datasets. Powered by Google Gemini.</div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load data at startup ──────────────────────────────────────────────────
    with st.spinner("Loading datasets…"):
        datasets = load_all_datasets()

    loaded = {name: df for name, df in datasets.items() if not df.empty}
    failed = [name for name, df in datasets.items() if df.empty]

    if failed:
        st.warning(f"⚠️ Could not load: {', '.join(failed)}")

    if not loaded:
        st.error("❌ No datasets could be loaded. Please check the `data/` directory.")
        return

    # ── Dataset status pills ──────────────────────────────────────────────────
    st.markdown("**Datasets available:**")
    cols = st.columns(len(datasets))
    for col, (name, df) in zip(cols, datasets.items()):
        if df.empty:
            col.error(f"✗ {name.split('(')[0].strip()}")
        else:
            col.success(f"✓ {name.split('(')[0].strip()} ({len(df):,} rows)")

    st.divider()

    # ── Gemini engine ────────────────────────────────----------------──────────
    engine = GeminiQueryEngine()

    if not engine.is_available():
        st.warning(
            "⚠️ Gemini API key is not configured. "
            "Set `GEMINI_API_KEY` in your `.env` file to enable AI queries."
        )

    # ── Ask a Question ────────────────────────────────────────────────────────
    st.subheader("❓ Ask a Question")

    with st.expander("💡 View Example Questions"):
        for q in EXAMPLE_QUERIES:
            st.write(f"• {q}")

    col1, col2 = st.columns([4, 1])
    with col1:
        user_query = st.text_input(
            "Enter your question:",
            placeholder="e.g. Which district has the highest cancer incidence and worst deprivation score?",
            label_visibility="collapsed",
            key="ra_query_input",
        )
    with col2:
        submit = st.button("🔍 Ask Gemini", type="primary", width="stretch")

    if submit and user_query:
        if not engine.is_available():
            st.error("❌ Gemini API key is not set — cannot process queries.")
        else:
            context = _build_context(loaded)
            full_prompt = (
                f"{context}\n\n"
                f"User question: {user_query}\n\n"
                "Please provide:\n"
                "1. A direct answer, referencing specific district names and values where possible.\n"
                "2. Any relevant patterns, comparisons, or caveats.\n"
                "3. Suggested follow-up questions if useful.\n\n"
                "Be concise but specific. If the answer requires data not present, say so clearly."
            )
            with st.spinner("🤔 Analysing across all datasets…"):
                try:
                    response = engine.model.generate_content(full_prompt)
                    st.success("✅ Analysis complete")
                    st.markdown(response.text)
                except Exception as exc:
                    st.error(f"❌ Gemini error: {exc}")

    st.divider()

    # ── Automatic Insights ────────────────────────────────────────────────────
    st.subheader("📊 Automatic Cross-Dataset Insights")
    if st.button("Generate Insights", key="ra_insights"):
        if not engine.is_available():
            st.warning("Please configure the Gemini API key first.")
        else:
            context = _build_context(loaded)
            prompt = (
                f"{context}\n\n"
                "Generate 5 key insights about public health, deprivation, and cancer incidence "
                "in the East of England. Reference specific districts and statistics. "
                "Focus on patterns, inequalities, and notable outliers."
            )
            with st.spinner("🤔 Generating insights…"):
                try:
                    response = engine.model.generate_content(prompt)
                    st.markdown(response.text)
                except Exception as exc:
                    st.error(f"❌ Gemini error: {exc}")

    st.divider()

    # ── Deprivation × Cancer Scatter ──────────────────────────────────────────
    st.subheader("🔗 Deprivation vs Cancer Incidence")
    st.write(
        "The core analytical question: is there a relationship between deprivation rank "
        "and overall cancer incidence in the East of England? Each point = one district."
    )
    _render_deprivation_cancer_scatter(loaded)

    st.divider()

    # ── Composite Vulnerability League Table ──────────────────────────────────
    st.subheader("🏆 Priority for Intervention — Composite Vulnerability Score")
    st.write(
        "Districts ranked by a composite score that combines IMD rank, overall cancer rate, "
        "and non-White population proportion. Higher score = greater need for targeted early-detection efforts."
    )
    _render_vulnerability_table(loaded)

    st.divider()

    # ── Data Overview ─────────────────────────────────────────────────────────
    st.subheader("🔍 Data Overview")
    selected_name = st.selectbox(
        "Select a dataset to explore:",
        options=list(loaded.keys()),
        key="ra_dataset_selector",
    )
    df = loaded[selected_name]

    tab1, tab2, tab3 = st.tabs(["Preview", "Statistics", "Columns"])

    with tab1:
        st.dataframe(df.head(10), width="stretch")

    with tab2:
        numeric_cols = get_numeric_columns(df)
        if numeric_cols:
            st.write("**Numeric Columns Summary:**")
            st.dataframe(df[numeric_cols].describe(), width="stretch")
        else:
            st.info("No numeric columns found in this dataset.")

    with tab3:
        st.write(f"**Total Columns: {len(df.columns)}**")
        col_info = pd.DataFrame(
            {
                "Column": df.columns,
                "Type": df.dtypes.astype(str).values,
                "Non-Null Count": df.count().values,
                "Null Count": df.isnull().sum().values,
            }
        )
        st.dataframe(col_info, width="stretch")


# ---------------------------------------------------------------------------
# Helper visualizations
# ---------------------------------------------------------------------------


def _render_deprivation_cancer_scatter(loaded: dict) -> None:
    """Scatter: IMD Overall Rank vs Overall Cancer Rate, one point per district."""
    imd_df = loaded.get("Index of Multiple Deprivation 2025", pd.DataFrame())
    cancer_df = loaded.get("Cancer Incidence (Overall)", pd.DataFrame())

    if imd_df.empty or cancer_df.empty:
        st.info("Both deprivation and cancer datasets are required for this chart.")
        return

    imd_code_col = "Local Authority District code (2024)"
    imd_name_col = "Local Authority District name (2024)"
    imd_rank_col = "Index of Multiple Deprivation (IMD) Rank"
    cancer_code_col = "Geography code"
    cancer_name_col = "Geography name "
    cancer_rate_col = "Rate"

    # Clean and merge on district code
    imd_clean = imd_df[[imd_code_col, imd_name_col, imd_rank_col]].dropna()
    cancer_clean = cancer_df[[cancer_code_col, cancer_name_col, cancer_rate_col]].copy()
    cancer_clean[cancer_rate_col] = pd.to_numeric(
        cancer_clean[cancer_rate_col].astype(str).str.replace(",", ""), errors="coerce"
    )
    cancer_clean = cancer_clean.dropna(subset=[cancer_rate_col])

    merged = pd.merge(
        imd_clean,
        cancer_clean,
        left_on=imd_code_col,
        right_on=cancer_code_col,
        how="inner",
    )

    if merged.empty:
        st.warning("No matching districts found between IMD and cancer datasets.")
        return

    fig = go.Figure()

    # 1. Add Scatter trace for districts
    fig.add_trace(
        go.Scatter(
            x=merged[imd_rank_col].tolist(),
            y=merged[cancer_rate_col].tolist(),
            mode="markers",
            name="Districts",
            text=merged[imd_name_col].tolist(),
            hovertemplate="<b>%{text}</b><br>IMD Rank: %{x}<br>Cancer Rate: %{y:.1f}<extra></extra>",
            marker=dict(
                size=9,
                color="#E63946",
                opacity=0.8,
                line=dict(width=1, color="DarkSlateGrey"),
            ),
        )
    )

    # 2. Add OLS regression line trace using numpy
    try:
        x_vals = merged[imd_rank_col].dropna().values
        y_vals = merged[cancer_rate_col].dropna().values
        if len(x_vals) > 1:
            slope, intercept = np.polyfit(x_vals, y_vals, 1)
            x_line = np.array([x_vals.min(), x_vals.max()])
            y_line = slope * x_line + intercept
            fig.add_trace(
                go.Scatter(
                    x=x_line.tolist(),
                    y=y_line.tolist(),
                    mode="lines",
                    name="OLS Trendline",
                    line=dict(color="#2A9D8F", width=2, dash="dash"),
                    hovertemplate="Trendline<extra></extra>",
                )
            )
    except Exception:
        pass

    fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
    fig.update_layout(
        title="Deprivation Rank vs Cancer Incidence Rate — East of England Districts",
        xaxis_title="IMD Overall Rank (lower = more deprived)",
        yaxis_title="Overall Cancer Rate (per 100,000)",
        height=480,
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Trendline = OLS regression. A negative slope would indicate that more deprived districts "
        "(lower rank number) tend to have higher cancer rates."
    )


def _render_vulnerability_table(loaded: dict) -> None:
    """Composite vulnerability score: normalise IMD rank + cancer rate + minority population."""
    imd_df = loaded.get("Index of Multiple Deprivation 2025", pd.DataFrame())
    cancer_df = loaded.get("Cancer Incidence (Overall)", pd.DataFrame())
    pop_df = loaded.get("Population by Ethnicity", pd.DataFrame())

    if imd_df.empty or cancer_df.empty:
        st.info(
            "Deprivation and cancer datasets are required for the vulnerability table."
        )
        return

    imd_code_col = "Local Authority District code (2024)"
    imd_name_col = "Local Authority District name (2024)"
    imd_rank_col = "Index of Multiple Deprivation (IMD) Rank"
    cancer_code_col = "Geography code"
    cancer_name_col = "Geography name "
    cancer_rate_col = "Rate"

    imd_clean = imd_df[[imd_code_col, imd_name_col, imd_rank_col]].dropna().copy()
    cancer_clean = cancer_df[[cancer_code_col, cancer_name_col, cancer_rate_col]].copy()
    cancer_clean[cancer_rate_col] = pd.to_numeric(
        cancer_clean[cancer_rate_col].astype(str).str.replace(",", ""), errors="coerce"
    )
    cancer_clean = cancer_clean.dropna(subset=[cancer_rate_col])

    merged = pd.merge(
        imd_clean,
        cancer_clean,
        left_on=imd_code_col,
        right_on=cancer_code_col,
        how="inner",
    )

    # Normalise each component 0→1
    max_rank = merged[imd_rank_col].max()
    # More deprived = lower rank → invert so higher score = worse deprivation
    merged["dep_score"] = 1 - (merged[imd_rank_col] - 1) / (max_rank - 1 + 1e-9)

    r_min = merged[cancer_rate_col].min()
    r_max = merged[cancer_rate_col].max()
    merged["cancer_score"] = (merged[cancer_rate_col] - r_min) / (r_max - r_min + 1e-9)

    # Add minority proportion if population data available
    has_pop = False
    if not pop_df.empty:
        pop_code_col = "LAD24CD"
        pop_df_clean = pop_df.copy()
        pop_df_clean.columns = [
            c.replace("\r\n", "\n").replace("\r", "\n") for c in pop_df_clean.columns
        ]
        sum_cols = [
            c
            for c in [
                "Asian Sum",
                "Black Sum",
                "Mixed Sum",
                "Others Sum",
                "Total - All Asian Groups",
                "Total - All Black Groups",
                "Total - All Mixed Groups",
                "Total - Other Ethnic Groups",
            ]
            if c in pop_df_clean.columns
        ]
        tot_col = next(
            (c for c in ["Total Population", "Total Sum"] if c in pop_df_clean.columns),
            None,
        )
        if pop_code_col in pop_df_clean.columns and sum_cols and tot_col:
            pop_clean = pop_df_clean[[pop_code_col] + sum_cols + [tot_col]].copy()
            for c in sum_cols + [tot_col]:
                pop_clean[c] = pd.to_numeric(
                    pop_clean[c].astype(str).str.replace(",", ""), errors="coerce"
                )
            pop_clean["minority_pct"] = (
                pop_clean[sum_cols].sum(axis=1)
                / pop_clean[tot_col].replace(0, np.nan)
                * 100
            )
            merged = pd.merge(
                merged,
                pop_clean[[pop_code_col, "minority_pct"]],
                left_on=imd_code_col,
                right_on=pop_code_col,
                how="left",
            )
            mp_min = merged["minority_pct"].min()
            mp_max = merged["minority_pct"].max()
            merged["pop_score"] = (merged["minority_pct"] - mp_min) / (
                mp_max - mp_min + 1e-9
            )
            merged["Composite Score"] = (
                merged["dep_score"] + merged["cancer_score"] + merged["pop_score"]
            ) / 3
            has_pop = True

    if not has_pop:
        merged["Composite Score"] = (merged["dep_score"] + merged["cancer_score"]) / 2
        merged["minority_pct"] = np.nan

    merged["Composite Score"] = (merged["Composite Score"] * 100).round(1)
    merged = merged.sort_values("Composite Score", ascending=False).reset_index(
        drop=True
    )
    merged.index += 1  # 1-based rank

    display_cols = {
        imd_name_col: "District",
        imd_rank_col: "IMD Rank",
        cancer_rate_col: "Cancer Rate (per 100k)",
    }
    if has_pop:
        display_cols["minority_pct"] = "Minority Pop. (%)"
    display_cols["Composite Score"] = "Vulnerability Score"

    table = merged[[c for c in display_cols if c in merged.columns]].rename(
        columns=display_cols
    )
    table.index.name = "Priority Rank"

    # Style the score column
    styled = table.style.background_gradient(
        subset=["Vulnerability Score"], cmap="YlOrRd"
    ).format(
        {
            "IMD Rank": "{:.0f}",
            "Cancer Rate (per 100k)": "{:.1f}",
            "Minority Pop. (%)": "{:.1f}",
            "Vulnerability Score": "{:.1f}",
        }
    )

    st.dataframe(styled, width="stretch", height=480)

    if has_pop:
        st.caption(
            "Score = average of normalised IMD deprivation, cancer rate, and minority population proportion. "
            "Higher score = greater priority for early cancer detection outreach."
        )
    else:
        st.caption(
            "Score = average of normalised IMD deprivation and cancer rate "
            "(population data not available for minority proportion)."
        )


def render_research_assistant_widget(key_suffix: str = ""):
    """Render a compact version of the AI Research Assistant for a sidebar/column panel."""
    st.subheader("🔬 AI Research Assistant")
    st.write("Ask questions across the East of England datasets.")

    # Load datasets
    datasets = load_all_datasets()
    loaded = {name: df for name, df in datasets.items() if not df.empty}
    if not loaded:
        st.error("No datasets could be loaded.")
        return

    engine = GeminiQueryEngine()
    if not engine.is_available():
        st.warning(
            "⚠️ Gemini API key is not configured. "
            "Set `GEMINI_API_KEY` in your `.env` file to enable AI queries."
        )
        return

    # User input
    user_query = st.text_input(
        "Ask Gemini:",
        placeholder="e.g. which area has highest cancer rate?",
        key=f"ra_widget_query_{key_suffix}",
        label_visibility="collapsed",
    )
    submit = st.button(
        "🔍 Ask Gemini",
        type="primary",
        width="stretch",
        key=f"ra_widget_submit_{key_suffix}",
    )

    if submit and user_query:
        context = _build_context(loaded)
        full_prompt = (
            f"{context}\n\n"
            f"User question: {user_query}\n\n"
            "Please provide a direct answer, referencing specific district names and values where possible. Be concise."
        )
        with st.spinner("Analyzing..."):
            try:
                response = engine.model.generate_content(full_prompt)
                st.markdown(response.text)
            except Exception as exc:
                st.error(f"Gemini error: {exc}")


if __name__ == "__main__":
    render_research_assistant_page()
