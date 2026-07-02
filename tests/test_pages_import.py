"""
Smoke tests — baseline before the Option A single-page refactor.

These tests verify that:
1. All page modules are importable.
2. Core map_utils helpers behave correctly in isolation.
3. Key data-loading functions handle missing files gracefully.

Run with:
    pytest tests/test_pages_import.py -v
"""

import importlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import Polygon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def _make_tiny_gdf() -> gpd.GeoDataFrame:
    """Return a minimal two-feature GeoDataFrame for unit testing."""
    geoms = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
    ]
    return gpd.GeoDataFrame(
        {
            "fid": ["A001", "A002"],
            "LAD24NM": ["Alpha", "Beta"],
            "LAD24CD": ["E01", "E02"],
        },
        geometry=geoms,
        crs="EPSG:4326",
    )


# ---------------------------------------------------------------------------
# 1. Module import smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_path",
    [
        "map_utils",
        "config",
        "data_loader",
        "utils",
    ],
)
def test_utility_modules_importable(module_path):
    """All utility modules must import without errors."""
    # map_utils imports streamlit_folium at module level; streamlit_folium in turn
    # imports streamlit.components.v1.  We must mock all three so the import chain
    # resolves without a real Streamlit server.
    st_mock = MagicMock()
    st_mock.components = MagicMock()
    st_mock.components.v1 = MagicMock()
    extra = {
        "streamlit": st_mock,
        "streamlit.components": st_mock.components,
        "streamlit.components.v1": st_mock.components.v1,
        "streamlit_folium": MagicMock(),
    }
    with patch.dict("sys.modules", extra):
        mod = importlib.import_module(module_path)
    assert mod is not None


@pytest.mark.parametrize(
    "module_path",
    [
        "pages.1_Population_Demographics",
        "pages.2_Deprivation_Analysis",
        "pages.3_Cancer_Trends",
        "pages.5_AI_Research_Assistant",
    ],
)
def test_page_modules_importable(module_path):
    """Every page module must be importable (no top-level side-effects)."""
    with patch.dict(
        "sys.modules", {"streamlit": MagicMock(), "streamlit_folium": MagicMock()}
    ):
        mod = importlib.import_module(module_path)
    assert mod is not None


# ---------------------------------------------------------------------------
# 2. map_utils unit tests (no Streamlit server required)
# ---------------------------------------------------------------------------


def test_compute_center():
    """compute_center should return sensible lat/lon from GeoDataFrame bounds."""
    from map_utils import compute_center

    gdf = _make_tiny_gdf()
    lat, lon = compute_center(gdf)
    # Bounding box is [0,0,2,1] → centre (lat=0.5, lon=1.0)
    assert abs(lat - 0.5) < 1e-6
    assert abs(lon - 1.0) < 1e-6


def test_prepare_geojson_payload_has_ids():
    """Every feature in the prepared payload must carry an 'id' field."""
    from map_utils import prepare_geojson_payload

    gdf = _make_tiny_gdf()
    payload, id_field = prepare_geojson_payload(gdf)

    assert "features" in payload
    for feat in payload["features"]:
        assert "id" in feat, "Feature is missing required 'id' field"


def test_prepare_geojson_payload_id_field_detected():
    """prepare_geojson_payload should detect 'fid' as the id field."""
    from map_utils import prepare_geojson_payload

    gdf = _make_tiny_gdf()
    _, id_field = prepare_geojson_payload(gdf)
    assert id_field == "fid"


def test_build_authority_options_round_trip():
    """build_authority_options should produce consistent option ↔ id mappings."""
    from map_utils import prepare_geojson_payload, build_authority_options

    gdf = _make_tiny_gdf()
    payload, _ = prepare_geojson_payload(gdf)
    options, option_to_id, id_to_display, id_to_props = build_authority_options(payload)

    assert len(options) == 2
    # Round-trip: name → id → name
    for name in options:
        fid = option_to_id[name]
        assert id_to_display[fid] == name


def test_extract_clicked_fid_from_tooltip():
    """extract_clicked_fid should match a display name found in the tooltip."""
    from map_utils import (
        prepare_geojson_payload,
        build_authority_options,
        extract_clicked_fid,
    )

    gdf = _make_tiny_gdf()
    payload, _ = prepare_geojson_payload(gdf)
    options, option_to_id, id_to_display, id_to_props = build_authority_options(payload)

    # Simulate a tooltip click on "Alpha"
    fake_map_output = {"last_object_clicked_tooltip": "Alpha"}
    clicked = extract_clicked_fid(fake_map_output, option_to_id, id_to_props)
    assert clicked == option_to_id["Alpha"]


def test_extract_clicked_fid_none_on_empty():
    """extract_clicked_fid should return None when map_output is empty."""
    from map_utils import extract_clicked_fid

    result = extract_clicked_fid({}, {}, {})
    assert result is None


def test_merge_overlay_preserves_geometry():
    """merge_overlay must preserve the geometry column after a join."""
    from map_utils import merge_overlay

    gdf = _make_tiny_gdf()
    overlay = pd.DataFrame({"fid": ["A001", "A002"], "population": [10000, 20000]})
    merged = merge_overlay(gdf, overlay, base_key="fid", overlay_key="fid")

    assert "geometry" in merged.columns
    assert "population" in merged.columns
    assert len(merged) == 2


# ---------------------------------------------------------------------------
# 3. Data-loading error handling
# ---------------------------------------------------------------------------


def test_load_geojson_raises_on_missing_file():
    """load_geojson must raise FileNotFoundError for a non-existent path."""
    from map_utils import load_geojson

    with pytest.raises(FileNotFoundError):
        load_geojson("/nonexistent/path/file.geojson")


def test_load_overlay_dataframe_raises_on_missing_file():
    """load_overlay_dataframe must raise FileNotFoundError for a non-existent path."""
    from map_utils import load_overlay_dataframe

    with pytest.raises(FileNotFoundError):
        load_overlay_dataframe("/nonexistent/path/overlay.csv")


# ---------------------------------------------------------------------------
# 4. GeoJSON geometry simplification (pre-optimisation baseline)
# ---------------------------------------------------------------------------


def test_geojson_payload_size_baseline():
    """Record the approximate serialised GeoJSON size (bytes) as a baseline.

    This test always passes — it just prints the size so we can compare it
    against the optimised version after the refactor.
    """
    import json
    from map_utils import prepare_geojson_payload

    base_path = DATA_DIR / "base_gdf_1.geojson"
    if not base_path.exists():
        pytest.skip("base_gdf_1.geojson not available in this environment")

    import geopandas as gpd

    gdf = gpd.read_file(str(base_path))
    payload, _ = prepare_geojson_payload(gdf)
    size_kb = len(json.dumps(payload).encode()) / 1024
    print(f"\n[BASELINE] base_gdf_1.geojson serialised size: {size_kb:.1f} KB")
    assert size_kb > 0  # always passes; value captured in output
