# WIDGET Document Architecture — Core Design v4

## Overview

This document defines the full five-document knowledge architecture that feeds AI agents operating within the WIDGET workflow I/O characterization and optimization system. It is temporarily titled "WRD Core Design" but describes all five documents in the architecture, not only the WRD.

The core insight is that a single workflow can be deployed many ways depending on performance goals, and a single deployment can exhibit different I/O behavior depending on the hardware it runs on. The document architecture mirrors this factorization precisely, giving agents the right scope of context for each tier of reasoning — neither too little to make good decisions, nor so much that capability-constrained local LLMs are overwhelmed.

---

## The Five Documents

| Document | Abbreviation | Describes | Changes when |
|----------|--------------|-----------|--------------|
| Workflow Representation Document | WRD | What the workflow *is* | Workflow code changes |
| Goal Document | GD | What the operator *wants* | Performance objectives change |
| Hardware Resource Document | HRD | What the hardware *provides* | Target system changes |
| Deployment Definition Document | DDD | How the workflow is *deployed* | Deployment strategy or goals change |
| I/O Definition Document | IODD | What I/O *actually happened* (or is predicted) | Each run on each system |

### Dependency Graph

```
                  ┌──────────┐
                  │   GD     │  operator performance objectives,
                  │  (Goal)  │  SLOs, resource budgets, priorities
                  └────┬─────┘
                       │ side input (motivates deployment choices)
                       ▼
 ┌──────────┐    ┌──────────┐    ┌──────────┐
 │   WRD    │───▶│   DDD    │───▶│   IODD   │
 │(Workflow)│ 1:N│(Deploy)  │ 1:N│  (I/O)   │
 └──────────┘    └──────────┘    └──────────┘
                       ▲
                       │ side input (constrains physical realization)
                  ┌────┴─────┐
                  │   HRD    │  storage tiers, bandwidth ceilings,
                  │(Hardware)│  network topology, contention model
                  └──────────┘
```

- **WRD → DDD** is one-to-many: one workflow definition, multiple deployment strategies (throughput-optimized, cost-optimized, latency-optimized, etc.).
- **DDD → IODD** is one-to-many: one deployment strategy can produce different I/O realizations on different hardware, or multiple profiling runs on the same hardware.
- **GD** is a side input to the WRD → DDD step. It encodes *why* the operator chose a particular deployment strategy. Every decision in the DDD back-references a GD goal ID.
- **HRD** is a side input to the DDD → IODD step. It defines the physical constraints within which I/O behavior materializes.

### Stability Ordering

The WRD is the most stable document — it changes only when the workflow code changes. The GD and HRD are moderately stable, changing only when operator objectives or hardware change. The DDD changes whenever strategy changes. The IODD is the least stable — produced by every run on every system.

---

## Cross-Reference ID Convention

All five documents share a common identifier scheme enabling unambiguous machine-parseable references across documents.

| Entity | ID Format | Example | Defined In |
|--------|-----------|---------|------------|
| Task | `task:<name>` | `task:contact_map` | WRD Task Registry |
| Dataset | `data:<name>` | `data:trajectory_frames` | WRD Data Flow Layer |
| P-C Edge | `pc:<producer>-><consumer>:<pattern>` | `pc:contact_map->aggregate:n_to_1` | WRD Execution Graph |
| Execution Profile | `profile:<name>` | `profile:tracks_only` | WRD Execution Profiles |
| Goal | `goal:<name>` | `goal:throughput_10gbs` | GD Goals |
| Hardware Tier | `tier:<name>` | `tier:burst_buffer` | HRD Storage Hierarchy |
| Compute Resource Class | `compute:<name>` | `compute:gpu_node` | HRD Compute Topology |
| DDD Strategy | `deploy:<wrd_id>:<strategy>` | `deploy:f3a9c2e1:throughput` | DDD Header |
| IODD Run | `iodd:<ddd_id>:<run_id>` | `iodd:deploy:f3a9c2e1:throughput:run_042` | IODD Header |

This convention ensures any entity mentioned in one document can be traced to its definition in another, making the full document set navigable by agents without requiring document-aware retrieval infrastructure.

---

## Agent Context Scoping

Different agent tiers in WIDGET consume different subsets of the document stack. The architecture is designed so each tier receives exactly the context it needs.

| Agent Tier | Primary Documents | Role |
|------------|-------------------|------|
| **Tier 1: Diagnosis (offline)** | WRD + IODD | Match observed I/O patterns to the IPDPS '26 taxonomy. The WRD provides structural context (what the workflow is, what P-C patterns it has); the IODD provides empirical evidence (what I/O actually happened). |
| **Tier 2: Prescription (advisory)** | WRD + GD + DDD + IODD | Recommend optimizations. Needs the full picture: what the workflow is (WRD), what the operator wants (GD), how it is deployed (DDD), and what I/O emerged (IODD) — to ensure recommendations are compatible with both goals and deployment constraints. |
| **Tier 3: Runtime Orchestration (online)** | DDD + IODD + HRD | Act on live telemetry within deployment constraints. The DDD defines what is allowed; the IODD defines current observed state; the HRD defines what is physically possible. |

The HRD is never needed by Tier 1 diagnosis because diagnosis reasons about workflow structure and observed I/O, not about hardware constraints. The WRD is never the primary document for Tier 3 orchestration because runtime decisions are scoped to the current deployment, not the abstract workflow.

---

## Generation Pipeline

Documents are generated in dependency order:

```
[1] WRD  ←  workflow source code + scientist questions
[2] GD   ←  operator or facility SLA requirements
[3] HRD  ←  system documentation + hardware profiling
[4] DDD  ←  WRD + GD + HRD  (agent-assisted or human operator)
[5] IODD ←  DDD + HRD + profiling tools (DataLife, DaYu, Darshan)
            OR predicted by agent from DDD + HRD before first run
```

Step 4 is the primary point where AI agent assistance adds high value: given a WRD, a GD, and an HRD, a prescription agent can propose a DDD that is likely to meet the operator's goals on the target hardware, before any run has executed.

Step 5 can be either empirical (from profiling a completed run) or predictive (agent reasoning from DDD + HRD). Predictive IODDs are generated when the operator wants to evaluate deployment strategies before committing to an allocation.

---

---

# Part I: Workflow Representation Document (WRD)

## WRD Purpose

The WRD captures the logical structure of a workflow — what it *is*, independent of how it is executed or what hardware it runs on. It is the most stable document in the architecture and the root from which all deployment reasoning flows.

**What belongs in the WRD:** logical task structure, task semantics, data flow and dataset descriptions, producer-consumer edge patterns, workflow-level structural classification, loop annotations, execution profiles, and the provenance of how the WRD was compiled.

**What does not belong in the WRD:** parallelism decisions, storage tier assignments, memory estimates, placement policies, hardware-specific constraints, operator performance goals, per-run I/O profiles, or observed bandwidth. These belong in the DDD, HRD, GD, and IODD respectively.

---

## WRD Design Principles

| Principle | Description |
|-----------|-------------|
| **Workflow-only scope** | Describes what the workflow is. Deployment decisions live in the DDD. Hardware constraints live in the HRD. |
| **Scientist-first** | Scientists provide a workflow code file and answer a small number of questions that cannot be answered from code. Everything else is extracted by static analysis or AI compilation. |
| **Versioned immutability** | Semantically immutable at a given version. Changes produce new versions under the same `workflow_lineage_id`. Companion documents pin to a specific WRD version. |
| **Pattern-aware** | Edges carry P-C cardinality patterns; the workflow carries a structural pattern classification. Agents use these as routing signals rather than re-deriving structure from raw topology. |
| **Portability** | Compiled from Pegasus DAX, Nextflow, Parsl, Swift/T, Slurm, Snakemake, and other formats. Translation gaps recorded with field-level confidence scores. |
| **Auditability** | Every agent-inferred field records who filled it, when, and with what confidence. No field is silently empty. |

---

## WRD Section 1: Workflow Header

**Purpose:** Top-level identity, provenance, versioning, and workflow-level structural classification.

**Key fields:**
- `workflow_lineage_id` — Stable UUID. Never changes across versions. Identifies the workflow concept, not a specific snapshot.
- `version` — Semantic version string (e.g., `1.2.0`). Incremented on any structural change to the WRD. Data enrichments (measured sizes, profiling refinements) update in place without incrementing the version.
- `version_notes` — Required changelog entry when version is incremented.
- `deprecated` — If true, companion documents must not use this version for new deployments.
- `workflow_name`, `workflow_description` — Human-readable. Description must meet Section 2a quality standards.
- `source_format` — `native` | `compiled_from_nextflow` | `compiled_from_pegasus_dax` | `compiled_from_parsl` | `compiled_from_slurm` | `compiled_from_snakemake` | `compiled_from_swift_t` | `other`
- `source_file` — Path to the primary workflow definition file.
- `schema_version`, `author`, `created_at`, `last_modified_at`

**Workflow-level pattern classification:**
- `workflow_pattern` — Structural pattern following the IPDPS '26 taxonomy:
  - `pipeline` — linear sequence; output of each stage feeds the next
  - `scatter_gather` — fan-out distributes work across parallel instances; fan-in aggregates results
  - `iterative` — one or more convergence or time-stepping loops
  - `cascading` — producer stage continuously feeds downstream consumers with partial results (streaming)
  - `hybrid` — combines two or more of the above at different stages
- `workflow_pattern_notes` — Agent-inferred justification, especially required for `hybrid`.

This classification belongs in the header because it is derivable from DAG topology and loop annotations, does not change between deployments, and gives agents a top-level routing signal for optimization strategy selection.

---

## WRD Section 2a: Semantic Description Quality Standards

**Applies to:** every natural language description field — workflow, task, and dataset levels.

**Minimum required content:**
- Workflow level: scientific problem, domain, inputs, outputs.
- Task level: what the task does in domain terms, inputs, outputs, why it exists.
- Dataset level: what the data represents scientifically, format rationale, which tasks depend on it.

**Authoring-time validation:** descriptions shorter than 20 words, or containing only generic verbs with no domain nouns, are flagged as quality warnings in Translation Metadata. Flagged descriptions do not block WRD creation.

---

## WRD Section 2: Task Registry

**Purpose:** The catalog of all tasks. The canonical source of truth for all relationships. The Execution Graph is derived from this section.

**Per-task fields:**

| Field | Description |
|-------|-------------|
| `task_id` | Stable snake_case identifier, normalized from the source code task/process name. |
| `task_name` | Human-readable name. |
| `semantic_description` | Scientist-facing domain description. Quality-validated per Section 2a. |
| `functional_role` | Agent-facing behavioral summary (e.g., "pairwise distance computation over trajectory frames; I/O dominant"). Distinct from `semantic_description`. |
| `executable_ref` | Script or executable reference. |
| `task_type` | `compute` \| `io` \| `preprocessing` \| `postprocessing` |
| `io_dominance` | `compute_bound` \| `io_bound` \| `balanced` \| `unknown`. Agent-inferred; refined by profiling. |
| `output_class` | `intermediate` \| `checkpoint`. Scientist-provided. See WRD Section 5. |
| `contention_sensitivity` | `high` \| `medium` \| `low` \| `unknown`. How sensitive this task's performance is to shared storage contention. Agent-inferred; confirmed by profiling. |
| `relationships` | Typed, annotated edges to upstream tasks. See relationship schema below. |
| `loop_annotation` | If the task participates in an iterative structure. See WRD Section 2b. |
| `temporal_io_annotation` | When I/O occurs relative to compute within this task. See WRD Section 2c. |

**Relationship schema** (each entry in `relationships`):

| Field | Description |
|-------|-------------|
| `type` | `data_dependency` \| `depends_on` \| `optional_after` |
| `target_task_id` | Upstream task this relationship points to. |
| `description` | What data or ordering constraint this represents. |
| `pc_pattern` | P-C cardinality (see WRD Section 2d). Only on `data_dependency` edges. |
| `communication_pattern` | `shared_file` \| `file_per_producer` \| `in_memory` \| `streaming_channel`. Workflow-level hint; DDD may override. |
| `data_volume_class` | `small` (< 1 GB) \| `medium` (1–100 GB) \| `large` (> 100 GB). Agent-estimated. |
| `co_scheduling_hint` | `beneficial` \| `neutral` \| `harmful`. Whether co-locating producer and consumer is expected to help. Agent-inferred from `pc_pattern` and `io_phase`. |

---

## WRD Section 2b: Loop Annotation Model

| Field | Description |
|-------|-------------|
| `loop_id` | Shared across all tasks participating in the same loop. |
| `loop_type` | `static` \| `parameter_sweep` \| `data_driven` \| `convergence` |
| `bound_type` | `fixed_count` \| `parameter_set_size` \| `runtime_determined` \| `convergence_criterion` |
| `fixed_count` | Integer. Only when `bound_type = fixed_count`. |
| `parameter_ref` | Parameter or input determining iteration count. Only when `bound_type = parameter_set_size`. |
| `convergence_condition` | Plain-language termination criterion. Required when `loop_type = convergence`. |
| `max_iterations_guard` | Hard upper bound. Required when `loop_type = convergence`. |
| `loop_position` | `body` \| `entry_gate` \| `exit_check` |

| Loop Type | Meaning |
|-----------|---------|
| `static` | Count known at authoring time. |
| `parameter_sweep` | Count equals the size of a named parameter set or input file collection. |
| `data_driven` | Count determined at runtime by input data; not known until execution. |
| `convergence` | Iterates until a scientific criterion is satisfied. Both `convergence_condition` and `max_iterations_guard` are required. |

---

## WRD Section 2c: Temporal I/O Annotation

Per-task annotation describing the temporal relationship between I/O and compute. Feeds IODD generation and pipeline overlap reasoning.

| Field | Description |
|-------|-------------|
| `io_phase` | `upfront` (reads all inputs before compute) \| `streaming` (interleaves I/O with compute) \| `deferred` (writes only after compute completes) \| `mixed` |
| `burstiness` | `bursty` (I/O in short concentrated windows) \| `sustained` (spread across task duration) \| `unknown` |
| `overlap_potential` | `high` \| `low` \| `unknown`. Whether this task's I/O can be meaningfully overlapped with adjacent tasks' compute. |

Agent-inferred from code analysis; confirmed or refined by DPM traces after first run.

---

## WRD Section 2d: Producer-Consumer Edge Pattern Classification

Cardinality annotation on every `data_dependency` edge. Attached to `relationships` entries and reflected in the Execution Graph.

| Pattern | Meaning |
|---------|---------|
| `1_to_1` | One producer instance → one consumer instance. |
| `1_to_n` | One producer instance → multiple consumer instances (fan-out / scatter). |
| `n_to_1` | Multiple producer instances → one consumer (fan-in / gather). |
| `n_to_n` | Multiple producers → multiple consumers (all-to-all or partitioned exchange). |

---

## WRD Section 3: Execution Graph

**Purpose:** Standalone encoding of the workflow DAG. Derived from the Task Registry — never edited directly.

**Consistency contract:** The Execution Graph carries a SHA-256 integrity hash of the Task Registry's relationship section. Any agent detecting a hash mismatch must reject the graph and request regeneration.

| Field | Description |
|-------|-------------|
| `integrity_hash` | SHA-256 of the canonical serialization of all `relationships` entries in the Task Registry. |
| `last_generated` | ISO 8601 timestamp. |
| `nodes` | All `task_id` values. |
| `edges` | `{from, to, type, pc_pattern}` objects derived from Task Registry relationships. |
| `loop_groups` | Tasks grouped by shared `loop_id`, with `loop_type` and a descriptive note. |
| `workflow_pattern_evidence` | Structural features justifying the `workflow_pattern` classification in the header. |

---

## WRD Section 4: Data Flow Layer

Two levels with different population timing.

### Section 4a: Semantic Dataset Layer (always required)

One entry per data artifact flowing between tasks.

| Field | Description |
|-------|-------------|
| `dataset_id` | Stable snake_case identifier. |
| `description` | Scientist-facing description. Quality-validated per Section 2a. |
| `file_format` | `netCDF4` \| `HDF5` \| `CSV` \| `parquet` \| `binary` \| `JSON` \| `text` \| `other` |
| `format_internals` | Internal layout details: chunking strategy, compression codec, variable-length data presence, typical request size. Agent-inferred from file inspection or code. Hints to IODD generator. |
| `role` | `input` (external source) \| `intermediate` \| `checkpoint` |
| `producer_task` | `task_id` of the writing task, or null for external inputs. |
| `consumer_tasks` | List of `task_id` values that read this dataset. |
| `pc_pattern` | The P-C pattern on this dataset's edges. Consistent with relationship annotations on consumer tasks. |

### Section 4b: Dataset Lifecycle Layer (progressively populated)

Logical properties derivable from the DAG; size fields populated from completed runs. These belong in the WRD, not the IODD, because they are hardware-agnostic and the DDD generator needs them to make storage tier and cleanup scheduling decisions.

| Field | Description |
|-------|-------------|
| `creation_phase` | Which task completion event creates this dataset. Derived from the DAG. |
| `last_consumer_phase` | The latest phase at which any consumer reads this dataset. Derived from the DAG. |
| `retention_window` | Span between `creation_phase` and `last_consumer_phase`. Used by DDD to schedule cleanup for intermediates. |
| `access_frequency_class` | `once` \| `few_times` \| `repeatedly`. How many times the dataset is read across all consumers. |
| `consumer_count` | Number of distinct consumer task instances that read this dataset in a typical run. |
| `size_measured_bytes` | Actual measured size from a completed run. Null until first run. |
| `size_measurement_run_id` | Run ID from which the measurement came. |
| `size_measurement_confidence` | `high` (direct measurement) \| `estimated` (extrapolated) \| `unavailable` |

---

## WRD Section 5: Task Output Classification

Per-task scientific judgment. `intermediate` outputs exist only to pass data to downstream tasks and may be cleaned up after their last consumer completes. `checkpoint` outputs have standalone scientific value and must be assigned to persistent storage by the DDD.

This classification cannot be reliably inferred by static analysis. It is the primary non-trivial question the agent asks the scientist during WRD compilation.

---

## WRD Section 6: Execution Profiles

Named, valid partial execution subsets representing scientifically meaningful stopping points.

| Field | Description |
|-------|-------------|
| `profile_name` | Short identifier (e.g., `tracks_only`, `full`). |
| `terminal_task_id` | The last task required for this profile. |
| `description` | What scientific results this profile produces. |
| `required_task_set` | Always auto-derived by backward DAG traversal from `terminal_task_id`. Never manually specified — doing so creates a second source of truth that can diverge from the DAG. |
| `output_dataset_ids` | Checkpoint datasets produced by tasks in `required_task_set`. |

---

## WRD Section 7: Translation Metadata

Full provenance of how this WRD was produced.

| Field | Description |
|-------|-------------|
| `source_format`, `source_file` | Origin of the WRD. |
| `translation_tool` | Agent or tool name and version that compiled this WRD. |
| `translation_timestamp` | When the compilation occurred. |
| `unmapped_fields` | Fields that could not be populated from the source, with reasons. |
| `round_trip_gaps` | Fields that would be lost if this WRD were compiled back to the source format. |
| `quality_warnings` | Description fields flagged by authoring-time validation. |
| `field_confidence_records` | One record per agent-inferred field: `field_path`, `filled_by`, `confidence_level` (`high` \| `medium` \| `low` \| `inferred`), `confidence_reason`, `requires_human_review`. |

---

## WRD Population Sources

| WRD Content | Source |
|-------------|--------|
| Task list, names, executables | Static analysis of workflow code |
| Task dependency graph | Static analysis (Nextflow channels, Pegasus DAX edges, Parsl `depends_on`, Slurm `--dependency`, etc.) |
| P-C edge patterns | Derived from DAG topology (fan-out/fan-in structure) and loop annotations |
| Workflow-level pattern | AI agent derivation from DAG topology + loop annotations |
| Loop structure and types | Static analysis; convergence conditions prompt scientist if not in code |
| Semantic descriptions | AI inference from docstrings, function names, comments; flagged for review if low confidence |
| `functional_role`, `io_dominance` | AI inference from code structure; refined by profiling |
| Temporal I/O annotation | AI inference; confirmed by DPM traces after first run |
| `contention_sensitivity` | AI inference; confirmed by profiling |
| Dataset descriptions and file formats | Static analysis of input/output declarations |
| `format_internals` | File inspection or code analysis |
| Dataset role (`input`/`intermediate`/`checkpoint`) | Role from DAG; `intermediate` vs. `checkpoint` requires scientist input |
| Dataset lifecycle (creation phase, retention window) | Derived from DAG structure |
| `size_measured_bytes` | Measured by deployment tooling (inputs) or from completed runs (outputs) |
| Execution profiles | Proposed by agent from checkpoint tasks; confirmed by scientist |
| `co_scheduling_hint` | AI inference from `pc_pattern` and `io_phase` |

---

---

# Part II: Goal Document (GD)

## GD Purpose

The GD captures the operator's performance objectives and constraints that motivate a particular deployment strategy. It encodes *intent* — why the operator chose a particular configuration. Every decision in the DDD must back-reference a GD goal ID. Without the GD, deployment decisions are opaque; a prescription agent cannot evaluate whether a recommendation is aligned with what the operator actually wants.

The GD is a side input to the WRD → DDD step. It does not describe the workflow, the hardware, or the deployment — it describes what success looks like for this run.

---

## GD Design Principles

| Principle | Description |
|-----------|-------------|
| **Intent-first** | Captures why a deployment is configured the way it is, not what the configuration is. |
| **Conflict-explicit** | When goals conflict, the GD defines priority ordering and resolution policy explicitly rather than leaving it to the DDD generator to guess. |
| **Hard vs. soft** | Hard constraints are non-negotiable (the DDD must not violate them). Soft preferences are optimization targets (the DDD should maximize them subject to constraints). |
| **Traceable** | Every GD entry carries a stable `goal_id`. DDD decisions back-reference these IDs so the motivation for any deployment choice is always traceable. |

---

## GD Section 1: Goal Document Header

| Field | Description |
|-------|-------------|
| `gd_id` | Stable identifier for this goal set. |
| `wrd_lineage_id` | The `workflow_lineage_id` this GD applies to. A GD is always scoped to a specific workflow. |
| `wrd_version` | The WRD version this GD was authored against. |
| `operator` | Name or role of the operator or team defining these goals. |
| `created_at`, `last_modified_at` | Timestamps. |
| `description` | Plain-language summary of the operational context (e.g., "Production 40-year reanalysis run for CMIP7 submission; throughput is the primary concern"). |

---

## GD Section 2: Goals

Each goal entry has a stable `goal_id` used by the DDD for back-references.

| Field | Description |
|-------|-------------|
| `goal_id` | Stable identifier (e.g., `goal:throughput_10gbs`). Format: `goal:<name>`. |
| `goal_type` | `throughput` \| `latency` \| `resource_budget` \| `cost` \| `reliability` \| `data_placement` \| `other` |
| `description` | Plain-language statement of the goal (e.g., "sustained input ingestion rate of at least 10 GB/s"). |
| `metric` | The measurable quantity (e.g., `input_ingestion_rate_gbs`, `end_to_end_wall_time_minutes`). |
| `target_value` | The target threshold (e.g., `10`, `30`). |
| `target_unit` | Unit of the metric (e.g., `GB/s`, `minutes`, `node-hours`). |
| `constraint_type` | `hard` (must be satisfied; DDD is invalid if violated) \| `soft` (optimize toward; may be traded off). |
| `priority` | Integer rank among soft goals. Lower number = higher priority when goals conflict. Not applicable to hard goals. |

---

## GD Section 3: Conflict Resolution Policy

Defines how the DDD generator should behave when two or more soft goals cannot be simultaneously maximized.

| Field | Description |
|-------|-------------|
| `priority_ordering` | Ordered list of `goal_id` values from highest to lowest priority. |
| `resolution_notes` | Free-text guidance for non-obvious tradeoffs (e.g., "accept up to 20% latency increase to achieve throughput target; do not sacrifice reliability under any circumstances"). |

---

## GD Section 4: Hard Constraints

Constraints that the DDD must not violate. Distinct from hard-constraint goals (which are quantified performance thresholds) — these are categorical restrictions.

| Field | Description |
|-------|-------------|
| `constraint_id` | Stable identifier (e.g., `goal:must_use_pfs_for_checkpoints`). |
| `description` | Plain-language statement (e.g., "checkpoint datasets must be written to the parallel filesystem, not burst buffer"). |
| `applies_to` | Which WRD entities this constraint applies to — a `task_id`, `dataset_id`, or `all`. |
| `rationale` | Why this constraint exists (e.g., "checkpoint files must survive node failure; burst buffer is not fault-tolerant on this system"). |

---

## GD Example

```yaml
gd_id: "gd:storm_tracking:production_cmip7"
wrd_lineage_id: "f3a9c2e1-847b-4d02-b6f1-2c3d4e5f6a7b"
wrd_version: "1.0.0"
operator: "NCAR Mesoscale Dynamics Group"
description: >
  Production 40-year reanalysis run for CMIP7 submission.
  Throughput is the primary concern. End-to-end wall time must
  fit within a 48-hour allocation window.

goals:
  - goal_id: "goal:throughput_10gbs"
    goal_type: throughput
    description: "Sustained input ingestion rate of at least 10 GB/s"
    metric: input_ingestion_rate_gbs
    target_value: 10
    target_unit: "GB/s"
    constraint_type: soft
    priority: 1

  - goal_id: "goal:wall_time_48hr"
    goal_type: latency
    description: "End-to-end pipeline completion within 48 hours"
    metric: end_to_end_wall_time_hours
    target_value: 48
    target_unit: hours
    constraint_type: hard

  - goal_id: "goal:max_nodes_256"
    goal_type: resource_budget
    description: "Maximum 256 compute nodes"
    metric: node_count
    target_value: 256
    target_unit: nodes
    constraint_type: hard

conflict_resolution:
  priority_ordering:
    - "goal:wall_time_48hr"
    - "goal:throughput_10gbs"
    - "goal:max_nodes_256"
  resolution_notes: >
    Hard constraints take absolute precedence. Among soft goals,
    throughput is more important than node efficiency. Accept up
    to 30% node underutilization to meet the throughput target.

hard_constraints:
  - constraint_id: "goal:must_use_pfs_for_checkpoints"
    description: "All checkpoint datasets must be written to the PFS"
    applies_to: "all checkpoint datasets"
    rationale: >
      Checkpoint files must survive node failure. Burst buffer on
      this system is not fault-tolerant and is not backed up.
```

---

---

# Part III: Hardware Resource Document (HRD)

## HRD Purpose

The HRD describes the physical hardware on which a deployment will execute — what the system *is*, independent of how it is used. It provides the physical envelope within which the DDD must operate and within which the IODD's I/O characteristics materialize.

The HRD is a side input to the DDD → IODD step. The DDD generator uses it to make tier assignment feasibility checks (can the assigned tier actually hold the data?) and bandwidth ceiling checks (is the target bandwidth achievable on this hardware?). The IODD generator uses it to contextualize observed I/O metrics (a 1 GB/s read rate is excellent on spinning disk but poor on NVMe SSD).

---

## HRD Design Principles

| Principle | Description |
|-----------|-------------|
| **Hardware-only scope** | Describes what the hardware provides, not how it should be used. Usage decisions live in the DDD. |
| **Tier-ID-based** | Every storage tier and compute resource class carries a stable `tier_id` or `compute_id`. DDD and IODD reference these IDs — never hardcoded tier names. |
| **Empirical where possible** | Performance characteristics should reflect measured values, not vendor specifications alone. Empirical measurements are flagged with their source and date. |
| **Versioned** | Hardware changes (node replacements, firmware upgrades, filesystem reconfiguration). The HRD carries a version and timestamp. DDDs pin to a specific HRD version. |
| **Contention-aware** | Explicitly models whether storage tiers are shared across jobs and what contention behavior looks like. This is essential for the DDD to reason about interference. |

---

## HRD Section 1: HRD Header

| Field | Description |
|-------|-------------|
| `hrd_id` | Stable identifier for this hardware description. |
| `system_name` | Human-readable system name (e.g., "Frontier @ OLCF", "Perlmutter @ NERSC"). |
| `version` | HRD version. Incremented when hardware configuration changes. |
| `version_notes` | What changed in this version. |
| `facility` | Facility or institution. |
| `created_at`, `last_modified_at` | Timestamps. |
| `description` | Plain-language summary of the system architecture. |

---

## HRD Section 2: Compute Topology

| Field | Description |
|-------|-------------|
| `compute_id` | Stable identifier (e.g., `compute:cpu_node`, `compute:gpu_node`). Format: `compute:<name>`. |
| `node_count` | Total available nodes of this class. |
| `cores_per_node` | Physical cores per node. |
| `hardware_threads_per_core` | Hyperthreads or SMT threads per core. |
| `memory_per_node_gb` | DRAM capacity per node. |
| `memory_bandwidth_gbs` | Peak memory bandwidth per node (empirical if available). |
| `accelerators` | List of accelerator types per node (e.g., `{type: A100, count: 4, memory_gb: 80}`) or null. |
| `interconnect_id` | Reference to the network fabric entry this class uses. |

---

## HRD Section 3: Network Fabric

| Field | Description |
|-------|-------------|
| `interconnect_id` | Stable identifier (e.g., `net:slingshot_hss`). |
| `interconnect_type` | `InfiniBand` \| `Slingshot` \| `OmniPath` \| `Ethernet` \| `other` |
| `topology` | `dragonfly` \| `fat_tree` \| `torus` \| `mesh` \| `other` |
| `bisection_bandwidth_gbs` | Bisection bandwidth in GB/s. |
| `injection_bandwidth_per_node_gbs` | Per-node injection bandwidth. |
| `latency_us` | Typical MPI latency in microseconds (empirical). |
| `notes` | Known bottlenecks or congestion characteristics. |

---

## HRD Section 4: Storage Hierarchy

One entry per storage tier available on the system. These `tier_id` values are what the DDD references for dataset tier assignments.

| Field | Description |
|-------|-------------|
| `tier_id` | Stable identifier. Format: `tier:<name>`. Examples: `tier:node_ssd`, `tier:burst_buffer`, `tier:pfs`, `tier:object_store`. |
| `tier_name` | Human-readable name. |
| `tier_type` | `node_local_ssd` \| `node_local_hdd` \| `burst_buffer` \| `parallel_filesystem` \| `object_store` \| `in_memory` |
| `total_capacity_tb` | Total capacity in TB. |
| `per_job_capacity_tb` | Capacity available to a single job (may differ from total for shared tiers). |
| `peak_read_bandwidth_gbs` | Peak read bandwidth in GB/s (empirical preferred over vendor spec). |
| `peak_write_bandwidth_gbs` | Peak write bandwidth in GB/s. |
| `metadata_ops_per_sec` | Peak metadata operation rate (creates, opens, stats per second). |
| `access_latency_us` | Typical access latency in microseconds. |
| `persistence` | `volatile` (data lost at job end) \| `persistent` (data survives across jobs) \| `semi_persistent` (configurable retention). |
| `shared_across_jobs` | Boolean. If true, contention with other jobs is possible. |
| `contention_model` | See Section 4a below. |
| `notes` | Known performance characteristics, quirks, or limitations. |
| `benchmark_source` | Source and date of empirical measurements (e.g., "IOR benchmark, 2024-09-15"). |

### HRD Section 4a: Contention Model

Describes how a storage tier's performance degrades under multi-job load. Used by the DDD to decide whether to assign hot intermediate data to a shared tier.

| Field | Description |
|-------|-------------|
| `contention_type` | `none` (dedicated, no contention) \| `proportional` (performance scales linearly with job count) \| `saturating` (performance degrades sharply above a threshold) \| `unknown` |
| `saturation_threshold_jobs` | Number of concurrent jobs above which performance degrades sharply. Only relevant when `contention_type = saturating`. |
| `degradation_factor` | Observed bandwidth degradation factor under typical contention (e.g., `0.4` means 40% of peak bandwidth available under contention). |
| `qos_guarantees` | Whether this tier offers QoS guarantees to individual jobs. Boolean. |

---

## HRD Section 5: Known Performance Characteristics

Empirical measurements and known system behaviors that are not captured by the per-tier fields.

| Field | Description |
|-------|-------------|
| `measurement_id` | Identifier for this measurement entry. |
| `measurement_type` | `io_bandwidth` \| `metadata_rate` \| `network_latency` \| `memory_bandwidth` \| `other` |
| `tier_or_component` | `tier_id` or `interconnect_id` or `compute_id` this measurement applies to. |
| `measured_value` | Numeric value. |
| `unit` | Unit of measurement. |
| `conditions` | Description of conditions under which measurement was taken. |
| `benchmark_tool` | Tool used (e.g., `IOR`, `mdtest`, `OSU micro-benchmarks`). |
| `measured_at` | Date of measurement. |
| `notes` | Caveats or anomalies. |

---

---

# Part IV: Deployment Definition Document (DDD)

## DDD Purpose

The DDD defines how a workflow is deployed to achieve a specific set of goals on specific hardware. It is the execution strategy layer — bridging the logical workflow structure (WRD) with the physical constraints (HRD) in pursuit of the operator's objectives (GD).

Every decision in the DDD is motivated by a GD goal and constrained by HRD capacity. The DDD makes this motivation explicit through `goal_ref` back-references on every decision field. This is what makes the DDD the primary document a prescription agent consults when evaluating whether a recommendation is feasible and aligned with operator intent.

A single WRD can have multiple DDDs representing different deployment strategies (e.g., throughput-optimized, cost-optimized, latency-optimized). Each DDD is a self-contained, versioned document.

---

## DDD Design Principles

| Principle | Description |
|-----------|-------------|
| **Decision + motivation** | Every deployment decision records both what was decided and which GD goal motivated it. Decisions without `goal_ref` are flagged as incomplete. |
| **Hardware-referenced** | Storage tier assignments and compute resource choices reference HRD IDs, not hardcoded names. |
| **WRD-version-pinned** | Every DDD pins to a specific WRD version and HRD version. If either changes, the DDD must be re-validated. |
| **One-to-many** | A single WRD can have multiple DDDs. Each represents a distinct deployment strategy. |
| **Agent-generatable** | The DDD is the primary document an AI prescription agent produces when given a WRD + GD + HRD. |

---

## DDD Section 1: DDD Header

| Field | Description |
|-------|-------------|
| `ddd_id` | Stable identifier. Format: `deploy:<wrd_lineage_id>:<strategy_name>`. |
| `strategy_name` | Short label for this deployment strategy (e.g., `throughput_optimized`, `cost_optimized`). |
| `wrd_lineage_id` | The WRD this DDD is derived from. |
| `wrd_version` | The specific WRD version this DDD was generated against. Must be re-validated if WRD version changes. |
| `hrd_id` | The HRD this DDD targets. |
| `hrd_version` | The specific HRD version. |
| `gd_id` | The GD that motivated this deployment strategy. |
| `execution_profile` | Which WRD execution profile this DDD is designed for (e.g., `profile:full`). |
| `generated_by` | Agent or human operator that produced this DDD. |
| `generated_at` | Timestamp. |
| `description` | Plain-language summary of this deployment strategy and its primary tradeoffs. |

---

## DDD Section 2: Per-Task Parallelism

One entry per task in the WRD Task Registry.

| Field | Description |
|-------|-------------|
| `task_id` | References `task:<name>` from the WRD. |
| `parallelism_instances` | Number of concurrent task instances. |
| `ranks_per_instance` | MPI ranks (or equivalent) per task instance. |
| `threads_per_rank` | OpenMP threads (or equivalent) per rank. |
| `compute_resource` | `compute_id` from HRD (e.g., `compute:gpu_node`). |
| `goal_ref` | `goal_id` from GD that motivated this parallelism choice. |
| `rationale` | Plain-language explanation of why this parallelism was chosen. |

---

## DDD Section 3: Storage Tier Assignments

One entry per dataset in the WRD Data Flow Layer.

| Field | Description |
|-------|-------------|
| `dataset_id` | References `data:<name>` from the WRD. |
| `assigned_tier` | `tier_id` from HRD. |
| `cleanup_policy` | `after_last_consumer` \| `end_of_job` \| `retain_indefinitely`. For intermediate datasets, the DDD may schedule cleanup based on WRD `retention_window`. |
| `replication` | Whether this dataset is replicated for fault tolerance. Boolean. |
| `caching_policy` | `none` \| `cache_on_first_read` \| `prefetch`. Relevant for datasets read multiple times (informed by WRD `access_frequency_class`). |
| `goal_ref` | `goal_id` motivating this tier assignment. |
| `rationale` | Why this tier was chosen (e.g., "large intermediate dataset; burst buffer provides sufficient bandwidth and capacity, reducing PFS contention"). |
| `feasibility_check` | Whether the HRD tier has sufficient capacity and bandwidth for this dataset. `pass` \| `warning` \| `fail`. Computed from WRD `size_measured_bytes` and HRD `per_job_capacity_tb`. |

---

## DDD Section 4: Task Placement and Co-scheduling

| Field | Description |
|-------|-------------|
| `group_id` | Identifier for this placement group. |
| `tasks` | List of `task_id` values that should be co-located or co-scheduled. |
| `placement_policy` | `co_locate` (same node or node group) \| `spread` (distribute across nodes) \| `no_constraint` |
| `co_schedule` | Whether these tasks should overlap in time. Boolean. |
| `goal_ref` | `goal_id` motivating this placement decision. |
| `rationale` | Typically references WRD `co_scheduling_hint` on the relevant P-C edges. |

---

## DDD Section 5: Stage Ordering and Pipelining

| Field | Description |
|-------|-------------|
| `pipeline_group_id` | Identifier for this pipelining decision. |
| `tasks` | List of `task_id` values that form a pipeline. |
| `overlap_strategy` | `full_overlap` (all stages run simultaneously on different data chunks) \| `partial_overlap` \| `sequential` |
| `batch_size` | Number of data items processed per pipeline cycle, if applicable. |
| `goal_ref` | `goal_id` motivating this pipelining decision. |
| `rationale` | Plain-language explanation. |

---

## DDD Section 6: Replication and Caching Strategy

Global-level replication and caching decisions not covered by per-dataset entries.

| Field | Description |
|-------|-------------|
| `global_replication_factor` | Default replication factor for checkpoint datasets not explicitly assigned. |
| `checkpoint_interval` | For iterative workflows, how frequently to write checkpoints (e.g., every N iterations). |
| `cache_warm_strategy` | Whether to pre-populate burst buffer or node-local storage before job start. |
| `goal_ref` | `goal_id` motivating global replication/caching choices (typically a reliability goal). |

---

## DDD Section 7: DDD Validation Summary

A machine-readable record of whether the DDD satisfies the GD's hard constraints against the target HRD.

| Field | Description |
|-------|-------------|
| `validation_status` | `valid` \| `warnings` \| `invalid` |
| `hard_constraint_checks` | One entry per GD hard constraint: `{constraint_id, status: pass/fail, evidence}`. |
| `capacity_checks` | One entry per storage tier: `{tier_id, total_assigned_gb, tier_capacity_gb, status: pass/warning/fail}`. |
| `bandwidth_checks` | One entry per critical P-C edge: `{pc_edge_id, required_bandwidth_gbs, tier_peak_bandwidth_gbs, status}`. |
| `validation_notes` | Free-text notes on warnings or borderline checks. |

---

---

# Part V: I/O Definition Document (IODD)

## IODD Purpose

The IODD captures the concrete I/O and communication semantics that emerge when a specific deployment (DDD) runs on specific hardware (HRD). It is either generated empirically from profiling tools (DataLife, DaYu, Darshan) after a completed run, or predicted by an agent from DDD + HRD before a run executes.

The IODD is the union of:
- DataLife's DFL-G lifecycle annotations (per-file creation, access, and consumer events)
- DaYu's SDG/FTG semantic mappings (dataset-level communication structure)
- Darshan's system-level I/O metrics (bytes, ops, bandwidth, POSIX timings)

All bound to a specific deployment on specific hardware.

---

## IODD Design Principles

| Principle | Description |
|-----------|-------------|
| **Run-scoped** | Every IODD is tied to a specific DDD + HRD + run. Multiple runs of the same DDD produce separate IODDs. |
| **Empirical or predictive** | Empirical IODDs come from profiling. Predictive IODDs are agent-generated estimates; they carry a `predictive: true` flag and confidence records. |
| **Diagnosis-ready** | Structured to directly feed Tier 1 diagnosis agents. Fields map to the IPDPS '26 I/O pattern taxonomy. |
| **Cross-referenceable** | References WRD, DDD, and HRD IDs throughout so any observed I/O characteristic can be traced to the workflow structure, deployment decision, and hardware tier that produced it. |

---

## IODD Section 1: IODD Header

| Field | Description |
|-------|-------------|
| `iodd_id` | Stable identifier. Format: `iodd:<ddd_id>:<run_id>`. |
| `ddd_id` | The DDD that was executed. |
| `hrd_id` | The HRD on which execution occurred. |
| `wrd_lineage_id` | Back-reference to the originating WRD. |
| `run_id` | Identifier of the specific execution run. |
| `run_start`, `run_end` | ISO 8601 timestamps. |
| `predictive` | Boolean. If true, this IODD was agent-generated from DDD + HRD, not from profiling. |
| `profiling_tools` | List of tools used (e.g., `[DataLife, DaYu, Darshan]`). Null if `predictive = true`. |
| `description` | Plain-language summary of what was observed or predicted. |

---

## IODD Section 2: Per-Task I/O Profile

One entry per task instance in the execution. For loop tasks, one entry per loop iteration (or an aggregate entry with per-iteration statistics).

| Field | Description |
|-------|-------------|
| `task_id` | References `task:<name>` from WRD. |
| `instance_id` | Instance index for parallel or loop tasks. |
| `storage_tier_used` | `tier_id` from HRD (may differ from DDD assignment if runtime routing occurred). |
| `bytes_read` | Total bytes read. |
| `bytes_written` | Total bytes written. |
| `read_ops` | Number of read operations. |
| `write_ops` | Number of write operations. |
| `open_ops` | Number of file open operations. |
| `close_ops` | Number of file close operations. |
| `observed_read_bandwidth_gbs` | Average read bandwidth in GB/s. |
| `observed_write_bandwidth_gbs` | Average write bandwidth in GB/s. |
| `peak_read_bandwidth_gbs` | Peak read bandwidth observed. |
| `peak_write_bandwidth_gbs` | Peak write bandwidth observed. |
| `posix_open_time_s` | Cumulative time spent in open() calls. |
| `posix_read_time_s` | Cumulative time spent in read() calls. |
| `posix_write_time_s` | Cumulative time spent in write() calls. |
| `posix_close_time_s` | Cumulative time spent in close() calls. |
| `access_pattern_observed` | `sequential` \| `random` \| `strided` \| `mixed`. |
| `io_phase_observed` | `upfront` \| `streaming` \| `deferred` \| `mixed`. Compared to WRD `temporal_io_annotation.io_phase` to detect anomalies. |
| `compute_to_io_ratio` | Fraction of task wall time spent in I/O. |
| `contention_events` | Number of detected contention events (lock waits, bandwidth throttling). |
| `dpm_trace_ref` | Reference to the DPM trace file or database entry. |

---

## IODD Section 3: Communication Channel Definitions

One entry per P-C edge in the WRD Execution Graph that was active in this run.

| Field | Description |
|-------|-------------|
| `pc_edge_id` | References `pc:<producer>-><consumer>:<pattern>` from WRD. |
| `physical_path` | How data actually moved: `shared_file_on_pfs` \| `staged_through_burst_buffer` \| `node_local_transfer` \| `in_memory_mpi` \| `streaming_pipe` |
| `tier_id` | `tier_id` from HRD where this data resided during transfer. |
| `data_volume_bytes` | Total bytes transferred on this channel. |
| `transfer_bandwidth_gbs` | Achieved bandwidth on this channel. |
| `transfer_time_s` | Wall time for the full data transfer on this channel. |
| `transfer_pattern` | `bulk_sequential` \| `fine_grained_random` \| `chunked_streaming` |
| `match_ddd` | Whether the physical path matches the DDD's storage tier assignment for this dataset. Boolean. Mismatches flag for investigation. |

---

## IODD Section 4: Data Format Observations

Per-dataset format details observed at runtime, supplementing the WRD `format_internals` with empirical confirmation or corrections.

| Field | Description |
|-------|-------------|
| `dataset_id` | References `data:<name>` from WRD. |
| `actual_file_format` | What was actually observed (may differ from WRD declaration if format conversion occurred). |
| `actual_chunk_size_bytes` | Observed chunk or request size. |
| `actual_compression` | Whether compression was active. |
| `variable_length_data` | Whether variable-length records were observed. |
| `metadata_fraction` | Fraction of I/O time spent on metadata operations (creates, stats, opens). |
| `notes` | Any format anomalies relevant to I/O performance. |

---

## IODD Section 5: Temporal I/O Behavior

System-level view of when I/O occurred across the full workflow execution.

| Field | Description |
|-------|-------------|
| `task_id` | Task this observation covers. |
| `io_start_offset_s` | When I/O began relative to task start (in seconds). |
| `io_end_offset_s` | When I/O ended relative to task start. |
| `io_burst_count` | Number of distinct I/O burst events observed. |
| `inter_burst_gap_s` | Average time between I/O bursts (for bursty tasks). |
| `compute_io_overlap_fraction` | Fraction of task wall time where compute and I/O were simultaneous. |
| `pipeline_overlap_observed` | Whether this task's I/O overlapped with an adjacent task's compute. Boolean. |
| `match_wrd_io_phase` | Whether observed `io_phase` matched WRD `temporal_io_annotation.io_phase`. Boolean. Mismatches flag for WRD update. |

---

## IODD Section 6: Contention and Interference

| Field | Description |
|-------|-------------|
| `tier_id` | Storage tier where contention was observed. |
| `contention_period_start`, `contention_period_end` | Wall-clock interval of detected contention. |
| `bandwidth_at_contention_gbs` | Bandwidth achieved during contention. |
| `bandwidth_baseline_gbs` | Baseline bandwidth on this tier without contention (from HRD). |
| `degradation_factor` | `bandwidth_at_contention / bandwidth_baseline`. |
| `likely_cause` | `multi_job_sharing` \| `cross_task_sharing` \| `metadata_bottleneck` \| `network_congestion` \| `unknown` |
| `affected_tasks` | List of `task_id` values affected during this contention period. |

---

## IODD Section 7: Per-File Lifecycle Events

DataLife-style tracking of individual file lifecycle within the run. Enables fine-grained diagnosis of data staging efficiency and early cleanup opportunities.

| Field | Description |
|-------|-------------|
| `dataset_id` | References `data:<name>` from WRD. |
| `file_path` | Actual filesystem path observed. |
| `created_at_offset_s` | Seconds after run start when file was created. |
| `first_read_at_offset_s` | Seconds after run start of first read access. |
| `last_read_at_offset_s` | Seconds after run start of last read access. |
| `deleted_at_offset_s` | Seconds after run start when file was deleted. Null if retained. |
| `read_count` | Total number of read accesses. |
| `unique_reader_count` | Number of distinct processes or tasks that read this file. |
| `size_bytes` | Observed file size. |
| `idle_time_s` | Time between last write and first read (staging gap). |
| `lifetime_s` | Time from creation to deletion (or end of run if not deleted). |
| `match_wrd_retention` | Whether actual lifetime matches WRD `retention_window` expectation. Boolean. |

---

## IODD Section 8: Diagnosis Summary

A machine-readable diagnosis of the run's I/O behavior, structured to directly feed Tier 1 diagnosis agents.

| Field | Description |
|-------|-------------|
| `overall_io_pattern` | The observed workflow-level I/O pattern: `pipeline` \| `scatter_gather` \| `iterative` \| `cascading` \| `hybrid`. Should match WRD `workflow_pattern` if the deployment behaved as designed. |
| `pattern_match_wrd` | Whether observed I/O pattern matches WRD `workflow_pattern`. Mismatch is a significant diagnostic signal. |
| `bottleneck_summary` | List of identified bottlenecks: `{task_id or tier_id, bottleneck_type, severity: high/medium/low, description}`. |
| `optimization_opportunities` | List of potential optimizations surfaced from the data: `{opportunity_type, affected_entities, estimated_impact, evidence}`. |
| `anomalies` | Fields where observed values diverged significantly from WRD annotations or DDD decisions, warranting investigation. |

---

---

# Cross-Document Summary

## Document Structure at a Glance

```
WRD  (what the workflow IS — stable, hardware-agnostic, deployment-agnostic)
│
├── Header: workflow_lineage_id, version, workflow_pattern
├── Task Registry: task_id, semantic_description, functional_role,
│   io_dominance, output_class, relationships (with pc_pattern,
│   co_scheduling_hint), loop_annotation, temporal_io_annotation
├── Execution Graph: integrity_hash, nodes, edges, loop_groups
├── Data Flow Layer:
│   ├── Semantic: dataset_id, description, file_format, format_internals,
│   │   role, producer_task, consumer_tasks, pc_pattern
│   └── Lifecycle: creation_phase, retention_window, consumer_count,
│       access_frequency_class, size_measured_bytes
├── Execution Profiles: profile_name, terminal_task_id,
│   required_task_set [AUTO-DERIVED], output_dataset_ids
└── Translation Metadata: confidence_records, quality_warnings

GD  (what the operator WANTS — scoped to a workflow + operator context)
│
├── Header: gd_id, wrd_lineage_id, operator
├── Goals: goal_id, goal_type, metric, target_value, constraint_type, priority
├── Conflict Resolution: priority_ordering, resolution_notes
└── Hard Constraints: constraint_id, applies_to, rationale

HRD  (what the hardware PROVIDES — scoped to a system)
│
├── Header: hrd_id, system_name, version
├── Compute Topology: compute_id, cores, memory, accelerators
├── Network Fabric: interconnect_id, topology, bandwidth, latency
├── Storage Hierarchy: tier_id, tier_type, capacity, peak bandwidth,
│   persistence, contention_model
└── Empirical Benchmarks: measurement_id, tier, measured_value, conditions

DDD  (how the workflow is DEPLOYED — references WRD + GD + HRD)
│
├── Header: ddd_id, wrd_version, hrd_version, gd_id, execution_profile
├── Per-Task Parallelism: task_id → instances, ranks, compute_id, goal_ref
├── Storage Tier Assignments: dataset_id → tier_id, cleanup_policy,
│   replication, feasibility_check, goal_ref
├── Task Placement / Co-scheduling: group_id, tasks, placement_policy,
│   co_schedule, goal_ref
├── Pipelining Decisions: pipeline_group_id, tasks, overlap_strategy,
│   goal_ref
├── Replication / Caching Strategy: global_replication, checkpoint_interval
└── Validation Summary: hard_constraint_checks, capacity_checks,
    bandwidth_checks

IODD  (what I/O HAPPENED — references DDD + HRD, per run)
│
├── Header: iodd_id, ddd_id, hrd_id, run_id, predictive
├── Per-Task I/O Profile: task_id, bytes_read/written, bandwidth,
│   POSIX timings, access_pattern_observed, io_phase_observed
├── Communication Channels: pc_edge_id, physical_path, tier_id,
│   transfer_bandwidth, match_ddd
├── Data Format Observations: dataset_id, actual_format, chunk_size,
│   metadata_fraction
├── Temporal I/O Behavior: task_id, io_burst_count, overlap_observed,
│   match_wrd_io_phase
├── Contention and Interference: tier_id, degradation_factor, affected_tasks
├── Per-File Lifecycle: dataset_id, created/read/deleted timestamps,
│   idle_time, lifetime, match_wrd_retention
└── Diagnosis Summary: overall_io_pattern, bottleneck_summary,
    optimization_opportunities, anomalies
```

---

## What Each Document Requires

| Document | Inputs Required to Generate |
|----------|-----------------------------|
| WRD | Workflow source code file + scientist answers one question (output_class per task) |
| GD | Operator objectives + facility SLA |
| HRD | System documentation + hardware profiling benchmarks |
| DDD | WRD + GD + HRD |
| IODD (empirical) | Completed run with profiling tools (DataLife, DaYu, Darshan) + DDD + HRD |
| IODD (predictive) | DDD + HRD + agent reasoning |

---

## Appendix: Changes from v3

| Area | Change |
|------|--------|
| Scope of document | Extended from WRD-only to full five-document architecture. WRD content unchanged from v3. |
| GD (Goal Document) | **Fully specified.** Header, Goals with typed fields and priority ordering, Conflict Resolution Policy, Hard Constraints, YAML example. |
| HRD (Hardware Resource Document) | **Fully specified.** Header, Compute Topology with `compute_id`, Network Fabric with `interconnect_id`, Storage Hierarchy with `tier_id` and Contention Model per tier, Empirical Benchmarks section. |
| DDD (Deployment Definition Document) | **Fully specified.** Header with WRD + HRD + GD version pins, Per-Task Parallelism with `goal_ref` on every field, Storage Tier Assignments with feasibility checks against HRD, Task Placement and Co-scheduling, Pipelining Decisions, Replication/Caching Strategy, Validation Summary. |
| IODD (I/O Definition Document) | **Fully specified.** Header with `predictive` flag, Per-Task I/O Profile with full POSIX metrics and phase comparison to WRD, Communication Channel Definitions per P-C edge, Data Format Observations, Temporal I/O Behavior, Contention and Interference model, Per-File Lifecycle (DataLife-style), Diagnosis Summary for Tier 1 agents. |
| Cross-reference ID convention | **Formalized.** All five documents share a common ID namespace. `task:`, `data:`, `pc:`, `tier:`, `compute:`, `goal:`, `deploy:`, `iodd:` prefixes defined. |
| Agent context scoping table | **Added.** Maps each agent tier (Diagnosis, Prescription, Orchestration) to its primary documents with rationale. |
| Generation pipeline | **Extended.** Steps 1–5 with emphasis on step 4 (DDD generation) as the primary AI agent value-add point. |