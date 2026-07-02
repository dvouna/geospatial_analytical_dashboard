import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from map_utils import load_overlay_dataframe
from visualizer import create_bar_chart, create_scatter_chart, display_summary_statistics

DATA_DIR = Path(__file__).parent.parent / "data"

CANCER_TYPES = ["breast", "bowel", "lung", "prostate", "skin"]
CANCER_COLORS = {
    "breast": "#E63946",
    "bowel": "#457B9D",
    "lung": "#2A9D8F",
    "prostate": "#E9C46A",
    "skin": "#F4A261",
}
AGE_BANDS = ["Age 00 to 24", "Age 25 to 49", "Age 50 to 59", "Age 60 to 69", "Age 70 to 79", "Age 80 and over"]


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

    st.title("🎗️ Cancer Trends Analysis Playground")
    st.write("Compare oncology rates, age profiles, confidence intervals, and cancer type compositions across East of England districts.")

    # ── Load datasets ──────────────────────────────────────────────────────────
    try:
        overall_df = load_overlay_dataframe(DATA_DIR / "overall_incidence.csv", index_col="fid")
    except FileNotFoundError:
        st.error("❌ `overall_incidence.csv` not found.")
        overall_df = pd.DataFrame()
    except Exception as exc:
        st.error(f"❌ Error loading overall cancer data: {exc}")
        overall_df = pd.DataFrame()

    try:
        top5_df = load_overlay_dataframe(DATA_DIR / "top_5_cancers.csv", index_col="fid")
    except FileNotFoundError:
        st.error("❌ `top_5_cancers.csv` not found.")
        top5_df = pd.DataFrame()
    except Exception as exc:
        st.error(f"❌ Error loading top-5 cancers data: {exc}")
        top5_df = pd.DataFrame()

    if overall_df.empty:
        st.warning("Overall Cancer data unavailable.")
        return

    # Clean numerics
    numeric_overall = CANCER_TYPES + ["Rate", "Total_incidence",
                                       "95% lower confidence interval",
                                       "95% upper confidence interval"]
    overall_df = _clean_numeric(overall_df, numeric_overall)
    if not top5_df.empty:
        top5_df = _clean_numeric(top5_df, AGE_BANDS + ["All ages"])

    display_summary_statistics(overall_df)
    st.divider()

    name_col = next(
        (c for c in ["Geography name ", "Geography name"] if c in overall_df.columns), None
    )

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_bar, tab_composition, tab_age, tab_ci, tab_heatmap, tab_scatter, tab_data = st.tabs([
        "📊 Compare Rates",
        "🥧 Type Composition",
        "🧒 Age Profiles",
        "📉 Confidence Intervals",
        "🌡️ Cross-Type Heatmap",
        "🎯 Scatter Relationships",
        "📋 Data Table",
    ])

    # ── Tab 1: Bar chart ───────────────────────────────────────────────────────
    with tab_bar:
        st.subheader("Compare Cancer Incidence Rates by District")
        rate_cols = {
            "Overall Standardised Rate": "Rate",
            "Total Incidence Count": "Total_incidence",
            "Breast Cancer Rate": "breast",
            "Bowel Cancer Rate": "bowel",
            "Lung Cancer Rate": "lung",
            "Prostate Cancer Rate": "prostate",
            "Skin Cancer Rate": "skin",
        }
        c1, c2 = st.columns(2)
        with c1:
            selected_label = st.selectbox("Y-Axis Metric:", list(rate_cols.keys()), key="c_t1_metric")
            metric_field = rate_cols[selected_label]
        with c2:
            sort_order = st.selectbox("Sort:", ["Highest to Lowest", "Lowest to Highest"], key="c_t1_sort")

        plot_df = overall_df.dropna(subset=[metric_field]).copy()
        ascending = sort_order == "Lowest to Highest"
        plot_df = plot_df.sort_values(by=metric_field, ascending=ascending)
        limit = st.slider("Districts to display:", 5, max(5, len(plot_df)), 15, key="c_t1_limit")
        show_df = plot_df.tail(limit) if sort_order == "Highest to Lowest" else plot_df.head(limit)
        show_df = show_df.sort_values(by=metric_field, ascending=not ascending)
        fig = create_bar_chart(show_df, x_col=name_col, y_col=metric_field,
                               title=f"{selected_label} — Top {limit} Districts")
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: Stacked composition ─────────────────────────────────────────────
    with tab_composition:
        st.subheader("Cancer Type Composition by District")
        st.info(
            "Stacked bars show how each district's total incidence is composed "
            "across the 5 cancer types. Toggle between proportional (%) and absolute counts."
        )
        avail_cancers = [c for c in CANCER_TYPES if c in overall_df.columns]
        view_mode = st.radio("View mode:", ["Proportional (%)", "Absolute (count)"],
                             horizontal=True, key="c_t2_mode")
        sort_by_t2 = st.selectbox("Sort districts by:", avail_cancers + ["Overall Rate"],
                                  key="c_t2_sort")

        comp_df = overall_df[[name_col] + avail_cancers + ["Rate"]].dropna().copy() if name_col else overall_df[avail_cancers + ["Rate"]].dropna().copy()
        sort_c = sort_by_t2 if sort_by_t2 != "Overall Rate" else "Rate"
        if sort_c in comp_df.columns:
            comp_df = comp_df.sort_values(sort_c, ascending=False)

        if view_mode == "Proportional (%)":
            totals = comp_df[avail_cancers].sum(axis=1).replace(0, float("nan"))
            for c in avail_cancers:
                comp_df[c] = comp_df[c] / totals * 100
            y_label = "Share of Total Incidence (%)"
        else:
            y_label = "Incidence Count"

        x_vals = comp_df[name_col].tolist() if name_col else comp_df.index.astype(str).tolist()
        fig = go.Figure()
        for cancer in avail_cancers:
            fig.add_trace(go.Bar(
                name=cancer.capitalize(),
                x=x_vals,
                y=comp_df[cancer].tolist(),
                marker_color=CANCER_COLORS.get(cancer, None),
            ))
        fig.update_layout(
            barmode="stack",
            title="Cancer Type Composition by District",
            xaxis_title="District",
            yaxis_title=y_label,
            xaxis_tickangle=-45,
            height=520,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 3: Age-band profiles ───────────────────────────────────────────────
    with tab_age:
        st.subheader("Age-Band Diagnosis Profiles")
        st.info(
            "Breakdown of cancer diagnoses across 6 age bands for a selected district and cancer type. "
            "Useful for targeting age-specific early-detection campaigns."
        )
        if top5_df.empty:
            st.warning("⚠️ `top_5_cancers.csv` not available — age profiles cannot be shown.")
        else:
            age_name_col = next(
                (c for c in ["Geography name ", "Geography name"] if c in top5_df.columns), None
            )
            cancer_type_col = "Cancer Type" if "Cancer Type" in top5_df.columns else None

            ca, cb = st.columns(2)
            with ca:
                districts_list = sorted(top5_df[age_name_col].dropna().unique().tolist()) if age_name_col else []
                sel_district = st.selectbox("Select district:", districts_list, key="c_t3_district")
            with cb:
                cancers_list = sorted(top5_df[cancer_type_col].dropna().unique().tolist()) if cancer_type_col else CANCER_TYPES
                sel_cancer = st.selectbox("Select cancer type:", cancers_list, key="c_t3_cancer")

            avail_age_cols = [c for c in AGE_BANDS if c in top5_df.columns]
            filt = top5_df.copy()
            if age_name_col:
                filt = filt[filt[age_name_col] == sel_district]
            if cancer_type_col:
                filt = filt[filt[cancer_type_col] == sel_cancer]

            if filt.empty:
                st.warning("No data found for this selection.")
            else:
                row = filt.iloc[0]
                age_counts = [row.get(c, 0) for c in avail_age_cols]
                age_labels = [c.replace("Age ", "") for c in avail_age_cols]

                fig = go.Figure(go.Bar(
                    x=age_labels,
                    y=age_counts,
                    marker_color=CANCER_COLORS.get(sel_cancer.lower(), "#457B9D"),
                    text=[f"{v:.0f}" for v in age_counts],
                    textposition="outside",
                ))
                fig.update_layout(
                    title=f"{sel_cancer} Diagnoses by Age Group — {sel_district}",
                    xaxis_title="Age Band",
                    yaxis_title="Number of Diagnoses",
                    height=440,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Show all districts for the selected cancer type
                st.subheader(f"All Districts — {sel_cancer} by Age Band")
                all_cancer = top5_df[top5_df[cancer_type_col] == sel_cancer].copy() if cancer_type_col else top5_df.copy()
                if age_name_col:
                    all_cancer = all_cancer.sort_values("All ages" if "All ages" in all_cancer.columns else avail_age_cols[-1], ascending=False)
                melted = all_cancer[[age_name_col] + avail_age_cols].melt(
                    id_vars=age_name_col, var_name="Age Band", value_name="Count"
                ) if age_name_col else pd.DataFrame()
                if not melted.empty:
                    fig2 = px.bar(
                        melted, x=age_name_col, y="Count", color="Age Band",
                        barmode="stack",
                        title=f"{sel_cancer} — All Districts, Stacked by Age Band",
                        color_discrete_sequence=px.colors.sequential.Viridis,
                    )
                    fig2.update_layout(xaxis_tickangle=-45, height=500)
                    st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 4: Confidence intervals ────────────────────────────────────────────
    with tab_ci:
        st.subheader("Cancer Rates with 95% Confidence Intervals")
        st.info(
            "Error bars show the 95% CI for each district's overall standardised rate. "
            "Overlapping intervals mean differences may not be statistically significant."
        )
        ci_lower = "95% lower confidence interval"
        ci_upper = "95% upper confidence interval"
        avail_ci = [c for c in [ci_lower, ci_upper, "Rate"] if c in overall_df.columns]

        if len(avail_ci) < 3:
            st.warning("Confidence interval columns not found in dataset.")
        else:
            ci_df = overall_df[[name_col, "Rate", ci_lower, ci_upper]].dropna().copy() if name_col else overall_df[["Rate", ci_lower, ci_upper]].dropna().copy()
            ci_df = ci_df.sort_values("Rate", ascending=False)

            ci_limit = st.slider("Districts:", 5, max(5, len(ci_df)), 20, key="c_t4_limit")
            ci_df = ci_df.head(ci_limit)

            x_ci = ci_df[name_col].tolist() if name_col else ci_df.index.astype(str).tolist()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
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
            ))
            fig.update_layout(
                title="Overall Standardised Cancer Rate with 95% CI",
                xaxis_title="District",
                yaxis_title="Rate (per 100,000)",
                xaxis_tickangle=-45,
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Tab 5: Cross-type heatmap ──────────────────────────────────────────────
    with tab_heatmap:
        st.subheader("Cancer Type × District Heatmap")
        st.info(
            "All 5 cancer types across all districts in a single view. "
            "Color intensity = incidence rate. Reveals clusters of high rates across multiple types."
        )
        avail_cancers = [c for c in CANCER_TYPES if c in overall_df.columns]
        hm_df = overall_df[[name_col] + avail_cancers].dropna().set_index(name_col) if name_col else overall_df[avail_cancers].dropna()

        sort_hm = st.selectbox("Sort rows by:", avail_cancers, key="c_t5_sort")
        hm_df = hm_df.sort_values(sort_hm, ascending=False)

        fig = px.imshow(
            hm_df[avail_cancers].T,
            labels=dict(x="District", y="Cancer Type", color="Rate"),
            color_continuous_scale="YlOrRd",
            title="Incidence Rate Heatmap — Cancer Type × District",
            aspect="auto",
        )
        fig.update_layout(height=360, xaxis_tickangle=-45)
        fig.update_traces(colorbar_title_text="Rate (per 100k)")
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 6: Scatter ─────────────────────────────────────────────────────────
    with tab_scatter:
        st.subheader("Specific Cancer vs Overall Rate")
        st.write("Does a specific cancer type track linearly with the district's overall rate?")
        avail_cancers = [c for c in CANCER_TYPES if c in overall_df.columns]
        selected_specific = st.selectbox("Cancer type:", avail_cancers, key="c_t6_specific")
        compare_df = overall_df.dropna(subset=["Rate", selected_specific]).copy()
        fig = create_scatter_chart(
            compare_df, x_col="Rate", y_col=selected_specific,
            color_col=name_col,
            title=f"Overall Rate vs {selected_specific.capitalize()} Rate"
        )
        fig.update_layout(
            xaxis_title="Overall Cancer Rate (per 100k)",
            yaxis_title=f"{selected_specific.capitalize()} Rate",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 7: Data table ──────────────────────────────────────────────────────
    with tab_data:
        st.subheader("📋 Dataset Previews")
        preview_tab1, preview_tab2 = st.tabs(["Incidence Overview", "Top 5 Cancers (Long)"])
        with preview_tab1:
            st.dataframe(overall_df, use_container_width=True)
        with preview_tab2:
            if not top5_df.empty:
                st.dataframe(top5_df, use_container_width=True)
            else:
                st.info("Top-5 cancers dataset is not loaded.")


if __name__ == "__main__":
    render_cancer_trends()
