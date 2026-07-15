"""
Gemini Query Engine Module
Handles natural language queries and code generation via Google Gemini API
"""

from __future__ import annotations

import hashlib
import html
import sys
import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import Optional, Any

try:
    from config import Config as _Config

    _DEBUG = _Config.DEBUG
except Exception:
    _DEBUG = False

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    GenerationConfig = None  # type: ignore

from config import Config

SYSTEM_INSTRUCTION = """
You are the dedicated East of England Public Health AI Assistant. 
Your sole task is to analyze, lookup, and answer questions about public health, deprivation, and cancer demographics within the 45 local authority districts in the East of England.

Strict Boundaries:
1. Base all answers strictly on the provided district profiles or dataset schemas.
2. If a user asks about any region outside the East of England (e.g., London, Manchester, Scotland, Wales, etc.) or any topic completely unrelated to public health/geospatial analytics, you must politely decline to answer, using the standard message: 
   "I am only configured to analyze and discuss public health, deprivation, and cancer trends within the East of England."
3. Do not answer general questions (e.g., historical facts, writing generic code, creative writing).
"""

# ---------------------------------------------------------------------------
# Module-level keyword pre-filter (Fix #5 — no API call needed for common queries)
# ---------------------------------------------------------------------------
# Keywords that unambiguously relate to the dashboard's subject domain.
# Used as a fast local pre-filter before spending an API call on scope
# classification — if ANY keyword is present the query is assumed in-scope
# and the Gemini call is skipped entirely.
_SCOPE_KEYWORDS: frozenset = frozenset(
    {
        "cancer",
        "incidence",
        "tumour",
        "tumor",
        "oncol",
        "deprivation",
        "imd",
        "depriv",
        "poverty",
        "income",
        "employment",
        "population",
        "demographic",
        "ethnic",
        "ethnicity",
        "asian",
        "black",
        "white",
        "mixed",
        "minority",
        "district",
        "authority",
        "area",
        "region",
        "east of england",
        "norfolk",
        "suffolk",
        "essex",
        "hertfordshire",
        "cambridgeshire",
        "bedfordshire",
        "luton",
        "peterborough",
        "ipswich",
        "colchester",
        "health",
        "mortality",
        "morbidity",
        "disease",
        "screening",
        "lung",
        "breast",
        "prostate",
        "bowel",
        "skin",
        "rate",
        "rank",
    }
)


@st.cache_resource
def get_gemini_engine() -> "GeminiQueryEngine":
    """Return a single, session-cached GeminiQueryEngine instance.

    Using ``@st.cache_resource`` ensures the underlying GenerativeModel is
    constructed exactly once per Streamlit session rather than on every rerun.
    """
    return GeminiQueryEngine()


class GeminiQueryEngine:
    """Interface for querying data using Gemini API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini API with system instructions

        Args:
            api_key: Google Gemini API key (from config if not provided)
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model = None
        self.model_name = Config.GEMINI_MODEL
        self.max_tokens = Config.GEMINI_MAX_TOKENS
        self.temperature = Config.GEMINI_TEMPERATURE
        self.system_instruction_fallback = False

        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Initialize with strict system instruction to enforce guardrails
                try:
                    self.model = genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=SYSTEM_INSTRUCTION,
                    )
                except TypeError:
                    # Fallback for older google-generativeai package versions
                    self.model = genai.GenerativeModel(model_name=self.model_name)
                    self.system_instruction_fallback = True
            except Exception as e:
                print(f"[gemini] Failed to initialize Gemini: {e}", file=sys.stderr)
                st.error(
                    "Failed to initialize Gemini AI. Please check your API key."
                    if not _DEBUG
                    else f"Failed to initialize Gemini: {str(e)}"
                )

    def is_available(self) -> bool:
        """Check if Gemini API is properly configured"""
        return self.model is not None

    def _get_prompt_with_instructions(self, prompt: str) -> str:
        """Prepends system instruction if the installed SDK version doesn't support constructor instructions."""
        if getattr(self, "system_instruction_fallback", False):
            return f"{SYSTEM_INSTRUCTION}\n\n[Context & Task]:\n{prompt}"
        return prompt

    def _make_generation_config(self):
        """Build a GenerationConfig from stored settings.

        Centralises token and temperature configuration so that every
        ``generate_content`` call honours the values set in ``.env``.
        Returns ``None`` gracefully when the SDK version is too old.
        """
        if GenerationConfig is None:
            return None
        try:
            return GenerationConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        except Exception:
            return None

    def get_query_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for a query string using models/text-embedding-004."""
        if not self.is_available():
            return []
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query",
            )
            return result.get("embedding", [])
        except Exception as e:
            print(f"[gemini] Error generating embedding: {e}", file=sys.stderr)
            if not _DEBUG:
                st.error("Error generating query embedding.")
            else:
                st.error(f"Error generating embedding: {e}")
            return []

    def is_query_in_scope(self, query: str, history_context: str = "") -> bool:
        """
        Check if the query is in-scope for the public health dashboard.

        A fast local keyword pre-filter is run first.  If it matches, the
        query is immediately accepted without spending an API call.  Only
        ambiguous queries (no keyword match) are sent to Gemini for a more
        nuanced classification.
        """
        # --- Fast local pre-filter (zero latency, zero cost) ---
        query_lower = query.lower()
        if any(kw in query_lower for kw in _SCOPE_KEYWORDS):
            return True

        # --- Ambiguous query: ask Gemini to classify ---
        if not self.is_available():
            return True  # Fallback: don't block queries when API is down

        prompt = f"""
        You are a scope classifier for a public health dashboard.
        Is the following user question related to public health, cancer trends, deprivation, demographics, or geographic authorities in the East of England?
        
        Consider the previous conversation context if relevant to understand the user's focus (e.g. if the user says "what about its cancer rate?", "its" refers to the previously mentioned district).
        
        Previous Conversation:
        {history_context}
        
        Answer ONLY with 'yes' or 'no'. Do not include explanations or punctuation.
        
        Question: "{query}"
        """
        try:
            response = self.model.generate_content(
                self._get_prompt_with_instructions(prompt),
                generation_config=self._make_generation_config(),
            )
            ans = response.text.strip().lower()
            return "yes" in ans
        except Exception:
            return True  # Fallback to True in case of API issues

    def answer_lookup_query(
        self, query: str, district_profiles_json: str, history_context: str = ""
    ) -> str:
        """
        Directly answer a lookup or comparison query using the cached district profiles context.
        """
        if not self.is_available():
            return "Gemini API is currently unavailable."

        prompt = f"""
        Below is the pre-compiled, cached JSON context containing demographics, deprivation ranks, 
        and cancer incidence rates for the 45 districts in the East of England.
        Use this data directly to answer the user's question.
        
        Consider the previous conversation context to resolve pronouns like "its", "their", "that area", or follow-up requests:
        {history_context}
        
        District Summary Profiles Context:
        {district_profiles_json}
        
        User Question: "{query}"
        
        Rules:
        1. Base your answer strictly on the provided JSON data.
        2. Do not use external database knowledge. If a district or value is missing, say so.
        3. Be direct, concise, and professional. Reference specific numbers and percentages.
        """
        try:
            response = self.model.generate_content(
                self._get_prompt_with_instructions(prompt),
                generation_config=self._make_generation_config(),
            )
            return response.text
        except Exception as e:
            return f"Error querying Gemini: {e}"

    def generate_pandas_code(
        self, query: str, schemas: str, history_context: str = ""
    ) -> str:
        """Prompt Gemini to generate a single executable Python/Pandas expression."""
        if not self.is_available():
            return ""

        prompt = f"""
        You are a python data analyst expert. Write a SINGLE executable block of Python code using Pandas that answers the user's question.
        
        The environment has the following DataFrames loaded:
        - `df_cancer`: Overall cancer incidence rates by district
        - `df_top5`: Top 5 cancers by area and age group
        - `df_population`: Population demographics by ethnicity
        - `df_deprivation`: Index of Multiple Deprivation (IoD 2025)
        
        Schemas:
        {schemas}
        
        Consider the previous conversation context to resolve pronouns or follow-up questions:
        {history_context}
        
        User Question: "{query}"
        
        RULES:
        1. Respond ONLY with the executable Python code block.
        2. Do NOT write explanations.
        3. Do NOT import libraries (pandas and numpy are already imported as `pd` and `np`).
        4. Make sure to clean columns if necessary (e.g. converting rate strings to numbers).
        5. Store the final result in a variable named `result`.
        6. Return the code inside python markdown tags (```python ... ```).
        7. If the user's request is a simple lookup or question that can be answered directly using the cached District Summary Profiles, output the string `USE_PROFILES`. Otherwise, generate the Pandas code.
        """
        try:
            response = self.model.generate_content(
                self._get_prompt_with_instructions(prompt),
                generation_config=self._make_generation_config(),
            )
            return response.text
        except Exception as e:
            return f"Error: {e}"

    def execute_pandas_code(
        self, code: str, context_dfs: dict[str, pd.DataFrame]
    ) -> dict[str, Any]:
        """
        Clean, validate, and execute Python/Pandas code in a restricted scope.
        """
        # Clean markdown wrappers
        clean_code = code.replace("```python", "").replace("```", "").strip()

        # Clean harmless imports that are commonly generated by the LLM
        clean_code = re.sub(
            r"^\s*import\s+pandas(\s+as\s+pd)?\s*$", "", clean_code, flags=re.MULTILINE
        )
        clean_code = re.sub(
            r"^\s*import\s+numpy(\s+as\s+np)?\s*$", "", clean_code, flags=re.MULTILINE
        )

        # Strict validation check for safety keywords
        blocked_words = [
            "import",
            "os",
            "sys",
            "subprocess",
            "open",
            "write",
            "read",
            "__import__",
            "builtins",
            "shutil",
            "socket",
            "urllib",
            "requests",
            "getattr",
            "setattr",
            "eval",
            "exec",
            "globals",
            "locals",
        ]

        # Check tokens rather than substrings where possible to avoid false positives (like 'read_csv' in comments)
        tokens = re.findall(r"\b\w+\b", clean_code)
        for token in tokens:
            if token in blocked_words:
                return {
                    "status": "error",
                    "error": f"Security Violation: Use of forbidden keyword '{token}' is blocked.",
                    "code": clean_code,
                }

        # Set up execution sandbox — deep-copy each DataFrame so that any
        # in-place mutations by LLM-generated code cannot escape the sandbox
        # and corrupt the caller's cached DataFrames.
        # __builtins__ is explicitly set to an empty dict to prevent generated
        # code from accessing Python's full builtin namespace (open, __import__,
        # compile, breakpoint, etc.).  Only pd and np are exposed.
        sandbox_globals = {
            "__builtins__": {},
            "pd": pd,
            "np": np,
            "df_cancer": context_dfs.get(
                "Cancer Incidence (Overall)", pd.DataFrame()
            ).copy(),
            "df_top5": context_dfs.get(
                "Cancer Incidence (Top 5 by Area)", pd.DataFrame()
            ).copy(),
            "df_population": context_dfs.get(
                "Population by Ethnicity", pd.DataFrame()
            ).copy(),
            "df_deprivation": context_dfs.get(
                "Index of Multiple Deprivation 2025", pd.DataFrame()
            ).copy(),
        }
        sandbox_locals = {}

        try:
            # Execute python snippet
            exec(clean_code, sandbox_globals, sandbox_locals)
            result = sandbox_locals.get("result")
            if result is None:
                return {
                    "status": "error",
                    "error": "The execution completed, but the variable 'result' was not defined in the code.",
                    "code": clean_code,
                }
            # Return a copy if result is a DataFrame/Series so the caller's
            # cached data cannot be mutated through a shared reference.
            if isinstance(result, (pd.DataFrame, pd.Series)):
                result = result.copy()
            return {"status": "success", "result": result, "code": clean_code}
        except Exception as e:
            return {"status": "error", "error": str(e), "code": clean_code}

    def explain_results(
        self, query: str, results_summary: str, history_context: str = ""
    ) -> str:
        """Explain the execution result in natural language."""
        if not self.is_available():
            return "Gemini API is currently unavailable."

        prompt = f"""
        You are a public health analyst explaining calculations to an audience.
        Explain the local calculation results in a concise, natural language format.
        
        Consider the previous conversation history if relevant to maintain dialogue flow:
        {history_context}
        
        User Question: "{query}"
        Calculation Output:
        {results_summary}
        
        Keep your answer focused on the question. Do not include coding details or python code.
        """
        try:
            response = self.model.generate_content(
                self._get_prompt_with_instructions(prompt),
                generation_config=self._make_generation_config(),
            )
            return response.text
        except Exception as e:
            return f"Error explaining result: {e}"

    def generate_visualization_insight(self, prompt_data: str, context_key: str) -> str:
        """
        Generate a concise 2-3 sentence insight interpreting a visualization
        based on the user's active filters and data summary.
        """
        if not self.is_available():
            return "Gemini API is currently unavailable."

        # Fetch relevant approved past examples for few-shot learning
        from utils.insights_logger import get_relevant_insights

        examples = get_relevant_insights(context_key, limit=2)

        examples_str = ""
        if examples:
            examples_str = "\nHere are examples of high-quality, approved interpretations for similar analyses. Mimic their style, tone, and level of detail:\n"
            for i, ex in enumerate(examples, 1):
                examples_str += f"Example {i}:\n- Data Profile: {ex.get('data_summary_str', '')[:300]}\n- Approved Insight: {ex.get('insight', '')}\n\n"

        prompt = f"""
        You are a senior public health analyst. Given the following subset of district-level data for the East of England:
        
        {prompt_data}
        {examples_str}
        Provide a concise, professional 2-3 sentence interpretation of this visualization.
        Explain what the data means, highlight notable patterns or variances (e.g., max/min), and relate it to deprivation, health, or cancer where appropriate.
        Do not repeat introductory phrases like "Based on the provided data" or "This chart shows". Start directly with the insights.
        """
        try:
            response = self.model.generate_content(
                self._get_prompt_with_instructions(prompt),
                generation_config=self._make_generation_config(),
            )
            return response.text
        except Exception as e:
            return f"Error generating insight: {e}"


@st.cache_data(show_spinner=False)
def _get_cached_insight(
    data_str: str,
    context_description: str,
    context_key: str,
    _approved_version: int = 0,
) -> str:
    """Cached wrapper to query the engine and prevent duplicate API billing.

    ``_approved_version`` is incremented each time a user approves an insight,
    which invalidates the Streamlit cache so the next call picks up the newly
    saved few-shot examples from ``approved_insights.jsonl``.

    The engine is intentionally NOT passed as an argument — Streamlit cannot
    hash arbitrary Python objects reliably and doing so would silently break
    cache invalidation.  Instead we retrieve the session-cached singleton via
    ``get_gemini_engine()`` which is guaranteed to be consistent.
    """
    prompt_data = (
        f"Context: {context_description}\n\nData Table (CSV format):\n{data_str}"
    )
    return get_gemini_engine().generate_visualization_insight(prompt_data, context_key)


def render_ai_insights(
    df_summary: pd.DataFrame, context_description: str, key_suffix: str
):
    """
    Renders a unified, styled Streamlit component that generates and displays
    Gemini AI insights for a given dataframe slice and context.
    """
    # Use the session-cached engine singleton — avoids re-initialising the
    # GenerativeModel on every Streamlit rerun.
    engine = get_gemini_engine()

    if not engine.is_available():
        return

    try:
        # Convert dataframe to a compact CSV string representation
        data_str = df_summary.head(30).to_csv(index=True)
    except Exception:
        data_str = ""

    # Generate a stable hash based on active data and context to prevent stale insight leakage
    hash_input = f"{data_str}_{context_description}"
    hash_val = hashlib.md5(hash_input.encode("utf-8")).hexdigest()
    state_key = f"ai_insight_{key_suffix}_{hash_val}"

    if st.button("✨ Generate insight", key=f"btn_ai_insight_{key_suffix}"):
        with st.spinner("Analyzing visualization data..."):
            try:
                # Pass the current approval version so the cache is
                # properly invalidated whenever a new insight is approved.
                approved_ver = st.session_state.get("approved_insights_version", 0)
                insight = _get_cached_insight(
                    data_str,
                    context_description,
                    key_suffix,
                    _approved_version=approved_ver,
                )
                st.session_state[state_key] = insight
            except Exception as e:
                print(f"[gemini] Failed to generate insight: {e}", file=sys.stderr)
                st.error(
                    "Failed to generate insight. Please try again."
                    if not _DEBUG
                    else f"Failed to generate insight: {e}"
                )

    # Display the insight if it exists in session state for the current data slice
    if state_key in st.session_state:
        # Escape AI-generated text before injecting into the raw HTML block to
        # prevent CSS/HTML injection from unexpected model output.
        safe_insight = html.escape(st.session_state[state_key])
        st.markdown(
            f"""
            <div style="
                background-color: #F8FAFC;
                border-left: 4px solid #6941C6;
                padding: 12px 16px;
                border-radius: 4px;
                font-family: 'Inter', sans-serif;
                color: #1E293B;
                margin-top: 10px;
                margin-bottom: 5px;
            ">
                <strong>Research Assistant Insight:</strong><br>
                {safe_insight}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Approve insight mechanism
        approved_state_key = f"insight_approved_{key_suffix}_{hash_val}"
        is_approved = st.session_state.get(approved_state_key, False)

        col_feedback1, col_feedback2 = st.columns([1, 4])
        with col_feedback1:
            if st.button(
                "👍 Approve insight" if not is_approved else "✅ Insight cached",
                key=f"btn_approve_{key_suffix}_{hash_val}",
                disabled=is_approved,
            ):
                from utils.insights_logger import save_approved_insight

                save_approved_insight(
                    context_key=key_suffix,
                    data_summary_str=data_str,
                    insight=st.session_state[state_key],
                )
                st.session_state[approved_state_key] = True
                # Bump the version counter so _get_cached_insight's Streamlit
                # cache is invalidated and future calls pick up the new
                # approved example for few-shot prompting.
                st.session_state["approved_insights_version"] = (
                    st.session_state.get("approved_insights_version", 0) + 1
                )
                st.toast("Insight saved to cache for continuous learning!")
                st.rerun()
