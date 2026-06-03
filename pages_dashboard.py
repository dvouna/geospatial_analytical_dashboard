"""
Dashboard Page
Interactive data visualization and exploration
"""

import streamlit as st
import pandas as pd
from data_loader import load_csv_file, get_data_summary, validate_geospatial_data
from visualizer import (
    create_line_chart, create_bar_chart, create_scatter_chart,
    create_histogram, create_box_plot, display_summary_statistics,
    get_numeric_columns, get_categorical_columns
)
from utils import export_dataframe_to_csv, filter_dataframe


def render_index_of_multiple_deprivation_page():
    st.title("📍 Index of Multiple Deprivation")
    st.write("Explore local area deprivation metrics, rankings, and decile distributions.")

    st.sidebar.header("📁 Data Source")
    data_source = st.sidebar.radio("Select data source:", ["IMD Dataset", "Upload CSV"])

    if data_source == "IMD Dataset":
        df = load_csv_file('data/imd_all_lsoa_rnd.csv')
    else:
        uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.sidebar.success("✅ File uploaded successfully")
        else:
            df = None

    if df is not None:
        st.subheader("📈 Dataset Overview")
        summary = get_data_summary(df)
        st.metric("Rows", summary['rows'])
        st.metric("Columns", summary['columns'])
        st.metric("Missing values", summary['missing_values'])

        if 'Index of Multiple Deprivation (IMD) Rank' in df.columns:
            rank_col = 'Index of Multiple Deprivation (IMD) Rank'
        else:
            rank_col = next((col for col in df.columns if 'Index of Multiple Deprivation' in col and 'Rank' in col), None)

        if 'Index of Multiple Deprivation (IMD) Decile' in df.columns:
            decile_col = 'Index of Multiple Deprivation (IMD) Decile'
        else:
            decile_col = next((col for col in df.columns if 'Index of Multiple Deprivation' in col and 'Decile' in col), None)

        area_name_col = next((col for col in df.columns if 'LSOA name' in col or 'Local Authority District name' in col), None)

        if rank_col and area_name_col:
            st.subheader("🏅 Most Deprived Areas")
            top_deprived = df.sort_values(rank_col).head(10)
            display_cols = [area_name_col, rank_col]
            if decile_col:
                display_cols.append(decile_col)
            st.dataframe(top_deprived[display_cols], use_container_width=True)

        if decile_col:
            st.subheader("📊 IMD Decile Distribution")
            try:
                decile_series = pd.to_numeric(df[decile_col], errors='coerce').dropna().astype(int)
                chart = pd.DataFrame(decile_series.value_counts().sort_index()).reset_index()
                chart.columns = ["Decile", "Count"]
                st.bar_chart(chart.set_index("Decile"))
            except Exception:
                st.warning("Unable to render IMD decile distribution for this dataset.")

        if get_numeric_columns(df):
            st.divider()
            st.subheader("📉 Visualizations")

            numeric_cols = get_numeric_columns(df)
            categorical_cols = get_categorical_columns(df)

            col1, col2 = st.columns(2)
            with col1:
                st.write("**Select Chart Type:**")
                chart_type = st.radio(
                    "Chart type",
                    ["Line Chart", "Bar Chart", "Scatter Plot", "Histogram", "Box Plot"],
                    label_visibility="collapsed"
                )
            with col2:
                if chart_type == "Histogram":
                    selected_col = st.selectbox("Select numeric column:", numeric_cols, key="imd_hist_col")
                    nbins = st.slider("Number of bins:", 5, 100, 30)
                    fig = create_histogram(df, selected_col, nbins)
                elif chart_type == "Box Plot":
                    selected_col = st.selectbox("Select numeric column:", numeric_cols, key="imd_box_col")
                    group_col = st.selectbox("Group by (optional):", ["None"] + categorical_cols, key="imd_box_group")
                    if group_col != "None":
                        fig = create_box_plot(df, selected_col, group_col)
                    else:
                        fig = create_box_plot(df, selected_col)
                else:
                    col_x = st.selectbox("X-axis:", numeric_cols, key="imd_x_col")
                    col_y = st.selectbox("Y-axis:", numeric_cols, index=1 if len(numeric_cols) > 1 else 0, key="imd_y_col")
                    if chart_type == "Line Chart":
                        fig = create_line_chart(df, col_x, col_y)
                    elif chart_type == "Bar Chart":
                        fig = create_bar_chart(df, col_x, col_y)
                    elif chart_type == "Scatter Plot":
                        color_col = st.selectbox("Color by (optional):", ["None"] + categorical_cols, key="imd_scatter_color")
                        if color_col != "None":
                            fig = create_scatter_chart(df, col_x, col_y, color_col)
                        else:
                            fig = create_scatter_chart(df, col_x, col_y)
                st.plotly_chart(fig, use_container_width=True)

        if validate_geospatial_data(df):
            st.info("✅ This dataset contains latitude/longitude data for geospatial visualization.")

        st.divider()
        st.subheader("💾 Export Data")
        csv_data = export_dataframe_to_csv(df, "imd_data_export.csv")
        st.download_button(
            label="📥 Download Dataset as CSV",
            data=csv_data,
            file_name="imd_data_export.csv",
            mime="text/csv"
        )
    else:
        st.info("👆 Please select a data source to get started")
