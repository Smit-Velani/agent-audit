"""
run_eval.py — Runs the full golden evaluation set through the agent, then
grades every answer with TWO independent judges. Saves each result
incrementally, so a rate-limit interruption doesn't lose prior work, and
can be safely rerun to resume exactly where it left off.
"""

import json
import time

import pandas as pd
from groq import APIStatusError

from agent import build_csv_agent, ask, set_dataframe, JUDGE_A_MODEL, JUDGE_B_MODEL
from judge import build_judge, grade

GOLDEN_SET_PATH = "data/golden_set.jsonl"
OUTPUT_PATH = "reports/eval_results.csv"


def load_golden_set(path):
    tasks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def load_already_processed(path):
    try:
        df = pd.read_csv(path)
        return set(df["id"].tolist())
    except FileNotFoundError:
        return set()


def append_result(path, result):
    df_row = pd.DataFrame([result])
    try:
        pd.read_csv(path)
        df_row.to_csv(path, mode="a", header=False, index=False)
    except FileNotFoundError:
        df_row.to_csv(path, mode="w", header=True, index=False)


def main():
    tasks = load_golden_set(GOLDEN_SET_PATH)
    already_done = load_already_processed(OUTPUT_PATH)
    remaining = [t for t in tasks if t["id"] not in already_done]

    print(f"Loaded {len(tasks)} tasks, {len(already_done)} already done, {len(remaining)} remaining.")
    if not remaining:
        print("Nothing left to do -- all tasks already processed.")
        return

    print("Building agent and two independent judges...")
    # Load the dataset before building the agent. Without this the tools
    # return "no dataset loaded" and every task fails for the wrong reason.
    set_dataframe(pd.read_csv("data/sales_data.csv"))
    agent = build_csv_agent()
    judge_a = build_judge(model=JUDGE_A_MODEL)
    judge_b = build_judge(model=JUDGE_B_MODEL)

    for i, task in enumerate(remaining, 1):
        print(f"[{i}/{len(remaining)}] {task['question'][:60]}...", flush=True)
        try:
            agent_answer = ask(agent, task["question"])
            grade_a = grade(judge_a, task["question"], agent_answer, task["expected"])
            grade_b = grade(judge_b, task["question"], agent_answer, task["expected"])
        except APIStatusError as e:
            print(f"\nHit an API error (rate limit or oversized request): {e}")
            print(f"Progress so far is saved in {OUTPUT_PATH}. If this was a daily "
                  f"token limit, wait for the reset time shown above; if it was a "
                  f"per-minute limit, waiting ~60s is usually enough. Then just "
                  f"rerun this same script -- it will skip everything already done "
                  f"and continue from here.")
            return

        result = {
            "id": task["id"],
            "category": task["category"],
            "question": task["question"],
            "expected": task["expected"],
            "agent_answer": agent_answer,
            "judge_a_score": grade_a["score"],
            "judge_a_reason": grade_a["reason"],
            "judge_b_score": grade_b["score"],
            "judge_b_reason": grade_b["reason"],
            "human_score": "",
        }
        append_result(OUTPUT_PATH, result)
        time.sleep(2)

    df = pd.read_csv(OUTPUT_PATH)
    print(f"\nAll done. {len(df)} total rows in {OUTPUT_PATH}")
    print(f"Judge A vs Judge B raw agreement: {(df.judge_a_score == df.judge_b_score).mean()*100:.1f}%")


if __name__ == "__main__":
    main()