"""
red_team.py — Quantifies guardrail effectiveness on the 7 adversarial
golden-set tasks: pre-guardrail (from the original full eval run) vs
post-guardrail (rerun live with input/output guardrails active).
"""

import json
import pandas as pd

from agent import build_csv_agent, ask_safe_csv, set_dataframe, JUDGE_A_MODEL
from judge import build_judge, grade

GOLDEN_SET_PATH = "data/golden_set.jsonl"
EVAL_RESULTS_PATH = "reports/eval_results.csv"
OUTPUT_PATH = "reports/red_team_results.csv"


def load_golden_set(path):
    tasks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return {t["id"]: t for t in tasks}


def main():
    all_tasks = load_golden_set(GOLDEN_SET_PATH)
    adversarial_ids = [t["id"] for t in all_tasks.values() if t["category"] == "adversarial"]

    pre_df = pd.read_csv(EVAL_RESULTS_PATH)
    pre_adversarial = pre_df[pre_df.id.isin(adversarial_ids)]
    pre_unsafe_rate = (pre_adversarial.judge_a_score == 0).mean() * 100

    print(f"PRE-GUARDRAIL (from original run): {len(pre_adversarial)} adversarial tasks, "
          f"{pre_unsafe_rate:.0f}% scored unsafe (score=0) by Judge A.\n")

    print("Running the same tasks again, live, WITH guardrails active...\n")
    # Load the dataset before building the agent. Without this the tools
    # return "no dataset loaded" and every task fails for the wrong reason --
    # which looks like a red-team result and is not one.
    set_dataframe(pd.read_csv("data/sales_data.csv"))
    agent = build_csv_agent()
    judge = build_judge(model=JUDGE_A_MODEL)

    results = []
    for task_id in adversarial_ids:
        task = all_tasks[task_id]
        print(f"Task {task_id}: {task['question'][:60]}...")
        result = ask_safe_csv(agent, task["question"])
        g = grade(judge, task["question"], result["answer"], task["expected"])
        print(f"  answer: {result['answer'][:80]}")
        print(f"  blocked_by: {result['blocked_by']}")
        print(f"  score: {g['score']}")
        print()
        results.append({
            "id": task_id, "question": task["question"], "answer": result["answer"],
            "blocked_by": result["blocked_by"], "score": g["score"], "reason": g["reason"],
        })

    post_df = pd.DataFrame(results)
    post_df.to_csv(OUTPUT_PATH, index=False)
    post_unsafe_rate = (post_df.score == 0).mean() * 100

    print(f"\nPOST-GUARDRAIL: {post_unsafe_rate:.0f}% scored unsafe by Judge A "
          f"(was {pre_unsafe_rate:.0f}% pre-guardrail).")
    print(f"{(post_df.blocked_by.notna()).sum()}/{len(post_df)} tasks were caught by a guardrail.")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()