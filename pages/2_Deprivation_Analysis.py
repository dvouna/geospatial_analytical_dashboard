import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
import sys
import numpy as np
from pathlib import Path

from config import Config
from map_utils import load_overlay_dataframe
from visualizer import (
    create_scatter_chart,
    create_heatmap,
    FLC26_QUALITATIVE,
    PLOTLY_LIGHT_LAYOUT,
)
from gemini_queries import render_ai_insights
from utils.data_loader_cancer import get_cancer_overall_df

DATA_DIR = Path(__file__).parent.parent / "data"

DOMAIN_SHORT = {
    "Overall IMD Rank": "Overall IMD",
    "Income Rank": "Income",
    "Employment Rank": "Employment",
    "Education Skills and Training Rank": "Education",
    "Health Deprivation and Disability Rank": "Health",
    "Crime Rank": "Crime",
    "Barriers to Housing and Services Rank": "Housing",
    "Living Environment Rank": "Living Env.",
    "Income Deprivation Affecting Children Index (IDACI) Rank": "IDACI (Children)",
    "Income Deprivation Affecting Older People (IDAOPI) Rank": "IDAOPI (Older)",
}

EAST_OF_ENGLAND_PREFIX = "E0"  # All East of England LADs start with 'E0'


def render_deprivation_playground():
    try:
        st.set_page_config(
            page_title="Deprivation Analysis Playground",
            page_icon="📊",
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
        div[data-testid="stHorizontalBlock"]:has(.sidebar-marker) > div[data-testid="stColumn"]:last-child {
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
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 2px;
            margin-top: 0.2rem;
            line-height: 1.15;
        ">Deprivation Analysis Playground</div>
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
        ">Explore correlations and distribution patterns across IMD 2025 deprivation domains — across England and within the East of England region.</div>
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
        margin-bottom: 15px;
        margin-top: 5px;
    ">How to use this page
    - Use the tabs below to explore different deprivation visualizations.
    </div>.
    """,
        unsafe_allow_html=True,
    )
    with st.popover(
        "💡 Guide: Analyzing Deprivation Playground", use_container_width=True
    ):
        st.markdown(
            """
            **How to use the Deprivation Analysis Playground:**
            - **Rank System**: Deprivation is ranked where rank #1 is the **most deprived** in the UK, and higher rank numbers indicate less deprivation.
            - **Scatter Correlation**: Plot two deprivation domains (e.g., Income vs Health) to see their relationship.
            - **District Radar**: Compare a district's profile across all 8 sub-domains to the English average. The axes are inverted, meaning lines plotted further toward the edges represent **higher deprivation** on those sub-domains.
            - **East of England Analysis**: View regional box plots, domain heatmaps, and parallel coordinate graphs.
            - **District Comparison**: Directly compare up to 5 districts' raw or inverted ranks side-by-side.
            """
        )

    # ── Load data ──────────────────────────────────────────────────────────────
    try:
        df = load_overlay_dataframe(DATA_DIR / "iod_2025.csv")
    except FileNotFoundError:
        st.error("❌ `iod_2025.csv` not found in the data directory.")
        return
    except Exception as exc:
        print(f"[deprivation] Error loading deprivation data: {exc}", file=sys.stderr)
        st.error(
            "❌ Error loading deprivation data. Please contact the administrator."
            if not Config.DEBUG
            else f"❌ Error loading deprivation data: {exc}"
        )
        return

    try:
        gdf_dist = gpd.read_file(str(DATA_DIR / "base_gdf_1.geojson"))
        eoe_codes = set(gdf_dist["District Code"].dropna().unique())
        eoe_df = df[df["District Code"].isin(eoe_codes)].copy()
    except Exception as exc:
        st.warning(f"⚠️ Could not filter East of England districts: {exc}")
        eoe_df = df.copy()

    # ── Split page layout ──────────────────────────────────────────────────────
    col_main, col_sidebar = st.columns([7, 3])

    with col_sidebar:
        st.markdown("<div class='sidebar-marker'></div>", unsafe_allow_html=True)
        import importlib

        ra_module = importlib.import_module("pages.5_AI_Research_Assistant")
        ra_module.render_research_assistant_widget(key_suffix="dep_playground")

    with col_main:
        rank_cols = [c for c in df.columns if "Rank" in c]
        short_rank_cols = {
            c: DOMAIN_SHORT.get(c, c.replace(" Rank", "").strip()) for c in rank_cols
        }
        sorted_rank_cols = sorted(rank_cols, key=lambda c: short_rank_cols[c])

        # ── Tabs ───────────────────────────────────────────────────────────────────
        (
            tab_district,
            tab_region,
            tab_scatter,
            tab_dep_cancer,
            tab_table,
        ) = st.tabs(
            [
                "District-Level Analysis",
                "Regional Analysis",
                "Deprivation Subdomains",
                "Deprivation vs Cancer",
                "Data Table",
            ]
        )

        # ── Scatter ────────────────────────────────────────────────────────────────
        with tab_scatter:
            st.write(
                "This tab has 1 visualization. Use it to analyze the correlation between deprivation domains. A lower rank indicates higher deprivation."
            )

            st.markdown("#### 1. Correlation Between Deprivation Domains")
            col_x, col_y = st.columns(2)
            with col_x:
                x_var = st.selectbox(
                    "X-Axis:",
                    options=sorted_rank_cols,
                    format_func=lambda c: short_rank_cols[c],
                    index=sorted_rank_cols.index("Overall IMD Rank")
                    if "Overall IMD Rank" in sorted_rank_cols
                    else 0,
                    key="imd_s_x",
                )
            with col_y:
                y_var = st.selectbox(
                    "Y-Axis:",
                    options=sorted_rank_cols,
                    format_func=lambda c: short_rank_cols[c],
                    index=sorted_rank_cols.index("Income Rank")
                    if "Income Rank" in sorted_rank_cols
                    else min(1, len(sorted_rank_cols) - 1),
                    key="imd_s_y",
                )
            plot_df = df.dropna(subset=[x_var, y_var]).copy()
            color_col = next(
                (c for c in ["ICB", "District Name"] if c in df.columns),
                None,
            )
            fig = create_scatter_chart(
                plot_df,
                x_col=x_var,
                y_col=y_var,
                color_col=color_col,
                title=f"{short_rank_cols[x_var]} vs {short_rank_cols[y_var]}",
            )
            fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
            fig.update_layout(
                xaxis_title=short_rank_cols[x_var],
                yaxis_title=short_rank_cols[y_var],
            )
            st.plotly_chart(fig, use_container_width=True)

            # Generate AI Insights
            render_ai_insights(
                plot_df,
                f"Analyzing scatter correlation between {short_rank_cols[x_var]} and {short_rank_cols[y_var]}",
                "tab_dep_scatter",
            )

        # ── East of England Analysis ──────────────────────────────────────────────
        with tab_region:
            st.write(
                "This tab has 3 visualizations. Use them to analyze deprivation ranks for districts in the East of England. Hover on the charts to see the district names. A lower deprivation rank indicates higher deprivation."
            )

            # 1. Parallel coordinates
            st.write("#### 1. Parallel Coordinates - Regional Profile")
            st.markdown(
                "Each line represents an East of England district. Lines crossing similarly indicate shared typological patterns."
            )
            para_df = eoe_df[rank_cols].dropna().copy()
            para_df_renamed = para_df.rename(columns=short_rank_cols)
            short_labels = list(para_df_renamed.columns)
            imd_col_short = DOMAIN_SHORT.get("Overall IMD Rank", "Overall IMD")

            if para_df_renamed.empty:
                st.warning("No data available for Parallel Coordinates.")
            else:
                dims = [
                    dict(
                        range=[para_df_renamed[c].max(), para_df_renamed[c].min()],
                        label=c,
                        values=para_df_renamed[c],
                    )
                    for c in short_labels
                ]
                fig = go.Figure(
                    data=go.Parcoords(
                        line=dict(
                            color=para_df_renamed[imd_col_short],
                            colorscale="RdYlGn_r",
                            showscale=True,
                            cmin=para_df_renamed[imd_col_short].min(),
                            cmax=para_df_renamed[imd_col_short].max(),
                            colorbar=dict(title="IMD Rank<br>(low=deprived)"),
                        ),
                        dimensions=dims,
                    )
                )
                fig.update_layout(
                    title="Parallel Coordinates — Deprivation Ranks (East of England)",
                    height=540,
                    **PLOTLY_LIGHT_LAYOUT,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Generate AI Insights
                render_ai_insights(
                    para_df_renamed,
                    "Analyzing parallel coordinates of regional deprivation profiles in East of England",
                    "tab_dep_eoe_parallel",
                )

            st.divider()

            # 2. Box plots by domain
            st.write("#### 2. Box Plots - Rank Distribution per Deprivation Domain")
            st.markdown(
                "Distribution of deprivation ranks within the region. Narrow boxes indicate more uniform deprivation; wide boxes indicate higher regional disparity."
            )
            if eoe_df.empty:
                st.warning("No data available for Box Plots.")
            else:
                melted = eoe_df[rank_cols].copy().rename(columns=short_rank_cols)
                melted = melted.melt(var_name="Domain", value_name="Rank").dropna()

                # Order domains by median rank ascending (most deprived first)
                domain_order = (
                    melted.groupby("Domain")["Rank"]
                    .median()
                    .sort_values()
                    .index.tolist()
                )
                fig = px.box(
                    melted,
                    x="Domain",
                    y="Rank",
                    category_orders={"Domain": domain_order},
                    color="Domain",
                    title="Rank Distribution by Deprivation Domain (East of England districts)",
                    labels={"Rank": "Deprivation Rank (lower = more deprived)"},
                )
                fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                fig.update_layout(
                    xaxis_tickangle=-30,
                    showlegend=False,
                    height=500,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Generate AI Insights
                render_ai_insights(
                    melted,
                    "Analyzing rank distribution by deprivation domain across East of England",
                    "tab_dep_eoe_box",
                )

            st.divider()

            # 3. Correlation heatmap
            st.write("#### 3. Correlation Heatmap - Regional Deprivation Domains")
            st.markdown(
                "Heatmap showing the linear relationships between deprivation domains for East of England districts."
            )
            if eoe_df.empty:
                st.warning("No data available for Heatmap.")
            else:
                corr_df = eoe_df[rank_cols].rename(columns=short_rank_cols).dropna()
                fig = create_heatmap(
                    corr_df,
                    title="Deprivation Sub-Domain Correlation Matrix (East of England)",
                )
                st.plotly_chart(fig, use_container_width=True)

                # Generate AI Insights
                render_ai_insights(
                    corr_df,
                    "Analyzing deprivation sub-domain correlation matrix in East of England",
                    "tab_dep_eoe_corr",
                )

        # ── Tab 6: District Comparison ─────────────────────────────────────────────
        with tab_district:
            st.write(
                "This tab has 2 visualizations. Use them to analyze deprivation ranks for districts in the East of England."
            )

            st.write("#### 1. District Comparison")
            st.markdown(
                "Compare deprivation ranks for districts in the East of England."
            )
            name_col_imd = "District Name"
            districts_available = (
                df[name_col_imd].dropna().sort_values().tolist()
                if name_col_imd in df.columns
                else []
            )

            if not districts_available:
                st.warning("District name column not found.")
            else:
                col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
                with col_sel1:
                    selected_districts = st.multiselect(
                        "Select districts (up to 5):",
                        options=districts_available,
                        default=districts_available[:1],
                        max_selections=5,
                        key="imd_comp_districts",
                    )
                with col_sel2:
                    view_mode = st.radio(
                        "Rank display:",
                        [
                            "Raw Rank (lower = more deprived)",
                            "Inverted (higher = more deprived)",
                        ],
                        key="imd_comp_mode",
                    )
                with col_sel3:
                    domain_filter = st.selectbox(
                        "Filter domains:",
                        options=["All Domains", "Main Domains Only"]
                        + sorted(list(DOMAIN_SHORT.values())),
                        key="imd_comp_filter",
                    )

                if not selected_districts:
                    st.warning("⚠️ Please select at least one district to compare.")
                else:
                    # Filter and melt data for selected districts
                    comp_df = df[df[name_col_imd].isin(selected_districts)].copy()

                    long_df = comp_df[[name_col_imd] + rank_cols].melt(
                        id_vars=[name_col_imd],
                        value_vars=rank_cols,
                        var_name="Domain_Raw",
                        value_name="Rank",
                    )
                    long_df["Domain"] = long_df["Domain_Raw"].map(short_rank_cols)

                    # Filter domains if requested
                    if domain_filter == "Main Domains Only":
                        main_domains = [
                            DOMAIN_SHORT[c]
                            for c in rank_cols
                            if c
                            not in (
                                "Income Deprivation Affecting Children Index (IDACI) Rank",
                                "Income Deprivation Affecting Older People (IDAOPI) Rank",
                            )
                        ]
                        long_df = long_df[long_df["Domain"].isin(main_domains)]
                    elif domain_filter != "All Domains":
                        long_df = long_df[long_df["Domain"] == domain_filter]

                    # Max rank in dataset for inversion (usually 296)
                    max_rank = df[rank_cols].max().max()

                    # Compute rank representation based on mode
                    if "Inverted" in view_mode:
                        long_df["Value"] = max_rank - long_df["Rank"] + 1
                        y_axis_title = (
                            "Inverted Deprivation Rank (higher = more deprived)"
                        )
                    else:
                        long_df["Value"] = long_df["Rank"]
                        y_axis_title = "Raw Deprivation Rank (lower = more deprived)"

                    # Visualizations
                    palette_imd = FLC26_QUALITATIVE
                    if len(selected_districts) == 1:
                        # Single district horizontal bar chart
                        fig = px.bar(
                            long_df,
                            x="Value",
                            y="Domain",
                            color="Domain",
                            orientation="h",
                            title=f"Deprivation Domain Rankings for {selected_districts[0]}",
                            labels={
                                "Value": y_axis_title,
                                "Domain": "Deprivation Domain",
                            },
                            color_discrete_sequence=palette_imd,
                            category_orders={
                                "Domain": sorted(long_df["Domain"].unique())
                            },
                        )
                        # For raw rank, we want the lowest rank (most deprived) at the top/right, so we can invert the x-axis
                        if "Inverted" not in view_mode:
                            fig.update_layout(xaxis=dict(autorange="reversed"))
                        fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                        fig.update_layout(
                            height=500,
                            showlegend=False,
                            yaxis={"categoryorder": "total ascending"},
                            hovermode="y unified",
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Generate AI Insights
                        render_ai_insights(
                            long_df,
                            f"Analyzing deprivation domain rankings for {selected_districts[0]}",
                            "tab_dep_comp_single",
                        )
                    else:
                        # Multi-district grouped bar chart comparison
                        fig = px.bar(
                            long_df,
                            x="Domain",
                            y="Value",
                            color=name_col_imd,
                            barmode="group",
                            title=f"District Deprivation Comparison ({view_mode})",
                            labels={
                                "Value": y_axis_title,
                                "Domain": "Deprivation Domain",
                                name_col_imd: "District",
                            },
                            color_discrete_sequence=palette_imd,
                        )
                        if "Inverted" not in view_mode:
                            fig.update_layout(yaxis=dict(autorange="reversed"))
                        fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
                        fig.update_layout(
                            height=520,
                            xaxis_tickangle=-30,
                            hovermode="x unified",
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Generate AI Insights
                        render_ai_insights(
                            long_df,
                            f"Comparing deprivation rankings across districts: {', '.join(selected_districts)} (Mode: {view_mode})",
                            "tab_dep_comp_multi",
                        )

                    # Comparison Data Table
                    st.write("### Comparison Data Table")
                    pivot_df = long_df.pivot(
                        index="Domain", columns=name_col_imd, values="Rank"
                    )

                    st.dataframe(
                        pivot_df.style.background_gradient(
                            cmap="RdYlGn", axis=None, vmin=1, vmax=max_rank
                        ).format("{:,.0f}"),
                        width="stretch",
                    )

                    st.divider()

                    # ── Radar chart comparison ─────────────────────────────────────────
                    st.write("#### 2. District Deprivation Radar — vs England Average")
                    st.markdown(
                        "The radar chart below displays ranks across all 8 IMD domains. Use it to compare ranks "
                        "between the selected districts, or against the England median (rank ≈ 148 of 296)."
                        "For each domain, a lower rank indicates a higher level of deprivation."
                    )

                    # Offer only the 8 main sub-domains (not IDACI/IDAOPI to keep readable)
                    radar_domains = [
                        c
                        for c in rank_cols
                        if c
                        not in (
                            "Income Deprivation Affecting Children Index (IDACI) Rank",
                            "Income Deprivation Affecting Older People (IDAOPI) Rank",
                        )
                    ]
                    radar_labels = [DOMAIN_SHORT.get(c, c) for c in radar_domains]

                    # Filter comparison districts specifically for radar (limit to 3 for readability)
                    radar_selected = selected_districts[:3]
                    if len(selected_districts) > 3:
                        st.warning(
                            "⚠️ Radar chart comparison is limited to the first 3 selected districts for readability."
                        )

                    max_radar_rank = df[radar_domains].max().max()
                    eng_avg = df[radar_domains].median().tolist()

                    def invert(vals):
                        return [max_radar_rank - v + 1 for v in vals]

                    fig_radar = go.Figure()
                    # England average baseline
                    avg_vals = invert(eng_avg) + [invert(eng_avg)[0]]
                    theta = radar_labels + [radar_labels[0]]
                    fig_radar.add_trace(
                        go.Scatterpolar(
                            r=avg_vals,
                            theta=theta,
                            fill="toself",
                            name="England Average",
                            line_color="rgba(150,150,150,0.6)",
                            fillcolor="rgba(200,200,200,0.2)",
                        )
                    )

                    colors = ["#E63946", "#2A9D8F", "#E9C46A"]
                    fill_colors = [
                        "rgba(230, 57, 70, 0.15)",
                        "rgba(42, 157, 143, 0.15)",
                        "rgba(233, 196, 106, 0.15)",
                    ]
                    for i, district in enumerate(radar_selected):
                        row = df[df[name_col_imd] == district]
                        if row.empty:
                            continue
                        vals = row[radar_domains].iloc[0].tolist()
                        inv_vals = invert(vals) + [invert(vals)[0]]
                        fig_radar.add_trace(
                            go.Scatterpolar(
                                r=inv_vals,
                                theta=theta,
                                fill="toself",
                                name=district,
                                line_color=colors[i % len(colors)],
                                fillcolor=fill_colors[i % len(colors)],
                            )
                        )

                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, max_radar_rank])
                        ),
                        showlegend=True,
                        title="Deprivation Profile (larger area = more deprived on that domain)",
                        height=520,
                        **PLOTLY_LIGHT_LAYOUT,
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
                    st.caption(
                        "Axes are inverted: rank #1 (most deprived) plots furthest out; "
                        "rank #296 (least deprived) plots at the centre."
                    )

                    # Generate AI Insights for Radar
                    render_ai_insights(
                        df[df[name_col_imd].isin(radar_selected)],
                        f"Analyzing radar chart of deprivation domains for districts: {', '.join(radar_selected)}",
                        "tab_dep_radar",
                    )

        # ── Deprivation-Cancer Correlation ────────────────────────────────────────
        with tab_dep_cancer:
            st.write("#### 1. Deprivation vs Cancer Incidence")
            st.markdown(
                "Use the chart below to explore the relationships between deprivation ranks "
                "and overall cancer incidence rates across the East of England. Each point represents one district. Hover over the points in the chart to view the district name, overall deprivation rank and overall cancer rate."
            )
            _render_deprivation_cancer_scatter(df)

        # ── Data table ────────────────────────────────────────────────────────────
        with tab_table:
            st.subheader("Dataset Preview")
            st.dataframe(df, width="stretch")


def _render_deprivation_cancer_scatter(imd_df: pd.DataFrame) -> None:
    """Scatter: IMD Overall Rank vs Overall Cancer Rate, one point per district."""
    try:
        cancer_df = get_cancer_overall_df(year_filter="all")
    except Exception:
        cancer_df = pd.DataFrame()

    if imd_df.empty or cancer_df.empty:
        st.info("Both deprivation and cancer datasets are required for this chart.")
        return

    imd_code_col = "District Code"
    imd_name_col = "District Name"
    imd_rank_col = "Overall IMD Rank"
    cancer_code_col = "District Code"
    cancer_name_col = "District Name"
    cancer_rate_col = "Rate"

    # Clean and merge on district code
    imd_clean = imd_df[[imd_code_col, imd_name_col, imd_rank_col]].dropna()
    cancer_clean = cancer_df[[cancer_code_col, cancer_name_col, cancer_rate_col]].copy()
    cancer_clean[cancer_rate_col] = pd.to_numeric(
        cancer_clean[cancer_rate_col].astype(str).str.replace(",", ""), errors="coerce"
    )
    cancer_clean = cancer_clean.dropna(subset=[cancer_rate_col])

    merged = pd.merge(
        imd_clean,
        cancer_clean,
        left_on=imd_code_col,
        right_on=cancer_code_col,
        how="inner",
        suffixes=("", "_cancer"),
    )

    if merged.empty:
        st.warning("No matching districts found between IMD and cancer datasets.")
        return

    fig = go.Figure()

    # 1. Add Scatter trace for districts
    fig.add_trace(
        go.Scatter(
            x=merged[imd_rank_col].tolist(),
            y=merged[cancer_rate_col].tolist(),
            mode="markers",
            name="Districts",
            text=merged[imd_name_col].tolist(),
            hovertemplate="<b>%{text}</b><br>IMD Rank: %{x}<br>Cancer Rate: %{y:.1f}<extra></extra>",
            marker=dict(
                size=9,
                color="#E63946",
                opacity=0.8,
                line=dict(width=1, color="DarkSlateGrey"),
            ),
        )
    )

    # 2. Add OLS regression line trace using numpy
    try:
        x_vals = merged[imd_rank_col].dropna().values
        y_vals = merged[cancer_rate_col].dropna().values
        if len(x_vals) > 1:
            slope, intercept = np.polyfit(x_vals, y_vals, 1)
            x_line = np.array([x_vals.min(), x_vals.max()])
            y_line = slope * x_line + intercept
            fig.add_trace(
                go.Scatter(
                    x=x_line.tolist(),
                    y=y_line.tolist(),
                    mode="lines",
                    name="OLS Trendline",
                    line=dict(color="#2A9D8F", width=2, dash="dash"),
                    hovertemplate="Trendline<extra></extra>",
                )
            )
    except Exception:
        pass

    fig.update_layout(**PLOTLY_LIGHT_LAYOUT)
    fig.update_layout(
        title="Deprivation Rank vs Cancer Incidence Rate — East of England Districts",
        xaxis_title="IMD Overall Rank (lower = more deprived)",
        yaxis_title="Overall Cancer Rate (per 100,000)",
        height=480,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Trendline = OLS regression. A negative slope would indicate that more deprived districts "
        "(lower rank number) tend to have higher cancer rates."
    )
    # Generate AI Insights
    render_ai_insights(
        merged,
        "Analyzing scatter correlation between IMD Overall Rank and Cancer Incidence Rate",
        "tab_dep_cancer_scatter",
    )


if __name__ == "__main__":
    render_deprivation_playground()
