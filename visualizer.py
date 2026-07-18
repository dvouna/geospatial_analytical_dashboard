"""
Visualization Utilities Module
Handles chart creation and visualization functions.
All charts apply the shared PLOTLY_LIGHT_LAYOUT for consistent Inter typography,
token-based colours, and transparent backgrounds.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List
import numpy as np

# ── Shared design tokens ──────────────────────────────────────────────────────

# Qualitative palette used across bar, scatter, pie, and treemap charts.
# Matches the FLC26 design system (primary blue + accent purple + 8 supporting hues).
FLC26_QUALITATIVE = [
    "#1F77B4",  # Primary Blue
    "#6941C6",  # Accent Purple
    "#2A9D8F",  # Teal
    "#E76F51",  # Coral
    "#E9C46A",  # Gold
    "#4CC9F0",  # Sky
    "#F4A261",  # Sandy Orange
    "#BC6C25",  # Warm Brown
    "#264653",  # Deep Navy
    "#A8DADC",  # Pale Teal
]

# Shared Plotly layout applied to every chart for consistent typography/colour.
# Charts with transparent paper/plot background inherit the card surface colour.
PLOTLY_LIGHT_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", size=13, color="#334155"),
    title_font=dict(family="Inter, sans-serif", size=16, color="#0F172A"),
    paper_bgcolor="rgba(0,0,0,0)",   # transparent — inherits card background
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=FLC26_QUALITATIVE,
    xaxis=dict(
        gridcolor="#E2E8F0",
        linecolor="#E2E8F0",
        tickfont=dict(size=11, color="#64748B"),
        title_font=dict(size=12, color="#475569"),
    ),
    yaxis=dict(
        gridcolor="#E2E8F0",
        linecolor="#E2E8F0",
        tickfont=dict(size=11, color="#64748B"),
        title_font=dict(size=12, color="#475569"),
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#E2E8F0",
        borderwidth=1,
        font=dict(size=12, color="#334155"),
        orientation="v",
        xanchor="left",
        x=1.02,
        y=1,
        yanchor="top",
    ),
    margin=dict(t=48, b=32, l=16, r=120),
    hoverlabel=dict(
        bgcolor="#0F172A",
        font_color="#F8FAFC",
        font_size=12,
        bordercolor="#0F172A",
    ),
)


# Mobile-optimised layout with scaled typography and margins.
PLOTLY_MOBILE_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", size=10, color="#334155"),
    title_font=dict(family="Inter, sans-serif", size=12, color="#0F172A"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=FLC26_QUALITATIVE,
    xaxis=dict(
        gridcolor="#E2E8F0",
        linecolor="#E2E8F0",
        tickfont=dict(size=9, color="#64748B"),
        title_font=dict(size=9, color="#475569"),
    ),
    yaxis=dict(
        gridcolor="#E2E8F0",
        linecolor="#E2E8F0",
        tickfont=dict(size=9, color="#64748B"),
        title_font=dict(size=9, color="#475569"),
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#E2E8F0",
        borderwidth=1,
        font=dict(size=9, color="#334155"),
        orientation="h",
        yanchor="bottom",
        y=-0.4,
        xanchor="center",
        x=0.5,
    ),
    margin=dict(t=40, b=24, l=8, r=8),
    hoverlabel=dict(
        bgcolor="#0F172A",
        font_color="#F8FAFC",
        font_size=10,
        bordercolor="#0F172A",
    ),
)


def get_plotly_layout() -> dict:
    """Return the mobile-optimized or desktop layout dictionary based on the device type."""
    from utils.device import get_is_mobile
    if get_is_mobile():
        return PLOTLY_MOBILE_LAYOUT
    return PLOTLY_LIGHT_LAYOUT


# ── Chart builder functions ───────────────────────────────────────────────────

def create_line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str = "Line Chart"):
    """Create an interactive line chart with Plotly."""
    fig = px.line(df, x=x_col, y=y_col, title=title, markers=True,
                  color_discrete_sequence=FLC26_QUALITATIVE)
    fig.update_layout(hovermode="x unified", **get_plotly_layout())
    return fig


def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str = "Bar Chart"):
    """Create an interactive bar chart with Plotly."""
    fig = px.bar(df, x=x_col, y=y_col, title=title,
                 color_discrete_sequence=FLC26_QUALITATIVE)
    fig.update_layout(hovermode="x unified", **get_plotly_layout())
    return fig


def create_scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    title: str = "Scatter Plot",
):
    """Create an interactive scatter plot with Plotly."""
    fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title,
                     color_discrete_sequence=FLC26_QUALITATIVE)
    fig.update_layout(hovermode="closest", **get_plotly_layout())
    return fig


def create_histogram(df: pd.DataFrame, col: str, nbins: int = 30, title: str = "Histogram"):
    """Create an interactive histogram with Plotly."""
    fig = px.histogram(df, x=col, nbins=nbins, title=title,
                       color_discrete_sequence=FLC26_QUALITATIVE)
    fig.update_layout(hovermode="x unified", **get_plotly_layout())
    return fig


def create_pie_chart(df: pd.DataFrame, names_col: str, values_col: str, title: str = "Pie Chart"):
    """Create an interactive pie chart with Plotly."""
    fig = px.pie(df, names=names_col, values=values_col, title=title,
                 color_discrete_sequence=FLC26_QUALITATIVE)
    fig.update_layout(**get_plotly_layout())
    return fig


def create_box_plot(
    df: pd.DataFrame,
    y_col: str,
    x_col: Optional[str] = None,
    title: str = "Box Plot",
):
    """Create an interactive box plot with Plotly."""
    fig = px.box(df, y=y_col, x=x_col, title=title,
                 color_discrete_sequence=FLC26_QUALITATIVE)
    fig.update_layout(**get_plotly_layout())
    return fig


def create_heatmap(df: pd.DataFrame, title: str = "Correlation Heatmap"):
    """Create a correlation heatmap using the diverging RdBu_r scale."""
    numeric_df = df.select_dtypes(include=[np.number])
    corr = numeric_df.corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale="RdBu_r",
        zmid=0,
    ))
    layout = dict(**get_plotly_layout())
    layout["height"] = 600
    layout["title"] = title
    fig.update_layout(**layout)
    return fig


def display_summary_statistics(df: pd.DataFrame):
    """Display summary statistics in four metric columns."""
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
    """Get list of numeric columns from DataFrame."""
    return df.select_dtypes(include=[np.number]).columns.tolist()


def get_categorical_columns(df: pd.DataFrame) -> List[str]:
    """Get list of categorical/string columns from DataFrame."""
    return df.select_dtypes(include=["object"]).columns.tolist()

