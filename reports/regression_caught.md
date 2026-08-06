# Regression Caught: filter_count Comparison-Operator Swap

## Summary

A deliberately introduced bug in `filter_count` (swapping the
`greater_than`/`less_than` comparison operators — a realistic
copy-paste/refactor mistake) dropped the eval pass rate on a 6-task
subset from **83% to 50%**. Reverting the bug restored the pass rate to
exactly 83%, with every individual task score matching the original
baseline. This confirms the evaluation harness reliably catches a real,
localized logic regression — not just crashes, but *silently wrong
answers*, which are the harder and more dangerous failure mode to catch.

## The bug

```python
# Before (correct):
elif condition == "greater_than" and col_numeric is not None:
    mask = col_numeric > typed_value
elif condition == "less_than" and col_numeric is not None:
    mask = col_numeric < typed_value

# After (bug -- operators swapped):
elif condition == "greater_than" and col_numeric is not None:
    mask = col_numeric < typed_value
elif condition == "less_than" and col_numeric is not None:
    mask = col_numeric > typed_value
```

## Results

| ID | Category | Before | After (bugged) | Fixed | Changed? |
|----|-----------|:------:|:---------------:|:-----:|----------|
| 4 | happy_path | 2 | 0 | 2 | **Regression, then recovered** |
| 11 | happy_path | 2 | 0 | 2 | **Regression, then recovered** |
| 18 | edge_case | 0 | 0 | 0 | Unaffected (pre-existing, unrelated issue) |
| 1 | happy_path | 2 | 2 | 2 | Unaffected (control) |
| 2 | happy_path | 2 | 2 | 2 | Unaffected (control) |
| 13 | happy_path | 2 | 2 | 2 | Unaffected (control) |

**Pass rate: 83% → 50% → 83%.**

Task 11 gives an especially clean confirmation of *why* it failed, not
just *that* it failed: the correct answer is 29 orders with revenue over
$1000. Under the bug, the agent reported **91** — and `120 - 29 = 91`
exactly, which is precisely what the flipped `<`/`>` logic produces
mathematically on a 120-row dataset. This isn't just "the number changed
and got worse" — it's mathematical proof the specific bug caused the
specific wrong output.

## Why the controls matter

Tasks 1, 2, and 13 use `compute_stat` and `filter_count(equals)`
respectively — neither touches the `greater_than`/`less_than` branch that
was bugged. Their scores staying at `2` throughout confirms the
regression was correctly localized to the exact code path that changed,
not a broader instability in the agent or judge.

## Task 18 (unrelated, pre-existing issue)

Task 18 stayed at `0` in all three runs for a separate reason: the agent
occasionally claims `greater_than` "is not supported" by `filter_count`
even though it is one of the tool's three real conditions — a
hallucinated limitation, not a real one. This is a distinct, already-known
issue tracked separately; it did not interfere with this regression test
since it was broken identically before, during, and after the bug.