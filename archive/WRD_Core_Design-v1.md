# Workflow Representation Document (WRD) — Core Design

## Goal

The Workflow Representation Document (WRD) is a structured, AI-readable format for describing scientific workflows in HPC environments. Its primary goals are:

1. **Bridge the expertise gap** — Allow domain scientists (physicists, biologists, climate scientists) to describe their workflows without needing knowledge of parallelism, node memory, storage tiers, or HPC system internals. The WRD captures what the scientist *knows* (what the workflow does, what data it needs, what results it produces) and separates it from deployment decisions that require HPC expertise.

2. **Enable AI-assisted deployment and diagnosis** — Provide AI agents with enough structured, semantic context to autonomously deploy workflows (via tools like Jarvis-MCP), diagnose I/O bottlenecks, and recommend optimizations — even when running on capability-constrained local LLMs in secure HPC environments.

3. **Serve as a universal interchange format** — Allow AI agents to compile WRDs from existing workflow formats (Pegasus DAX, Slurm scripts, XML pipelines, etc.) and to convert WRDs back into those formats. The WRD is the common language between workflow systems.

4. **Scale to concurrent multi-agent use** — Support thousands of workflow instances running simultaneously, with many agents reading WRDs concurrently, through a design that is modular, cacheable, and index-friendly.

---

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Scientist-first** | Scientists fill in what they know; HPC-specific fields are optional or agent-filled |
| **Immutability of template** | The WRD template is read-only once authored; deployment decisions live separately |
| **Separation of concerns** | Workflow definition, I/O characteristics, and deployment constraints are distinct layers |
| **AI readability** | Every structural component includes a natural language description field |
| **Portability** | Can be compiled from or exported to Pegasus, Slurm, XML, and other formats |
| **Scalability** | Modular structure allows partial loading; stable sections are cacheable across agents |

---

## Core Components

---

### 1. Workflow Header

**What it is:** Top-level identity and provenance metadata for the workflow.

**Key fields:**
- Unique workflow ID
- Human-readable name and description (written by the scientist)
- Source format (e.g., "compiled from Pegasus DAX", "authored natively")
- Schema version
- Author and creation timestamp

**Why:** AI agents need a stable identity anchor. The source format field supports round-trip translation and lets agents know what assumptions were made during compilation. The description written by the scientist is the most important field — it gives agents semantic context that no amount of profiling data can substitute for.

---

### 2. Task Registry

**What it is:** The catalog of all tasks in the workflow. Each task entry is a self-contained unit of meaning.

**Key fields per task:**
- Unique task ID and human-readable name
- **Semantic description** — a natural language explanation of what this task does, written for AI agent understanding (e.g., "filters raw genomic reads by quality score and outputs clean FASTQ files")
- Executable or script reference
- Task type classification: `compute`, `I/O`, `preprocessing`, `postprocessing`, `checkpoint`
- Relationship list — typed edges to other tasks:
  - `depends_on` — strict ordering dependency
  - `data_dependency` — this task consumes output produced by another task
  - `optional_after` — can run after but does not strictly require
- Loop annotation — if the task participates in an iterative loop, the loop bounds or termination condition are recorded explicitly

**Why:** The semantic description field is where domain knowledge lives at the task level — this is what bridges the scientist's understanding and the AI agent's reasoning. Explicit loop annotation is essential because agents that do not recognize cyclic structures will misinterpret execution order and misdiagnose timing or data dependency issues. Typed relationships give Jarvis-MCP and diagnostic agents richer information than a plain DAG edge.

---

### 3. Execution Graph

**What it is:** A standalone, explicit encoding of the workflow DAG — nodes are task IDs, edges carry the relationship type from the Task Registry.

**Why this is a separate section from the Task Registry:** At scale, tools that compile to Pegasus, Slurm, or Jarvis pipelines need only the graph structure, not the full task descriptions. Keeping the graph explicit avoids requiring full document traversal for structural queries and allows it to be indexed and cached independently. It is intentionally redundant with the Task Registry — that redundancy is a feature, not a flaw.

---

### 4. Data Flow Layer (Two-Level)

**What it is:** Per-task I/O declarations at two distinct levels.

#### 4a. Semantic I/O Layer (always required)
Captures the meaning of data exchange:
- Named dataset identifier
- What the data represents (scientist-authored description)
- File format (HDF5, NetCDF, CSV, binary, etc.)
- Role: `input`, `output`, `intermediate`, `checkpoint`
- Producer task ID and consumer task ID(s)

#### 4b. Physical I/O Layer (optional, from profiling)
Captures observed low-level characteristics from profiling runs (sourced from tools like DaYu):
- Bytes read/written per task
- Access pattern type: sequential, random, strided
- Operation counts (read/write)
- Observed bandwidth
- POSIX timing breakdowns

**Why two levels:** The semantic layer can always be populated — even from a Pegasus DAX or a Slurm script with no profiling data. The physical layer requires an actual profiling run and is optional. This separation means the WRD is useful from day one of workflow authoring, and becomes progressively richer as profiling data is collected. It also directly enables ablation studies in WIDGET — the physical layer can be exposed or hidden independently to test how much AI agents rely on it.

**Why this matters for scientists:** Scientists describe *what* data flows between tasks (the semantic layer) in terms they already understand. They do not need to know anything about POSIX operations or access patterns — that is filled in by profiling tools automatically.

---

### 5. Execution Profiles

**What it is:** Named, valid partial execution subsets of the workflow DAG, declared inside the WRD template.

**Key fields per profile:**
- Profile name (e.g., `basic_output`, `extended_output`, `full`)
- Terminal task — the furthest stage required for this profile
- Description of what results this profile produces
- Required task set (auto-resolved by traversing the DAG backwards from the terminal task, or explicitly listed)

**Why:** Many scientific workflows produce independently useful results at intermediate stages — for example, a storm tracking workflow with 9 stages where stages 6, 7, 8, and 9 each produce distinct scientific outputs. Scientists should be able to say "I only need results through stage 6" without manually figuring out which upstream tasks are required. The execution profile encodes this logic once in the template, so deployment plans can reference a profile by name and the required task set is always correctly derived from the dependency graph.

**Why it belongs in the template (not the deployment plan):** The dependency logic is a property of the workflow, not a deployment decision. If the dependency between stage 6 and stage 7 changes, it should be fixed once — in the template — and all deployment plans referencing that profile automatically reflect the change.

---

### 6. Task Classification: Intermediate vs. Checkpoint

**What it is:** A per-task flag distinguishing tasks whose outputs have standalone scientific value from those that exist purely to feed downstream tasks.

- `intermediate` — output is a stepping stone only; can potentially be cleaned up after downstream tasks complete
- `checkpoint` — output has standalone scientific value AND feeds downstream tasks; must be retained

**Why:** This directly informs storage planning in the deployment constraints layer. Checkpoint outputs need persistent storage allocation. Intermediate outputs can be allocated to faster, temporary storage tiers (burst buffer, node-local) and cleaned up, reducing storage pressure. Scientists understand the distinction intuitively — they know which outputs they want to keep — even if they do not know which storage tier to use.

---

### 7. Deployment Constraints Block (Scientist-Facing)

**What it is:** Resource boundary declarations authored by the scientist in terms they understand, not in HPC system terms.

**Scientist-authored fields (no HPC knowledge required):**
- Estimated input data size
- Estimated output data size per execution profile
- Whether the workflow has been run before (helps agents calibrate predictions)
- Any known data sensitivity constraints (e.g., cannot leave on-premise)

**Agent/system-filled fields (HPC expertise required):**
- Required or recommended parallelism range per task (min/max)
- Memory footprint estimate per task
- Storage tier recommendations per task (burst buffer, parallel filesystem, node-local)
- Total storage budget for the workflow

**Why split scientist vs. agent fields:** This is the core of the scientist-first principle. Scientists should not need to know what a burst buffer is, or what MPI rank counts are appropriate for their data size. The WRD captures what they *do* know (data sizes, sensitivity, profile target) and leaves the HPC-specific fields for agents or HPC staff to fill in — either manually or automatically via tools like WIDGET.

---

### 8. Translation Metadata Block

**What it is:** A record of how this WRD was produced and what information could or could not be mapped during compilation.

**Key fields:**
- Source format (Pegasus, Slurm, XML, native, etc.)
- Translation tool or agent that produced the WRD
- Timestamp
- List of fields that could not be mapped and were left empty
- Confidence annotations if an AI agent performed the compilation

**Why:** This block makes the WRD auditable and trustworthy. If an AI agent compiled a Pegasus DAX into WRD and had to leave the physical I/O layer empty because no profiling data existed, that is recorded explicitly rather than silently omitted. This is especially critical in secure HPC environments where a human operator needs to verify what an agent did before deployment proceeds. It also enables round-trip fidelity checks — when converting a WRD back to Slurm or Pegasus, the agent knows exactly what was lost in the original compilation and can flag gaps.

---

## Document Structure Summary

```
WRD (immutable template)
├── Workflow Header
├── Task Registry
│   ├── Task (with semantic description, relationships, loop annotations)
│   └── Task classification (intermediate vs. checkpoint)
├── Execution Graph (standalone DAG encoding)
├── Data Flow Layer
│   ├── Semantic I/O (always present)
│   └── Physical I/O (optional, from profiling)
├── Execution Profiles
│   ├── profile: basic_output  →  terminal: stage_6
│   ├── profile: extended_output  →  terminal: stage_8
│   └── profile: full  →  terminal: stage_9
├── Deployment Constraints
│   ├── Scientist-authored fields
│   └── Agent/system-filled fields
└── Translation Metadata

Deployment Plan Document (mutable, per-run, references WRD by ID)
├── WRD reference ID
├── Execution profile selected
├── Concrete parallelism, storage, and input decisions
└── Run-specific metadata
```

---

## What Scientists Need to Provide

The WRD is designed so that a domain scientist with no HPC systems knowledge can author a valid and useful WRD by providing only:

1. A description of what the workflow does overall
2. A list of tasks with descriptions of what each task does
3. Which tasks depend on which other tasks
4. What data files flow between tasks and what they represent
5. Which outputs are scientifically valuable (checkpoint vs. intermediate)
6. Approximate input/output data sizes
7. Which execution profiles make sense for their workflow

Everything else — parallelism levels, storage tier selection, POSIX-level I/O characteristics, node memory requirements — can be filled in by AI agents, profiling tools, or HPC staff.
