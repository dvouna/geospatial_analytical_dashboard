import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

from config import Config

from visualizer import (
    create_bar_chart,
    create_scatter_chart,
    FLC26_QUALITATIVE,
    PLOTLY_LIGHT_LAYOUT,
)
from utils.data_loader_cancer import (
    get_cancer_overall_df,
    get_cancer_top5_df,
    load_cancer_raw_data,
)
from gemini_queries import render_ai_insights

DATA_DIR = Path(__file__).parent.parent / "data"

CANCER_TYPES = [
    "bladder",
    "blood cancer",
    "bowel",
    "brain",
    "breast",
    "head and neck",
    "kidney",
    "liver and biliary tract",
    "lung",
    "ovary",
    "pancreas",
    "prostate",
    "skin",
    "uterus",
]

CANCER_COLORS = {
    "bladder": "#7209B7",
    "blood cancer": "#F72585",
    "blood": "#F72585",
    "bowel": "#4361EE",
    "brain": "#4CC9F0",
    "breast": "#E63946",
    "head and neck": "#560BAD",
    "kidney": "#3A0CA3",
    "liver and biliary tract": "#3F37C9",
    "lung": "#2A9D8F",
    "ovary": "#DDA15E",
    "pancreas": "#BC6C25",
    "prostate": "#E9C46A",
    "skin": "#F4A261",
    "skin cancer": "#F4A261",
    "uterus": "#9B5DE5",
}

AGE_BANDS = [
    "Age 00 to 24",
    "Age 25 to 49",
    "Age 50 to 59",
    "Age 60 to 69",
    "Age 70 to 79",
    "Age 80 and over",
]


def _clean_numeric(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce"
            )
    return df


def render_cancer_trends():
    try:
        st.set_page_config(
            page_title="Cancer Trends Analysis Playground",
            page_icon="🎗️",
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

        /* Sidebar separator: left border + padding on the research assistant column */
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
            border-left: 2px solid var(--color-border, #E2E8F0) !important;
            padding-left: 1.5rem !important;
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
            margin-top: 1.5rem;
            line-height: 1.15;
        ">Cancer Trends Analysis Playground</div>
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
            margin-bottom: 18px;
            margin-top: 2px;
        ">Compare oncology rates, age profiles, confidence intervals, and cancer type compositions across East of England districts.</div>
        """,
        unsafe_allow_html=True,
    )

    with st.popover(
        "💡 Guide: Analyzing Cancer Trends Playground", use_container_width=True
    ):
        st.markdown(
            """
            **How to use the Cancer Trends Analysis Playground:**
            - **District Cancer Analysis**: Compare specific cancer incidence rates or overall age-standardised rates across up to 5 districts. Note the 95% Confidence Intervals (CI) plots.
            - **Cancer Type Analysis**: Compare overall incidence and counts, or view the stacked composition of cancer types (bladder, breast, lung, bowel, etc.) by district.
            - **Historical Trends**: Plot Crude Rates or Incidence Counts over time (2018–2022) to observe historical progress.
            - **Age Profiles**: Examine age-band breakdowns (0-24, 25-49, 50-59, 60-69, 70-79, 80+) for targeted healthcare outreach.
            - **Regional Analysis**: Discover statistical confidence intervals and cross-type correlations at a glance across the East of England.
            """
        )

    # ── Year Selector ──────────────────────────────────────────────────────────
    years = ["All Years (Average)", "2022", "2021", "2020", "2019", "2018"]
    selected_year_str = st.selectbox(
        "📅 Select Analysis Year:", options=years, index=0, key="cancer_year_selector"
    )

    if selected_year_str == "All Years (Average)":
        year_val = "all"
    else:
        year_val = int(selected_year_str)

    # ── Load datasets ──────────────────────────────────────────────────────────
    try:
        overall_df = get_cancer_overall_df(year_filter=year_val)
    except Exception as exc:
        print(f"[cancer] Error loading overall cancer data: {exc}", file=sys.stderr)
        st.error(
            "❌ Error loading overall cancer data. Please contact the administrator."
            if not Config.DEBUG
            else f"❌ Error loading overall cancer data: {exc}"
        )
        overall_df = pd.DataFrame()

    try:
        top5_df = get_cancer_top5_df(year_filter=year_val)
    except Exception as exc:
        print(f"[cancer] Error loading top-5 cancers data: {exc}", file=sys.stderr)
        st.error(
            "❌ Error loading top-5 cancers data. Please contact the administrator."
            if not Config.DEBUG
            else f"❌ Error loading top-5 cancers data: {exc}"
        )
        top5_df = pd.DataFrame()

    if overall_df.empty:
        st.warning("Overall Cancer data unavailable.")
        return

    # Clean numerics
    numeric_overall = CANCER_TYPES + [
        "Rate",
        "Total_incidence",
        "95% lower confidence interval",
        "95% upper confidence interval",
    ]
    overall_df = _clean_numeric(overall_df, numeric_overall)
    if not top5_df.empty:
        top5_df = _clean_numeric(top5_df, AGE_BANDS + ["All ages"])

    # ── Split page layout ──────────────────────────────────────────────────────
    col_main, col_sidebar = st.columns([7, 3])

    with col_sidebar:
        import importlib

        ra_module = importlib.import_module("pages.5_AI_Research_Assistant")
        ra_module.render_research_assistant_widget(key_suffix="cancer_playground")

    with col_main:
        name_col = next(
            (c for c in ["District Name"] if c in overall_df.columns),
            None,
        )

        # ── Tabs ───────────────────────────────────────────────────────────────────
        (
            tab_comp,
            tab_type_analysis,
            tab_trends,
            tab_age,
            tab_regional,
            tab_data,
        ) = st.tabs(
            [
                "District Level Analysis",
                "Cancer Type Comparison",
                "Temporal Trends",
                "Age Profiles",
                "Regional Comparison",
                "Data Table",
            ]
        )

        # ── Tab 1: District Cancer Analysis ───────────────────────────────────────
        with tab_comp:
            st.subheader("District Cancer Analysis")
            st.info(
                "Select and compare cancer incidence rates and confidence intervals across districts. "
                "You can select up to 5 districts for comparison."
            )

            districts_available = (
                overall_df[name_col].dropna().sort_values().tolist()
                if name_col in overall_df.columns
                else []
            )

            if not districts_available:
                st.warning("District name column not found.")
            else:
                col_sel1, col_sel2 = st.columns([2, 1])
                with col_sel1:
                    selected_districts = st.multiselect(
                        "Select districts (up to 5):",
                        options=districts_available,
                        default=districts_available[:1],
                        max_selections=5,
                        key="cancer_comp_districts",
                    )
                with col_sel2:
                    comp_mode = st.radio(
                        "Comparison mode:",
                        ["Specific Cancer Rates", "Overall Rate with 95% CI"],
                        key="cancer_comp_mode",
                    )

                if not selected_districts:
                    st.warning("⚠️ Please select at least one district to compare.")
                else:
                    # Filter dataset for selected districts
                    comp_df = overall_df[
                        overall_df[name_col].isin(selected_districts)
                    ].copy()

                    if comp_mode == "Specific Cancer Rates":
                        # Melt specific cancer types to long format
                        avail_cancers = [
                            c for c in CANCER_TYPES if c in overall_df.columns
                        ]
                        long_df = comp_df[[name_col] + avail_cancers].melt(
                            id_vars=[name_col],
                            value_vars=avail_cancers,
                            var_name="Cancer_Raw",
                            value_name="Rate",
                        )
                        long_df["Cancer Type"] = long_df["Cancer_Raw"].str.capitalize()

                        if len(selected_districts) == 1:
                            # Single district horizontal bar chart
                            fig = px.bar(
                                long_df,
                                x="Rate",
                                y="Cancer Type",
                                color="Cancer Type",
                                orientation="h",
                                title=f"Cancer Incidence Rates for {selected_districts[0]}",
                                labels={
                                    "Rate": "Incidence Rate (per 100k)",
                                    "Cancer Type": "Cancer Type",
                                },
                                color_discrete_map={
                                    c.capitalize(): CANCER_COLORS[c]
                                    for c in CANCER_COLORS
                                    if c in CANCER_COLORS
                                },
                                category_orders={
                                    "Cancer Type": [
                                        c.capitalize() for c in CANCER_TYPES
                                    ]
                                },
                            )
                            fig.update_layout(
                                height=450,
                                showlegend=False,
                                yaxis={"categoryorder": "total ascending"},
                                hovermode="y unified",
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            # Multi-district grouped vertical bar chart
                            fig = px.bar(
                                long_df,
                                x="Cancer Type",
                                y="Rate",
                                color=name_col,
                                barmode="group",
                                title="District Comparison: Cancer Incidence Rates",
                                labels={
                                    "Rate": "Incidence Rate (per 100k)",
                                    name_col: "District",
                                },
                                color_discrete_sequence=FLC26_QUALITATIVE,
                            )
                            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                            fig.update_layout(height=500, hovermode="x unified")
                            st.plotly_chart(fig, use_container_width=True)

                        # Generate AI Insights
                        render_ai_insights(
                            long_df,
                            f"Comparing specific cancer incidence rates across selected districts: {', '.join(selected_districts)}",
                            "tab_cancer_comp_rate",
                        )

                        # Comparison Data Table
                        st.write("#### 📋 Comparison Data Table")
                        pivot_df = long_df.pivot(
                            index="Cancer Type", columns=name_col, values="Rate"
                        )
                        st.dataframe(
                            pivot_df.style.format("{:.1f} per 100k"),
                            width="stretch",
                        )
                    else:
                        # Overall Rate with 95% CI comparison (scatter with error_y)
                        ci_lower = "95% lower confidence interval"
                        ci_upper = "95% upper confidence interval"

                        if (
                            ci_lower not in overall_df.columns
                            or ci_upper not in overall_df.columns
                        ):
                            st.warning(
                                "Confidence interval columns not found in dataset."
                            )
                        else:
                            # Render Plotly Scatter with error bars
                            fig = go.Figure()

                            # Add error bars trace
                            fig.add_trace(
                                go.Scatter(
                                    x=comp_df[name_col].tolist(),
                                    y=comp_df["Rate"].tolist(),
                                    error_y=dict(
                                        type="data",
                                        symmetric=False,
                                        array=(
                                            comp_df[ci_upper] - comp_df["Rate"]
                                        ).tolist(),
                                        arrayminus=(
                                            comp_df["Rate"] - comp_df[ci_lower]
                                        ).tolist(),
                                        color="rgba(100,100,100,0.6)",
                                    ),
                                    mode="markers",
                                    marker=dict(
                                        size=12, color="#E63946", symbol="diamond"
                                    ),
                                    name="Overall Standardised Rate",
                                )
                            )

                            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                            fig.update_layout(
                                title="Overall Standardised Cancer Rates with 95% CI",
                                xaxis_title="District",
                                yaxis_title="Rate (per 100,000)",
                                height=500,
                                hovermode="x unified",
                            )
                            st.plotly_chart(fig, use_container_width=True)

                            # Generate AI Insights
                            render_ai_insights(
                                comp_df,
                                f"Comparing overall standardised cancer rates with 95% CI across selected districts: {', '.join(selected_districts)}",
                                "tab_cancer_comp_ci",
                            )

                            # Comparison Data Table
                            st.write("### 📋 Comparison Data Table")
                            summary_df = (
                                comp_df[[name_col, "Rate", ci_lower, ci_upper]]
                                .set_index(name_col)
                                .T
                            )
                            st.dataframe(
                                summary_df.style.format("{:.1f}"),
                                width="stretch",
                            )

        # ── Tab 2: Cancer Type Analysis ──────────────────────────────────────────
        with tab_type_analysis:
            st.subheader("Compare Cancer Incidence Rates by District")
            rate_cols = {
                "Overall Rate": "Rate",
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
            c1, c2 = st.columns(2)
            with c1:
                selected_label = st.selectbox(
                    "Y-Axis Metric:", sorted(list(rate_cols.keys())), key="c_t1_metric"
                )
                metric_field = rate_cols[selected_label]
            with c2:
                sort_order = st.selectbox(
                    "Sort:", ["Highest to Lowest", "Lowest to Highest"], key="c_t1_sort"
                )

            plot_df = overall_df.dropna(subset=[metric_field]).copy()
            ascending = sort_order == "Lowest to Highest"
            plot_df = plot_df.sort_values(by=metric_field, ascending=ascending)
            limit = st.slider(
                "Districts to display:", 5, max(5, len(plot_df)), 15, key="c_t1_limit"
            )
            show_df = (
                plot_df.tail(limit)
                if sort_order == "Highest to Lowest"
                else plot_df.head(limit)
            )
            show_df = show_df.sort_values(by=metric_field, ascending=not ascending)
            fig = create_bar_chart(
                show_df,
                x_col=name_col,
                y_col=metric_field,
                title=f"{selected_label} — Top {limit} Districts",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Generate AI Insights
            render_ai_insights(
                show_df[[name_col, metric_field]],
                f"Analyzing {selected_label} for top {limit} districts sorted by {sort_order}",
                "tab_cancer_type_single",
            )

            st.divider()

            st.subheader("Cancer Type Composition by District")
            st.info(
                "Stacked bars show how each district's total incidence is composed "
                "across the cancer types. Toggle between proportional (%) and absolute counts."
            )
            avail_cancers = [c for c in CANCER_TYPES if c in overall_df.columns]
            view_mode = st.radio(
                "View mode:",
                ["Proportional (%)", "Absolute (count)"],
                horizontal=True,
                key="c_t2_mode",
            )
            sort_by_t2 = st.selectbox(
                "Sort districts by:",
                sorted(avail_cancers + ["Overall Rate"]),
                key="c_t2_sort",
            )

            count_cols = [f"count_{c}" for c in avail_cancers]
            comp_cols = (
                [name_col] + avail_cancers + count_cols + ["Rate"]
                if name_col
                else avail_cancers + count_cols + ["Rate"]
            )
            comp_df = overall_df[comp_cols].dropna().copy()

            sort_c = sort_by_t2 if sort_by_t2 != "Overall Rate" else "Rate"
            if sort_c in comp_df.columns:
                comp_df = comp_df.sort_values(sort_c, ascending=False)

            if view_mode == "Proportional (%)":
                totals = comp_df[avail_cancers].sum(axis=1).replace(0, float("nan"))
                for c in avail_cancers:
                    comp_df[c] = comp_df[c] / totals * 100
                y_label = "Share of Total Incidence (%)"
            else:
                for c in avail_cancers:
                    if f"count_{c}" in comp_df.columns:
                        comp_df[c] = comp_df[f"count_{c}"]
                y_label = "Incidence Count"

            x_vals = (
                comp_df[name_col].tolist()
                if name_col
                else comp_df.index.astype(str).tolist()
            )
            fig = go.Figure()
            for cancer in avail_cancers:
                fig.add_trace(
                    go.Bar(
                        name=cancer.capitalize(),
                        x=x_vals,
                        y=comp_df[cancer].tolist(),
                        marker_color=CANCER_COLORS.get(cancer, None),
                    )
                )
            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
            fig.update_layout(
                barmode="stack",
                title="Cancer Type Composition by District",
                xaxis_title="District",
                yaxis_title=y_label,
                xaxis_tickangle=-45,
                height=520,
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Tab 3: Historical Trends ──────────────────────────────────────────────
        with tab_trends:
            st.subheader("Historical Cancer Trends (2018–2022)")
            st.info(
                "Track how cancer rates and counts have changed over the 5-year period. "
                "Select one or more districts and a cancer type to see the trend."
            )
            raw_cancer_df = load_cancer_raw_data()
            if raw_cancer_df.empty:
                st.warning("Historical data is unavailable.")
            else:
                icbs_available = ["All ICBs"] + sorted(
                    raw_cancer_df["ICB"].dropna().unique().tolist()
                )
                sel_icb = st.selectbox(
                    "Filter Districts by ICB:",
                    options=icbs_available,
                    key="cancer_trend_icb_select",
                )
                if sel_icb != "All ICBs":
                    raw_cancer_df = raw_cancer_df[raw_cancer_df["ICB"] == sel_icb]

                districts_available = sorted(
                    raw_cancer_df["Geography Name"].dropna().unique().tolist()
                )
                sel_trend_districts = st.multiselect(
                    "Select Districts for Trend:",
                    options=districts_available,
                    default=districts_available[:2]
                    if len(districts_available) > 1
                    else districts_available[:1],
                    key="cancer_trend_dist_multiselect",
                )
                cancers_available = sorted(
                    raw_cancer_df["Cancer Type"].unique().tolist()
                )
                sel_trend_cancer = st.selectbox(
                    "Select Cancer Type for Trend:",
                    options=["All Cancers"] + cancers_available,
                    key="cancer_trend_type_select",
                )
                trend_metric = st.radio(
                    "Trend Metric:",
                    ["Crude Rate (per 100k)", "Total Incidence Count"],
                    horizontal=True,
                    key="cancer_trend_metric_radio",
                )
                if not sel_trend_districts:
                    st.warning("⚠️ Please select at least one district to view trends.")
                else:
                    trend_df = raw_cancer_df[
                        raw_cancer_df["Geography Name"].isin(sel_trend_districts)
                    ].copy()
                    if sel_trend_cancer != "All Cancers":
                        trend_df = trend_df[trend_df["Cancer Type"] == sel_trend_cancer]

                    grouped_trend = (
                        trend_df.groupby(["Year", "Geography Name", "fid"])[
                            "Total Incidence"
                        ]
                        .sum()
                        .reset_index()
                    )
                    try:
                        gdf_dist = gpd.read_file(str(DATA_DIR / "base_gdf_1.geojson"))
                        df_dist_pop = pd.DataFrame(
                            gdf_dist[["fid", "total_population"]]
                        )
                        df_dist_pop["fid"] = df_dist_pop["fid"].astype(str).str.strip()
                        grouped_trend["fid"] = (
                            grouped_trend["fid"].astype(str).str.strip()
                        )
                        grouped_trend = grouped_trend.merge(
                            df_dist_pop, on="fid", how="inner"
                        )
                        grouped_trend["Crude Rate (per 100k)"] = (
                            grouped_trend["Total Incidence"]
                            / grouped_trend["total_population"]
                        ) * 100000
                    except Exception as e:
                        print(
                            f"[cancer] Error merging population data: {e}",
                            file=sys.stderr,
                        )
                        st.error(
                            "❌ Error merging population data. Please contact the administrator."
                            if not Config.DEBUG
                            else f"Error merging population data: {e}"
                        )
                        grouped_trend["Crude Rate (per 100k)"] = 0

                    grouped_trend = grouped_trend.rename(
                        columns={"Total Incidence": "Total Incidence Count"}
                    )

                    y_axis_col = trend_metric
                    fig_trend = px.line(
                        grouped_trend,
                        x="Year",
                        y=y_axis_col,
                        color="Geography Name",
                        title=f"{sel_trend_cancer} — {trend_metric} Trend Over Time",
                        markers=True,
                        color_discrete_sequence=FLC26_QUALITATIVE,
                    )
                    fig_trend.update_layout(**PLOTLY_LIGHT_LAYOUT)
                    fig_trend.update_layout(
                        xaxis=dict(tickmode="linear", tick0=2018, dtick=1),
                        hovermode="x unified",
                        height=480,
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)

                    # Generate AI Insights
                    render_ai_insights(
                        grouped_trend,
                        f"Analyzing historical trend of {sel_trend_cancer} ({trend_metric}) for selected districts.",
                        "tab_cancer_historical",
                    )

        # ── Tab 4: Age Profiles ───────────────────────────────────────────────────
        with tab_age:
            st.subheader("Age-Band Diagnosis Profiles")
            st.info(
                "Breakdown of cancer diagnoses across 6 age bands for selected districts (up to 5) and a cancer type. "
                "Useful for targeting age-specific early-detection campaigns."
            )
            if top5_df.empty:
                st.warning("⚠️ Age profiles cannot be shown (dataset unavailable).")
            else:
                age_name_col = next(
                    (c for c in ["District Name"] if c in top5_df.columns),
                    None,
                )
                cancer_type_col = (
                    "Cancer Type" if "Cancer Type" in top5_df.columns else None
                )

                ca, cb = st.columns(2)
                with ca:
                    icb_list = ["All ICBs"] + (
                        sorted(top5_df["ICB"].dropna().unique().tolist())
                        if "ICB" in top5_df.columns
                        else []
                    )
                    if len(icb_list) > 1:
                        sel_icb = st.selectbox(
                            "Filter by ICB:", options=icb_list, key="c_t3_icb"
                        )
                        if sel_icb != "All ICBs":
                            top5_df = top5_df[top5_df["ICB"] == sel_icb]

                    districts_list = (
                        sorted(top5_df[age_name_col].dropna().unique().tolist())
                        if age_name_col
                        else []
                    )
                    sel_districts = st.multiselect(
                        "Select districts (up to 5):",
                        options=districts_list,
                        default=[districts_list[0]] if districts_list else [],
                        max_selections=5,
                        key="c_t3_districts",
                    )
                with cb:
                    cancers_list = (
                        sorted(top5_df[cancer_type_col].dropna().unique().tolist())
                        if cancer_type_col
                        else sorted(CANCER_TYPES)
                    )
                    sel_cancer = st.selectbox(
                        "Select cancer type:", cancers_list, key="c_t3_cancer"
                    )

                if not sel_districts:
                    st.warning(
                        "⚠️ Please select at least one district to view age profiles."
                    )
                else:
                    avail_age_cols = [c for c in AGE_BANDS if c in top5_df.columns]
                    filt = top5_df.copy()
                    if age_name_col:
                        filt = filt[filt[age_name_col].isin(sel_districts)]
                    if cancer_type_col:
                        filt = filt[filt[cancer_type_col] == sel_cancer]

                    if filt.empty:
                        st.warning("No data found for this selection.")
                    else:
                        if len(sel_districts) == 1:
                            # Original single-district bar chart
                            row = filt.iloc[0]
                            age_counts = [row.get(c, 0) for c in avail_age_cols]
                            age_labels = [c.replace("Age ", "") for c in avail_age_cols]

                            fig = go.Figure(
                                go.Bar(
                                    x=age_labels,
                                    y=age_counts,
                                    marker_color=CANCER_COLORS.get(
                                        sel_cancer.lower(), "#457B9D"
                                    ),
                                    text=[f"{v:.0f}" for v in age_counts],
                                    textposition="outside",
                                )
                            )
                            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                            fig.update_layout(
                                title=f"{sel_cancer} Diagnoses by Age Group — {sel_districts[0]}",
                                xaxis_title="Age Band",
                                yaxis_title="Number of Diagnoses",
                                height=440,
                            )
                            st.plotly_chart(fig, use_container_width=True)

                            # Generate AI Insights
                            render_ai_insights(
                                pd.DataFrame(
                                    {"Age Band": age_labels, "Diagnoses": age_counts}
                                ),
                                f"Analyzing {sel_cancer} diagnoses by age group for district {sel_districts[0]}",
                                "tab_cancer_age_single",
                            )
                        else:
                            # Grouped bar chart comparison
                            melted_dist = filt.melt(
                                id_vars=[age_name_col],
                                value_vars=avail_age_cols,
                                var_name="Age Band Raw",
                                value_name="Diagnoses",
                            )
                            melted_dist["Age Band"] = melted_dist[
                                "Age Band Raw"
                            ].str.replace("Age ", "")

                            fig = px.bar(
                                melted_dist,
                                x="Age Band",
                                y="Diagnoses",
                                color=age_name_col,
                                barmode="group",
                                title=f"{sel_cancer} Diagnoses by Age Group — Comparison",
                                labels={
                                    "Diagnoses": "Number of Diagnoses",
                                    age_name_col: "District",
                                },
                                color_discrete_sequence=FLC26_QUALITATIVE,
                            )
                            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                            fig.update_layout(height=440, hovermode="x unified")
                            st.plotly_chart(fig, width="stretch")

                        # Show all districts for the selected cancer type (second viz)
                        st.subheader(f"All Districts — {sel_cancer} by Age Band")
                        all_cancer = (
                            top5_df[top5_df[cancer_type_col] == sel_cancer].copy()
                            if cancer_type_col
                            else top5_df.copy()
                        )
                        if age_name_col:
                            all_cancer = all_cancer.sort_values(
                                "All ages"
                                if "All ages" in all_cancer.columns
                                else avail_age_cols[-1],
                                ascending=False,
                            )
                        melted = (
                            all_cancer[[age_name_col] + avail_age_cols].melt(
                                id_vars=age_name_col,
                                var_name="Age Band",
                                value_name="Count",
                            )
                            if age_name_col
                            else pd.DataFrame()
                        )
                        if not melted.empty:
                            fig2 = px.bar(
                                melted,
                                x=age_name_col,
                                y="Count",
                                color="Age Band",
                                barmode="stack",
                                title=f"{sel_cancer} — All Districts, Stacked by Age Band",
                                color_discrete_sequence=px.colors.sequential.Viridis,
                            )
                            fig2.update_layout(**PLOTLY_LIGHT_LAYOUT)
                            fig2.update_layout(xaxis_tickangle=-45, height=500)
                            st.plotly_chart(fig2, width="stretch")

        # ── Tab 5: Regional Analysis ──────────────────────────────────────────────
        with tab_regional:
            st.subheader("Regional Cancer Analysis")
            st.info(
                "This tab combines region-wide visualizations to reveal high-level distribution, "
                "statistical significance, and cross-type correlations across the East of England."
            )

            # 1. Confidence Intervals
            st.write("### 📉 Cancer Rates with 95% Confidence Intervals")
            st.write(
                "Error bars show the 95% confidence interval (CI) for each district's overall standardised rate."
            )
            ci_lower = "95% lower confidence interval"
            ci_upper = "95% upper confidence interval"
            avail_ci = [
                c for c in [ci_lower, ci_upper, "Rate"] if c in overall_df.columns
            ]

            if len(avail_ci) < 3:
                st.warning("Confidence interval columns not found in dataset.")
            else:
                ci_df = (
                    overall_df[[name_col, "Rate", ci_lower, ci_upper]].dropna().copy()
                    if name_col
                    else overall_df[["Rate", ci_lower, ci_upper]].dropna().copy()
                )
                ci_df = ci_df.sort_values("Rate", ascending=False)

                ci_limit = st.slider(
                    "Districts to show in CI plot:",
                    5,
                    max(5, len(ci_df)),
                    20,
                    key="cancer_ra_ci_limit",
                )
                ci_df = ci_df.head(ci_limit)

                x_ci = (
                    ci_df[name_col].tolist()
                    if name_col
                    else ci_df.index.astype(str).tolist()
                )
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=x_ci,
                        y=ci_df["Rate"].tolist(),
                        error_y=dict(
                            type="data",
                            symmetric=False,
                            array=(ci_df[ci_upper] - ci_df["Rate"]).tolist(),
                            arrayminus=(ci_df["Rate"] - ci_df[ci_lower]).tolist(),
                            color="rgba(100,100,100,0.5)",
                        ),
                        mode="markers",
                        marker=dict(size=10, color="#E63946"),
                        name="Overall Rate",
                    )
                )
                fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                fig.update_layout(
                    title="Overall Standardised Cancer Rate with 95% CI",
                    xaxis_title="District",
                    yaxis_title="Rate (per 100,000)",
                    xaxis_tickangle=-45,
                    height=500,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Generate AI Insights
                render_ai_insights(
                    ci_df,
                    f"Analyzing overall standardised cancer rates with 95% CI for top {ci_limit} districts",
                    "tab_cancer_regional_ci",
                )

            st.divider()

            # 2. Cross-Type Heatmap
            st.write("### 🌡️ Cancer Type × District Heatmap")
            st.write(
                "Reveals geographic clusters where multiple cancer types have high age-standardised incidence rates."
            )
            avail_cancers = [c for c in CANCER_TYPES if c in overall_df.columns]
            hm_df = (
                overall_df[[name_col] + avail_cancers].dropna().set_index(name_col)
                if name_col
                else overall_df[avail_cancers].dropna()
            )

            sort_hm = st.selectbox(
                "Sort heatmap districts by:",
                sorted(avail_cancers),
                key="cancer_ra_sort_hm",
            )
            hm_df = hm_df.sort_values(sort_hm, ascending=False)

            fig = px.imshow(
                hm_df[avail_cancers].T,
                labels=dict(x="District", y="Cancer Type", color="Rate"),
                color_continuous_scale="YlOrRd",
                title="Incidence Rate Heatmap — Cancer Type × District",
                aspect="auto",
            )
            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
            fig.update_layout(height=360, xaxis_tickangle=-45)
            fig.update_traces(colorbar_title_text="Rate (per 100k)")
            st.plotly_chart(fig, use_container_width=True)

            # Generate AI Insights
            render_ai_insights(
                hm_df,
                f"Analyzing incidence rate heatmap sorted by {sort_hm}",
                "tab_cancer_regional_hm",
            )

            st.divider()

            # 3. Scatter Relationships
            st.write("### 🎯 Specific Cancer vs Overall Rate")
            st.write(
                "Scatter relationship showing how strongly a specific cancer type tracks with a district's overall oncology rate."
            )
            avail_cancers = [c for c in CANCER_TYPES if c in overall_df.columns]
            selected_specific = st.selectbox(
                "Select cancer type for scatter:",
                sorted(avail_cancers),
                key="cancer_ra_scatter_specific",
            )
            compare_df = overall_df.dropna(subset=["Rate", selected_specific]).copy()
            color_col = "ICB" if "ICB" in compare_df.columns else name_col
            fig = create_scatter_chart(
                compare_df,
                x_col="Rate",
                y_col=selected_specific,
                color_col=color_col,
                title=f"Overall Rate vs {selected_specific.capitalize()} Rate",
            )
            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
            fig.update_layout(
                xaxis_title="Overall Cancer Rate (per 100k)",
                yaxis_title=f"{selected_specific.capitalize()} Rate",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Generate AI Insights
            render_ai_insights(
                compare_df,
                f"Analyzing scatter relationship between overall rate and {selected_specific} rate",
                "tab_cancer_regional_scatter",
            )

        # ── Tab 6: Data Table ─────────────────────────────────────────────────────
        with tab_data:
            st.subheader("📋 Dataset Previews")
            preview_tab1, preview_tab2 = st.tabs(
                ["Incidence Overview", "Top 5 Cancers (Long)"]
            )
            with preview_tab1:
                st.dataframe(overall_df, width="stretch")
            with preview_tab2:
                if not top5_df.empty:
                    st.dataframe(top5_df, width="stretch")
                else:
                    st.info("Top-5 cancers dataset is not loaded.")


if __name__ == "__main__":
    render_cancer_trends()
