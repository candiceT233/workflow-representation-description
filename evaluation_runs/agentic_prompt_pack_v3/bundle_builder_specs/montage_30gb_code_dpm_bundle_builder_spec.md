# Bundle Builder Spec v3: Montage 30GB / code_dpm

This file is for the experiment orchestrator, not for the decision agent.

## Objective

Create the clean input bundle consumed by the matching v3 prompt and
agent-facing manifest.

## Destination

```text
agent_contexts/montage_30gb/code_dpm/allowed/
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
- Statically computed Widget DPM candidate-plan score table copied into the clean input bundle. The table must score every node-count/storage-tier candidate in this prompt, identify the deterministic lowest-DPM plan, and remain unchanged across all trials for this workflow/scale/setup.

Disallowed inputs for this setup:
- WDD-suite YAML files.
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


## DPM Score Table Requirements

For this DPM-enabled setup, the clean bundle must include a statically computed
DPM candidate-plan score table generated before the first decision agent starts.
Reuse the same static DPM table unchanged across all trials for the same
workflow/scale/setup.

The DPM artifact must be derived from the existing DataLife profile for the
same workflow/scale. The decision-agent bundle should include provenance
metadata identifying the DataLife profile path/id and checksum when available,
but should not include raw DataLife traces unless the setup explicitly allows
them.

The table must:

1. Score every candidate deployment plan:
   - node counts: `30, 60, 120`
   - storage tiers: `beegfs, scratch, tmpfs`
2. Include one row per node-count/storage-tier plan, or an equivalent explicit
   representation that can be losslessly converted into that table.
3. Include the deterministic lowest-DPM plan.
4. Preserve the raw Widget DPM output and a normalized agent-facing table.
5. Include DPM provenance metadata: source profiler type `DataLife`,
   DataLife profile path/id, DataLife profile checksum if available, Widget
   config/workflow identifier, and candidate node/storage set.
6. Include checksums for both raw and normalized DPM files.
7. Exclude measured runtime results, previous agent choices, report summaries,
   and any chat-derived conclusions.

