"""
Data Loading and Caching Module
Handles CSV and public dataset loading with Streamlit caching
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
import os
import json
import geopandas as gpd

# Cache data loading for performance
@st.cache_data
def load_csv_file(file_path: str) -> Optional[pd.DataFrame]:
    """
    Load a CSV file with caching
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        pandas DataFrame or None if loading fails
    """
    try:
        df = pd.read_csv(file_path)
        st.success(f"✅ Loaded {len(df)} rows from {Path(file_path).name}")
        return df
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        return None


@st.cache_data
def load_geojson_file(file_path: str) -> Optional[gpd.GeoDataFrame]:
    """
    Load a GeoJSON file with caching
    
    Args:
        file_path: Path to GeoJSON file
        
    Returns:
        GeoDataFrame or None if loading fails
    """
    try:
        gdf = gpd.read_file(file_path)
        st.success(f"✅ Loaded {len(gdf)} features from {Path(file_path).name}")
        return gdf
    except Exception as e:
        st.error(f"❌ Error loading GeoJSON file: {str(e)}")
        return None


@st.cache_data
def load_sample_dataset(dataset_name: str) -> Optional[pd.DataFrame]:
    """
    Load sample datasets for demonstration
    
    Args:
        dataset_name: Name of the sample dataset
        
    Returns:
        pandas DataFrame
    """
    datasets = {
        'sample_sales': generate_sample_sales_data(),
        'sample_locations': generate_sample_locations_data(),
    }
    
    return datasets.get(dataset_name)


def generate_sample_sales_data() -> pd.DataFrame:
    """Generate sample sales data for demo"""
    import random
    import numpy as np
    from datetime import datetime, timedelta
    
    np.random.seed(42)
    dates = [datetime.now() - timedelta(days=x) for x in range(365)]
    
    data = {
        'Date': sorted(dates),
        'Product': np.random.choice(['Product A', 'Product B', 'Product C', 'Product D'], 365),
        'Region': np.random.choice(['North', 'South', 'East', 'West'], 365),
        'Sales': np.random.randint(100, 10000, 365),
        'Quantity': np.random.randint(1, 100, 365),
    }
    
    return pd.DataFrame(data)


def generate_sample_locations_data() -> pd.DataFrame:
    """Generate sample location data with lat/lon for geospatial demo"""
    import random
    import numpy as np
    
    np.random.seed(42)
    
    locations = [
        {'name': 'New York', 'lat': 40.7128, 'lon': -74.0060, 'value': 8000},
        {'name': 'Los Angeles', 'lat': 34.0522, 'lon': -118.2437, 'value': 6000},
        {'name': 'Chicago', 'lat': 41.8781, 'lon': -87.6298, 'value': 5000},
        {'name': 'Houston', 'lat': 29.7604, 'lon': -95.3698, 'value': 4500},
        {'name': 'Phoenix', 'lat': 33.4484, 'lon': -112.0742, 'value': 3500},
        {'name': 'Philadelphia', 'lat': 39.9526, 'lon': -75.1652, 'value': 3000},
        {'name': 'San Antonio', 'lat': 29.4241, 'lon': -98.4936, 'value': 2800},
        {'name': 'San Diego', 'lat': 32.7157, 'lon': -117.1611, 'value': 2600},
        {'name': 'Dallas', 'lat': 32.7767, 'lon': -96.7970, 'value': 2500},
        {'name': 'San Jose', 'lat': 37.3382, 'lon': -121.8863, 'value': 2300},
    ]
    
    return pd.DataFrame(locations)


def get_data_summary(df: pd.DataFrame) -> Dict:
    """
    Generate summary statistics for a dataset
    
    Args:
        df: pandas DataFrame
        
    Returns:
        Dictionary with summary information
    """
    return {
        'rows': len(df),
        'columns': len(df.columns),
        'memory_usage': df.memory_usage(deep=True).sum() / 1024 / 1024,  # MB
        'missing_values': df.isnull().sum().sum(),
        'dtypes': df.dtypes.value_counts().to_dict(),
    }


def validate_geospatial_data(df: pd.DataFrame) -> bool:
    """
    Check if dataset has latitude and longitude columns for geospatial visualization
    
    Args:
        df: pandas DataFrame
        
    Returns:
        True if lat/lon columns exist, False otherwise
    """
    required_cols = ['lat', 'lon', 'latitude', 'longitude']
    df_cols = [col.lower() for col in df.columns]
    
    has_lat = any(col in df_cols for col in ['lat', 'latitude'])
    has_lon = any(col in df_cols for col in ['lon', 'longitude'])
    
    return has_lat and has_lon


def validate_geodataframe(gdf) -> bool:
    """
    Check if object is a valid GeoDataFrame with geometry
    
    Args:
        gdf: GeoDataFrame or object to validate
        
    Returns:
        True if valid GeoDataFrame with geometry, False otherwise
    """
    try:
        return isinstance(gdf, gpd.GeoDataFrame) and 'geometry' in gdf.columns
    except:
        return False


def normalize_geospatial_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize latitude and longitude column names
    
    Args:
        df: pandas DataFrame
        
    Returns:
        DataFrame with standardized 'latitude' and 'longitude' columns
    """
    df_copy = df.copy()
    
    # Rename columns to standard names
    for col in df_copy.columns:
        if col.lower() in ['lat', 'latitude']:
            df_copy.rename(columns={col: 'latitude'}, inplace=True)
        elif col.lower() in ['lon', 'longitude']:
            df_copy.rename(columns={col: 'longitude'}, inplace=True)
    
    return df_copy


def get_available_local_files(data_dir: str = 'data') -> Dict[str, List[str]]:
    """
    Get list of available data files in data directory
    
    Args:
        data_dir: Directory to search for data files
        
    Returns:
        Dictionary with file types as keys and file paths as values
    """
    available_files = {
        'csv': [],
        'geojson': [],
        'json': []
    }
    
    if not os.path.exists(data_dir):
        return available_files
    
    for file in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file)
        if os.path.isfile(file_path):
            if file.endswith('.csv'):
                available_files['csv'].append(file_path)
            elif file.endswith('.geojson'):
                available_files['geojson'].append(file_path)
            elif file.endswith('.json'):
                available_files['json'].append(file_path)
    
    return available_files
