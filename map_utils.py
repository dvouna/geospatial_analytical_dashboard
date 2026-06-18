from pathlib import Path
import json
from typing import Optional, Tuple, List, Dict
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium


DEFAULT_ID_CANDIDATES = [
    "fid",
    "LAD24CD",
    "LAD13CD",
    "LAD19CD",
    "LAD20CD",
    "code",
    "id",
]
MAP_TILE_OPTIONS = [
    "Basic (OpenStreetMap)",
    "Light Streets (CartoDB)",
    "Satellite (ArcGIS)",
]


@st.cache_data
def load_geojson(path: str or Path) -> gpd.GeoDataFrame:
    """Load a GeoJSON/Shapefile into a GeoDataFrame and ensure WGS84 (EPSG:4326).

    Raises FileNotFoundError on missing path, or forwards other exceptions from geopandas.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {p}")

    gdf = gpd.read_file(str(p))
    if gdf.crs is None or gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    return gdf


@st.cache_data
def load_base_gdf(data_dir: Path) -> gpd.GeoDataFrame:
    """Load the shared base GeoJSON and ensure WGS84."""
    data_path = data_dir / "base_gdf_1.geojson"
    return load_geojson(data_path)


def build_authority_options(
    geojson_payload: dict, id_field: Optional[str] = None
) -> Tuple[List[str], Dict[str, str], Dict[str, str], Dict[str, dict]]:
    """Build selectbox options and id/display/properties lookup dicts.

    Returns:
        (options, option_to_id, id_to_display, id_to_props)
    """
    display_names = []
    features = geojson_payload.get("features", [])

    # Try to find a sensible name field
    first_props = features[0].get("properties", {}) if features else {}
    name_field = next(
        (c for c in ["LAD24NM", "name", "NAME", "LA_Name"] if c in first_props), None
    )

    for feat in features:
        fid = str(feat.get("id"))
        props = feat.get("properties", {})
        name = props.get(name_field) if name_field else fid
        display_names.append((name, fid))

    options = [d[0] for d in display_names]
    option_to_id = {name: fid for name, fid in display_names}
    id_to_display = {fid: name for name, fid in display_names}
    id_to_props = {str(feat.get("id")): feat.get("properties", {}) for feat in features}

    return options, option_to_id, id_to_display, id_to_props


def extract_clicked_fid(
    map_output: dict, option_to_id: dict, id_to_props: dict
) -> Optional[str]:
    """Identify the clicked feature ID from the map output or tooltip metadata."""
    if not map_output:
        return None

    clicked = map_output.get("last_object_clicked")
    if isinstance(clicked, dict):
        clicked_id = clicked.get("id")
        if clicked_id is not None and str(clicked_id) in id_to_props:
            return str(clicked_id)

    tooltip = map_output.get("last_object_clicked_tooltip")
    if not tooltip:
        return None

    tooltip_text = str(tooltip)
    for display_name, fid in sorted(
        option_to_id.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if display_name and display_name in tooltip_text:
            return str(fid)

    for fid in id_to_props:
        if f"fid: {fid}" in tooltip_text or f">{fid}<" in tooltip_text:
            return str(fid)

    return None


def trigger_rerun():
    """Trigger a Streamlit page rerun safely.

    Uses ``st.rerun()`` when available (Streamlit ≥ 1.27) and falls back to
    the deprecated ``st.experimental_rerun()`` for older installations.
    The ``return`` after ``st.rerun()`` is intentional — without it execution
    would fall through to the deprecated call even when the modern API is used.
    """
    if hasattr(st, "rerun"):
        st.rerun()
        return
    st.experimental_rerun()  # noqa: DEP001 – fallback for Streamlit < 1.27


def display_props_as_kv(props: dict):
    """Render feature properties as a clean two-column Streamlit table."""
    if not props:
        st.info("No details are available for this selection.")
        return
    kv_df = pd.DataFrame(
        [(k, v) for k, v in props.items()], columns=["Metric", "Value"]
    )
    kv_df["Value"] = kv_df["Value"].astype(str)
    st.table(kv_df)


def compute_center(gdf: gpd.GeoDataFrame) -> Tuple[float, float]:
    """Return (lat, lon) center computed from GeoDataFrame bounds."""
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    avg_lat = (bounds[1] + bounds[3]) / 2
    avg_lon = (bounds[0] + bounds[2]) / 2
    return avg_lat, avg_lon


def prepare_geojson_payload(
    gdf: gpd.GeoDataFrame,
    id_field_candidates: Optional[List[str]] = None,
) -> Tuple[dict, Optional[str]]:
    """Convert GeoDataFrame to a GeoJSON payload (dict) and ensure each feature has a stable `id`.

    Returns (payload, detected_id_field_name).
    """
    if id_field_candidates is None:
        id_field_candidates = DEFAULT_ID_CANDIDATES

    payload = json.loads(gdf.to_json())

    # detect an id field present in GeoDataFrame columns
    id_field = next((c for c in id_field_candidates if c in gdf.columns), None)

    for i, feat in enumerate(payload.get("features", [])):
        props = feat.setdefault("properties", {})
        if id_field and id_field in props:
            feat_id = props.get(id_field)
        else:
            feat_id = str(i)
        feat["id"] = feat_id

    return payload, id_field


def load_overlay_dataframe(
    path: str or Path, index_col: Optional[str] = None, dtype: Optional[dict] = None
) -> pd.DataFrame:
    """Load a tabular overlay (CSV/TSV) to be joined to the base GeoDataFrame.

    - `path`: file path to the CSV (or other file readable by pandas).
    - `index_col`: optional column name to normalize (e.g., 'LAD24CD').
    - `dtype`: optional dtypes mapping passed to `pd.read_csv`.

    Returns a pandas DataFrame. Raises FileNotFoundError if missing.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Overlay file not found: {p}")

    # Let pandas infer format by suffix; read_csv handles most delimited files
    df = pd.read_csv(p, dtype=dtype)

    # Normalize the key column to string and strip whitespace when provided
    if index_col and index_col in df.columns:
        df[index_col] = df[index_col].astype(str).str.strip()

    return df


def merge_overlay(
    base_gdf: gpd.GeoDataFrame,
    overlay_df: pd.DataFrame,
    base_key: str = "fid",
    overlay_key: str = "fid",
    how: str = "left",
) -> gpd.GeoDataFrame:
    """Return a new GeoDataFrame merging `overlay_df` onto `base_gdf` by the given keys.

    This does not mutate `base_gdf` and will preserve geometry. Both keys are
    normalized to strings before joining.
    """
    # Make copies to avoid mutating inputs
    base_copy = base_gdf.copy()
    overlay_copy = overlay_df.copy()

    if base_key in base_copy.columns:
        base_copy[base_key] = base_copy[base_key].astype(str).str.strip()
    if overlay_key in overlay_copy.columns:
        overlay_copy[overlay_key] = overlay_copy[overlay_key].astype(str).str.strip()

    merged = base_copy.merge(
        overlay_copy,
        left_on=base_key,
        right_on=overlay_key,
        how=how,
        suffixes=("", "_overlay"),
    )
    return gpd.GeoDataFrame(merged, geometry=base_copy.geometry.name)


def create_folium_map(
    center: Tuple[float, float],
    zoom: int = 8,
    tiles: str = "CartoDB positron",
    attr: Optional[str] = None,
) -> folium.Map:
    """Create and return a Folium Map object with provided center/tiles."""
    return folium.Map(
        location=[center[0], center[1]], zoom_start=zoom, tiles=tiles, attr=attr
    )


def get_map_tile_config(map_type: str) -> Tuple[str, Optional[str]]:
    """Return Folium tiles and attribution for a supported map type label."""
    if map_type == "Basic (OpenStreetMap)":
        return "OpenStreetMap", None
    if map_type == "Light Streets (CartoDB)":
        return (
            "https://{s}.basemaps.cartocdn.com/positron/{z}/{x}/{y}{r}.png",
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors '
            '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        )
    return (
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, "
        "Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
    )


def render_map_settings(
    key: str, index: int = 2, show_help_text: bool = False
) -> Tuple[str, Optional[str]]:
    """Render shared sidebar map settings and return Folium tile config."""
    st.sidebar.subheader("Map Settings")
    if show_help_text:
        st.sidebar.write("Select a map background type:")
    map_type = st.sidebar.radio(
        "Map type:",
        MAP_TILE_OPTIONS,
        key=key,
        index=index,
    )
    return get_map_tile_config(map_type)


def add_geojson_layer(
    m: folium.Map,
    geojson_payload: dict,
    gdf_columns,
    selected_id: Optional[str] = None,
    tooltip_fields: Optional[List[str]] = None,
):
    """Add a styled GeoJSON layer to a Folium map. Highlights `selected_id` if provided.

    Returns the created GeoJson object.
    """
    if tooltip_fields is None:
        tooltip_fields = [c for c in gdf_columns if c != "geometry"][:3]

    def style_fn(feature):
        if selected_id is not None and str(feature.get("id")) == str(selected_id):
            return {
                "fillColor": "#ff7800",
                "color": "orange",
                "weight": 3,
                "fillOpacity": 0.7,
            }
        return {
            "fillColor": "#318dcc",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.4,
        }

    gj = folium.GeoJson(
        geojson_payload,
        style_function=style_fn,
        highlight_function=lambda x: {
            "weight": 3,
            "color": "orange",
            "fillOpacity": 0.6,
        },
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, localize=True),
    )
    gj.add_to(m)
    return gj


def render_map_st_folium(
    m: folium.Map,
    width: str = "100%",
    height: int = 900,
    returned_objects: Optional[list] = None,
):
    """Wrapper around `st_folium` to render a Folium map inside Streamlit and return interaction objects."""
    if returned_objects is None:
        returned_objects = []
    return st_folium(m, width=width, height=height, returned_objects=returned_objects)


__all__ = [
    "load_geojson",
    "load_base_gdf",
    "build_authority_options",
    "extract_clicked_fid",
    "trigger_rerun",
    "display_props_as_kv",
    "load_overlay_dataframe",
    "merge_overlay",
    "compute_center",
    "prepare_geojson_payload",
    "create_folium_map",
    "get_map_tile_config",
    "render_map_settings",
    "add_geojson_layer",
    "render_map_st_folium",
]
