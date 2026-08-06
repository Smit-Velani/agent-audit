"""
tools.py — Schema-agnostic tools for Scout.
Works with any pandas DataFrame loaded from a CSV.
"""

import pandas as pd
from langchain_core.tools import tool

_df: pd.DataFrame = pd.DataFrame()

def set_dataframe(df: pd.DataFrame):
    global _df
    _df = df

@tool
def list_columns() -> str:
    """Lists all column names and their data types in the loaded dataset."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    lines = [f"{col}: {dtype}" for col, dtype in _df.dtypes.items()]
    return "Columns:\n" + "\n".join(lines)

@tool
def compute_stat(column: str, stat: str, group_by: str = "") -> str:
    """Computes mean, sum, count, min, max, or median on any numeric column,
    optionally grouped by another column."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    if column not in _df.columns:
        return f"Error: column '{column}' not found. Available: {list(_df.columns)}"
    if stat not in ("mean", "sum", "count", "min", "max", "median"):
        return f"Error: stat must be one of mean/sum/count/min/max/median, got '{stat}'"
    if stat != "count" and not pd.api.types.is_numeric_dtype(_df[column]):
        return (f"Error: column '{column}' is not numeric (dtype={_df[column].dtype}). "
                f"Try 'count' instead, or choose a numeric column.")
    if group_by:
        if group_by not in _df.columns:
            return f"Error: group_by column '{group_by}' not found."
        result = _df.groupby(group_by)[column].agg(stat)
        return result.to_string()
    result = getattr(_df[column], stat)()
    return f"{stat}({column}) = {result}"

@tool
def filter_count(column: str, condition: str, value: str) -> str:
    """Counts rows matching equals, greater_than, or less_than on any column."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    if column not in _df.columns:
        return f"Error: column '{column}' not found. Available: {list(_df.columns)}"
    col = _df[column]
    try:
        typed_value = float(value)
        col_numeric = pd.to_numeric(col, errors="coerce")
    except ValueError:
        typed_value = value
        col_numeric = None
    if condition == "equals":
        mask = col == typed_value
    elif condition == "greater_than" and col_numeric is not None:
        mask = col_numeric > typed_value
    elif condition == "less_than" and col_numeric is not None:
        mask = col_numeric < typed_value
    else:
        return f"Error: unsupported condition '{condition}' for this column/value type."
    return f"{mask.sum()} rows match {column} {condition} {value}"

@tool
def get_sample_rows(n: int = 5) -> str:
    """Returns the first n rows of the dataset as a text preview."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    return _df.head(n).to_string()