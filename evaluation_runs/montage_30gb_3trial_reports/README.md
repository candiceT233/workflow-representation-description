# Montage 30GB Three-Trial Evaluation Results

This folder contains the Montage 30GB agentic deployment evaluation results.
The main summary figure is:

- `montage30_runtime_summary.png`

The setup definitions below apply to this specific evaluation snapshot. Future
evaluations may change the setup boundaries, so use the definitions stored next
to each result set rather than assuming labels have a global meaning.

## Common Evaluation Context

- Workflow: Montage `mProjectPP` reprojection.
- Scale: 15,000 FITS input tiles, approximately 30GB.
- Candidate node counts: `30`, `60`, `120`.
- Baseline storage: `beegfs`.
- Agentic storage candidates: `beegfs`, `scratch`, `tmpfs`.
- Runtime plotted: deployment runtime, excluding validation/comparison time.
- Validation/comparison time was retained separately for correctness checks.

## Setup Definitions

| Figure label | Setup name | Inputs available to the agent |
|---|---|---|
| BeeGFS baseline | `baseline` | No agentic optimization. BeeGFS-only execution at candidate node counts. |
| code-only | `code_only` | Workflow repository/scripts, local cluster/site configuration, candidate node counts, candidate storage tiers. |
| code + DPM | `code_dpm` | Same as `code_only`, plus precomputed Widget DPM score outputs. No WDD-suite YAML files. |
| DPM-only | `dpm_only` | Candidate node/storage list, Widget DPM score outputs, and minimal labels needed to interpret the score table. No workflow repository/scripts and no WDD-suite YAML files. |
| WDD pair + DPM | `wdd_pair_dpm` | Workflow repository/scripts, local cluster/site configuration, candidate node/storage list, `WDD.yml`, `IODD.yml`, and Widget DPM score outputs. |
| WDD full + DPM | `wdd_full_dpm` | Workflow repository/scripts, local cluster/site configuration, candidate node/storage list, the full WDD suite, and Widget DPM score outputs. |

## Key Distinction: `code + DPM` vs `WDD pair + DPM`

Both setups include workflow code/scripts and Widget DPM score outputs.

The difference is that `WDD pair + DPM` additionally gives the agent the compact
workflow-representation pair:

- `WDD.yml`
- `IODD.yml`

The `code + DPM` setup does not receive any WDD-suite YAML files.

For this Montage 30GB result, both setups found a fast local-storage strategy,
but `WDD pair + DPM` was more stable:

| Setup | Mean runtime | Selected deployments |
|---|---:|---|
| `code_dpm` | 3.33 s | `120/tmpfs` x2; `60/tmpfs` x1 |
| `wdd_pair_dpm` | 3.00 s | `120/tmpfs` x3 |

## WDD Pair vs Full WDD Suite

`WDD pair + DPM` is an ablation. It uses only:

- `WDD.yml`
- `IODD.yml`

It does not include:

- `HRD.yml`
- `GD.yml`
- `DDD.yml`
- `EDD_*.yml`

The full WDD-suite condition includes all of those files.

## Additional Context

The exact original prompts for the historical runs were not saved as standalone
prompt files. The recoverable setup boundaries and reconstructed prompt context
are documented in:

- `AGENT_CONTEXT_AND_PROMPT_RECONSTRUCTION.md`
