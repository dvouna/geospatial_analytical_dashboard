import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from map_utils import load_overlay_dataframe
from visualizer import create_bar_chart, create_histogram, create_box_plot, display_summary_statistics

DATA_DIR = Path(__file__).parent.parent / "data"

# ── Column definitions ─────────────────────────────────────────────────────────

ETHNIC_SUMS = {
    "White": "White Sum",
    "Asian": "Asian Sum",
    "Black": "Black Sum",
    "Mixed": "Mixed Sum",
    "Others": "Others Sum",
}

SUBGROUP_MAP = {
    "Asian": [
        "Asian, Asian British or Asian Welsh: Bangladeshi\n(number)",
        "Asian, Asian British or Asian Welsh: Chinese\n(number)",
        "Asian, Asian British or Asian Welsh: Indian\n(number)",
        "Asian, Asian British or Asian Welsh: Pakistani\n(number)",
        "Asian, Asian British or Asian Welsh: Other Asian\n(number)",
    ],
    "Black": [
        "Black, Black British, Black Welsh, Caribbean or African: African\n(number)",
        "Black, Black British, Black Welsh, Caribbean or African: Caribbean\n(number)",
        "Black, Black British, Black Welsh, Caribbean or African: Other Black\n(number)",
    ],
    "Mixed": [
        "Mixed or Multiple ethnic groups: White and Asian\n(number)",
        "Mixed or Multiple ethnic groups: White and Black African\n(number)",
        "Mixed or Multiple ethnic groups: White and Black Caribbean\n(number)",
        "Mixed or Multiple ethnic groups: Other Mixed or Multiple ethnic groups\n(number)",
    ],
    "White": [
        "White: English, Welsh, Scottish, Northern Irish or British\n(number)",
        "White: Irish\n(number)",
        "White: Gypsy or Irish Traveller\n(number)",
        "White: Roma\n(number)",
        "White: Other White\n(number)",
    ],
    "Others": [
        "Other ethnic group: Arab\n(number)",
        "Other ethnic group: Any other ethnic group\n(number)",
    ],
}

SUBGROUP_LABELS = {
    "Asian": ["Bangladeshi", "Chinese", "Indian", "Pakistani", "Other Asian"],
    "Black": ["African", "Caribbean", "Other Black"],
    "Mixed": ["White & Asian", "White & Black African", "White & Black Caribbean", "Other Mixed"],
    "White": ["British", "Irish", "Gypsy/Traveller", "Roma", "Other White"],
    "Others": ["Arab", "Any Other"],
}

PALETTE = px.colors.qualitative.Set2


def _clean_numeric(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce"
            )
    return df


def render_population_playground():
    try:
        st.set_page_config(
            page_title="Population Demographics Playground",
            page_icon="👥",
            layout="wide",
        )
    except Exception:
        pass

    st.title("👥 Population Demographics Playground")
    st.write(
        "Analyze and compare ethnic group proportions and sub-group breakdowns "
        "across East of England districts."
    )

    # ── Load data ──────────────────────────────────────────────────────────────
    try:
        df = load_overlay_dataframe(DATA_DIR / "population_detail.csv", index_col="fid")
    except FileNotFoundError:
        st.error("❌ `population_detail.csv` not found in the data directory.")
        return
    except Exception as exc:
        st.error(f"❌ Error loading population data: {exc}")
        return

    # ── Split page layout ──────────────────────────────────────────────────────
    col_main, col_sidebar = st.columns([7, 3])

    with col_sidebar:
        import importlib
        ra_module = importlib.import_module("pages.5_AI_Research_Assistant")
        ra_module.render_research_assistant_widget(key_suffix="pop_playground")

    with col_main:
        display_summary_statistics(df)
        st.divider()

        name_col = next(
            (c for c in ["LAD24NM", "Geography name ", "Geography name"] if c in df.columns), None
        )
        sum_cols = [v for v in ETHNIC_SUMS.values() if v in df.columns]
        all_num_cols = sum_cols + [
            col for cols in SUBGROUP_MAP.values() for col in cols if col in df.columns
        ]
        if "Total Sum" in df.columns:
            all_num_cols.append("Total Sum")
        df = _clean_numeric(df, all_num_cols)

        # ── Tabs ───────────────────────────────────────────────────────────────────
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Single Metric",
            "🗂️ Ethnic Composition",
            "🔬 Sub-Group Breakdown",
            "🌳 Diversity Treemap",
            "📋 Data Table",
        ])

        # ── Tab 1: Original single-metric charts ──────────────────────────────────
        with tab1:
            st.subheader("Explore a Single Ethnic Group Metric")
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                selected_metric = st.selectbox(
                    "Ethnic group:", options=list(ETHNIC_SUMS.keys()),
                    format_func=lambda k: f"{k} ({ETHNIC_SUMS[k]})",
                    key="pop_t1_metric"
                )
                metric_col = ETHNIC_SUMS[selected_metric]
            with c2:
                chart_type = st.radio(
                    "Chart type:", ["Bar Chart", "Histogram", "Box Plot"],
                    horizontal=True, key="pop_t1_chart"
                )
            with c3:
                num_districts = st.slider(
                    "Districts (bar chart):", 5, max(5, len(df)), 15, key="pop_t1_limit"
                )

            sort_order = st.selectbox(
                "Sort:", ["Highest to Lowest", "Lowest to Highest"], key="pop_t1_sort"
            )
            ascending = sort_order == "Lowest to Highest"
            plot_df = df.dropna(subset=[metric_col]).sort_values(by=metric_col, ascending=ascending)

            if chart_type == "Bar Chart":
                bar_df = (plot_df.tail(num_districts) if sort_order == "Highest to Lowest"
                          else plot_df.head(num_districts))
                bar_df = bar_df.sort_values(by=metric_col, ascending=not ascending)
                fig = create_bar_chart(bar_df, x_col=name_col, y_col=metric_col,
                                       title=f"Top {num_districts} districts — {metric_col}")
                st.plotly_chart(fig, use_container_width=True)
            elif chart_type == "Histogram":
                fig = create_histogram(plot_df, col=metric_col,
                                       title=f"Distribution of {metric_col} across all districts")
                st.plotly_chart(fig, use_container_width=True)
            elif chart_type == "Box Plot":
                fig = create_box_plot(plot_df, y_col=metric_col,
                                      title=f"Box Plot: {metric_col} Spread")
                st.plotly_chart(fig, use_container_width=True)

        # ── Tab 2: Stacked composition bar ────────────────────────────────────────
        with tab2:
            st.subheader("Ethnic Composition by District")
            st.info(
                "Each bar shows the proportional ethnic makeup of a district. "
                "Toggle between proportions (%) and absolute counts."
            )

            view_mode = st.radio(
                "View mode:", ["Proportional (%)", "Absolute (count)"],
                horizontal=True, key="pop_t2_mode"
            )
            sort_by = st.selectbox(
                "Sort districts by:", ["White", "Asian", "Black", "Mixed", "Others", "Total Population"],
                key="pop_t2_sort"
            )

            comp_df = df[[name_col] + sum_cols].dropna().copy() if name_col else df[sum_cols].dropna().copy()
            if "Total Sum" in df.columns:
                comp_df["Total Sum"] = df.loc[comp_df.index, "Total Sum"]

            sort_col = ETHNIC_SUMS.get(sort_by, "Total Sum") if sort_by != "Total Population" else "Total Sum"
            if sort_col in comp_df.columns:
                comp_df = comp_df.sort_values(sort_col, ascending=False)

            if view_mode == "Proportional (%)":
                for col in sum_cols:
                    total = comp_df[sum_cols].sum(axis=1).replace(0, float("nan"))
                    comp_df[col] = comp_df[col] / total * 100
                y_label = "Population Share (%)"
                barmode = "stack"
            else:
                y_label = "Population Count"
                barmode = "stack"

            x_vals = comp_df[name_col].tolist() if name_col else comp_df.index.tolist()
            fig = go.Figure()
            for group_name, col in ETHNIC_SUMS.items():
                if col in comp_df.columns:
                    fig.add_trace(go.Bar(
                        name=group_name,
                        x=x_vals,
                        y=comp_df[col].tolist(),
                    ))
            fig.update_layout(
                barmode=barmode,
                title="Ethnic Composition by District",
                xaxis_title="District",
                yaxis_title=y_label,
                legend_title="Ethnic Group",
                xaxis_tickangle=-45,
                height=520,
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Tab 3: Sub-group breakdown ─────────────────────────────────────────────
        with tab3:
            st.subheader("Sub-Group Breakdown Within an Ethnic Group")
            st.info(
                "Select a broad ethnic group to see how its sub-categories vary across districts. "
                "'Asian Sum' hides very different sub-populations — Luton vs Cambridge, for example."
            )

            selected_group = st.selectbox(
                "Select ethnic group:", list(SUBGROUP_MAP.keys()), key="pop_t3_group"
            )
            sub_cols = [c for c in SUBGROUP_MAP[selected_group] if c in df.columns]
            sub_labels = SUBGROUP_LABELS[selected_group][: len(sub_cols)]

            if not sub_cols:
                st.warning("Sub-group columns not found in dataset.")
            else:
                num_top = st.slider(
                    "Number of districts:", 5, max(5, len(df)), 20, key="pop_t3_limit"
                )
                sum_col = ETHNIC_SUMS[selected_group]
                sub_df = df[[name_col] + sub_cols].dropna().copy() if name_col else df[sub_cols].dropna().copy()
                if sum_col in df.columns:
                    sub_df[sum_col] = df.loc[sub_df.index, sum_col]
                    sub_df = sub_df.sort_values(sum_col, ascending=False).head(num_top)

                # Rename columns to short labels
                rename_map = dict(zip(sub_cols, sub_labels))
                sub_df = sub_df.rename(columns=rename_map)

                x_vals = sub_df[name_col].tolist() if name_col else sub_df.index.tolist()
                fig = go.Figure()
                for label in sub_labels:
                    if label in sub_df.columns:
                        fig.add_trace(go.Bar(name=label, x=x_vals, y=sub_df[label].tolist()))
                fig.update_layout(
                    barmode="group",
                    title=f"{selected_group} Sub-Group Breakdown (Top {num_top} districts)",
                    xaxis_title="District",
                    yaxis_title="Population Count",
                    legend_title="Sub-group",
                    xaxis_tickangle=-45,
                    height=520,
                )
                st.plotly_chart(fig, use_container_width=True)

        # ── Tab 4: Treemap ─────────────────────────────────────────────────────────
        with tab4:
            st.subheader("Diversity Treemap — All Districts")
            st.info(
                "Each rectangle is a district, sized by total population and subdivided "
                "by ethnic group proportions. Instantly reveals diversity concentration."
            )

            treemap_df = df[[name_col] + sum_cols].dropna().copy() if name_col else df[sum_cols].dropna().copy()

            # Melt into long format for treemap
            long_rows = []
            for _, row in treemap_df.iterrows():
                district = row[name_col] if name_col else str(row.name)
                for group_name, col in ETHNIC_SUMS.items():
                    val = row.get(col, 0)
                    if pd.notna(val) and val > 0:
                        long_rows.append({
                            "District": district,
                            "Ethnic Group": group_name,
                            "Population": val,
                        })
            long_df = pd.DataFrame(long_rows)

            if long_df.empty:
                st.warning("Not enough data to build treemap.")
            else:
                fig = px.treemap(
                    long_df,
                    path=["Ethnic Group", "District"],
                    values="Population",
                    color="Ethnic Group",
                    color_discrete_sequence=PALETTE,
                    title="Population Distribution: Ethnic Groups × Districts",
                )
                fig.update_layout(height=620)
                fig.update_traces(textinfo="label+percent parent")
                st.plotly_chart(fig, use_container_width=True)

        # ── Tab 5: Raw table ──────────────────────────────────────────────────────
        with tab5:
            st.subheader("📋 Dataset Preview")
            st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    render_population_playground()
