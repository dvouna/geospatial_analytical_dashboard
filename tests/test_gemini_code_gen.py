"""
Unit tests for Gemini Code Gen, District Profiles, Semantic Cache, and Guardrails.
Run with:
    pytest tests/test_gemini_code_gen.py -v
"""

from __future__ import annotations

import json
import pandas as pd
from unittest.mock import patch

from utils.code_cache import SemanticCodeCache
from utils.profile_generator import generate_district_profiles
from gemini_queries import GeminiQueryEngine


# ---------------------------------------------------------------------------
# 1. Semantic Code Cache Tests
# ---------------------------------------------------------------------------

def test_semantic_cache_similarity():
    """Verify that cosine similarity is calculated correctly."""
    cache = SemanticCodeCache(cache_filename="test_cache.json")
    
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0, 3.0]
    # Perfect match
    assert abs(cache._cosine_similarity(vec_a, vec_b) - 1.0) < 1e-6
    
    vec_c = [-1.0, -2.0, -3.0]
    # Opposite direction
    assert abs(cache._cosine_similarity(vec_a, vec_c) - (-1.0)) < 1e-6

    vec_d = [0.0, 0.0, 0.0]
    # Zero vector
    assert cache._cosine_similarity(vec_a, vec_d) == 0.0


def test_semantic_cache_add_and_get(tmp_path):
    """Verify that cache correctly saves, retrieves, and clears code entries."""
    # Patch data_path to use a temp directory
    with patch("utils.code_cache.data_path", return_value=tmp_path):
        cache = SemanticCodeCache(cache_filename="temp_cache.json", threshold=0.90)
        
        query = "What is the average cancer rate?"
        vector = [0.1, 0.2, 0.3, 0.4]
        code = "result = df_cancer['Rate'].mean()"
        
        # Initial check (empty)
        assert cache.get_cached_code(vector) is None
        
        # Add to cache
        cache.add_to_cache(query, vector, code)
        
        # Exact vector lookup
        cached_result = cache.get_cached_code(vector)
        assert cached_result is not None
        assert cached_result[0] == code
        assert abs(cached_result[1] - 1.0) < 1e-6
        
        # Close vector lookup (above threshold)
        close_vector = [0.101, 0.2, 0.3, 0.4]
        cached_result = cache.get_cached_code(close_vector)
        assert cached_result is not None
        assert cached_result[0] == code
        assert cached_result[1] >= 0.90

        # Far vector lookup (below threshold)
        far_vector = [-0.1, -0.2, -0.3, 0.4]
        assert cache.get_cached_code(far_vector) is None
        
        # Clear cache
        cache.clear_cache()
        assert cache.get_cached_code(vector) is None


# ---------------------------------------------------------------------------
# 2. Profile Generator Tests
# ---------------------------------------------------------------------------

def test_profile_generator_merging():
    """Verify profile generator successfully merges datasets on code columns."""
    df_cancer = pd.DataFrame({
        "Geography code": ["E07000001", "E07000002"],
        "Geography name ": ["District Alpha", "District Beta"],
        "Rate": [450.5, 520.1],
        "Total_incidence": [1200, 1500],
        "lung": [45.1, 52.3]
    })
    
    df_imd = pd.DataFrame({
        "Local Authority District code (2024)": ["E07000001", "E07000002"],
        "Local Authority District name (2024)": ["District Alpha", "District Beta"],
        "Index of Multiple Deprivation (IMD) Rank": [120, 85],
        "Income Rank": [115, 90]
    })
    
    df_pop = pd.DataFrame({
        "LAD24CD": ["E07000001", "E07000002"],
        "Total Population": [150000, 180000],
        "Total - All White Groups": [130000, 140000],
        "Total - All Asian Groups": [10000, 25000]
    })
    
    profiles_json = generate_district_profiles(df_cancer, df_imd, df_pop)
    profiles = json.loads(profiles_json)
    
    assert "District Alpha" in profiles
    assert "District Beta" in profiles
    
    alpha = profiles["District Alpha"]
    assert alpha["Code"] == "E07000001"
    assert alpha["Population"]["Total"] == 150000
    assert alpha["Population"]["Ethnic_Shares"]["White"] == "86.7%"
    assert alpha["Population"]["Ethnic_Shares"]["Asian"] == "6.7%"
    assert alpha["Deprivation"]["IMD_Overall_Rank"] == 120
    assert alpha["Cancer"]["Overall_Rate_Per_100k"] == 450.5
    assert alpha["Cancer"]["Type_Rates_Per_100k"]["Lung"] == 45.1


# ---------------------------------------------------------------------------
# 3. Restricted Execution Sandbox Tests
# ---------------------------------------------------------------------------

def test_sandbox_execution_success():
    """Verify that safe Pandas code executes successfully and returns 'result'."""
    engine = GeminiQueryEngine()
    
    df_cancer = pd.DataFrame({"Rate": [10.0, 20.0, 30.0]})
    context_dfs = {"Cancer Incidence (Overall)": df_cancer}
    
    code = """
    result = df_cancer['Rate'].mean()
    """
    
    exec_res = engine.execute_pandas_code(code, context_dfs)
    assert exec_res["status"] == "success"
    assert exec_res["result"] == 20.0


def test_sandbox_execution_no_result():
    """Verify sandbox fails when 'result' variable is not defined in generated code."""
    engine = GeminiQueryEngine()
    context_dfs = {}
    
    code = "val = 10 + 20"
    exec_res = engine.execute_pandas_code(code, context_dfs)
    assert exec_res["status"] == "error"
    assert "result" in exec_res["error"]


def test_sandbox_execution_violation():
    """Verify sandbox successfully blocks forbidden keywords (e.g. import, os)."""
    engine = GeminiQueryEngine()
    context_dfs = {}
    
    # Simple import attempt
    code = "import os; result = 10"
    exec_res = engine.execute_pandas_code(code, context_dfs)
    assert exec_res["status"] == "error"
    assert "Security Violation" in exec_res["error"]

    # Substring bypass check
    code = "result = __import__('os').system('echo hello')"
    exec_res = engine.execute_pandas_code(code, context_dfs)
    assert exec_res["status"] == "error"
    assert "Security Violation" in exec_res["error"]
