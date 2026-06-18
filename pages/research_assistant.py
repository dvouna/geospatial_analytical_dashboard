"""
Research Assistant Page
Multi-dataset natural language querying with Google Gemini API.

Datasets loaded at startup:
  - overall_incidence   : overall_incidence.csv
  - top_5_cancers       : top_5_cancers.csv
  - population_detail   : population_detail.csv
  - deprivation         : iod_2025.csv
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from gemini_queries import GeminiQueryEngine
from visualizer import get_numeric_columns

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
    return {
        "Cancer Incidence (Overall)": _load(DATA_DIR / "overall_incidence.csv"),
        "Cancer Incidence (Top 5 by Area)": _load(DATA_DIR / "top_5_cancers.csv"),
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
    st.title("🔬 Future Leaders Innovation Challenge — Research Assistant")
    st.write(
        "Ask questions across the East of England cancer, population, "
        "and deprivation datasets. Powered by Google Gemini."
    )

    # ── Sidebar ──────────────────────────────────────────────────────────────
    st.sidebar.subheader("💡 Example Questions")
    for q in EXAMPLE_QUERIES:
        st.sidebar.caption(f"• {q}")

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

    # ── Gemini engine ──────────────────────────────────────────────────────────
    engine = GeminiQueryEngine()

    if not engine.is_available():
        st.warning(
            "⚠️ Gemini API key is not configured. "
            "Set `GEMINI_API_KEY` in your `.env` file to enable AI queries."
        )

    # ── Ask a Question ────────────────────────────────────────────────────────
    st.subheader("❓ Ask a Question")
    col1, col2 = st.columns([4, 1])
    with col1:
        user_query = st.text_input(
            "Enter your question:",
            placeholder="e.g. Which district has the highest cancer incidence and worst deprivation score?",
            label_visibility="collapsed",
            key="ra_query_input",
        )
    with col2:
        submit = st.button("🔍 Ask Gemini", type="primary", use_container_width=True)

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
        st.dataframe(df.head(10), use_container_width=True)

    with tab2:
        numeric_cols = get_numeric_columns(df)
        if numeric_cols:
            st.write("**Numeric Columns Summary:**")
            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
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
        st.dataframe(col_info, use_container_width=True)


if __name__ == "__main__":
    render_research_assistant_page()
