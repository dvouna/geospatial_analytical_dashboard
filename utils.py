"""
Utility Functions Module
Helper functions for the application
"""

import streamlit as st
import pandas as pd
from typing import List, Tuple
import io


def export_dataframe_to_csv(df: pd.DataFrame, filename: str = "data_export.csv") -> bytes:
    """
    Export DataFrame to CSV bytes
    
    Args:
        df: pandas DataFrame
        filename: Name for the export file
        
    Returns:
        CSV file as bytes
    """
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode()


def export_dataframe_to_excel(df: pd.DataFrame, filename: str = "data_export.xlsx") -> bytes:
    """
    Export DataFrame to Excel bytes
    
    Args:
        df: pandas DataFrame
        filename: Name for the export file
        
    Returns:
        Excel file as bytes
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


def filter_dataframe(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Apply multiple filters to a DataFrame
    
    Args:
        df: pandas DataFrame
        filters: Dictionary of {column: [values]} to filter
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    for column, values in filters.items():
        if column in filtered_df.columns and values:
            filtered_df = filtered_df[filtered_df[column].isin(values)]
    
    return filtered_df


def get_column_stats(df: pd.DataFrame, column: str) -> dict:
    """
    Get statistics for a specific column
    
    Args:
        df: pandas DataFrame
        column: Column name
        
    Returns:
        Dictionary with column statistics
    """
    if column not in df.columns:
        return {}
    
    col_data = df[column]
    
    if col_data.dtype in ['int64', 'float64']:
        return {
            'count': col_data.count(),
            'mean': col_data.mean(),
            'median': col_data.median(),
            'std': col_data.std(),
            'min': col_data.min(),
            'max': col_data.max(),
            'missing': col_data.isnull().sum()
        }
    else:
        return {
            'count': col_data.count(),
            'unique': col_data.nunique(),
            'missing': col_data.isnull().sum(),
            'mode': col_data.mode()[0] if not col_data.mode().empty else None
        }


def format_large_number(num: float, decimals: int = 2) -> str:
    """
    Format large numbers with K, M, B suffixes
    
    Args:
        num: Number to format
        decimals: Number of decimal places
        
    Returns:
        Formatted string
    """
    for unit in ['', 'K', 'M', 'B']:
        if abs(num) < 1000.0:
            return f"{num:.{decimals}f}{unit}"
        num /= 1000.0
    return f"{num:.{decimals}f}T"


def create_download_button(label: str, data: bytes, file_name: str, file_type: str):
    """
    Create a Streamlit download button
    
    Args:
        label: Button label
        data: File data (bytes)
        file_name: Name for downloaded file
        file_type: MIME type (e.g., 'text/csv')
    """
    st.download_button(
        label=label,
        data=data,
        file_name=file_name,
        mime=file_type
    )
