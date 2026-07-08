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
import plotly.graph_objects as go
from pathlib import Path
from gemini_queries import GeminiQueryEngine
from visualizer import get_numeric_columns, PLOTLY_LIGHT_LAYOUT
from utils.data_loader_cancer import get_cancer_overall_df, get_cancer_top5_df
from utils.code_cache import SemanticCodeCache
from utils.profile_generator import generate_district_profiles

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
# Prompt builder — cached, pre-aggregated context for Gemini
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _build_context(*dataframes: pd.DataFrame, names: tuple[str, ...] = ()) -> str:
    """
    Build a rich, pre-aggregated context string for Gemini.

    Decorated with ``@st.cache_data`` so the string is computed ONCE per
    unique combination of dataset content and then reused on every subsequent
    user query — Gemini never re-reads raw rows on each button click.

    The context includes, for each dataset:
    - Column schema and data types
    - Descriptive statistics (.describe()) across all numeric columns
    - The 5 highest and 5 lowest-ranked districts for the first key metric
    - Total district count

    Parameters
    ----------
    *dataframes
        DataFrames in the same order as ``names``.
    names
        Tuple of dataset names matching the positional dataframes.
    """
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
            (c for c in ["LAD24NM", "Geography name ", "Geography name",
                         "Local Authority District name (2024)"]
             if c in df.columns),
            None,
        )
        if name_col and numeric_cols:
            key_metric = numeric_cols[0]
            try:
                sorted_df = df[[name_col, key_metric]].dropna().sort_values(
                    key_metric, ascending=False
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
    """
    Thin helper that unpacks ``loaded`` into positional args so
    ``_build_context`` can be hashed and cached by Streamlit.

    Call this everywhere instead of calling ``_build_context`` directly.
    """
    names = tuple(loaded.keys())
    frames = tuple(loaded.values())
    return _build_context(*frames, names=names)


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
    st.session_state.setdefault("ra_chat_history", [])
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

    with st.popover("💡 Guide: Conversational AI Analysis", use_container_width=True):
        st.markdown(
            """
            **How to use the AI Research Assistant:**
            - **Conversational Queries**: Type natural language questions in the query box (e.g., *"Which districts in the East of England have high deprivation and also high breast cancer rates?"*).
            - **Integrated Context**: Gemini automatically receives contextual dataset summaries of population demographics, deprivation subdomains, and cancer incidence.
            - **Interactive Visualizations**: Review the correlation scatter plot of deprivation vs overall cancer rate, complete with OLS trendlines.
            - **Composite Vulnerability Priority**: Read the composite vulnerability table combining deprivation, cancer rates, and minority population shares to rank priority areas.
            """
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

    # ── Gemini engine ──────────────────────────────────────────────────────────
    engine = GeminiQueryEngine()

    if not engine.is_available():
        st.warning(
            "⚠️ Gemini API key is not configured. "
            "Set `GEMINI_API_KEY` in your `.env` file to enable AI queries."
        )

    # Initialize Semantic Cache
    cache_manager = SemanticCodeCache()

    # Sidebar settings
    with st.sidebar:
        st.markdown("### ⚙️ AI Settings")
        if st.button("🗑️ Clear Semantic Cache", use_container_width=True):
            cache_manager.clear_cache()
            st.success("Semantic cache cleared!")
        if st.button("🧹 Clear Chat History", use_container_width=True):
            st.session_state["ra_chat_history"] = []
            st.rerun()

    # ── Ask a Question ────────────────────────────────────────────────────────
    st.subheader("❓ Conversational AI Assistant")

    with st.expander("💡 View Example Questions"):
        for q in EXAMPLE_QUERIES:
            st.write(f"• {q}")

    # Render previous conversation history
    for chat in st.session_state["ra_chat_history"]:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])
            if "code" in chat and chat["code"]:
                with st.expander("💻 View Generated Code"):
                    st.code(chat["code"], language="python")
            if "df" in chat and chat["df"] is not None:
                st.dataframe(chat["df"], width="stretch")
            if "metric" in chat and chat["metric"] is not None:
                st.metric("Calculation Result", chat["metric"])

    # User input chat bar
    user_query = st.chat_input("Ask about East of England public health...")

    if user_query:
        # 1. Display user query instantly and append to history
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state["ra_chat_history"].append({"role": "user", "content": user_query})

        if not engine.is_available():
            err_msg = "❌ Gemini API key is not set — cannot process queries."
            with st.chat_message("assistant"):
                st.error(err_msg)
            st.session_state["ra_chat_history"].append({"role": "assistant", "content": err_msg})
        else:
            # Format last 3 conversation turns as history context
            turns = []
            for t in st.session_state["ra_chat_history"][:-1]:  # Exclude the current user question
                role_label = "User" if t["role"] == "user" else "Assistant"
                turns.append(f"{role_label}: {t['content']}")
            history_context = "\n".join(turns[-6:])  # Up to 3 full turns
            
            context = _get_context(loaded)
            
            with st.spinner("🤔 Checking query scope..."):
                in_scope = engine.is_query_in_scope(user_query, history_context)
                
            if not in_scope:
                warning_msg = "I am only configured to analyze and discuss public health, deprivation, and cancer trends within the East of England."
                with st.chat_message("assistant"):
                    st.warning(warning_msg)
                st.session_state["ra_chat_history"].append({"role": "assistant", "content": warning_msg})
            else:
                with st.spinner("🤔 Analyzing query..."):
                    # Ask Gemini to generate code or decide to use static profiles
                    code_suggestion = engine.generate_pandas_code(user_query, context, history_context)
                
                if "USE_PROFILES" in code_suggestion:
                    with st.spinner("⚡ Fetching district profiles..."):
                        profiles_json = generate_district_profiles(
                            df_cancer=loaded.get("Cancer Incidence (Overall)", pd.DataFrame()),
                            df_imd=loaded.get("Index of Multiple Deprivation 2025", pd.DataFrame()),
                            df_pop=loaded.get("Population by Ethnicity", pd.DataFrame())
                        )
                        answer = engine.answer_lookup_query(user_query, profiles_json, history_context)
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                    st.session_state["ra_chat_history"].append({"role": "assistant", "content": answer})
                else:
                    # Execution path for complex analytical queries
                    query_vector = engine.get_query_embedding(user_query)
                    cached_result = cache_manager.get_cached_code(query_vector) if query_vector else None
                    
                    if cached_result:
                        code_to_run, sim_score = cached_result
                        st.info(f"⚡ Semantic Cache Hit (similarity: {sim_score:.1%}) — running cached code")
                    else:
                        code_to_run = code_suggestion
                        
                    with st.spinner("⚙️ Executing analysis locally..."):
                        exec_result = engine.execute_pandas_code(code_to_run, loaded)
                    
                    if exec_result["status"] == "success":
                        res = exec_result["result"]
                        code = exec_result["code"]
                        
                        # Explain results in natural language
                        with st.spinner("✍️ Writing summary..."):
                            summary_input = f"Code executed:\n{code}\n\nResult:\n{str(res)[:1000]}"
                            explanation = engine.explain_results(user_query, summary_input, history_context)
                        
                        # Render assistant response bubble
                        with st.chat_message("assistant"):
                            st.markdown(explanation)
                            with st.expander("💻 View Generated Code"):
                                st.code(code, language="python")
                            
                            df_val, metric_val = None, None
                            if isinstance(res, (pd.DataFrame, pd.Series)):
                                st.dataframe(res, width="stretch")
                                df_val = res
                            elif isinstance(res, (int, float, np.integer, np.floating)):
                                st.metric("Calculation Result", f"{res:,.2f}")
                                metric_val = f"{res:,.2f}"
                            else:
                                st.write(res)
                        
                        # Append to chat history
                        history_entry = {
                            "role": "assistant",
                            "content": explanation,
                            "code": code,
                            "df": df_val,
                            "metric": metric_val
                        }
                        st.session_state["ra_chat_history"].append(history_entry)
                        
                        # If it was a cache miss, save the verified code to the cache
                        if not cached_result and query_vector and code_to_run:
                            cache_manager.add_to_cache(user_query, query_vector, code_to_run)
                    else:
                        error_msg = f"❌ Execution Error: {exec_result['error']}"
                        with st.chat_message("assistant"):
                            st.error(error_msg)
                            with st.expander("💻 View Failed Code"):
                                st.code(exec_result["code"], language="python")
                        st.session_state["ra_chat_history"].append({
                            "role": "assistant",
                            "content": error_msg,
                            "code": exec_result["code"]
                        })
        st.rerun()

    st.divider()

    # ── Automatic Insights ────────────────────────────────────────────────────
    st.subheader("📊 Automatic Cross-Dataset Insights")
    if st.button("Generate Insights", key="ra_insights"):
        if not engine.is_available():
            st.warning("Please configure the Gemini API key first.")
        else:
            context = _get_context(loaded)  # cached — no rebuild on each click
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
    """Render a compact, conversational version of the AI Research Assistant for a sidebar/column panel."""
    st.subheader("🔬 AI Research Assistant")
    st.session_state.setdefault("ra_chat_history", [])

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

    cache_manager = SemanticCodeCache()

    # Clear chat button in widget
    col_w1, col_w2 = st.columns([2, 1])
    with col_w2:
        if st.button("🧹 Clear Chat", key=f"ra_widget_clear_{key_suffix}", use_container_width=True):
            st.session_state["ra_chat_history"] = []
            st.rerun()
    with col_w1:
        st.caption("Shared conversation history")

    # Render history inside a scrollable container of fixed height
    with st.container(height=300):
        if not st.session_state["ra_chat_history"]:
            st.info("Ask any question about East of England demographics, deprivation, or cancer data below!")
        for chat in st.session_state["ra_chat_history"]:
            with st.chat_message(chat["role"]):
                st.markdown(chat["content"])
                if "code" in chat and chat["code"]:
                    with st.expander("💻 View Code"):
                        st.code(chat["code"], language="python")
                if "df" in chat and chat["df"] is not None:
                    st.dataframe(chat["df"], width="stretch")
                if "metric" in chat and chat["metric"] is not None:
                    st.metric("Result", chat["metric"])

    # Sticky chat input for this widget
    widget_query = st.chat_input("Ask Gemini...", key=f"ra_widget_input_{key_suffix}")

    if widget_query:
        # Append user query
        st.session_state["ra_chat_history"].append({"role": "user", "content": widget_query})
        
        # Build history context
        turns = []
        for t in st.session_state["ra_chat_history"][:-1]:
            role_label = "User" if t["role"] == "user" else "Assistant"
            turns.append(f"{role_label}: {t['content']}")
        history_context = "\n".join(turns[-6:])  # Up to 3 turns
        
        if not engine.is_query_in_scope(widget_query, history_context):
            warning_msg = "⚠️ Question out of scope for the East of England."
            st.session_state["ra_chat_history"].append({"role": "assistant", "content": warning_msg})
        else:
            context = _get_context(loaded)
            
            # Ask Gemini to generate code or decide to use static profiles
            code_suggestion = engine.generate_pandas_code(widget_query, context, history_context)
            
            if "USE_PROFILES" in code_suggestion:
                profiles_json = generate_district_profiles(
                    df_cancer=loaded.get("Cancer Incidence (Overall)", pd.DataFrame()),
                    df_imd=loaded.get("Index of Multiple Deprivation 2025", pd.DataFrame()),
                    df_pop=loaded.get("Population by Ethnicity", pd.DataFrame())
                )
                answer = engine.answer_lookup_query(widget_query, profiles_json, history_context)
                st.session_state["ra_chat_history"].append({"role": "assistant", "content": answer})
            else:
                # Execution path for complex analytical queries
                query_vector = engine.get_query_embedding(widget_query)
                cached_result = cache_manager.get_cached_code(query_vector) if query_vector else None
                
                if cached_result:
                    code_to_run, _ = cached_result
                else:
                    code_to_run = code_suggestion
                    
                exec_result = engine.execute_pandas_code(code_to_run, loaded)
                
                if exec_result["status"] == "success":
                    res = exec_result["result"]
                    code = exec_result["code"]
                    
                    summary_input = f"Code executed:\n{code}\n\nResult:\n{str(res)[:1000]}"
                    explanation = engine.explain_results(widget_query, summary_input, history_context)
                    
                    df_val, metric_val = None, None
                    if isinstance(res, (pd.DataFrame, pd.Series)):
                        df_val = res
                    elif isinstance(res, (int, float, np.integer, np.floating)):
                        metric_val = f"{res:,.2f}"
                        
                    st.session_state["ra_chat_history"].append({
                        "role": "assistant",
                        "content": explanation,
                        "code": code,
                        "df": df_val,
                        "metric": metric_val
                    })
                    
                    # If cache miss, save verified code
                    if not cached_result and query_vector and code_to_run:
                        cache_manager.add_to_cache(widget_query, query_vector, code_to_run)
                else:
                    error_msg = f"❌ Execution Error: {exec_result['error']}"
                    st.session_state["ra_chat_history"].append({
                        "role": "assistant",
                        "content": error_msg,
                        "code": exec_result["code"]
                    })
        st.rerun()


if __name__ == "__main__":
    render_research_assistant_page()
