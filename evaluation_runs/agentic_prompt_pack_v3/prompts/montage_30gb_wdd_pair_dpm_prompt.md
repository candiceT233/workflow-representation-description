# Agent Prompt v3: Montage 30GB / wdd_pair_dpm

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

Test whether workflow code, the WDD.yml and IODD.yml pair, and statically computed Widget DPM score files let the agent identify an I/O-improved deployment relative to the BeeGFS baseline.

This is a controlled experiment. Only the information input regime should differ
between setups. Keep workflow scale, candidate node counts, candidate storage
tiers, runtime definitions, validation method, and cleanup policy fixed.

This is decision-only mode. Choose exactly one node count and one storage tier.
Do not submit jobs, run workflow scripts, modify inputs, modify the prompt, or
materialize the selected deployment. The neutral executor will consume your
decision report.

## Workflow Context

- Workflow: Montage mProjectPP reprojection
- Scale: 15,000 FITS input tiles, approximately 30GB
- Candidate node counts: 30, 60, 120
- Candidate storage tiers: beegfs, scratch, tmpfs
- Baseline policy: BeeGFS-only at 30, 60, and 120 nodes.

Neutral workflow facts:
- The workflow phase under evaluation is Montage mProjectPP reprojection.
- The input data are FITS tiles.
- Output correctness is determined by comparison with BeeGFS baseline outputs.

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
- Files in this setup's clean input bundle.
- Workflow repository files copied into the clean input bundle.
- Run scripts copied into the clean input bundle.
- Cluster site configuration copied into the clean input bundle.
- Candidate node counts and storage tiers listed in this prompt.
- WDD.yml copied into the clean input bundle.
- IODD.yml copied into the clean input bundle.
- Statically computed Widget DPM candidate-plan score table copied into the clean input bundle. The table must score every node-count/storage-tier candidate in this prompt, include `estT_prod`, `estT_cons`, `workflow_io_time`, `data_movement_time`, and final `dpm` for each scored candidate, identify the deterministic lowest-DPM plan, and remain unchanged across all trials for this workflow/scale/setup. The normalized score table must be generated from Widget `predict_dpm_space` or `analyze_workflow_dpm`, not from `prepare_and_dump_dpm` movement-node exports alone.

Clean input bundle:

```text
agent_contexts/montage_30gb/wdd_pair_dpm/allowed/
```

The matching agent-facing manifest lists only the clean input bundle, not the
original source locations used to build it. Inspect the clean input bundle only.

## Disallowed Inputs

You must not inspect:
- HRD.yml, GD.yml, DDD.yml, and EDD_*.yml.
- Prior evaluation reports.
- Chat-derived conclusions from other setups.

If a needed conclusion is not derivable from the allowed inputs, report that as
a limitation instead of using prior knowledge, chat history, previous runs, or
other setups.

## Allowed Tools

You may use:
- shell for read-only inspection of the clean input bundle
- static DPM score files from clean input bundle

You may write only the required decision report and local notes needed to
produce it. Do not modify clean input bundle files.

Tool policy:

- web_access: false
- subagents: false
- slurm_job_submission: false
- workflow_execution: false
- widget_mcp_live_calls: false

Use the statically computed DPM candidate-plan score table from the clean input bundle as decision evidence. The DPM table must contain one score for every candidate node-count/storage-tier plan in this prompt; each scored plan must include `estT_prod`, `estT_cons`, `workflow_io_time`, `data_movement_time`, and final `dpm`; the table must identify the deterministic lowest-DPM plan, must record that it was derived from the existing DataLife profile for this workflow/scale, and is reused unchanged across all trials for this workflow/scale/setup. It must not be derived from `prepare_and_dump_dpm` or other movement-node exports alone. Report whether your selected deployment follows or overrides that lowest-DPM plan. Do not make live Widget MCP calls in this decision-agent prompt.

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
8. Cite the DPM score table, the deterministic DPM-best plan, and whether the selected deployment follows or overrides DPM.
9. Apply the tie-breaking rules below.
10. Save the required decision report for the neutral executor.

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
prompt_record_id: <workflow>_<scale>_wdd_pair_dpm_<timestamp>
prompt_version: 3
setup: wdd_pair_dpm
workflow: Montage 30GB
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
  widget_mcp_live_calls: false
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
    dpm_score: <float>
    is_dpm_best: <true|false>
    expected_runtime_rank: <int or unknown>
    reason_selected_or_rejected: <text>
dpm_evidence:
  dpm_table_path: <path>
  dpm_table_sha256: <sha256 if provided by orchestrator>
  dpm_provenance: DataLife-derived static Widget DPM artifact
  datalife_profile_id_or_path: <path/id from DPM artifact metadata, not raw traces unless explicitly allowed>
  datalife_profile_sha256: <sha256 if provided by orchestrator>
  all_candidate_plans_scored: <true|false>
  dpm_selected_node_count: <int>
  dpm_selected_storage_tier: <beegfs|scratch|tmpfs>
  agent_followed_dpm_argmin: <true|false>
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
