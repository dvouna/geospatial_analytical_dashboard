"""
District Profile Generator for the FLC26 Dashboard.
Consolidates demographics, deprivation, and cancer incidence datasets into
compact, structured district-level JSON profiles for token-efficient grounding.
"""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd
from typing import Any


@st.cache_data(show_spinner=False)
def generate_district_profiles(
    df_cancer: pd.DataFrame, df_imd: pd.DataFrame, df_pop: pd.DataFrame
) -> str:
    """
    Compile a structured JSON string of summary profiles for all districts.

    Combines population demographics, deprivation subdomains, and cancer
    incidence datasets on their official ONS District Codes.
    """
    if df_cancer.empty and df_imd.empty and df_pop.empty:
        return "{}"

    # 1. Clean Deprivation Data
    imd_code_col = "Local Authority District code (2024)"
    imd_name_col = "Local Authority District name (2024)"
    imd_rank_col = "Index of Multiple Deprivation (IMD) Rank"

    imd_ranks = [
        "Income Rank",
        "Employment Rank",
        "Education Skills and Training Rank",
        "Health Deprivation and Disability Rank",
        "Crime Rank",
        "Barriers to Housing and Services Rank",
        "Living Environment Rank",
    ]

    df_imd_clean = pd.DataFrame()
    if not df_imd.empty and imd_code_col in df_imd.columns:
        cols_to_keep = [imd_code_col, imd_name_col, imd_rank_col] + [
            c for c in imd_ranks if c in df_imd.columns
        ]
        df_imd_clean = df_imd[cols_to_keep].dropna(subset=[imd_code_col]).copy()
        df_imd_clean[imd_code_col] = df_imd_clean[imd_code_col].astype(str).str.strip()

    # 2. Clean Cancer Data
    cancer_code_col = "Geography code"
    cancer_rate_col = "Rate"
    cancer_inc_col = "Total_incidence"
    cancer_types = ["breast", "lung", "bowel", "prostate", "skin"]

    df_cancer_clean = pd.DataFrame()
    if not df_cancer.empty and cancer_code_col in df_cancer.columns:
        cols_to_keep = [cancer_code_col, cancer_rate_col, cancer_inc_col] + [
            c for c in cancer_types if c in df_cancer.columns
        ]
        df_cancer_clean = (
            df_cancer[cols_to_keep].dropna(subset=[cancer_code_col]).copy()
        )
        df_cancer_clean[cancer_code_col] = (
            df_cancer_clean[cancer_code_col].astype(str).str.strip()
        )

        # Clean numeric cancer rates
        for col in [cancer_rate_col, cancer_inc_col] + cancer_types:
            if col in df_cancer_clean.columns:
                df_cancer_clean[col] = pd.to_numeric(
                    df_cancer_clean[col].astype(str).str.replace(",", "").str.strip(),
                    errors="coerce",
                )

    # 3. Clean Population Data
    pop_code_col = "LAD24CD"
    pop_total_col = next(
        (
            c
            for c in ["Total Population", "Total Sum", "total_population"]
            if c in df_pop.columns
        ),
        None,
    )
    pop_ethnicities = {
        "White": "Total - All White Groups",
        "Asian": "Total - All Asian Groups",
        "Black": "Total - All Black Groups",
        "Mixed": "Total - All Mixed Groups",
        "Others": "Total - Other Ethnic Groups",
    }

    df_pop_clean = pd.DataFrame()
    if not df_pop.empty and pop_code_col in df_pop.columns:
        cols_to_keep = [pop_code_col]
        if pop_total_col:
            cols_to_keep.append(pop_total_col)
        cols_to_keep.extend(
            [v for v in pop_ethnicities.values() if v in df_pop.columns]
        )

        df_pop_clean = df_pop[cols_to_keep].dropna(subset=[pop_code_col]).copy()
        df_pop_clean[pop_code_col] = df_pop_clean[pop_code_col].astype(str).str.strip()

        # Clean numeric population counts
        num_cols = [c for c in df_pop_clean.columns if c != pop_code_col]
        for col in num_cols:
            df_pop_clean[col] = pd.to_numeric(
                df_pop_clean[col].astype(str).str.replace(",", "").str.strip(),
                errors="coerce",
            )

    # 4. Perform Sequential Joins on District Codes
    merged = pd.DataFrame()
    if not df_imd_clean.empty:
        merged = df_imd_clean.copy()
        join_col = imd_code_col
    elif not df_cancer_clean.empty:
        merged = df_cancer_clean.copy()
        join_col = cancer_code_col
    elif not df_pop_clean.empty:
        merged = df_pop_clean.copy()
        join_col = pop_code_col
    else:
        return "{}"

    if not df_cancer_clean.empty and join_col != cancer_code_col:
        merged = pd.merge(
            merged,
            df_cancer_clean,
            left_on=join_col,
            right_on=cancer_code_col,
            how="outer",
        )
        merged[join_col] = merged[join_col].fillna(merged[cancer_code_col])
        merged.drop(columns=[cancer_code_col], errors="ignore")

    if not df_pop_clean.empty and join_col != pop_code_col:
        merged = pd.merge(
            merged, df_pop_clean, left_on=join_col, right_on=pop_code_col, how="outer"
        )
        merged[join_col] = merged[join_col].fillna(merged[pop_code_col])
        merged.drop(columns=[pop_code_col], errors="ignore")

    # Clean name reference
    name_col = next(
        (
            c
            for c in [imd_name_col, "Geography name ", "Geography name"]
            if c in merged.columns
        ),
        None,
    )

    # 5. Build structured profiles dictionary
    profiles: dict[str, dict[str, Any]] = {}

    for _, row in merged.iterrows():
        district_name = (
            str(row.get(name_col)) if name_col and pd.notna(row.get(name_col)) else None
        )
        if not district_name or district_name == "nan" or district_name.strip() == "":
            continue

        district_code = str(row.get(join_col))

        # Demographic summary
        pop_total = row.get(pop_total_col)
        pop_data = {}
        if pd.notna(pop_total):
            pop_data["Total"] = int(pop_total)
            ethnic_shares = {}
            for label, col_name in pop_ethnicities.items():
                val = row.get(col_name)
                if pd.notna(val) and pop_total > 0:
                    ethnic_shares[label] = f"{(val / pop_total * 100):.1f}%"
            if ethnic_shares:
                pop_data["Ethnic_Shares"] = ethnic_shares

        # Deprivation summary
        imd_val = row.get(imd_rank_col)
        dep_data = {}
        if pd.notna(imd_val):
            dep_data["IMD_Overall_Rank"] = int(imd_val)
            subdomain_ranks = {}
            for col in imd_ranks:
                rank_val = row.get(col)
                if pd.notna(rank_val):
                    short_label = col.replace(" Rank", "")
                    subdomain_ranks[short_label] = int(rank_val)
            if subdomain_ranks:
                dep_data["Subdomain_Ranks"] = subdomain_ranks

        # Cancer summary
        rate_val = row.get(cancer_rate_col)
        cancer_data = {}
        if pd.notna(rate_val):
            cancer_data["Overall_Rate_Per_100k"] = round(float(rate_val), 1)
            inc_val = row.get(cancer_inc_col)
            if pd.notna(inc_val):
                cancer_data["Total_Cases"] = int(inc_val)

            type_rates = {}
            for col in cancer_types:
                val = row.get(col)
                if pd.notna(val):
                    type_rates[col.capitalize()] = round(float(val), 1)
            if type_rates:
                cancer_data["Type_Rates_Per_100k"] = type_rates

        profiles[district_name] = {
            "Code": district_code,
            "Population": pop_data,
            "Deprivation": dep_data,
            "Cancer": cancer_data,
        }

    return json.dumps(profiles, indent=2, ensure_ascii=False)
