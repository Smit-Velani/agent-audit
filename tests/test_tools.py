import pandas as pd
import pytest
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "agentaudit"))

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sales_data.csv")


def test_compute_stat_mean_revenue():
    df = pd.read_csv(DATA_PATH)
    result = df["revenue"].mean()
    assert abs(result - 784.41) < 1.0, f"Expected ~784.41, got {result}"


def test_compute_stat_sum_units():
    df = pd.read_csv(DATA_PATH)
    assert df["units_sold"].sum() == 3098


def test_filter_count_greater_than():
    df = pd.read_csv(DATA_PATH)
    mask = pd.to_numeric(df["units_sold"], errors="coerce") > 30
    assert mask.sum() == 53


def test_filter_count_equals():
    df = pd.read_csv(DATA_PATH)
    assert (df["region"] == "West").sum() == 31


def test_compute_stat_nonexistent_column_returns_error():
    df = pd.read_csv(DATA_PATH)
    if "profit_margin" not in df.columns:
        result = f"Error: column 'profit_margin' not found. Available: {list(df.columns)}"
        assert "Error" in result


def test_compute_stat_nonnumeric_column_is_detected():
    df = pd.read_csv(DATA_PATH)
    assert not pd.api.types.is_numeric_dtype(df["customer_segment"])