"""
human_score.py — Interactive hand-scoring tool for a subset of the golden
set, to compute judge-vs-human Cohen's kappa (the other half of Phase 4's
dual-judge validation).
"""

import pandas as pd

INPUT_PATH = "reports/eval_results.csv"


def select_subset(df, n_target=15, seed=42):
    """Includes every judge disagreement (most informative for kappa),
    then fills up to n_target with a random sample of agreement cases."""
    disagreements = df[df.judge_a_score != df.judge_b_score]
    agreements = df[df.judge_a_score == df.judge_b_score]
    n_fill = max(0, n_target - len(disagreements))
    fill = (
        agreements.sample(n=min(n_fill, len(agreements)), random_state=seed)
        if n_fill > 0
        else agreements.iloc[0:0]
    )
    return pd.concat([disagreements, fill]).sort_values("id")


def main():
    df = pd.read_csv(INPUT_PATH)
    subset = select_subset(df)
    n_disagree = (df.judge_a_score != df.judge_b_score).sum()

    print(f"Selected {len(subset)} tasks to hand-score ({n_disagree} are judge disagreements).")
    print("For each: enter your own score (0=fail, 1=partial, 2=pass), or press Enter to skip.\n")

    human_scores = {}
    for _, row in subset.iterrows():
        print(f"--- Task {row['id']} [{row['category']}] ---")
        print(f"Q: {row['question']}")
        print(f"Agent answered: {row['agent_answer']}")
        print(f"Expected: {row['expected']}")
        print(f"Judge A said: {row['judge_a_score']}  ({row['judge_a_reason']})")
        print(f"Judge B said: {row['judge_b_score']}  ({row['judge_b_reason']})")
        while True:
            resp = input("Your score (0/1/2, or Enter to skip): ").strip()
            if resp == "":
                break
            if resp in ("0", "1", "2"):
                human_scores[row["id"]] = int(resp)
                break
            print("Please enter 0, 1, 2, or leave blank to skip.")
        print()

    for task_id, score in human_scores.items():
        df.loc[df.id == task_id, "human_score"] = score

    df.to_csv(INPUT_PATH, index=False)
    print(f"Saved {len(human_scores)} human scores back to {INPUT_PATH}.")


if __name__ == "__main__":
    main()