"""utils package
Cross-cutting helper utilities for the geospatial dashboard.

Public helpers:
- load_csv, load_json, normalize_id_column (from `io`)
- project_root, data_path, resource_path (from `paths`)
- export_dataframe_to_csv, export_dataframe_to_excel,
  filter_dataframe, get_column_stats, format_large_number,
  create_download_button (from `export`)

Import example:
    from utils import load_csv, data_path, export_dataframe_to_csv

"""

from .io import load_csv, load_json, normalize_id_column
from .paths import project_root, data_path, resource_path
from .export import (
    export_dataframe_to_csv,
    export_dataframe_to_excel,
    filter_dataframe,
    get_column_stats,
    format_large_number,
    create_download_button,
)

__all__ = [
    # io
    "load_csv",
    "load_json",
    "normalize_id_column",
    # paths
    "project_root",
    "data_path",
    "resource_path",
    # export
    "export_dataframe_to_csv",
    "export_dataframe_to_excel",
    "filter_dataframe",
    "get_column_stats",
    "format_large_number",
    "create_download_button",
]
