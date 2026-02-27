# Agent Benchmark Runner

This repository includes a benchmark script:

- `run_agent_template_evaluation.py`

It runs a controlled comparison of two agents (Gemini and Claude) across:

- WDD YAML generation
- Workflow knowledge Markdown generation

## Requirements

- Python 3.10+ (recommended)
- CLI tools available in `PATH`:
  - `gemini`
  - `claude`
- Python dependencies in `requirements.txt`

## Create Virtual Environment

From repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configure API Keys

Edit `run_agent_template_evaluation.py` and set:

- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`

Use placeholders in source control; do not commit real keys.

## Run Benchmark

```bash
source .venv/bin/activate
python run_agent_template_evaluation.py
```

## Monitor Progress

The script prints live progress logs (task start/end, status, duration, output path).

Run outputs are written under:

- `evaluation_runs/<timestamp>/`

Key artifacts:

- `precheck.json`
- `task_order.json`
- `metrics.json`
- `metrics.csv`
- `aggregates.json`
- `run_summary.json`
