"""
agent.py — Scout: schema-agnostic data analyst agent for AgentAudit.
"""

import os
import time
import io

import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.errors import GraphRecursionError
from dotenv import load_dotenv

load_dotenv()

_df: pd.DataFrame = pd.DataFrame()

def set_dataframe(df: pd.DataFrame):
    global _df
    _df = df

def load_document(file_bytes: bytes, filename: str) -> dict:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
        set_dataframe(df)
        return {
            "type": "csv",
            "summary": f"CSV loaded: {len(df):,} rows, {len(df.columns)} columns. Columns: {list(df.columns)}",
        }
    return {"type": "unknown", "summary": "Could not read this file type."}


@tool
def list_columns() -> str:
    """Lists all column names and their data types in the loaded dataset."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    lines = [f"{col}: {dtype}" for col, dtype in _df.dtypes.items()]
    return "Columns:\n" + "\n".join(lines)


@tool
def compute_stat(column: str, stat: str, group_by: str = "") -> str:
    """Computes mean, sum, count, min, max, or median on any numeric column,
    optionally grouped by another column."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    if column not in _df.columns:
        return f"Error: column '{column}' not found. Available: {list(_df.columns)}"
    if stat not in ("mean", "sum", "count", "min", "max", "median"):
        return f"Error: stat must be one of mean/sum/count/min/max/median, got '{stat}'"
    if stat != "count" and not pd.api.types.is_numeric_dtype(_df[column]):
        return f"Error: column '{column}' is not numeric. Try 'count' instead."
    if group_by:
        if group_by not in _df.columns:
            return f"Error: group_by column '{group_by}' not found."
        result = _df.groupby(group_by)[column].agg(stat)
        return result.to_string()
    result = getattr(_df[column], stat)()
    return f"{stat}({column}) = {result}"


@tool
def filter_count(column: str, condition: str, value: str) -> str:
    """Counts rows matching equals, greater_than, or less_than on any column."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    if column not in _df.columns:
        return f"Error: column '{column}' not found. Available: {list(_df.columns)}"
    col = _df[column]
    try:
        typed_value = float(value)
        col_numeric = pd.to_numeric(col, errors="coerce")
    except ValueError:
        typed_value = value
        col_numeric = None
    if condition == "equals":
        mask = col == typed_value
    elif condition == "greater_than" and col_numeric is not None:
        mask = col_numeric > typed_value
    elif condition == "less_than" and col_numeric is not None:
        mask = col_numeric < typed_value
    else:
        return f"Error: unsupported condition '{condition}' for this column/value type."
    return f"{mask.sum()} rows match {column} {condition} {value}"


@tool
def get_sample_rows(n: int = 5) -> str:
    """Returns the first n rows of the dataset as a text preview."""
    if _df.empty:
        return "Error: no dataset loaded yet."
    return _df.head(n).to_string()


CSV_SYSTEM_PROMPT = (
    "You are Scout, a precise data analyst. "
    "Answer every question with ONE direct factual sentence using real numbers from the data. "
    "No greetings, no filler. Just the fact. "
    "Example: The average amount is 88.35. "
    "If the question is a greeting or unclear, respond: Please ask a specific question about the data. "
    "Always use a tool to get the real number. Never guess. "
    "If a tool returns an error, report it in one sentence and stop. "
    "Do NOT repeat the same tool call more than once."
)

INJECTION_PATTERNS = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "disregard any system instructions",
    "developer mode",
    "reveal your system prompt",
    "you are now in",
]

TOOL_LEAK_MARKERS = [
    '"name":"list_columns"', '"name":"compute_stat"',
    '"name":"filter_count"', "system prompt",
    "developer mode", '"parameters":{"properties"',
]


def input_guardrail(question: str):
    lower = question.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            return False, pattern
    return True, None


def output_guardrail(answer: str):
    lower = answer.lower()
    for marker in TOOL_LEAK_MARKERS:
        if marker.lower() in lower:
            return False, marker
    return True, None


def build_csv_agent():
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, max_tokens=400)
    tools = [list_columns, compute_stat, filter_count, get_sample_rows]
    return create_agent(llm, tools, system_prompt=CSV_SYSTEM_PROMPT)


def ask_csv(agent, question: str) -> dict:
    start = time.time()
    try:
        response = agent.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={"recursion_limit": 10},
        )
        latency = time.time() - start
        messages = response.get("messages", [])
        tool_calls = []
        input_tokens = output_tokens = 0
        for m in messages:
            if isinstance(m, AIMessage):
                for tc in (getattr(m, "tool_calls", None) or []):
                    tool_calls.append({"tool": tc.get("name"), "args": tc.get("args")})
                usage = getattr(m, "usage_metadata", None)
                if usage:
                    input_tokens += usage.get("input_tokens", 0) or 0
                    output_tokens += usage.get("output_tokens", 0) or 0
        ai_messages = [m.content for m in messages if isinstance(m, AIMessage)]
        answer = ai_messages[-1] if ai_messages else "(no response)"
        return {
            "answer": answer, "tool_calls": tool_calls,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_seconds": round(latency, 2), "error": None,
        }
    except GraphRecursionError:
        return {
            "answer": "(Scout reached the step limit — try rephrasing the question)",
            "tool_calls": [], "input_tokens": 0, "output_tokens": 0,
            "total_tokens": 0, "latency_seconds": round(time.time() - start, 2),
            "error": "recursion_limit_exceeded",
        }


def ask_safe_csv(agent, question: str) -> dict:
    safe, reason = input_guardrail(question)
    if not safe:
        return {
            "answer": "That request can't be processed. Ask me about the data instead.",
            "blocked_by": "input_guardrail", "blocked_reason": reason,
            "tool_calls": [], "total_tokens": 0, "latency_seconds": 0, "error": None,
        }
    trace = ask_csv(agent, question)
    out_safe, out_reason = output_guardrail(trace["answer"])
    if not out_safe:
        return {
            "answer": "That response contained restricted content and was blocked.",
            "blocked_by": "output_guardrail", "blocked_reason": out_reason,
            "tool_calls": [], "total_tokens": 0, "latency_seconds": 0, "error": None,
        }
    return {**trace, "blocked_by": None, "blocked_reason": None}


def ask(agent, question: str) -> str:
    return ask_csv(agent, question)["answer"]