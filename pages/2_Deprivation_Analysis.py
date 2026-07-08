import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from map_utils import load_overlay_dataframe
from visualizer import (
    create_scatter_chart,
    create_heatmap,
    FLC26_QUALITATIVE,
    PLOTLY_LIGHT_LAYOUT,
)

DATA_DIR = Path(__file__).parent.parent / "data"

DOMAIN_SHORT = {
    "Index of Multiple Deprivation (IMD) Rank": "Overall IMD",
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

    # ── Load data ──────────────────────────────────────────────────────────────
    try:
        df = load_overlay_dataframe(DATA_DIR / "iod_2025.csv")
    except FileNotFoundError:
        st.error("❌ `iod_2025.csv` not found in the data directory.")
        return
    except Exception as exc:
        st.error(f"❌ Error loading deprivation data: {exc}")
        return

    try:
        local_df = load_overlay_dataframe(DATA_DIR / "local_districts.csv")
        eoe_codes = set(local_df["LAD24CD"].dropna().unique())
        eoe_df = df[df["Local Authority District code (2024)"].isin(eoe_codes)].copy()
    except Exception as exc:
        st.warning(f"⚠️ Could not load or filter East of England districts: {exc}")
        eoe_df = df.copy()

    # ── Split page layout ──────────────────────────────────────────────────────
    col_main, col_sidebar = st.columns([7, 3])

    with col_sidebar:
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
            tab_scatter,
            tab_radar,
            tab_eoe,
            tab_comp,
            tab_table,
        ) = st.tabs(
            [
                "🔍 Scatter",
                "🕸️ District Radar",
                "📈 East of England Analysis",
                "⚔️ District Comparison",
                "📋 Data Table",
            ]
        )

        # ── Scatter ────────────────────────────────────────────────────────────────
        with tab_scatter:
            st.subheader("Correlation Between Deprivation Domains")
            st.info(
                "💡 Lower rank = higher deprivation in the UK (rank #1 = most deprived)."
            )
            col_x, col_y = st.columns(2)
            with col_x:
                x_var = st.selectbox(
                    "X-Axis:",
                    options=sorted_rank_cols,
                    format_func=lambda c: short_rank_cols[c],
                    index=sorted_rank_cols.index("Index of Multiple Deprivation (IMD) Rank") if "Index of Multiple Deprivation (IMD) Rank" in sorted_rank_cols else 0,
                    key="imd_s_x",
                )
            with col_y:
                y_var = st.selectbox(
                    "Y-Axis:",
                    options=sorted_rank_cols,
                    format_func=lambda c: short_rank_cols[c],
                    index=sorted_rank_cols.index("Income Rank") if "Income Rank" in sorted_rank_cols else min(1, len(sorted_rank_cols) - 1),
                    key="imd_s_y",
                )
            plot_df = df.dropna(subset=[x_var, y_var]).copy()
            color_col = next(
                (
                    c
                    for c in ["ICB", "Local Authority District name (2024)"]
                    if c in df.columns
                ),
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
            st.plotly_chart(fig, width="stretch")

        # ── Radar chart ───────────────────────────────────────────────────────────
        with tab_radar:
            st.subheader("District Deprivation Radar — vs England Average")
            st.info(
                "Displays a district's rank across all domains on a radar chart. "
                "Compare against the England median (rank ≈ 148 of 296). "
                "Districts plotted further toward the centre are **more deprived** on that domain."
            )

            name_col_imd = "Local Authority District name (2024)"

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

            districts_available = (
                df[name_col_imd].dropna().sort_values().tolist()
                if name_col_imd in df.columns
                else []
            )

            if not districts_available:
                st.warning("District name column not found.")
            else:
                selected_districts = st.multiselect(
                    "Select up to 3 districts to compare:",
                    options=districts_available,
                    default=districts_available[:1],
                    max_selections=3,
                    key="imd_radar_districts",
                )

                max_rank = df[radar_domains].max().max()
                # England average = median rank ≈ halfway
                eng_avg = df[radar_domains].median().tolist()

                # Invert so that MORE deprived = larger on chart (more visible)
                def invert(vals):
                    return [max_rank - v + 1 for v in vals]

                fig = go.Figure()
                # England average baseline
                avg_vals = invert(eng_avg) + [invert(eng_avg)[0]]
                theta = radar_labels + [radar_labels[0]]
                fig.add_trace(
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
                for i, district in enumerate(selected_districts):
                    row = df[df[name_col_imd] == district]
                    if row.empty:
                        continue
                    vals = row[radar_domains].iloc[0].tolist()
                    inv_vals = invert(vals) + [invert(vals)[0]]
                    fig.add_trace(
                        go.Scatterpolar(
                            r=inv_vals,
                            theta=theta,
                            fill="toself",
                            name=district,
                            line_color=colors[i % len(colors)],
                            fillcolor=fill_colors[i % len(colors)],
                        )
                    )

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, max_rank])),
                    showlegend=True,
                    title="Deprivation Profile (larger area = more deprived on that domain)",
                    height=520,
                    **PLOTLY_LIGHT_LAYOUT
                )
                st.plotly_chart(fig, width="stretch")
                st.caption(
                    "Axes are inverted: rank #1 (most deprived) plots furthest out; "
                    "rank #296 (least deprived) plots at the centre."
                )

        # ── East of England Analysis ──────────────────────────────────────────────
        with tab_eoe:
            st.subheader("📈 East of England Regional Analysis")
            st.info(
                "This section analyzes deprivation ranks and correlations specifically for the "
                "45 local authority districts in the East of England region."
            )

            # 1. Parallel coordinates
            st.write("### 〰️ Parallel Coordinates — Regional Deprivation Profiles")
            st.write("Each line represents an East of England district. Lines crossing similarly indicate shared typological patterns.")
            para_df = eoe_df[rank_cols].dropna().copy()
            para_df_renamed = para_df.rename(columns=short_rank_cols)
            short_labels = list(para_df_renamed.columns)
            imd_col_short = DOMAIN_SHORT.get(
                "Index of Multiple Deprivation (IMD) Rank", "Overall IMD"
            )

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
                    **PLOTLY_LIGHT_LAYOUT
                )
                st.plotly_chart(fig, width="stretch")

            st.divider()

            # 2. Box plots by domain
            st.write("### 📦 Rank Distribution per Deprivation Domain (East of England)")
            st.write("Distribution of deprivation ranks within the region. Narrow boxes = more uniform; wide boxes = higher regional disparity.")
            if eoe_df.empty:
                st.warning("No data available for Box Plots.")
            else:
                melted = eoe_df[rank_cols].copy().rename(columns=short_rank_cols)
                melted = melted.melt(var_name="Domain", value_name="Rank").dropna()

                # Order domains by median rank ascending (most deprived first)
                domain_order = (
                    melted.groupby("Domain")["Rank"].median().sort_values().index.tolist()
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
                st.plotly_chart(fig, width="stretch")

            st.divider()

            # 3. Correlation heatmap
            st.write("### 🌡️ Correlation Heatmap — Regional Deprivation Domains")
            st.write("Strength of linear relationship between deprivation domains across East of England districts.")
            if eoe_df.empty:
                st.warning("No data available for Heatmap.")
            else:
                corr_df = eoe_df[rank_cols].rename(columns=short_rank_cols).dropna()
                fig = create_heatmap(
                    corr_df, title="Deprivation Sub-Domain Correlation Matrix (East of England)"
                )
                st.plotly_chart(fig, width="stretch")

        # ── Tab 6: District Comparison ─────────────────────────────────────────────
        with tab_comp:
            st.subheader("⚔️ District Comparison")
            st.info(
                "Select and compare deprivation domain rankings across districts. "
                "You can select up to 5 districts for comparison."
            )

            name_col_imd = "Local Authority District name (2024)"
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
                        st.plotly_chart(fig, width="stretch")
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
                            height=520, xaxis_tickangle=-30, hovermode="x unified",
                        )
                        st.plotly_chart(fig, width="stretch")

                    # Comparison Data Table
                    st.write("### 📋 Comparison Data Table")
                    pivot_df = long_df.pivot(
                        index="Domain", columns=name_col_imd, values="Rank"
                    )

                    st.dataframe(
                        pivot_df.style.background_gradient(
                            cmap="RdYlGn", axis=None, vmin=1, vmax=max_rank
                        ).format("{:,.0f}"),
                        width="stretch",
                    )

        # ── Data table ────────────────────────────────────────────────────────────
        with tab_table:
            st.subheader("📋 Dataset Preview")
            st.dataframe(df, width="stretch")


if __name__ == "__main__":
    render_deprivation_playground()
