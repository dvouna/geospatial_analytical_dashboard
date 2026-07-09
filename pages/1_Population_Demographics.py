import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from map_utils import load_overlay_dataframe
from visualizer import (
    create_bar_chart,
    create_histogram,
    create_box_plot,
    FLC26_QUALITATIVE,
    PLOTLY_LIGHT_LAYOUT,
)

DATA_DIR = Path(__file__).parent.parent / "data"

# ── Column definitions ─────────────────────────────────────────────────────────

ETHNIC_SUMS = {
    "White": "Total - All White Groups",
    "Asian": "Total - All Asian Groups",
    "Black": "Total - All Black Groups",
    "Mixed": "Total - All Mixed Groups",
    "Others": "Total - Other Ethnic Groups",
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
    "Mixed": [
        "White & Asian",
        "White & Black African",
        "White & Black Caribbean",
        "Other Mixed",
    ],
    "White": ["British", "Irish", "Gypsy/Traveller", "Roma", "Other White"],
    "Others": ["Arab", "Any Other"],
}

PALETTE = FLC26_QUALITATIVE


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
            page_title="Population Demographics",
            page_icon="👥",
            layout="wide",
        )
    except Exception:
        pass

    st.markdown(
        """
        <style>
        /* Reduce Streamlit's default top block padding */
        .block-container { padding-top: 1rem !important; }

        /* Enforce Inter font and increase font size by 2px (to 16px) for tabs */
        div[data-testid="stTabs"] > div:first-child button {
            font-family: 'Inter', sans-serif !important;
        }
        div[data-testid="stTabs"] > div:first-child button p {
            font-family: 'Inter', sans-serif !important;
            font-size: 16px !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            font-family: 'Inter', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 2px;
            margin-top: 0;
            line-height: 1.15;
        ">Population Demographics</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            color: var(--color-text-muted, #64748B);
            font-weight: 500;
            margin-bottom: 17px;
            margin-top: 5px;
        ">Analyze and compare ethnic group proportions and sub-group breakdowns across East of England districts.</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <div style="
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: var(--color-text-muted, #64748B);
        font-weight: 400;
        margin-bottom: 15px;
        margin-top: 2px;
    ">How to use this page
    - Use the tabs below to explore population visualizations.
    </div>.
    """,
        unsafe_allow_html=True,
    )
    with st.popover(
        "💡 Guide: Analyzing Demographics Playground", use_container_width=True
    ):
        st.markdown(
            """
            **How to use the Population Demographics Playground:**
            - **District Population Analysis**: Select up to 5 districts to compare their ethnic subgroup distributions. Toggle between absolute count and proportional share (%).
            - **Ethnic Groups**: Focus on a single broad group (e.g., Asian, Black, White). Visualize the distribution across districts using Bar Charts, Histograms, or Box Plots.
            - **Sub Group Breakdown**: Compare detailed components within a broad group (e.g., Bangladeshi, Indian, Chinese within Asian) for top districts.
            - **Regional Population Analysis**: Review overall makeup stack charts, or explore the Diversity Treemap to see ethnic concentrations.
            """
        )

    # ── Load data ──────────────────────────────────────────────────────────────
    try:
        df = load_overlay_dataframe(DATA_DIR / "population_detail.csv", index_col="fid")
        # Normalize column names by replacing CRLF with LF and map total column name
        df.columns = [c.replace("\r\n", "\n").replace("\r", "\n") for c in df.columns]
        df = df.rename(columns={"Total Population": "Total Sum"})
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
        name_col = next(
            (
                c
                for c in ["LAD24NM", "Geography name ", "Geography name"]
                if c in df.columns
            ),
            None,
        )
        sum_cols = [v for v in ETHNIC_SUMS.values() if v in df.columns]
        all_num_cols = sum_cols + [
            col for cols in SUBGROUP_MAP.values() for col in cols if col in df.columns
        ]
        if "Total Sum" in df.columns:
            all_num_cols.append("Total Sum")
        df = _clean_numeric(df, all_num_cols)

        # ── Tabs ───────────────────────────────────────────────────────────────────
        tab_dist_pop, tab_ethnic_analysis, tab_regional_pop, tab_pop_cancer, tab_pop_dep, tab_data = (
            st.tabs(
                [
                    "District Population Analysis",
                    "Ethnic Groups Analysis",
                    "Regional Population Analysis",
                    "Population-Cancer",
                    "Population-Deprivation",
                    "Data Table",
                ]
            )
        )

        # ── Tab 1: District Population Analysis ───────────────────────────────────
        with tab_dist_pop:
            st.subheader("District Population Analysis")
            st.info(
                "Select and compare ethnic-subgroup distributions across districts. "
                "You can select up to 5 districts for comparison."
            )

            # Controls
            col_sel1, col_sel2 = st.columns([2, 2])
            with col_sel1:
                selected_districts = st.multiselect(
                    "Select districts (up to 5):",
                    options=sorted(df[name_col].dropna().unique()) if name_col else [],
                    default=[df[name_col].iloc[0]] if name_col and len(df) > 0 else [],
                    max_selections=5,
                    key="pop_t5_comp_districts",
                )
                view_mode = st.radio(
                    "Compare by:",
                    ["Proportional (%)", "Absolute (count)"],
                    horizontal=True,
                    key="pop_t5_comp_mode",
                )
            with col_sel2:
                broad_group_filter = st.selectbox(
                    "Filter ethnic subgroups:",
                    options=["All Groups"] + sorted(list(SUBGROUP_MAP.keys())),
                    key="pop_t5_comp_filter",
                )

            if not selected_districts:
                st.warning("⚠️ Please select at least one district to compare.")
            else:
                # Get all subgroup columns
                subgroup_cols = [
                    c for cols in SUBGROUP_MAP.values() for c in cols if c in df.columns
                ]

                # Mappings to short labels and parent groups
                subgroup_to_label = {}
                subgroup_to_parent = {}
                for parent, cols in SUBGROUP_MAP.items():
                    labels = SUBGROUP_LABELS[parent]
                    for col, label in zip(cols, labels):
                        subgroup_to_label[col] = label
                        subgroup_to_parent[col] = parent

                # Filter dataset for selected districts
                comp_df = df[df[name_col].isin(selected_districts)].copy()

                # Melt to long format for Plotly
                melt_cols = [name_col] + subgroup_cols
                if "Total Sum" in comp_df.columns:
                    melt_cols.append("Total Sum")

                long_df = comp_df[melt_cols].melt(
                    id_vars=[name_col, "Total Sum"]
                    if "Total Sum" in comp_df.columns
                    else [name_col],
                    value_vars=subgroup_cols,
                    var_name="Subgroup_Raw",
                    value_name="Count",
                )

                long_df["Subgroup"] = long_df["Subgroup_Raw"].map(subgroup_to_label)
                long_df["Parent Group"] = long_df["Subgroup_Raw"].map(
                    subgroup_to_parent
                )

                # Filter by broad group if requested
                if broad_group_filter != "All Groups":
                    long_df = long_df[long_df["Parent Group"] == broad_group_filter]

                # Compute metric value based on mode
                if view_mode == "Proportional (%)" and "Total Sum" in long_df.columns:
                    long_df["Value"] = (long_df["Count"] / long_df["Total Sum"]) * 100
                    y_axis_title = "Proportion of District Population (%)"
                else:
                    long_df["Value"] = long_df["Count"]
                    y_axis_title = "Population Count"

                # Visualizations
                if len(selected_districts) == 1:
                    # Single district horizontal bar chart
                    fig = px.bar(
                        long_df,
                        x="Value",
                        y="Subgroup",
                        color="Parent Group",
                        orientation="h",
                        title=f"Subgroup Breakdown for {selected_districts[0]} ({view_mode})",
                        labels={
                            "Value": y_axis_title,
                            "Subgroup": "Ethnic Subgroup",
                            "Parent Group": "Ethnic Group",
                        },
                        color_discrete_sequence=PALETTE,
                        category_orders={
                            "Subgroup": sorted(long_df["Subgroup"].unique())
                        },
                    )
                    fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                    fig.update_layout(
                        height=550,
                        yaxis={"categoryorder": "total ascending"},
                        hovermode="y unified",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # Multi-district grouped bar chart
                    fig = px.bar(
                        long_df,
                        x="Subgroup",
                        y="Value",
                        color=name_col,
                        barmode="group",
                        title=f"District Comparison: Subgroup Breakdown ({view_mode})",
                        labels={
                            "Value": y_axis_title,
                            "Subgroup": "Ethnic Subgroup",
                            name_col: "District",
                        },
                        color_discrete_sequence=PALETTE,
                    )
                    fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                    fig.update_layout(
                        height=550, xaxis_tickangle=-45, hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Comparison Table
                st.write("Comparison Data Table")
                pivot_df = long_df.pivot(
                    index=["Parent Group", "Subgroup"], columns=name_col, values="Value"
                )
                if view_mode == "Proportional (%)":
                    st.dataframe(pivot_df.style.format("{:.2f}%"), width="stretch")
                else:
                    st.dataframe(pivot_df.style.format("{:,.0f}"), width="stretch")

        # ── Tab 2: Ethnic Groups Analysis ─────────────────────────────────────────
        with tab_ethnic_analysis:
            st.subheader("Explore a Single Ethnic Group Metric")
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                selected_metric = st.selectbox(
                    "Ethnic group:",
                    options=sorted(list(ETHNIC_SUMS.keys())),
                    format_func=lambda k: f"{k} ({ETHNIC_SUMS[k]})",
                    key="pop_t1_metric",
                )
                metric_col = ETHNIC_SUMS[selected_metric]
            with c2:
                chart_type = st.radio(
                    "Chart type:",
                    ["Bar Chart", "Histogram", "Box Plot"],
                    horizontal=True,
                    key="pop_t1_chart",
                )
            with c3:
                num_districts = st.slider(
                    "Districts (bar chart):", 5, max(5, len(df)), 15, key="pop_t1_limit"
                )

            sort_order = st.selectbox(
                "Sort:", ["Highest to Lowest", "Lowest to Highest"], key="pop_t1_sort"
            )
            ascending = sort_order == "Lowest to Highest"
            plot_df = df.dropna(subset=[metric_col]).sort_values(
                by=metric_col, ascending=ascending
            )

            if chart_type == "Bar Chart":
                bar_df = (
                    plot_df.tail(num_districts)
                    if sort_order == "Highest to Lowest"
                    else plot_df.head(num_districts)
                )
                bar_df = bar_df.sort_values(by=metric_col, ascending=not ascending)
                fig = create_bar_chart(
                    bar_df,
                    x_col=name_col,
                    y_col=metric_col,
                    title=f"Top {num_districts} districts — {metric_col}",
                )
                st.plotly_chart(fig, use_container_width=True)
            elif chart_type == "Histogram":
                fig = create_histogram(
                    plot_df,
                    col=metric_col,
                    title=f"Distribution of {metric_col} across all districts",
                )
                st.plotly_chart(fig, use_container_width=True)
            elif chart_type == "Box Plot":
                fig = create_box_plot(
                    plot_df, y_col=metric_col, title=f"Box Plot: {metric_col} Spread"
                )
                st.plotly_chart(fig, use_container_width=True)

            st.divider()

            st.subheader("Sub-Group Breakdown Within an Ethnic Group")
            st.info(
                "Select a broad ethnic group to see how its sub-categories vary across districts. "
                "'Asian Sum' hides very different sub-populations — Luton vs Cambridge, for example."
            )

            selected_group = st.selectbox(
                "Select ethnic group:",
                sorted(list(SUBGROUP_MAP.keys())),
                key="pop_t3_group",
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
                sub_df = (
                    df[[name_col] + sub_cols].dropna().copy()
                    if name_col
                    else df[sub_cols].dropna().copy()
                )
                if sum_col in df.columns:
                    sub_df[sum_col] = df.loc[sub_df.index, sum_col]
                    sub_df = sub_df.sort_values(sum_col, ascending=False).head(num_top)

                # Rename columns to short labels
                rename_map = dict(zip(sub_cols, sub_labels))
                sub_df = sub_df.rename(columns=rename_map)

                x_vals = (
                    sub_df[name_col].tolist() if name_col else sub_df.index.tolist()
                )
                fig = go.Figure()
                for label in sub_labels:
                    if label in sub_df.columns:
                        fig.add_trace(
                            go.Bar(name=label, x=x_vals, y=sub_df[label].tolist())
                        )
                fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
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

        # ── Tab: Population-Cancer ────────────────────────────────────────────────
        with tab_pop_cancer:
            st.subheader("Population-Cancer Cross Analysis")
            st.info(
                "Explore relationships between district-level demographics (ethnic group proportions) "
                "and cancer incidence rates per 100,000 population."
            )

            import numpy as np
            from utils.data_loader_cancer import get_cancer_overall_df
            try:
                cancer_df = get_cancer_overall_df(year_filter="all")
            except Exception as e:
                st.error(f"❌ Error loading cancer data: {e}")
                cancer_df = pd.DataFrame()

            if cancer_df.empty:
                st.warning("⚠️ Cancer dataset is empty or could not be loaded.")
            else:
                pop_cancer_df = pd.merge(
                    df,
                    cancer_df,
                    on="LAD24CD",
                    suffixes=("_pop", "_cancer")
                )

                if pop_cancer_df.empty:
                    st.warning("⚠️ No matching districts found between population and cancer datasets.")
                else:
                    pop_cancer_df["% White"] = (pop_cancer_df["Total - All White Groups"] / pop_cancer_df["Total Sum"]) * 100
                    pop_cancer_df["% Asian"] = (pop_cancer_df["Total - All Asian Groups"] / pop_cancer_df["Total Sum"]) * 100
                    pop_cancer_df["% Black"] = (pop_cancer_df["Total - All Black Groups"] / pop_cancer_df["Total Sum"]) * 100
                    pop_cancer_df["% Mixed"] = (pop_cancer_df["Total - All Mixed Groups"] / pop_cancer_df["Total Sum"]) * 100
                    pop_cancer_df["% Others"] = (pop_cancer_df["Total - Other Ethnic Groups"] / pop_cancer_df["Total Sum"]) * 100

                    broad_pct_cols = {
                        "% White": "% White",
                        "% Asian": "% Asian",
                        "% Black": "% Black",
                        "% Mixed": "% Mixed",
                        "% Others": "% Others"
                    }

                    pct_cols = [c for c in df.columns if "(percent)" in c]
                    demog_options = list(broad_pct_cols.keys()) + sorted(pct_cols)

                    cancer_types_rates = {
                        "Overall Cancer Rate": "Rate",
                        "Total Incidence Count": "Total_incidence",
                        "Bladder Cancer Rate": "bladder",
                        "Blood Cancer Rate": "blood cancer",
                        "Bowel Cancer Rate": "bowel",
                        "Brain Cancer Rate": "brain",
                        "Breast Cancer Rate": "breast",
                        "Head & Neck Cancer Rate": "head and neck",
                        "Kidney Cancer Rate": "kidney",
                        "Liver & Biliary Cancer Rate": "liver and biliary tract",
                        "Lung Cancer Rate": "lung",
                        "Ovarian Cancer Rate": "ovary",
                        "Pancreatic Cancer Rate": "pancreas",
                        "Prostate Cancer Rate": "prostate",
                        "Skin Cancer Rate": "skin",
                        "Uterine Cancer Rate": "uterus",
                    }

                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        sel_demog = st.selectbox(
                            "Select Demographic Metric (X-Axis):",
                            options=demog_options,
                            key="pop_cancer_x_var"
                        )
                    with col_c2:
                        sel_cancer_label = st.selectbox(
                            "Select Cancer Metric (Y-Axis):",
                            options=sorted(list(cancer_types_rates.keys())),
                            key="pop_cancer_y_var"
                        )
                        sel_cancer = cancer_types_rates[sel_cancer_label]

                    x_data = pd.to_numeric(pop_cancer_df[sel_demog], errors="coerce")
                    y_data = pd.to_numeric(pop_cancer_df[sel_cancer], errors="coerce")
                    district_names = pop_cancer_df["LAD24NM_pop"] if "LAD24NM_pop" in pop_cancer_df.columns else pop_cancer_df["LAD24NM"]

                    plot_data = pd.DataFrame({
                        "Demographic": x_data,
                        "CancerMetric": y_data,
                        "District": district_names
                    }).dropna()

                    if plot_data.empty:
                        st.warning("⚠️ No valid data points found for this selection.")
                    else:
                        r_coef = np.corrcoef(plot_data["Demographic"], plot_data["CancerMetric"])[0, 1]

                        st.write("### 🔍 Correlation Analysis")
                        st.metric(
                            label=f"Pearson Correlation Coefficient (r) between {sel_demog} and {sel_cancer_label}",
                            value=f"{r_coef:.3f}",
                            help="r values close to 1 or -1 indicate strong positive or negative relationships. Close to 0 indicates no linear correlation."
                        )

                        fig = px.scatter(
                            plot_data,
                            x="Demographic",
                            y="CancerMetric",
                            hover_name="District",
                            title=f"Correlation: {sel_demog} vs {sel_cancer_label}",
                            labels={
                                "Demographic": sel_demog,
                                "CancerMetric": sel_cancer_label
                            },
                            color_discrete_sequence=PALETTE
                        )

                        if len(plot_data) > 1:
                            try:
                                slope, intercept = np.polyfit(plot_data["Demographic"], plot_data["CancerMetric"], 1)
                                x_min, x_max = plot_data["Demographic"].min(), plot_data["Demographic"].max()
                                x_line = np.array([x_min, x_max])
                                y_line = slope * x_line + intercept
                                fig.add_trace(go.Scatter(
                                    x=x_line,
                                    y=y_line,
                                    mode="lines",
                                    name=f"Trendline (y = {slope:.2f}x + {intercept:.2f})",
                                    line=dict(dash="dash", color="#E63946", width=2)
                                ))
                            except Exception:
                                pass

                        fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                        st.plotly_chart(fig, use_container_width=True)

                        st.divider()

                        st.write("### ⚔️ District Demographics vs Cancer Rate Side-by-Side")
                        selected_dists = st.multiselect(
                            "Select districts for direct comparison:",
                            options=sorted(plot_data["District"].unique()),
                            default=sorted(plot_data["District"].unique())[:3],
                            max_selections=5,
                            key="pop_cancer_dists_sel"
                        )

                        if selected_dists:
                            comp_subset = plot_data[plot_data["District"].isin(selected_dists)]
                            col_sub1, col_sub2 = st.columns(2)
                            with col_sub1:
                                fig_dem = px.bar(
                                    comp_subset,
                                    x="District",
                                    y="Demographic",
                                    title=f"{sel_demog} by District",
                                    labels={"Demographic": sel_demog},
                                    color_discrete_sequence=[PALETTE[0]]
                                )
                                fig_dem.update_layout(**PLOTLY_LIGHT_LAYOUT)
                                st.plotly_chart(fig_dem, use_container_width=True)
                            with col_sub2:
                                fig_can = px.bar(
                                    comp_subset,
                                    x="District",
                                    y="CancerMetric",
                                    title=f"{sel_cancer_label} by District",
                                    labels={"CancerMetric": sel_cancer_label},
                                    color_discrete_sequence=[PALETTE[1]]
                                )
                                fig_can.update_layout(**PLOTLY_LIGHT_LAYOUT)
                                st.plotly_chart(fig_can, use_container_width=True)

        # ── Tab: Population-Deprivation ───────────────────────────────────────────
        with tab_pop_dep:
            st.subheader("Population-Deprivation Cross Analysis")
            st.info(
                "Explore relationships between district-level demographics (ethnic group proportions) "
                "and Indices of Deprivation 2025 Ranks. Lower rank number represents higher deprivation (Rank 1 is the most deprived)."
            )

            import numpy as np
            try:
                dep_df = load_overlay_dataframe(DATA_DIR / "iod_2025.csv")
            except Exception as e:
                st.error(f"❌ Error loading deprivation data: {e}")
                dep_df = pd.DataFrame()

            if dep_df.empty:
                st.warning("⚠️ Deprivation dataset is empty or could not be loaded.")
            else:
                pop_dep_df = pd.merge(
                    df,
                    dep_df,
                    left_on="LAD24CD",
                    right_on="Local Authority District code (2024)",
                    suffixes=("_pop", "_dep")
                )

                if pop_dep_df.empty:
                    st.warning("⚠️ No matching districts found between population and deprivation datasets.")
                else:
                    pop_dep_df["% White"] = (pop_dep_df["Total - All White Groups"] / pop_dep_df["Total Sum"]) * 100
                    pop_dep_df["% Asian"] = (pop_dep_df["Total - All Asian Groups"] / pop_dep_df["Total Sum"]) * 100
                    pop_dep_df["% Black"] = (pop_dep_df["Total - All Black Groups"] / pop_dep_df["Total Sum"]) * 100
                    pop_dep_df["% Mixed"] = (pop_dep_df["Total - All Mixed Groups"] / pop_dep_df["Total Sum"]) * 100
                    pop_dep_df["% Others"] = (pop_dep_df["Total - Other Ethnic Groups"] / pop_dep_df["Total Sum"]) * 100

                    broad_pct_cols = {
                        "% White": "% White",
                        "% Asian": "% Asian",
                        "% Black": "% Black",
                        "% Mixed": "% Mixed",
                        "% Others": "% Others"
                    }

                    pct_cols = [c for c in df.columns if "(percent)" in c]
                    demog_options = list(broad_pct_cols.keys()) + sorted(pct_cols)

                    dep_domains = {
                        "Index of Multiple Deprivation (IMD) Rank": "Index of Multiple Deprivation (IMD) Rank",
                        "Income Rank": "Income Rank",
                        "Employment Rank": "Employment Rank",
                        "Education Skills and Training Rank": "Education Skills and Training Rank",
                        "Health Deprivation and Disability Rank": "Health Deprivation and Disability Rank",
                        "Crime Rank": "Crime Rank",
                        "Barriers to Housing and Services Rank": "Barriers to Housing and Services Rank",
                        "Living Environment Rank": "Living Environment Rank",
                        "Income Deprivation Affecting Children Index (IDACI) Rank": "Income Deprivation Affecting Children Index (IDACI) Rank",
                        "Income Deprivation Affecting Older People (IDAOPI) Rank": "Income Deprivation Affecting Older People (IDAOPI) Rank",
                    }

                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        sel_demog_dep = st.selectbox(
                            "Select Demographic Metric (X-Axis):",
                            options=demog_options,
                            key="pop_dep_x_var"
                        )
                    with col_d2:
                        sel_dep_label = st.selectbox(
                            "Select Deprivation Domain (Y-Axis):",
                            options=sorted(list(dep_domains.keys())),
                            key="pop_dep_y_var"
                        )
                        sel_dep = dep_domains[sel_dep_label]

                    x_data = pd.to_numeric(pop_dep_df[sel_demog_dep], errors="coerce")
                    y_data = pd.to_numeric(pop_dep_df[sel_dep], errors="coerce")
                    district_names = pop_dep_df["LAD24NM_pop"] if "LAD24NM_pop" in pop_dep_df.columns else pop_dep_df["LAD24NM"]

                    plot_data_dep = pd.DataFrame({
                        "Demographic": x_data,
                        "DeprivationMetric": y_data,
                        "District": district_names
                    }).dropna()

                    if plot_data_dep.empty:
                        st.warning("⚠️ No valid data points found for this selection.")
                    else:
                        r_coef = np.corrcoef(plot_data_dep["Demographic"], plot_data_dep["DeprivationMetric"])[0, 1]

                        st.write("### 🔍 Correlation Analysis")
                        st.metric(
                            label=f"Pearson Correlation Coefficient (r) between {sel_demog_dep} and {sel_dep_label}",
                            value=f"{r_coef:.3f}",
                            help="r values close to 1 or -1 indicate strong positive or negative relationships."
                        )

                        fig = px.scatter(
                            plot_data_dep,
                            x="Demographic",
                            y="DeprivationMetric",
                            hover_name="District",
                            title=f"Correlation: {sel_demog_dep} vs {sel_dep_label}",
                            labels={
                                "Demographic": sel_demog_dep,
                                "DeprivationMetric": sel_dep_label
                            },
                            color_discrete_sequence=PALETTE
                        )

                        fig.update_layout(yaxis=dict(autorange="reversed"))

                        if len(plot_data_dep) > 1:
                            try:
                                slope, intercept = np.polyfit(plot_data_dep["Demographic"], plot_data_dep["DeprivationMetric"], 1)
                                x_min, x_max = plot_data_dep["Demographic"].min(), plot_data_dep["Demographic"].max()
                                x_line = np.array([x_min, x_max])
                                y_line = slope * x_line + intercept
                                fig.add_trace(go.Scatter(
                                    x=x_line,
                                    y=y_line,
                                    mode="lines",
                                    name=f"Trendline (y = {slope:.2f}x + {intercept:.2f})",
                                    line=dict(dash="dash", color="#E63946", width=2)
                                ))
                            except Exception:
                                pass

                        fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                        st.plotly_chart(fig, use_container_width=True)

                        st.divider()

                        st.write("### 📊 Demographics in Extreme Deprivation Profiles")
                        st.info(
                            "This chart contrasts the demographic breakdown of the 10 most deprived "
                            "districts with the 10 least deprived districts in the region for the selected domain."
                        )

                        sorted_by_dep = pop_dep_df.sort_values(by=sel_dep)

                        most_deprived = sorted_by_dep.head(10).copy()
                        least_deprived = sorted_by_dep.tail(10).copy()

                        most_deprived["Group"] = "10 Most Deprived Districts"
                        least_deprived["Group"] = "10 Least Deprived Districts"

                        extremes_df = pd.concat([most_deprived, least_deprived])

                        group_means = extremes_df.groupby("Group")[
                            ["% White", "% Asian", "% Black", "% Mixed", "% Others"]
                        ].mean().reset_index()

                        group_means_long = group_means.melt(
                            id_vars=["Group"],
                            value_vars=["% White", "% Asian", "% Black", "% Mixed", "% Others"],
                            var_name="Ethnic Group",
                            value_name="Percentage Share (%)"
                        )

                        fig_groups = px.bar(
                            group_means_long,
                            x="Group",
                            y="Percentage Share (%)",
                            color="Ethnic Group",
                            barmode="group",
                            title=f"Average Demographics: 10 Most vs 10 Least Deprived Districts ({sel_dep_label})",
                            color_discrete_sequence=PALETTE
                        )
                        fig_groups.update_layout(**PLOTLY_LIGHT_LAYOUT)
                        st.plotly_chart(fig_groups, use_container_width=True)

        # ── Tab 4: Regional Population Analysis ──────────────────────────────────
        with tab_regional_pop:
            st.subheader("Ethnic Composition by District")
            st.info(
                "Each bar shows the proportional ethnic makeup of a district. "
                "Toggle between proportions (%) and absolute counts."
            )

            view_mode = st.radio(
                "View mode:",
                ["Proportional (%)", "Absolute (count)"],
                horizontal=True,
                key="pop_t2_mode",
            )
            sort_by = st.selectbox(
                "Sort districts by:",
                ["Asian", "Black", "Mixed", "Others", "Total Population", "White"],
                key="pop_t2_sort",
            )

            comp_df = (
                df[[name_col] + sum_cols].dropna().copy()
                if name_col
                else df[sum_cols].dropna().copy()
            )
            if "Total Sum" in df.columns:
                comp_df["Total Sum"] = df.loc[comp_df.index, "Total Sum"]

            sort_col = (
                ETHNIC_SUMS.get(sort_by, "Total Sum")
                if sort_by != "Total Population"
                else "Total Sum"
            )
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
                    fig.add_trace(
                        go.Bar(
                            name=group_name,
                            x=x_vals,
                            y=comp_df[col].tolist(),
                        )
                    )
            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
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

            st.divider()

            st.subheader("Diversity Treemap — All Districts")
            st.info(
                "Each rectangle is a district, sized by total population and subdivided "
                "by ethnic group proportions. Instantly reveals diversity concentration."
            )

            treemap_df = (
                df[[name_col] + sum_cols].dropna().copy()
                if name_col
                else df[sum_cols].dropna().copy()
            )

            # Melt into long format for treemap
            long_rows = []
            for _, row in treemap_df.iterrows():
                district = row[name_col] if name_col else str(row.name)
                for group_name, col in ETHNIC_SUMS.items():
                    val = row.get(col, 0)
                    if pd.notna(val) and val > 0:
                        long_rows.append(
                            {
                                "District": district,
                                "Ethnic Group": group_name,
                                "Population": val,
                            }
                        )
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
                fig.update_layout(height=620, **PLOTLY_LIGHT_LAYOUT)
                fig.update_traces(textinfo="label+percent parent")
                st.plotly_chart(fig, use_container_width=True)

        # ── Tab 5: Data Table ─────────────────────────────────────────────────────
        with tab_data:
            st.subheader("Dataset Preview")
            st.dataframe(df, width="stretch")


if __name__ == "__main__":
    render_population_playground()
