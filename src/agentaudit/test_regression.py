"""
test_regression.py — Runs a small, curated subset of the golden set
through the agent + Judge A, for regression testing. Run once BEFORE a
change (as baseline) and once AFTER (to check for score drops).
"""

import sys
import json
import pandas as pd

from agent import build_csv_agent, ask
from judge import build_judge, grade

GOLDEN_SET_PATH = "data/golden_set.jsonl"

# 3 tasks using filter_count(greater_than) -- directly exercises the bug --
# plus 3 controls that don't, to confirm the bug stays localized
SUBSET_IDS = [4, 11, 18, 1, 2, 13]


def load_golden_set(path):
    tasks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return {t["id"]: t for t in tasks}


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    output_path = f"reports/regression_{label}.csv"

    all_tasks = load_golden_set(GOLDEN_SET_PATH)
    tasks = [all_tasks[i] for i in SUBSET_IDS]

    agent = build_csv_agent()
    judge = build_judge(model="llama-3.3-70b-versatile")

    results = []
    for task in tasks:
        print(f"Task {task['id']}: {task['question'][:60]}...")
        answer = ask(agent, task["question"])
        g = grade(judge, task["question"], answer, task["expected"])
        print(f"  answer: {answer}")
        print(f"  score: {g['score']}  reason: {g['reason']}")
        results.append({
            "id": task["id"], "category": task["category"],
            "question": task["question"], "answer": answer,
            "score": g["score"], "reason": g["reason"],
        })

    df = pd.DataFrame(results)
    df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")
    print(f"Pass rate (score==2): {(df.score==2).mean()*100:.0f}%")


if __name__ == "__main__":
    main()