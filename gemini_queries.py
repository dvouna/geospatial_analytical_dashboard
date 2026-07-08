"""
Gemini Query Engine Module
Handles natural language queries and code generation via Google Gemini API
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import Optional, Any

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

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
                        system_instruction=SYSTEM_INSTRUCTION
                    )
                except TypeError:
                    # Fallback for older google-generativeai package versions
                    self.model = genai.GenerativeModel(model_name=self.model_name)
                    self.system_instruction_fallback = True
            except Exception as e:
                st.error(f"Failed to initialize Gemini: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Gemini API is properly configured"""
        return self.model is not None

    def _get_prompt_with_instructions(self, prompt: str) -> str:
        """Prepends system instruction if the installed SDK version doesn't support constructor instructions."""
        if getattr(self, "system_instruction_fallback", False):
            return f"{SYSTEM_INSTRUCTION}\n\n[Context & Task]:\n{prompt}"
        return prompt

    def get_query_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for a query string using models/text-embedding-004."""
        if not self.is_available():
            return []
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query"
            )
            return result.get("embedding", [])
        except Exception as e:
            st.error(f"Error generating embedding: {e}")
            return []

    def is_query_in_scope(self, query: str, history_context: str = "") -> bool:
        """
        Perform a pre-flight classification query to check if the question
        is in-scope (public health, demographics, cancer, deprivation in the East of England).
        """
        if not self.is_available():
            return True  # Fallback to True if API is unavailable so we don't block queries
        
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
            response = self.model.generate_content(self._get_prompt_with_instructions(prompt))
            ans = response.text.strip().lower()
            return "yes" in ans
        except Exception:
            return True  # Fallback to True in case of API issues

    def answer_lookup_query(self, query: str, district_profiles_json: str, history_context: str = "") -> str:
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
            response = self.model.generate_content(self._get_prompt_with_instructions(prompt))
            return response.text
        except Exception as e:
            return f"Error querying Gemini: {e}"

    def generate_pandas_code(self, query: str, schemas: str, history_context: str = "") -> str:
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
            response = self.model.generate_content(self._get_prompt_with_instructions(prompt))
            return response.text
        except Exception as e:
            return f"Error: {e}"

    def execute_pandas_code(self, code: str, context_dfs: dict[str, pd.DataFrame]) -> dict[str, Any]:
        """
        Clean, validate, and execute Python/Pandas code in a restricted scope.
        """
        # Clean markdown wrappers
        clean_code = code.replace("```python", "").replace("```", "").strip()
        
        # Clean harmless imports that are commonly generated by the LLM
        clean_code = re.sub(r'^\s*import\s+pandas(\s+as\s+pd)?\s*$', '', clean_code, flags=re.MULTILINE)
        clean_code = re.sub(r'^\s*import\s+numpy(\s+as\s+np)?\s*$', '', clean_code, flags=re.MULTILINE)
        
        # Strict validation check for safety keywords
        blocked_words = [
            "import", "os", "sys", "subprocess", "open", "write", "read",
            "__import__", "builtins", "shutil", "socket", "urllib", "requests",
            "getattr", "setattr", "eval", "exec", "globals", "locals"
        ]
        
        # Check tokens rather than substrings where possible to avoid false positives (like 'read_csv' in comments)
        tokens = re.findall(r'\b\w+\b', clean_code)
        for token in tokens:
            if token in blocked_words:
                return {
                    "status": "error",
                    "error": f"Security Violation: Use of forbidden keyword '{token}' is blocked.",
                    "code": clean_code
                }
        
        # Set up execution sandbox
        sandbox_globals = {
            "pd": pd,
            "np": np,
            "df_cancer": context_dfs.get("Cancer Incidence (Overall)", pd.DataFrame()),
            "df_top5": context_dfs.get("Cancer Incidence (Top 5 by Area)", pd.DataFrame()),
            "df_population": context_dfs.get("Population by Ethnicity", pd.DataFrame()),
            "df_deprivation": context_dfs.get("Index of Multiple Deprivation 2025", pd.DataFrame()),
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
                    "code": clean_code
                }
            return {
                "status": "success",
                "result": result,
                "code": clean_code
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "code": clean_code
            }

    def explain_results(self, query: str, results_summary: str, history_context: str = "") -> str:
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
            response = self.model.generate_content(self._get_prompt_with_instructions(prompt))
            return response.text
        except Exception as e:
            return f"Error explaining result: {e}"
