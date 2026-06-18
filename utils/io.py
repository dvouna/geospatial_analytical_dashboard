"""I/O helpers for the project.

Provides lightweight wrappers around pandas and pathlib to keep callers concise
and to centralize common behaviors such as normalizing ID columns.
"""

from pathlib import Path
import json
import pandas as pd
from typing import Optional


def load_csv(path, index_col: Optional[str] = None, dtype: Optional[dict] = None) -> pd.DataFrame:
    """Load a CSV into a DataFrame using a Path-like object or string.

    Args:
        path: Path or string to CSV file.
        index_col: Optional column to use as index (will not modify original file).
        dtype: Optional dtype dict to pass to pandas.

    Returns:
        pandas.DataFrame
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    df = pd.read_csv(p, dtype=dtype)
    if index_col and index_col in df.columns:
        df = df.set_index(index_col)
    return df


def load_json(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON not found: {p}")
    with p.open("r", encoding="utf8") as fh:
        return json.load(fh)


def normalize_id_column(df: pd.DataFrame, col: str = "fid") -> pd.DataFrame:
    """Ensure the id column is a trimmed string type for reliable joins.

    This returns a shallow copy of `df` with the normalized column.
    """
    if col not in df.columns:
        return df
    out = df.copy()
    out[col] = out[col].astype(str).str.strip()
    return out
