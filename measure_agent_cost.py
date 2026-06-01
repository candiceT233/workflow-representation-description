#!/usr/bin/env python3
"""
measure_agent_cost.py — authoritative, API-free token/cost measurement for a
terminal Claude Code agent run, segmented by phase.

WHY THIS WORKS WITHOUT API ACCESS
  Claude Code writes a local session transcript at
    ~/.claude/projects/<project-slug>/<session-uuid>.jsonl
  Every assistant turn in that file carries a `message.usage` object with the
  REAL token counts the model reported:
    input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens
  plus an ISO `timestamp`. We parse that file — nothing is sent anywhere.

PHASE SEGMENTATION
  The agent prints sentinel lines at phase boundaries (see the io_opt_deploy_run-*.prompt
  METRICS PROTOCOL). Sentinels are matched anywhere in assistant text:
    @@WIDGET_METRIC planning_start@@   @@WIDGET_METRIC planning_end@@
    @@WIDGET_METRIC running_start@@    @@WIDGET_METRIC running_end@@
  Turns are bucketed into: setup | planning | running | other, by the most recent sentinel.
  If no sentinels are present, everything lands in "session_total" only.

USAGE
  python3 measure_agent_cost.py <transcript.jsonl> [--out metrics_tokens.json] [--include-sidechain]
  python3 measure_agent_cost.py --latest [--project <slug>]      # auto-pick newest transcript
"""
import argparse, glob, json, os, sys
from datetime import datetime

SENTINELS = {
    "planning_start": "planning",
    "planning_end": "_end_planning",   # sentinel closes the planning bucket
    "running_start": "running",
    "running_end": "_end_running",
}
PHASES = ["setup", "planning", "running", "other"]


def _iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def new_bucket():
    return dict(turns=0, tool_calls=0,
                input_tokens=0, output_tokens=0,
                cache_creation_input_tokens=0, cache_read_input_tokens=0,
                first_ts=None, last_ts=None)


def add_ts(b, dt):
    if dt is None:
        return
    if b["first_ts"] is None or dt < b["first_ts"]:
        b["first_ts"] = dt
    if b["last_ts"] is None or dt > b["last_ts"]:
        b["last_ts"] = dt


def text_of(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return c
    out = []
    if isinstance(c, list):
        for blk in c:
            if isinstance(blk, dict) and blk.get("type") == "text":
                out.append(blk.get("text", ""))
    return "\n".join(out)


def detect_phase_change(text, current):
    """Return new phase given sentinels found in `text` (last match wins)."""
    phase = current
    for line in text.splitlines():
        if "@@WIDGET_METRIC" not in line:
            continue
        if "planning_start" in line:
            phase = "planning"
        elif "planning_end" in line:
            phase = "setup" if current == "setup" else "other"  # gap between phases
            phase = "between"
        elif "running_start" in line:
            phase = "running"
        elif "running_end" in line:
            phase = "between"
    return phase


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript", nargs="?", help="path to <session>.jsonl")
    ap.add_argument("--latest", action="store_true", help="auto-pick newest transcript")
    ap.add_argument("--project", default="-u-mtang9-widget-eval",
                    help="project slug under ~/.claude/projects/")
    ap.add_argument("--include-sidechain", action="store_true",
                    help="also count subagent (Task) turns (isSidechain=true)")
    ap.add_argument("--out", default=None, help="write metrics JSON here")
    a = ap.parse_args()

    path = a.transcript
    if a.latest or not path:
        base = os.path.expanduser(f"~/.claude/projects/{a.project}")
        cands = sorted(glob.glob(os.path.join(base, "*.jsonl")), key=os.path.getmtime)
        if not cands:
            sys.exit(f"no transcripts under {base}")
        path = cands[-1]
    if not os.path.exists(path):
        sys.exit(f"not found: {path}")

    buckets = {p: new_bucket() for p in PHASES + ["between"]}
    total = new_bucket()
    phase = "setup"
    session_id = None

    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            session_id = o.get("sessionId", session_id)
            if o.get("isSidechain") and not a.include_sidechain:
                continue
            msg = o.get("message") or {}
            dt = _iso(o.get("timestamp"))

            # phase transitions come from assistant text sentinels
            if o.get("type") == "assistant":
                phase = detect_phase_change(text_of(msg), phase)

            b = buckets.get(phase, buckets["other"])

            # count tool calls (tool_use blocks) on any turn
            content = msg.get("content")
            if isinstance(content, list):
                tc = sum(1 for blk in content
                         if isinstance(blk, dict) and blk.get("type") == "tool_use")
                if tc:
                    b["tool_calls"] += tc
                    total["tool_calls"] += tc

            u = msg.get("usage")
            if o.get("type") == "assistant" and u:
                for k in ("input_tokens", "output_tokens",
                          "cache_creation_input_tokens", "cache_read_input_tokens"):
                    v = u.get(k) or 0
                    b[k] += v
                    total[k] += v
                b["turns"] += 1
                total["turns"] += 1
                add_ts(b, dt)
                add_ts(total, dt)

    def finalize(b):
        billed_in = (b["input_tokens"] + b["cache_creation_input_tokens"]
                     + b["cache_read_input_tokens"])
        wall = None
        if b["first_ts"] and b["last_ts"]:
            wall = round((b["last_ts"] - b["first_ts"]).total_seconds(), 1)
        return dict(turns=b["turns"], tool_calls=b["tool_calls"],
                    input_tokens=b["input_tokens"], output_tokens=b["output_tokens"],
                    cache_creation_input_tokens=b["cache_creation_input_tokens"],
                    cache_read_input_tokens=b["cache_read_input_tokens"],
                    billed_input_tokens=billed_in,
                    total_tokens=billed_in + b["output_tokens"],
                    wall_seconds=wall)

    result = dict(
        transcript=path, session_id=session_id,
        tokens_are_estimate=False, source="claude_code_local_transcript",
        phases={p: finalize(buckets[p]) for p in ["setup", "planning", "running", "between", "other"]},
        session_total=finalize(total),
    )

    out = json.dumps(result, indent=2)
    print(out)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(out)
        print(f"\nwrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
