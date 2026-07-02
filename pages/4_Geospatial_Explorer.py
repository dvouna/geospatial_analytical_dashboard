import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

from map_utils import (
    load_base_gdf,
    prepare_geojson_payload,
    build_authority_options,
    compute_center,
    create_folium_map,
    get_map_tile_config,
    add_geojson_layer,
    render_map_st_folium,
    load_overlay_dataframe,
    merge_overlay,
    display_props_as_kv,
    extract_clicked_fid,
)

DATA_DIR = Path(__file__).parent.parent / "data"

# Metrics to compare in the mini-bar; maps display label → (data column, units)
COMPARE_METRICS = {
    "IMD Overall Rank": ("imd_rank", "rank (lower = more deprived)"),
    "Overall Cancer Rate": ("cancer_rate", "per 100,000"),
    "Total Population": ("total_population", "people"),
}


def _regional_averages(id_to_props: dict, metrics: list[str]) -> dict[str, float]:
    """Compute average of each numeric metric across all districts."""
    totals: dict[str, list] = {m: [] for m in metrics}
    for props in id_to_props.values():
        for m in metrics:
            val = props.get(m)
            try:
                totals[m].append(float(val))
            except (TypeError, ValueError):
                pass
    return {m: (sum(v) / len(v) if v else 0.0) for m, v in totals.items()}


def _render_comparison_chart(props: dict, regional_avgs: dict, id_to_props: dict) -> None:
    """Render a horizontal bar comparing selected district against regional average."""
    st.markdown("#### 📊 District vs Regional Average")

    rows = []
    for label, (col, unit) in COMPARE_METRICS.items():
        dist_val = props.get(col)
        avg_val = regional_avgs.get(col)
        try:
            dist_val = float(dist_val)
            avg_val = float(avg_val)
        except (TypeError, ValueError):
            continue
        rows.append({
            "Metric": label,
            "District": dist_val,
            "Regional Avg": avg_val,
            "unit": unit,
        })

    if not rows:
        st.info("No numeric metrics available for comparison.")
        return

    df = pd.DataFrame(rows)

    for _, row in df.iterrows():
        metric = row["Metric"]
        dist_v = row["District"]
        avg_v = row["Regional Avg"]
        unit = row["unit"]
        pct_diff = ((dist_v - avg_v) / avg_v * 100) if avg_v != 0 else 0

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=["Regional Avg", "This District"],
            x=[avg_v, dist_v],
            orientation="h",
            marker_color=["#6C757D", "#E63946" if dist_v > avg_v else "#2A9D8F"],
            text=[f"{avg_v:,.1f}", f"{dist_v:,.1f}"],
            textposition="outside",
        ))
        diff_label = f"+{pct_diff:.1f}%" if pct_diff >= 0 else f"{pct_diff:.1f}%"
        fig.update_layout(
            title=dict(text=f"{metric}  <span style='font-size:13px;color:gray'>({diff_label} vs avg)</span>"),
            height=140,
            margin=dict(l=0, r=40, t=40, b=10),
            xaxis_title=unit,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)


def render_geospatial_explorer():
    try:
        st.set_page_config(
            page_title="Geospatial Map Explorer",
            page_icon="🗺️",
            layout="wide",
        )
    except Exception:
        pass

    st.title("🗺️ Geospatial Map Explorer")
    st.write(
        "Dedicated full-page workspace for exploring UK local authority boundary layers. "
        "Select a district to compare it against the East of England regional average."
    )

    # ── Load base GeoJSON ──────────────────────────────────────────────────────
    try:
        gdf = load_base_gdf(DATA_DIR)
    except FileNotFoundError:
        st.error("❌ Unable to load base boundaries GeoJSON data.")
        return
    except Exception as exc:
        st.error(f"❌ Error loading base boundaries: {exc}")
        return

    # ── Attempt to load overlay ────────────────────────────────────────────────
    try:
        overlay_df = load_overlay_dataframe(DATA_DIR / "local_districts.csv", index_col="fid")
        gdf = merge_overlay(gdf, overlay_df, base_key="fid", overlay_key="fid")
    except Exception:
        pass

    # ── Layout ─────────────────────────────────────────────────────────────────
    col_map, col_props = st.columns([7, 3])

    with col_props:
        st.subheader("🛠️ Settings & Inspection")

        # Tile selection
        tiles_label = st.radio(
            "Map Background:",
            options=["Basic (OpenStreetMap)", "Light Streets (CartoDB)", "Satellite (ArcGIS)"],
            index=1,
            key="geo_play_tiles",
        )
        tiles, attr = get_map_tile_config(tiles_label)

        # Prepare GeoJSON payload
        geojson_payload, id_field = prepare_geojson_payload(gdf, simplify_tolerance=0.001)
        options, option_to_id, id_to_display, id_to_props = build_authority_options(geojson_payload)

        # Zoom/select
        selected_display = st.selectbox(
            "Search and zoom to district:",
            options=["All districts"] + options,
            index=0,
            key="geo_play_zoom",
        )

        active_fid = None
        if selected_display != "All districts":
            active_fid = option_to_id.get(selected_display)

        st.markdown("---")
        st.markdown("### 🔍 Selected Properties")

        # Compute regional averages once
        metric_cols = [col for _, (col, _) in COMPARE_METRICS.items()]
        regional_avgs = _regional_averages(id_to_props, metric_cols)

        if active_fid:
            props = id_to_props.get(str(active_fid), {})
            display_props_as_kv(props)
            st.markdown("---")
            _render_comparison_chart(props, regional_avgs, id_to_props)
        else:
            st.info("Click a district on the map or search above to inspect attributes.")

    with col_map:
        center = compute_center(gdf)
        m = create_folium_map(center=center, zoom=8, tiles=tiles, attr=attr)

        features = geojson_payload.get("features", [])
        tooltip_fields = []
        if features:
            keys = list(features[0].get("properties", {}).keys())
            tooltip_fields = [f for f in ["fid", "LAD24NM", "imd_rank", "total_population"] if f in keys]
            if not tooltip_fields:
                tooltip_fields = keys[:3]

        add_geojson_layer(
            m,
            geojson_payload,
            gdf_columns=gdf.columns,
            selected_id=active_fid,
            tooltip_fields=tooltip_fields or None,
        )

        map_output = render_map_st_folium(
            m,
            width="100%",
            height=680,
            returned_objects=["last_object_clicked", "last_object_clicked_tooltip", "last_active_drawing"],
        )

        # Map click sync
        clicked_fid = extract_clicked_fid(map_output, option_to_id, id_to_props)
        if clicked_fid and clicked_fid != active_fid:
            if clicked_fid in id_to_display:
                st.session_state["geo_play_zoom"] = id_to_display[clicked_fid]
                st.rerun()


if __name__ == "__main__":
    render_geospatial_explorer()
