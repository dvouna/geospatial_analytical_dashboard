"""
Export and filter helpers.

These utilities were previously in the root-level ``utils.py``, which was
shadowed by the ``utils/`` package and therefore unreachable.  They live here
so they can be imported as:

    from utils import export_dataframe_to_csv
    from utils.export import create_download_button
"""

import io
import pandas as pd
import streamlit as st


def export_dataframe_to_csv(df: pd.DataFrame, filename: str = "data_export.csv", index: bool = False, **kwargs) -> bytes:
    """
    Export DataFrame to CSV bytes.

    Args:
        df: pandas DataFrame
        filename: Name for the export file (unused in bytes output, kept for
                  API symmetry with ``create_download_button``).
        index: Whether to include the index in the CSV (default False).
        **kwargs: Additional arguments passed to df.to_csv.

    Returns:
        CSV file as bytes.
    """
    buffer = io.StringIO()
    df.to_csv(buffer, index=index, **kwargs)
    return buffer.getvalue().encode("utf-8")


def create_download_button(
    label: str, data: bytes, file_name: str, file_type: str, **kwargs
) -> None:
    """
    Render a Streamlit download button.

    Args:
        label: Button label text.
        data: File data as bytes.
        file_name: Suggested filename for the downloaded file.
        file_type: MIME type (e.g. ``'text/csv'``).
        **kwargs: Additional arguments passed to st.download_button (e.g., key, use_container_width)
    """
    st.download_button(
        label=label,
        data=data,
        file_name=file_name,
        mime=file_type,
        **kwargs
    )
