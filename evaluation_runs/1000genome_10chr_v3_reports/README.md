# 1000Genome 10-Chromosome Controlled Evaluation

- Run tag: `1kg10chr_v3_20260626T220420Z`
- Runtime excludes validation, report generation, plotting, and cleanup.
- Baseline runs BeeGFS at 2, 5, and 10 nodes; the baseline bar uses the fastest successful BeeGFS node count within each trial.
- Non-baseline bars use the exact node/storage deployment selected by each fresh decision agent.

## Agentic Deployment Choices

| setup | selected deployment | input regime |
|---|---:|---|
| `code_only` | 10 nodes / tmpfs | workflow code + runner snapshot + site config |
| `code_dpm` | 5 nodes / scratch | code inputs plus static DataLife-derived Widget DPM table |
| `dpm_only` | 5 nodes / scratch | static DataLife-derived Widget DPM table only |
| `wdd_pair_only` | 10 nodes / scratch | code inputs plus WDD.yml/IODD.yml pair |
| `wdd_pair_dpm` | 5 nodes / scratch | code inputs plus WDD.yml/IODD.yml pair plus static DPM table |

## Runtime Summary

| setup | n | mean s | std s | choice stability | choices |
|---|---:|---:|---:|---:|---|
| `baseline` | 3 | 561.33 | 162.45 | 0.67 | 10/beegfs x2; 5/beegfs x1 |
| `code_only` | 3 | 216.00 | 3.00 | 1.00 | 10/tmpfs x3 |
| `code_dpm` | 3 | 288.67 | 3.21 | 1.00 | 5/scratch x3 |
| `dpm_only` | 3 | 292.67 | 5.03 | 1.00 | 5/scratch x3 |
| `wdd_pair_only` | 3 | 216.33 | 3.06 | 1.00 | 10/scratch x3 |
| `wdd_pair_dpm` | 3 | 286.67 | 6.43 | 1.00 | 5/scratch x3 |

## BeeGFS Baseline Node-Count Reference

| nodes | mean s |
|---:|---:|
| 2 | 1720.67 |
| 5 | 734.00 |
| 10 | 582.33 |

## Artifacts

- `all_runs.csv`: every successful timing log discovered.
- `selected_runs.csv`: selected comparison rows.
- `summary_by_setup.csv`: means, standard deviations, and stability labels.
- `1000genome10_runtime_summary.svg`: runtime summary plot.
