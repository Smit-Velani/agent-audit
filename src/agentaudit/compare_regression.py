"""
compare_regression.py — Compares a before/after regression test run and
shows exactly which tasks flipped from pass to fail.
"""

import pandas as pd

before = pd.read_csv("reports/regression_before.csv")
after = pd.read_csv("reports/regression_after2.csv")

merged = before.merge(after, on="id", suffixes=("_before", "_after"))

print(f"{'ID':<4}{'Category':<14}{'Before':<8}{'After':<8}{'Changed?'}")
for _, row in merged.iterrows():
    changed = "<<< REGRESSION" if row.score_before != row.score_after else ""
    print(f"{row.id:<4}{row.category_before:<14}{row.score_before:<8}{row.score_after:<8}{changed}")

pass_rate_before = (before.score == 2).mean() * 100
pass_rate_after = (after.score == 2).mean() * 100
print(f"\nPass rate before: {pass_rate_before:.0f}%")
print(f"Pass rate after:  {pass_rate_after:.0f}%")