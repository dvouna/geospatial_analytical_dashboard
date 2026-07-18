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
from pathlib import Path

from gemini_queries import get_gemini_engine
from visualizer import get_numeric_columns
from utils.data_loader_cancer import get_cancer_overall_df, get_cancer_top5_df
from utils.code_cache import SemanticCodeCache
from utils.profile_generator import generate_district_profiles

DATA_DIR = Path(__file__).parent.parent / "data"

# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------

# Maximum permitted length (characters) for a user-submitted query. Queries
# beyond this limit are rejected before reaching the Gemini API to prevent
# token-cost abuse and to limit prompt-injection surface area.
MAX_QUERY_LEN = 2000

# Maximum length (characters) preserved from each individual conversation
# turn when building the history context injected into Gemini prompts.
# This limits the amount of injected content a user can embed in history.
_MAX_TURN_LEN = 500


def _build_safe_history_context(history: list[dict], n_turns: int = 6) -> str:
    """
    Build a sanitised conversation-history string for injection into Gemini
    prompts.

    Security measures applied:
    - Each turn is truncated to ``_MAX_TURN_LEN`` characters so a user cannot
      plant large instruction blocks via their own messages.
    - Common prompt-injection trigger phrases are stripped from user turns
      (e.g. lines beginning with "Ignore", "Forget", "System:").
    - The resulting block is wrapped in XML-like delimiters so that the model
      can distinguish conversation history from the live instruction text.

    Parameters
    ----------
    history:
        The current ``ra_chat_history`` session-state list (excluding the
        current user message — pass the slice ``[:-1]``).
    n_turns:
        Maximum number of individual role turns to include (default 6 = 3
        full user/assistant rounds).
    """
    # Injection-trigger prefixes to strip from user content (case-insensitive).
    _INJECTION_PREFIXES = (
        "ignore ",
        "forget ",
        "disregard ",
        "override ",
        "system:",
        "[system]",
        "<system>",
        "assistant:",
        "[assistant]",
        "new instruction",
        "act as",
        "you are now",
    )

    safe_turns: list[str] = []
    for turn in history[-n_turns:]:
        role_label = "User" if turn.get("role") == "user" else "Assistant"
        raw_content = str(turn.get("content", ""))

        # Strip injection-trigger lines from user turns only.
        if role_label == "User":
            filtered_lines = [
                line
                for line in raw_content.splitlines()
                if not line.strip().lower().startswith(_INJECTION_PREFIXES)
            ]
            raw_content = " ".join(filtered_lines)

        # Truncate each turn to limit planted-instruction size.
        truncated = raw_content[:_MAX_TURN_LEN]
        if len(raw_content) > _MAX_TURN_LEN:
            truncated += " [truncated]"

        safe_turns.append(f"{role_label}: {truncated}")

    if not safe_turns:
        return ""

    body = "\n".join(safe_turns)
    return f"<conversation_history>\n{body}\n</conversation_history>"


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
            (
                c
                for c in [
                    "LAD24NM",
                    "Geography name ",
                    "Geography name",
                    "Local Authority District name (2024)",
                ]
                if c in df.columns
            ),
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
        '<div class="page-title">Research Assistant</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="page-body">Ask questions across the East of England cancer, population, and deprivation datasets. Powered by Google Gemini.</div>',
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

    # ── Gemini engine ──────────────────────────────────────────────────────────
    # Use the session-cached engine singleton to avoid re-initialising
    # the GenerativeModel on every Streamlit rerun.
    engine = get_gemini_engine()

    if not engine.is_available():
        st.warning(
            "⚠️ Gemini API key is not configured. "
            "Set `GEMINI_API_KEY` in your `.env` file to enable AI queries."
        )

    # Initialize Semantic Cache
    cache_manager = SemanticCodeCache()

    # ── Ask a Question ────────────────────────────────────────────────────────
    from utils.device import get_is_mobile

    if not get_is_mobile():
        col_chat, col_context = st.columns([58, 42], gap="large")
    else:
        col_chat = st.container()
        col_context = None

    with col_chat:
        with st.expander("💡 Example questions", expanded=not get_is_mobile()):
            for q in EXAMPLE_QUERIES:
                st.markdown(f"- {q}")

        # Render previous conversation history
        if get_is_mobile() and len(st.session_state["ra_chat_history"]) > 0:
            history_container = st.container(height=400)
        else:
            history_container = st.container()

        with history_container:
            for chat in st.session_state["ra_chat_history"]:
                with st.chat_message(chat["role"]):
                    st.markdown(chat["content"])
                    if "df" in chat and chat["df"] is not None:
                        st.dataframe(chat["df"], width="stretch")
                    if "metric" in chat and chat["metric"] is not None:
                        st.metric("Calculation Result", chat["metric"])

        # User input chat bar
        user_query = st.chat_input("Ask about East of England public health...")

    if col_context:
        with col_context:
            st.markdown("### 📋 Analyst Context Panel")

            # Show last query statistics if any
            if st.session_state["ra_chat_history"]:
                last_assistant_msg = next(
                    (
                        c
                        for c in reversed(st.session_state["ra_chat_history"])
                        if c["role"] == "assistant"
                    ),
                    None,
                )
                if last_assistant_msg:
                    st.success("🤖 **Last Response Generated**")
                    st.text_area(
                        "Copy last explanation:",
                        value=last_assistant_msg["content"],
                        height=200,
                        key="last_resp_textarea",
                    )

            st.markdown("#### 🗄️ Available Datasets & Schema")
            st.info(
                "• **Index of Multiple Deprivation 2025**: Ranks for all 7 subdomains across all districts.\n"
                "• **Population Demographics**: Census population counts segmented by ethnic subgroups.\n"
                "• **Cancer Incidence rates**: ONS age-standardised Crude Rates and 95% Confidence Intervals (2018-2022)."
            )
            st.markdown("#### 💡 Tips for Prompting")
            st.write(
                "1. Be specific about the cancer type (e.g. *lung*, *breast*, *skin*).\n"
                "2. Ask for comparisons between specific districts (e.g. *'Compare deprivation in Norwich and Ipswich'*).\n"
                "3. You can request mathematical aggregates (e.g. *'What is the average breast cancer rate across the top 10 most deprived districts?'*)."
            )

    if user_query:
        # Reject oversized inputs before any API call to prevent token-cost
        # abuse and to reduce the prompt-injection surface area.
        if len(user_query) > MAX_QUERY_LEN:
            st.warning(
                f"⚠️ Query too long ({len(user_query):,} chars). "
                f"Please limit to {MAX_QUERY_LEN:,} characters."
            )
            st.stop()

        # 1. Display user query instantly and append to history
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state["ra_chat_history"].append(
            {"role": "user", "content": user_query}
        )

        if not engine.is_available():
            err_msg = "❌ Gemini API key is not set — cannot process queries."
            with st.chat_message("assistant"):
                st.error(err_msg)
            st.session_state["ra_chat_history"].append(
                {"role": "assistant", "content": err_msg}
            )
        else:
            # Build a sanitised history context to limit prompt-injection risk.
            # _build_safe_history_context() truncates, strips injection phrases,
            # and wraps the block in clear delimiters.
            history_context = _build_safe_history_context(
                st.session_state["ra_chat_history"][
                    :-1
                ]  # Exclude current user question
            )

            context = _get_context(loaded)

            with st.spinner("🤔 Checking query scope..."):
                in_scope = engine.is_query_in_scope(user_query, history_context)

            if not in_scope:
                warning_msg = "I am only configured to analyze and discuss public health, deprivation, and cancer trends within the East of England."
                with st.chat_message("assistant"):
                    st.warning(warning_msg)
                st.session_state["ra_chat_history"].append(
                    {"role": "assistant", "content": warning_msg}
                )
            else:
                with st.spinner("🤔 Analyzing query..."):
                    # Ask Gemini to generate code or decide to use static profiles
                    code_suggestion = engine.generate_pandas_code(
                        user_query, context, history_context
                    )

                if "USE_PROFILES" in code_suggestion:
                    with st.spinner("⚡ Fetching district profiles..."):
                        profiles_json = generate_district_profiles(
                            df_cancer=loaded.get(
                                "Cancer Incidence (Overall)", pd.DataFrame()
                            ),
                            df_imd=loaded.get(
                                "Index of Multiple Deprivation 2025", pd.DataFrame()
                            ),
                            df_pop=loaded.get(
                                "Population by Ethnicity", pd.DataFrame()
                            ),
                        )
                        answer = engine.answer_lookup_query(
                            user_query, profiles_json, history_context
                        )
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                    st.session_state["ra_chat_history"].append(
                        {"role": "assistant", "content": answer}
                    )
                else:
                    # Execution path for complex analytical queries
                    query_vector = engine.get_query_embedding(user_query)
                    cached_result = (
                        cache_manager.get_cached_code(query_vector)
                        if query_vector
                        else None
                    )

                    if cached_result:
                        code_to_run, sim_score = cached_result
                        st.info(
                            f"⚡ Semantic Cache Hit (similarity: {sim_score:.1%}) — running cached code"
                        )
                    else:
                        code_to_run = code_suggestion

                    with st.spinner("⚙️ Executing analysis locally..."):
                        exec_result = engine.execute_pandas_code(code_to_run, loaded)

                    if exec_result["status"] == "success":
                        res = exec_result["result"]
                        code = exec_result["code"]

                        # Explain results in natural language
                        with st.spinner("✍️ Writing summary..."):
                            summary_input = (
                                f"Code executed:\n{code}\n\nResult:\n{str(res)[:1000]}"
                            )
                            explanation = engine.explain_results(
                                user_query, summary_input, history_context
                            )

                        # Render assistant response bubble
                        with st.chat_message("assistant"):
                            st.markdown(explanation)

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
                            "metric": metric_val,
                        }
                        st.session_state["ra_chat_history"].append(history_entry)

                        # If it was a cache miss, save the verified code to the cache
                        if not cached_result and query_vector and code_to_run:
                            cache_manager.add_to_cache(
                                user_query, query_vector, code_to_run
                            )
                    else:
                        error_msg = f"❌ Execution Error: {exec_result['error']}"
                        with st.chat_message("assistant"):
                            st.error(error_msg)
                        st.session_state["ra_chat_history"].append(
                            {
                                "role": "assistant",
                                "content": error_msg,
                                "code": exec_result["code"],
                            }
                        )
        st.rerun()

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


def render_research_assistant_widget(key_suffix: str = ""):
    """Render a compact, conversational version of the AI Research Assistant for a sidebar/column panel."""
    st.subheader("Research Assistant")
    st.session_state.setdefault("ra_chat_history", [])

    # Load datasets
    datasets = load_all_datasets()
    loaded = {name: df for name, df in datasets.items() if not df.empty}
    if not loaded:
        st.error("No datasets could be loaded.")
        return

    engine = get_gemini_engine()
    if not engine.is_available():
        st.warning(
            "⚠️ Gemini API key is not configured. "
            "Set `GEMINI_API_KEY` in your `.env` file to enable AI queries."
        )
        return

    cache_manager = SemanticCodeCache()

    st.caption("Shared conversation history")

    # Render history inside a scrollable container of fixed height
    with st.container(height=300):
        if not st.session_state["ra_chat_history"]:
            st.info(
                "Ask any question about East of England demographics, deprivation, or cancer data below!"
            )
        for chat in st.session_state["ra_chat_history"]:
            with st.chat_message(chat["role"]):
                st.markdown(chat["content"])
                if "df" in chat and chat["df"] is not None:
                    st.dataframe(chat["df"], width="stretch")
                if "metric" in chat and chat["metric"] is not None:
                    st.metric("Result", chat["metric"])

    # Sticky chat input for this widget
    widget_query = st.chat_input(
        "Ask Research Assistant...", key=f"ra_widget_input_{key_suffix}"
    )

    if widget_query:
        # Reject oversized inputs before any API call.
        if len(widget_query) > MAX_QUERY_LEN:
            st.session_state["ra_chat_history"].append(
                {
                    "role": "assistant",
                    "content": (
                        f"⚠️ Query too long ({len(widget_query):,} chars). "
                        f"Please limit to {MAX_QUERY_LEN:,} characters."
                    ),
                }
            )
            st.rerun()

        # Append user query
        st.session_state["ra_chat_history"].append(
            {"role": "user", "content": widget_query}
        )

        # Build a sanitised history context to limit prompt-injection risk.
        history_context = _build_safe_history_context(
            st.session_state["ra_chat_history"][:-1]  # Exclude current user message
        )

        if not engine.is_query_in_scope(widget_query, history_context):
            warning_msg = "⚠️ Question out of scope for the East of England."
            st.session_state["ra_chat_history"].append(
                {"role": "assistant", "content": warning_msg}
            )
        else:
            context = _get_context(loaded)

            # Ask Gemini to generate code or decide to use static profiles
            code_suggestion = engine.generate_pandas_code(
                widget_query, context, history_context
            )

            if "USE_PROFILES" in code_suggestion:
                profiles_json = generate_district_profiles(
                    df_cancer=loaded.get("Cancer Incidence (Overall)", pd.DataFrame()),
                    df_imd=loaded.get(
                        "Index of Multiple Deprivation 2025", pd.DataFrame()
                    ),
                    df_pop=loaded.get("Population by Ethnicity", pd.DataFrame()),
                )
                answer = engine.answer_lookup_query(
                    widget_query, profiles_json, history_context
                )
                st.session_state["ra_chat_history"].append(
                    {"role": "assistant", "content": answer}
                )
            else:
                # Execution path for complex analytical queries
                query_vector = engine.get_query_embedding(widget_query)
                cached_result = (
                    cache_manager.get_cached_code(query_vector)
                    if query_vector
                    else None
                )

                if cached_result:
                    code_to_run, _ = cached_result
                else:
                    code_to_run = code_suggestion

                exec_result = engine.execute_pandas_code(code_to_run, loaded)

                if exec_result["status"] == "success":
                    res = exec_result["result"]
                    code = exec_result["code"]

                    summary_input = (
                        f"Code executed:\n{code}\n\nResult:\n{str(res)[:1000]}"
                    )
                    explanation = engine.explain_results(
                        widget_query, summary_input, history_context
                    )

                    df_val, metric_val = None, None
                    if isinstance(res, (pd.DataFrame, pd.Series)):
                        df_val = res
                    elif isinstance(res, (int, float, np.integer, np.floating)):
                        metric_val = f"{res:,.2f}"

                    st.session_state["ra_chat_history"].append(
                        {
                            "role": "assistant",
                            "content": explanation,
                            "code": code,
                            "df": df_val,
                            "metric": metric_val,
                        }
                    )

                    # If cache miss, save verified code
                    if not cached_result and query_vector and code_to_run:
                        cache_manager.add_to_cache(
                            widget_query, query_vector, code_to_run
                        )
                else:
                    error_msg = f"❌ Execution Error: {exec_result['error']}"
                    st.session_state["ra_chat_history"].append(
                        {
                            "role": "assistant",
                            "content": error_msg,
                            "code": exec_result["code"],
                        }
                    )
        st.rerun()


if __name__ == "__main__":
    render_research_assistant_page()
