import pandas as pd
import numpy as np
import streamlit as st
import geopandas as gpd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

REVERSE_CANCER_MAPPING = {
    "Bladder": "bladder",
    "Blood cancer": "blood cancer",
    "Bowel": "bowel",
    "Brain": "brain",
    "Breast": "breast",
    "Head and neck": "head and neck",
    "Kidney": "kidney",
    "Liver and biliary tract": "liver and biliary tract",
    "Lung": "lung",
    "Ovary": "ovary",
    "Pancreas": "pancreas",
    "Prostate": "prostate",
    "Skin cancer": "skin",
    "Uterus": "uterus"
}

@st.cache_data
def load_cancer_raw_data() -> pd.DataFrame:
    """Load the raw cancer_2018_2022.csv dataset."""
    csv_path = DATA_DIR / "cancer_2018_2022.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)

@st.cache_data
def get_cancer_overall_df(year_filter: str or int = "all") -> pd.DataFrame:
    """
    Pivot and aggregate the cancer data to produce a district-level DataFrame
    with overall and specific cancer metrics.
    
    Includes crude rates (per 100k) and 95% Poisson confidence intervals.
    """
    df = load_cancer_raw_data()
    if df.empty:
        return pd.DataFrame()
        
    gdf_path = DATA_DIR / "base_gdf_1.geojson"
    if not gdf_path.exists():
        return pd.DataFrame()
    df_dist = pd.DataFrame(gpd.read_file(str(gdf_path)).drop(columns="geometry"))
    
    # Filter by year if specified
    if year_filter != "all":
        df_filtered = df[df["Year"] == int(year_filter)].copy()
        num_years = 1
    else:
        df_filtered = df.copy()
        num_years = 5
        
    # Pivot to get counts of each cancer type by fid
    pivot_df = df_filtered.groupby(["fid", "Cancer Type"])["Total Incidence"].sum().unstack(fill_value=0)
    pivot_df = pivot_df.rename(columns=REVERSE_CANCER_MAPPING)
    
    # Ensure all cancer columns are present
    for c in REVERSE_CANCER_MAPPING.values():
        if c not in pivot_df.columns:
            pivot_df[c] = 0
            
    # Calculate raw total count (sum of all cancers for CI)
    raw_total_count = pivot_df.sum(axis=1)
    
    # Calculate counts (average per year if aggregated)
    if num_years > 1:
        counts_df = pivot_df / num_years
        total_incidence = raw_total_count / num_years
    else:
        counts_df = pivot_df.copy()
        total_incidence = raw_total_count.copy()
        
    # Join with district info (population, names)
    df_dist_key = df_dist[["fid", "District Code", "District Name", "total_population"]].set_index("fid")
    result_df = counts_df.join(df_dist_key, how="inner")
    
    # Calculate rates (per 100k) and keep counts in separate columns
    for c in REVERSE_CANCER_MAPPING.values():
        # Store counts in count_ columns
        result_df[f"count_{c}"] = result_df[c]
        # Store rates in standard columns
        result_df[c] = (result_df[c] / result_df["total_population"]) * 100000
        
    result_df["Total_incidence"] = total_incidence
    result_df["Rate"] = (total_incidence / result_df["total_population"]) * 100000
    
    # 95% Poisson confidence interval
    margin = 1.96 * np.sqrt(raw_total_count)
    lci_raw = np.maximum(0, raw_total_count - margin)
    uci_raw = raw_total_count + margin
    
    result_df["95% lower confidence interval"] = (lci_raw / (num_years * result_df["total_population"])) * 100000
    result_df["95% upper confidence interval"] = (uci_raw / (num_years * result_df["total_population"])) * 100000
    
    # Re-add harmonised name/code columns
    result_df["District Name"] = result_df["District Name"]
    result_df["District Code"] = result_df["District Code"]
    
    result_df = result_df.reset_index()
    result_df["fid"] = result_df["fid"].astype(str).str.strip()
    return result_df

@st.cache_data
def get_cancer_top5_df(year_filter: str or int = "all") -> pd.DataFrame:
    """
    Aggregate the age-band counts grouped by district and cancer type.
    """
    df = load_cancer_raw_data()
    if df.empty:
        return pd.DataFrame()
        
    # Filter by year if specified
    if year_filter != "all":
        df_filtered = df[df["Year"] == int(year_filter)].copy()
        num_years = 1
    else:
        df_filtered = df.copy()
        num_years = 5
        
    age_cols = [
        "Age 00 to 24",
        "Age 25 to 49",
        "Age 50 to 59",
        "Age 60 to 69",
        "Age 70 to 79",
        "Age 80 and over",
        "Total Incidence"
    ]
    
    # Group by district and cancer type
    grouped = df_filtered.groupby(["fid", "Geography Name", "Cancer Type"])[age_cols].sum().reset_index()
    
    # Average counts if aggregated
    if num_years > 1:
        for c in age_cols:
            grouped[c] = grouped[c] / num_years
            
    # Rename columns for compatibility
    grouped = grouped.rename(columns={
        "Total Incidence": "All ages",
        "Geography Name": "District Name"
    })
    
    # Normalize fid
    grouped["fid"] = grouped["fid"].astype(str).str.strip()
    
    return grouped
