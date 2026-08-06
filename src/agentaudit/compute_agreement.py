"""
compute_agreement.py — Computes the two kappa numbers Phase 4 needs:
Judge A vs Judge B (inter-judge), and Judge vs Human (on the hand-scored
subset).
"""

import pandas as pd
from sklearn.metrics import cohen_kappa_score

INPUT_PATH = "reports/eval_results.csv"


def main():
    df = pd.read_csv(INPUT_PATH)

    kappa_ab = cohen_kappa_score(df.judge_a_score, df.judge_b_score)
    raw_agreement_ab = (df.judge_a_score == df.judge_b_score).mean()
    print(f"Judge A vs Judge B (all {len(df)} tasks):")
    print(f"  Raw agreement: {raw_agreement_ab*100:.1f}%")
    print(f"  Cohen's kappa: {kappa_ab:.3f}")
    print()

    mask = df.human_score.notna() & (df.human_score.astype(str).str.strip() != "")
    human_scored = df[mask].copy()
    if len(human_scored) == 0:
        print("No human scores found yet -- run human_score.py first.")
        return
    human_scored["human_score"] = human_scored["human_score"].astype(float).astype(int)

    kappa_a_human = cohen_kappa_score(human_scored.judge_a_score, human_scored.human_score)
    kappa_b_human = cohen_kappa_score(human_scored.judge_b_score, human_scored.human_score)
    raw_agreement_a_human = (human_scored.judge_a_score == human_scored.human_score).mean()

    print(f"Judge A vs Human ({len(human_scored)} hand-scored tasks):")
    print(f"  Raw agreement: {raw_agreement_a_human*100:.1f}%")
    print(f"  Cohen's kappa: {kappa_a_human:.3f}")
    print()
    print(f"Judge B vs Human ({len(human_scored)} hand-scored tasks):")
    print(f"  Cohen's kappa: {kappa_b_human:.3f}")


if __name__ == "__main__":
    main()