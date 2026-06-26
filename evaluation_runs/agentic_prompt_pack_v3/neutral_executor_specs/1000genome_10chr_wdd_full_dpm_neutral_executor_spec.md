# Neutral Executor Spec v3: 1000Genome 10 chromosomes / wdd_full_dpm

This file is for the neutral evaluator that runs a decision produced by a fresh
agent. It is not an input to the decision agent.

## Inputs

- Agent decision report for `1000genome_10chr` / `wdd_full_dpm`.
- Baseline outputs for correctness comparison.
- Workflow run harness controlled by the evaluator.

## Execution Rules

1. Read exactly one selected node count and storage tier from the decision
   report.
2. Record the DPM score table path, DPM argmin plan, and whether the
   agent followed or overrode the DPM argmin.
3. Do not reinterpret the decision using information unavailable to the agent.
4. Submit workflow jobs with Slurm account `oddite` and partition `slurm`.
5. Measure deployment runtime as stage-in plus workflow execution.
6. Measure validation separately.
7. Exclude validation, plotting, report generation, and cleanup from deployment
   runtime.
8. Validate outputs against the BeeGFS baseline outputs.
9. Clean only job-owned scratch/tmpfs paths created by this run.
10. Record fixed environment metadata, commands, timing logs, validation result,
   cleanup result, and any executor-side failures.

## Output Metrics

```yaml
selected_node_count: <int>
selected_storage_tier: <beegfs|scratch|tmpfs>
dpm_argmin_node_count: <int>
dpm_argmin_storage_tier: <beegfs|scratch|tmpfs>
agent_followed_dpm_argmin: <true|false>
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
