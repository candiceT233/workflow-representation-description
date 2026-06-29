# Portable Agentic Workflow I/O Evaluation Runbook

This document describes how to reproduce the workflow I/O optimization evaluation on a different HPC cluster. It is written to be portable: cluster-specific paths, accounts, partitions, storage labels, and module commands should be supplied in a local site configuration before running.

## Evaluation Goal

Measure whether an agent can improve workflow deployment choices using several input regimes:

- `code_only`: repository and run-script exploration only; the agent must infer an I/O-improved deployment relative to the BeeGFS baseline without WDD or DPM inputs.
- `wdd_pair_only`: code plus only the `WDD.yml` and `IODD.yml` files; the agent must infer an I/O-improved deployment relative to the BeeGFS baseline. This is an ablation, not the default WDD-suite condition.
- `wdd_pair_dpm`: code, `WDD.yml`, `IODD.yml`, and statically computed Widget DPM scores; the agent must infer an I/O-improved deployment relative to the BeeGFS baseline. This is also an ablation.
- `code_dpm`: workflow repository/scripts plus statically computed Widget DPM scores, with no WDD-suite YAML files; the agent must infer an I/O-improved deployment relative to the BeeGFS baseline.
- `dpm_only`: statically computed Widget DPM scores as a compressed decision signal, with no repository/scripts and no WDD-suite YAML files; the agent must infer an I/O-improved deployment relative to the BeeGFS baseline.

Deferred setups retained for later prompt review but not active in the current
rerun:

- `wdd_full_only`: code plus the full WDD document suite generated from code exploration plus profiling traces; the agent must infer an I/O-improved deployment relative to the BeeGFS baseline.
- `wdd_full_dpm`: code, the full WDD document suite, and statically computed Widget DPM scores; the agent must infer an I/O-improved deployment relative to the BeeGFS baseline.

Each setup is compared against a BeeGFS/shared-filesystem baseline. The evaluation must report both the selected node scale and selected storage tier, because node count is part of the deployment decision.

## Required Runtime Metrics

Use these definitions consistently across clusters:

- `stage_s`: time to move/copy workflow inputs into the selected execution storage tier.
- `exec_s`: time to run the workflow task phase.
- `deployment_runtime_s`: `stage_s + exec_s`.
- `validation_s`: output validation/comparison time.
- `workflow_runtime_s`: same as `deployment_runtime_s`; validation is measured but not counted as workflow runtime.

Validation must be retained in reports because it detects incorrect deployments, but it is not normal workflow runtime.

## Cluster Site Configuration

Create a small local configuration file for each target cluster. At minimum record:

```bash
export EVAL_ACCOUNT=<slurm-account>
export EVAL_PARTITION=<slurm-partition>
export EVAL_SHARED_ROOT=<shared-parallel-filesystem-project-dir>
export EVAL_RUN_ROOT=<project-local-evaluation-dir>
export EVAL_SCRATCH_ROOT=<node-local-or-fast-scratch-root>
export EVAL_TMPFS_ROOT=/dev/shm/$USER
export EVAL_WIDGET_REPO=<path-to-widget-repo>
export EVAL_WORKFLOW_REPO_ROOT=<path-to-workflow-repos>
```

Storage labels must be mapped explicitly:

| Portable label | Meaning | Example on current cluster |
|---|---|---|
| `beegfs` | Shared parallel filesystem, no agentic staging | `/rcfs/...` with `stat -f -c %T == fhgfs` |
| `scratch` | Disk-backed node-local or fast per-node scratch | `/scratch/$USER/...` |
| `tmpfs` | Memory-backed per-node storage | `/dev/shm/$USER/...` |

Do not assume `/scratch` is node-local. Verify with the cluster documentation and `stat -f -c %T`. If it is shared or quota-limited, describe that in the site config and interpret results accordingly.

## Storage Candidate Policy

Baseline runs:

- Use `beegfs` only.
- Do not stage inputs or outputs to scratch/tmpfs.
- Evaluate all candidate node counts for a reference scale comparison.

Agentic runs:

- Candidate storage tiers are `beegfs`, `scratch`, and `tmpfs`.
- `beegfs` means no staging; the workflow reads inputs and writes outputs on the shared filesystem.
- `scratch` means stage each task/node shard to scratch when capacity allows.
- `tmpfs` means stage each task/node shard to memory-backed storage when capacity allows.

The agent must be allowed to choose `beegfs`. This is important because some workloads or scales may not benefit from staging, and the evaluation should measure whether the agent recognizes that.

## Fresh Trial Protocol

Run three independent trials for each workflow and setup.

For each trial:

1. Create a fresh trial input directory under the shared evaluation root.
2. Copy or generate the workflow input into that trial directory.
3. Run BeeGFS baseline at each candidate node count.
4. Run the selected agentic setups over the same node-count and storage-tier candidate set.
5. Validate outputs against the trial baseline outputs.
6. Delete job-owned temporary scratch/tmpfs directories.

Do not reuse a partially completed trial as a new trial. Reusing already-generated immutable source inputs is acceptable only if the per-trial execution input directory is freshly staged or generated and the report records that policy.

## Agent Isolation Protocol

For an end-to-end agentic evaluation, each setup should start from a clean instruction context:

- The `code_only` agent receives only the workflow repository, run scripts, local cluster site config, allowed node/storage candidates, BeeGFS baseline definition, and runtime metric definition. Its task is to infer workflow I/O behavior and choose an I/O-improved deployment relative to that baseline.
- The `wdd_pair_only` agent receives the same plus only `WDD.yml` and `IODD.yml`. Its task is to choose an I/O-improved deployment relative to the BeeGFS baseline.
- The `wdd_pair_dpm` agent receives the same as `wdd_pair_only` plus statically computed Widget DPM score outputs. Its task is to choose an I/O-improved deployment relative to the BeeGFS baseline.
- The `code_dpm` agent receives workflow repository/scripts, local cluster site config, allowed node/storage candidates, and statically computed Widget DPM score outputs. Its task is to choose an I/O-improved deployment relative to the BeeGFS baseline. It must not receive WDD-suite YAML files, prior reports, or chat-derived conclusions.
- The `dpm_only` agent receives only local cluster site config, allowed node/storage candidates, statically computed Widget DPM score outputs, and minimal labels needed to interpret the score table. Its task is to choose an I/O-improved deployment relative to the BeeGFS baseline. It must not receive workflow repository/scripts, WDD-suite YAML files, prior reports, or chat-derived conclusions.

Deferred full-suite setups:

- The `wdd_full_only` agent receives the same plus the full WDD document suite. Its task is to choose an I/O-improved deployment relative to the BeeGFS baseline.
- The `wdd_full_dpm` agent receives the same as `wdd_full_only` plus statically computed Widget DPM score outputs. Its task is to choose an I/O-improved deployment relative to the BeeGFS baseline.

Do not give later agents conclusions learned from earlier runs unless those conclusions are present in the allowed input artifacts. If a workflow dependency rule is important, it must be in the allowed WDD-suite files or derivable from the repository/scripts.

## WDD Suite Definition

The default WDD-suite condition means the complete YAML set, not only `WDD.yml` and `IODD.yml`.

Required full-suite files:

- `WDD.yml`: workflow stages, tasks, data objects, data dependencies, scale options, storage candidates, and workflow-level anti-patterns.
- `IODD.yml`: empirical I/O observations, profiler capability notes, bottleneck hypotheses, optimization opportunities, and negative evidence.
- `HRD.yml`: hardware/resource description, scheduler, node topology, and storage hierarchy.
- `GD.yml`: goals, constraints, success criteria, and evaluation objective.
- `DDD.yml`: deployment description or prescription, cleanup policy, and scheduler/runtime choices.
- `EDD_*.yml`: experiment definitions for relevant scales.

For Montage/DataLife, the full suite currently contains:

```bash
DDD.yml
EDD_30gb_120node.yml
EDD_6gb_16node.yml
GD.yml
HRD.yml
IODD.yml
WDD.yml
```

For 1000 Genome/DataLife, the full suite currently contains:

```bash
DDD.yml
EDD_10chr_10node.yml
EDD_10chr_5node.yml
GD.yml
HRD.yml
IODD.yml
WDD.yml
```

If an evaluation uses only `WDD.yml` and `IODD.yml`, label it `wdd_pair_only` or `wdd_pair_dpm` in reports. Do not call that the full WDD suite.

## Widget DPM Protocol

For every DPM-enabled setup (`code_dpm`, `dpm_only`, `wdd_pair_dpm`, and
`wdd_full_dpm`), DPM must be used as a candidate-plan scoring function, not as a
vague guidance label.

The candidate-plan table must be generated from Widget's full DPM scoring path
(`predict_dpm_space` or `analyze_workflow_dpm`). Do not use
`prepare_and_dump_dpm` / `dpm_export.py` movement-node exports as the normalized
candidate-plan table. Those exports estimate movement-node costs only; they may
be kept as supporting provenance, but they do not include the full producer and
consumer workflow I/O terms required for candidate-plan DPM.

Before starting the decision agent, run Widget DPM over the full deployment
candidate space:

```text
candidate_plan_space = candidate_node_counts x candidate_storage_tiers
```

For Montage 30GB, this means DPM must score all nine plans:

```text
30/beegfs, 30/scratch, 30/tmpfs
60/beegfs, 60/scratch, 60/tmpfs
120/beegfs, 120/scratch, 120/tmpfs
```

For 1000 Genome 10 chromosomes, this means DPM must score all nine plans:

```text
2/beegfs, 2/scratch, 2/tmpfs
5/beegfs, 5/scratch, 5/tmpfs
10/beegfs, 10/scratch, 10/tmpfs
```

The DPM bundle must contain:

- the raw Widget DPM output,
- a normalized candidate-plan score table,
- per-plan `estT_prod`, `estT_cons`, `workflow_io_time`,
  `data_movement_time`, and final `dpm`,
- checksums for both files,
- the deterministic DPM argmin deployment,
- a note describing any candidate plan that could not be scored.

Validation gate: before launching a DPM-enabled decision agent, inspect the
normalized table and confirm every scored candidate has the required full-DPM
fields. A zero `data_movement_time` is acceptable only when the plan genuinely
requires no movement; `workflow_io_time` must still be present and must not be
replaced by movement time.

The DPM bundle must not contain measured runtime results, previous agent
choices, report summaries, or chat-derived conclusions.

For `wdd_pair_dpm` and `wdd_full_dpm`:

1. Register the workflow in the Widget config so Widget can find the workflow representation and trace-derived graph.
2. Verify the node-count candidates match the experiment design.
3. Verify storage candidates include `beegfs`, `scratch`, and `tmpfs` when those tiers exist on the target cluster.
4. Run Widget DPM across the full candidate-plan space using the existing
   DataLife profile for the same workflow/scale as upstream profiler evidence.
5. Record the DPM inputs, raw outputs, normalized static score table, and argmin in
   the report directory.
6. Give the static DPM score table to the decision agent as an allowed input.
7. Reuse the same static DPM score table unchanged across all trials for the
   same workflow/scale/setup.
8. Record DPM artifact provenance: source profiler type `DataLife`, DataLife
   profile path/id, DataLife profile checksum if available, Widget config or
   workflow identifier, candidate node/storage set, raw DPM output path, and
   normalized table checksum.
9. Do not include raw DataLife traces in the decision-agent bundle unless a
   setup explicitly allows traces; DPM-enabled setups consume the static DPM
   artifact and provenance metadata.

If Widget cannot represent the workflow as a DAG, use producer-consumer task pairs when that is the correct model for the workflow.

For `code_dpm`:

1. The agent may inspect workflow source, run scripts, and cluster site config.
2. The agent may inspect the statically computed Widget DPM candidate-plan
   score table and raw DPM output.
3. The agent may inspect DPM provenance metadata identifying the existing
   DataLife profile used to compute DPM, but not raw DataLife traces.
4. The agent must not inspect any WDD-suite YAML files or prior evaluation reports.
5. Record the static DPM score table, DPM argmin, agent-selected deployment, and source
   files inspected in the report.

For `dpm_only`:

1. The agent may inspect the statically computed Widget DPM candidate-plan
   score table and raw DPM output.
2. The agent may inspect DPM provenance metadata identifying the existing
   DataLife profile used to compute DPM, but not raw DataLife traces.
3. The agent may inspect only minimal labels required to map scores to choices: workflow name, candidate node counts, storage labels, and edge names.
4. The agent must not inspect workflow source, run scripts, WDD-suite YAML files, raw DataLife traces, or prior evaluation reports.
5. Record exactly which static DPM score table and label schema were provided.
6. If the agent does not select the DPM argmin, it must explicitly state why it
   overrode the deterministic DPM-best plan using only allowed evidence.

## Montage 30GB Evaluation

Workload:

- Workflow phase: Montage `mProjectPP` reprojection.
- Input scale: 15,000 FITS tiles, approximately 30GB total.
- Candidate node counts: `30`, `60`, `120`.
- Baseline reference: BeeGFS/shared filesystem at all three node counts.
- Agentic storage candidates: `beegfs`, `scratch`, `tmpfs`.

Execution model:

1. Stage/generate the 30GB FITS input set into a fresh per-trial shared directory.
2. For each node count, shard input files by Slurm rank.
3. Baseline uses the shared tile directory directly and writes projected FITS files to shared output.
4. Agentic `beegfs` uses the shared tile directory directly and writes to a separate shared output path.
5. Agentic `scratch`/`tmpfs` copies each rank's shard plus `template.hdr` to the selected local tier, runs `mProjectPP`, and validates outputs against baseline.

Required outputs:

- Raw timing log for every trial/setup/node/storage combination.
- Aggregate table by setup, node count, and storage tier.
- Per-trial selected deployment for baseline and each agentic setup.
- Mean and sample standard deviation over three trials.
- Plot of selected deployment runtime mean/std.
- Plot of runtime by scale and storage tier.

Current full-suite Montage rerun modes:

- `wdd_full_only`: full WDD suite, no DPM scores.
- `wdd_full_dpm`: full WDD suite plus statically computed Widget DPM scores.

Current DPM ablation Montage rerun modes:

- `code_dpm`: repository/scripts plus statically computed Widget DPM scores, no WDD-suite YAML files.
- `dpm_only`: statically computed Widget DPM scores plus minimal labels only, no repository/scripts and no WDD-suite YAML files.

## 1000 Genome Evaluation

Workload:

- Workflow stages: `individuals`, `individuals_merge`, `sifting`, `mutation_overlap`, `frequency`.
- Input scale: 10 chromosomes.
- Candidate node counts: `2`, `5`, `10`.
- Baseline reference: BeeGFS/shared filesystem at all three node counts.
- Agentic storage candidates: `beegfs`, `scratch`, `tmpfs`.

Execution model:

1. Run the default workflow unchanged for BeeGFS baseline.
2. Preserve chromosome-level data locality where the workflow naturally has independent chromosome partitions.
3. Do not stage out intermediate chromosome-local data unless it is a required final output.
4. Validate the final outputs against the baseline.

The WDD/IODD should explicitly describe chromosome-local dependencies so a fresh agent can infer that intermediate stage-out is unnecessary.

## Slurm Execution Pattern

Use dependency chains to keep the experiment clean and avoid resource spikes:

```bash
stage_job=$(sbatch --parsable \
  --account="$EVAL_ACCOUNT" \
  --partition="$EVAL_PARTITION" \
  --export=ALL,DEST="$trial_input_dir" \
  stage_input.sbatch)

run_job=$(sbatch --parsable \
  --dependency=afterok:$stage_job \
  --nodes="$nodes" \
  --account="$EVAL_ACCOUNT" \
  --partition="$EVAL_PARTITION" \
  --export=ALL,MODE="$mode",STORAGE_TIER="$storage",TILE_DIR="$trial_input_dir" \
  run_mode.sbatch)
```

For large matrices, serialize jobs within a trial unless the cluster allocation explicitly permits concurrent runs. Serialization makes filesystem contention easier to interpret and avoids accidentally benchmarking interference between your own jobs.

## Cleanup Requirements

Every run script must clean:

- Per-job scratch directories under `$EVAL_SCRATCH_ROOT`.
- Per-job tmpfs directories under `$EVAL_TMPFS_ROOT`.
- Incomplete per-trial shared input/output directories from canceled runs.

Never delete outside the project/evaluation roots except job-owned scratch/tmpfs paths created by the current evaluation. Keep project-side logs and reports for audit.

Recommended naming:

```bash
TAG=<workflow>_<scale>_3trial_<UTC timestamp>
LOCALBASE=$EVAL_SCRATCH_ROOT/${TAG}_${nodes}node_${mode}_${storage}_${SLURM_JOB_ID}
TMPFSBASE=$EVAL_TMPFS_ROOT/${TAG}_${nodes}node_${mode}_${storage}_${SLURM_JOB_ID}
```

## Report Checklist

Each final report should include:

- Workflow name, scale, input size, and candidate node counts.
- Storage candidates and the storage mapping for the cluster.
- Setup definitions and allowed inputs.
- Per-trial selected node count before improvement: best BeeGFS baseline scale.
- Per-trial selected node count and storage tier after improvement for each setup.
- Runtime mean and sample standard deviation over three trials.
- Validation time reported separately.
- Output correctness status.
- Static DPM candidate-plan score table, DPM argmin, agent-selected deployment, and
  whether the agent followed the DPM argmin for every DPM-enabled setup.
- Plots for selected deployment runtime and runtime by scale/storage.
- Notes on scheduler delays, cache effects, and any failed or canceled jobs.

## Portability Checks Before Running

Run these checks on the target cluster:

```bash
hostname
sinfo -p "$EVAL_PARTITION"
stat -f -c '%T %m' "$EVAL_SHARED_ROOT"
stat -f -c '%T %m' "$EVAL_SCRATCH_ROOT" || true
df -h "$EVAL_TMPFS_ROOT"
ulimit -a
```

Also verify:

- Required compilers, Python, workflow binaries, and profiler libraries are installed.
- The Slurm account can request every candidate node count.
- `tmpfs` has enough per-node capacity for the staged shard plus output files.
- Scratch quotas and purge policy are compatible with the trial duration.
- Output validation tools are available without adding large runtime overhead to `deployment_runtime_s`.

## Current Cluster Example

The current PNNL run uses:

```bash
export EVAL_ACCOUNT=oddite
export EVAL_PARTITION=slurm
export EVAL_RUN_ROOT=/qfs/projects/datamesh/tang584/widget_evaluation
export EVAL_SHARED_ROOT=/rcfs/projects/chess/tang584
export EVAL_SCRATCH_ROOT=/scratch/$USER
export EVAL_TMPFS_ROOT=/dev/shm/$USER
```

Current Montage three-trial harness:

```bash
workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/submit_montage_3trials.sh
workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/run_trial_mode.sbatch
workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/trial_worker.sh
workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/generate_report.py
```

Current full WDD-suite source for Montage:

```bash
workflow_representation_experiments/Montage/datalife_code/docs/DDD.yml
workflow_representation_experiments/Montage/datalife_code/docs/EDD_30gb_120node.yml
workflow_representation_experiments/Montage/datalife_code/docs/EDD_6gb_16node.yml
workflow_representation_experiments/Montage/datalife_code/docs/GD.yml
workflow_representation_experiments/Montage/datalife_code/docs/HRD.yml
workflow_representation_experiments/Montage/datalife_code/docs/WDD.yml
workflow_representation_experiments/Montage/datalife_code/docs/IODD.yml
```
