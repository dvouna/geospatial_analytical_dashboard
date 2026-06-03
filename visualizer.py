"""
Visualization Utilities Module
Handles chart creation and visualization functions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List
import numpy as np


def create_line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str = "Line Chart"):
    """Create an interactive line chart with Plotly"""
    fig = px.line(df, x=x_col, y=y_col, title=title, markers=True)
    fig.update_layout(hovermode='x unified')
    return fig


def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str = "Bar Chart"):
    """Create an interactive bar chart with Plotly"""
    fig = px.bar(df, x=x_col, y=y_col, title=title)
    fig.update_layout(hovermode='x unified')
    return fig


def create_scatter_chart(df: pd.DataFrame, x_col: str, y_col: str, color_col: Optional[str] = None, title: str = "Scatter Plot"):
    """Create an interactive scatter plot with Plotly"""
    fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title)
    fig.update_layout(hovermode='closest')
    return fig


def create_histogram(df: pd.DataFrame, col: str, nbins: int = 30, title: str = "Histogram"):
    """Create an interactive histogram with Plotly"""
    fig = px.histogram(df, x=col, nbins=nbins, title=title)
    fig.update_layout(hovermode='x unified')
    return fig


def create_pie_chart(df: pd.DataFrame, names_col: str, values_col: str, title: str = "Pie Chart"):
    """Create an interactive pie chart with Plotly"""
    fig = px.pie(df, names=names_col, values=values_col, title=title)
    return fig


def create_box_plot(df: pd.DataFrame, y_col: str, x_col: Optional[str] = None, title: str = "Box Plot"):
    """Create an interactive box plot with Plotly"""
    fig = px.box(df, y=y_col, x=x_col, title=title)
    return fig


def create_heatmap(df: pd.DataFrame, title: str = "Correlation Heatmap"):
    """Create a correlation heatmap"""
    numeric_df = df.select_dtypes(include=[np.number])
    corr = numeric_df.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale='RdBu',
        zmid=0
    ))
    fig.update_layout(title=title, height=600)
    return fig


def display_summary_statistics(df: pd.DataFrame):
    """Display summary statistics in columns"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Rows", len(df))
    with col2:
        st.metric("Total Columns", len(df.columns))
    with col3:
        missing = df.isnull().sum().sum()
        st.metric("Missing Values", missing)
    with col4:
        memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        st.metric("Memory Usage (MB)", f"{memory_mb:.2f}")


def get_numeric_columns(df: pd.DataFrame) -> List[str]:
    """Get list of numeric columns from DataFrame"""
    return df.select_dtypes(include=[np.number]).columns.tolist()


def get_categorical_columns(df: pd.DataFrame) -> List[str]:
    """Get list of categorical/string columns from DataFrame"""
    return df.select_dtypes(include=['object']).columns.tolist()
