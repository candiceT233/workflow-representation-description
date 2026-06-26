# Neutral Executor Spec v3: Montage 30GB / wdd_pair_only

This file is for the neutral evaluator that runs a decision produced by a fresh
agent. It is not an input to the decision agent.

## Inputs

- Agent decision report for `montage_30gb` / `wdd_pair_only`.
- Baseline outputs for correctness comparison.
- Workflow run harness controlled by the evaluator.

## Execution Rules

1. Read exactly one selected node count and storage tier from the decision
   report.
2. Do not reinterpret the decision using information unavailable to the agent.
3. Submit workflow jobs with Slurm account `oddite` and partition `slurm`.
4. Measure deployment runtime as stage-in plus workflow execution.
5. Measure validation separately.
6. Exclude validation, plotting, report generation, and cleanup from deployment
   runtime.
7. Validate outputs against the BeeGFS baseline outputs.
8. Clean only job-owned scratch/tmpfs paths created by this run.
9. Record fixed environment metadata, commands, timing logs, validation result,
   cleanup result, and any executor-side failures.

## Output Metrics

```yaml
selected_node_count: <int>
selected_storage_tier: <beegfs|scratch|tmpfs>

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
