#!/usr/bin/env python3
"""
Q&A Evaluation: Compare how well models answer workflow questions when given
ONLY workflow_knowledge (Markdown) vs. ONLY WDD (YAML) as context.

Uses three Q&A prompt files from doc/ and three models (Gemini, Claude, OpenCode).
Outputs structured results and optional LLM-as-judge scores for correctness.
"""

import argparse
import csv
import datetime as dt
import json
import os
import random
import re
import shlex
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent
DOC_DIR = REPO_ROOT / "doc"
KNOWLEDGE_DIR = REPO_ROOT / "workflow_knowledge"
WDD_DIR = REPO_ROOT / "workflow_wdd"
RESULTS_ROOT = REPO_ROOT / "evaluation_runs"
QA_EVAL_SUBDIR = "qa_eval"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "<PASTE_GEMINI_API_KEY_HERE>")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "<PASTE_ANTHROPIC_API_KEY_HERE>")

TIMEOUT_SECONDS = 300
VERBOSE = True

# Q&A prompt files (1000 Genomes)
QA_FILES = [
    DOC_DIR / "1000genome-workflow-knowledge-eval-1.txt",
    DOC_DIR / "1000genome-workflow-knowledge-eval-2.txt",
    DOC_DIR / "1000genome-workflow-knowledge-eval-3.txt",
]

# Knowledge and WDD: 1000genome, pick from trial 1-3
# Context is agent-specific: --agents claude uses claude-generated files, etc.
# Fallback to gemini when agent has no matching pairs.
WORKFLOW_PREFIX = "1000genome"
GEN_AGENT = "gemini"  # fallback when agent has no knowledge+wdd pairs


@dataclass
class Agent:
    name: str
    api_env: str
    api_key: str
    cmd_template: str
    model: str
    use_stdin: bool = False  # Pass prompt via stdin (avoids EBADF, ARG_MAX for OpenCode)


AGENTS = [
    Agent(
        name="gemini",
        api_env="GEMINI_API_KEY",
        api_key=GEMINI_API_KEY,
        cmd_template="gemini --model {model} --output-format json -p {prompt}",
        model="gemini-2.5-flash",
    ),
    Agent(
        name="claude",
        api_env="ANTHROPIC_API_KEY",
        api_key=ANTHROPIC_API_KEY,
        cmd_template="claude --output-format json -p {prompt}",
        model="sonnet-4.6-default",
    ),
    Agent(
        name="opencode",
        api_env="OPENCODE_API_KEY",
        api_key="no_key_required",
        cmd_template="/home/mtang11/.opencode/bin/opencode run -m opencode/minimax-m2.5-free --format json {prompt}",
        model="opencode/minimax-m2.5-free",
        # use_stdin=False: OpenCode rejects "stdin and input arguments may not both be used"
    ),
]


def log(msg: str) -> None:
    if VERBOSE:
        ts = dt.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)


def is_placeholder(s: str) -> bool:
    return s.strip().startswith("<") and s.strip().endswith(">")


def pick_knowledge_and_wdd(
    agent_name: str, trial: Optional[int] = None
) -> Tuple[Path, Path, int]:
    """Pick knowledge (md) and wdd (yaml) from trial 1-3 for the given agent.
    Returns (knowledge_path, wdd_path, trial_used).
    Falls back to GEN_AGENT files when agent has no matching pairs."""
    for candidate in (agent_name.lower(), GEN_AGENT):
        available = []
        for t in (1, 2, 3):
            k = KNOWLEDGE_DIR / f"{WORKFLOW_PREFIX}-knowledge-{candidate}-trial{t}.md"
            w = WDD_DIR / f"{WORKFLOW_PREFIX}-wdd-{candidate}-trial{t}.yaml"
            if k.exists() and w.exists():
                available.append((t, k, w))
        if not available:
            continue
        if trial is not None:
            chosen = [x for x in available if x[0] == trial]
            if not chosen:
                raise FileNotFoundError(
                    f"Trial {trial} not found for {agent_name}; available: {[x[0] for x in available]}"
                )
            t, k, w = chosen[0]
        else:
            t, k, w = random.choice(available)
        return k, w, t
    raise FileNotFoundError(
        f"No matching knowledge+wdd pairs for {agent_name} or fallback {GEN_AGENT}"
    )


def parse_qa_file(path: Path) -> List[Tuple[str, str, str]]:
    """Parse Q&A file. Returns list of (section, question, reference_answer)."""
    text = path.read_text(encoding="utf-8")
    items: List[Tuple[str, str, str]] = []
    current_section = ""
    current_q = ""
    current_a = ""
    for line in text.splitlines():
        if line.startswith("# ======") or line.startswith("SECTION "):
            if current_q and current_a:
                items.append((current_section, current_q.strip(), current_a.strip()))
            current_section = line.strip() if line.strip() else current_section
            current_q = ""
            current_a = ""
        elif line.strip().startswith("Q:"):
            if current_q and current_a:
                items.append((current_section, current_q.strip(), current_a.strip()))
            current_q = line.replace("Q:", "").strip()
            current_a = ""
        elif line.strip().startswith("A:"):
            current_a = line.replace("A:", "").strip()
        elif line.strip() == "---":
            if current_q and current_a:
                items.append((current_section, current_q.strip(), current_a.strip()))
            current_q = ""
            current_a = ""
        elif current_a and line.strip():
            current_a += " " + line.strip()
        elif current_q and line.strip() and not line.strip().startswith("#"):
            current_q += " " + line.strip()
    if current_q and current_a:
        items.append((current_section, current_q.strip(), current_a.strip()))
    return items


def load_all_qa() -> List[Tuple[str, str, str, str]]:
    """Load all Q&A from the three files. Returns (source_file, section, question, ref_answer)."""
    all_qa: List[Tuple[str, str, str, str]] = []
    for p in QA_FILES:
        if not p.exists():
            log(f"SKIP {p} (not found)")
            continue
        for section, q, a in parse_qa_file(p):
            all_qa.append((p.name, section, q, a))
    return all_qa


def build_qa_prompt(question: str, context: str, context_type: str) -> str:
    """Build prompt: model gets ONLY context, must answer question."""
    return f"""You are answering a question about the 1000 Genomes workflow. Use ONLY the following {context_type} as your source. Do not use external knowledge.

CONTEXT ({context_type}):
---
{context}
---

QUESTION: {question}

Provide a concise, accurate answer based only on the context above. If the context does not contain enough information, say so briefly."""


# Stderr lines to strip when agent fails (Node deprecation, MCP noise, etc.)
_STDERR_NOISE_PATTERNS = [
    r"\(node:\d+\) \[DEP0040\] DeprecationWarning:.*",
    r"\(Use `node --trace-deprecation.*",
    r"Loaded cached credentials\.?",
    r"Server '[\w-]+' supports tool updates\. Listening for changes\.\.\.?",
]


def _filter_stderr_noise(stderr: str) -> str:
    """Remove known noise from stderr (Node warnings, MCP logs) to surface actual errors."""
    lines = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(re.match(pat, stripped) for pat in _STDERR_NOISE_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines).strip() or stderr[:300]


def run_agent(agent: Agent, prompt: str) -> Tuple[bool, str, Optional[Dict]]:
    """Run agent and return (success, answer_text, tokens)."""
    cmd_parts = shlex.split(agent.cmd_template)
    cmd: List[str] = []
    for part in cmd_parts:
        if part == "{prompt}":
            if not getattr(agent, "use_stdin", False):
                cmd.append(prompt)
        else:
            cmd.append(part.format(model=agent.model))
    env = os.environ.copy()
    if agent.api_key == "no_key_required":
        env.pop(agent.api_env, None)
    else:
        env[agent.api_env] = agent.api_key
    # Suppress Node deprecation warnings for gemini CLI (Node.js-based)
    if agent.name == "gemini":
        prev = env.get("NODE_OPTIONS", "")
        env["NODE_OPTIONS"] = f"{prev} --no-deprecation".strip()
    # OpenCode: use_stdin not supported ("stdin and input arguments may not both be used")
    kwargs: Dict = {"capture_output": True, "text": True, "timeout": TIMEOUT_SECONDS, "check": False}
    if getattr(agent, "use_stdin", False):
        kwargs["stdin"] = subprocess.PIPE
        kwargs["input"] = prompt
    try:
        p = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            **kwargs,
        )
        stdout = p.stdout or ""
        stderr = p.stderr or ""
        if p.returncode != 0:
            # Try parsing stdout for JSON with error/response (Gemini may output JSON on failure)
            err_msg = None
            try:
                data = json.loads(stdout.strip())
                err_msg = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
                if not err_msg and data.get("response"):
                    err_msg = f"(partial response): {str(data.get('response', ''))[:200]}"
            except (json.JSONDecodeError, TypeError):
                pass
            if not err_msg:
                filtered = _filter_stderr_noise(stderr)
                err_msg = filtered[:500] if filtered else stderr[:500]
            return False, f"exit {p.returncode}: {err_msg}", None
        # Parse JSON for Gemini/Claude (stdout may have version prefix e.g. "0.30.1\n{...}")
        data = None
        try:
            raw = stdout.strip()
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", stdout.strip())
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        try:
            if data:
                answer = (data.get("response") or data.get("result") or "").strip()
                tokens = None
                stats = data.get("stats") or {}
                models = stats.get("models") or {}
                if models:
                    total = input_tok = output_tok = 0
                    for m in models.values() if isinstance(models, dict) else []:
                        tok = (m or {}).get("tokens") or {}
                        total += int(tok.get("total") or 0)
                        input_tok += int(tok.get("input") or tok.get("prompt") or 0)
                        output_tok += int(tok.get("output") or tok.get("completion") or 0)
                    if total or input_tok or output_tok:
                        tokens = {"total": total or (input_tok + output_tok), "input": input_tok, "output": output_tok}
            else:
                answer = stdout.strip()
                tokens = None
        except (TypeError, KeyError):
            answer = stdout.strip()
            tokens = None
        return True, answer[:4000] if answer else "(empty)", tokens
    except subprocess.TimeoutExpired:
        return False, "timeout", None
    except Exception as e:
        return False, str(e)[:500], None


def judge_answer(reference: str, model_answer: str, judge_agent: Agent) -> Optional[float]:
    """Use LLM judge to score model answer vs reference (1-5). Returns None if judge fails."""
    prompt = f"""You are evaluating how correct and complete a model's answer is compared to a reference.

REFERENCE ANSWER: {reference[:1500]}

MODEL ANSWER: {model_answer[:1500]}

Score from 1 to 5:
- 5: Fully correct and complete, matches reference
- 4: Mostly correct, minor omissions
- 3: Partially correct, some errors or omissions
- 2: Mostly incorrect or incomplete
- 1: Wrong or irrelevant

Reply with ONLY a single number (1, 2, 3, 4, or 5)."""
    ok, out, _ = run_agent(judge_agent, prompt)
    if not ok:
        return None
    m = re.search(r"\b([1-5])\b", out)
    if m:
        return float(m.group(1))
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Q&A evaluation: knowledge vs WDD context")
    parser.add_argument("--agents", required=True, help='Agents to run (e.g. "gemini,claude,opencode" or "all")')
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM-as-judge scoring")
    parser.add_argument("--trial", type=int, choices=[1, 2, 3], default=None, help="Fix trial 1-3 (default: random)")
    args = parser.parse_args()

    agent_names = [a.strip().lower() for a in args.agents.split(",") if a.strip()]
    if "all" in agent_names:
        active_agents = list(AGENTS)
    elif agent_names:
        by_name = {a.name.lower(): a for a in AGENTS}
        active_agents = [by_name[n] for n in agent_names if n in by_name]
        unknown = [n for n in agent_names if n not in by_name]
        if unknown:
            print(f"ERROR: Unknown agents: {unknown}. Available: {[a.name for a in AGENTS]}")
            return
    else:
        print("ERROR: --agents is required (e.g. 'gemini,claude,opencode' or 'all')")
        return

    # Load context per agent (claude uses claude-generated, gemini uses gemini-generated, etc.)
    agent_contexts: Dict[str, Dict] = {}
    try:
        for agent in active_agents:
            k_path, w_path, t = pick_knowledge_and_wdd(agent.name, args.trial)
            agent_contexts[agent.name] = {
                "knowledge_text": k_path.read_text(encoding="utf-8"),
                "wdd_text": w_path.read_text(encoding="utf-8"),
                "knowledge_file": k_path.name,
                "wdd_file": w_path.name,
                "trial_used": t,
            }
            log(f"{agent.name}: trial {t} — {k_path.name}, {w_path.name}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return

    all_qa = load_all_qa()
    log(f"Loaded {len(all_qa)} Q&A pairs from {len(QA_FILES)} files")

    run_start = dt.datetime.now()
    run_dir = RESULTS_ROOT / run_start.strftime("%Y%m%d-%H%M%S") / QA_EVAL_SUBDIR
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"Run directory: {run_dir}")

    records: List[Dict] = []
    judge_agent = active_agents[0] if active_agents and not is_placeholder(active_agents[0].api_key) else None

    for i, (source_file, section, question, ref_answer) in enumerate(all_qa):
        qid = f"q{i+1:03d}"
        for agent in active_agents:
            if is_placeholder(agent.api_key):
                log(f"SKIP {qid} {agent.name} | no API key")
                continue
            ctx = agent_contexts[agent.name]
            for context_type, context in [
                ("workflow_knowledge", ctx["knowledge_text"]),
                ("wdd_yaml", ctx["wdd_text"]),
            ]:
                tid = f"{qid}__{agent.name}__{context_type}"
                prompt = build_qa_prompt(question, context, context_type)
                log(f"RUN {tid}")
                timestamp = dt.datetime.now().isoformat()
                t0 = time.perf_counter()
                ok, answer, tokens = run_agent(agent, prompt)
                dur = round(time.perf_counter() - t0, 2)
                rec = {
                    "timestamp": timestamp,
                    "qid": qid,
                    "source_file": source_file,
                    "section": section,
                    "question": question[:200],
                    "reference_answer": ref_answer[:500],
                    "agent": agent.name,
                    "context_type": context_type,
                    "success": ok,
                    "model_answer": answer,
                    "duration_s": dur,
                    "total_tokens": tokens.get("total") if tokens else None,
                    "input_tokens": tokens.get("input") if tokens else None,
                    "output_tokens": tokens.get("output") if tokens else None,
                    "tokens": tokens,
                    "judge_score": None,
                    "correctness": None,
                }
                if not args.no_judge and ok and judge_agent and answer and "(empty)" not in answer:
                    score = judge_answer(ref_answer, answer, judge_agent)
                    rec["judge_score"] = score
                    rec["correctness"] = score
                records.append(rec)
                (run_dir / f"{tid}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary
    summary_path = run_dir / "summary.json"
    by_agent_context: Dict[str, List[Dict]] = {}
    for r in records:
        k = f"{r['agent']}__{r['context_type']}"
        by_agent_context.setdefault(k, []).append(r)
    summary = {}
    for k, rows in by_agent_context.items():
        scores = [r["judge_score"] for r in rows if r.get("judge_score") is not None]
        total_tokens = [r["total_tokens"] for r in rows if r.get("total_tokens") is not None]
        summary[k] = {
            "n": len(rows),
            "success": sum(1 for r in rows if r["success"]),
            "correctness_mean": round(statistics.mean(scores), 2) if scores else None,
            "correctness_std": round(statistics.stdev(scores), 2) if len(scores) > 1 else None,
            "judge_mean": round(statistics.mean(scores), 2) if scores else None,
            "judge_std": round(statistics.stdev(scores), 2) if len(scores) > 1 else None,
            "duration_mean_s": round(statistics.mean([r["duration_s"] for r in rows]), 2),
            "duration_total_s": round(sum(r["duration_s"] for r in rows), 2),
            "total_tokens_sum": sum(total_tokens) if total_tokens else None,
            "total_tokens_mean": round(statistics.mean(total_tokens), 1) if total_tokens else None,
        }
    # Build run_meta; context varies by agent
    first_ctx = agent_contexts[active_agents[0].name]
    run_meta = {
        "run_start": run_start.isoformat(),
        "trial_used": first_ctx["trial_used"],
        "knowledge_file": first_ctx["knowledge_file"],
        "wdd_file": first_ctx["wdd_file"],
        "context_by_agent": {
            a.name: {
                "knowledge_file": agent_contexts[a.name]["knowledge_file"],
                "wdd_file": agent_contexts[a.name]["wdd_file"],
                "trial_used": agent_contexts[a.name]["trial_used"],
            }
            for a in active_agents
        },
        "agents": [a.name for a in active_agents],
        "context_types": ["workflow_knowledge", "wdd_yaml"],
        "n_questions": len(all_qa),
        "summary": summary,
    }
    summary_path.write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    csv_path = run_dir / "results.csv"
    if records:
        keys = list(records[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(records)

    log("Done.")
    print(json.dumps({
        "run_dir": str(run_dir),
        "run_start": run_start.isoformat(),
        "context_by_agent": run_meta["context_by_agent"],
        "summary": summary,
    }, indent=2))


if __name__ == "__main__":
    main()
