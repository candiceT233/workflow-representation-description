# Baseline Execution Spec v3: Montage 30GB

This is not an agentic prompt. Baseline is a deterministic reference procedure.

## Objective

Run BeeGFS-only baseline at every candidate node count and validate outputs.
Baseline produces the fixed reference used by all agentic setups.

## Workflow Context

- Workflow: Montage mProjectPP reprojection
- Scale: 15,000 FITS input tiles, approximately 30GB
- Candidate node counts: 30, 60, 120
- Baseline storage: beegfs only
- Baseline policy: BeeGFS-only at 30, 60, and 120 nodes.

## Procedure

1. Use BeeGFS/shared filesystem as active workflow storage.
2. Do not stage inputs to scratch or tmpfs.
3. Run at every candidate node count.
4. Validate outputs.
5. Report fixed-node runtimes and per-trial best BeeGFS runtime.
6. Measure validation separately from workflow runtime.
7. Save timing logs, validation output, cleanup status, and environment
   metadata.
