# Formal Agentic Evaluation Prompt Specification

Status: v3 draft for discussion

This document formalizes prompt structure for the workflow I/O deployment
evaluation. It is intended to make future agentic runs auditable by recording
the exact objective, context, allowed inputs, tool permissions, output contract,
and success criteria before each agent starts.

The current prompt templates are reconstructed from the existing evaluation
runbook and run harnesses, then refined using general prompt-engineering
guidance: place instructions first, separate instructions from context, be
specific about outcomes and format, provide explicit constraints, and define
success criteria for agentic research/action tasks. Relevant guidance reviewed:

- OpenAI prompt engineering best practices:
  https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-openai-api
- Anthropic prompting best practices:
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Anthropic context engineering for agents:
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

## Prompt Record Requirements

Every agentic evaluation run should create a prompt record before execution:

```yaml
prompt_record:
  prompt_id: <workflow>_<scale>_<setup>_<timestamp>
  workflow: <Montage|1000Genome|PyFLEXTRKR|...>
  scale: <human-readable scale>
  setup: <code_only|code_dpm|dpm_only|wdd_pair_only|wdd_pair_dpm>
  model_or_agent: <agent/model name and version if known>
  run_workspace: <path>
  allowed_input_manifest: <path to manifest file>
  prompt_file: <path to exact prompt text>
  bundle_inventory_file: <path to clean input inventory with checksums>
  neutral_executor_spec: <path to evaluator execution spec>
  output_contract_file: <path to expected decision report schema/checklist>
  tool_manifest_file: <path to allowed tools/MCPs>
  created_at_utc: <timestamp>
```

The prompt file must be immutable for the run. If a prompt is revised, create a
new prompt file and record the revision.

## Controlled Evaluation Plan

The evaluation should be run as a controlled multi-agent experiment. Each setup
is executed by a fresh agent with a fresh workspace and a setup-specific prompt.
The purpose is to isolate the effect of changing the agent's information input,
while holding the workflow, scale, candidate deployment choices, cluster
constraints, output contract, and evaluation metrics constant.

### Fixed Variables

These must remain identical across all agentic setups for a given workflow and
scale:

- workflow and input scale,
- candidate node counts,
- candidate storage tiers,
- Slurm account and partition,
- baseline definition,
- runtime accounting,
- output validation method,
- cleanup policy,
- report schema,
- number of trials,
- random/input generation policy,
- tool availability except where the tested setup explicitly changes it.

### Controlled Variable

The main experimental variable is the information available to the agent:

| Setup | Changed information input |
|---|---|
| `code_only` | code/scripts only; I/O-improvement decision relative to BeeGFS baseline |
| `code_dpm` | code/scripts + DPM |
| `dpm_only` | DPM only, with minimal labels |
| `wdd_pair_only` | code/scripts + `WDD.yml` + `IODD.yml` |
| `wdd_pair_dpm` | code/scripts + `WDD.yml` + `IODD.yml` + DPM |

Deferred setups retained for later prompt review, but not active in the current
rerun:

| Deferred Setup | Changed information input |
|---|---|
| `wdd_full_only` | code/scripts + full WDD suite |
| `wdd_full_dpm` | code/scripts + full WDD suite + DPM |

Everything else should be held constant unless the setup definition explicitly
requires otherwise.

### DPM-Enabled Setup Requirement

For every active DPM-enabled setup (`code_dpm`, `dpm_only`, and
`wdd_pair_dpm`), DPM must be provided as a complete candidate-plan score table.
The same requirement applies if deferred `wdd_full_dpm` is reactivated later.
It is not sufficient to provide an informal DPM summary.

Before the decision agent starts, the orchestrator must use Widget DPM to score
every deployment plan in:

```text
candidate_node_counts x candidate_storage_tiers
```

The DPM artifact bundle must include:

- raw Widget DPM output,
- normalized candidate-plan score table,
- one score per node-count/storage-tier plan,
- deterministic lowest-DPM plan,
- checksums for DPM artifacts,
- explicit notes for any candidate that could not be scored.

The DPM artifact bundle must not include measured runtime results, previous
agent choices, report summaries, or chat-derived conclusions.

Reports must distinguish:

- the DPM argmin deployment,
- the agent-selected deployment,
- the neutral-executor measured runtime,
- whether the agent followed or overrode the DPM argmin.

### Baseline Procedure

The baseline is not an agentic setup and does not receive an agent prompt. It is
a fixed reference:

1. Run BeeGFS-only deployment at every candidate node count.
2. Copy all baseline outputs required by the workflow's default execution.
3. Validate baseline outputs.
4. Report both fixed-node baseline runtimes and per-trial best BeeGFS baseline.

The per-trial best BeeGFS baseline is an oracle-style reference. It must be
labeled separately from fixed-node baseline runtimes.

### Fresh Agent Protocol

For every agentic setup:

1. Start a new agent session.
2. Provide only the setup-specific prompt file.
3. Provide only the setup-specific allowed input manifest.
4. Provide a clean input bundle created from the matching bundle-builder spec.
5. Use a fresh workspace.
6. Do not include previous setup results, previous agent conclusions, or chat
   summaries unless they are listed as allowed inputs.
7. Require the agent to write a decision report only.
8. Do not allow the decision agent to submit Slurm jobs, execute workflow
   scripts, call subagents, use web access, or make live Widget MCP calls.
9. Require a neutral executor to run the selected deployment and record exact
   commands, inputs, outputs, timing, validation, and cleanup.

### Trial Protocol

For each workflow/scale/setup:

1. Run three independent trials.
2. Each trial must start from a fresh execution directory.
3. Immutable source input may be reused only if that reuse is recorded.
4. Scratch/tmpfs paths must be job-scoped and removed after each job.
5. Validation must be run every trial and reported separately from runtime.

### Evaluation Metrics

Report:

- selected node count per trial,
- selected storage tier per trial,
- deployment runtime per trial,
- validation time per trial,
- output correctness,
- for DPM-enabled setups: statically computed full candidate-plan DPM score table,
- for DPM-enabled setups: DPM artifact provenance showing the static table was
  derived from the existing DataLife profile for the same workflow/scale,
- for DPM-enabled setups: deterministic DPM argmin deployment,
- for DPM-enabled setups: whether the agent followed or overrode the DPM argmin,
- mean deployment runtime,
- sample standard deviation,
- speedup against fixed-node baselines,
- speedup against per-trial best BeeGFS baseline,
- choice stability score:
  - exact deployment stability: same node count and storage tier,
  - node-count stability,
  - storage-tier stability.

### Required Prompt Files

For each workflow/scale, create one prompt file per setup:

```text
prompts/
  <workflow>_<scale>_code_only_prompt.txt
  <workflow>_<scale>_code_dpm_prompt.txt
  <workflow>_<scale>_dpm_only_prompt.txt
  <workflow>_<scale>_wdd_pair_only_prompt.txt
  <workflow>_<scale>_wdd_pair_dpm_prompt.txt
  deferred/<workflow>_<scale>_wdd_full_only_prompt.txt
  deferred/<workflow>_<scale>_wdd_full_dpm_prompt.txt
```

Also create manifests:

```text
manifests/
  <workflow>_<scale>_code_only_allowed_inputs.yml
  <workflow>_<scale>_code_dpm_allowed_inputs.yml
  <workflow>_<scale>_dpm_only_allowed_inputs.yml
  <workflow>_<scale>_wdd_pair_only_allowed_inputs.yml
  <workflow>_<scale>_wdd_pair_dpm_allowed_inputs.yml
  <workflow>_<scale>_wdd_full_only_allowed_inputs.yml
  <workflow>_<scale>_wdd_full_dpm_allowed_inputs.yml
```

The prompt file and manifest together define the experimental condition.

Also create orchestrator-only specs that are not given to the decision agent:

```text
bundle_builder_specs/
  <workflow>_<scale>_<setup>_bundle_builder_spec.md

neutral_executor_specs/
  <workflow>_<scale>_<setup>_neutral_executor_spec.md

baseline_specs/
  <workflow>_<scale>_baseline_execution_spec.md
```

### Evaluation Order

Recommended order:

1. Baseline at all node counts.
2. `code_only`.
3. `code_dpm`.
4. `dpm_only`.
5. `wdd_pair_only`.
6. `wdd_pair_dpm`.

Deferred and not active in the current rerun:

7. `wdd_full_only`.
8. `wdd_full_dpm`.

This order is for experiment management only. Agents must not receive results
from earlier conditions.

### Current Workflow/Scale Matrix

Initial controlled matrix:

| Workflow | Scale | Candidate nodes | Candidate storage | Status |
|---|---|---|---|---|
| Montage | 30GB / 15,000 FITS tiles | `30`, `60`, `120` | `beegfs`, `scratch`, `tmpfs` | reports exist; prompts reconstructed |
| 1000Genome | 10 chromosomes | `2`, `5`, `10` | `beegfs`, `scratch`, `tmpfs` | running; prompts need formalization before additional reruns |

Future optional matrix:

| Workflow | Scale | Notes |
|---|---|---|
| PyFLEXTRKR | 480 files / 80 nodes | existing earlier comparison only; prompt formalization needed before rerun |
| Montage | 6GB / 16 and 120 nodes | useful for scale-transfer comparison |

Do not start new evaluations until the prompt files and allowed-input manifests
for the target workflow/scale have been reviewed.

## Formal Prompt Sections

Use these sections in order.

### 1. Role

Defines the agent identity and expertise.

Example:

```text
You are an HPC workflow I/O deployment engineer. Your task is to choose one
workflow deployment strategy under the exact input and tool constraints listed
below.
```

### 2. Objective

Defines the goal in measurable terms.

Example:

```text
Choose an I/O-improved deployment expected to reduce workflow runtime relative
to the BeeGFS baseline while preserving output correctness. The deployment
choice includes both node count and storage tier. A neutral executor, not this
decision agent, will run the workflow and measure runtime.
```

### 3. Evaluation Question

States what the experiment is trying to learn.

Example:

```text
This setup tests whether the allowed input regime is sufficient for an agent to
choose an I/O-improved node-count and storage-tier deployment compared with the
BeeGFS baseline.
```

### 4. Workflow And Scale Context

Provides only the workflow/scale information allowed for the setup.

Example fields:

```yaml
workflow_name: Montage
workflow_phase: mProjectPP reprojection
scale: 30GB
input_count: 15000 FITS tiles
candidate_node_counts: [30, 60, 120]
candidate_storage_tiers: [beegfs, scratch, tmpfs]
baseline_storage: beegfs
```

### 5. Cluster And Resource Context

States scheduler, storage mapping, and resource constraints.

Example:

```yaml
slurm_account: oddite
slurm_partition: slurm
shared_storage:
  label: beegfs
  path_root: /rcfs/projects/chess/tang584
scratch_storage:
  label: scratch
  path_root: /scratch/$USER
tmpfs_storage:
  label: tmpfs
  path_root: /dev/shm/$USER
cleanup_policy:
  remove_job_owned_scratch: true
  remove_job_owned_tmpfs: true
  do_not_remove_outside_project: true
```

### 6. Allowed Inputs

Lists exactly what this agent may inspect. This section is the core of the
evaluation design.

Example:

```text
You may inspect:
- workflow repository files under <path>
- run scripts under <path>
- local cluster site config under <path>
- candidate node/storage list in this prompt
```

### 7. Disallowed Inputs

Lists what this agent must not inspect.

Example:

```text
You must not inspect:
- WDD-suite YAML files
- Widget DPM output files
- prior evaluation reports
- notes or summaries from other setup runs
```

### 8. Allowed Tools

Records tool availability. For reproducibility, this should include local shell
inspection, Slurm submission, workflow execution, Widget MCP, web access, and
whether subagents are allowed. In v3 prompts, the decision agent is
decision-only: Slurm submission, workflow execution, web access, subagents, and
live Widget MCP calls are disabled.

Example:

```yaml
allowed_tools:
  shell_read_clean_bundle: true
  write_decision_report: true
  slurm_submit: false
  workflow_execution: false
  widget_mcp: false
  web_access: false
  subagents: false
```

### 9. Required Procedure

Gives ordered steps. In v3, this prevents the decision agent from crossing into
execution, validation, or cleanup work owned by the neutral executor.

Example:

```text
1. Inspect only allowed inputs.
2. Record the files inspected.
3. Select exactly one node count and one storage tier.
4. Specify the intended stage-in, workflow-storage, and stage-out policy.
5. Estimate staging overhead, storage-capacity risk, and scheduler feasibility.
6. Compare the selected deployment against every candidate node/storage pair.
7. Apply tie-breaking rules.
8. Save the decision report for the neutral executor.
```

### 10. Decision Criteria

States how the agent should choose among options.

Example:

```text
Prefer the deployment with the best expected workflow runtime subject to:
- output correctness,
- storage capacity,
- scheduler feasibility,
- cleanup requirements,
- stage-in and stage-out overhead,
- shared filesystem load.

Tie-breaking rules:
- If expected runtime difference is below 10%, prefer the simpler deployment
  with less data movement.
- If storage choices appear equivalent, prefer the storage tier requiring fewer
  staging steps.
- If node choices appear equivalent, prefer the lower node count.
```

### 11. Output Contract

Defines the exact output required from the agent.

Example:

```yaml
agent_output:
  prompt_version: 3
  selected_node_count: <int>
  selected_storage_tier: <beegfs|scratch|tmpfs>
  stage_in_policy: <text>
  workflow_storage_policy: <text>
  stage_out_policy: <text>
  expected_improvement_reason: <paragraph>
  confidence: <low|medium|high>
  assumptions:
    - <text>
  evidence_used:
    - <file/path/tool output>
  files_inspected:
    - <path>
  candidate_comparison:
    - node_count: <int>
      storage_tier: <beegfs|scratch|tmpfs>
      dpm_score: <float or not_applicable>
      is_dpm_best: <true|false|not_applicable>
      expected_runtime_rank: <int or unknown>
      reason_selected_or_rejected: <text>
  dpm_evidence:
    dpm_table_path: <path or not_applicable>
    dpm_table_sha256: <sha256 or not_applicable>
    all_candidate_plans_scored: <true|false|not_applicable>
    dpm_selected_node_count: <int or not_applicable>
    dpm_selected_storage_tier: <beegfs|scratch|tmpfs|not_applicable>
    agent_followed_dpm_argmin: <true|false|not_applicable>
  limitations:
    - <known caveat>
```

### 12. Stop And Escalation Conditions

Defines when the agent should stop rather than continue.

Example:

```text
Stop and report if:
- the run would require files outside the allowed workspace,
- credentials or private data are requested,
- scheduler/account configuration is missing,
- selected storage capacity appears insufficient,
- required inputs are missing for this setup.
```

## Common Prompt Template

```text
<role>
You are an HPC workflow I/O deployment engineer. Your task is to choose one
workflow deployment strategy under the exact input and tool constraints listed
below.
</role>

<objective>
Choose an I/O-improved deployment expected to reduce workflow runtime relative
to the BeeGFS baseline while preserving output correctness. The deployment
choice includes both node count and storage tier. A neutral executor, not this
decision agent, will run the workflow and measure runtime.
</objective>

<evaluation_question>
This setup tests whether the allowed input regime is sufficient for an agent to
choose an I/O-improved node-count and storage-tier deployment compared with the
BeeGFS baseline.
</evaluation_question>

<workflow_context>
Workflow: {workflow_name}
Scale: {scale_description}
Candidate node counts: {candidate_node_counts}
Candidate storage tiers: {candidate_storage_tiers}
Baseline storage: BeeGFS only
</workflow_context>

<cluster_context>
Slurm account: {slurm_account}
Slurm partition: {slurm_partition}
Shared storage label/path: {shared_storage}
Scratch label/path: {scratch_storage}
Tmpfs label/path: {tmpfs_storage}
Cleanup policy: remove only job-owned scratch/tmpfs paths created by this run.
</cluster_context>

<allowed_inputs>
{allowed_input_list}
</allowed_inputs>

<disallowed_inputs>
{disallowed_input_list}
</disallowed_inputs>

<allowed_tools>
{allowed_tool_list}
</allowed_tools>

<required_procedure>
1. Inspect only allowed inputs.
2. Record the files inspected.
3. Select exactly one node count and one storage tier.
4. Specify the intended stage-in, workflow-storage, and stage-out policy.
5. Estimate staging overhead, storage-capacity risk, and scheduler feasibility.
6. Compare every candidate node/storage pair.
7. Save the required decision report for the neutral executor.
</required_procedure>

<decision_criteria>
Prefer the deployment with the best expected workflow runtime subject to output
correctness, storage capacity, scheduler feasibility, cleanup requirements, and
stage-in/stage-out overhead. If expected runtime difference is below 10%, prefer
the simpler deployment with less data movement.
</decision_criteria>

<output_contract>
Return and save:
- selected_node_count
- selected_storage_tier
- stage_in_policy
- workflow_storage_policy
- stage_out_policy
- expected_improvement_reason
- confidence
- assumptions
- evidence_used
- files_inspected
- candidate_comparison
- limitations
</output_contract>

<stop_conditions>
Stop and report if required inputs are missing, selected storage capacity
appears insufficient, scheduler/account configuration cannot be assessed, or the
task would require inspecting disallowed files or writing outside the allowed
workspace.
</stop_conditions>
```

## Setup-Specific Input Blocks

### code_only

Purpose: test whether source-code and run-script exploration alone are enough
for the agent to identify an I/O-improved deployment relative to the BeeGFS
baseline.

```text
Allowed inputs:
- workflow repository
- run scripts
- local cluster/site config
- candidate node/storage list
- BeeGFS baseline definition and runtime metric definition

Disallowed inputs:
- WDD-suite YAML files
- Widget DPM outputs
- prior evaluation reports
- chat-derived conclusions from other setup runs

Allowed tools:
- shell for read-only inspection inside the clean input bundle
- write decision report
```

### code_dpm

Purpose: test whether source code plus statically computed DPM scores let the
agent identify an I/O-improved deployment relative to the BeeGFS baseline.

```text
Allowed inputs:
- workflow repository
- run scripts
- local cluster/site config
- candidate node/storage list
- statically computed Widget DPM candidate-plan score table for every node/storage deployment plan, reused unchanged across trials
- raw Widget DPM output, deterministic DPM argmin, and DataLife-profile provenance metadata

Disallowed inputs:
- WDD-suite YAML files
- raw DataLife traces, unless explicitly included in a separate setup
- prior evaluation reports
- chat-derived conclusions from other setup runs

Allowed tools:
- shell for read-only inspection inside the clean input bundle
- write decision report
- static DPM score files copied into the clean input bundle
```

### dpm_only

Purpose: test whether statically computed DPM scores alone are enough as a
compressed decision signal for identifying an I/O-improved deployment relative
to the BeeGFS baseline.

```text
Allowed inputs:
- candidate node/storage list
- statically computed Widget DPM candidate-plan score table for every node/storage deployment plan, reused unchanged across trials
- raw Widget DPM output, deterministic DPM argmin, and DataLife-profile provenance metadata
- minimal labels needed to map DPM scores to workflow edges/storage choices

Disallowed inputs:
- workflow repository
- run scripts
- raw DataLife traces, unless explicitly included in a separate setup
- WDD-suite YAML files
- prior evaluation reports
- chat-derived conclusions from other setup runs
```

### wdd_pair_only

Purpose: test whether workflow code plus only `WDD.yml` and `IODD.yml` from the
WDD suite let the agent identify an I/O-improved deployment relative to the
BeeGFS baseline.

```text
Allowed inputs:
- workflow repository
- run scripts
- local cluster/site config
- candidate node/storage list
- WDD.yml
- IODD.yml

Disallowed inputs:
- HRD.yml
- GD.yml
- DDD.yml
- EDD_*.yml
- Widget DPM outputs
- prior evaluation reports
- chat-derived conclusions from other setup runs
```

### wdd_pair_dpm

Purpose: test whether workflow code, `WDD.yml`, `IODD.yml`, and statically
computed DPM scores let the agent identify an I/O-improved deployment relative
to the BeeGFS baseline.

```text
Allowed inputs:
- workflow repository
- run scripts
- local cluster/site config
- candidate node/storage list
- WDD.yml
- IODD.yml
- statically computed Widget DPM candidate-plan score table for every node/storage deployment plan, reused unchanged across trials
- raw Widget DPM output, deterministic DPM argmin, and DataLife-profile provenance metadata

Disallowed inputs:
- HRD.yml
- GD.yml
- DDD.yml
- EDD_*.yml
- raw DataLife traces, unless explicitly included in a separate setup
- prior evaluation reports
- chat-derived conclusions from other setup runs
```

### wdd_full_only

Purpose: test whether workflow code plus the full WDD suite let the agent
identify an I/O-improved deployment relative to the BeeGFS baseline.

```text
Allowed inputs:
- workflow repository
- run scripts
- local cluster/site config
- candidate node/storage list
- WDD.yml
- IODD.yml
- HRD.yml
- GD.yml
- DDD.yml
- EDD_*.yml

Disallowed inputs:
- Widget DPM outputs
- prior evaluation reports
- chat-derived conclusions from other setup runs
```

### wdd_full_dpm

Purpose: test whether workflow code, the full WDD suite, and statically
computed DPM scores let the agent identify an I/O-improved deployment relative
to the BeeGFS baseline.

```text
Allowed inputs:
- workflow repository
- run scripts
- local cluster/site config
- candidate node/storage list
- full WDD suite
- statically computed Widget DPM candidate-plan score table for every node/storage deployment plan, reused unchanged across trials
- raw Widget DPM output, deterministic DPM argmin, and DataLife-profile provenance metadata

Disallowed inputs:
- raw DataLife traces, unless explicitly included in a separate setup
- prior evaluation reports
- chat-derived conclusions from other setup runs
```

## Workflow-Specific Values

### Montage 30GB

```yaml
workflow_name: Montage
workflow_phase: mProjectPP reprojection
scale_description: 15000 FITS tiles, approximately 30GB
candidate_node_counts: [30, 60, 120]
candidate_storage_tiers: [beegfs, scratch, tmpfs]
baseline_policy: BeeGFS-only at each node count
selected_baseline_policy: per-trial best BeeGFS node count
```

### 1000Genome 10 Chromosomes

```yaml
workflow_name: 1000Genome
workflow_stages:
  - individuals
  - individuals_merge
  - sifting
  - mutation_overlap
  - frequency
scale_description: 10 chromosomes
candidate_node_counts: [2, 5, 10]
candidate_storage_tiers: [beegfs, scratch, tmpfs]
baseline_policy: BeeGFS-only at each node count, all outputs copied
```

## Required Prompt Artifacts Per Run

Each setup/run should save:

```text
prompt.txt
allowed_inputs.yml
bundle_inventory.yml
neutral_executor_spec.md
agent_decision_report.md
executor_commands_run.txt
executor_runtime_metrics.csv
executor_validation_report.md
executor_cleanup_report.md
```

## Open Questions For Review

1. Should baseline be reported as fixed-node baselines only, oracle-best
   per-trial baseline only, or both? The current reports use both.
2. What exact bundle-builder implementation should enforce the clean input
   folders and checksums on each target cluster?
