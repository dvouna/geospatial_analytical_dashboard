"""
Cancer Statistics Page
Explore cancer incidence and rate data by geography and cancer type.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_csv_file


def render_cancer_statistics_page():
    st.title("🧬 Cancer Statistics")
    st.write("Explore cancer incidence and rate data across health geography levels.")

    st.sidebar.header("📁 Data Source")
    source_options = [
        "data/incidence_icbs.csv",
        "data/Incidence_laua.csv"
    ]
    selected_source = st.sidebar.selectbox("Select dataset:", source_options)
    df = load_csv_file(selected_source)

    if df is None:
        st.info("👆 Select a dataset to view cancer statistics.")
        return

    df.columns = [col.strip() for col in df.columns]
    df['Count'] = pd.to_numeric(df['Count'], errors='coerce')
    if 'Rate' in df.columns:
        df['Rate'] = pd.to_numeric(df['Rate'], errors='coerce')

    geography_types = sorted(df['Geography type'].dropna().unique())
    geography_type = st.sidebar.selectbox("Geography type:", geography_types)
    filtered = df[df['Geography type'] == geography_type]

    st.sidebar.subheader("📊 Filter")
    cancer_types = sorted(filtered['NDRS main'].dropna().unique())
    selected_cancer = st.sidebar.selectbox("Cancer type:", ["All"] + cancer_types)
    if selected_cancer != "All":
        filtered = filtered[filtered['NDRS main'] == selected_cancer]

    if filtered.empty:
        st.warning("No records match the selected filters.")
        return

    st.subheader("Dataset summary")
    st.write(f"**Total records:** {len(filtered)}")
    if 'Geography name' in filtered.columns:
        st.write(f"**Sample geography:** {filtered['Geography name'].dropna().unique()[:5].tolist()}")

    st.divider()

    if 'Count' in filtered.columns:
        counts = filtered.groupby('NDRS main', as_index=False)['Count'].sum()
        fig_count = px.bar(
            counts.sort_values('Count', ascending=False),
            x='NDRS main',
            y='Count',
            title='Total Cancer Count by Type',
            labels={'NDRS main': 'Cancer Type', 'Count': 'Total Count'}
        )
        fig_count.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_count, use_container_width=True)

    if 'Rate' in filtered.columns:
        rates = filtered.groupby('NDRS main', as_index=False)['Rate'].mean()
        fig_rate = px.bar(
            rates.sort_values('Rate', ascending=False),
            x='NDRS main',
            y='Rate',
            title='Average Cancer Rate by Type',
            labels={'NDRS main': 'Cancer Type', 'Rate': 'Rate per 100,000'}
        )
        fig_rate.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_rate, use_container_width=True)

    st.divider()
    st.subheader("Detailed table")
    show_cols = [col for col in ['Year', 'Gender', 'Age at diagnosis', 'Geography type', 'Geography name', 'NDRS main', 'Count', 'Rate'] if col in filtered.columns]
    st.dataframe(filtered[show_cols].head(50), use_container_width=True)

    st.divider()
    st.subheader("Geography and stage breakdown")
    if 'Stage' in filtered.columns:
        stage_counts = filtered['Stage'].fillna('Unknown').value_counts().rename_axis('Stage').reset_index(name='Records')
        st.dataframe(stage_counts, use_container_width=True)


if __name__ == "__main__":
    render_cancer_statistics_page()
