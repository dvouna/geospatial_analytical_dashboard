"""
General Insights Page
Displays pre-generated cross-dataset insights from a local file, reducing API latency and cost.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import sys
import numpy as np
from pathlib import Path

from config import Config
from gemini_queries import get_gemini_engine
from utils.data_loader_cancer import get_cancer_overall_df, get_cancer_top5_df

DATA_DIR = Path(__file__).parent.parent / "data"
INSIGHTS_FILE = DATA_DIR / "global_insights.md"


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


@st.cache_data(show_spinner=False)
def _build_context(*dataframes: pd.DataFrame, names: tuple[str, ...] = ()) -> str:
    parts = [
        "You are a public-health data analyst for the East of England.\n"
        "Below are pre-computed statistical summaries of the available datasets.\n"
        "Do NOT ask for raw data — use these summaries to answer questions precisely.\n"
    ]

    for name, df in zip(names, dataframes):
        if df.empty:
            parts.append(f"### {name}\n(Dataset unavailable)\n")
            continue

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        text_cols = df.select_dtypes(include="object").columns.tolist()

        # Schema block
        schema = (
            f"### {name}\n"
            f"Rows: {df.shape[0]}  |  Columns: {df.shape[1]}\n"
            f"Text columns: {', '.join(text_cols[:8])}\n"
            f"Numeric columns: {', '.join(numeric_cols[:15])}\n"
        )

        # Descriptive statistics for numeric columns
        if numeric_cols:
            desc = df[numeric_cols[:15]].describe().round(2).to_string()
            schema += f"\nDescriptive statistics:\n{desc}\n"

        # Top 5 and bottom 5 for the first key numeric metric
        name_col = next(
            (c for c in ["District Name", "Geography Name"] if c in df.columns),
            None,
        )
        if name_col and numeric_cols:
            key_metric = numeric_cols[0]
            try:
                sorted_df = (
                    df[[name_col, key_metric]]
                    .dropna()
                    .sort_values(key_metric, ascending=False)
                )
                top5 = sorted_df.head(5).to_string(index=False)
                bot5 = sorted_df.tail(5).to_string(index=False)
                schema += (
                    f"\nHighest 5 districts by {key_metric}:\n{top5}\n"
                    f"\nLowest 5 districts by {key_metric}:\n{bot5}\n"
                )
            except Exception:
                pass

        parts.append(schema)

    return "\n".join(parts)


def _get_context(loaded: dict[str, pd.DataFrame]) -> str:
    names = tuple(loaded.keys())
    frames = tuple(loaded.values())
    return _build_context(*frames, names=names)


def _generate_and_save_insights(loaded: dict[str, pd.DataFrame]) -> str:
    """Generate insights via Gemini and save to global_insights.md."""
    engine = get_gemini_engine()
    if not engine.is_available():
        return "❌ Gemini API key is not configured. Set `GEMINI_API_KEY` in your `.env` file to enable AI queries."

    context = _get_context(loaded)
    prompt = (
        f"{context}\n\n"
        "Generate 5 key insights about public health, deprivation, and cancer incidence "
        "in the East of England. Reference specific districts and statistics. "
        "Focus on patterns, inequalities, and notable outliers."
    )
    try:
        response = engine.model.generate_content(prompt)
        text = response.text
        # Write to local file for cache persistence
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(INSIGHTS_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        return text
    except Exception as exc:
        print(f"[general_insights] Gemini error: {exc}", file=sys.stderr)
        return f"❌ Gemini encountered an error. Please try again. Details: {exc}"


def render_general_insights_page():
    try:
        st.set_page_config(
            page_title="General Insights",
            page_icon="💡",
            layout="wide",
            initial_sidebar_state="collapsed",
        )
    except Exception:
        pass

    st.markdown(
        """
        <style>
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
            margin-top: 1.5rem;
            line-height: 1.15;
        ">General Insights</div>
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
        ">Pre-generated public health and cancer trends insights for the East of England.</div>
        """,
        unsafe_allow_html=True,
    )

    datasets = load_all_datasets()
    loaded = {name: df for name, df in datasets.items() if not df.empty}

    if not loaded:
        st.error("❌ No datasets could be loaded. Please check the `data/` directory.")
        return

    # Check if pre-generated file exists
    insights_content = ""
    if INSIGHTS_FILE.exists():
        try:
            with open(INSIGHTS_FILE, "r", encoding="utf-8") as f:
                insights_content = f.read()
        except Exception as exc:
            st.warning(f"⚠️ Failed to read pre-generated insights: {exc}")

    if insights_content:
        st.markdown(insights_content)
    else:
        st.info("Insights have not been generated yet. Click the button below to generate them.")

    st.divider()

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        button_label = "🔄 Refresh Insights" if insights_content else "✨ Generate Insights"
        if st.button(button_label, use_container_width=True):
            with st.spinner("Analyzing public health data and generating insights…"):
                text = _generate_and_save_insights(loaded)
                if not text.startswith("❌"):
                    st.toast("Insights updated and saved successfully!")
                    st.rerun()
                else:
                    st.error(text)

    st.divider()

    # ── Composite Vulnerability League Table ──────────────────────────────────
    st.subheader("🏆 Priority for Intervention — Composite Vulnerability Score")
    st.write(
        "Districts ranked by a composite score that combines IMD rank, overall cancer rate, "
        "and non-White population proportion. Higher score = greater need for targeted early-detection efforts."
    )
    _render_vulnerability_table(loaded)


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

    imd_code_col = "District Code"
    imd_name_col = "District Name"
    imd_rank_col = "Overall IMD Rank"
    cancer_code_col = "District Code"
    cancer_name_col = "District Name"
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
        suffixes=("", "_cancer"),
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
        pop_code_col = "District Code"
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
                "All Asians (Total)",
                "All Balcks (Total)",
                "All Mixed Ethnic Groups (Total)",
                "Other Ethnic Groups (Total)",
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
        imd_code_col: "District Code",
        imd_name_col: "District Name",
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


if __name__ == "__main__":
    render_general_insights_page()
