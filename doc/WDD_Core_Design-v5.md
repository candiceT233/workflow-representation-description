# WIDGET Document Architecture — Core Design v5

## Overview

This document defines the full five-document knowledge architecture that feeds AI agents operating within the WIDGET workflow I/O characterization and optimization system.

The core insight is that a single workflow can be deployed many ways depending on performance goals, and a single deployment can exhibit different I/O behavior depending on the hardware it runs on. The document architecture mirrors this factorization precisely, giving agents the right scope of context for each tier of reasoning.

---

## The Five Documents

| Document | Abbreviation | Describes | Changes when |
|----------|--------------|-----------|--------------|
| Workflow Definition Document | WDD | What the workflow *is* | Workflow code changes |
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
 │   WDD    │───▶│   DDD    │───▶│   IODD   │
 │(Workflow)│ 1:N│(Deploy)  │ 1:N│  (I/O)   │
 └──────────┘    └──────────┘    └──────────┘
                       ▲
                       │ side input (constrains physical realization)
                  ┌────┴─────┐
                  │   HRD    │  storage tiers, bandwidth ceilings,
                  │(Hardware)│  network topology, contention model
                  └──────────┘
```

### Stability Ordering

WDD (most stable) → GD / HRD (moderately stable) → DDD (changes with strategy) → IODD (least stable, per run).

---

## Cross-Reference ID Convention

| Entity | ID Format | Example | Defined In |
|--------|-----------|---------|------------|
| Stage | `stage:<n>` | `stage:simulation` | WDD Stage Catalog |
| Task | `task:<n>` | `task:contact_map` | WDD Task Registry |
| Dataset | `data:<n>` | `data:trajectory_frames` | WDD Data Flow Layer |
| P-C Edge | `pc:<producer>-><consumer>:<pattern>` | `pc:contact_map->aggregate:n_to_1` | WDD P-C Edges |
| I/O Hint | `hint:<n>` | `hint:partial_access_training` | WDD I/O Behavioral Hints |
| Execution Profile | `profile:<n>` | `profile:tracks_only` | WDD Execution Profiles |
| Goal | `goal:<n>` | `goal:throughput_10gbs` | GD Goals |
| Hardware Tier | `tier:<n>` | `tier:burst_buffer` | HRD Storage Hierarchy |
| Compute Resource | `compute:<n>` | `compute:gpu_node` | HRD Compute Topology |
| DDD Strategy | `deploy:<wdd_id>:<strategy>` | `deploy:f3a9c2e1:throughput` | DDD Header |
| IODD Run | `iodd:<ddd_id>:<run_id>` | `iodd:deploy:f3a9c2e1:throughput:run_042` | IODD Header |

---

## Agent Context Scoping

| Agent Tier | Primary Documents | Role |
|------------|-------------------|------|
| **Tier 1: Diagnosis (offline)** | WDD + IODD | Match observed I/O patterns to IPDPS '26 taxonomy. WDD provides structural context; IODD provides empirical evidence. |
| **Tier 2: Prescription (advisory)** | WDD + GD + DDD + IODD | Recommend optimizations compatible with goals and deployment constraints. |
| **Tier 3: Runtime Orchestration (online)** | DDD + IODD + HRD | Act on live telemetry. DDD defines what is allowed; IODD defines current state; HRD defines what is physically possible. |

---

## Generation Pipeline

```
[1] WDD  ←  workflow source code + scientist questions
[2] GD   ←  operator or facility SLA requirements
[3] HRD  ←  system documentation + hardware profiling
[4] DDD  ←  WDD + GD + HRD  (agent-assisted or human operator)
[5] IODD ←  DDD + HRD + profiling tools (DataLife, DaYu, Darshan)
            OR predicted by agent from DDD + HRD before first run
```

Step 4 is the primary AI agent value-add point. Step 5 can be empirical or predictive.

---

---

# Part I: Workflow Definition Document (WDD)

## WDD Purpose

The WDD captures the logical structure of a workflow — what it *is*, independent of how it is executed or what hardware it runs on. It is the most stable document and the root from which all deployment reasoning flows. Everything in the WDD must be derivable from static analysis of the source code — no profiling data, no hardware specifics, no deployment decisions.

**What belongs in the WDD:** stage structure, task catalog, task semantics, parallelism model, producer-consumer edges with coupling classification, workflow-level pattern classification, data object registry with format hints, I/O behavioral hints, execution profiles, and generation provenance.

**What does not belong in the WDD:** parallelism instance counts, storage tier assignments, memory estimates, placement policies, hardware constraints, operator goals, per-run I/O profiles, or observed bandwidth. These belong in DDD, HRD, GD, and IODD respectively.

---

## WDD Design Principles

| Principle | Description |
|-----------|-------------|
| **Workflow-only scope** | Describes what the workflow is. Deployment decisions live in the DDD. Hardware constraints live in the HRD. |
| **Static-analysis-first** | Everything derivable from code is extracted by the agent. The scientist is only asked about things that cannot be inferred from code (output_class, convergence conditions, workflow description). |
| **Versioned immutability** | Semantically immutable at a given version. Changes produce new versions under the same `workflow_lineage_id`. Companion documents pin to a specific WDD version. |
| **Pattern-aware** | Edges carry P-C cardinality and coupling; the workflow carries structural pattern classification. Agents use these as routing signals. |
| **Hint-forward** | I/O behavioral concerns visible from code are captured as typed, named hints — giving diagnosis agents a pre-loaded list of suspicions rather than starting cold. |
| **Portability** | Compiled from Nextflow, Pegasus DAX, Parsl, Slurm, Snakemake, Swift/T. Translation gaps recorded with field-level confidence scores. |
| **Auditability** | Every agent-inferred field records who filled it, when, and with what confidence. No field is silently empty. |

---

## WDD Field Status Model

Every field in the WDD carries a `_status` annotation that tells the generating agent exactly what to do with it.

| Status | Meaning |
|--------|---------|
| `required_static` | Extract from workflow source code via static analysis. If extraction fails, escalate to `required_static_ask`. |
| `required_static_ask` | Cannot be reliably inferred from code. Agent **must** prompt the scientist before proceeding. |
| `required_deploy` | Leave null at compile time. Deployment tooling (Jarvis-MCP) measures from filesystem or completed run outputs. |
| `optional_enrichment` | Leave null at compile time. DPM tracing populates after first run. Not required for initial deployment. |

**Agent Readiness Gate** — before handing WDD to DDD generator, verify:
- All `required_static` and `required_static_ask` fields are non-null
- `execution_graph.integrity_hash` matches current task_registry
- All `required_task_sets` in execution_profiles were auto-derived
- `translation_metadata.field_confidence_records` has one entry per agent-inferred field
- Any `requires_human_review: true` field has been reviewed or explicitly deferred

---

## WDD Generation Procedure

The following 7-step procedure is given to Claude Code along with the workflow codebase.

**Step 1 — Survey codebase structure.** Read the top-level directory, README, and orchestration files (Makefile, shell scripts, Nextflow main.nf, Pegasus DAX, Parsl app file, Snakemake Snakefile, Slurm submission script). Identify: workflow entry point, how stages/tasks are defined and launched, configuration files.

**Step 2 — Identify all stages and tasks.** Walk the orchestration layer to enumerate every stage and every distinct executable unit. For each task: determine stage membership, read source code, note inputs and outputs.

**Step 3 — Build the data object registry.** Compile a deduplicated list of all data objects. Classify each as input/intermediate/output/checkpoint/config. If the code uses HDF5 or netCDF, extract dataset names, dtypes, and shapes from file-creation code.

**Step 4 — Map producer-consumer edges.** For each data object, identify producers and consumers. Classify P-C pattern (1-1, 1-n, n-1, n-n). Determine coupling (tight vs. loose). Describe what data moves and how it is accessed.

**Step 5 — Analyze workflow-level patterns.** From the DAG: classify as cascading, iterative, scatter_gather, pipeline, broadcast, checkpointing, conditional, or hybrid. Identify critical path and control flow (iteration, conditionals).

**Step 6 — Extract I/O behavioral hints.** Re-read task code looking for: partial file access, format mismatch, small file overhead, unnecessary serialization, data reuse, checkpoint waste, metadata overhead.

**Step 7 — Assemble and validate.** Write `wdd.yaml`. Validate: every task references valid data_ids; every data_id appears in at least one task; every pc_edge references valid task_ids; cross-reference index is consistent; stage execution order matches DAG. Mark any assumption with `[ASSUMPTION]`.

**Format-specific extraction rules:**

| Source Format | Task extraction | Dependency extraction |
|---|---|---|
| Nextflow | `process` blocks | Channel connections between processes |
| Pegasus DAX | `<job>` elements | `<uses>` file elements on jobs |
| Parsl | `@python_app` / `@bash_app` decorators | `depends_on=` arguments |
| Slurm | Script steps, job arrays | `#SBATCH --dependency=` directives |
| Snakemake | `rule` blocks | `input:`/`output:` file matching across rules |
| Swift/T | `app` functions | Data-flow variable passing |

---

## WDD Section 1: Workflow Header

**Purpose:** Identity, provenance, versioning, and workflow-level structural classification.

| Field | Status | Description |
|-------|--------|-------------|
| `workflow_lineage_id` | `required_static` | Stable UUID. Never changes across versions. Generate once; preserve on recompile. |
| `version` | `required_static` | Semantic version (e.g., `1.0.0`). Increment on structural changes. Data enrichments update in place. |
| `version_notes` | `required_static` | Changelog entry required when version increments. |
| `deprecated` | `required_static` | If true, companion documents must not use this version for new deployments. |
| `workflow_name` | `required_static` | Human-readable name. |
| `workflow_description` | `required_static_ask` | 1–3 sentence scientific summary. Quality-validated per Section 2a. |
| `source_format` | `required_static` | `native` \| `compiled_from_nextflow` \| `compiled_from_pegasus_dax` \| `compiled_from_parsl` \| `compiled_from_slurm` \| `compiled_from_snakemake` \| `compiled_from_swift_t` \| `other` |
| `source_file` | `required_static` | Path to primary workflow definition file. |
| `source_commit` | `required_static` | Git commit hash if available; null otherwise. |
| `schema_version` | `required_static` | Always `"wdd-5.0"`. |
| `generated_by` | `required_static` | Agent name and version (e.g., `"claude-code-3.7"`). |
| `created_at`, `last_modified_at` | `required_static` | ISO 8601 timestamps. |

**Workflow-level pattern classification** (part of header):

| Field | Status | Description |
|-------|--------|-------------|
| `workflow_pattern` | `required_static` | Primary pattern: `pipeline` \| `scatter_gather` \| `iterative` \| `cascading` \| `broadcast` \| `checkpointing` \| `conditional` \| `hybrid` |
| `secondary_patterns` | `required_static` | Additional patterns when `workflow_pattern = hybrid`. |
| `workflow_pattern_notes` | `required_static` | Justification referencing DAG structure and P-C patterns. Required for `hybrid`. |

---

## WDD Section 2a: Semantic Description Quality Standards

Applies to every natural language description field — workflow, stage, task, and dataset levels.

Minimum required content: workflow level — scientific problem, domain, inputs, outputs; task level — what it does in domain terms, inputs, outputs, why it exists; dataset level — what the data represents scientifically and which tasks depend on it.

Authoring-time validation: descriptions shorter than 20 words, or containing only generic verbs with no domain nouns, are flagged as quality warnings in Translation Metadata. Flagged descriptions do not block WDD creation.

---

## WDD Section 2: Stage Catalog

**Purpose:** Logical groupings of tasks that achieve a distinct workflow milestone. Stages execute in a defined order; tasks within a stage may run in parallel. Stages give Tier 1 diagnosis agents a coarser reasoning granularity before drilling to task level, and correspond to the stage-level analysis in the IPDPS '26 characterization (e.g., temporal hotspots at specific stages).

| Field | Status | Description |
|-------|--------|-------------|
| `stage_id` | `required_static` | Format: `stage:<descriptor>` (e.g., `stage:simulation`). |
| `name` | `required_static` | Human-readable stage name. |
| `order` | `required_static` | Integer execution order (1-indexed). |
| `description` | `required_static` | What this stage accomplishes in the workflow. |
| `tasks` | `required_static` | List of `task_id` values belonging to this stage. |

---

## WDD Section 3: Task Registry

**Purpose:** The catalog of all tasks. The canonical source of truth for all relationships. The Execution Graph is derived from this section — never edited directly.

| Field | Status | Description |
|-------|--------|-------------|
| `task_id` | `required_static` | Stable snake_case identifier normalized from source code. |
| `name` | `required_static` | Human-readable name. |
| `stage` | `required_static` | `stage_id` this task belongs to. |
| `executable` | `required_static` | Script or binary name (e.g., `openmm_simulation.py`). |
| `description` | `required_static_ask` | 2–4 sentence domain description. What it does, inputs, outputs, why it exists. Quality-validated per Section 2a. |
| `behavioral_notes` | `required_static` | I/O-relevant behaviors from code inspection: reads all input at startup or streams? Writes output incrementally or at end? Internal iteration or checkpointing? Memory patterns (full load vs. chunked)? |
| `parallelism_model` | `required_static` | See parallelism model schema below. |
| `io_dominance` | `required_static` | `compute_bound` \| `io_bound` \| `balanced` \| `unknown`. Agent-inferred; refined by profiling. |
| `output_class` | `required_static_ask` | `intermediate` \| `checkpoint`. Scientist-provided. Cannot be reliably inferred from code. |
| `inputs` | `required_static` | List of `data_id` values this task reads. |
| `outputs` | `required_static` | List of `data_id` values this task writes. |

**Parallelism model schema:**

| Field | Description |
|-------|-------------|
| `type` | `serial` \| `embarrassingly_parallel` \| `data_parallel` \| `task_parallel` |
| `description` | How multiple instances relate. E.g., "Each instance processes one chromosome independently" or "All instances share a global model and synchronize gradients." |

---

## WDD Section 4: Data Object Registry

**Purpose:** Every logical data object flowing through the workflow. These are logical descriptions — not bound to physical paths, formats, or storage tiers (those belong in DDD/IODD).

### Section 4a: Semantic Layer (always required)

| Field | Status | Description |
|-------|--------|-------------|
| `data_id` | `required_static` | Format: `data:<descriptor>`. |
| `name` | `required_static` | Human-readable name. |
| `description` | `required_static_ask` | What this data represents scientifically. Quality-validated per Section 2a. |
| `category` | `required_static` | `input` \| `intermediate` \| `output` \| `checkpoint` \| `config`. Config distinguishes parameter files and run configs from data flowing in the P-C graph. |
| `persistence` | `required_static` | `transient` (within one task) \| `stage_scoped` (within one stage) \| `workflow_scoped` (full run) \| `persistent` (survives across runs). |
| `format_hint` | `required_static` | See format hint schema below. |
| `cardinality` | `required_static` | How many instances exist at runtime. E.g., "one per chromosome (10 total)", "one per simulation task (12 instances)", "single global file." |
| `estimated_size_hint` | `required_static` | Order-of-magnitude size if inferrable from code. Write "unknown" if not determinable. |
| `producer_task` | `required_static` | `task_id` of writing task, or null for external inputs. |
| `consumer_tasks` | `required_static` | List of `task_id` values that read this dataset. |

**Format hint schema:**

| Field | Description |
|-------|-------------|
| `container` | `HDF5` \| `netCDF4` \| `CSV` \| `parquet` \| `tar` \| `plain_binary` \| `text` \| `JSON` \| `unknown` |
| `datasets` | For HDF5/netCDF: list of `{dataset_name, description, dtype, shape_hint}`. Captures dataset-level layout visible in source code. |
| `compression` | `none` \| `gzip` \| `lzf` \| `lz4` \| `zstd` \| `blosc` \| `unknown` |
| `layout_hint` | `contiguous` \| `chunked` \| `unknown` |
| `typical_request_size_kb` | Estimated I/O request size from code inspection. Null if not determinable. |

### Section 4b: Dataset Lifecycle Layer (progressively populated)

Logical lifecycle properties derivable from the DAG. Size fields populated from completed runs. These belong in the WDD — not the IODD — because the DDD generator needs them to make storage tier and cleanup scheduling decisions before any run exists.

| Field | Status | Description |
|-------|--------|-------------|
| `creation_phase` | `required_static` | Which `task_id` completion creates this dataset. Derived from producer_task. |
| `last_consumer_phase` | `required_static` | Latest `task_id` that reads this dataset (last in topological order). |
| `retention_window` | `required_static` | Span between creation_phase and last_consumer_phase. DDD uses this to schedule cleanup for intermediates on volatile tiers. |
| `access_frequency_class` | `required_static` | `once` \| `few_times` \| `repeatedly`. |
| `consumer_count` | `required_static` | Number of distinct consumer task instances in a typical run. |
| `size_measured_bytes` | `required_deploy` | Measured by deployment tooling. Null until first run. |
| `size_measurement_run_id` | `required_deploy` | Run ID of measurement. |
| `size_measurement_confidence` | `required_deploy` | `high` \| `estimated` \| `unavailable` |

---

## WDD Section 5: Producer-Consumer Edges

**Purpose:** Every data dependency between tasks. Distinct from the task-level `inputs`/`outputs` lists — this section encodes the *relationship* between producer and consumer, not just which data objects exist.

| Field | Status | Description |
|-------|--------|-------------|
| `edge_id` | `required_static` | Format: `pc:<producer_task>-><consumer_task>:<pattern>`. |
| `producer` | `required_static` | `task_id` of producing task. |
| `consumer` | `required_static` | `task_id` of consuming task. |
| `data_objects` | `required_static` | List of `data_id` values transferred on this edge. Edges may carry multiple datasets. |
| `pc_pattern` | `required_static` | `1_to_1` \| `1_to_n` \| `n_to_1` \| `n_to_n` |
| `pc_pattern_rationale` | `required_static` | Why this classification. E.g., "All 12 parallel simulation tasks produce trajectory files consumed by a single aggregate task → n_to_1." |
| `data_flow_description` | `required_static` | Prose description of what data moves, how it is accessed (full read, partial read, streamed), and notable characteristics. |
| `coupling` | `required_static` | `tight` \| `loose`. Tight = consumer cannot begin until producer fully completes and data is written. Loose = consumer can begin on partial/streaming output. |
| `coupling_rationale` | `required_static` | Why this coupling classification. |
| `communication_pattern` | `required_static` | `shared_file` \| `file_per_producer` \| `in_memory` \| `streaming_channel`. Workflow-level hint; DDD may override. |
| `data_volume_class` | `required_static` | `small` (< 1 GB) \| `medium` (1–100 GB) \| `large` (> 100 GB). Agent-estimated. |
| `co_scheduling_hint` | `required_static` | `beneficial` \| `neutral` \| `harmful`. Whether co-locating producer and consumer is expected to help. Agent-inferred from pc_pattern and coupling. |

**Note on coupling vs. co_scheduling_hint:** `coupling` is a feasibility constraint derivable from code — it tells the DDD what pipeline strategies are *possible*. `co_scheduling_hint` is an optimization signal — it tells the DDD whether co-location is *beneficial*. Both are needed. Tight coupling with beneficial co-scheduling hint = strong case for co-location. Loose coupling with harmful hint = spread across nodes.

---

## WDD Section 6: Workflow Graph

**Purpose:** Standalone DAG encoding derived from the Task Registry and P-C Edges. Never edited directly.

**Consistency contract:** Carries a SHA-256 integrity hash of all relationships. Any agent detecting a hash mismatch must reject the graph and request regeneration.

| Field | Status | Description |
|-------|--------|-------------|
| `integrity_hash` | `required_static` | SHA-256 of canonical serialization of all pc_edges. |
| `last_generated` | `required_static` | ISO 8601 timestamp. |
| `dag_edges` | `required_static` | `{from, to, via}` objects derived from pc_edges. |
| `loop_groups` | `required_static` | Tasks grouped by shared loop structure, with loop_type and note. |
| `critical_path_hint` | `required_static` | Longest chain of sequential dependencies if determinable from code; "indeterminate from static analysis" otherwise. |
| `control_flow` | `required_static` | `{has_iteration, iteration_description, has_conditional_branches, conditional_description}`. |
| `workflow_pattern_evidence` | `required_static` | Structural features justifying the header `workflow_pattern` classification. |
| `stage_execution_order` | `required_static` | Flat ordered list of `stage_id` values. Agent-navigable shortcut for stage-level reasoning. |

**Cross-reference index** (flat lookup table for agent navigation without full-document traversal):

```yaml
cross_reference:
  task_to_stage:
    "task:<n>": "stage:<n>"
  data_to_producer:
    "data:<n>": "task:<n>"
  data_to_consumers:
    "data:<n>": ["task:<n>", ...]
  stage_execution_order:
    - "stage:<n>"   # in execution order
```

---

## WDD Section 7: I/O Behavioral Hints

**Purpose:** Static-analysis-visible I/O concerns captured as typed, named observations. These are the code-inspection equivalent of DaYu's runtime observations. Capturing them in the WDD gives Tier 1 diagnosis agents a pre-loaded list of suspicions to investigate before any profiling has run.

Each hint has a stable `hint_id` and a typed `potential_concern` drawn from the IPDPS '26 finding vocabulary.

| Field | Status | Description |
|-------|--------|-------------|
| `hint_id` | `required_static` | Format: `hint:<short_name>`. |
| `description` | `required_static` | Observation from code inspection. E.g., "The aggregate task opens all 12 simulation output files sequentially but reads only 3 of 4 HDF5 datasets from each — potential partial file access waste." |
| `affected_tasks` | `required_static` | List of `task_id` values involved. |
| `affected_data` | `required_static` | List of `data_id` values involved. |
| `potential_concern` | `required_static` | Typed classification from controlled vocabulary below. |

**Concern vocabulary:**

| Value | Meaning |
|-------|---------|
| `partial_access` | Task opens a file but reads only a subset of its contents (e.g., DDMD training reads 3 of 4 HDF5 datasets) |
| `format_mismatch` | Layout choice mismatched to access pattern (e.g., chunked HDF5 for small sequentially-accessed files) |
| `small_file_overhead` | Many small files created where a single larger file would suffice |
| `unnecessary_serialization` | Aggregation step exists only to merge files for a single downstream consumer |
| `data_reuse` | Same data read by multiple tasks (inter-task) or re-read by the same task (intra-task) |
| `checkpoint_waste` | Checkpoint files written but rarely/never read in normal execution path |
| `metadata_overhead` | Many datasets per file or many small files causing metadata-heavy I/O |
| `unknown` | Concern is visible but does not fit above categories |

---

## WDD Section 8: Execution Profiles

**Purpose:** Named, valid partial execution subsets representing scientifically meaningful stopping points. Allows operators to run a workflow through a specific checkpoint without running the full pipeline.

| Field | Status | Description |
|-------|--------|-------------|
| `profile_name` | `required_static_ask` | Short identifier (e.g., `tracks_only`, `full`). Proposed by agent from checkpoint tasks; confirmed by scientist. |
| `terminal_task_id` | `required_static` | The last task required for this profile. |
| `description` | `required_static_ask` | What scientific results this profile produces. |
| `required_task_set` | `required_static` | **Auto-derived only** by backward DAG traversal from `terminal_task_id`. Never manually specified. |
| `output_dataset_ids` | `required_static` | Checkpoint datasets produced by tasks in `required_task_set`. |

---

## WDD Section 9: Open Design Decisions

The following fields have two defensible design choices. The trade-offs are documented here to inform the final decision.

### 9a: Loop Annotation Model

**Your design (structured schema):** Loop annotation is a per-task structured object with `loop_type` (static/parameter_sweep/data_driven/convergence), `bound_type`, `convergence_condition`, `max_iterations_guard`, `loop_position`. All fields are typed and machine-comparable.

**Jaime's design (prose in control_flow):** `has_iteration: true/false` plus a free-text `iteration_description` in the workflow graph's `control_flow` block.

**Advantages of your structured schema:** The IODD can compute a boolean `match_wdd_io_phase` against `loop_type`. The DDD can auto-derive parallelism constraints from `convergence` vs. `parameter_sweep`. The `max_iterations_guard` field is a hard safety constraint that cannot be expressed in prose. Capability-constrained local LLMs reason better over typed values than natural language.

**Disadvantages of your structured schema:** Adds complexity. `loop_position` (body/entry_gate/exit_check) is rarely determinable from code without deep analysis; most agents will leave it `unknown`, reducing its value. Convergence conditions in scientific code are sometimes implicit (tolerance checks buried in solver logic) and hard to extract reliably.

**Advantages of Jaime's prose approach:** Simpler. The iteration description prose is more likely to be accurate — an agent is less likely to hallucinate a correct prose description than to misclassify a structured field. Reduces the number of `unknown` fields in practice.

**Disadvantage:** Breaks machine-comparability with IODD temporal observations. Diagnosis agents cannot programmatically detect loop anomalies.

---

### 9b: Temporal I/O Annotation per Task

**Your design:** Per-task structured annotation: `io_phase` (upfront/streaming/deferred/mixed), `burstiness` (bursty/sustained/unknown), `overlap_potential` (high/low/unknown). Agent-inferred; refined by DPM post-run.

**Jaime's design:** `behavioral_notes` free-text field in the task entry covering the same ground (reads all input at startup or streams? writes output incrementally or at end?).

**Advantages of your structured annotation:** Enables the IODD `match_wdd_io_phase` boolean computation — the core anomaly detection signal for Tier 1 diagnosis. DDD pipelining decisions can be auto-generated from `overlap_potential` values. Burstiness feeds storage contention risk scoring.

**Disadvantages:** `burstiness` and `overlap_potential` are frequently `unknown` for workflows without prior profiling. This creates many `unknown` fields that add noise without signal.

**Advantages of Jaime's behavioral_notes:** More likely to be accurate from code inspection alone. A well-written behavioral_notes paragraph captures nuance that three categorical fields may lose (e.g., "reads all input upfront except for config reloads on iteration boundaries").

**Disadvantages:** behavioral_notes cannot be machine-compared to IODD observations. Diagnosis agents must parse prose to detect anomalies, which is unreliable at scale.

---

### 9c: `contention_sensitivity` per task

**Your design:** Per-task field `contention_sensitivity: high | medium | low | unknown`. Agent-inferred from io_dominance and access pattern; confirmed by profiling.

**Jaime's design:** Not present. Contention risk is implied by io_dominance and the P-C edge patterns.

**Advantages of your field:** Gives the DDD a direct signal for tier assignment risk — a `high` contention_sensitivity task should be isolated on a dedicated tier. Saves the DDD agent from re-deriving this from io_dominance + pc_pattern on every DDD generation.

**Disadvantages:** Almost always `unknown` before first profiling run, which reduces its signal value in the initial DDD. Adds a field that agents will fill with `unknown` by default and rarely update.

**Advantages of omitting:** Cleaner schema. The DDD can derive an equivalent signal from `io_dominance = io_bound` + `pc_pattern = n_to_n` without a redundant field.

---

### 9d: Dataset Lifecycle Layer (Section 4b)

**Your design:** Structured lifecycle fields in the WDD: `creation_phase`, `last_consumer_phase`, `retention_window`, `access_frequency_class`, `consumer_count`, `size_measured_bytes`.

**Jaime's design:** `persistence` field on data objects (transient/stage_scoped/workflow_scoped/persistent) plus `cardinality` prose.

**Advantages of your lifecycle layer:** Gives the DDD generator precise cleanup scheduling data — it knows exactly when the last consumer finishes (last_consumer_phase) and can schedule burst buffer deallocation at that point. `retention_window` expressed as a DAG span is hardware-agnostic and directly actionable. This is the core design insight from the DataLife paper (SC '23): lifecycle-aware scheduling is what enables the 15× speedup.

**Disadvantages:** `creation_phase` and `last_consumer_phase` are redundant with the DAG topology — a sufficiently capable agent can derive them from pc_edges. Adds fields that are auto-computable rather than genuinely new information.

**Advantages of Jaime's persistence field:** Simpler. `stage_scoped` vs. `workflow_scoped` communicates the essential intent. Combined with `cardinality`, the DDD has enough to make tier assignments.

**Disadvantage:** `stage_scoped` doesn't tell the DDD *when* within the stage cleanup is safe. For volatile-tier management, "stage ends" is too coarse — on a 12-hour stage, freeing burst buffer space when the last consumer finishes (not when the stage ends) could free hours of capacity.

---

### 9e: Translation Metadata and Confidence Records

**Your design:** Structured `translation_metadata` section with `unmapped_fields`, `round_trip_gaps`, `quality_warnings`, and `field_confidence_records` (one record per agent-inferred field: field_path, filled_by, confidence_level, confidence_reason, requires_human_review).

**Jaime's design:** Inline `[ASSUMPTION]` prefix on any field value that required guesswork. Simpler but not machine-parseable.

**Advantages of your structured records:** Programmatically auditable — a downstream tool can query "show me all low-confidence fields that require human review" without parsing every field value. Confidence records accumulate across WDD versions, showing which fields improved after profiling.

**Disadvantages:** Significant overhead. For a 30-task workflow with 60 inferred fields, the confidence records section can be longer than the rest of the WDD combined. Many capability-constrained local LLMs will fill confidence records poorly — writing `high` everywhere to avoid effort.

**Advantages of Jaime's [ASSUMPTION] prefix:** Zero overhead. An agent reviewing a WDD can grep for `[ASSUMPTION]` and get an instant list. Low chance of hallucination — either the prefix is there or it isn't.

**Disadvantages:** Not machine-sortable by confidence level. No way to track which agent made the inference or when. Cannot distinguish "low confidence in this specific number" from "could not determine this field at all."

---

## WDD Section 10: Translation Metadata

Full provenance of how this WDD was produced. Populated at generation time.

| Field | Status | Description |
|-------|--------|-------------|
| `source_format` | `required_static` | Source workflow format. |
| `source_file` | `required_static` | Primary workflow definition file. |
| `translation_tool` | `required_static` | Agent name and version. |
| `translation_timestamp` | `required_static` | ISO 8601 timestamp. |
| `unmapped_fields` | `required_static` | Fields that could not be populated from source, with reasons. Empty list is valid. |
| `round_trip_gaps` | `required_static` | Fields that would be lost if this WDD were compiled back to source format. |
| `quality_warnings` | `required_static` | Description fields flagged by quality validation (< 20 words or no domain nouns). |
| `field_confidence_records` | `required_static` | One record per agent-inferred field: `{field_path, filled_by, confidence_level (high\|medium\|low\|inferred), confidence_reason, requires_human_review}`. See Section 9e for design trade-offs. |

---

## WDD Population Sources

| WDD Content | Source |
|-------------|--------|
| Stage and task list, names, executables | Static analysis of workflow orchestration files |
| Task dependency graph | Format-specific extraction (see Generation Procedure table) |
| P-C edge patterns and coupling | DAG topology analysis + code inspection |
| Workflow-level pattern | Agent derivation from DAG + loop structure |
| Parallelism model per task | Code structure (for loops, scatter, MPI calls, job arrays) |
| I/O behavioral hints | Code re-read targeting partial access, format, serialization patterns |
| Semantic descriptions | AI inference from docstrings, function names, comments |
| `io_dominance` | AI inference from code; refined by profiling |
| `behavioral_notes` | AI inference from I/O call patterns in task source |
| `format_hint` (container, datasets, compression, layout) | File inspection / h5py or netCDF4 code analysis |
| `typical_request_size_kb` | Code analysis; null if not determinable |
| Dataset role, cardinality, size hint | DAG structure + code inspection |
| Dataset lifecycle (creation_phase, retention_window) | Derived from DAG topology |
| `size_measured_bytes` | Measured by deployment tooling or completed run |
| Execution profiles | Proposed by agent from checkpoint tasks; confirmed by scientist |
| `output_class` | Scientist-provided |
| `source_commit` | Git metadata |

---

## WDD Validation Checklist

After generation, validate:

1. **Completeness** — every file read/written in the codebase is represented as a data object
2. **Consistency** — every `data_id` in task inputs/outputs appears in data object registry; every `task_id` in pc_edges appears in task registry
3. **Pattern accuracy** — P-C pattern classifications match actual producer/consumer cardinalities
4. **No deployment leakage** — WDD contains zero references to hardware, storage tiers, node counts, or performance targets
5. **Cross-reference integrity** — cross_reference index matches body content
6. **Stage ordering** — `stage_execution_order` matches DAG dependencies
7. **Integrity hash** — `execution_graph.integrity_hash` is current
8. **Assumption transparency** — every assumption is marked `[ASSUMPTION]` in its field value AND has a confidence record

---

## WDD Corner Cases

The following scenarios require special handling during WDD generation.

**Multi-dataset edges.** A single P-C edge may carry multiple data objects simultaneously (e.g., the openmm→aggregate edge in DeepDriveMD transfers four HDF5 datasets in one file). The `data_objects` field on pc_edges is a list — use it. Do not create one edge per dataset when a single task relationship transfers all of them.

**Config/parameter objects.** Configuration files (JSON params, YAML run configs, input parameter files) are real data objects that tasks read but that do not participate in the scientific P-C data flow. Use `category: config` to distinguish these from `input` data. This prevents agents from modeling config files as intermediate data to be staged or cleaned up.

**Conditional patterns.** Workflows where tasks only execute if a runtime condition is met (data quality checks, convergence tests) should use `workflow_pattern: conditional` or include `conditional` in `secondary_patterns` for hybrid workflows. Document the branching logic in `control_flow.conditional_description`.

**Partial file access.** When a task opens a file but reads only a subset of its datasets (e.g., DDMD training reads point_cloud/fnc/rmsd but not contact_map), always create an `io_behavioral_hints` entry with `potential_concern: partial_access`. This is the most commonly missed finding in static analysis — requires reading both the file-creation code and the file-reading code side-by-side.

**Broadcast patterns.** When a single producer's output is consumed by many downstream tasks that each read the full dataset (not a partitioned subset), this is `pc_pattern: 1_to_n` with `potential_concern: data_reuse` in hints. Distinguish from scatter (1_to_n where each consumer reads a different partition of the data).

---


---

# Part II: Goal Document (GD)

## GD Purpose

The GD captures the operator's performance objectives and constraints that motivate a particular deployment strategy. It encodes *intent* — why the operator chose a particular configuration. Every decision in the DDD must back-reference a GD goal ID. Without the GD, deployment decisions are opaque; a prescription agent cannot evaluate whether a recommendation is aligned with what the operator actually wants.

The GD is a side input to the WDD → DDD step. It does not describe the workflow, the hardware, or the deployment — it describes what success looks like for this run.

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
| `wdd_lineage_id` | The `workflow_lineage_id` this GD applies to. A GD is always scoped to a specific workflow. |
| `wdd_version` | The WDD version this GD was authored against. |
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
| `applies_to` | Which WDD entities this constraint applies to — a `task_id`, `dataset_id`, or `all`. |
| `rationale` | Why this constraint exists (e.g., "checkpoint files must survive node failure; burst buffer is not fault-tolerant on this system"). |

---

## GD Example

```yaml
gd_id: "gd:storm_tracking:production_cmip7"
wdd_lineage_id: "f3a9c2e1-847b-4d02-b6f1-2c3d4e5f6a7b"
wdd_version: "1.0.0"
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

The DDD defines how a workflow is deployed to achieve a specific set of goals on specific hardware. It is the execution strategy layer — bridging the logical workflow structure (WDD) with the physical constraints (HRD) in pursuit of the operator's objectives (GD).

Every decision in the DDD is motivated by a GD goal and constrained by HRD capacity. The DDD makes this motivation explicit through `goal_ref` back-references on every decision field. This is what makes the DDD the primary document a prescription agent consults when evaluating whether a recommendation is feasible and aligned with operator intent.

A single WDD can have multiple DDDs representing different deployment strategies (e.g., throughput-optimized, cost-optimized, latency-optimized). Each DDD is a self-contained, versioned document.

---

## DDD Design Principles

| Principle | Description |
|-----------|-------------|
| **Decision + motivation** | Every deployment decision records both what was decided and which GD goal motivated it. Decisions without `goal_ref` are flagged as incomplete. |
| **Hardware-referenced** | Storage tier assignments and compute resource choices reference HRD IDs, not hardcoded names. |
| **WDD-version-pinned** | Every DDD pins to a specific WDD version and HRD version. If either changes, the DDD must be re-validated. |
| **One-to-many** | A single WDD can have multiple DDDs. Each represents a distinct deployment strategy. |
| **Agent-generatable** | The DDD is the primary document an AI prescription agent produces when given a WDD + GD + HRD. |

---

## DDD Section 1: DDD Header

| Field | Description |
|-------|-------------|
| `ddd_id` | Stable identifier. Format: `deploy:<wdd_lineage_id>:<strategy_name>`. |
| `strategy_name` | Short label for this deployment strategy (e.g., `throughput_optimized`, `cost_optimized`). |
| `wdd_lineage_id` | The WDD this DDD is derived from. |
| `wdd_version` | The specific WDD version this DDD was generated against. Must be re-validated if WDD version changes. |
| `hrd_id` | The HRD this DDD targets. |
| `hrd_version` | The specific HRD version. |
| `gd_id` | The GD that motivated this deployment strategy. |
| `execution_profile` | Which WDD execution profile this DDD is designed for (e.g., `profile:full`). |
| `generated_by` | Agent or human operator that produced this DDD. |
| `generated_at` | Timestamp. |
| `description` | Plain-language summary of this deployment strategy and its primary tradeoffs. |

---

## DDD Section 2: Per-Task Parallelism

One entry per task in the WDD Task Registry.

| Field | Description |
|-------|-------------|
| `task_id` | References `task:<name>` from the WDD. |
| `parallelism_instances` | Number of concurrent task instances. |
| `ranks_per_instance` | MPI ranks (or equivalent) per task instance. |
| `threads_per_rank` | OpenMP threads (or equivalent) per rank. |
| `compute_resource` | `compute_id` from HRD (e.g., `compute:gpu_node`). |
| `goal_ref` | `goal_id` from GD that motivated this parallelism choice. |
| `rationale` | Plain-language explanation of why this parallelism was chosen. |

---

## DDD Section 3: Storage Tier Assignments

One entry per dataset in the WDD Data Flow Layer.

| Field | Description |
|-------|-------------|
| `dataset_id` | References `data:<name>` from the WDD. |
| `assigned_tier` | `tier_id` from HRD. |
| `cleanup_policy` | `after_last_consumer` \| `end_of_job` \| `retain_indefinitely`. For intermediate datasets, the DDD may schedule cleanup based on WDD `retention_window`. |
| `replication` | Whether this dataset is replicated for fault tolerance. Boolean. |
| `caching_policy` | `none` \| `cache_on_first_read` \| `prefetch`. Relevant for datasets read multiple times (informed by WDD `access_frequency_class`). |
| `goal_ref` | `goal_id` motivating this tier assignment. |
| `rationale` | Why this tier was chosen (e.g., "large intermediate dataset; burst buffer provides sufficient bandwidth and capacity, reducing PFS contention"). |
| `feasibility_check` | Whether the HRD tier has sufficient capacity and bandwidth for this dataset. `pass` \| `warning` \| `fail`. Computed from WDD `size_measured_bytes` and HRD `per_job_capacity_tb`. |

---

## DDD Section 4: Task Placement and Co-scheduling

| Field | Description |
|-------|-------------|
| `group_id` | Identifier for this placement group. |
| `tasks` | List of `task_id` values that should be co-located or co-scheduled. |
| `placement_policy` | `co_locate` (same node or node group) \| `spread` (distribute across nodes) \| `no_constraint` |
| `co_schedule` | Whether these tasks should overlap in time. Boolean. |
| `goal_ref` | `goal_id` motivating this placement decision. |
| `rationale` | Typically references WDD `co_scheduling_hint` on the relevant P-C edges. |

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
| **Cross-referenceable** | References WDD, DDD, and HRD IDs throughout so any observed I/O characteristic can be traced to the workflow structure, deployment decision, and hardware tier that produced it. |

---

## IODD Section 1: IODD Header

| Field | Description |
|-------|-------------|
| `iodd_id` | Stable identifier. Format: `iodd:<ddd_id>:<run_id>`. |
| `ddd_id` | The DDD that was executed. |
| `hrd_id` | The HRD on which execution occurred. |
| `wdd_lineage_id` | Back-reference to the originating WDD. |
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
| `task_id` | References `task:<name>` from WDD. |
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
| `io_phase_observed` | `upfront` \| `streaming` \| `deferred` \| `mixed`. Compared to WDD `temporal_io_annotation.io_phase` to detect anomalies. |
| `compute_to_io_ratio` | Fraction of task wall time spent in I/O. |
| `contention_events` | Number of detected contention events (lock waits, bandwidth throttling). |
| `dpm_trace_ref` | Reference to the DPM trace file or database entry. |

---

## IODD Section 3: Communication Channel Definitions

One entry per P-C edge in the WDD Execution Graph that was active in this run.

| Field | Description |
|-------|-------------|
| `pc_edge_id` | References `pc:<producer>-><consumer>:<pattern>` from WDD. |
| `physical_path` | How data actually moved: `shared_file_on_pfs` \| `staged_through_burst_buffer` \| `node_local_transfer` \| `in_memory_mpi` \| `streaming_pipe` |
| `tier_id` | `tier_id` from HRD where this data resided during transfer. |
| `data_volume_bytes` | Total bytes transferred on this channel. |
| `transfer_bandwidth_gbs` | Achieved bandwidth on this channel. |
| `transfer_time_s` | Wall time for the full data transfer on this channel. |
| `transfer_pattern` | `bulk_sequential` \| `fine_grained_random` \| `chunked_streaming` |
| `match_ddd` | Whether the physical path matches the DDD's storage tier assignment for this dataset. Boolean. Mismatches flag for investigation. |

---

## IODD Section 4: Data Format Observations

Per-dataset format details observed at runtime, supplementing the WDD `format_internals` with empirical confirmation or corrections.

| Field | Description |
|-------|-------------|
| `dataset_id` | References `data:<name>` from WDD. |
| `actual_file_format` | What was actually observed (may differ from WDD declaration if format conversion occurred). |
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
| `match_wdd_io_phase` | Whether observed `io_phase` matched WDD `temporal_io_annotation.io_phase`. Boolean. Mismatches flag for WDD update. |

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
| `dataset_id` | References `data:<name>` from WDD. |
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
| `match_wdd_retention` | Whether actual lifetime matches WDD `retention_window` expectation. Boolean. |

---

## IODD Section 8: Diagnosis Summary

A machine-readable diagnosis of the run's I/O behavior, structured to directly feed Tier 1 diagnosis agents.

| Field | Description |
|-------|-------------|
| `overall_io_pattern` | The observed workflow-level I/O pattern: `pipeline` \| `scatter_gather` \| `iterative` \| `cascading` \| `hybrid`. Should match WDD `workflow_pattern` if the deployment behaved as designed. |
| `pattern_match_wdd` | Whether observed I/O pattern matches WDD `workflow_pattern`. Mismatch is a significant diagnostic signal. |
| `bottleneck_summary` | List of identified bottlenecks: `{task_id or tier_id, bottleneck_type, severity: high/medium/low, description}`. |
| `optimization_opportunities` | List of potential optimizations surfaced from the data: `{opportunity_type, affected_entities, estimated_impact, evidence}`. |
| `anomalies` | Fields where observed values diverged significantly from WDD annotations or DDD decisions, warranting investigation. |

---

---

# Cross-Document Summary

## Document Structure at a Glance

```
WDD  (what the workflow IS — stable, hardware-agnostic, deployment-agnostic)
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
├── Header: gd_id, wdd_lineage_id, operator
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

DDD  (how the workflow is DEPLOYED — references WDD + GD + HRD)
│
├── Header: ddd_id, wdd_version, hrd_version, gd_id, execution_profile
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
│   match_wdd_io_phase
├── Contention and Interference: tier_id, degradation_factor, affected_tasks
├── Per-File Lifecycle: dataset_id, created/read/deleted timestamps,
│   idle_time, lifetime, match_wdd_retention
└── Diagnosis Summary: overall_io_pattern, bottleneck_summary,
    optimization_opportunities, anomalies
```

---

## What Each Document Requires

| Document | Inputs Required to Generate |
|----------|-----------------------------|
| WDD | Workflow source code file + scientist answers one question (output_class per task) |
| GD | Operator objectives + facility SLA |
| HRD | System documentation + hardware profiling benchmarks |
| DDD | WDD + GD + HRD |
| IODD (empirical) | Completed run with profiling tools (DataLife, DaYu, Darshan) + DDD + HRD |
| IODD (predictive) | DDD + HRD + agent reasoning |

---

## Appendix: Changes from v3

| Area | Change |
|------|--------|
| Scope of document | Extended from WDD-only to full five-document architecture. WDD content unchanged from v3. |
| GD (Goal Document) | **Fully specified.** Header, Goals with typed fields and priority ordering, Conflict Resolution Policy, Hard Constraints, YAML example. |
| HRD (Hardware Resource Document) | **Fully specified.** Header, Compute Topology with `compute_id`, Network Fabric with `interconnect_id`, Storage Hierarchy with `tier_id` and Contention Model per tier, Empirical Benchmarks section. |
| DDD (Deployment Definition Document) | **Fully specified.** Header with WDD + HRD + GD version pins, Per-Task Parallelism with `goal_ref` on every field, Storage Tier Assignments with feasibility checks against HRD, Task Placement and Co-scheduling, Pipelining Decisions, Replication/Caching Strategy, Validation Summary. |
| IODD (I/O Definition Document) | **Fully specified.** Header with `predictive` flag, Per-Task I/O Profile with full POSIX metrics and phase comparison to WDD, Communication Channel Definitions per P-C edge, Data Format Observations, Temporal I/O Behavior, Contention and Interference model, Per-File Lifecycle (DataLife-style), Diagnosis Summary for Tier 1 agents. |
| Cross-reference ID convention | **Formalized.** All five documents share a common ID namespace. `task:`, `data:`, `pc:`, `tier:`, `compute:`, `goal:`, `deploy:`, `iodd:` prefixes defined. |
| Agent context scoping table | **Added.** Maps each agent tier (Diagnosis, Prescription, Orchestration) to its primary documents with rationale. |
| Generation pipeline | **Extended.** Steps 1–5 with emphasis on step 4 (DDD generation) as the primary AI agent value-add point. |

---

---

# Appendix: Design Comparison Notes (v5 vs. Jaime's WDD)

This appendix records what your v4 WDD design has that Jaime's WDD does not cover. These items are either already incorporated into v5 (marked ✅) or remain open decisions (marked 🔲 in Section 9).

## Items from Your v4 Not in Jaime's Design

**1. Field-status model and agent readiness gate** ✅
Incorporated into v5 WDD Field Status Model section. The `_status` annotation system (required_static, required_static_ask, required_deploy, optional_enrichment) and the readiness gate checklist have no equivalent in Jaime's design, which uses `[ASSUMPTION]` prefixes but provides no population protocol or escalation path for fields that cannot be extracted from code.

**2. Versioning and immutability model** ✅
Incorporated into v5 Section 1 (Workflow Header). The `workflow_lineage_id` + semantic versioning + `deprecated` flag + `version_notes` changelog have no equivalent in Jaime's `wdd_version: "1.0"` single field. Critical for companion document (DDD, IODD) version pinning.

**3. Loop annotation model (Section 2b)** 🔲
See Section 9a for design trade-offs. Not yet incorporated — awaiting your decision on structured schema vs. prose.

**4. Temporal I/O annotation per task (Section 2c)** 🔲
See Section 9b for design trade-offs. Not yet incorporated — awaiting your decision.

**5. `contention_sensitivity` per task** 🔲
See Section 9c for design trade-offs. Not yet incorporated — awaiting your decision.

**6. `format_internals` (your design) vs. `format_hint` (Jaime's design)** ✅
Resolved by combining both. v5 Section 4a uses Jaime's `format_hint` structure (with `datasets` sub-entries carrying `dataset_name`, `dtype`, `shape_hint` — richer at the dataset level) plus your `typical_request_size_kb` field (request size hint missing from Jaime). The `compression` and `layout_hint` fields were present in both designs.

**7. Dataset Lifecycle Layer (Section 4b)** 🔲
See Section 9d for design trade-offs. The lifecycle layer is included in v5 Section 4b. Awaiting your decision on whether to keep the full structured layer or simplify to Jaime's `persistence` + `cardinality`.

**8. Execution profiles** ✅
Incorporated into v5 Section 8. No equivalent in Jaime's design.

**9. Translation metadata and field-level confidence records** 🔲
See Section 9e for design trade-offs. Translation metadata is included in v5 Section 10 with both approaches documented. Awaiting your decision on structured confidence records vs. inline `[ASSUMPTION]` prefixes.

**10. Multi-format extraction instructions** ✅
Incorporated into v5 Generation Procedure section as a format-specific extraction table (Nextflow, Pegasus DAX, Parsl, Slurm, Snakemake, Swift/T).

## What Jaime Added That Was Missing from Your v4 (now in v5)

**Stage Catalog** — Explicit stage grouping with `stage_id`, `order`, and task membership list. Added as v5 Section 2. Adds `stage_execution_order` to the cross-reference index and `stage` field to each task.

**`coupling` on P-C Edges** — `tight` vs. `loose` with rationale. Added to v5 Section 5. Complements `co_scheduling_hint`: coupling is a feasibility constraint (what is *possible*); co_scheduling_hint is an optimization signal (what is *beneficial*).

**`io_behavioral_hints` Section** — Typed, named static-analysis observations with controlled `potential_concern` vocabulary. Added as v5 Section 7. Directly maps to findings from hpc_workflow_io paper. Gives Tier 1 agents pre-loaded suspicions before profiling.

**Cross-reference index** — Flat machine-readable lookup: task_to_stage, data_to_producer, data_to_consumers, stage_execution_order. Added to v5 Section 6. Removes multi-hop traversal cost for capability-constrained LLMs.

**`parallelism_model` on tasks** — `type` (serial/embarrassingly_parallel/data_parallel/task_parallel) + description. Added to v5 Section 3. Derivable from code; directly informs DDD generation.

**`source_commit`** — Git commit hash in header. Added to v5 Section 1.

**`config` category for data objects** — Distinguishes parameter files from P-C data flow objects. Added to v5 Section 4a `category` field.

**Claude Code generation procedure** — 7-step analysis procedure operationalizing WDD generation. Added as v5 Generation Procedure section.

## Corner Cases Added from Comparison

Added to v5 WDD Corner Cases section: multi-dataset edges, config/parameter objects, conditional patterns, partial file access detection, and broadcast vs. scatter distinction.