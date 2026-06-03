"""
Ethnic Composition Page
Explore ethnicity composition across local authority areas.
"""

import streamlit as st
import pandas as pd
import plotly.express as px


def load_ethnicity_data():
    df = pd.read_csv('data/population_by_ethnicity.csv', header=4)
    df.columns = [str(col).strip().replace('\n', ' ').replace('\xa0', ' ') for col in df.columns]
    if len(df.columns) >= 2:
        df.rename(columns={df.columns[0]: 'Area code', df.columns[1]: 'Area name'}, inplace=True)
    if 'Area name' in df.columns:
        df['Area name'] = df['Area name'].astype(str).str.strip()
    return df


def render_ethnic_composition_page():
    st.title("🌍 Ethnic Composition")
    st.write("Explore the ethnic composition of local areas using Census 2021 data.")

    df = load_ethnicity_data()
    if df is None or df.empty:
        st.error("Unable to load ethnicity composition data.")
        return

    if 'Area name' not in df.columns:
        st.error("The ethnicity dataset does not contain an Area name column.")
        return

    selected_area = st.sidebar.selectbox("Select local area:", df['Area name'].dropna().unique())
    area_data = df[df['Area name'] == selected_area].copy()

    if area_data.empty:
        st.warning("No ethnicity records found for the selected area.")
        return

    area_row = area_data.iloc[0]
    percent_cols = [col for col in df.columns if col.lower().endswith('(percent)')]

    if percent_cols:
        percent_series = area_row[percent_cols].replace('-', pd.NA).dropna().astype(float)
        percent_series.index = [col.replace(' (percent)', '').replace('  ', ' ') for col in percent_series.index]
        percent_series = percent_series.sort_values(ascending=False)

        st.subheader(f"Ethnic composition for {selected_area}")
        fig = px.bar(
            percent_series.head(12).reset_index(),
            x=0,
            y='index',
            orientation='h',
            labels={'index': 'Ethnic group', 0: 'Percent'},
            title='Top ethnic groups by share (%)'
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("Detailed ethnicity numbers and percentages")
        display_cols = ['Area code', 'Area name'] + percent_cols
        display_cols = [col for col in display_cols if col in df.columns]
        st.dataframe(area_data[display_cols].T, use_container_width=True)
    else:
        st.warning("No percentage fields were found in the ethnicity dataset.")

    st.divider()
    st.subheader("Area-level ethnic group overview")
    st.write("Top rows of the ethnicity dataset:")
    st.dataframe(df[['Area code', 'Area name'] + percent_cols].head(10), use_container_width=True)


if __name__ == "__main__":
    render_ethnic_composition_page()
