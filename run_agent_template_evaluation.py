#!/usr/bin/env python3
# future import intentionally omitted
"""
Run agent benchmark for workflow WDD and knowledge generation.

Outputs are written to three locations:
  1. evaluation_runs/<timestamp>/  - Run metadata (precheck, metrics, aggregates, stdout/stderr logs)
  2. workflow_wdd/                 - WDD YAML files: {workflow}-wdd-{agent}-trial{N}.yaml
  3. workflow_knowledge/           - Knowledge Markdown files: {workflow}-knowledge-{agent}-trial{N}.md

Files in workflow_wdd/ and workflow_knowledge/ are created by the agents (or recovered from stdout).
A task may fail validation but still produce a file; check metrics.json for validation scores.
"""

import csv
import argparse
import datetime as dt
import json
import os
import yaml
import random
import re
import shlex
import shutil
import statistics
import subprocess
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path("/home/mtang11/scripts/workflow-representation-description")
TEMPLATE_WDD_PROMPT = REPO_ROOT / "template_wdd_gen-v7.prompt"
TEMPLATE_KNOWLEDGE_PROMPT = REPO_ROOT / "template_workflow_knowledge_gen-v7.prompt"
RESULTS_ROOT = REPO_ROOT / "evaluation_runs"
WDD_OUTPUT_DIR = REPO_ROOT / "workflow_wdd"
KNOWLEDGE_OUTPUT_DIR = REPO_ROOT / "workflow_knowledge"

# Read keys from environment variables.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "<PASTE_GEMINI_API_KEY_HERE>")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "<PASTE_ANTHROPIC_API_KEY_HERE>")


TRIALS = 3
RANDOM_SEED = 20260223
TIMEOUT_SECONDS = 3600
VERBOSE = True

WORKFLOWS = [
    {"name": "1000genome", "repo_path": str(REPO_ROOT / "workflows_repo/1000genome-workflow")}
]


@dataclass
class Agent:
    name: str
    api_env: str
    api_key: str
    cmd_template: str  # must include {prompt}
    model: str
    temperature: str
    seed: str
    max_tokens: str


AGENTS = [
    Agent(
        name="gemini",
        api_env="GEMINI_API_KEY",
        api_key=GEMINI_API_KEY,
        cmd_template="gemini --model {model} --output-format json -p {prompt}",
        model="gemini-2.5-flash",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
    Agent(
        name="claude",
        api_env="ANTHROPIC_API_KEY",
        api_key=ANTHROPIC_API_KEY,
        # Use Haiku (cheapest) to avoid credit issues; use --model sonnet for Sonnet 4.6.
        cmd_template="claude --model haiku --dangerously-skip-permissions --output-format json -p {prompt}",
        model="haiku",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
    Agent(
        name="opencode",
        api_env="OPENCODE_API_KEY",
        api_key="no_key_required",  # MiniMax M2.5 Free built-in, no API key needed
        cmd_template="/home/mtang11/.opencode/bin/opencode run -m opencode/minimax-m2.5-free {prompt}",
        model="opencode/minimax-m2.5-free",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
]

TOKEN_PATTERNS = {
    "input_tokens": [re.compile(r"(input|prompt) tokens?\s*[:=]\s*([\d,]+)", re.I)],
    "output_tokens": [re.compile(r"(output|completion) tokens?\s*[:=]\s*([\d,]+)", re.I)],
    "total_tokens": [re.compile(r"(total tokens?|tokens used)\s*[:=]\s*([\d,]+)", re.I)],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(message: str) -> None:
    if VERBOSE:
        ts = dt.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {message}", flush=True)


def is_placeholder(s: str) -> bool:
    s = s.strip()
    return s.startswith("<") and s.endswith(">")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_tokens(text: str) -> Dict[str, Optional[int]]:
    """Extract token counts from regex patterns in text (fallback when JSON unavailable)."""
    out = {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    for key, patterns in TOKEN_PATTERNS.items():
        for p in patterns:
            m = p.search(text)
            if m:
                out[key] = int(m.group(2).replace(",", ""))
                break
    return out


def parse_tokens_from_json(stdout: str) -> Tuple[Dict[str, Optional[int]], Optional[str]]:
    """
    Parse Gemini/Claude JSON output for token stats and response body.
    Returns (tokens_dict, response_text). response_text is None if not JSON or no response key.
    """
    out = {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    response_text: Optional[str] = None
    try:
        data = json.loads(stdout.strip())
        if not isinstance(data, dict):
            return out, None
        response_text = data.get("response") or data.get("result")  # Gemini uses "response", Claude uses "result"
        stats = data.get("stats") or {}
        models = stats.get("models") or {}
        # Aggregate tokens across all models (Gemini/Claude may use multiple)
        prompt_sum = 0
        candidates_sum = 0
        total_sum = 0
        for model_data in models.values() if isinstance(models, dict) else []:
            tok = (model_data or {}).get("tokens") or {}
            if isinstance(tok, dict):
                prompt_sum += int(tok.get("prompt") or 0)
                candidates_sum += int(tok.get("candidates") or 0)
                total_sum += int(tok.get("total") or 0)
        if total_sum > 0:
            out["input_tokens"] = prompt_sum or None
            out["output_tokens"] = candidates_sum or None
            out["total_tokens"] = total_sum
        elif prompt_sum or candidates_sum:
            out["input_tokens"] = prompt_sum or None
            out["output_tokens"] = candidates_sum or None
            out["total_tokens"] = prompt_sum + candidates_sum
        # Fallback: Claude may use top-level "usage" with input_tokens/output_tokens
        if not out["total_tokens"]:
            usage = data.get("usage") or {}
            if isinstance(usage, dict):
                inp = usage.get("input_tokens") or usage.get("prompt_tokens")
                out_tok = usage.get("output_tokens") or usage.get("completion_tokens")
                if inp is not None or out_tok is not None:
                    out["input_tokens"] = int(inp) if inp is not None else None
                    out["output_tokens"] = int(out_tok) if out_tok is not None else None
                    out["total_tokens"] = (out["input_tokens"] or 0) + (out["output_tokens"] or 0)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return out, response_text


def metric_text(text: str) -> Dict[str, int]:
    return {"lines": len(text.splitlines()), "words": len(re.findall(r"\S+", text)), "chars": len(text)}


def check_cli(agent: Agent) -> Tuple[bool, str]:
    exe = shlex.split(agent.cmd_template)[0]
    p = shutil.which(exe)
    return (p is not None, p or f"{exe} not found in PATH")


def resolve_active_agents(all_agents: List[Agent], selector: str) -> List[Agent]:
    selector = selector.strip().lower()
    if selector in {"", "all", "*"}:
        return list(all_agents)

    requested = [x.strip().lower() for x in selector.split(",") if x.strip()]
    by_name = {a.name.lower(): a for a in all_agents}
    missing = [name for name in requested if name not in by_name]
    if missing:
        available = ", ".join(sorted(by_name.keys()))
        raise ValueError(f"Unknown BENCH_AGENTS value(s): {', '.join(missing)}. Available: {available}")
    return [by_name[name] for name in requested]


def template_metrics(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lengths = [len(x) for x in lines] or [0]
    return {
        "file": str(path),
        "line_count": len(lines),
        "word_count": len(re.findall(r"\S+", text)),
        "char_count": len(text),
        "bullet_count": sum(1 for x in lines if x.lstrip().startswith("- ")),
        "numbered_item_count": sum(1 for x in lines if re.match(r"^\s*\d+\.", x)),
        "avg_line_length": round(statistics.mean(lengths), 2),
    }


def build_prompt(mode: str, template_text: str, wf_name: str, wf_repo: str, out_path: Path, agent: Agent) -> str:
    out_kind = "WDD YAML" if mode == "wdd" else "workflow knowledge Markdown"
    return textwrap.dedent(
        f"""
        Task: produce exactly one {out_kind} file.
        Context:
        - workflow_name: {wf_name}
        - workflow_repo_path: {wf_repo}
        - output_path: {out_path}
        - agent_name: {agent.name}
        Constraints:
        - static analysis only
        - no deployment/runtime tuning details
        - follow template instructions exactly
        - write final output to output_path (if you have file access)
        - INCLUDE THE COMPLETE FILE CONTENT IN YOUR RESPONSE so the script can save it to output_path
        - end response with: STATUS: success | OUTPUT: <output_path>
        TEMPLATE START
        {template_text}
        TEMPLATE END
        """
    ).strip()


def validate_output(mode: str, path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"valid": False, "score": 0.0, "issues": ["file_missing"]}
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return {"valid": False, "score": 0.0, "issues": ["file_empty"]}
    issues: List[str] = []
    if mode == "wdd":
        score = 0.2
        try:
            doc = yaml.safe_load(text)
            if isinstance(doc, dict):
                score += 0.4
                keys = ["metadata", "stages", "tasks", "data_objects"]
                score += 0.4 * (sum(1 for k in keys if k in doc) / len(keys))
            else:
                issues.append("yaml_not_mapping")
        except Exception as exc:  # pylint: disable=broad-except
            issues.append(f"yaml_parse_error:{exc}")
        return {"valid": score >= 0.8, "score": round(score, 3), "issues": issues}
    lower = text.lower()
    terms = ["stages", "tasks", "data", "workflow", "dependency"]
    present = sum(1 for t in terms if t in lower)
    score = 0.3 + 0.7 * (present / len(terms))
    if present < 3:
        issues.append("missing_core_terms")
    return {"valid": score >= 0.75, "score": round(score, 3), "issues": issues}


def _is_valid_workflow_payload(payload: str, mode: str) -> bool:
    """Reject error messages or trivial content; require structural indicators."""
    if not payload or len(payload.strip()) < 100:
        return False
    # Reject common error/API messages.
    lower = payload.lower()
    for reject in ("credit balance is too low", "permission denied", "api key", "error:", "is_error", "rate limit"):
        if reject in lower and len(payload) < 500:
            return False
    if mode == "wdd":
        return bool(re.search(r"(metadata|workflow_name|schema_version)\s*:", payload))
    return bool(re.search(r"(workflow|task|stage|# )", payload, re.I))


def _extract_payload_from_stdout(stdout: str, mode: str) -> Optional[str]:
    """Best-effort extraction when agent prints result instead of writing file."""
    if not stdout.strip():
        return None

    # Trim trailing status line if present.
    status_idx = stdout.rfind("STATUS:")
    body = stdout[:status_idx] if status_idx != -1 else stdout
    body = body.strip()

    if not body:
        return None

    # Prefer fenced code blocks when available.
    if mode == "wdd":
        yaml_block = re.search(r"```(?:yaml|yml)?\n(.*?)\n```", body, re.DOTALL | re.IGNORECASE)
        if yaml_block:
            return yaml_block.group(1).strip() + "\n"
        # Fallback: attempt from first likely YAML key.
        yaml_start = re.search(r"(?m)^(metadata|schema_version|workflow_name)\s*:", body)
        if yaml_start:
            return body[yaml_start.start():].strip() + "\n"
    else:
        md_block = re.search(r"```(?:markdown|md)?\n(.*?)\n```", body, re.DOTALL | re.IGNORECASE)
        if md_block:
            return md_block.group(1).strip() + "\n"
        return body + "\n"

    return None


def run_one(run_dir: Path, task: Dict[str, object]) -> Dict[str, object]:
    agent: Agent = task["agent"]  # type: ignore[assignment]
    tid = str(task["task_id"])
    mode = str(task["mode"])
    out_path: Path = task["out_path"]  # type: ignore[assignment]
    prompt = str(task["prompt"])
    slug = re.sub(r"[^a-z0-9_.-]+", "_", tid.lower())
    prompt_path = run_dir / f"{slug}.prompt.txt"
    stdout_path = run_dir / f"{slug}.stdout.log"
    stderr_path = run_dir / f"{slug}.stderr.log"
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    # Build argv safely so multiline prompt is passed as one argument.
    cmd_parts = shlex.split(agent.cmd_template)
    cmd: List[str] = []
    for part in cmd_parts:
        if part == "{prompt}":
            cmd.append(prompt)
        else:
            cmd.append(
                part.format(
                    model=agent.model,
                    temperature=agent.temperature,
                    seed=agent.seed,
                    max_tokens=agent.max_tokens,
                )
            )
    env = os.environ.copy()
    if agent.api_key == "no_key_required":
        # Free model (e.g. OpenCode minimax-m2.5-free): do not set API key;
        # remove it from env so the CLI does not receive an invalid key.
        env.pop(agent.api_env, None)
    else:
        env[agent.api_env] = agent.api_key
    # OpenCode: allow reading workflow repo without permission prompts (YOLO mode)
    if agent.name.lower() == "opencode":
        env["OPENCODE_YOLO"] = "true"
        env["OPENCODE_DANGEROUSLY_SKIP_PERMISSIONS"] = "true"
    t0 = time.perf_counter()
    rec: Dict[str, object] = {
        "task_id": tid,
        "trial": task["trial"],
        "agent": agent.name,
        "mode": mode,
        "workflow": task["workflow"],
        "status": "unknown",
        "started_at": now_iso(),
        "finished_at": None,
        "duration_s": None,
        "exit_code": None,
        "error": None,
        "prompt_path": str(prompt_path),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "output_path": str(out_path),
        "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "validation": None,
        "output_metrics": None,
        "model_control": {
            "model": agent.model,
            "temperature": agent.temperature,
            "seed": agent.seed,
            "max_tokens": agent.max_tokens,
            "cmd_template": agent.cmd_template,
        },
    }
    log(f"START {tid} | agent={agent.name} mode={mode} output={out_path}")
    try:
        p = subprocess.run(
            cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
        )
        stdout_path.write_text(p.stdout or "", encoding="utf-8")
        stderr_path.write_text(p.stderr or "", encoding="utf-8")
        rec["exit_code"] = p.returncode
        rec["status"] = "ok" if p.returncode == 0 else "failed"
        if p.returncode != 0:
            rec["error"] = f"non-zero exit {p.returncode}"
        # Token extraction: prefer JSON stats (Gemini/Claude --output-format json), else regex.
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        tokens_from_json, response_text = parse_tokens_from_json(p.stdout or "")
        if tokens_from_json.get("total_tokens") or tokens_from_json.get("input_tokens"):
            rec["tokens"] = tokens_from_json
        else:
            rec["tokens"] = parse_tokens(combined)
        # Fallback: if agent did not write output file, try capturing payload from stdout or JSON response.
        # Run even when returncode != 0 so we can recover content from agents that exit non-zero.
        if not out_path.exists():
            body = response_text if response_text else (p.stdout or "")
            payload = _extract_payload_from_stdout(body, mode)
            if payload and _is_valid_workflow_payload(payload, mode):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(payload, encoding="utf-8")
                log(f"RECOVERED {tid} | wrote output from stdout to {out_path}")
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
        rec["status"] = "timeout"
        rec["error"] = f"timeout>{TIMEOUT_SECONDS}s"
    except Exception as exc:  # pylint: disable=broad-except
        stderr_path.write_text(str(exc), encoding="utf-8")
        rec["status"] = "error"
        rec["error"] = str(exc)
    rec["duration_s"] = round(time.perf_counter() - t0, 3)
    rec["finished_at"] = now_iso()
    rec["validation"] = validate_output(mode, out_path)
    if out_path.exists():
        txt = out_path.read_text(encoding="utf-8", errors="ignore")
        rec["output_metrics"] = metric_text(txt) | {"exists": True, "bytes": out_path.stat().st_size}
    else:
        rec["output_metrics"] = {"exists": False, "bytes": 0, "lines": 0, "words": 0, "chars": 0}
    if rec["status"] == "ok" and not rec["validation"]["valid"]:  # type: ignore[index]
        rec["status"] = "failed_validation"
        rec["error"] = rec["error"] or "output_invalid"
    log(
        f"DONE {tid} | status={rec['status']} duration={rec['duration_s']}s "
        f"validation={rec['validation']['score']} output={out_path}"  # type: ignore[index]
    )
    return rec


def flatten(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for r in records:
        row = dict(r)
        tok = row.pop("tokens", {})
        val = row.pop("validation", {})
        outm = row.pop("output_metrics", {})
        mc = row.pop("model_control", {})
        row.update(
            {
                "input_tokens": tok.get("input_tokens") if isinstance(tok, dict) else None,
                "output_tokens": tok.get("output_tokens") if isinstance(tok, dict) else None,
                "total_tokens": tok.get("total_tokens") if isinstance(tok, dict) else None,
                "validation_valid": val.get("valid") if isinstance(val, dict) else None,
                "validation_score": val.get("score") if isinstance(val, dict) else None,
                "validation_issues": ";".join(val.get("issues", [])) if isinstance(val, dict) else None,
                "output_exists": outm.get("exists") if isinstance(outm, dict) else None,
                "output_bytes": outm.get("bytes") if isinstance(outm, dict) else None,
                "output_lines": outm.get("lines") if isinstance(outm, dict) else None,
                "output_words": outm.get("words") if isinstance(outm, dict) else None,
                "model": mc.get("model") if isinstance(mc, dict) else None,
                "temperature": mc.get("temperature") if isinstance(mc, dict) else None,
                "seed": mc.get("seed") if isinstance(mc, dict) else None,
                "max_tokens": mc.get("max_tokens") if isinstance(mc, dict) else None,
            }
        )
        rows.append(row)
    return rows


def aggregate(records: List[Dict[str, object]]) -> Dict[str, object]:
    g: Dict[str, List[Dict[str, object]]] = {}
    for r in records:
        g.setdefault(f"{r['agent']}__{r['mode']}", []).append(r)
    out: Dict[str, object] = {}
    for k, rows in g.items():
        dur = [float(x["duration_s"]) for x in rows if isinstance(x.get("duration_s"), (int, float))]
        val = [float(x["validation"]["score"]) for x in rows if isinstance(x.get("validation"), dict)]  # type: ignore[index]
        passed = sum(1 for x in rows if isinstance(x.get("validation"), dict) and x["validation"].get("valid"))  # type: ignore[index]
        out[k] = {
            "n": len(rows),
            "duration_mean_s": round(statistics.mean(dur), 3) if dur else None,
            "duration_std_s": round(statistics.pstdev(dur), 3) if len(dur) > 1 else 0.0,
            "validation_mean": round(statistics.mean(val), 3) if val else None,
            "validation_pass_rate": round(passed / len(rows), 3) if rows else 0.0,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run controlled agent benchmark.")
    parser.add_argument(
        "--agents",
        default="all",
        help='Comma-separated agent names to run (e.g. "claude" or "gemini,claude"). Default: all',
    )
    args = parser.parse_args()

    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    WDD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_dir = RESULTS_ROOT / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    run_started = now_iso()
    log(f"Run directory: {run_dir}")
    log(f"Output dirs: workflow_wdd={WDD_OUTPUT_DIR}, workflow_knowledge={KNOWLEDGE_OUTPUT_DIR}")

    active_agents = resolve_active_agents(AGENTS, args.agents)
    log(f"Active agents for this run: {', '.join(a.name for a in active_agents)}")

    pre = {"api": {}, "cli": {}, "active_agents": [a.name for a in active_agents]}
    for a in active_agents:
        pre["api"][a.name] = {"configured": not is_placeholder(a.api_key), "env_var": a.api_env}
        ok, info = check_cli(a)
        pre["cli"][a.name] = {"ok": ok, "info": info}
    write_json(run_dir / "precheck.json", pre)
    log("Precheck written (API/CLI availability).")
    write_json(
        run_dir / "template_metrics.json",
        {"wdd_template": template_metrics(TEMPLATE_WDD_PROMPT), "knowledge_template": template_metrics(TEMPLATE_KNOWLEDGE_PROMPT)},
    )
    log("Template metrics computed.")

    wdd_tpl = TEMPLATE_WDD_PROMPT.read_text(encoding="utf-8")
    kn_tpl = TEMPLATE_KNOWLEDGE_PROMPT.read_text(encoding="utf-8")
    tasks: List[Dict[str, object]] = []
    for trial in range(1, TRIALS + 1):
        for wf in WORKFLOWS:
            for a in active_agents:
                for mode in ("wdd", "knowledge"):
                    out_path = (
                        WDD_OUTPUT_DIR / f"{wf['name']}-wdd-{a.name}-trial{trial}.yaml"
                        if mode == "wdd"
                        else KNOWLEDGE_OUTPUT_DIR / f"{wf['name']}-knowledge-{a.name}-trial{trial}.md"
                    )
                    tpl = wdd_tpl if mode == "wdd" else kn_tpl
                    tasks.append(
                        {
                            "task_id": f"trial{trial}__{a.name}__{mode}__{wf['name']}",
                            "trial": trial,
                            "agent": a,
                            "mode": mode,
                            "workflow": wf["name"],
                            "repo": wf["repo_path"],
                            "out_path": out_path,
                            "prompt": build_prompt(mode, tpl, wf["name"], wf["repo_path"], out_path, a),
                        }
                    )

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(tasks)
    log(f"Task matrix ready: {len(tasks)} tasks (trials={TRIALS}, seed={RANDOM_SEED}).")
    write_json(
        run_dir / "task_order.json",
        [{"task_id": t["task_id"], "agent": t["agent"].name, "mode": t["mode"]} for t in tasks],  # type: ignore[index]
    )

    records: List[Dict[str, object]] = []
    for t in tasks:
        a: Agent = t["agent"]  # type: ignore[assignment]
        if is_placeholder(a.api_key):
            log(f"SKIP {t['task_id']} | missing API key placeholder for {a.name}")
            records.append(
                {
                    "task_id": t["task_id"],
                    "trial": t["trial"],
                    "agent": a.name,
                    "mode": t["mode"],
                    "workflow": t["workflow"],
                    "status": "skipped",
                    "started_at": now_iso(),
                    "finished_at": now_iso(),
                    "duration_s": 0.0,
                    "exit_code": None,
                    "error": f"{a.api_env} placeholder not replaced",
                    "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
                    "validation": {"valid": False, "score": 0.0, "issues": ["skipped_no_api_key"]},
                    "output_metrics": {"exists": False, "bytes": 0, "lines": 0, "words": 0, "chars": 0},
                    "model_control": {
                        "model": a.model,
                        "temperature": a.temperature,
                        "seed": a.seed,
                        "max_tokens": a.max_tokens,
                        "cmd_template": a.cmd_template,
                    },
                }
            )
            continue
        records.append(
            run_one(
                run_dir=run_dir,
                task={
                    "task_id": t["task_id"],
                    "trial": t["trial"],
                    "agent": a,
                    "mode": t["mode"],
                    "workflow": t["workflow"],
                    "out_path": t["out_path"],
                    "prompt": t["prompt"],
                },
            )
        )

    write_json(
        run_dir / "metrics.json",
        {"run_started_at": run_started, "run_finished_at": now_iso(), "trials": TRIALS, "random_seed": RANDOM_SEED, "records": records},
    )
    rows = flatten(records)
    csv_path = run_dir / "metrics.csv"
    if rows:
        all_keys = sorted(set().union(*(r.keys() for r in rows)))
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    write_json(run_dir / "aggregates.json", aggregate(records))
    log("Aggregates written.")

    # Collect workflow outputs created this run (from records' output_path)
    created_wdd: List[str] = []
    created_knowledge: List[str] = []
    for r in records:
        out = r.get("output_path")
        if not out:
            continue
        p = Path(out)
        if p.exists():
            try:
                rel = str(p.relative_to(REPO_ROOT))
            except ValueError:
                rel = str(p)
            if p.suffix in (".yaml", ".yml"):
                created_wdd.append(rel)
            elif p.suffix == ".md":
                created_knowledge.append(rel)
    summary = {
        "run_dir": str(run_dir),
        "precheck": str(run_dir / "precheck.json"),
        "task_order": str(run_dir / "task_order.json"),
        "metrics_json": str(run_dir / "metrics.json"),
        "metrics_csv": str(csv_path),
        "aggregates": str(run_dir / "aggregates.json"),
        "workflow_wdd_created": created_wdd,
        "workflow_knowledge_created": created_knowledge,
    }
    write_json(run_dir / "run_summary.json", summary)
    log("Run complete. Summary written.")
    if created_wdd or created_knowledge:
        log(f"Workflow outputs: {len(created_wdd)} WDD, {len(created_knowledge)} knowledge")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
    raise SystemExit(0)
#!/usr/bin/env python3
# future import intentionally omitted

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
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path("/home/mtang11/scripts/workflow-representation-description")
TEMPLATE_WDD_PROMPT = REPO_ROOT / "template_wdd_gen-v7.prompt"
TEMPLATE_KNOWLEDGE_PROMPT = REPO_ROOT / "template_workflow_knowledge_gen-v7.prompt"

RESULTS_ROOT = REPO_ROOT / "evaluation_runs"
WDD_OUTPUT_DIR = REPO_ROOT / "workflow_wdd"
KNOWLEDGE_OUTPUT_DIR = REPO_ROOT / "workflow_knowledge"

# Replace placeholders before running.
GEMINI_API_KEY = "<PASTE_GEMINI_API_KEY_HERE>"
ANTHROPIC_API_KEY = "<PASTE_ANTHROPIC_API_KEY_HERE>"

TRIALS = 3
RANDOM_SEED = 20260223
TIMEOUT_SECONDS = 3600

WORKFLOWS = [
    {"name": "1000genome", "repo_path": str(REPO_ROOT / "workflows_repo/1000genome-workflow")}
]


@dataclass
class Agent:
    name: str
    api_env: str
    api_key: str
    # Must include {prompt}. You can also include {model}/{temperature}/{seed}/{max_tokens}.
    cmd_template: str
    model: str
    temperature: str
    seed: str
    max_tokens: str


AGENTS = [
    Agent(
        name="gemini",
        api_env="GEMINI_API_KEY",
        api_key=GEMINI_API_KEY,
        cmd_template="gemini -p {prompt}",
        model="<SET_GEMINI_MODEL>",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
    Agent(
        name="claude",
        api_env="ANTHROPIC_API_KEY",
        api_key=ANTHROPIC_API_KEY,
        cmd_template="claude --dangerously-skip-permissions -p {prompt}",
        model="<SET_CLAUDE_MODEL>",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
]


TOKEN_PATTERNS = {
    "input_tokens": [re.compile(r"(input|prompt) tokens?\s*[:=]\s*([\d,]+)", re.I)],
    "output_tokens": [re.compile(r"(output|completion) tokens?\s*[:=]\s*([\d,]+)", re.I)],
    "total_tokens": [re.compile(r"(total tokens?|tokens used)\s*[:=]\s*([\d,]+)", re.I)],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def is_placeholder(s: str) -> bool:
    s = s.strip()
    return s.startswith("<") and s.endswith(">")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_tokens(text: str) -> Dict[str, Optional[int]]:
    out: Dict[str, Optional[int]] = {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    for k, patterns in TOKEN_PATTERNS.items():
        for p in patterns:
            m = p.search(text)
            if m:
                out[k] = int(m.group(2).replace(",", ""))
                break
    return out


def metric_text(text: str) -> Dict[str, int]:
    return {"lines": len(text.splitlines()), "words": len(re.findall(r"\S+", text)), "chars": len(text)}


def check_cli(agent: Agent) -> Tuple[bool, str]:
    exe = shlex.split(agent.cmd_template)[0]
    path = shutil.which(exe)
    return (path is not None, path or f"{exe} not in PATH")


def build_prompt(mode: str, template_text: str, wf_name: str, wf_repo: str, out_path: Path, agent: Agent) -> str:
    out_kind = "WDD YAML" if mode == "wdd" else "workflow knowledge Markdown"
    return textwrap.dedent(
        f"""
        Task: produce exactly one {out_kind} file.
        Context:
        - workflow_name: {wf_name}
        - workflow_repo_path: {wf_repo}
        - output_path: {out_path}
        - agent_name: {agent.name}

        Constraints:
        - static analysis only
        - no deployment/runtime tuning details
        - follow template instructions exactly
        - write final output to output_path
        - end response with: STATUS: success | OUTPUT: <output_path>

        TEMPLATE START
        {template_text}
        TEMPLATE END
        """
    ).strip()


def validate_output(mode: str, out_path: Path) -> Dict[str, object]:
    issues: List[str] = []
    if not out_path.exists():
        return {"valid": False, "score": 0.0, "issues": ["file_missing"]}
    text = out_path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return {"valid": False, "score": 0.0, "issues": ["file_empty"]}

    if mode == "wdd":
        score = 0.2
        try:
            import yaml  # type: ignore

            doc = yaml.safe_load(text)
            if isinstance(doc, dict):
                score += 0.4
                keys = ["metadata", "stages", "tasks", "data_objects"]
                present = sum(1 for k in keys if k in doc)
                score += 0.4 * (present / len(keys))
            else:
                issues.append("yaml_not_mapping")
        except Exception as exc:  # pylint: disable=broad-except
            issues.append(f"yaml_parse_error:{exc}")
        return {"valid": score >= 0.8, "score": round(score, 3), "issues": issues}

    lower = text.lower()
    terms = ["stages", "tasks", "data", "workflow", "dependency"]
    present = sum(1 for t in terms if t in lower)
    score = 0.3 + 0.7 * (present / len(terms))
    if present < 3:
        issues.append("missing_core_terms")
    return {"valid": score >= 0.75, "score": round(score, 3), "issues": issues}


def run_task(run_dir: Path, task: Dict[str, object]) -> Dict[str, object]:
    agent: Agent = task["agent"]  # type: ignore[assignment]
    task_id = str(task["task_id"])
    mode = str(task["mode"])
    out_path: Path = task["out_path"]  # type: ignore[assignment]
    prompt_text = str(task["prompt_text"])

    slug = re.sub(r"[^a-z0-9_.-]+", "_", task_id.lower())
    prompt_file = run_dir / f"{slug}.prompt.txt"
    stdout_file = run_dir / f"{slug}.stdout.log"
    stderr_file = run_dir / f"{slug}.stderr.log"
    prompt_file.write_text(prompt_text + "\n", encoding="utf-8")

    cmd = shlex.split(
        agent.cmd_template.format(
            prompt=prompt_text,
            model=agent.model,
            temperature=agent.temperature,
            seed=agent.seed,
            max_tokens=agent.max_tokens,
        )
    )
    env = os.environ.copy()
    env[agent.api_env] = agent.api_key

    started = now_iso()
    t0 = time.perf_counter()
    rec: Dict[str, object] = {
        "task_id": task_id,
        "trial": task["trial"],
        "agent": agent.name,
        "mode": mode,
        "workflow": task["workflow"],
        "status": "unknown",
        "started_at": started,
        "finished_at": None,
        "duration_s": None,
        "exit_code": None,
        "error": None,
        "prompt_path": str(prompt_file),
        "stdout_log": str(stdout_file),
        "stderr_log": str(stderr_file),
        "output_path": str(out_path),
        "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "validation": None,
        "output_metrics": None,
        "model_control": {
            "model": agent.model,
            "temperature": agent.temperature,
            "seed": agent.seed,
            "max_tokens": agent.max_tokens,
            "cmd_template": agent.cmd_template,
        },
    }

    try:
        p = subprocess.run(
            cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
        )
        stdout_file.write_text(p.stdout or "", encoding="utf-8")
        stderr_file.write_text(p.stderr or "", encoding="utf-8")
        rec["exit_code"] = p.returncode
        rec["status"] = "ok" if p.returncode == 0 else "failed"
        if p.returncode != 0:
            rec["error"] = f"non-zero exit {p.returncode}"
        rec["tokens"] = parse_tokens((p.stdout or "") + "\n" + (p.stderr or ""))
    except subprocess.TimeoutExpired as exc:
        stdout_file.write_text(exc.stdout or "", encoding="utf-8")
        stderr_file.write_text(exc.stderr or "", encoding="utf-8")
        rec["status"] = "timeout"
        rec["error"] = f"timeout>{TIMEOUT_SECONDS}s"
    except Exception as exc:  # pylint: disable=broad-except
        stderr_file.write_text(str(exc), encoding="utf-8")
        rec["status"] = "error"
        rec["error"] = str(exc)

    rec["duration_s"] = round(time.perf_counter() - t0, 3)
    rec["finished_at"] = now_iso()
    rec["validation"] = validate_output(mode, out_path)
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8", errors="ignore")
        rec["output_metrics"] = metric_text(text) | {"bytes": out_path.stat().st_size, "exists": True}
    else:
        rec["output_metrics"] = {"exists": False, "bytes": 0, "lines": 0, "words": 0, "chars": 0}

    if rec["status"] == "ok" and not rec["validation"]["valid"]:  # type: ignore[index]
        rec["status"] = "failed_validation"
        rec["error"] = rec["error"] or "output_invalid"
    return rec


def flatten(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows = []
    for r in records:
        row = dict(r)
        tok = row.pop("tokens", {})
        val = row.pop("validation", {})
        outm = row.pop("output_metrics", {})
        mc = row.pop("model_control", {})
        row.update(
            {
                "input_tokens": tok.get("input_tokens") if isinstance(tok, dict) else None,
                "output_tokens": tok.get("output_tokens") if isinstance(tok, dict) else None,
                "total_tokens": tok.get("total_tokens") if isinstance(tok, dict) else None,
                "validation_valid": val.get("valid") if isinstance(val, dict) else None,
                "validation_score": val.get("score") if isinstance(val, dict) else None,
                "validation_issues": ";".join(val.get("issues", [])) if isinstance(val, dict) else None,
                "output_exists": outm.get("exists") if isinstance(outm, dict) else None,
                "output_bytes": outm.get("bytes") if isinstance(outm, dict) else None,
                "output_lines": outm.get("lines") if isinstance(outm, dict) else None,
                "output_words": outm.get("words") if isinstance(outm, dict) else None,
                "model": mc.get("model") if isinstance(mc, dict) else None,
                "temperature": mc.get("temperature") if isinstance(mc, dict) else None,
                "seed": mc.get("seed") if isinstance(mc, dict) else None,
                "max_tokens": mc.get("max_tokens") if isinstance(mc, dict) else None,
            }
        )
        rows.append(row)
    return rows


def aggregate(records: List[Dict[str, object]]) -> Dict[str, object]:
    groups: Dict[str, List[Dict[str, object]]] = {}
    for r in records:
        groups.setdefault(f"{r['agent']}__{r['mode']}", []).append(r)
    out: Dict[str, object] = {}
    for k, rows in groups.items():
        dur = [float(x["duration_s"]) for x in rows if isinstance(x.get("duration_s"), (int, float))]
        val = [float(x["validation"]["score"]) for x in rows if isinstance(x.get("validation"), dict)]  # type: ignore[index]
        pass_n = sum(1 for x in rows if isinstance(x.get("validation"), dict) and x["validation"].get("valid"))  # type: ignore[index]
        out[k] = {
            "n": len(rows),
            "duration_mean_s": round(statistics.mean(dur), 3) if dur else None,
            "duration_std_s": round(statistics.pstdev(dur), 3) if len(dur) > 1 else 0.0,
            "validation_mean": round(statistics.mean(val), 3) if val else None,
            "validation_pass_rate": round(pass_n / len(rows), 3) if rows else 0.0,
        }
    return out


def main() -> None:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    WDD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_started = now_iso()
    run_dir = RESULTS_ROOT / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    pre = {"api": {}, "cli": {}}
    for a in AGENTS:
        pre["api"][a.name] = {"configured": not is_placeholder(a.api_key), "env_var": a.api_env}
        ok, info = check_cli(a)
        pre["cli"][a.name] = {"ok": ok, "info": info}
    write_json(run_dir / "precheck.json", pre)

    write_json(
        run_dir / "template_metrics.json",
        {
            "wdd_template": template_metrics(TEMPLATE_WDD_PROMPT),
            "knowledge_template": template_metrics(TEMPLATE_KNOWLEDGE_PROMPT),
        },
    )

    wdd_tpl = TEMPLATE_WDD_PROMPT.read_text(encoding="utf-8")
    kn_tpl = TEMPLATE_KNOWLEDGE_PROMPT.read_text(encoding="utf-8")

    tasks: List[Dict[str, object]] = []
    for trial in range(1, TRIALS + 1):
        for wf in WORKFLOWS:
            wf_name = wf["name"]
            wf_repo = wf["repo_path"]
            for a in AGENTS:
                for mode in ("wdd", "knowledge"):
                    out_path = (
                        WDD_OUTPUT_DIR / f"{wf_name}-wdd-{a.name}-trial{trial}.yaml"
                        if mode == "wdd"
                        else KNOWLEDGE_OUTPUT_DIR / f"{wf_name}-knowledge-{a.name}-trial{trial}.md"
                    )
                    tpl = wdd_tpl if mode == "wdd" else kn_tpl
                    tasks.append(
                        {
                            "task_id": f"trial{trial}__{a.name}__{mode}__{wf_name}",
                            "trial": trial,
                            "agent": a,
                            "mode": mode,
                            "workflow": wf_name,
                            "repo": wf_repo,
                            "out_path": out_path,
                            "prompt_text": build_prompt(mode, tpl, wf_name, wf_repo, out_path, a),
                        }
                    )

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(tasks)
    write_json(
        run_dir / "task_order.json",
        [{"task_id": t["task_id"], "agent": t["agent"].name, "mode": t["mode"]} for t in tasks],  # type: ignore[index]
    )

    records: List[Dict[str, object]] = []
    for t in tasks:
        a: Agent = t["agent"]  # type: ignore[assignment]
        if is_placeholder(a.api_key):
            records.append(
                {
                    "task_id": t["task_id"],
                    "trial": t["trial"],
                    "agent": a.name,
                    "mode": t["mode"],
                    "workflow": t["workflow"],
                    "status": "skipped",
                    "started_at": now_iso(),
                    "finished_at": now_iso(),
                    "duration_s": 0.0,
                    "exit_code": None,
                    "error": f"{a.api_env} placeholder not replaced",
                    "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
                    "validation": {"valid": False, "score": 0.0, "issues": ["skipped_no_api_key"]},
                    "output_metrics": {"exists": False, "bytes": 0, "lines": 0, "words": 0, "chars": 0},
                    "model_control": {
                        "model": a.model,
                        "temperature": a.temperature,
                        "seed": a.seed,
                        "max_tokens": a.max_tokens,
                        "cmd_template": a.cmd_template,
                    },
                }
            )
            continue

        records.append(
            run_task(
                run_dir=run_dir,
                task=t["task_id"],  # type: ignore[arg-type]
                agent=a,
                mode=t["mode"],  # type: ignore[arg-type]
                workflow_name=t["workflow"],  # type: ignore[arg-type]
                workflow_repo_path=t["repo"],  # type: ignore[arg-type]
                output_path=t["out_path"],  # type: ignore[arg-type]
                prompt_text=t["prompt_text"],  # type: ignore[arg-type]
            )
        )

    write_json(
        run_dir / "metrics.json",
        {
            "run_started_at": run_started,
            "run_finished_at": now_iso(),
            "trials": TRIALS,
            "random_seed": RANDOM_SEED,
            "records": records,
        },
    )

    rows = flatten(records)
    csv_path = run_dir / "metrics.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_json(run_dir / "aggregates.json", aggregate(records))
    summary = {
        "run_dir": str(run_dir),
        "precheck": str(run_dir / "precheck.json"),
        "task_order": str(run_dir / "task_order.json"),
        "metrics_json": str(run_dir / "metrics.json"),
        "metrics_csv": str(csv_path),
        "aggregates": str(run_dir / "aggregates.json"),
    }
    write_json(run_dir / "run_summary.json", summary)
    print(json.dumps(summary, indent=2))


if False and __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Controlled evaluation: Gemini vs Claude on two output modes.

Compares:
1) Structured WDD YAML generation
2) Generic workflow knowledge Markdown generation

Controls:
- Fixed templates (no agent-authored intermediate prompts)
- Same workflow repo input across all conditions
- Randomized task order with fixed seed
- Repeated trials
- Validation + quantitative metrics collection
"""

# future import intentionally omitted

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
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path("/home/mtang11/scripts/workflow-representation-description")
TEMPLATE_WDD_PROMPT = REPO_ROOT / "template_wdd_gen-v7.prompt"
TEMPLATE_KNOWLEDGE_PROMPT = REPO_ROOT / "template_workflow_knowledge_gen-v7.prompt"

RESULTS_ROOT = REPO_ROOT / "evaluation_runs"
WDD_OUTPUT_DIR = REPO_ROOT / "workflow_wdd"
KNOWLEDGE_OUTPUT_DIR = REPO_ROOT / "workflow_knowledge"

# Hard-coded placeholders (replace before running).
GEMINI_API_KEY = "<PASTE_GEMINI_API_KEY_HERE>"
ANTHROPIC_API_KEY = "<PASTE_ANTHROPIC_API_KEY_HERE>"

TRIALS = 3
RANDOM_SEED = 20260223
TASK_TIMEOUT_SECONDS = 3600

WORKFLOWS = [
    {
        "name": "1000genome",
        "repo_path": str(REPO_ROOT / "workflows_repo/1000genome-workflow"),
    }
]


@dataclass
class AgentConfig:
    name: str
    api_env_var: str
    api_key_value: str
    # Must include "{prompt}".
    command_template: str
    # For audit and control metadata.
    model_id: str
    temperature: str
    seed: str
    max_tokens: str


AGENTS: List[AgentConfig] = [
    AgentConfig(
        name="gemini",
        api_env_var="GEMINI_API_KEY",
        api_key_value=GEMINI_API_KEY,
        command_template="gemini -p {prompt}",
        model_id="<SET_GEMINI_MODEL_ID>",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
    AgentConfig(
        name="claude",
        api_env_var="ANTHROPIC_API_KEY",
        api_key_value=ANTHROPIC_API_KEY,
        command_template="claude -p {prompt}",
        model_id="<SET_CLAUDE_MODEL_ID>",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
]

TOKEN_PATTERNS = {
    "input_tokens": [
        re.compile(r"input tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"prompt tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
    "output_tokens": [
        re.compile(r"output tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"completion tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
    "total_tokens": [
        re.compile(r"total tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"tokens used\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def ensure_dirs() -> None:
    for path in [RESULTS_ROOT, WDD_OUTPUT_DIR, KNOWLEDGE_OUTPUT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def parse_tokens(output_text: str) -> Dict[str, Optional[int]]:
    parsed = {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    for key, patterns in TOKEN_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(output_text)
            if match:
                parsed[key] = int(match.group(1).replace(",", ""))
                break
    return parsed


def is_placeholder(value: str) -> bool:
    v = value.strip()
    return v.startswith("<") and v.endswith(">")


def check_cli_exists(agent: AgentConfig) -> Tuple[bool, str]:
    parts = shlex.split(agent.command_template)
    if not parts:
        return False, "empty command template"
    exe = parts[0]
    resolved = shutil.which(exe)
    if not resolved:
        return False, f"CLI not found in PATH: {exe}"
    return True, resolved


def template_metrics(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lengths = [len(line) for line in lines] or [0]
    return {
        "file": str(path),
        "line_count": len(lines),
        "word_count": word_count(text),
        "char_count": len(text),
        "bullet_count": sum(1 for l in lines if l.lstrip().startswith("- ")),
        "numbered_item_count": sum(1 for l in lines if re.match(r"^\s*\d+\.", l)),
        "avg_line_length": round(statistics.mean(lengths), 2),
    }


def build_execution_prompt(
    mode: str,
    template_text: str,
    workflow_name: str,
    workflow_repo_path: str,
    output_path: Path,
    agent_name: str,
) -> str:
    mode_name = "WDD YAML" if mode == "wdd" else "workflow knowledge Markdown"
    return textwrap.dedent(
        f"""
        You must complete exactly one task: produce {mode_name}.

        Fixed context:
        - workflow_name: {workflow_name}
        - workflow_repo_path: {workflow_repo_path}
        - output_path: {output_path}
        - agent_name: {agent_name}

        Strict constraints:
        - Use static repository analysis only.
        - Do not include deployment/runtime tuning details.
        - Follow the template instructions exactly.
        - Write final output to output_path.
        - End with one line: STATUS: success | OUTPUT: <output_path>

        TEMPLATE START
        {template_text}
        TEMPLATE END
        """
    ).strip()


def collect_output_metrics(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"exists": False, "bytes": 0, "lines": 0, "words": 0}
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "exists": True,
        "bytes": path.stat().st_size,
        "lines": len(text.splitlines()),
        "words": word_count(text),
    }


def validate_wdd_yaml(path: Path) -> Dict[str, object]:
    result = {"valid": False, "score": 0.0, "issues": []}
    if not path.exists():
        result["issues"].append("file_missing")
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        result["issues"].append("file_empty")
        return result

    score = 0.2
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            score += 0.4
            required_keys = ["metadata", "stages", "tasks", "data_objects"]
            present = sum(1 for key in required_keys if key in parsed)
            score += 0.4 * (present / len(required_keys))
        else:
            result["issues"].append("yaml_not_mapping")
    except Exception as exc:  # pylint: disable=broad-except
        result["issues"].append(f"yaml_parse_error:{exc}")

    result["score"] = round(score, 3)
    result["valid"] = score >= 0.8
    return result


def validate_knowledge_md(path: Path) -> Dict[str, object]:
    result = {"valid": False, "score": 0.0, "issues": []}
    if not path.exists():
        result["issues"].append("file_missing")
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        result["issues"].append("file_empty")
        return result

    lower = text.lower()
    must_terms = ["stages", "tasks", "data", "workflow", "dependency"]
    present = sum(1 for t in must_terms if t in lower)
    score = 0.3 + 0.7 * (present / len(must_terms))
    if present < 3:
        result["issues"].append("missing_core_sections_or_terms")
    result["score"] = round(score, 3)
    result["valid"] = score >= 0.75
    return result


def run_agent_task(
    run_dir: Path,
    task_id: str,
    agent: AgentConfig,
    mode: str,
    workflow_name: str,
    workflow_repo_path: str,
    output_path: Path,
    prompt_text: str,
) -> Dict[str, object]:
    slug = re.sub(r"[^a-z0-9_.-]+", "_", task_id.lower())
    prompt_path = run_dir / f"{slug}.prompt.txt"
    stdout_path = run_dir / f"{slug}.stdout.log"
    stderr_path = run_dir / f"{slug}.stderr.log"
    prompt_path.write_text(prompt_text + "\n", encoding="utf-8")

    cmd = shlex.split(
        agent.command_template.format(
            prompt=prompt_text,
            model=agent.model_id,
            temperature=agent.temperature,
            seed=agent.seed,
            max_tokens=agent.max_tokens,
        )
    )

    env = os.environ.copy()
    env[agent.api_env_var] = agent.api_key_value

    started_at = now_iso()
    t0 = time.perf_counter()
    record: Dict[str, object] = {
        "task_id": task_id,
        "agent": agent.name,
        "mode": mode,
        "workflow_name": workflow_name,
        "workflow_repo_path": workflow_repo_path,
        "output_path": str(output_path),
        "prompt_path": str(prompt_path),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "started_at": started_at,
        "finished_at": None,
        "duration_seconds": None,
        "exit_code": None,
        "status": "unknown",
        "error": None,
        "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "output_metrics": None,
        "validation": None,
        "model_control": {
            "model_id": agent.model_id,
            "temperature": agent.temperature,
            "seed": agent.seed,
            "max_tokens": agent.max_tokens,
            "command_template": agent.command_template,
        },
    }

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT_SECONDS,
            check=False,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        stdout_path.write_text(proc.stdout or "", encoding="utf-8")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8")
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")

        record["duration_seconds"] = elapsed
        record["finished_at"] = now_iso()
        record["exit_code"] = proc.returncode
        record["tokens"] = parse_tokens(combined)
        record["status"] = "ok" if proc.returncode == 0 else "failed"
        if proc.returncode != 0:
            record["error"] = f"non-zero exit code {proc.returncode}"
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.perf_counter() - t0, 3)
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
        record["duration_seconds"] = elapsed
        record["finished_at"] = now_iso()
        record["status"] = "timeout"
        record["error"] = f"timeout after {TASK_TIMEOUT_SECONDS}s"
    except Exception as exc:  # pylint: disable=broad-except
        elapsed = round(time.perf_counter() - t0, 3)
        stderr_path.write_text(str(exc), encoding="utf-8")
        record["duration_seconds"] = elapsed
        record["finished_at"] = now_iso()
        record["status"] = "error"
        record["error"] = str(exc)

    record["output_metrics"] = collect_output_metrics(output_path)
    record["validation"] = validate_wdd_yaml(output_path) if mode == "wdd" else validate_knowledge_md(output_path)

    exists = bool(record["output_metrics"]["exists"])  # type: ignore[index]
    valid = bool(record["validation"]["valid"])  # type: ignore[index]
    if record["status"] == "ok" and (not exists or not valid):
        record["status"] = "failed_validation"
        if not record["error"]:
            record["error"] = "output_missing_or_invalid"

    return record


def flatten_for_csv(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for rec in records:
        row = dict(rec)
        tokens = row.pop("tokens", {})
        validation = row.pop("validation", {})
        output_metrics = row.pop("output_metrics", {})
        model_control = row.pop("model_control", {})

        if isinstance(tokens, dict):
            row["input_tokens"] = tokens.get("input_tokens")
            row["output_tokens"] = tokens.get("output_tokens")
            row["total_tokens"] = tokens.get("total_tokens")
        if isinstance(validation, dict):
            row["validation_valid"] = validation.get("valid")
            row["validation_score"] = validation.get("score")
            row["validation_issues"] = ";".join(validation.get("issues", []))
        if isinstance(output_metrics, dict):
            row["output_exists"] = output_metrics.get("exists")
            row["output_bytes"] = output_metrics.get("bytes")
            row["output_lines"] = output_metrics.get("lines")
            row["output_words"] = output_metrics.get("words")
        if isinstance(model_control, dict):
            row["model_id"] = model_control.get("model_id")
            row["temperature"] = model_control.get("temperature")
            row["seed"] = model_control.get("seed")
            row["max_tokens"] = model_control.get("max_tokens")
        rows.append(row)
    return rows


def aggregate(records: List[Dict[str, object]]) -> Dict[str, object]:
    grouped: Dict[str, List[Dict[str, object]]] = {}
    for rec in records:
        key = f"{rec['agent']}__{rec['mode']}"
        grouped.setdefault(key, []).append(rec)

    out: Dict[str, object] = {}
    for key, rows in grouped.items():
        durations = [float(r["duration_seconds"]) for r in rows if isinstance(r.get("duration_seconds"), (int, float))]
        val_scores = [float(r["validation"]["score"]) for r in rows if isinstance(r.get("validation"), dict)]  # type: ignore[index]
        token_totals = [
            r["tokens"].get("total_tokens")  # type: ignore[index]
            for r in rows
            if isinstance(r.get("tokens"), dict)
        ]
        token_totals = [int(x) for x in token_totals if isinstance(x, int)]
        pass_count = sum(
            1 for r in rows if isinstance(r.get("validation"), dict) and r["validation"].get("valid") is True  # type: ignore[index]
        )
        out[key] = {
            "n": len(rows),
            "duration_mean_s": round(statistics.mean(durations), 3) if durations else None,
            "duration_std_s": round(statistics.pstdev(durations), 3) if len(durations) > 1 else 0.0,
            "validation_mean": round(statistics.mean(val_scores), 3) if val_scores else None,
            "validation_pass_rate": round(pass_count / len(rows), 3) if rows else 0.0,
            "total_tokens_mean": round(statistics.mean(token_totals), 3) if token_totals else None,
        }
    return out


def main() -> None:
    ensure_dirs()
    run_started_at = now_iso()
    run_stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RESULTS_ROOT / run_stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    precheck: Dict[str, object] = {"api_key_checks": {}, "cli_checks": {}}
    for agent in AGENTS:
        precheck["api_key_checks"][agent.name] = {
            "configured": not is_placeholder(agent.api_key_value),
            "env_var": agent.api_env_var,
        }
        ok, info = check_cli_exists(agent)
        precheck["cli_checks"][agent.name] = {"ok": ok, "info": info}
    write_json(run_dir / "precheck.json", precheck)

    template_stats = {
        "wdd_template_metrics": template_metrics(TEMPLATE_WDD_PROMPT),
        "knowledge_template_metrics": template_metrics(TEMPLATE_KNOWLEDGE_PROMPT),
    }
    write_json(run_dir / "template_metrics.json", template_stats)

    wdd_template_text = TEMPLATE_WDD_PROMPT.read_text(encoding="utf-8")
    knowledge_template_text = TEMPLATE_KNOWLEDGE_PROMPT.read_text(encoding="utf-8")

    tasks: List[Dict[str, object]] = []
    for trial in range(1, TRIALS + 1):
        for wf in WORKFLOWS:
            wf_name = wf["name"]
            wf_repo = wf["repo_path"]
            for agent in AGENTS:
                for mode in ("wdd", "knowledge"):
                    output_path = (
                        WDD_OUTPUT_DIR / f"{wf_name}-wdd-{agent.name}-trial{trial}.yaml"
                        if mode == "wdd"
                        else KNOWLEDGE_OUTPUT_DIR / f"{wf_name}-knowledge-{agent.name}-trial{trial}.md"
                    )
                    template_text = wdd_template_text if mode == "wdd" else knowledge_template_text
                    prompt_text = build_execution_prompt(
                        mode=mode,
                        template_text=template_text,
                        workflow_name=wf_name,
                        workflow_repo_path=wf_repo,
                        output_path=output_path,
                        agent_name=agent.name,
                    )
                    tasks.append(
                        {
                            "task_id": f"trial{trial}__{agent.name}__{mode}__{wf_name}",
                            "trial": trial,
                            "agent": agent,
                            "mode": mode,
                            "workflow_name": wf_name,
                            "workflow_repo_path": wf_repo,
                            "output_path": output_path,
                            "prompt_text": prompt_text,
                        }
                    )

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(tasks)
    write_json(
        run_dir / "task_order.json",
        [{"task_id": t["task_id"], "agent": t["agent"].name, "mode": t["mode"]} for t in tasks],  # type: ignore[index]
    )

    records: List[Dict[str, object]] = []
    for task in tasks:
        agent: AgentConfig = task["agent"]  # type: ignore[assignment]
        if is_placeholder(agent.api_key_value):
            records.append(
                {
                    "task_id": task["task_id"],
                    "agent": agent.name,
                    "mode": task["mode"],
                    "workflow_name": task["workflow_name"],
                    "workflow_repo_path": task["workflow_repo_path"],
                    "output_path": str(task["output_path"]),
                    "prompt_path": None,
                    "stdout_log": None,
                    "stderr_log": None,
                    "started_at": now_iso(),
                    "finished_at": now_iso(),
                    "duration_seconds": 0.0,
                    "exit_code": None,
                    "status": "skipped",
                    "error": f"{agent.api_env_var} placeholder not replaced",
                    "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
                    "output_metrics": collect_output_metrics(task["output_path"]),  # type: ignore[arg-type]
                    "validation": {"valid": False, "score": 0.0, "issues": ["skipped_no_api_key"]},
                    "model_control": {
                        "model_id": agent.model_id,
                        "temperature": agent.temperature,
                        "seed": agent.seed,
                        "max_tokens": agent.max_tokens,
                        "command_template": agent.command_template,
                    },
                }
            )
            continue

        records.append(
            run_agent_task(
                run_dir=run_dir,
                task_id=task["task_id"],  # type: ignore[arg-type]
                agent=agent,
                mode=task["mode"],  # type: ignore[arg-type]
                workflow_name=task["workflow_name"],  # type: ignore[arg-type]
                workflow_repo_path=task["workflow_repo_path"],  # type: ignore[arg-type]
                output_path=task["output_path"],  # type: ignore[arg-type]
                prompt_text=task["prompt_text"],  # type: ignore[arg-type]
            )
        )

    write_json(
        run_dir / "metrics.json",
        {
            "run_started_at": run_started_at,
            "run_finished_at": now_iso(),
            "trials": TRIALS,
            "random_seed": RANDOM_SEED,
            "records": records,
        },
    )

    flat = flatten_for_csv(records)
    csv_path = run_dir / "metrics.csv"
    if flat:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(flat[0].keys()))
            writer.writeheader()
            writer.writerows(flat)

    aggregates = aggregate(records)
    write_json(run_dir / "aggregates.json", aggregates)

    summary = {
        "run_dir": str(run_dir),
        "precheck_json": str(run_dir / "precheck.json"),
        "template_metrics_json": str(run_dir / "template_metrics.json"),
        "task_order_json": str(run_dir / "task_order.json"),
        "metrics_json": str(run_dir / "metrics.json"),
        "metrics_csv": str(csv_path),
        "aggregates_json": str(run_dir / "aggregates.json"),
    }
    write_json(run_dir / "run_summary.json", summary)
    print(json.dumps(summary, indent=2))


if False and __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Controlled evaluation: Gemini vs Claude on two output modes

Goal:
- Compare two agents on the same workflow-understanding task with two output modes:
  1) Structured WDD YAML
  2) Generic workflow knowledge Markdown

Design controls:
- Fixed templates (no agent-authored intermediate prompts).
- Same workflow inputs for all conditions.
- Randomized task order (deterministic seed).
- Multiple trials.
- Per-run validation + quantitative metrics.
"""

# future import intentionally omitted

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
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# User configuration
# -----------------------------------------------------------------------------

REPO_ROOT = Path("/home/mtang11/scripts/workflow-representation-description")
TEMPLATE_WDD_PROMPT = REPO_ROOT / "template_wdd_gen-v7.prompt"
TEMPLATE_KNOWLEDGE_PROMPT = REPO_ROOT / "template_workflow_knowledge_gen-v7.prompt"

RESULTS_ROOT = REPO_ROOT / "evaluation_runs"
RENDERED_PROMPTS_DIR = REPO_ROOT / "evaluation_rendered_prompts"
WDD_OUTPUT_DIR = REPO_ROOT / "workflow_wdd"
KNOWLEDGE_OUTPUT_DIR = REPO_ROOT / "workflow_knowledge"

# Hard-coded placeholders as requested. Replace values before running.
GEMINI_API_KEY = "<PASTE_GEMINI_API_KEY_HERE>"
ANTHROPIC_API_KEY = "<PASTE_ANTHROPIC_API_KEY_HERE>"

# Controlled experiment settings
TRIALS = 3
RANDOM_SEED = 20260223
TASK_TIMEOUT_SECONDS = 3600

WORKFLOWS = [
    {
        "name": "1000genome",
        "repo_path": str(REPO_ROOT / "workflows_repo/1000genome-workflow"),
    }
]


@dataclass
class AgentConfig:
    name: str
    api_env_var: str
    api_key_value: str
    # Must include "{prompt}".
    # For strict control, keep model/temp/seed/max_tokens fixed in this template.
    command_template: str
    # Metadata for audit/comparison
    model_id: str
    temperature: str
    seed: str
    max_tokens: str


AGENTS: List[AgentConfig] = [
    AgentConfig(
        name="gemini",
        api_env_var="GEMINI_API_KEY",
        api_key_value=GEMINI_API_KEY,
        command_template="gemini -p {prompt}",
        model_id="<SET_GEMINI_MODEL_ID>",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
    AgentConfig(
        name="claude",
        api_env_var="ANTHROPIC_API_KEY",
        api_key_value=ANTHROPIC_API_KEY,
        command_template="claude -p {prompt}",
        model_id="<SET_CLAUDE_MODEL_ID>",
        temperature="<SET_TEMP>",
        seed="<SET_SEED>",
        max_tokens="<SET_MAX_TOKENS>",
    ),
]


TOKEN_PATTERNS = {
    "input_tokens": [
        re.compile(r"input tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"prompt tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
    "output_tokens": [
        re.compile(r"output tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"completion tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
    "total_tokens": [
        re.compile(r"total tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"tokens used\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
}


# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def ensure_dirs() -> None:
    for path in [RESULTS_ROOT, RENDERED_PROMPTS_DIR, WDD_OUTPUT_DIR, KNOWLEDGE_OUTPUT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def template_metrics(path: Path) -> Dict[str, float]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    line_lengths = [len(x) for x in lines] or [0]
    bullets = sum(1 for line in lines if line.lstrip().startswith("- "))
    numbered = sum(1 for line in lines if re.match(r"^\s*\d+\.", line))
    return {
        "file": str(path),
        "line_count": len(lines),
        "word_count": word_count(text),
        "char_count": len(text),
        "bullet_count": bullets,
        "numbered_item_count": numbered,
        "avg_line_length": round(statistics.mean(line_lengths), 2),
    }


def parse_tokens(output_text: str) -> Dict[str, Optional[int]]:
    parsed = {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    for key, patterns in TOKEN_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(output_text)
            if match:
                parsed[key] = int(match.group(1).replace(",", ""))
                break
    return parsed


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def check_cli_exists(agent: AgentConfig) -> Tuple[bool, str]:
    parts = shlex.split(agent.command_template)
    if not parts:
        return False, "empty command template"
    exe = parts[0]
    resolved = shutil.which(exe)
    if resolved is None:
        return False, f"CLI not found in PATH: {exe}"
    return True, resolved


def is_placeholder(value: str) -> bool:
    return value.strip().startswith("<") and value.strip().endswith(">")


# -----------------------------------------------------------------------------
# Prompt rendering (fixed across agents except agent metadata)
# -----------------------------------------------------------------------------

def build_execution_prompt(
    mode: str,
    template_text: str,
    workflow_name: str,
    workflow_repo_path: str,
    output_path: Path,
    agent: AgentConfig,
) -> str:
    mode_name = "WDD YAML" if mode == "wdd" else "workflow knowledge Markdown"
    return textwrap.dedent(
        f"""
        You must complete exactly one task: produce {mode_name}.

        Fixed context:
        - workflow_name: {workflow_name}
        - workflow_repo_path: {workflow_repo_path}
        - output_path: {output_path}
        - agent_name: {agent.name}

        Strict constraints:
        - Use static repository analysis only.
        - Do not include deployment/runtime tuning decisions.
        - Follow the template instructions below.
        - Write final result to output_path.
        - End with one line: STATUS: success | OUTPUT: <output_path>

        TEMPLATE START
        {template_text}
        TEMPLATE END
        """
    ).strip()


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

def validate_wdd_yaml(path: Path) -> Dict[str, object]:
    result = {"valid": False, "score": 0.0, "issues": []}
    if not path.exists():
        result["issues"].append("file_missing")
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        result["issues"].append("file_empty")
        return result

    score = 0.2
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            score += 0.4
            required_keys = ["metadata", "stages", "tasks", "data_objects"]
            present = sum(1 for k in required_keys if k in parsed)
            score += 0.4 * (present / len(required_keys))
        else:
            result["issues"].append("yaml_not_mapping")
    except Exception as exc:  # pylint: disable=broad-except
        result["issues"].append(f"yaml_parse_error:{exc}")

    result["score"] = round(score, 3)
    result["valid"] = score >= 0.8
    return result


def validate_knowledge_md(path: Path) -> Dict[str, object]:
    result = {"valid": False, "score": 0.0, "issues": []}
    if not path.exists():
        result["issues"].append("file_missing")
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        result["issues"].append("file_empty")
        return result

    score = 0.3
    lower = text.lower()
    must_terms = ["stages", "tasks", "data", "workflow", "dependency"]
    present = sum(1 for term in must_terms if term in lower)
    score += 0.7 * (present / len(must_terms))
    if present < 3:
        result["issues"].append("missing_core_sections_or_terms")

    result["score"] = round(score, 3)
    result["valid"] = score >= 0.75
    return result


def collect_output_metrics(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"exists": False, "bytes": 0, "lines": 0, "words": 0}
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "exists": True,
        "bytes": path.stat().st_size,
        "lines": len(text.splitlines()),
        "words": word_count(text),
    }


# -----------------------------------------------------------------------------
# Task execution
# -----------------------------------------------------------------------------

def run_agent_task(
    run_dir: Path,
    task_id: str,
    agent: AgentConfig,
    mode: str,
    workflow_name: str,
    workflow_repo_path: str,
    output_path: Path,
    prompt_text: str,
) -> Dict[str, object]:
    slug = re.sub(r"[^a-z0-9_.-]+", "_", task_id.lower())
    prompt_path = run_dir / f"{slug}.prompt.txt"
    stdout_path = run_dir / f"{slug}.stdout.log"
    stderr_path = run_dir / f"{slug}.stderr.log"
    prompt_path.write_text(prompt_text + "\n", encoding="utf-8")

    cmd = shlex.split(
        agent.command_template.format(
            prompt=prompt_text,
            model=agent.model_id,
            temperature=agent.temperature,
            seed=agent.seed,
            max_tokens=agent.max_tokens,
        )
    )

    env = os.environ.copy()
    env[agent.api_env_var] = agent.api_key_value

    started_at = now_iso()
    t0 = time.perf_counter()
    record: Dict[str, object] = {
        "task_id": task_id,
        "mode": mode,
        "agent": agent.name,
        "workflow_name": workflow_name,
        "workflow_repo_path": workflow_repo_path,
        "output_path": str(output_path),
        "prompt_path": str(prompt_path),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "started_at": started_at,
        "finished_at": None,
        "duration_seconds": None,
        "exit_code": None,
        "status": "unknown",
        "error": None,
        "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "output_metrics": None,
        "validation": None,
        "model_control": {
            "model_id": agent.model_id,
            "temperature": agent.temperature,
            "seed": agent.seed,
            "max_tokens": agent.max_tokens,
            "command_template": agent.command_template,
        },
    }

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT_SECONDS,
            check=False,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        stdout_path.write_text(proc.stdout or "", encoding="utf-8")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8")
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")

        record["duration_seconds"] = elapsed
        record["finished_at"] = now_iso()
        record["exit_code"] = proc.returncode
        record["tokens"] = parse_tokens(combined)
        record["status"] = "ok" if proc.returncode == 0 else "failed"
        if proc.returncode != 0:
            record["error"] = f"non-zero exit code {proc.returncode}"
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.perf_counter() - t0, 3)
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
        record["duration_seconds"] = elapsed
        record["finished_at"] = now_iso()
        record["status"] = "timeout"
        record["error"] = f"timeout after {TASK_TIMEOUT_SECONDS}s"
    except Exception as exc:  # pylint: disable=broad-except
        elapsed = round(time.perf_counter() - t0, 3)
        stderr_path.write_text(str(exc), encoding="utf-8")
        record["duration_seconds"] = elapsed
        record["finished_at"] = now_iso()
        record["status"] = "error"
        record["error"] = str(exc)

    # Strict post-checks for controlled run quality
    record["output_metrics"] = collect_output_metrics(output_path)
    if mode == "wdd":
        record["validation"] = validate_wdd_yaml(output_path)
    else:
        record["validation"] = validate_knowledge_md(output_path)

    # Force failure label when output is missing/invalid, even if CLI returned 0.
    valid = bool(record["validation"]["valid"])  # type: ignore[index]
    exists = bool(record["output_metrics"]["exists"])  # type: ignore[index]
    if record["status"] == "ok" and (not exists or not valid):
        record["status"] = "failed_validation"
        if not record["error"]:
            record["error"] = "output_missing_or_invalid"

    return record


# -----------------------------------------------------------------------------
# Experiment orchestration
# -----------------------------------------------------------------------------

def flatten_for_csv(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for rec in records:
        row = dict(rec)
        tokens = row.pop("tokens", {})
        validation = row.pop("validation", {})
        output_metrics = row.pop("output_metrics", {})
        model_control = row.pop("model_control", {})

        if isinstance(tokens, dict):
            row["input_tokens"] = tokens.get("input_tokens")
            row["output_tokens"] = tokens.get("output_tokens")
            row["total_tokens"] = tokens.get("total_tokens")
        if isinstance(validation, dict):
            row["validation_valid"] = validation.get("valid")
            row["validation_score"] = validation.get("score")
            row["validation_issues"] = ";".join(validation.get("issues", []))
        if isinstance(output_metrics, dict):
            row["output_exists"] = output_metrics.get("exists")
            row["output_bytes"] = output_metrics.get("bytes")
            row["output_lines"] = output_metrics.get("lines")
            row["output_words"] = output_metrics.get("words")
        if isinstance(model_control, dict):
            row["model_id"] = model_control.get("model_id")
            row["temperature"] = model_control.get("temperature")
            row["seed"] = model_control.get("seed")
            row["max_tokens"] = model_control.get("max_tokens")
        rows.append(row)
    return rows


def aggregate(records: List[Dict[str, object]]) -> Dict[str, object]:
    groups: Dict[str, List[Dict[str, object]]] = {}
    for rec in records:
        key = f"{rec['agent']}__{rec['mode']}"
        groups.setdefault(key, []).append(rec)

    summary: Dict[str, object] = {}
    for key, rows in groups.items():
        durations = [
            float(r["duration_seconds"]) for r in rows
            if isinstance(r.get("duration_seconds"), (int, float))
        ]
        validation_scores = [
            float(r["validation"]["score"])  # type: ignore[index]
            for r in rows if isinstance(r.get("validation"), dict)
        ]
        success_count = sum(
            1 for r in rows if r.get("status") in {"ok", "failed_validation", "failed"}
        )
        pass_count = sum(
            1 for r in rows
            if isinstance(r.get("validation"), dict) and r["validation"].get("valid") is True
        )
        summary[key] = {
            "n": len(rows),
            "duration_mean_s": round(statistics.mean(durations), 3) if durations else None,
            "duration_std_s": round(statistics.pstdev(durations), 3) if len(durations) > 1 else 0.0,
            "validation_mean": round(statistics.mean(validation_scores), 3) if validation_scores else None,
            "validation_pass_rate": round(pass_count / success_count, 3) if success_count else 0.0,
        }
    return summary


def main() -> None:
    ensure_dirs()
    run_started_at = now_iso()
    run_stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RESULTS_ROOT / run_stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    # Precheck keys + CLI
    precheck: Dict[str, object] = {"api_key_checks": {}, "cli_checks": {}}
    for agent in AGENTS:
        key_ok = not is_placeholder(agent.api_key_value)
        precheck["api_key_checks"][agent.name] = {
            "env_var": agent.api_env_var,
            "configured": key_ok,
        }
        cli_ok, cli_info = check_cli_exists(agent)
        precheck["cli_checks"][agent.name] = {"ok": cli_ok, "info": cli_info}
    write_json(run_dir / "precheck.json", precheck)

    # Fixed template stats
    template_stats = {
        "wdd_template_metrics": template_metrics(TEMPLATE_WDD_PROMPT),
        "knowledge_template_metrics": template_metrics(TEMPLATE_KNOWLEDGE_PROMPT),
    }
    write_json(run_dir / "template_metrics.json", template_stats)

    wdd_template_text = TEMPLATE_WDD_PROMPT.read_text(encoding="utf-8")
    knowledge_template_text = TEMPLATE_KNOWLEDGE_PROMPT.read_text(encoding="utf-8")

    # Build controlled task matrix (2 agents x 2 modes x workflows x trials)
    tasks: List[Dict[str, object]] = []
    for trial in range(1, TRIALS + 1):
        for wf in WORKFLOWS:
            workflow_name = wf["name"]
            workflow_repo_path = wf["repo_path"]
            for agent in AGENTS:
                for mode in ("wdd", "knowledge"):
                    out_path = (
                        WDD_OUTPUT_DIR / f"{workflow_name}-wdd-{agent.name}-trial{trial}.yaml"
                        if mode == "wdd"
                        else KNOWLEDGE_OUTPUT_DIR / f"{workflow_name}-knowledge-{agent.name}-trial{trial}.md"
                    )
                    template_text = wdd_template_text if mode == "wdd" else knowledge_template_text
                    prompt_text = build_execution_prompt(
                        mode=mode,
                        template_text=template_text,
                        workflow_name=workflow_name,
                        workflow_repo_path=workflow_repo_path,
                        output_path=out_path,
                        agent=agent,
                    )
                    task_id = f"trial{trial}__{agent.name}__{mode}__{workflow_name}"
                    tasks.append(
                        {
                            "task_id": task_id,
                            "trial": trial,
                            "agent": agent,
                            "mode": mode,
                            "workflow_name": workflow_name,
                            "workflow_repo_path": workflow_repo_path,
                            "output_path": out_path,
                            "prompt_text": prompt_text,
                        }
                    )

    # Randomize task order to reduce order bias
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(tasks)
    write_json(
        run_dir / "task_order.json",
        [{"task_id": t["task_id"], "mode": t["mode"], "agent": t["agent"].name} for t in tasks],  # type: ignore[index]
    )

    records: List[Dict[str, object]] = []
    for task in tasks:
        agent: AgentConfig = task["agent"]  # type: ignore[assignment]
        if is_placeholder(agent.api_key_value):
            records.append(
                {
                    "task_id": task["task_id"],
                    "mode": task["mode"],
                    "agent": agent.name,
                    "workflow_name": task["workflow_name"],
                    "workflow_repo_path": task["workflow_repo_path"],
                    "output_path": str(task["output_path"]),
                    "prompt_path": None,
                    "stdout_log": None,
                    "stderr_log": None,
                    "started_at": now_iso(),
                    "finished_at": now_iso(),
                    "duration_seconds": 0.0,
                    "exit_code": None,
                    "status": "skipped",
                    "error": f"{agent.api_env_var} placeholder not replaced",
                    "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
                    "output_metrics": collect_output_metrics(task["output_path"]),  # type: ignore[arg-type]
                    "validation": {"valid": False, "score": 0.0, "issues": ["skipped_no_api_key"]},
                    "model_control": {
                        "model_id": agent.model_id,
                        "temperature": agent.temperature,
                        "seed": agent.seed,
                        "max_tokens": agent.max_tokens,
                        "command_template": agent.command_template,
                    },
                }
            )
            continue

        rec = run_agent_task(
            run_dir=run_dir,
            task_id=task["task_id"],  # type: ignore[arg-type]
            agent=agent,
            mode=task["mode"],  # type: ignore[arg-type]
            workflow_name=task["workflow_name"],  # type: ignore[arg-type]
            workflow_repo_path=task["workflow_repo_path"],  # type: ignore[arg-type]
            output_path=task["output_path"],  # type: ignore[arg-type]
            prompt_text=task["prompt_text"],  # type: ignore[arg-type]
        )
        records.append(rec)

    # Persist records
    write_json(
        run_dir / "metrics.json",
        {
            "run_started_at": run_started_at,
            "run_finished_at": now_iso(),
            "trials": TRIALS,
            "random_seed": RANDOM_SEED,
            "records": records,
        },
    )

    flat = flatten_for_csv(records)
    csv_path = run_dir / "metrics.csv"
    if flat:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(flat[0].keys()))
            writer.writeheader()
            writer.writerows(flat)

    aggregates = aggregate(records)
    write_json(run_dir / "aggregates.json", aggregates)

    summary = {
        "run_dir": str(run_dir),
        "records_json": str(run_dir / "metrics.json"),
        "records_csv": str(csv_path),
        "aggregates_json": str(run_dir / "aggregates.json"),
        "template_metrics_json": str(run_dir / "template_metrics.json"),
        "task_order_json": str(run_dir / "task_order.json"),
    }
    write_json(run_dir / "run_summary.json", summary)
    print(json.dumps(summary, indent=2))


if False and __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Run Gemini + Claude workflow-prompt evaluation end-to-end.

What this script does:
1) Asks each agent to compare the two template prompts (qualitative + quantitative).
2) Asks each agent to generate two workflow-specific prompts per workflow:
   - {agent}-{workflow}-wdd-gen.prompt
   - {agent}-{workflow}-knowledge-gen.prompt
3) Uses each generated WDD prompt to produce:
   - workflow_wdd/{workflow}-wdd-{agent}.yaml
4) Uses each generated knowledge prompt to produce:
   - workflow_knowledge/{workflow}-knowledge-{agent}.md
5) Records timing, token hints (when present in CLI output), and summary metrics.

Notes:
- API keys are placeholders; set real values before running.
- Agent command templates may need adjustment for your local CLI flags.
"""

# future import intentionally omitted

import csv
import datetime as dt
import json
import os
import re
import shlex
import shutil
import statistics
import subprocess
import textwrap
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path("/home/mtang11/scripts/workflow-representation-description")
TEMPLATE_WDD_PROMPT = REPO_ROOT / "template_wdd_gen-v7.prompt"
TEMPLATE_KNOWLEDGE_PROMPT = REPO_ROOT / "template_workflow_knowledge_gen-v7.prompt"
RESULTS_ROOT = REPO_ROOT / "evaluation_runs"
GENERATED_PROMPTS_DIR = REPO_ROOT / "generated_prompts"
WDD_OUTPUT_DIR = REPO_ROOT / "workflow_wdd"
KNOWLEDGE_OUTPUT_DIR = REPO_ROOT / "workflow_knowledge"

# Fill these or export env vars before running.
API_KEYS = {
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "<PUT_GEMINI_API_KEY_HERE>"),
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "<PUT_ANTHROPIC_API_KEY_HERE>"),
}


@dataclass
class AgentConfig:
    name: str
    # Must include "{prompt}" placeholder.
    command_template: str
    api_env_var: Optional[str] = None
    timeout_seconds: int = 3600


AGENTS: List[AgentConfig] = [
    AgentConfig(
        name="gemini",
        command_template="gemini -p {prompt}",
        api_env_var="GEMINI_API_KEY",
    ),
    AgentConfig(
        name="claude",
        command_template="claude -p {prompt}",
        api_env_var="ANTHROPIC_API_KEY",
    ),
]

# Add workflows later by appending dict entries.
WORKFLOWS = [
    {
        "name": "1000genome",
        "repo_path": str(REPO_ROOT / "workflows_repo/1000genome-workflow"),
    }
]


TOKEN_PATTERNS = {
    "input_tokens": [
        re.compile(r"input tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"prompt tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
    "output_tokens": [
        re.compile(r"output tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"completion tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
    "total_tokens": [
        re.compile(r"total tokens?\s*[:=]\s*([\d,]+)", re.IGNORECASE),
        re.compile(r"tokens used\s*[:=]\s*([\d,]+)", re.IGNORECASE),
    ],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def ensure_dirs() -> None:
    for path in [RESULTS_ROOT, GENERATED_PROMPTS_DIR, WDD_OUTPUT_DIR, KNOWLEDGE_OUTPUT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def check_cli_exists(agent: AgentConfig) -> Tuple[bool, str]:
    parts = shlex.split(agent.command_template)
    if not parts:
        return False, "empty command template"
    exe = parts[0]
    resolved = shutil.which(exe)
    if resolved is None:
        return False, f"CLI not found in PATH: {exe}"
    return True, resolved


def parse_tokens(output_text: str) -> Dict[str, Optional[int]]:
    parsed: Dict[str, Optional[int]] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }
    for key, patterns in TOKEN_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(output_text)
            if match:
                parsed[key] = int(match.group(1).replace(",", ""))
                break
    return parsed


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def template_metrics(path: Path) -> Dict[str, float]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    line_lengths = [len(x) for x in lines] or [0]
    bullets = sum(1 for line in lines if line.lstrip().startswith("- "))
    numbered = sum(1 for line in lines if re.match(r"^\s*\d+\.", line))
    headings = sum(1 for line in lines if line.strip().endswith(":") or line.isupper())
    return {
        "file": str(path),
        "line_count": len(lines),
        "word_count": word_count(text),
        "char_count": len(text),
        "bullet_count": bullets,
        "numbered_item_count": numbered,
        "heading_like_lines": headings,
        "avg_line_length": round(statistics.mean(line_lengths), 2),
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run_agent_task(
    agent: AgentConfig,
    prompt_text: str,
    run_dir: Path,
    task_name: str,
) -> Dict[str, object]:
    task_slug = re.sub(r"[^a-z0-9_.-]+", "_", task_name.lower())
    stdout_path = run_dir / f"{agent.name}__{task_slug}.stdout.log"
    stderr_path = run_dir / f"{agent.name}__{task_slug}.stderr.log"

    started_at = now_iso()
    t0 = time.perf_counter()

    result_record: Dict[str, object] = {
        "agent": agent.name,
        "task_name": task_name,
        "started_at": started_at,
        "finished_at": None,
        "duration_seconds": None,
        "exit_code": None,
        "status": "unknown",
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "error": None,
    }

    cmd = shlex.split(agent.command_template.format(prompt=prompt_text))
    env = os.environ.copy()
    if agent.api_env_var:
        env[agent.api_env_var] = API_KEYS.get(agent.api_env_var, "")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=agent.timeout_seconds,
            check=False,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        stdout_path.write_text(proc.stdout or "", encoding="utf-8")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8")

        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        result_record["tokens"] = parse_tokens(combined)
        result_record["exit_code"] = proc.returncode
        result_record["duration_seconds"] = elapsed
        result_record["finished_at"] = now_iso()
        result_record["status"] = "ok" if proc.returncode == 0 else "failed"
        if proc.returncode != 0:
            result_record["error"] = f"non-zero exit code {proc.returncode}"
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.perf_counter() - t0, 3)
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
        result_record["duration_seconds"] = elapsed
        result_record["finished_at"] = now_iso()
        result_record["status"] = "timeout"
        result_record["error"] = f"timeout after {agent.timeout_seconds}s"
    except Exception as exc:  # pylint: disable=broad-except
        elapsed = round(time.perf_counter() - t0, 3)
        stderr_path.write_text(str(exc), encoding="utf-8")
        result_record["duration_seconds"] = elapsed
        result_record["finished_at"] = now_iso()
        result_record["status"] = "error"
        result_record["error"] = str(exc)

    return result_record


def build_comparison_prompt(agent_name: str, output_path: Path) -> str:
    return textwrap.dedent(
        f"""
        Compare two template prompts and save the result to:
        {output_path}

        Templates:
        - {TEMPLATE_WDD_PROMPT}
        - {TEMPLATE_KNOWLEDGE_PROMPT}

        Required output format (Markdown):
        1) Short qualitative comparison (goals, strengths, risks)
        2) Quantitative table (line count, word count, bullet count, section count)
        3) Practical implications for workflow exploration quality
        4) Recommendation for when to use each template

        Keep it evidence-based and concise.
        Agent name: {agent_name}
        """
    ).strip()


def build_generate_wdd_prompt_prompt(
    agent_name: str,
    workflow_name: str,
    workflow_repo_path: str,
    out_prompt_path: Path,
) -> str:
    return textwrap.dedent(
        f"""
        Generate a workflow-specific WDD-generation prompt and write it to:
        {out_prompt_path}

        Use this template as base:
        {TEMPLATE_WDD_PROMPT}

        Context to embed:
        - agent_name: {agent_name}
        - workflow_name: {workflow_name}
        - workflow_repo_path: {workflow_repo_path}
        - output_wdd_yaml: {WDD_OUTPUT_DIR / f"{workflow_name}-wdd-{agent_name}.yaml"}

        Requirements:
        - Keep style/structure close to the template.
        - Make it executable for a terminal agent.
        - Ensure it asks to analyze only static repo evidence.
        """
    ).strip()


def build_generate_knowledge_prompt_prompt(
    agent_name: str,
    workflow_name: str,
    workflow_repo_path: str,
    out_prompt_path: Path,
) -> str:
    return textwrap.dedent(
        f"""
        Generate a workflow-specific knowledge-generation prompt and write it to:
        {out_prompt_path}

        Use this template as base:
        {TEMPLATE_KNOWLEDGE_PROMPT}

        Context to embed:
        - agent_name: {agent_name}
        - workflow_name: {workflow_name}
        - workflow_repo_path: {workflow_repo_path}
        - output_knowledge_markdown: {KNOWLEDGE_OUTPUT_DIR / f"{workflow_name}-knowledge-{agent_name}.md"}

        Requirements:
        - Keep style/structure close to the template.
        - Output should be Markdown knowledge report, not YAML.
        - Ensure it asks to analyze only static repo evidence.
        """
    ).strip()


def build_execute_generated_prompt_request(
    generated_prompt_path: Path,
    expected_output_path: Path,
    workflow_repo_path: str,
) -> str:
    return textwrap.dedent(
        f"""
        Read and execute instructions from:
        {generated_prompt_path}

        Required context:
        - Workflow repo path: {workflow_repo_path}
        - Expected output path: {expected_output_path}

        Constraints:
        - Use static analysis only.
        - Write the final output to the expected output path.
        - End your response with a one-line status including the output path.
        """
    ).strip()


def flatten_for_csv(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    flat: List[Dict[str, object]] = []
    for rec in records:
        row = dict(rec)
        tokens = row.pop("tokens", {})
        if isinstance(tokens, dict):
            row.update(
                {
                    "input_tokens": tokens.get("input_tokens"),
                    "output_tokens": tokens.get("output_tokens"),
                    "total_tokens": tokens.get("total_tokens"),
                }
            )
        flat.append(row)
    return flat


def main() -> None:
    ensure_dirs()

    run_stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RESULTS_ROOT / run_stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, object]] = []
    template_stats = {
        "wdd_template_metrics": template_metrics(TEMPLATE_WDD_PROMPT),
        "knowledge_template_metrics": template_metrics(TEMPLATE_KNOWLEDGE_PROMPT),
    }
    write_json(run_dir / "template_metrics.json", template_stats)

    for agent in AGENTS:
        ok, cli_info = check_cli_exists(agent)
        if not ok:
            records.append(
                {
                    "agent": agent.name,
                    "task_name": "precheck_cli",
                    "started_at": now_iso(),
                    "finished_at": now_iso(),
                    "duration_seconds": 0,
                    "exit_code": None,
                    "status": "skipped",
                    "stdout_log": None,
                    "stderr_log": None,
                    "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
                    "error": cli_info,
                }
            )
            continue

        # (1) Compare templates
        cmp_out = run_dir / f"{agent.name}-template-comparison.md"
        cmp_prompt = build_comparison_prompt(agent.name, cmp_out)
        records.append(run_agent_task(agent, cmp_prompt, run_dir, "compare_templates"))

        for wf in WORKFLOWS:
            workflow_name = wf["name"]
            workflow_repo_path = wf["repo_path"]

            wdd_prompt_path = GENERATED_PROMPTS_DIR / f"{agent.name}-{workflow_name}-wdd-gen.prompt"
            knowledge_prompt_path = GENERATED_PROMPTS_DIR / f"{agent.name}-{workflow_name}-knowledge-gen.prompt"
            wdd_output = WDD_OUTPUT_DIR / f"{workflow_name}-wdd-{agent.name}.yaml"
            knowledge_output = KNOWLEDGE_OUTPUT_DIR / f"{workflow_name}-knowledge-{agent.name}.md"

            # (2) Generate two prompts per agent/workflow
            prompt_text = build_generate_wdd_prompt_prompt(
                agent.name, workflow_name, workflow_repo_path, wdd_prompt_path
            )
            records.append(
                run_agent_task(agent, prompt_text, run_dir, f"generate_wdd_prompt__{workflow_name}")
            )

            prompt_text = build_generate_knowledge_prompt_prompt(
                agent.name, workflow_name, workflow_repo_path, knowledge_prompt_path
            )
            records.append(
                run_agent_task(
                    agent, prompt_text, run_dir, f"generate_knowledge_prompt__{workflow_name}"
                )
            )

            # (3) Execute generated WDD prompt -> YAML
            execute_prompt = build_execute_generated_prompt_request(
                wdd_prompt_path, wdd_output, workflow_repo_path
            )
            records.append(
                run_agent_task(agent, execute_prompt, run_dir, f"generate_wdd_yaml__{workflow_name}")
            )

            # (4) Execute generated knowledge prompt -> Markdown
            execute_prompt = build_execute_generated_prompt_request(
                knowledge_prompt_path, knowledge_output, workflow_repo_path
            )
            records.append(
                run_agent_task(
                    agent, execute_prompt, run_dir, f"generate_knowledge_md__{workflow_name}"
                )
            )

    write_json(run_dir / "metrics.json", {"run_started_at": now_iso(), "records": records})

    flat_rows = flatten_for_csv(records)
    csv_path = run_dir / "metrics.csv"
    if flat_rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0].keys()))
            writer.writeheader()
            writer.writerows(flat_rows)

    summary = {
        "run_dir": str(run_dir),
        "template_metrics_file": str(run_dir / "template_metrics.json"),
        "records_file": str(run_dir / "metrics.json"),
        "records_csv": str(csv_path),
        "generated_prompts_dir": str(GENERATED_PROMPTS_DIR),
        "wdd_output_dir": str(WDD_OUTPUT_DIR),
        "knowledge_output_dir": str(KNOWLEDGE_OUTPUT_DIR),
    }
    write_json(run_dir / "run_summary.json", summary)

    print(json.dumps(summary, indent=2))


if False and __name__ == "__main__":
    main()
