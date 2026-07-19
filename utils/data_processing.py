import pandas as pd

def clean_numeric(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """
    Cleans specified columns in a dataframe by stripping strings,
    removing commas, and forcing to numeric types.
    """
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce"
            )
    return df
