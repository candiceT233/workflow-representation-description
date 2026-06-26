# Bundle Builder Spec v3: Montage 30GB / wdd_pair_only

This file is for the experiment orchestrator, not for the decision agent.

## Objective

Create the clean input bundle consumed by the matching v3 prompt and
agent-facing manifest.

## Destination

```text
agent_contexts/montage_30gb/wdd_pair_only/allowed/
```

## Source Paths

- workflow_repository: `hpc_workflows/repos/Montage`
- run_harness: `workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/`
- wdd_documents_if_allowed: `workflow_representation_experiments/Montage/datalife_code/docs/`
- dpm_outputs_if_allowed: `workflow_representation_experiments/Montage/agentic_runs_3trial_30gb/`

## Include Policy

Allowed inputs for this setup:
- Files in this setup's clean input bundle.
- Workflow repository files copied into the clean input bundle.
- Run scripts copied into the clean input bundle.
- Cluster site configuration copied into the clean input bundle.
- Candidate node counts and storage tiers listed in this prompt.
- WDD.yml copied into the clean input bundle.
- IODD.yml copied into the clean input bundle.

Disallowed inputs for this setup:
- HRD.yml, GD.yml, DDD.yml, and EDD_*.yml.
- Widget DPM outputs.
- Prior evaluation reports.
- Chat-derived conclusions from other setups.

## Required Builder Actions

1. Create a fresh destination directory for each trial.
2. Copy only files allowed by this setup.
3. Exclude prior reports, chat transcripts, generated analysis summaries, and
   outputs from other setups.
4. Exclude original source path metadata from the agent-facing manifest.
5. Write a file inventory with path, size, and sha256 for each included file.
6. Write a bundle-level sha256 or Merkle-style digest over the inventory.
7. Make allowed input files read-only for the decision agent where practical.
8. Save the builder log outside the agent-facing bundle.

