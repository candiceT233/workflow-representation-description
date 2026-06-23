# Montage 30GB Agent Context and Prompt Reconstruction

## Status

The exact verbatim prompts used during the Montage 30GB agentic evaluation were
not saved as standalone prompt files. This document records the recoverable
agent context, setup boundaries, and reconstructed prompt templates from the
available run harnesses, reports, and evaluation runbook.

This should be treated as a reconstruction for audit and future reruns, not as a
verbatim transcript of the original prompts.

## Evaluation Goal

Evaluate whether an agent can improve workflow deployment choices for Montage
30GB by selecting node count and storage tier under different information
regimes. Compare each agentic condition against a BeeGFS/shared-filesystem
baseline.

The evaluation asks whether different inputs lead to:

- faster measured runtime,
- stable deployment decisions across trials,
- correct output generation,
- interpretable reasoning about storage and node-scale choices.

## Common Experiment Context

- Workflow: Montage `mProjectPP` reprojection.
- Input scale: 15,000 FITS tiles, approximately 30GB total.
- Candidate node counts: `30`, `60`, `120`.
- Candidate storage tiers for agentic setups: `beegfs`, `scratch`, `tmpfs`.
- Baseline storage: `beegfs` only.
- Runtime metric: deployment runtime, excluding validation/comparison time.
- Validation: output correctness check retained separately.
- Slurm account: `oddite`.
- Slurm partition: `slurm`.
- Cleanup requirement: remove only job-owned scratch/tmpfs data; keep project
  reports and timing logs.

## Setup Definitions

### Baseline

No agentic optimization. Run BeeGFS-only baseline at all candidate node counts.
The selected baseline in reports is the best BeeGFS deployment for each trial,
while fixed-node BeeGFS means are reported separately.

### code_only

Allowed inputs:

- workflow repository and scripts,
- local cluster/site configuration,
- candidate node counts,
- candidate storage tiers.

Disallowed inputs:

- WDD/IODD/HRD/GD/DDD/EDD YAML documents,
- Widget DPM scores,
- prior evaluation reports,
- chat-derived conclusions from other setups.

### code_dpm

Allowed inputs:

- same as `code_only`,
- Widget DPM score outputs.

Disallowed inputs:

- WDD-suite YAML documents,
- prior evaluation reports,
- chat-derived conclusions from other setups.

### dpm_only

Allowed inputs:

- candidate node counts,
- candidate storage tiers,
- Widget DPM score outputs,
- minimal labels needed to map DPM scores to workflow edges/storage choices.

Disallowed inputs:

- workflow repository and scripts,
- WDD-suite YAML documents,
- prior evaluation reports,
- chat-derived conclusions from other setups.

### wdd_pair_only

This is an ablation condition. The hypothesis is: what if the agent receives
only the workflow/deployment structure and I/O-pattern description, instead of
the full WDD suite?

Allowed inputs:

- workflow repository and scripts,
- local cluster/site configuration,
- candidate node counts,
- candidate storage tiers,
- `WDD.yml`,
- `IODD.yml`.

Disallowed inputs:

- `HRD.yml`, `GD.yml`, `DDD.yml`, `EDD_*.yml`,
- Widget DPM scores,
- prior evaluation reports,
- chat-derived conclusions from other setups.

### wdd_pair_dpm

This is the WDD-pair ablation plus Widget DPM guidance.

Allowed inputs:

- same as `wdd_pair_only`,
- Widget DPM score outputs.

Disallowed inputs:

- full WDD-suite files beyond `WDD.yml` and `IODD.yml`,
- prior evaluation reports,
- chat-derived conclusions from other setups.

### wdd_full_only

Allowed inputs:

- workflow repository and scripts,
- local cluster/site configuration,
- candidate node counts,
- candidate storage tiers,
- full WDD suite: `WDD.yml`, `IODD.yml`, `HRD.yml`, `GD.yml`, `DDD.yml`,
  `EDD_*.yml`.

Disallowed inputs:

- Widget DPM scores,
- prior evaluation reports,
- chat-derived conclusions from other setups.

### wdd_full_dpm

Allowed inputs:

- same as `wdd_full_only`,
- Widget DPM score outputs.

Disallowed inputs:

- prior evaluation reports,
- chat-derived conclusions from other setups.

## Reconstructed Common Prompt Template

The following prompt template captures the intended instruction used for each
agentic setup. It is reconstructed from the runbook and harness behavior.

```text
You are evaluating deployment choices for the Montage 30GB workflow on this HPC
cluster.

Goal:
Choose a deployment strategy that minimizes measured workflow deployment
runtime while preserving output correctness.

Workflow:
- Montage mProjectPP reprojection.
- Input scale: 15,000 FITS tiles, about 30GB total.

Allowed deployment choices:
- Node counts: 30, 60, 120.
- Storage tiers: beegfs, scratch, tmpfs.

Baseline:
- BeeGFS-only.
- No scratch/tmpfs staging.
- Baseline must be evaluated at all candidate node counts.

Runtime accounting:
- Count stage-in plus execution time as workflow deployment runtime.
- Keep validation/comparison time separately.
- Do not include validation time in workflow runtime.

Cluster constraints:
- Use Slurm account oddite.
- Use Slurm partition slurm.
- Respect shared filesystem usage.
- Use only job-owned scratch/tmpfs paths.
- Clean job-owned temporary files after copying required outputs and logs.
- Do not remove anything outside the project/evaluation roots except job-owned
  scratch/tmpfs paths created by this run.

Required output:
1. Explain the selected deployment strategy.
2. Identify selected node count and storage tier.
3. Explain why the strategy should improve I/O behavior.
4. Run the workflow at the selected deployment.
5. Validate output correctness against the baseline.
6. Report deployment runtime, validation time, output status, and cleanup status.
7. Record enough logs and metadata for audit.

Use only the inputs allowed for this setup. Do not use prior results or
cross-setup conclusions unless they are present in the allowed input artifacts.
```

## Setup-Specific Prompt Additions

### code_only Addition

```text
You may inspect only the workflow repository, run scripts, local cluster/site
configuration, and the candidate node/storage list. Do not inspect WDD-suite
YAML files, Widget DPM outputs, or previous reports.
```

### code_dpm Addition

```text
You may inspect the workflow repository, run scripts, local cluster/site
configuration, candidate node/storage list, and Widget DPM score outputs. Do not
inspect WDD-suite YAML files or previous reports.
```

### dpm_only Addition

```text
You may inspect only Widget DPM score outputs, the candidate node/storage list,
and minimal labels needed to map DPM scores to workflow edges/storage choices.
Do not inspect workflow source code, run scripts, WDD-suite YAML files, or
previous reports.
```

### wdd_pair_only Addition

```text
You may inspect the workflow repository, run scripts, local cluster/site
configuration, candidate node/storage list, WDD.yml, and IODD.yml. This condition
tests whether only deployment/workflow structure plus I/O-pattern information is
sufficient. Do not inspect HRD/GD/DDD/EDD files, Widget DPM outputs, or previous
reports.
```

### wdd_pair_dpm Addition

```text
You may inspect the workflow repository, run scripts, local cluster/site
configuration, candidate node/storage list, WDD.yml, IODD.yml, and Widget DPM
score outputs. Do not inspect the rest of the WDD suite or previous reports.
```

### wdd_full_only Addition

```text
You may inspect the workflow repository, run scripts, local cluster/site
configuration, candidate node/storage list, and the full WDD suite. Do not
inspect Widget DPM outputs or previous reports.
```

### wdd_full_dpm Addition

```text
You may inspect the workflow repository, run scripts, local cluster/site
configuration, candidate node/storage list, the full WDD suite, and Widget DPM
score outputs. Do not inspect previous reports.
```

## Known Limitation

Because the original prompts were not saved, this reconstruction cannot prove
the exact natural-language instruction received by each agent. Future
evaluations should write the prompt, allowed input manifest, model/agent
identity, tool availability, and output contract into the report directory before
the agent begins work.
