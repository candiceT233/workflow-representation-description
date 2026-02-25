# WIDGET Architecture v6 — Change Summary

**Scope:** `WRD_Core_Design_v6.md` and all six agent templates (WRD, EDD, DDD, GD, HRD, IODD)  
**Previous version:** v5 / schema versions `wrd-5.0`, `ddd-5.0`, `gd-5.0`, `hrd-5.0`, `iodd-5.0`  
**Current version:** v6 / schema versions `wrd-6.0`, `edd-1.0`, `ddd-6.0`, `gd-6.0`, `hrd-6.0`, `iodd-6.0`

---

## Core Design Change: Six-Document Architecture + Formal Relationship Notation

The architecture expands from five documents to six with the addition of the **Experiment Definition Document (EDD)**. The formal relationships between all documents are now stated as:

```
EDD = f(WDD, input)
[sets of IODD] = execution(WDD, EDD, DDD, HRD, GD)
```

The second relationship is the key conceptual update: the IODD is not a single output of one DDD run on one system. It is a *set of run records*, each produced by one execution of a specific (WDD, EDD, DDD, HRD, GD) combination. Each IODD instance pins all five input documents by ID and version, enabling structured cross-run comparisons:

| Comparison type | What changes | What you learn |
|---|---|---|
| Same WDD + EDD, different DDDs | Deployment strategy | Effect of storage/parallelism choices on I/O |
| Same WDD, different EDDs | Experiment configuration | Effect of input scale on I/O behavior |
| Same all five, repeated runs | Nothing | Run-to-run variability |

---

## New Document: Experiment Definition Document (EDD) — `edd-1.0`

### Purpose

The EDD answers "what specific experiment is this run." It is distinct from:
- **WDD** — what the workflow *is* (stable, changes only with source code)
- **GD** — what the operator *wants* from this run (optimization intent)

The EDD is the bridge between the workflow's static structure and a specific execution instance.

### Two-Phase Design

The EDD is generated in two phases, reflected in a three-status field model:

| Status | Phase | Meaning |
|---|---|---|
| `required_static` | Phase 1 — Code Analysis | Derivable from static analysis of the workflow repo. Generated alongside the WDD. Stable across all experiments on this workflow. |
| `required_instance` | Phase 2 — Scientist Input | Requires a human decision. The scientist fills this before DDD generation begins. |
| `required_derived` | Phase 2 — Auto-Computed | Computed automatically once all `required_instance` fields are filled. Never manually specified. |

### Versioning

The EDD introduces three levels of identity to distinguish configuration from execution:

| Field | Stable across | Changes when |
|---|---|---|
| `experiment_lineage_id` | All re-runs of the same parameter configuration | A new experiment configuration is defined |
| `version` | Repeated submissions with identical parameters | Parameter values change significantly |
| `instance_id` | Nothing — unique per submission | Every new job submission |

The `instance_id` is the field that links EDD records to IODD run records.

### Document Structure

**Metadata** — experiment identity, WDD pin (`wrd_lineage_id` + `wrd_version`), instance identity, provenance.

**Section A: Experiment Parameter Catalog** — one entry per configurable parameter discovered during static analysis of the workflow repo (config files, argparse definitions, env var reads). Each entry includes:
- Static skeleton: `source_file`, `source_location`, `parameter_type`, `possible_values`, `default_value`
- Cross-references: `affects.cardinalities`, `affects.hardware_paths`, `affects.data_objects_in_scope` (auto-derived from WDD `cardinality_source` and `hardware_path` annotations)
- Instance layer: `resolved_value` (scientist fills), `validation_check` (computed)

**Section B: Resolved Cardinalities** — one entry per data object with non-fixed cardinality (`cardinality_source.type = config_determined | runtime_determined`). For config-determined objects the resolved count is computed automatically from the resolved parameter value. For runtime-determined objects the scientist provides the count or an agent scans `input_data_root`. Each entry also computes `estimated_total_size` (`WRD estimated_size_hint × resolved_count`) as the primary input to DDD capacity feasibility checks.

**Section C: Hardware Resolution** — C.1 resolves WDD `hardware_path.execution_alternatives` into a concrete path selection per task (scientist chooses, with rationale). C.2 computes the `hardware_floor` — minimum resource requirements derived by substituting resolved parameter values into WDD `minimum_resource_assertions`. The DDD must verify all floor entries are satisfied by the target HRD before generating a deployment plan.

**Section D: Execution Context** — `target_system` (HRD id), `execution_profile`, `input_data_root`, `output_data_root`, free-text notes.

---

## WRD_Core_Design_v6.md (`wrd-6.0`)

### Scope unchanged

The WDD scope remains: static-analysis-derivable content only. The v6 additions are purely structural hooks for EDD resolution — no deployment decisions, no resolved values, no profiling data.

### Relationship notation updated

Section 1 now leads with the formal relationships:

```
EDD = f(WDD, input)
[sets of IODD] = execution(WDD, EDD, DDD, HRD, GD)
```

The architecture description is updated throughout from "five-document" to "six-document."

### New field: `hardware_path` on tasks (Section B)

Added to every task entry. Three sub-fields:

- **`has_conditional_execution`** (boolean) — true if the task contains code paths that select different execution logic based on a runtime parameter (e.g., `--device cpu/gpu`, `USE_GPU` env var, `torch.cuda.is_available()` guards).

- **`execution_alternatives`** — list of paths visible in code, each with `path_id`, `condition` (what triggers it), `description` (what differs between paths), and `io_dominance_hint`. Only populated when `has_conditional_execution = true`.

- **`minimum_resource_assertions`** — resource requirements explicitly validated in source code (assert statements, argparse range checks, MPI size guards). Each entry records `resource` (e.g., `gpu_memory_gb`, `n_mpi_ranks`), `condition` (the constraint as written in code), and `source_location` (file:line). Empty list if no assertions found.

The EDD reads `hardware_path` to resolve which path a specific experiment takes and what hardware floor applies.

### New field: `cardinality_source` on data objects (Section C)

Added to every data object entry alongside `cardinality`. Four sub-fields:

- **`type`** — `fixed | config_determined | runtime_determined`
  - `fixed`: count is hardcoded or derivable from code alone; no EDD resolution needed
  - `config_determined`: count comes from a config/CLI/env parameter; EDD resolves from `resolved_value`
  - `runtime_determined`: count depends on actual input data; scientist or directory scan provides it

- **`controlling_parameter`** — parameter name as it appears in the config, matching a `parameter_id` in the EDD catalog. Null for fixed and runtime-determined objects.

- **`config_file`** — relative path to the file where the controlling parameter is defined.

- **`possible_values`** — range or enumeration if statically determinable from code (e.g., "integers 1–22"); "unknown" if no bounds found.

### Section 11 added: EDD Design

The design specification for the EDD (purpose, relationships, versioning, field status model, document structure, full schema, generation procedure, corner cases) is embedded in the WRD Core Design document as Section 11 for co-location with the architecture specification.

---

## template_DDD.yaml (`ddd-5.0` → `ddd-6.0`)

### Formal relationship added

```
DDD = prescription(WRD, EDD, GD, HRD)
```

### WHO FILLS THIS / input set updated

All references to `WRD + GD + HRD` updated to `WRD + EDD + GD + HRD` throughout the purpose block and field status legend.

### Reasoning protocol expanded (9 steps, was 7)

Step 2 added: **Read the full EDD** — verify completeness gate passed, then extract `resolved_cardinalities`, `hardware_resolution.path_selections`, `hardware_resolution.hardware_floor`, and `execution_context.target_system`.

Step 5 added: **Verify all EDD `hardware_floor` entries are satisfied by HRD resources** before proceeding with any other reasoning. A floor violation must halt DDD generation.

### Readiness gate expanded

Three new checks:
- EDD completeness gate confirmed passed (no `required_instance` nulls, no `validation_check == "fail"`)
- All EDD `hardware_floor` entries have `satisfied == true` against HRD
- `parallelism_instances` derived from EDD `resolved_cardinalities` (not inferred from WRD cardinality prose)

### Header: EDD pin fields added

Two new fields after `wrd_version`:
- **`edd_lineage_id`** — copied from EDD `metadata.experiment_lineage_id`
- **`edd_instance_id`** — copied from EDD `metadata.instance_id`

`ddd_id` format updated: now `deploy:<wrd_id_short>:<edd_instance_id_short>:<strategy_name>` to include the EDD instance in the stable identifier.

### `parallelism_instances` reasoning updated

Primary source is now **EDD `resolved_cardinalities`** — find the entry for the data object produced by this task and read `resolved_count`. This is the authoritative instance count for the experiment. WRD cardinality prose is the fallback only for tasks with no variable-cardinality output.

### `compute_resource` reasoning updated

Primary source is now **EDD `hardware_resolution.path_selections`** — find the entry for this task and use `selected_path_id` to determine CPU vs GPU resource. The EDD `hardware_floor` for this task must be verified against the selected HRD resource before accepting the choice.

### `feasibility_check` and `capacity_checks` updated

Both now read **EDD `resolved_cardinalities[*].estimated_total_size`** for dataset size estimates rather than computing `WRD estimated_size_hint × cardinality` inline. The EDD has already done this multiplication with the concrete resolved counts; the DDD just reads the result.

---

## template_IODD.yaml (`iodd-5.0` → `iodd-6.0`)

### Formal relationship added (prominent, first in file)

```
[sets of IODD] = execution(WDD, EDD, DDD, HRD, GD)
```

The purpose block now explains the cross-run comparison model enabled by pinning all five documents.

### EMPIRICAL / PREDICTIVE mode descriptions updated

Predictive mode now lists `WRD + EDD + DDD + HRD` as inputs (was `DDD + HRD`). The EDD's `resolved_cardinalities` and `hardware_floor` inform `bytes_read/written` and capacity estimates in predictive mode.

### Header: EDD pin fields added

Two new fields after `wrd_lineage_id`:
- **`edd_lineage_id`** — copied from EDD `metadata.experiment_lineage_id`; enables grouping IODD records by experiment type
- **`edd_instance_id`** — copied from EDD `metadata.instance_id`; links IODD to the specific parameter values, resolved cardinalities, and hardware floor of that run

`run_id` updated: now explicitly aliased to EDD `instance_id` as the canonical run identity. Legacy mode (no EDD) falls back to scheduler job ID or generated UUID.

`iodd_id` format updated: `iodd:<ddd_id>:<edd_instance_id>` (was `iodd:<ddd_id>:<run_id>`).

### Predictive mode reasoning updated

`per_task_io_profile` and `communication_channels` predictive population now reads **EDD `resolved_cardinalities[*].estimated_total_size`** for `bytes_read`, `bytes_written`, and `data_volume_bytes` estimates rather than computing `WRD estimated_size_hint × cardinality` inline.

Readiness gates updated in both empirical and predictive modes to require `edd_lineage_id` and `edd_instance_id` filled.

---

## template_GD.yaml (`gd-5.0` → `gd-6.0`)
## template_HRD.yaml (`hrd-5.0` → `hrd-6.0`)

Schema version bump and architecture design version updated only. No structural changes. GD describes operator intent and HRD describes physical hardware — both are independent of the EDD.

---

## Summary of Schema Version Changes

| Document | v5 schema | v6 schema | Change type |
|---|---|---|---|
| WRD | `wrd-5.0` | `wrd-6.0` | New fields: `hardware_path`, `cardinality_source` |
| EDD | *(new)* | `edd-1.0` | New document |
| DDD | `ddd-5.0` | `ddd-6.0` | New inputs, EDD pin fields, updated reasoning |
| GD | `gd-5.0` | `gd-6.0` | Version bump only |
| HRD | `hrd-5.0` | `hrd-6.0` | Version bump only |
| IODD | `iodd-5.0` | `iodd-6.0` | Formal relationship, EDD pin fields, updated reasoning |