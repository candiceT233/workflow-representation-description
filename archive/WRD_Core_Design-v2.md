# Workflow Representation Document (WRD) — Core Design v2

## Goal

The Workflow Representation Document (WRD) is a structured, AI-readable format for describing scientific workflows in HPC environments. Its primary goals are:

1. **Bridge the expertise gap** — Allow domain scientists (physicists, biologists, climate scientists) to describe their workflows without needing knowledge of parallelism, node memory, storage tiers, or HPC system internals. The WRD captures what the scientist *knows* and separates it from deployment decisions that require HPC expertise.

2. **Enable AI-assisted deployment and diagnosis** — Provide AI agents with enough structured, semantic context to autonomously deploy workflows (via tools like Jarvis-MCP), diagnose I/O bottlenecks, and recommend optimizations — even when running on capability-constrained local LLMs in secure HPC environments.

3. **Serve as a universal interchange format** — Allow AI agents to compile WRDs from existing workflow formats (Pegasus DAX, Slurm scripts, XML pipelines, etc.) and to convert WRDs back into those formats. The WRD is the common language between workflow systems.

4. **Scale to concurrent multi-agent use** — Support thousands of workflow instances running simultaneously, with many agents reading and writing WRDs concurrently, through a design that is modular, cacheable, index-friendly, and consistency-safe.

---

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Scientist-first** | Scientists fill in what they know; HPC-specific fields are optional or agent-filled. Data sizes are never manually entered — they are measured automatically by tooling. |
| **Versioned immutability** | The WRD template is semantically immutable at a given version. Changes produce new versions under the same workflow lineage ID. Deployment plans pin to a specific version. |
| **Separation of concerns** | Workflow definition, I/O characteristics, deployment constraints, and run-time state are distinct layers that can be read and written independently. |
| **AI readability** | Every structural component includes a natural language description field with defined quality standards. Vague descriptions are flagged at authoring time. |
| **Portability** | Can be compiled from or exported to Pegasus, Slurm, XML, and other formats. Translation gaps are recorded explicitly with field-level confidence scores. |
| **Scalability** | Modular structure allows partial loading; stable sections are cacheable across agents. Concurrent writes to different sections are safe; concurrent writes to the same section use optimistic locking. |
| **Auditability** | Every non-scientist-authored field records who or what filled it in, when, and with what confidence. No field is silently empty. |

---

## Core Components

---

### 1. Workflow Header

**What it is:** Top-level identity, provenance, and versioning metadata for the workflow.

**Key fields:**
- `workflow_lineage_id` — A stable UUID assigned at first authoring. Never changes across versions. This is the identity of the workflow concept, not a specific version.
- `version` — Semantic version string (e.g., `2.1.0`). Incremented by the author on any change to the template. Deployment plans pin to a specific version.
- `version_notes` — Human-readable changelog entry explaining what changed from the previous version. Required when version is incremented.
- `deprecated` — Boolean. If true, agents must not use this version for new deployments.
- `workflow_name` — Human-readable name.
- `workflow_description` — Scientist-authored description of what this workflow does. See Section 2a for quality standards.
- `source_format` — How this WRD was produced: `native`, `compiled_from_pegasus`, `compiled_from_slurm`, etc.
- `schema_version` — WRD schema version this document conforms to.
- `author`, `created_at`, `last_modified_at`

**Why versioning belongs here:** Scientific workflows evolve. A design that treats the template as simply "immutable" will either be routinely violated in practice or create friction that causes scientists to work around the format entirely. The versioning model resolves this by distinguishing between the *workflow lineage* (what the workflow is, identified by `workflow_lineage_id`) and a *specific snapshot* of it (identified by `workflow_lineage_id` + `version`).

A deployment plan that pins to lineage `abc123` at version `2.1.0` continues to work correctly even after the scientist publishes `2.2.0`. Agents reading the WRD for a running deployment are always reading a specific, frozen snapshot. The `deprecated` flag allows old versions to be cleanly retired without breaking in-flight runs.

---

### 2a. Semantic Description Quality Standards

**What it is:** Authoring-time standards that apply to every natural language description field in the WRD — both at the workflow level and the task level.

These descriptions are the most load-bearing fields in the WRD. The quality of these fields directly determines how useful agents can be. A description like "runs the simulation" gives an agent almost nothing to work with, and there is no profiling data or graph structure that can substitute for missing semantic context.

**Minimum required content:**
- For workflow-level descriptions: what scientific problem is being solved, what domain it belongs to, what inputs it starts from, and what outputs it ultimately produces.
- For task-level descriptions: what the task does in domain terms, what it takes as input, what it produces as output, and why it exists in the workflow (what would be missing if it were skipped).

**Authoring-time validation:**
- Descriptions shorter than 20 words are flagged as likely insufficient.
- Descriptions containing only generic verbs with no domain nouns (e.g., "processes data", "runs computation") are flagged as non-informative.
- Flagged descriptions do not block WRD creation but are recorded in the Translation Metadata Block as quality warnings that agents and operators can inspect.

**Example:**

> *Insufficient:* "Runs the filter step."
>
> *Good:* "Filters raw genomic reads by Phred quality score (threshold Q20), discarding reads with more than 10% low-quality bases. Takes raw FASTQ files from the sequencer output task and produces clean FASTQ files consumed by the alignment task. Without this task, the alignment step produces a high rate of spurious mappings."

---

### 2. Task Registry

**What it is:** The catalog of all tasks in the workflow. Each task entry is a self-contained unit of semantic meaning. Structural relationships are also represented in the Execution Graph (Section 3); the two are intentionally redundant, with the Task Registry as the canonical source of truth.

**Key fields per task:**
- `task_id` — Unique identifier within this WRD version.
- `task_name` — Human-readable name.
- `semantic_description` — Natural language description meeting the quality standards in Section 2a. Author-provided.
- `executable_ref` — Script or executable reference.
- `task_type` — Classification: `compute`, `I/O`, `preprocessing`, `postprocessing`, `checkpoint`
- `output_class` — `intermediate` or `checkpoint` (see Section 6)
- `relationships` — Typed edges to other tasks:
  - `depends_on` — strict ordering dependency
  - `data_dependency` — this task consumes output produced by another task; implies `depends_on` but carries additional I/O semantics
  - `optional_after` — can run after but does not strictly require
- `loop_annotation` — if the task participates in an iterative structure; see Section 2b

**Why:** The semantic description field is where domain knowledge lives at the task level — this is what bridges the scientist's understanding and the AI agent's reasoning. Typed relationships give Jarvis-MCP and diagnostic agents richer information than a plain DAG edge.

---

### 2b. Loop Annotation Model

**What it is:** A structured, typed annotation for any task that participates in an iterative loop. This is one of the most consequential fields in the Task Registry — agents that do not correctly understand loop structure will misinterpret execution order, generate incorrect Slurm job arrays, and misdiagnose data dependency failures.

**Fields:**

| Field | Description |
|-------|-------------|
| `loop_id` | Unique identifier for this loop structure. Multiple tasks share a `loop_id` if they are all inside the same loop body. |
| `loop_type` | `static`, `parameter_sweep`, `data_driven`, or `convergence`. See definitions below. |
| `bound_type` | `fixed_count`, `runtime_determined`, `parameter_set_size`, or `convergence_criterion` |
| `fixed_count` | Integer. Only present when `bound_type = fixed_count`. |
| `parameter_ref` | Reference to the parameter or dataset that determines loop count. Only present when `bound_type = parameter_set_size`. |
| `convergence_condition` | Human-readable description of the termination condition. Required when `loop_type = convergence`. E.g., "iterate until L2 residual norm drops below 1e-6 or 500 iterations are reached, whichever comes first." |
| `max_iterations_guard` | Integer. A hard upper bound to prevent runaway loops. Required when `loop_type = convergence`. |
| `loop_position` | `body`, `entry_gate`, or `exit_check` — which role this task plays within the loop. |

**Loop type definitions:**

| Loop Type | Description |
|-----------|-------------|
| `static` | Loop count is known at workflow-authoring time and does not change between runs. |
| `parameter_sweep` | Loop count equals the number of items in a named parameter set (e.g., one iteration per input file, per simulation timestep value, or per ensemble member). |
| `data_driven` | Loop count is determined at runtime by the size or structure of input data and is not known until that data is inspected. |
| `convergence` | Loop continues until a scientific criterion is satisfied. Count is unknown at start; `convergence_condition` and `max_iterations_guard` are both required. |

**Why this level of specification is necessary:** A plain loop bounds field is insufficient for anything but static loops. Consider a climate ensemble workflow that runs one simulation per ensemble member: an agent building a Slurm job array needs to know the loop is `parameter_sweep` type tied to the `ensemble_members` parameter — not a fixed count of 50. If next month the ensemble size changes to 80, the agent must recompute the array size from the parameter, not from a hardcoded number.

Convergence loops are the most hazardous case. Without a `max_iterations_guard`, an agent cannot protect the HPC system from a runaway workflow. Without a human-readable `convergence_condition`, a diagnostic agent has no basis for determining whether a workflow that ran 500 iterations terminated normally or hit the guard. Both fields are required when `loop_type = convergence`.

---

### 3. Execution Graph

**What it is:** A standalone, explicit encoding of the workflow DAG — nodes are task IDs, edges carry the relationship type from the Task Registry.

**Why this is a separate section from the Task Registry:** At scale, tools that compile to Pegasus, Slurm, or Jarvis pipelines need only the graph structure, not the full task descriptions. Keeping the graph explicit avoids requiring full document traversal for structural queries and allows it to be indexed and cached independently. It is intentionally redundant with the Task Registry — that redundancy is a feature, not a flaw.

**Consistency model:** The Task Registry is the canonical source of truth for relationships. The Execution Graph is a derived projection and must never be edited directly. It is regenerated automatically whenever the Task Registry is modified, as part of the version-increment process.

To enforce this, the Execution Graph carries an **integrity hash** of the Task Registry's relationship section. Any agent that reads the Execution Graph and detects a hash mismatch must refuse to use it and must alert the author that re-generation is required. When a WRD is compiled from an external format, the compiler populates both sections in a single atomic operation.

This resolves a gap in v1, which described redundancy as desirable but provided no resolution strategy when the two sections diverge.

---

### 4. Data Flow Layer (Three-Level)

**What it is:** Per-task I/O declarations at three levels. The addition of a Measured I/O Layer in v2 removes the prior design's dependence on scientist-provided data size estimates, which are often unavailable or unreliable.

#### Level 1 — Semantic I/O Layer (always required, author-provided)

Captures the meaning of data exchange:
- Named dataset identifier
- What the data represents (scientist-authored description meeting Section 2a standards)
- File format (HDF5, NetCDF, CSV, binary, etc.)
- Role: `input`, `output`, `intermediate`, `checkpoint`
- Producer task ID and consumer task ID(s)

#### Level 2 — Measured I/O Layer (auto-populated by deployment tooling, not the scientist)

This layer captures concrete data sizes as measured by tooling — not estimated by the scientist. It replaces the v1 "estimated input data size" and "estimated output data size" scientist-authored fields, which were impractical because scientists generally do not know these numbers, especially for first-run workflows or workflows that scale nonlinearly with input parameters.

| Field | Source |
|-------|--------|
| `input_data_bytes` | Measured by the deployment tool (e.g., Jarvis-MCP) by inspecting the actual input dataset before the run begins. Null and flagged as unresolved if inputs are not yet available. |
| `output_data_bytes_per_profile` | Measured from a prior completed run for each execution profile. Null on first run; populated after the first successful execution. |
| `measurement_run_id` | ID of the run from which measurements were taken. |
| `measurement_timestamp` | When the measurement was taken. |
| `measurement_confidence` | `high` (direct measurement), `estimated` (extrapolated from smaller runs), or `unavailable` (no prior run, no accessible input) |

The `measurement_confidence` field is critical: agents must handle the `unavailable` case explicitly, which typically means reserving conservative storage estimates and alerting the operator before deployment proceeds. An agent that silently ignores a null data size and proceeds with storage allocation is more dangerous than one that halts and asks.

#### Level 3 — Physical I/O Layer (optional, from profiling tools like DaYu)

Captures observed low-level characteristics from profiling runs:
- Bytes read/written per task
- Access pattern type: sequential, random, strided
- Operation counts (read/write)
- Observed bandwidth
- POSIX timing breakdowns

This layer requires an actual profiling run and is optional. It also directly enables ablation studies in WIDGET — the physical layer can be exposed or hidden independently to test how much AI agents rely on it.

---

### 5. Execution Profiles

**What it is:** Named, valid partial execution subsets of the workflow DAG, declared inside the WRD template.

**Key fields per profile:**
- `profile_name` — e.g., `basic_output`, `extended_output`, `full`
- `terminal_task_id` — the furthest stage required for this profile
- `description` — what scientific results this profile produces (author-provided)
- `required_task_set` — **always auto-derived by backward traversal from `terminal_task_id` through the Execution Graph; never manually specified**
- `output_dataset_ids` — the dataset IDs from the Data Flow Layer that this profile produces as its primary outputs

**Why `required_task_set` must be derived, never manually listed:** If it were manually specified, it would become another source of inconsistency — an author could add a dependency between two tasks, forget to update a profile's required task set, and produce a deployment plan that skips a required task. Since the Execution Graph is the canonical structure, the required task set for any profile is always and only computed by backward traversal. This is non-negotiable.

**Why it belongs in the template:** The dependency logic is a property of the workflow, not a deployment decision. If the dependency between stage 6 and stage 7 changes, it should be fixed once — in the template — and all deployment plans referencing that profile automatically reflect the change.

---

### 6. Task Classification: Intermediate vs. Checkpoint

**What it is:** A per-dataset flag (not just per-task — a single task can produce both types) distinguishing outputs with standalone scientific value from those that exist purely to feed downstream tasks.

- `intermediate` — output is a stepping stone only; can potentially be allocated to faster, temporary storage tiers (burst buffer, node-local) and cleaned up after downstream tasks complete, reducing storage pressure.
- `checkpoint` — output has standalone scientific value AND feeds downstream tasks; must be retained after the workflow completes. Requires persistent storage allocation.

**Why:** Scientists understand this distinction intuitively — they know which outputs they want to keep — even if they do not know which storage tier to use. This is one of the fields where scientist input is both necessary and reliable, unlike data sizes which require measurement.

---

### 7. Deployment Constraints Block

**What it is:** Resource boundary declarations split between what the scientist can reliably provide and what must come from agents or tooling. Note that the scientist's *run configuration* (scope, scale, input subset) lives in the Deployment Plan Document, not here — this block captures workflow-level constraints that are stable across runs.

**Scientist-authored fields (stable across runs, belong in the WRD template):**
- `data_sensitivity` — Any known constraints on where data may reside (e.g., cannot leave on-premise, HIPAA-regulated, export-controlled). Stable — does not change run to run.

Note: `estimated input data size` and `estimated output data size` from v1 are **removed**. Scientists are never asked to estimate data sizes. These are handled by the Measured I/O Layer (Section 4, Level 2). `prior_run_exists` is also removed — the Measured I/O Layer's `measurement_confidence` field conveys this information directly.

**Agent/system-filled fields (HPC expertise required):**

Each of these fields carries a `filled_by`, `timestamp`, and `confidence` record alongside its value (see Section 8).

- `parallelism_range_per_task` — min/max recommended MPI ranks or thread counts, filled by WIDGET or HPC staff
- `memory_footprint_per_task` — filled by WIDGET or profiling tools
- `storage_tier_recommendations` — derived from task classification (Section 6) and measured data sizes (Section 4)
- `total_storage_budget` — computed from measured output sizes across all datasets in the selected profile
- `input_data_size` — measured by deployment tooling from the input data directory, not provided by the scientist

**Run configuration (per-run, lives in the Deployment Plan Document — not here):**

The scientist's run-specific choices are not workflow properties and do not belong in the WRD template. They are recorded in the Deployment Plan Document for each submission:
- `input_data_path` — the filesystem path to the input data directory for this run
- `execution_profile` — which profile to run (e.g., `basic_output`, `full`)
- `input_subset` — if not using the full input dataset, a description of the subset (e.g., "ensemble members 1–5 only", "10% random sample of input files")
- `scale_override` — if running at reduced parallelism or node count relative to the workflow's recommended range (e.g., single-node correctness check)
- `parameter_overrides` — any parameter values that differ from the workflow's defaults for this run

**Why run configuration belongs in the Deployment Plan, not the WRD template:** The WRD template describes what the workflow *is*. The Deployment Plan describes how a particular execution of it should be run. A scientist may submit the same workflow dozens of times — once at small scale to verify correctness, once at full scale for production, once on a subset of data for a quick result — and each of those is a different Deployment Plan referencing the same WRD version.

---

### 8. Translation Metadata Block

**What it is:** A complete record of how this WRD was produced, what information could or could not be mapped, and the confidence of every field that was filled in by an AI agent or automated tool rather than a human author.

**Top-level fields:**
- `source_format` — Pegasus, Slurm, XML, native, other
- `translation_tool` — tool or agent that produced this WRD
- `translation_timestamp` — ISO 8601
- `unmapped_fields` — list of field paths that could not be populated from the source, each with the reason it was unmapped
- `round_trip_gaps` — fields that will be lost or degraded if this WRD is compiled back to the source format
- `quality_warnings` — descriptions flagged by the authoring-time validation in Section 2a

**Field-level confidence records:**

This is the most significant addition to this block in v2. In v1, "confidence annotations if an AI agent performed the compilation" was described vaguely. In v2, every field filled by an AI agent or automated tool carries a confidence record at the individual field level.

Each record contains:
- `field_path` — the dot-path of the field (e.g., `task_registry.tasks[genomic_filter].semantic_description`)
- `filled_by` — the agent or tool that populated this field
- `confidence_level` — `high`, `medium`, `low`, or `inferred`
- `confidence_reason` — human-readable explanation (e.g., "semantic description inferred from task executable name only; no docstring or comment was present in the source DAX")
- `requires_human_review` — boolean, set to `true` when `confidence_level` is `low` or `inferred`

**Why field-level confidence is required:** A human operator reviewing an AI-compiled WRD before approving deployment in a secure HPC environment needs to know exactly where to focus their review — not just that "the agent had some uncertainty somewhere." A single document-level confidence score is nearly useless for this purpose.

When a Pegasus DAX is compiled into a WRD, task dependencies can typically be derived with high confidence from the DAX structure. Semantic descriptions, however, often have to be inferred from executable names or parameter labels — which may be meaningful (`run_quality_filter.py`) or opaque (`step_04.py`). An operator needs to see exactly which semantic descriptions are marked `requires_human_review = true` so they can correct them before the workflow is approved for deployment.

---

### 9. Concurrent Access and Write Consistency Model

**What it is:** The rules governing how multiple agents reading and writing different sections of a WRD simultaneously do so safely. This was absent in v1 despite concurrent multi-agent use being a stated goal.

**Read access:** Any number of agents may read any section simultaneously with no locking required. The template sections are effectively read-only once a version is published.

**Write access by section:**

| Section | Write Model |
|---------|-------------|
| Header, Task Registry, Execution Graph, Execution Profiles, Semantic I/O Layer | Writes produce a new version. The version-increment process is atomic. No concurrent writes to the same version. |
| Measured I/O Layer (Level 2) | Optimistic locking per dataset entry. A deployment tool writes by claiming the dataset ID, writing, and recording a write token. If two tools attempt to write the same entry simultaneously, the second write is rejected and must retry. |
| Physical I/O Layer (Level 3) | Optimistic locking per task profiling record. Same model as Level 2. Write conflicts are flagged in the Translation Metadata Block. |
| Agent/system-filled deployment constraint fields | Optimistic locking per field. Each field carries a `last_modified_by` and a version token. Agents include the current token in write requests; a stale token causes a rejection. |

**Why optimistic rather than exclusive locking:** Exclusive locking would serialize all profiling and deployment constraint fills, creating a bottleneck at exactly the point where thousands of agents are working concurrently. Optimistic locking is correct here because different agents are almost always writing different fields — one is measuring input data size for workflow A, another is recording profiling results for workflow B. True write conflicts (two agents writing the same field for the same workflow) should be exceptional.

---

## Document Structure Summary

```
WRD (versioned — changes increment version, stable across versions via lineage ID)
├── Workflow Header
│   ├── workflow_lineage_id (stable forever), version, version_notes, deprecated
│   └── workflow_description  [quality-validated, author-provided]
├── Task Registry  [CANONICAL SOURCE OF TRUTH for relationships]
│   ├── Task (semantic_description, relationships, loop_annotation)
│   │   └── loop_annotation: loop_type, bound_type, convergence_condition, max_iterations_guard
│   └── Task output_class (intermediate vs. checkpoint, per dataset)
├── Execution Graph  [DERIVED from Task Registry — never edited directly]
│   └── integrity_hash of Task Registry relationships
├── Data Flow Layer
│   ├── Semantic I/O  [author-provided, always present]
│   ├── Measured I/O  [tooling-measured — NOT scientist-estimated]
│   │   └── measurement_confidence: high | estimated | unavailable
│   └── Physical I/O  [optional, from profiling tools like DaYu]
├── Execution Profiles
│   ├── profile: basic_output  →  terminal: stage_6
│   │   └── required_task_set  [ALWAYS auto-derived, never manually specified]
│   └── profile: full  →  terminal: stage_9
├── Deployment Constraints
│   ├── Scientist fields: prior_run_exists, data_sensitivity, preferred_profile
│   │   (data size estimates REMOVED — now measured automatically)
│   └── Agent/system fields: parallelism, storage tiers, budget
│       └── each carries: filled_by, timestamp, confidence_level
└── Translation Metadata
    ├── unmapped_fields, round_trip_gaps, quality_warnings
    └── field_confidence_records[]
        └── {field_path, filled_by, confidence_level, confidence_reason, requires_human_review}

Deployment Plan Document (mutable, per-run, references WRD by ID + version)
├── wrd_lineage_id + wrd_version  [pins to a specific frozen snapshot]
├── input_data_path  [filesystem path to input data for this run]
├── execution_profile  [which profile to run]
├── input_subset  [if not using the full input dataset]
├── scale_override  [if running below recommended parallelism]
├── parameter_overrides  [any per-run parameter values]
└── Concrete parallelism, storage, and HPC resource decisions
```

---

## What Scientists Need to Provide

A scientist does not author a WRD by filling in fields manually. The WRD is compiled from artifacts the scientist already has or can trivially specify. The scientist's complete input is three things:

**1. A workflow code file** in whatever format they already use — a Pegasus DAX, a Nextflow script, a Parsl Python file, a Swift/T script, a shell script that submits Slurm jobs, or any other workflow description format. This is the artifact the scientist already wrote to describe and run their workflow. An AI agent or static analysis tool compiles it into a WRD, extracting task structure, dependencies, loop patterns, and data flow as far as the source format allows.

**2. The path to the input data directory** on the HPC filesystem. The deployment tooling (e.g., Jarvis-MCP) inspects this directory to measure actual input data sizes, file formats present, and dataset structure. The scientist does not describe or estimate the data — they point to where it lives.

**3. A run configuration** specifying how they want this particular execution to behave relative to the full workflow. This is not HPC configuration — it is scientific scope configuration. It covers things like:
- Which execution profile to use (e.g., run only through stage 6, not the full pipeline)
- Whether to run on a subset of the input data (e.g., a single ensemble member for a test run, or 10% of input files for a scale-down validation)
- Whether to run at reduced parallelism (e.g., a single-node run to verify correctness before full-scale submission)
- Any parameter overrides relative to the workflow's defaults

This run configuration lives in the Deployment Plan Document, not in the WRD template itself — it is per-run, not a property of the workflow definition.

---

### How Each WRD Field Gets Populated

This table maps every category of WRD content to its actual source. Nothing requires the scientist to manually describe structure that already exists in their code.

| WRD Content | Source |
|-------------|--------|
| Task list and names | Static analysis or AI compilation of the workflow code file |
| Task dependency graph | Static analysis of the workflow code (Pegasus DAX edges, Nextflow channel declarations, Parsl `depends_on`, Slurm `#SBATCH --dependency`, etc.) |
| Loop structure | Static analysis of the workflow code; AI agent fills `loop_type` and infers bounds where possible |
| Semantic descriptions (task and workflow) | AI agent inference from code structure, function names, comments, docstrings, and parameter names in the workflow file. Quality-validated per Section 2a; low-confidence inferences flagged for human review in Translation Metadata. |
| Data flow — file formats and roles | Static analysis of the workflow code (input/output declarations, file extensions, channel types) |
| Data flow — actual input sizes | Measured by deployment tooling from the input data directory path provided by the scientist |
| Data flow — output sizes | Measured from prior completed runs; `unavailable` on first run |
| Physical I/O characteristics | Collected by DPM system I/O tracing during runtime; matched to tasks by task name and PID recorded in the trace |
| Task dependency graph (runtime-confirmed) | Derived from DPM I/O traces: tasks that write a file that another task reads are connected by a `data_dependency` edge, confirming or supplementing the statically-derived graph |
| Checkpoint vs. intermediate classification | Cannot be reliably inferred — this is the one field the scientist must explicitly provide, because only the scientist knows which outputs are scientifically valuable to retain |
| Execution profiles | Scientist specifies which intermediate stages produce independently useful results; required task sets are always auto-derived |
| Parallelism, memory, storage tiers | Filled by WIDGET, Jarvis-MCP, or HPC staff after WRD compilation |
| Data sensitivity constraints | Scientist-provided if applicable; otherwise absent |

**The one field that cannot be extracted or measured:** The checkpoint vs. intermediate classification of output datasets. Static analysis can identify which files are written by which tasks, but it cannot determine which of those outputs the scientist considers scientifically valuable to retain after the run. This distinction lives in the scientist's domain knowledge, not in the code. It is the only structural field that requires explicit scientist input beyond the three items listed above.

---

### WRD Compilation Pipeline

The process of producing a WRD from scientist inputs follows this sequence:

```
Scientist provides:
  [1] workflow code file  +  [2] input data path  +  [3] run configuration

        │                          │                        │
        ▼                          ▼                        ▼
  Static analysis /          Deployment tool          Deployment Plan
  AI compilation             measures input           Document (per-run)
  of code file               data directory
        │                          │
        ▼                          ▼
  WRD Template populated:    Measured I/O Layer
  - Task Registry            populated with
  - Execution Graph          actual input sizes
  - Semantic I/O Layer
  - Loop annotations
  - Translation Metadata
  (with confidence records)
        │
        ▼
  Scientist reviews
  Translation Metadata
  quality warnings,
  corrects low-confidence
  semantic descriptions
        │
        ▼
  First run executes
        │
        ├──► DPM I/O traces collected during runtime
        │         │
        │         ▼
        │    Physical I/O Layer populated
        │    Runtime dependency graph confirmed
        │
        └──► Output sizes measured after completion
                  │
                  ▼
             Measured I/O Layer updated
             (output_data_bytes_per_profile populated)
```

After the first run, the WRD is substantially complete. Subsequent runs have fully populated Measured I/O and Physical I/O layers, giving agents rich data for storage planning and optimization.

---

## Appendix: Changes from Version 1

| Issue | Change in v2 |
|-------|-------------|
| Immutability breaks under scientific iteration | Replaced with versioned immutability: changes increment `version` under a stable `workflow_lineage_id`. Deployment plans pin to a specific version. |
| Loop annotation underspecified | Full loop model introduced: `loop_type` (static / parameter_sweep / data_driven / convergence), `bound_type`, `convergence_condition`, `max_iterations_guard`, `loop_position`. |
| Execution Graph consistency undefined | Task Registry declared canonical. Execution Graph carries an integrity hash and is treated as derived — never edited directly. Agents must detect and reject stale graphs. |
| Confidence annotation too vague | Field-level confidence records introduced per filled field: `field_path`, `filled_by`, `confidence_level`, `confidence_reason`, `requires_human_review`. |
| Scientists asked to estimate data sizes | Data size estimation fields removed. Measured I/O Layer added (Level 2 of Data Flow), populated by deployment tooling. `measurement_confidence` handles the unavailable first-run case. |
| Concurrent write model absent | Write consistency model defined per section type: version increment for template sections; optimistic locking with write tokens for agent-filled fields and profiling data. |
| Semantic description quality unenforceable | Quality standards defined in Section 2a with authoring-time validation rules. Failures recorded as quality warnings in Translation Metadata. |
| Scientists asked to manually describe workflow structure | Scientists provide a workflow code file (Pegasus, Nextflow, Parsl, Slurm, etc.); task structure, dependencies, and data flow are extracted by static analysis and AI compilation. Scientists do not re-describe what is already in their code. |
| No model for runtime I/O trace integration | DPM I/O traces (task name + PID per I/O operation) populate the Physical I/O Layer and can independently confirm or supplement the statically-derived dependency graph. |
| Run configuration had no defined home | Run configuration (input data path, execution profile, input subset, scale override, parameter overrides) is now explicitly part of the Deployment Plan Document, not the WRD template. The WRD describes what the workflow is; the Deployment Plan describes how a particular run should execute. |
