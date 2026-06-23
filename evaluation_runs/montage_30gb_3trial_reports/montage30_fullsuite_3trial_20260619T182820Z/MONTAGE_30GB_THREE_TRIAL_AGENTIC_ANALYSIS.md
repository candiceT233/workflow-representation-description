# Montage 30GB Three-Trial Agentic Deployment Evaluation

Run tag: `montage30_fullsuite_3trial_20260619T182820Z`

Deployment runtime is `stage + exec`. Validation is measured and reported separately, but is not included in workflow runtime.

## Setup Inputs

- `baseline`: BeeGFS-only run with no deployment or I/O adjustment; evaluated at 30, 60, and 120 nodes.
- `wdd_full_only`: fresh agentic choice using the full WDD suite: WDD, IODD, HRD, GD, DDD, and relevant EDD files.
- `wdd_full_dpm`: fresh agentic choice using the full WDD suite plus Widget DPM guidance.

## Completion

- Timing logs found: 63 / expected 63
- Successful timing logs: 63 / 63

## Selected Deployment Per Trial

| Trial | Setup | Nodes | Storage | Stage s | Exec s | Runtime s | Validation s |
|---:|---|---:|---|---:|---:|---:|---:|
| 1 | baseline_best_beegfs | 60 | beegfs | 0 | 15 | 15 | 8 |
| 1 | wdd_full_dpm | 120 | scratch | 2 | 1 | 3 | 5 |
| 1 | wdd_full_only | 120 | tmpfs | 2 | 1 | 3 | 3 |
| 2 | baseline_best_beegfs | 30 | beegfs | 0 | 38 | 38 | 12 |
| 2 | wdd_full_dpm | 60 | beegfs | 0 | 32 | 32 | 76 |
| 2 | wdd_full_only | 60 | tmpfs | 16 | 2 | 18 | 35 |
| 3 | baseline_best_beegfs | 120 | beegfs | 0 | 17 | 17 | 13 |
| 3 | wdd_full_dpm | 60 | scratch | 3 | 2 | 5 | 11 |
| 3 | wdd_full_only | 120 | scratch | 3 | 1 | 4 | 8 |

## Mean Runtime Of Selected Deployments

| Setup | Mean runtime s | Std s | Mean speedup vs best BeeGFS baseline |
|---|---:|---:|---:|
| baseline_best_beegfs | 23.33 | 12.74 | 1.00x |
| wdd_full_only | 8.33 | 8.39 | 2.80x |
| wdd_full_dpm | 13.33 | 16.20 | 1.75x |

## Decision Stability

| Setup | Stability score | Selected deployments |
|---|---:|---|
| baseline_best_beegfs | 33% | 60/beegfs x1; 30/beegfs x1; 120/beegfs x1 |
| wdd_full_only | 33% | 120/tmpfs x1; 60/tmpfs x1; 120/scratch x1 |
| wdd_full_dpm | 33% | 120/scratch x1; 60/beegfs x1; 60/scratch x1 |

Baseline node-count runtime options: 30 nodes: 263.67s mean; 60 nodes: 61.00s mean; 120 nodes: 43.33s mean.

## Full Aggregate

| Mode | Storage | Nodes | Trials | Mean runtime s | Std s | Mean stage s | Mean exec s | Mean validation s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | beegfs | 30 | 3 | 263.67 | 393.47 | 0.00 | 263.67 | 30.00 |
| baseline | beegfs | 60 | 3 | 61.00 | 40.29 | 0.00 | 61.00 | 16.33 |
| baseline | beegfs | 120 | 3 | 43.33 | 42.19 | 0.00 | 43.33 | 16.33 |
| wdd_full_only | beegfs | 30 | 3 | 43.67 | 19.22 | 0.00 | 43.67 | 21.00 |
| wdd_full_only | scratch | 30 | 3 | 60.00 | 52.51 | 57.00 | 3.00 | 116.67 |
| wdd_full_only | tmpfs | 30 | 3 | 54.33 | 52.99 | 51.67 | 2.67 | 65.33 |
| wdd_full_only | beegfs | 60 | 3 | 85.33 | 58.02 | 0.00 | 85.33 | 27.00 |
| wdd_full_only | scratch | 60 | 3 | 24.00 | 31.19 | 22.00 | 2.00 | 38.33 |
| wdd_full_only | tmpfs | 60 | 3 | 8.67 | 8.14 | 7.00 | 1.67 | 16.00 |
| wdd_full_only | beegfs | 120 | 3 | 28.67 | 32.33 | 0.00 | 28.67 | 17.67 |
| wdd_full_only | scratch | 120 | 3 | 16.33 | 21.36 | 15.33 | 1.00 | 18.00 |
| wdd_full_only | tmpfs | 120 | 3 | 19.33 | 24.09 | 18.33 | 1.00 | 24.33 |
| wdd_full_dpm | beegfs | 30 | 3 | 47.33 | 37.29 | 0.00 | 47.33 | 107.33 |
| wdd_full_dpm | scratch | 30 | 3 | 47.67 | 41.62 | 44.67 | 3.00 | 60.00 |
| wdd_full_dpm | tmpfs | 30 | 3 | 23.67 | 17.01 | 20.67 | 3.00 | 57.33 |
| wdd_full_dpm | beegfs | 60 | 3 | 79.33 | 97.08 | 0.00 | 79.33 | 67.67 |
| wdd_full_dpm | scratch | 60 | 3 | 21.67 | 28.87 | 19.67 | 2.00 | 33.33 |
| wdd_full_dpm | tmpfs | 60 | 3 | 20.00 | 25.98 | 18.00 | 2.00 | 31.67 |
| wdd_full_dpm | beegfs | 120 | 3 | 81.00 | 56.82 | 0.00 | 81.00 | 77.67 |
| wdd_full_dpm | scratch | 120 | 3 | 33.33 | 26.39 | 32.33 | 1.00 | 36.33 |
| wdd_full_dpm | tmpfs | 120 | 3 | 19.00 | 25.16 | 18.00 | 1.00 | 26.67 |

## Plots

- `selected_runtime_choice_stability.svg`
- `runtime_by_scale_storage.svg`

## Raw Files

- `raw_timings.csv`
- `aggregate_by_setup_scale_storage.csv`
- `selected_deployments_by_trial.csv`
- `choice_stability.csv`
