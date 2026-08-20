"""
test_grounding.py — Tests for the domain-hallucination guardrail.

The red-team pass found a failure neither keyword guardrail could catch: the
agent invented a customer segment called "Premium" that exists nowhere in the
data. These tests pin that exact case, and equally importantly pin the cases
that must NOT fire -- a grounding check that flags real values is worse than
none, because it trains the reader to ignore it.
"""

import pandas as pd
import pytest

from agent import grounding_guardrail, _dataset_vocabulary

DATA_PATH = "data/sales_data.csv"


@pytest.fixture
def df():
    return pd.read_csv(DATA_PATH)


def test_catches_the_premium_hallucination(df):
    """The exact answer from red-team Task 27."""
    answer = ("The customer segment with the highest count is 'Premium' "
              "with 40 customers.")
    ok, term = grounding_guardrail(answer, df)

    assert ok is False
    assert term.lower() == "premium"


def test_passes_real_segment_names(df):
    """Consumer, Enterprise and SMB are all in the data and must not fire."""
    answer = ("Total revenue by segment: Consumer $51,543.18, "
              "Enterprise $19,422.81, SMB $23,163.03.")
    ok, term = grounding_guardrail(answer, df)

    assert ok is True, f"falsely flagged {term}"


def test_passes_column_names(df):
    """Column names are legitimate vocabulary too."""
    answer = "I computed the mean of the revenue column grouped by region."
    ok, term = grounding_guardrail(answer, df)

    assert ok is True, f"falsely flagged {term}"


def test_passes_plain_numeric_answer(df):
    answer = "The average revenue per order is $784.41."
    ok, term = grounding_guardrail(answer, df)

    assert ok is True, f"falsely flagged {term}"


def test_fails_open_without_data():
    """
    With no dataframe there is no vocabulary to check against. Guessing would
    produce false positives on every capitalised word, so the check declines
    to fire rather than fabricating a verdict of its own.
    """
    ok, term = grounding_guardrail("Anything at all, Premium included.", None)
    assert ok is True
    assert term is None


def test_vocabulary_skips_high_cardinality_columns(df):
    """
    Only low-cardinality object columns count as categories. An ID or
    free-text column would otherwise flood the vocabulary and make the check
    permissive to the point of uselessness.
    """
    wide = df.copy()
    wide["note"] = [f"free text {i}" for i in range(len(wide))]

    vocab = _dataset_vocabulary(wide, max_unique=50)
    assert not any(v.startswith("free text") for v in vocab)


def test_invented_region_is_caught(df):
    """Generalises beyond the one case the red team happened to find."""
    answer = "The Northwest region had the highest revenue."
    ok, term = grounding_guardrail(answer, df)

    assert ok is False
    assert term.lower() == "northwest"