from pathlib import Path
import json
from typing import Optional, Tuple, List

import geopandas as gpd
import folium
from streamlit_folium import st_folium


DEFAULT_ID_CANDIDATES = ["LAD24CD", "LAD13CD", "LAD19CD", "LAD20CD", "code", "id"]


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


def create_folium_map(
    center: Tuple[float, float], zoom: int = 8, tiles: str = "CartoDB positron", attr: Optional[str] = None
) -> folium.Map:
    """Create and return a Folium Map object with provided center/tiles."""
    return folium.Map(location=[center[0], center[1]], zoom_start=zoom, tiles=tiles, attr=attr)


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
            return {"fillColor": "#ff7800", "color": "orange", "weight": 3, "fillOpacity": 0.7}
        return {"fillColor": "#318dcc", "color": "black", "weight": 1, "fillOpacity": 0.4}

    gj = folium.GeoJson(
        geojson_payload,
        style_function=style_fn,
        highlight_function=lambda x: {"weight": 3, "color": "orange", "fillOpacity": 0.6},
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, localize=True),
    )
    gj.add_to(m)
    return gj


def render_map_st_folium(m: folium.Map, width: str = "100%", height: int = 600, returned_objects: Optional[list] = None):
    """Wrapper around `st_folium` to render a Folium map inside Streamlit and return interaction objects."""
    if returned_objects is None:
        returned_objects = []
    return st_folium(m, width=width, height=height, returned_objects=returned_objects)


__all__ = [
    "load_geojson",
    "compute_center",
    "prepare_geojson_payload",
    "create_folium_map",
    "add_geojson_layer",
    "render_map_st_folium",
]
