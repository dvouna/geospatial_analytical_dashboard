"""
DEPRECATED — this root-level utils.py is shadowed by the ``utils/`` package
and is therefore unreachable via ``import utils`` or ``from utils import …``.

All helpers have been moved into the package:
  - Export / filter helpers  →  utils/export.py
  - I/O helpers              →  utils/io.py
  - Path helpers             →  utils/paths.py

Use:
    from utils import export_dataframe_to_csv, filter_dataframe, ...

This file is kept as a reference shim and should not be imported directly.
"""

# Re-export everything so an accidental direct import still works.
from utils import (  # noqa: F401 — intentional star-style re-export
    export_dataframe_to_csv,
    export_dataframe_to_excel,
    filter_dataframe,
    get_column_stats,
    format_large_number,
    create_download_button,
    load_csv,
    load_json,
    normalize_id_column,
    project_root,
    data_path,
    resource_path,
)
