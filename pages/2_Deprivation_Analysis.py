import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pathlib import Path

from map_utils import load_overlay_dataframe
from visualizer import create_scatter_chart, create_heatmap, display_summary_statistics

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

    st.title("📊 Deprivation Analysis Playground")
    st.write(
        "Explore correlations and distribution patterns across IMD 2025 "
        "deprivation domains — across England and within the East of England region."
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

    display_summary_statistics(df)
    st.divider()

    rank_cols = [c for c in df.columns if "Rank" in c]
    short_rank_cols = {c: DOMAIN_SHORT.get(c, c.replace(" Rank", "").strip()) for c in rank_cols}

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_scatter, tab_radar, tab_parallel, tab_box, tab_heatmap, tab_table = st.tabs([
        "🔍 Scatter",
        "🕸️ District Radar",
        "〰️ Parallel Coords",
        "📦 Domain Box Plots",
        "🌡️ Correlation Heatmap",
        "📋 Data Table",
    ])

    # ── Scatter ────────────────────────────────────────────────────────────────
    with tab_scatter:
        st.subheader("Correlation Between Deprivation Domains")
        st.info("💡 Lower rank = higher deprivation in the UK (rank #1 = most deprived).")
        col_x, col_y = st.columns(2)
        with col_x:
            x_var = st.selectbox("X-Axis:", options=rank_cols,
                                 format_func=lambda c: short_rank_cols[c],
                                 index=0, key="imd_s_x")
        with col_y:
            y_var = st.selectbox("Y-Axis:", options=rank_cols,
                                 format_func=lambda c: short_rank_cols[c],
                                 index=min(1, len(rank_cols) - 1), key="imd_s_y")
        plot_df = df.dropna(subset=[x_var, y_var]).copy()
        color_col = next(
            (c for c in ["ICB", "Local Authority District name (2024)"] if c in df.columns), None
        )
        fig = create_scatter_chart(
            plot_df, x_col=x_var, y_col=y_var, color_col=color_col,
            title=f"{short_rank_cols[x_var]} vs {short_rank_cols[y_var]}"
        )
        fig.update_layout(xaxis_title=short_rank_cols[x_var], yaxis_title=short_rank_cols[y_var])
        st.plotly_chart(fig, use_container_width=True)

    # ── Radar chart ───────────────────────────────────────────────────────────
    with tab_radar:
        st.subheader("District Deprivation Radar — vs England Average")
        st.info(
            "Displays a district's rank across all domains on a radar chart. "
            "Compare against the England median (rank ≈ 148 of 296). "
            "Districts plotted further toward the centre are **more deprived** on that domain."
        )

        name_col_imd = "Local Authority District name (2024)"
        code_col_imd = "Local Authority District code (2024)"

        # Offer only the 8 main sub-domains (not IDACI/IDAOPI to keep readable)
        radar_domains = [c for c in rank_cols if c not in (
            "Income Deprivation Affecting Children Index (IDACI) Rank",
            "Income Deprivation Affecting Older People (IDAOPI) Rank",
        )]
        radar_labels = [DOMAIN_SHORT.get(c, c) for c in radar_domains]

        districts_available = df[name_col_imd].dropna().sort_values().tolist() if name_col_imd in df.columns else []

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
            fig.add_trace(go.Scatterpolar(
                r=avg_vals, theta=theta,
                fill="toself", name="England Average",
                line_color="rgba(150,150,150,0.6)",
                fillcolor="rgba(200,200,200,0.2)",
            ))

            colors = ["#E63946", "#2A9D8F", "#E9C46A"]
            for i, district in enumerate(selected_districts):
                row = df[df[name_col_imd] == district]
                if row.empty:
                    continue
                vals = row[radar_domains].iloc[0].tolist()
                inv_vals = invert(vals) + [invert(vals)[0]]
                fig.add_trace(go.Scatterpolar(
                    r=inv_vals, theta=theta,
                    fill="toself", name=district,
                    line_color=colors[i % len(colors)],
                    fillcolor=colors[i % len(colors)].replace(")", ",0.15)").replace("rgb", "rgba") if "rgb" in colors[i % len(colors)] else colors[i % len(colors)] + "26",
                ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max_rank])),
                showlegend=True,
                title="Deprivation Profile (larger area = more deprived on that domain)",
                height=520,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Axes are inverted: rank #1 (most deprived) plots furthest out; "
                "rank #296 (least deprived) plots at the centre."
            )

    # ── Parallel coordinates ──────────────────────────────────────────────────
    with tab_parallel:
        st.subheader("Parallel Coordinates — Multi-Domain Deprivation Profiles")
        st.info(
            "Each line is a district. Lines that cross similarly reveal typological clusters. "
            "Colour = Overall IMD Rank (darker = more deprived)."
        )
        para_df = df[rank_cols].dropna().copy()
        para_df_renamed = para_df.rename(columns=short_rank_cols)
        short_labels = list(para_df_renamed.columns)
        imd_col_short = DOMAIN_SHORT.get("Index of Multiple Deprivation (IMD) Rank", "Overall IMD")

        dims = [
            dict(range=[para_df_renamed[c].max(), para_df_renamed[c].min()],
                 label=c, values=para_df_renamed[c])
            for c in short_labels
        ]
        fig = go.Figure(data=go.Parcoords(
            line=dict(
                color=para_df_renamed[imd_col_short],
                colorscale="RdYlGn_r",
                showscale=True,
                cmin=para_df_renamed[imd_col_short].min(),
                cmax=para_df_renamed[imd_col_short].max(),
                colorbar=dict(title="IMD Rank<br>(low=deprived)"),
            ),
            dimensions=dims,
        ))
        fig.update_layout(
            title="Parallel Coordinates — Deprivation Ranks Across All Domains",
            height=540,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Box plots by domain ───────────────────────────────────────────────────
    with tab_box:
        st.subheader("Rank Distribution per Deprivation Domain")
        st.info(
            "How spread out are the deprivation ranks for each domain across all 296 districts? "
            "Narrow boxes = more uniform distribution; wide boxes = high inequality across districts."
        )
        melted = df[rank_cols].copy().rename(columns=short_rank_cols)
        melted = melted.melt(var_name="Domain", value_name="Rank").dropna()

        # Order domains by median rank ascending (most deprived first)
        domain_order = (
            melted.groupby("Domain")["Rank"].median().sort_values().index.tolist()
        )
        fig = px.box(
            melted, x="Domain", y="Rank",
            category_orders={"Domain": domain_order},
            color="Domain",
            title="Rank Distribution by Deprivation Domain (all 296 English districts)",
            labels={"Rank": "Deprivation Rank (lower = more deprived)"},
        )
        fig.update_layout(
            xaxis_tickangle=-30,
            showlegend=False,
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Correlation heatmap ───────────────────────────────────────────────────
    with tab_heatmap:
        st.subheader("Correlation Heatmap — All Deprivation Domains")
        st.write("Strength of linear relationship between deprivation sub-domains.")
        corr_df = df[rank_cols].rename(columns=short_rank_cols).dropna()
        fig = create_heatmap(corr_df, title="Deprivation Sub-Domain Correlation Matrix")
        st.plotly_chart(fig, use_container_width=True)

    # ── Data table ────────────────────────────────────────────────────────────
    with tab_table:
        st.subheader("📋 Dataset Preview")
        st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    render_deprivation_playground()
