#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parent
PROMPTS = BASE / "prompts"
MANIFESTS = BASE / "manifests"
BASELINE_SPECS = BASE / "baseline_specs"
BUNDLE_SPECS = BASE / "bundle_builder_specs"
EXECUTOR_SPECS = BASE / "neutral_executor_specs"

DPM_STATIC_TABLE_INPUT = (
    "Statically computed Widget DPM candidate-plan score table copied into the "
    "clean input bundle. The table must score every node-count/storage-tier "
    "candidate in this prompt, identify the deterministic lowest-DPM plan, and "
    "remain unchanged across all trials for this workflow/scale/setup."
)

SETUPS = {
    "code_only": {
        "purpose": "Test whether workflow code and run-script exploration alone let the agent identify an I/O-improved deployment relative to the BeeGFS baseline.",
        "allowed": [
            "Files in this setup's clean input bundle.",
            "Workflow repository files copied into the clean input bundle.",
            "Run scripts copied into the clean input bundle.",
            "Cluster site configuration copied into the clean input bundle.",
            "Candidate node counts and storage tiers listed in this prompt.",
        ],
        "disallowed": [
            "WDD-suite YAML files.",
            "Widget DPM outputs.",
            "Prior evaluation reports.",
            "Chat-derived conclusions from other setups.",
        ],
        "tools": ["shell for read-only inspection of the clean input bundle"],
        "widget_live": False,
    },
    "code_dpm": {
        "purpose": "Test whether workflow code plus statically computed Widget DPM score files let the agent identify an I/O-improved deployment relative to the BeeGFS baseline.",
        "allowed": [
            "Files in this setup's clean input bundle.",
            "Workflow repository files copied into the clean input bundle.",
            "Run scripts copied into the clean input bundle.",
            "Cluster site configuration copied into the clean input bundle.",
            "Candidate node counts and storage tiers listed in this prompt.",
            DPM_STATIC_TABLE_INPUT,
        ],
        "disallowed": [
            "WDD-suite YAML files.",
            "Prior evaluation reports.",
            "Chat-derived conclusions from other setups.",
        ],
        "tools": ["shell for read-only inspection of the clean input bundle", "static DPM score files from clean input bundle"],
        "widget_live": False,
    },
    "dpm_only": {
        "purpose": "Test whether statically computed Widget DPM score files alone are enough for the agent to identify an I/O-improved deployment relative to the BeeGFS baseline.",
        "allowed": [
            "Files in this setup's clean input bundle.",
            "Candidate node counts and storage tiers listed in this prompt.",
            DPM_STATIC_TABLE_INPUT,
            "Minimal labels copied into the clean input bundle to map DPM scores to workflow edges, node counts, and storage choices.",
        ],
        "disallowed": [
            "Workflow repository and scripts.",
            "Run harness internals.",
            "Workflow executor implementation details.",
            "WDD-suite YAML files.",
            "Prior evaluation reports.",
            "Chat-derived conclusions from other setups.",
        ],
        "tools": ["shell for read-only inspection of the clean input bundle", "static DPM score files from clean input bundle"],
        "widget_live": False,
    },
    "wdd_pair_only": {
        "purpose": "Test whether workflow code plus the WDD.yml and IODD.yml pair let the agent identify an I/O-improved deployment relative to the BeeGFS baseline.",
        "allowed": [
            "Files in this setup's clean input bundle.",
            "Workflow repository files copied into the clean input bundle.",
            "Run scripts copied into the clean input bundle.",
            "Cluster site configuration copied into the clean input bundle.",
            "Candidate node counts and storage tiers listed in this prompt.",
            "WDD.yml copied into the clean input bundle.",
            "IODD.yml copied into the clean input bundle.",
        ],
        "disallowed": [
            "HRD.yml, GD.yml, DDD.yml, and EDD_*.yml.",
            "Widget DPM outputs.",
            "Prior evaluation reports.",
            "Chat-derived conclusions from other setups.",
        ],
        "tools": ["shell for read-only inspection of the clean input bundle"],
        "widget_live": False,
    },
    "wdd_pair_dpm": {
        "purpose": "Test whether workflow code, the WDD.yml and IODD.yml pair, and statically computed Widget DPM score files let the agent identify an I/O-improved deployment relative to the BeeGFS baseline.",
        "allowed": [
            "Files in this setup's clean input bundle.",
            "Workflow repository files copied into the clean input bundle.",
            "Run scripts copied into the clean input bundle.",
            "Cluster site configuration copied into the clean input bundle.",
            "Candidate node counts and storage tiers listed in this prompt.",
            "WDD.yml copied into the clean input bundle.",
            "IODD.yml copied into the clean input bundle.",
            DPM_STATIC_TABLE_INPUT,
        ],
        "disallowed": [
            "HRD.yml, GD.yml, DDD.yml, and EDD_*.yml.",
            "Prior evaluation reports.",
            "Chat-derived conclusions from other setups.",
        ],
        "tools": ["shell for read-only inspection of the clean input bundle", "static DPM score files from clean input bundle"],
        "widget_live": False,
    },
    "wdd_full_only": {
        "purpose": "Test whether workflow code plus the full WDD suite let the agent identify an I/O-improved deployment relative to the BeeGFS baseline.",
        "allowed": [
            "Files in this setup's clean input bundle.",
            "Workflow repository files copied into the clean input bundle.",
            "Run scripts copied into the clean input bundle.",
            "Cluster site configuration copied into the clean input bundle.",
            "Candidate node counts and storage tiers listed in this prompt.",
            "Full WDD suite copied into the clean input bundle: WDD.yml, IODD.yml, HRD.yml, GD.yml, DDD.yml, EDD_*.yml.",
        ],
        "disallowed": [
            "Widget DPM outputs.",
            "Prior evaluation reports.",
            "Chat-derived conclusions from other setups.",
        ],
        "tools": ["shell for read-only inspection of the clean input bundle"],
        "widget_live": False,
    },
    "wdd_full_dpm": {
        "purpose": "Test whether workflow code, the full WDD suite, and statically computed Widget DPM score files let the agent identify an I/O-improved deployment relative to the BeeGFS baseline.",
        "allowed": [
            "Files in this setup's clean input bundle.",
            "Workflow repository files copied into the clean input bundle.",
            "Run scripts copied into the clean input bundle.",
            "Cluster site configuration copied into the clean input bundle.",
            "Candidate node counts and storage tiers listed in this prompt.",
            "Full WDD suite copied into the clean input bundle: WDD.yml, IODD.yml, HRD.yml, GD.yml, DDD.yml, EDD_*.yml.",
            DPM_STATIC_TABLE_INPUT,
        ],
        "disallowed": [
            "Prior evaluation reports.",
            "Chat-derived conclusions from other setups.",
        ],
        "tools": ["shell for read-only inspection of the clean input bundle", "static DPM score files from clean input bundle"],
        "widget_live": False,
    },
}

WORKFLOWS = {
    "montage_30gb": {
        "display": "Montage 30GB",
        "workflow": "Montage mProjectPP reprojection",
        "scale": "15,000 FITS input tiles, approximately 30GB",
        "nodes": [30, 60, 120],
        "storage": ["beegfs", "scratch", "tmpfs"],
        "baseline": "BeeGFS-only at 30, 60, and 120 nodes.",
        "neutral_notes": [
            "The workflow phase under evaluation is Montage mProjectPP reprojection.",
            "The input data are FITS tiles.",
            "Output correctness is determined by comparison with BeeGFS baseline outputs.",
        ],
        "sources": {
            "repo": "hpc_workflows/repos/Montage",
            "run_harness": "workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/",
            "wdd_docs": "workflow_representation_experiments/Montage/datalife_code/docs/",
            "dpm_outputs": "workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/",
        },
    },
    "1000genome_10chr": {
        "display": "1000Genome 10 chromosomes",
        "workflow": "1000Genome workflow",
        "scale": "10 chromosomes",
        "nodes": [2, 5, 10],
        "storage": ["beegfs", "scratch", "tmpfs"],
        "baseline": "BeeGFS-only at 2, 5, and 10 nodes, with all default outputs copied.",
        "neutral_notes": [
            "The workflow stages are named individuals, individuals_merge, sifting, mutation_overlap, and frequency.",
            "The workload contains 10 chromosomes.",
            "Output correctness is determined by comparison with BeeGFS baseline outputs.",
        ],
        "sources": {
            "repo": "hpc_workflows/repos/1000genome-workflow",
            "run_harness": "workflow_representation_experiments/1000Genome/agentic_runs_3trial_10chr/",
            "wdd_docs": "workflow_representation_experiments/1000Genome/datalife_code/docs/",
            "dpm_outputs": "workflow_representation_experiments/1000Genome/agentic_runs_3trial_10chr/",
        },
    },
}


def bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def prompt_text(workflow_key: str, setup: str) -> str:
    wf = WORKFLOWS[workflow_key]
    st = SETUPS[setup]
    bundle = f"agent_contexts/{workflow_key}/{setup}/allowed/"
    dpm_required = "static DPM score files from clean input bundle" in st["tools"]
    dpm_note = (
        "Use the statically computed DPM candidate-plan score table from the clean input bundle as decision evidence. The DPM table must contain one score for every candidate node-count/storage-tier plan in this prompt, must identify the deterministic lowest-DPM plan, must record that it was derived from the existing DataLife profile for this workflow/scale, and is reused unchanged across all trials for this workflow/scale/setup. Report whether your selected deployment follows or overrides that lowest-DPM plan."
        if dpm_required
        else "DPM score files are not allowed for this setup."
    )
    dpm_procedure = (
        "8. Cite the DPM score table, the deterministic DPM-best plan, and whether the selected deployment follows or overrides DPM.\n"
        "9. Apply the tie-breaking rules below.\n"
        "10. Save the required decision report for the neutral executor."
        if dpm_required
        else "8. Apply the tie-breaking rules below.\n9. Save the required decision report for the neutral executor."
    )
    dpm_candidate_fields = (
        "    dpm_score: <float>\n"
        "    is_dpm_best: <true|false>\n"
        if dpm_required
        else ""
    )
    dpm_evidence_block = (
        "dpm_evidence:\n"
        "  dpm_table_path: <path>\n"
        "  dpm_table_sha256: <sha256 if provided by orchestrator>\n"
        "  dpm_provenance: DataLife-derived static Widget DPM artifact\n"
        "  datalife_profile_id_or_path: <path/id from DPM artifact metadata, not raw traces unless explicitly allowed>\n"
        "  datalife_profile_sha256: <sha256 if provided by orchestrator>\n"
        "  all_candidate_plans_scored: <true|false>\n"
        "  dpm_selected_node_count: <int>\n"
        "  dpm_selected_storage_tier: <beegfs|scratch|tmpfs>\n"
        "  agent_followed_dpm_argmin: <true|false>\n"
        if dpm_required
        else ""
    )
    return f"""# Agent Prompt v3: {wf['display']} / {setup}

## Role

You are an HPC workflow I/O deployment engineer. Your task is to choose one
workflow deployment strategy under the exact input and tool constraints listed
below.

## Objective

Choose an I/O-improved deployment expected to reduce workflow runtime relative
to the BeeGFS baseline while preserving output correctness. The deployment
choice includes both node count and storage tier. A neutral executor, not this
decision agent, will run the workflow and measure runtime.

Runtime definitions for the neutral executor:

- deployment_runtime_s: stage-in plus workflow execution.
- validation_s: output comparison and correctness checks.
- excluded_from_runtime: validation, report generation, plotting, and cleanup.

## Evaluation Question

{st['purpose']}

This is a controlled experiment. Only the information input regime should differ
between setups. Keep workflow scale, candidate node counts, candidate storage
tiers, runtime definitions, validation method, and cleanup policy fixed.

This is decision-only mode. Choose exactly one node count and one storage tier.
Do not submit jobs, run workflow scripts, modify inputs, modify the prompt, or
materialize the selected deployment. The neutral executor will consume your
decision report.

## Workflow Context

- Workflow: {wf['workflow']}
- Scale: {wf['scale']}
- Candidate node counts: {', '.join(map(str, wf['nodes']))}
- Candidate storage tiers: {', '.join(wf['storage'])}
- Baseline policy: {wf['baseline']}

Neutral workflow facts:
{bullet(wf['neutral_notes'])}

Do not assume any workflow dependency, data-locality, or staging policy unless
it is derivable from this setup's allowed inputs.

## Cluster Context

- Slurm account: `oddite`
- Slurm partition: `slurm`
- Storage candidate `beegfs`: shared parallel filesystem.
- Storage candidate `scratch`: job-owned scratch filesystem or directory,
  prepared and cleaned by the neutral executor.
- Storage candidate `tmpfs`: job-owned memory-backed filesystem or directory,
  prepared and cleaned by the neutral executor.
- Use only job-owned scratch/tmpfs directories.
- Do not remove anything outside the project/evaluation roots except job-owned
  scratch/tmpfs paths created by this run.

## Allowed Inputs

You may inspect only:
{bullet(st['allowed'])}

Clean input bundle:

```text
{bundle}
```

The matching agent-facing manifest lists only the clean input bundle, not the
original source locations used to build it. Inspect the clean input bundle only.

## Disallowed Inputs

You must not inspect:
{bullet(st['disallowed'])}

If a needed conclusion is not derivable from the allowed inputs, report that as
a limitation instead of using prior knowledge, chat history, previous runs, or
other setups.

## Allowed Tools

You may use:
{bullet(st['tools'])}

You may write only the required decision report and local notes needed to
produce it. Do not modify clean input bundle files.

Tool policy:

- web_access: false
- subagents: false
- slurm_job_submission: false
- workflow_execution: false
- widget_mcp_live_calls: {str(st['widget_live']).lower()}

{dpm_note} Do not make live Widget MCP calls in this decision-agent prompt.

## Required Procedure

1. Inspect only allowed inputs.
2. Record the files inspected.
3. Select exactly one node count and one storage tier.
4. Specify the intended stage-in, workflow-storage, and stage-out policy at a
   high level. Do not write executable scripts.
5. Explain the expected I/O improvement relative to the BeeGFS baseline using
   only allowed evidence.
6. Estimate staging overhead, storage-capacity risk, and scheduler feasibility
   using only allowed evidence.
7. Compare the selected deployment against every candidate node-count/storage
   combination.
{dpm_procedure}

## Decision Criteria

Prefer the deployment with the best expected workflow runtime subject to:

- output correctness,
- storage capacity,
- scheduler feasibility,
- cleanup requirements,
- stage-in and stage-out overhead,
- shared filesystem load,
- respecting only the allowed evidence for this setup.

Tie-breaking rules:

- If expected runtime difference is below 10%, prefer the simpler deployment
  with less data movement.
- If storage choices appear equivalent, prefer the storage tier requiring fewer
  staging steps.
- If node choices appear equivalent, prefer the lower node count.
- If evidence is insufficient to distinguish options, state that clearly and
  apply the rules above.

## Output Contract

Save one agent decision report containing:

```yaml
prompt_record_id: <workflow>_<scale>_{setup}_<timestamp>
prompt_version: 3
setup: {setup}
workflow: {wf['display']}
agent_provider: <provider if known>
model: <name/version if known>
temperature: <value if known>
session_id: <id if known>
allowed_input_manifest: <path>
prompt_sha256: <sha256 if provided by orchestrator>
manifest_sha256: <sha256 if provided by orchestrator>
input_bundle_sha256: <sha256 if provided by orchestrator>
tool_policy:
  web_access: false
  subagents: false
  slurm_job_submission: false
  workflow_execution: false
  widget_mcp_live_calls: {str(st['widget_live']).lower()}
selected_node_count: <int>
selected_storage_tier: <beegfs|scratch|tmpfs>
stage_in_policy: <text>
workflow_storage_policy: <text>
stage_out_policy: <text>
expected_improvement_reason: <text>
confidence: <low|medium|high>
assumptions:
  - <text>
evidence_used:
  - <path or tool output from allowed bundle>
files_inspected:
  - <path inside clean input bundle>
candidate_comparison:
  - node_count: <int>
    storage_tier: <beegfs|scratch|tmpfs>
{dpm_candidate_fields.rstrip()}
    expected_runtime_rank: <int or unknown>
    reason_selected_or_rejected: <text>
{dpm_evidence_block.rstrip()}
disallowed_inputs_avoided:
  - <confirmation>
executor_requirements:
  validation_required: true
  runtime_excludes_validation: true
  cleanup_required: true
limitations:
  - <text>
```

## Stop Conditions

Stop and report if:

- required allowed inputs are missing,
- the run would require inspecting disallowed inputs,
- the decision would require writing outside the allowed workspace,
- credentials or private data are requested,
- storage capacity appears insufficient for the selected deployment,
- scheduler/account configuration cannot be assessed from allowed evidence.
"""


def manifest_text(workflow_key: str, setup: str) -> str:
    wf = WORKFLOWS[workflow_key]
    st = SETUPS[setup]
    allowed = "\n".join(f"  - {item!r}" for item in st["allowed"])
    disallowed = "\n".join(f"  - {item!r}" for item in st["disallowed"])
    tools = "\n".join(f"  - {item!r}" for item in st["tools"])
    nodes = ", ".join(map(str, wf["nodes"]))
    storage = ", ".join(f"'{s}'" for s in wf["storage"])
    dpm_required = "static DPM score files from clean input bundle" in st["tools"]
    dpm_requirements = ""
    dpm_report_requirement = ""
    if dpm_required:
        dpm_requirements = """  dpm_score_table_requirements:
    required: true
    must_score_every_candidate_plan: true
    candidate_plan_space: 'candidate_node_counts x candidate_storage_tiers'
    must_include_dpm_argmin: true
    must_preserve_raw_widget_output: true
    must_not_include_prior_runtime_results: true
"""
        dpm_report_requirement = "    - dpm_evidence\n"
    else:
        dpm_requirements = """  dpm_score_table_requirements:
    required: false
"""
    return f"""prompt_manifest:
  version: 3
  workflow_key: {workflow_key}
  workflow_display: {wf['display']!r}
  setup: {setup!r}
  mode: decision_only_single_deployment
  controlled_variable: information_input_regime
  clean_input_bundle: {'agent_contexts/' + workflow_key + '/' + setup + '/allowed/'!r}
  agent_may_inspect_original_source_paths: false
  candidate_node_counts: [{nodes}]
  candidate_storage_tiers: [{storage}]
  storage_descriptions:
    beegfs: 'shared parallel filesystem'
    scratch: 'job-owned scratch filesystem or directory prepared by the neutral executor'
    tmpfs: 'job-owned memory-backed filesystem or directory prepared by the neutral executor'
  baseline_policy: {wf['baseline']!r}
  allowed_inputs:
{allowed}
  disallowed_inputs:
{disallowed}
  allowed_tools:
{tools}
  tool_policy:
    web_access: false
    subagents: false
    slurm_job_submission: false
    workflow_execution: false
    widget_mcp_live_calls: {str(st['widget_live']).lower()}
  writable_outputs:
    - 'agent decision report'
    - 'local notes needed to produce the decision report'
  clean_input_bundle_policy:
    read_only: true
    do_not_modify_inputs: true
{dpm_requirements.rstrip()}
  report_requirements:
    - prompt_record_id
    - prompt_version
    - agent_provider
    - model
    - allowed_input_manifest
    - prompt_sha256
    - manifest_sha256
    - input_bundle_sha256
    - selected_node_count
    - selected_storage_tier
    - stage_in_policy
    - workflow_storage_policy
    - stage_out_policy
    - confidence
    - assumptions
    - candidate_comparison
{dpm_report_requirement.rstrip()}
    - evidence_used
    - files_inspected
    - limitations
"""


def bundle_spec_text(workflow_key: str, setup: str) -> str:
    wf = WORKFLOWS[workflow_key]
    st = SETUPS[setup]
    dpm_required = "static DPM score files from clean input bundle" in st["tools"]
    dpm_builder_section = ""
    if dpm_required:
        dpm_builder_section = f"""

## DPM Score Table Requirements

For this DPM-enabled setup, the clean bundle must include a statically computed
DPM candidate-plan score table generated before the first decision agent starts.
Reuse the same static DPM table unchanged across all trials for the same
workflow/scale/setup.

The DPM artifact must be derived from the existing DataLife profile for the
same workflow/scale. The decision-agent bundle should include provenance
metadata identifying the DataLife profile path/id and checksum when available,
but should not include raw DataLife traces unless the setup explicitly allows
them.

The table must:

1. Score every candidate deployment plan:
   - node counts: `{', '.join(map(str, wf['nodes']))}`
   - storage tiers: `{', '.join(wf['storage'])}`
2. Include one row per node-count/storage-tier plan, or an equivalent explicit
   representation that can be losslessly converted into that table.
3. Include the deterministic lowest-DPM plan.
4. Preserve the raw Widget DPM output and a normalized agent-facing table.
5. Include DPM provenance metadata: source profiler type `DataLife`,
   DataLife profile path/id, DataLife profile checksum if available, Widget
   config/workflow identifier, and candidate node/storage set.
6. Include checksums for both raw and normalized DPM files.
7. Exclude measured runtime results, previous agent choices, report summaries,
   and any chat-derived conclusions.
"""
    return f"""# Bundle Builder Spec v3: {wf['display']} / {setup}

This file is for the experiment orchestrator, not for the decision agent.

## Objective

Create the clean input bundle consumed by the matching v3 prompt and
agent-facing manifest.

## Destination

```text
agent_contexts/{workflow_key}/{setup}/allowed/
```

## Source Paths

- workflow_repository: `{wf['sources']['repo']}`
- run_harness: `{wf['sources']['run_harness']}`
- wdd_documents_if_allowed: `{wf['sources']['wdd_docs']}`
- dpm_outputs_if_allowed: `{wf['sources']['dpm_outputs']}`

## Include Policy

Allowed inputs for this setup:
{bullet(st['allowed'])}

Disallowed inputs for this setup:
{bullet(st['disallowed'])}

## Required Builder Actions

1. Create a fresh destination directory for each trial.
2. Copy only files allowed by this setup.
3. Exclude prior reports, chat transcripts, generated analysis summaries, and
   outputs from other setups.
4. Exclude original source path metadata from the agent-facing manifest.
5. Write a file inventory with path, size, and sha256 for each included file.
6. Write a bundle-level sha256 or Merkle-style digest over the inventory.
7. Make allowed input files read-only for the decision agent where practical.
8. Save the builder log outside the agent-facing bundle.
{dpm_builder_section}
"""


def executor_spec_text(workflow_key: str, setup: str) -> str:
    wf = WORKFLOWS[workflow_key]
    st = SETUPS[setup]
    dpm_required = "static DPM score files from clean input bundle" in st["tools"]
    dpm_executor_step = (
        "2. Record the DPM score table path, DPM argmin plan, and whether the\n"
        "   agent followed or overrode the DPM argmin.\n"
        "3. Do not reinterpret the decision using information unavailable to the agent.\n"
        "4. Submit workflow jobs with Slurm account `oddite` and partition `slurm`.\n"
        "5. Measure deployment runtime as stage-in plus workflow execution.\n"
        "6. Measure validation separately.\n"
        "7. Exclude validation, plotting, report generation, and cleanup from deployment\n"
        "   runtime.\n"
        "8. Validate outputs against the BeeGFS baseline outputs.\n"
        "9. Clean only job-owned scratch/tmpfs paths created by this run.\n"
        "10. Record fixed environment metadata, commands, timing logs, validation result,\n"
        "   cleanup result, and any executor-side failures."
        if dpm_required
        else "2. Do not reinterpret the decision using information unavailable to the agent.\n"
        "3. Submit workflow jobs with Slurm account `oddite` and partition `slurm`.\n"
        "4. Measure deployment runtime as stage-in plus workflow execution.\n"
        "5. Measure validation separately.\n"
        "6. Exclude validation, plotting, report generation, and cleanup from deployment\n"
        "   runtime.\n"
        "7. Validate outputs against the BeeGFS baseline outputs.\n"
        "8. Clean only job-owned scratch/tmpfs paths created by this run.\n"
        "9. Record fixed environment metadata, commands, timing logs, validation result,\n"
        "   cleanup result, and any executor-side failures."
    )
    dpm_metrics = (
        "dpm_argmin_node_count: <int>\n"
        "dpm_argmin_storage_tier: <beegfs|scratch|tmpfs>\n"
        "agent_followed_dpm_argmin: <true|false>\n"
        if dpm_required
        else ""
    )
    return f"""# Neutral Executor Spec v3: {wf['display']} / {setup}

This file is for the neutral evaluator that runs a decision produced by a fresh
agent. It is not an input to the decision agent.

## Inputs

- Agent decision report for `{workflow_key}` / `{setup}`.
- Baseline outputs for correctness comparison.
- Workflow run harness controlled by the evaluator.

## Execution Rules

1. Read exactly one selected node count and storage tier from the decision
   report.
{dpm_executor_step}

## Output Metrics

```yaml
selected_node_count: <int>
selected_storage_tier: <beegfs|scratch|tmpfs>
{dpm_metrics.rstrip()}
deployment_runtime_s: <float>
stage_in_s: <float>
workflow_execution_s: <float>
validation_s: <float>
cleanup_s: <float>
runtime_excludes_validation: true
correctness_passed: <true|false>
executor_notes:
  - <text>
```
"""


def baseline_spec_text(workflow_key: str) -> str:
    wf = WORKFLOWS[workflow_key]
    return f"""# Baseline Execution Spec v3: {wf['display']}

This is not an agentic prompt. Baseline is a deterministic reference procedure.

## Objective

Run BeeGFS-only baseline at every candidate node count and validate outputs.
Baseline produces the fixed reference used by all agentic setups.

## Workflow Context

- Workflow: {wf['workflow']}
- Scale: {wf['scale']}
- Candidate node counts: {', '.join(map(str, wf['nodes']))}
- Baseline storage: beegfs only
- Baseline policy: {wf['baseline']}

## Procedure

1. Use BeeGFS/shared filesystem as active workflow storage.
2. Do not stage inputs to scratch or tmpfs.
3. Run at every candidate node count.
4. Validate outputs.
5. Report fixed-node runtimes and per-trial best BeeGFS runtime.
6. Measure validation separately from workflow runtime.
7. Save timing logs, validation output, cleanup status, and environment
   metadata.
"""


def main() -> None:
    PROMPTS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    BASELINE_SPECS.mkdir(parents=True, exist_ok=True)
    BUNDLE_SPECS.mkdir(parents=True, exist_ok=True)
    EXECUTOR_SPECS.mkdir(parents=True, exist_ok=True)
    for workflow_key in WORKFLOWS:
        (BASELINE_SPECS / f"{workflow_key}_baseline_execution_spec.md").write_text(baseline_spec_text(workflow_key))
        for setup in SETUPS:
            (PROMPTS / f"{workflow_key}_{setup}_prompt.md").write_text(prompt_text(workflow_key, setup))
            (MANIFESTS / f"{workflow_key}_{setup}_allowed_inputs.yml").write_text(manifest_text(workflow_key, setup))
            (BUNDLE_SPECS / f"{workflow_key}_{setup}_bundle_builder_spec.md").write_text(bundle_spec_text(workflow_key, setup))
            (EXECUTOR_SPECS / f"{workflow_key}_{setup}_neutral_executor_spec.md").write_text(executor_spec_text(workflow_key, setup))


if __name__ == "__main__":
    main()
