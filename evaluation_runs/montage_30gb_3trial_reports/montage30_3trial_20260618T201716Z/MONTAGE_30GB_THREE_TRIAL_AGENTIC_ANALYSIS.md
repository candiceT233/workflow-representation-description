# Montage 30GB Three-Trial Agentic Deployment Evaluation

Run tag: `montage30_3trial_20260618T201716Z`

Deployment runtime is `stage + exec`. Validation is measured and reported separately, but is not included in workflow runtime.

## Setup Inputs

- `baseline`: BeeGFS-only run with no deployment or I/O adjustment; evaluated at 30, 60, and 120 nodes.
- `code_only`: fresh agentic choice using repository/script exploration only; candidates are 30/60/120 nodes and BeeGFS/scratch/tmpfs storage.
- `wdd_only`: WDD/IODD pair only. This is the earlier two-file ablation, not the full WDD suite.
- `wdd_dpm`: WDD/IODD pair plus Widget DPM guidance. This is the earlier two-file+DPM ablation.

## Completion

- Timing logs found: 90 / expected 90
- Successful timing logs: 90 / 90

## Selected Deployment Per Trial

| Trial | Setup | Nodes | Storage | Stage s | Exec s | Runtime s | Validation s |
|---:|---|---:|---|---:|---:|---:|---:|
| 1 | baseline_best_beegfs | 30 | beegfs | 0 | 10 | 10 | 6 |
| 1 | code_only | 120 | tmpfs | 2 | 1 | 3 | 3 |
| 1 | wdd_dpm | 120 | tmpfs | 2 | 1 | 3 | 3 |
| 1 | wdd_only | 120 | tmpfs | 2 | 1 | 3 | 3 |
| 2 | baseline_best_beegfs | 60 | beegfs | 0 | 22 | 22 | 12 |
| 2 | code_only | 120 | tmpfs | 1 | 1 | 2 | 3 |
| 2 | wdd_dpm | 120 | tmpfs | 2 | 1 | 3 | 3 |
| 2 | wdd_only | 120 | tmpfs | 2 | 1 | 3 | 3 |
| 3 | baseline_best_beegfs | 30 | beegfs | 0 | 14 | 14 | 7 |
| 3 | code_only | 120 | scratch | 2 | 1 | 3 | 6 |
| 3 | wdd_dpm | 120 | tmpfs | 2 | 1 | 3 | 3 |
| 3 | wdd_only | 120 | scratch | 2 | 1 | 3 | 4 |

## Mean Runtime Of Selected Deployments

| Setup | Mean runtime s | Std s | Mean speedup vs best BeeGFS baseline |
|---|---:|---:|---:|
| baseline_best_beegfs | 15.33 | 6.11 | 1.00x |
| code_only | 2.67 | 0.58 | 5.75x |
| wdd_only | 3.00 | 0.00 | 5.11x |
| wdd_dpm | 3.00 | 0.00 | 5.11x |

## Decision Stability

| Setup | Stability score | Selected deployments |
|---|---:|---|
| baseline_best_beegfs | 67% | 30/beegfs x2; 60/beegfs x1 |
| code_only | 67% | 120/tmpfs x2; 120/scratch x1 |
| wdd_only | 67% | 120/tmpfs x2; 120/scratch x1 |
| wdd_dpm | 100% | 120/tmpfs x3 |

Baseline node-count runtime options: 30 nodes: 24.00s mean; 60 nodes: 19.00s mean; 120 nodes: 49.00s mean.

## Full Aggregate

| Mode | Storage | Nodes | Trials | Mean runtime s | Std s | Mean stage s | Mean exec s | Mean validation s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | beegfs | 30 | 3 | 24.00 | 20.88 | 0.00 | 24.00 | 6.00 |
| baseline | beegfs | 60 | 3 | 19.00 | 2.65 | 0.00 | 19.00 | 10.67 |
| baseline | beegfs | 120 | 3 | 49.00 | 32.70 | 0.00 | 49.00 | 32.00 |
| code_only | beegfs | 30 | 3 | 198.33 | 165.30 | 0.00 | 198.33 | 21.67 |
| code_only | scratch | 30 | 3 | 9.00 | 2.00 | 6.67 | 2.33 | 11.33 |
| code_only | tmpfs | 30 | 3 | 6.67 | 0.58 | 4.00 | 2.67 | 11.00 |
| code_only | beegfs | 60 | 3 | 70.33 | 75.75 | 0.00 | 70.33 | 20.67 |
| code_only | scratch | 60 | 3 | 5.67 | 2.08 | 4.00 | 1.67 | 5.67 |
| code_only | tmpfs | 60 | 3 | 4.00 | 1.00 | 2.33 | 1.67 | 5.67 |
| code_only | beegfs | 120 | 3 | 12.67 | 2.52 | 0.00 | 12.67 | 7.33 |
| code_only | scratch | 120 | 3 | 3.67 | 1.15 | 2.67 | 1.00 | 4.00 |
| code_only | tmpfs | 120 | 3 | 2.67 | 0.58 | 1.67 | 1.00 | 3.00 |
| wdd_only | beegfs | 30 | 3 | 137.33 | 133.15 | 0.00 | 137.33 | 44.33 |
| wdd_only | scratch | 30 | 3 | 8.00 | 1.00 | 5.33 | 2.67 | 11.00 |
| wdd_only | tmpfs | 30 | 3 | 6.67 | 0.58 | 4.00 | 2.67 | 11.00 |
| wdd_only | beegfs | 60 | 3 | 11.67 | 4.62 | 0.00 | 11.67 | 13.67 |
| wdd_only | scratch | 60 | 3 | 5.00 | 0.00 | 3.00 | 2.00 | 5.33 |
| wdd_only | tmpfs | 60 | 3 | 9.33 | 7.51 | 7.33 | 2.00 | 11.00 |
| wdd_only | beegfs | 120 | 3 | 34.33 | 40.41 | 0.00 | 34.33 | 15.33 |
| wdd_only | scratch | 120 | 3 | 4.00 | 1.00 | 3.00 | 1.00 | 3.33 |
| wdd_only | tmpfs | 120 | 3 | 3.33 | 0.58 | 2.33 | 1.00 | 3.00 |
| wdd_dpm | beegfs | 30 | 3 | 12.00 | 3.61 | 0.00 | 12.00 | 20.00 |
| wdd_dpm | scratch | 30 | 3 | 7.33 | 0.58 | 4.67 | 2.67 | 11.00 |
| wdd_dpm | tmpfs | 30 | 3 | 8.00 | 1.00 | 5.00 | 3.00 | 11.33 |
| wdd_dpm | beegfs | 60 | 3 | 16.67 | 1.15 | 0.00 | 16.67 | 17.00 |
| wdd_dpm | scratch | 60 | 3 | 5.00 | 0.00 | 3.00 | 2.00 | 6.00 |
| wdd_dpm | tmpfs | 60 | 3 | 3.67 | 0.58 | 2.00 | 1.67 | 5.33 |
| wdd_dpm | beegfs | 120 | 3 | 58.00 | 38.57 | 0.00 | 58.00 | 14.33 |
| wdd_dpm | scratch | 120 | 3 | 4.33 | 0.58 | 3.33 | 1.00 | 3.33 |
| wdd_dpm | tmpfs | 120 | 3 | 3.00 | 0.00 | 2.00 | 1.00 | 3.00 |

## Plots

- `selected_runtime_choice_stability.svg`
- `runtime_by_scale_storage.svg`

## Raw Files

- `raw_timings.csv`
- `aggregate_by_setup_scale_storage.csv`
- `selected_deployments_by_trial.csv`
- `choice_stability.csv`
