"""
log_traces.py — Runs a handful of sample questions through the trace-
instrumented agent and appends structured records to reports/traces.jsonl.

Deliberately uses a SMALL sample (not the full golden set) to conserve
API budget -- this just seeds initial data for Phase 9's dashboard. Every
future run_eval.py run will also append here going forward.
"""

import json
import time

import pandas as pd
from agent import build_csv_agent, ask_csv, set_dataframe

TRACE_PATH = "reports/traces.jsonl"

SAMPLE_QUESTIONS = [
    "What is the average revenue per order?",
    "How many orders came from the West region?",
    "What is the total revenue grouped by customer segment?",
    "What is the variance of revenue?",
    "How many orders had more than 30 units sold?",
    "What is the average profit_margin per order?",
]


def log_trace(question, trace, version="v1"):
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": version,
        "question": question,
        "answer": trace["answer"],
        "tool_calls": trace["tool_calls"],
        "input_tokens": trace["input_tokens"],
        "output_tokens": trace["output_tokens"],
        "total_tokens": trace["total_tokens"],
        "latency_seconds": trace["latency_seconds"],
        "error": trace["error"],
    }
    with open(TRACE_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def main():
    # Load the dataset before building the agent. Without this the tools
    # return "no dataset loaded" and every task fails for the wrong reason.
    set_dataframe(pd.read_csv("data/sales_data.csv"))
    agent = build_csv_agent()
    for q in SAMPLE_QUESTIONS:
        print(f"Running: {q}")
        trace = ask_csv(agent, q)
        record = log_trace(q, trace)
        print(f"  answer: {record['answer'][:80]}")
        print(f"  tool_calls: {record['tool_calls']}")
        print(f"  tokens: {record['total_tokens']}  latency: {record['latency_seconds']}s")
        print()
        time.sleep(2)

    print(f"Logged {len(SAMPLE_QUESTIONS)} traces to {TRACE_PATH}")


if __name__ == "__main__":
    main()