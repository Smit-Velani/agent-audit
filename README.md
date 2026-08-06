# AgentAudit 🔭

> AI agent evaluation harness with Scout — an interactive data analyst powered by LLaMA 3 with built-in dual-judge validation, CI regression testing, and adversarial red-teaming.

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-green?style=flat-square)](https://langchain.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA3-orange?style=flat-square)](https://groq.com)
[![CI](https://img.shields.io/badge/Tests-16%20passed-brightgreen?style=flat-square)](https://github.com/Smit-Velani/agent-audit/actions)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)

---

## Overview

AgentAudit is a full-stack AI evaluation framework built around **Scout** — a ReAct-style data analyst agent that answers questions about any uploaded CSV dataset. The project demonstrates production-grade evaluation infrastructure: not just building an agent, but rigorously proving it works.

**Live Demo:** [Coming soon on Streamlit Cloud]

---

## Key Results

| Metric | Value |
|--------|-------|
| Cohen's Kappa (Judge A vs Human) | **0.774** (substantial agreement) |
| Judge A vs Judge B agreement | 82.8% raw, κ = 0.672 |
| Regression caught | Pass rate 83% → 50% → 83% (bug introduced and fixed) |
| Red-team unsafe rate | 86% pre-guardrail → 57% post-guardrail |
| Golden set tasks | 29 (15 happy-path, 7 edge-case, 7 adversarial) |
| Test suite | 16/16 passing |

---

## Features

**Scout — CSV Data Analyst**
- Upload any CSV dataset and ask questions in natural language
- Schema-agnostic tools: `compute_stat`, `filter_count`, `list_columns`, `get_sample_rows`
- Auto-generated insights, charts, and column profiles on upload
- WhatsApp-style chat interface with suggested questions
- Every answer scored by an independent LLM judge in real time
- Full trace logging: tool calls, token usage, latency per response
- Downloadable PDF session report with all charts and conversation

**Evaluation Harness**
- 29-task golden set with hand-written rubrics across three categories
- Dual-judge validation using two independent LLM graders (LLaMA 3.3 70B + LLaMA 3.1 8B)
- Human scoring interface for Cohen's kappa computation
- Incremental-save resumable eval runner (rate-limit safe)
- CI regression suite with before/after comparison
- Adversarial red-team pass with input and output guardrails
- Harness-driven decision log documenting guardrail trade-offs

---

## Architecture

```
agent.py              # Scout ReAct agent — schema-agnostic tools, guardrails
judge.py              # LLM-as-judge grader with structured output (Pydantic)
run_eval.py           # Full golden set evaluation with dual judges
human_score.py        # Interactive hand-scoring CLI for kappa validation
compute_agreement.py  # Cohen's kappa computation
log_traces.py         # Token/latency/tool-call trace logging
red_team.py           # Adversarial evaluation with guardrail before/after
test_regression.py    # CI regression suite
app/streamlit_app.py  # Scout chat UI + analysis dashboard
```

---

## Tech Stack

- **Agent** — LangChain, LangGraph, Groq (LLaMA 3.1 8B / 3.3 70B)
- **Evaluation** — scikit-learn (Cohen's kappa), Pydantic, custom rubric grading
- **Frontend** — Streamlit, Plotly
- **PDF Reports** — ReportLab
- **Testing** — pytest, GitHub Actions CI
- **Data** — pandas, numpy

---

## Installation

```bash
git clone https://github.com/Smit-Velani/agent-audit.git
cd agent-audit
pip install -r requirements.txt
```

Create a `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```

Run the app:
```bash
streamlit run app/streamlit_app.py
```

---

## Running the Evaluation Harness

```bash
# Generate the sales dataset
python data/generate_sales_data.py

# Run full golden set evaluation (resumable)
python src/agentaudit/run_eval.py

# Hand-score a subset for kappa validation
python src/agentaudit/human_score.py

# Compute Cohen's kappa
python src/agentaudit/compute_agreement.py

# Run red-team adversarial pass
python src/agentaudit/red_team.py

# Run CI regression tests
pytest tests/ -v
```

---

## Evaluation Findings

**Dual-judge validation:** Judge A (LLaMA 3.3 70B) tracked human scoring more closely than Judge B (LLaMA 3.1 8B) — κ=0.774 vs κ=0.622. A more capable model makes a more reliable judge.

**Regression detection:** A single operator swap (`>` ↔ `<`) in `filter_count` dropped pass rate from 83% to 50%. Task 11 reported 91 orders instead of 29 — and 120 − 29 = 91 exactly, mathematical proof the specific bug caused the specific wrong output.

**Red-team findings:** Task 26 (jailbreak) caused the agent to leak its full tool schemas and hallucinate a nonexistent `brave_search` tool pre-guardrail. Post-guardrail: blocked cleanly. Task 27 surfaced a domain hallucination gap — the agent invented a customer segment called "Premium" that does not exist in the dataset. Keyword guardrails catch known attack patterns, not domain hallucination.

**Guardrail trade-off:** Blunt keyword guardrails reduced injection compliance to zero but introduced over-broad refusals on Tasks 23 and 29. Documented in `reports/decision_log.md` — kept the safer behavior deliberately.

---

## Project Structure

```
agent-audit/
├── app/                    # Streamlit dashboard
├── data/                   # Golden set, sales dataset, data generator
├── reports/                # Eval results, regression reports, red-team findings
├── src/agentaudit/         # Agent, judge, harness scripts
├── tests/                  # pytest suite
└── .github/workflows/      # GitHub Actions CI
```

---

## Author

**Smitkumar Velani** — MS Data Science, Northeastern University  
[LinkedIn](https://linkedin.com/in/smit-velani) · [GitHub](https://github.com/Smit-Velani)