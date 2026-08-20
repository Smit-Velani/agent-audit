"""
compute_agreement.py — Computes the agreement statistics behind the headline
kappa numbers: Judge A vs Judge B (inter-judge, all tasks), and Judge vs
Human (on the hand-scored subset), each with a bootstrap confidence interval.

The interval matters more than usual here. Cohen's kappa on a small sample is
unstable, and a point estimate reported alone invites the reader to treat it
as more precise than it is. Bootstrapping the scored pairs gives an honest
range, and the width of that range is itself the argument for hand-scoring
more tasks.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

INPUT_PATH = "reports/eval_results.csv"
OUTPUT_PATH = "reports/agreement.csv"


def bootstrap_kappa_ci(a, b, n_boot=5000, alpha=0.05, seed=0):
    """
    Percentile bootstrap interval for Cohen's kappa.

    Resamples the scored pairs with replacement and recomputes kappa each
    time. Replicates where one rater used only a single category are dropped
    -- kappa is undefined there, since there is no disagreement structure to
    measure -- and the count of those drops is returned so the reader can see
    how often it happened.

    Returns (kappa, ci_low, ci_high, n_valid_replicates).
    """
    a = np.asarray(a)
    b = np.asarray(b)
    n = len(a)
    rng = np.random.default_rng(seed)

    point = cohen_kappa_score(a, b)

    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        aa, bb = a[idx], b[idx]
        if len(np.unique(aa)) < 2 or len(np.unique(bb)) < 2:
            continue
        k = cohen_kappa_score(aa, bb)
        if np.isfinite(k):
            boots.append(k)

    if len(boots) < 100:
        return float(point), np.nan, np.nan, len(boots)

    boots = np.array(boots)
    lo = float(np.percentile(boots, 100 * alpha / 2))
    hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
    return float(point), lo, hi, len(boots)


def interpret(kappa):
    """Landis & Koch (1977) benchmark labels, stated for orientation only."""
    if kappa < 0.00:
        return "poor"
    if kappa < 0.21:
        return "slight"
    if kappa < 0.41:
        return "fair"
    if kappa < 0.61:
        return "moderate"
    if kappa < 0.81:
        return "substantial"
    return "almost perfect"


def main():
    df = pd.read_csv(INPUT_PATH)
    rows = []

    # --- Inter-judge agreement, all tasks ---------------------------------
    k_ab, lo_ab, hi_ab, nb_ab = bootstrap_kappa_ci(df.judge_a_score, df.judge_b_score)
    raw_ab = (df.judge_a_score == df.judge_b_score).mean()

    print(f"Judge A vs Judge B  (n = {len(df)} tasks)")
    print(f"  Raw agreement : {raw_ab*100:.1f}%")
    print(f"  Cohen's kappa : {k_ab:.3f}  95% CI ({lo_ab:.3f}, {hi_ab:.3f})  [{interpret(k_ab)}]")
    print()

    rows.append({
        "comparison": "Judge A vs Judge B", "n": len(df),
        "raw_agreement": raw_ab, "kappa": k_ab,
        "ci_low": lo_ab, "ci_high": hi_ab,
        "ci_width": hi_ab - lo_ab, "interpretation": interpret(k_ab),
        "bootstrap_replicates": nb_ab,
    })

    # --- Judge vs human, hand-scored subset -------------------------------
    mask = df.human_score.notna() & (df.human_score.astype(str).str.strip() != "")
    hs = df[mask].copy()

    if len(hs) == 0:
        print("No human scores found -- run human_score.py first.")
        pd.DataFrame(rows).to_csv(OUTPUT_PATH, index=False)
        return

    hs["human_score"] = hs["human_score"].astype(float).astype(int)

    for label, col in [("Judge A vs Human", "judge_a_score"),
                       ("Judge B vs Human", "judge_b_score")]:
        k, lo, hi, nb = bootstrap_kappa_ci(hs[col], hs.human_score)
        raw = (hs[col] == hs.human_score).mean()

        print(f"{label}  (n = {len(hs)} hand-scored of {len(df)})")
        print(f"  Raw agreement : {raw*100:.1f}%")
        print(f"  Cohen's kappa : {k:.3f}  95% CI ({lo:.3f}, {hi:.3f})  [{interpret(k)}]")
        print()

        rows.append({
            "comparison": label, "n": len(hs),
            "raw_agreement": raw, "kappa": k,
            "ci_low": lo, "ci_high": hi,
            "ci_width": hi - lo, "interpretation": interpret(k),
            "bootstrap_replicates": nb,
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_PATH, index=False)

    # --- Honesty note about precision -------------------------------------
    jah = out[out.comparison == "Judge A vs Human"].iloc[0]
    print("-" * 66)
    print(f"Note on precision: the judge-vs-human kappa rests on "
          f"{int(jah.n)} hand-scored")
    print(f"tasks, giving a 95% interval {jah.ci_width:.2f} wide. The point "
          f"estimate of {jah.kappa:.3f}")
    print(f"sits in the '{jah.interpretation}' band, but the interval spans "
          f"several bands.")
    print("Hand-scoring the remaining tasks is the only way to tighten it; "
          "reporting")
    print("the point estimate alone would overstate what this sample can "
          "support.")
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()