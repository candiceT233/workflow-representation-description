# WIDGET Architecture v7 — Change Summary

**Scope:** `wdd_design-v7.md`, `WIDGET_conventions.md`, and all six agent templates  
**Previous version:** v6 / schema versions `wrd-6.0`, `edd-1.0`, `ddd-6.0`, `gd-6.0`, `hrd-6.0`, `iodd-6.0`  
**Current version:** v7 / schema versions `wrd-7.0`, `edd-2.0`, `ddd-7.0`, `gd-7.0`, `hrd-7.0`, `iodd-7.0`

---

## Summary of Changes

### New: `WIDGET_conventions.md` (shared reference)

A new shared reference document extracts and consolidates content that was repeated verbatim across all six templates in v6:

- **ID namespace table** — all prefix conventions in one place. Templates now reference this table instead of repeating it.
- **Field status code definitions** — one table covering all six documents' status codes.
- **Compact vs. full document format** — explicit guidance that `_status`, `_prompt`, `_reasoning`, and `_extract` annotations are stripped from inter-agent transfers. Completed documents passed between agents carry only `key: value` pairs plus header IDs. Estimated token reduction: ~60% for consumed documents.
- **Cross-run comparison model** — the IODD comparison table.
- **Seven key design principles** — consolidated from scattered PURPOSE blocks.

**Token efficiency impact:** Eliminates approximately 2,500 tokens of repeated boilerplate across the six templates.

---

## WDD (`wrd-6.0` → `wrd-7.0`)

### New field: `io_access_type` on tasks

Added to every task entry alongside `io_dominance`. Values:
`posix_independent | mpi_io_collective | mpi_io_independent | hdf5_parallel | netcdf4_parallel | python_serial | unknown`

**Why:** The v6 WDD captured that a task was `io_bound` but not *how* it performed I/O. This omission left DDD agents unable to configure MPI-IO aggregators, and left IODD agents unable to detect MPI-IO bottlenecks. `io_access_type` directly informs:
- DDD `io_aggregator_config` (new in v7) for collective I/O tasks
- IODD `mpi_io_observations` (new in v7) for aggregator match checking
- WDD `io_behavioral_hints.potential_concern = mpi_io_pattern_risk` (new concern type)

**Extraction guidance added:** Step 3 of the Generation Procedure now describes how to infer `io_access_type` from import statements, MPI API calls, and HDF5 build usage.

### New field: `restart_model` on tasks

Added to every task entry. Values: `idempotent | checkpoint_restart | non_restartable | unknown`

Companion field: `restart_checkpoint_dataset` (data_id of the checkpoint file read at startup for `checkpoint_restart` tasks).

**Why:** The v6 DDD had `checkpoint_interval` and `global_replication_factor` but no way to know *how* a workflow recovers from failure. `restart_model` enables:
- DDD `restart_strategy` section (new in v7) to derive the appropriate recovery plan
- Identification of which checkpoints are operationally required for restart vs. scientifically valuable outputs

**Extraction guidance added:** Step 4 of the Generation Procedure describes how to infer `restart_model` from checkpoint-read logic at task startup, `--resume` / `--restart` CLI flags, and "skip if output exists" guards.

### New: `conditional_inclusions` on execution profiles

Added to each execution profile entry. One entry per task that is conditionally included based on an EDD parameter value. Previously the DDD generator had no mechanism to know which tasks in `required_task_set` were gated by EDD parameters (Section 11.8 corner case from v6 became a first-class field).

### New: `mpi_io_pattern_risk` in `io_behavioral_hints.potential_concern`

Added as a new concern type alongside existing vocabulary. Triggered when: a task uses `mpi_io_independent` but file access patterns suggest collective would improve performance (many ranks writing to the same file, or strided access patterns detectable in the code structure).

### Removed: Redundant ID namespace block

All six templates previously contained a full ID namespace block. Templates now reference `WIDGET_conventions.md` instead.

---

## EDD (`edd-1.0` → `edd-2.0`)

### New: Section E — Software Environment

Adds four sub-sections to the EDD:

**E.1 `required_modules`** — HPC module list (Lmod/Tcl). `required_instance` field populated by scientist for each target system.
- Prompt: "What modules must be loaded on {target_system} before this workflow can run?"
- Used by DDD `job_script.environment_setup.module_load_commands`.

**E.2 `container`** — container image path, runtime (singularity/apptainer/shifter/docker), and bind mount paths.
- `required_instance`. null if not containerized.
- Used by DDD `job_script.environment_setup.container_command`.

**E.3 `critical_libraries`** — configuration of libraries with direct I/O performance impact:
- `hdf5.build_type`: `parallel | serial | unknown`. Determines whether PHDF5 is available for tasks with `io_access_type = hdf5_parallel`.
- `darshan.preloaded` and `darshan.library_path`: determines whether IODD empirical profiling is available without extra setup, and supplies the `LD_PRELOAD` path for explicit instrumentation.

**E.4 `environment_variables`** — structural environment variables not captured in `experiment_parameters` (e.g., `ROMIO_HINTS`, `PYTHONPATH` overrides).

**Why:** In v6 the software environment was entirely absent from the document architecture. Agents generating job scripts had no authoritative source for module loads, container commands, or library paths. This caused agents to either guess or require additional operator clarification at job submission time — exactly the kind of friction the architecture is designed to eliminate.

---

## HRD (`hrd-6.0` → `hrd-7.0`)

### Fixed: Schema version bug

v6 HRD template contained `schema_version: "hrd-5.0"` — a copy-paste error from the pre-v6 template. Corrected to `hrd-7.0`.

### New: Section 5 — Job Scheduler

The most significant structural addition to the HRD. Captures the scheduling layer that mediates access to hardware:

**`scheduler_type`** — `slurm | pbs | lsf | cobalt | flux | other`

**`partitions` list** — one entry per queue/partition, with:
- `partition_id`, `description`, `max_nodes`, `max_walltime_hours`
- `max_jobs_per_user`, `node_classes_available` (links to compute_ids)
- `charging_model`: `node_hours | core_hours | gpu_hours`
- `exclusive_node_access`: `always | optional | never`

**Supporting fields:**
- `account_required` + `account_flag` (for `#SBATCH --account=`)
- `job_array_support`, `dependency_support`
- `typical_queue_wait_minutes` (per partition, for capacity planning)

**Why:** The v6 DDD prescribed parallelism and storage but produced no job script. Agents using Jarvis-MCP had to infer scheduler directives from context. The HRD scheduler section is the authoritative source the DDD job_script section reads from.

### New: `node_local_storage` on compute nodes

Added to each `compute_topology` entry. Captures: `type` (nvme_ssd/hdd/ramdisk), `capacity_gb`, `peak_read_bandwidth_gbs`, `peak_write_bandwidth_gbs`, and notes (e.g., "Cleared at job end. Accessible at /tmp").

**Why:** v6 HRD captured node-local storage as a tier in `storage_hierarchy` but didn't associate it with specific node classes. DDD agents couldn't determine which compute nodes had node-local storage available without inferring it from tier names.

### New: `stripe_tuning` on storage tiers

Added to each `storage_hierarchy` entry. Fields: `default_stripe_count`, `recommended_stripe_count_large_writes`, `recommended_stripe_size_mb`, `notes`.

**Why:** The v6 HRD included a free-text `notes` field that sometimes mentioned Lustre stripe tuning, but this was not machine-readable. DDD agents now derive concrete `lfs setstripe` commands from structured stripe tuning data.

### New: `staging_directives` on storage tiers

Added to each `storage_hierarchy` entry. Fields: `stage_in_directive` (template string), `stage_out_directive`, `directive_syntax` (`DataWarp | BurstBuffer | BB_JOB_DIRECTIVE | none`), `notes`.

**Why:** Burst buffer systems (Cray DataWarp, SLURM BB) require job-level staging directives in the job script header. Without structured directive templates in the HRD, agents had no way to emit correct staging syntax for a given system.

### New: `mount_point` on storage tiers

Added to each `storage_hierarchy` entry. E.g., `/pscratch`, `/tmp`, `/bb`.

**Why:** IODD empirical mode maps Darshan file paths to tier_ids by matching file path prefixes against mount points. This field makes that mapping explicit rather than requiring hardcoded heuristics.

---

## DDD (`ddd-6.0` → `ddd-7.0`)

### New: `io_aggregator_config` on per-task parallelism entries

Added to each `per_task_parallelism` entry. Required when `WDD task.io_access_type = mpi_io_collective` or `hdf5_parallel`. Fields:
- `aggregator_count`: derived from HRD `stripe_tuning.recommended_stripe_count_large_writes`
- `cb_buffer_size_mb`: collective buffer size per aggregator (typically 16–64 MB)
- `romio_hints`: ROMIO hint string (e.g., `cb_nodes=4:cb_buffer_size=64m`)

**Why:** MPI-IO collective operations require correct ROMIO aggregator configuration to achieve good performance on parallel filesystems. Without this, collective I/O tasks silently fall back to suboptimal defaults. The `romio_hints` string is picked up by `job_script.environment_setup.environment_variable_exports`.

### New: `stripe_directive` on storage tier assignments

Added to each `storage_tier_assignments` entry. Derives the concrete `lfs setstripe` command for large sequential writers (checkpoint files and large intermediates) from HRD `stripe_tuning` data.

### New: Section 4 — Data Staging Plan

Three sub-sections:

**`stage_in_steps`** — one entry per dataset with `caching_policy = prefetch`. Specifies: `source_tier`, `dest_tier`, `source_path_template`, `dest_path_template`, `command_or_directive`, `estimated_staging_time_minutes`.

**`stage_out_steps`** — one entry per checkpoint/output dataset on a volatile tier that must be copied to persistent storage after job completion.

**`stripe_setup_commands`** — `lfs setstripe` commands to run before writing large files, consolidated from `stripe_directive` fields.

The staging plan is the operational bridge between the DDD's tier assignment decisions and the actual job script. It eliminates the gap between "checkpoints should be on PFS" and "here is how to get them there."

### New: Section 7 — `restart_strategy`

Added to `replication_and_caching`. Fields:
- `model`: `full_restart | stage_restart | task_restart | checkpoint_restart`
  - Derived from WDD `restart_model` values; uses the most conservative model among non-idempotent tasks.
- `restart_checkpoint_datasets`: data_ids of checkpoints used for recovery
- `operator_action_required`: boolean — can restart be automated via `--dependency=afternotok`?

### New: Section 8 — Job Script

The most consequential addition to the DDD for practical usability. Generates concrete, runnable scheduler directives:

**`scheduler_type`** — copied from HRD.

**`target_partition`** — selected from HRD `scheduler.partitions` based on node requirements, estimated walltime, and GD goals.

**`account`** — required when HRD `scheduler.account_required = true`. Elicited from operator.

**`estimated_walltime_hours`** — sum of per-task wall time estimates + staging time + 10–20% safety margin.

**`exclusive_nodes`** — recommended for io_bound workloads to prevent shared-tier contention.

**`directives` list** — complete `#SBATCH` / `#PBS` / `#BSUB` lines, sufficient to produce a runnable job submission.

**`environment_setup`** — preamble commands derived from EDD environment section:
- `module_load_commands` from EDD `required_modules`
- `container_command` from EDD `container.runtime`
- `ld_preload` from EDD `darshan.library_path` (if not auto-loaded)
- `environment_variable_exports` from EDD `environment_variables` + ROMIO hints
- `stripe_setup_commands` from `staging_plan`

**New: `scheduler_feasibility_checks`** in `validation_summary` — verifies `total_nodes_required` and `estimated_walltime_hours` are within the selected partition's limits.

### Condensed reasoning protocols

The verbose `_agent_reasoning_protocol` blocks from v6 (which ran to 20–30 lines per section) have been replaced with concise bullet-point KEY REASONING RULES comments (3–6 lines per section). The detailed pedagogical content is available in `WIDGET_conventions.md` and a companion `DDD_reasoning_guide.md` (to be authored separately). Estimated token reduction: ~1,500 tokens from the DDD template alone.

---

## GD (`gd-6.0` → `gd-7.0`)

### Simplified conflict resolution trigger

**v6 behavior:** `resolution_notes` was prompted whenever any two soft goals could theoretically conflict (triggered on throughput + cost, latency + cost, or matching priority ranks). This fired on nearly every real deployment since almost every operator has both throughput and cost goals.

**v7 behavior:** `resolution_notes` is ONLY required when two or more soft goals share the **same priority rank**. When goals have distinct priority ranks, the default resolution policy applies automatically: satisfy hard goals first, then soft goals in ascending priority order. No operator input needed for the common case.

**Added:** Explicit default conflict resolution policy documented in the template comment, so agents know how to proceed without prompting.

---

## IODD (`iodd-6.0` → `iodd-7.0`)

### Removed: `run_id` field

`run_id` was documented in v6 as "same as EDD metadata.instance_id when available" but persisted as a separate field with legacy fallback logic. In v7, `edd_instance_id` is the canonical run identity. Legacy runs without a formal EDD use the Slurm job ID directly as `edd_instance_id`. The `run_id` field is removed.

### Standardized: `per_task_io_profile` granularity

v6 allowed "one entry per iteration, or one aggregate entry with per-iteration statistics." This ambiguity caused different IODD records for the same workflow to have incompatible structures, breaking automated cross-run comparison.

v7 standardizes on: **one aggregate entry per task** (summed across all instances). Per-instance statistics are available as an optional `per_instance_stats` nested list for diagnostic deep-dives when contention or variability is suspected. This ensures IODD records are always structurally comparable.

### New: `mpi_io_observations` per task

Added to each `per_task_io_profile` entry. Required when `WDD task.io_access_type = mpi_io_collective | mpi_io_independent | hdf5_parallel`. Fields:
- `collective_ops`, `independent_ops` (from Darshan MPI-IO module)
- `aggregator_count_used` (actual ROMIO aggregators)
- `aggregator_count_planned` (from DDD `io_aggregator_config`)
- `match_ddd_aggregator`: boolean — flag for aggregator misconfiguration

### New: `mpi_io_aggregator_mismatch` bottleneck type

Added to `diagnosis_summary.bottleneck_summary.bottleneck_type` allowed values and to `anomalies.anomaly_type`.

### New: `tune_mpi_io_aggregators` and `adjust_stripe_count` optimization types

Added to `optimization_opportunities.opportunity_type` allowed values.

---

## Summary of Schema Version Changes

| Document | v6 schema | v7 schema | Change type |
|---|---|---|---|
| WDD | `wrd-6.0` | `wrd-7.0` | New fields: `io_access_type`, `restart_model`, `conditional_inclusions` |
| EDD | `edd-1.0` | `edd-2.0` | New section: Software Environment (E.1–E.4) |
| DDD | `ddd-6.0` | `ddd-7.0` | New: `io_aggregator_config`, `stripe_directive`, staging plan, restart strategy, job script, scheduler feasibility checks |
| GD  | `gd-6.0`  | `gd-7.0`  | Simplified conflict resolution trigger |
| HRD | `hrd-6.0` | `hrd-7.0` | Bug fix, new sections: scheduler, node_local_storage; new fields: stripe_tuning, staging_directives, mount_point |
| IODD | `iodd-6.0` | `iodd-7.0` | Removed run_id; standardized granularity; new MPI-IO fields |

---

## Token Efficiency Impact Summary

| Change | Estimated token reduction |
|---|---|
| Shared `WIDGET_conventions.md` replaces repeated ID namespace + status code blocks | ~2,500 tokens across 6 templates |
| Compact inter-agent document format (strip annotations from consumed docs) | ~60% reduction per completed document passed between agents |
| Condensed DDD reasoning protocols | ~1,500 tokens from DDD template |
| GD conflict resolution: fewer operator prompts | Eliminates 1–2 round trips per deployment |
| `run_id` removal from IODD | Minor |
| **Total estimated reduction (authoring templates)** | **~4,000–5,000 tokens** |
| **Total estimated reduction (inter-agent transfers of completed docs)** | **~60%** |