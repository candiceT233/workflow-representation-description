# Montage 30GB Three-Trial Agentic Deployment Evaluation

Run tag: `montage30_dpmablation_3trial_20260619T211704Z`

Deployment runtime is `stage + exec`. Validation is measured and reported separately, but is not included in workflow runtime.

## Setup Inputs

- `baseline`: BeeGFS-only run with no deployment or I/O adjustment; evaluated at 30, 60, and 120 nodes.
- `code_dpm`: workflow repository/scripts plus site config and Widget DPM scores; no WDD-suite YAML files.
- `dpm_only`: Widget DPM scores plus minimal workflow/storage/node labels; no workflow repository/scripts and no WDD-suite YAML files.

## Completion

- Timing logs found: 63 / expected 63
- Successful timing logs: 63 / 63

## Selected Deployment Per Trial

| Trial | Setup | Nodes | Storage | Stage s | Exec s | Runtime s | Validation s |
|---:|---|---:|---|---:|---:|---:|---:|
| 1 | baseline_best_beegfs | 60 | beegfs | 0 | 12 | 12 | 7 |
| 1 | code_dpm | 120 | tmpfs | 2 | 1 | 3 | 12 |
| 1 | dpm_only | 120 | scratch | 2 | 1 | 3 | 8 |
| 2 | baseline_best_beegfs | 60 | beegfs | 0 | 43 | 43 | 8 |
| 2 | code_dpm | 60 | tmpfs | 2 | 1 | 3 | 6 |
| 2 | dpm_only | 120 | tmpfs | 5 | 1 | 6 | 7 |
| 3 | baseline_best_beegfs | 120 | beegfs | 0 | 44 | 44 | 17 |
| 3 | code_dpm | 120 | tmpfs | 3 | 1 | 4 | 7 |
| 3 | dpm_only | 60 | tmpfs | 3 | 2 | 5 | 6 |

## Mean Runtime Of Selected Deployments

| Setup | Mean runtime s | Std s | Mean speedup vs best BeeGFS baseline |
|---|---:|---:|---:|
| baseline_best_beegfs | 33.00 | 18.19 | 1.00x |
| code_dpm | 3.33 | 0.58 | 9.90x |
| dpm_only | 4.67 | 1.53 | 7.07x |

## Decision Stability

| Setup | Stability score | Selected deployments |
|---|---:|---|
| baseline_best_beegfs | 67% | 60/beegfs x2; 120/beegfs x1 |
| code_dpm | 67% | 120/tmpfs x2; 60/tmpfs x1 |
| dpm_only | 33% | 120/scratch x1; 120/tmpfs x1; 60/tmpfs x1 |

Baseline node-count runtime options: 30 nodes: 111.33s mean; 60 nodes: 317.67s mean; 120 nodes: 81.00s mean.

## Full Aggregate

| Mode | Storage | Nodes | Trials | Mean runtime s | Std s | Mean stage s | Mean exec s | Mean validation s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | beegfs | 30 | 3 | 111.33 | 73.66 | 0.00 | 111.33 | 35.00 |
| baseline | beegfs | 60 | 3 | 317.67 | 502.82 | 0.00 | 317.67 | 188.33 |
| baseline | beegfs | 120 | 3 | 81.00 | 63.22 | 0.00 | 81.00 | 11.67 |
| code_dpm | beegfs | 30 | 3 | 155.00 | 222.57 | 0.00 | 155.00 | 29.33 |
| code_dpm | scratch | 30 | 3 | 15.00 | 8.72 | 12.00 | 3.00 | 22.33 |
| code_dpm | tmpfs | 30 | 3 | 10.33 | 1.53 | 7.33 | 3.00 | 14.33 |
| code_dpm | beegfs | 60 | 3 | 26.33 | 28.31 | 0.00 | 26.33 | 18.33 |
| code_dpm | scratch | 60 | 3 | 4.67 | 0.58 | 2.67 | 2.00 | 11.67 |
| code_dpm | tmpfs | 60 | 3 | 3.67 | 0.58 | 2.00 | 1.67 | 7.00 |
| code_dpm | beegfs | 120 | 3 | 39.67 | 17.93 | 0.00 | 39.67 | 28.00 |
| code_dpm | scratch | 120 | 3 | 17.33 | 19.73 | 16.33 | 1.00 | 25.33 |
| code_dpm | tmpfs | 120 | 3 | 16.00 | 21.66 | 15.00 | 1.00 | 22.00 |
| dpm_only | beegfs | 30 | 3 | 154.00 | 249.42 | 0.00 | 154.00 | 66.00 |
| dpm_only | scratch | 30 | 3 | 17.67 | 15.89 | 14.67 | 3.00 | 26.00 |
| dpm_only | tmpfs | 30 | 3 | 13.67 | 8.96 | 10.67 | 3.00 | 21.67 |
| dpm_only | beegfs | 60 | 3 | 225.00 | 350.93 | 0.00 | 225.00 | 81.67 |
| dpm_only | scratch | 60 | 3 | 22.67 | 15.95 | 20.67 | 2.00 | 18.67 |
| dpm_only | tmpfs | 60 | 3 | 10.33 | 9.24 | 8.33 | 2.00 | 16.67 |
| dpm_only | beegfs | 120 | 3 | 215.67 | 350.18 | 0.00 | 215.67 | 103.00 |
| dpm_only | scratch | 120 | 3 | 31.00 | 25.24 | 30.00 | 1.00 | 26.00 |
| dpm_only | tmpfs | 120 | 3 | 12.33 | 11.85 | 11.33 | 1.00 | 7.67 |

## Plots

- `selected_runtime_choice_stability.svg`
- `runtime_by_scale_storage.svg`

## Raw Files

- `raw_timings.csv`
- `aggregate_by_setup_scale_storage.csv`
- `selected_deployments_by_trial.csv`
- `choice_stability.csv`
