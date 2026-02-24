# GEMINI.md - Workflow Representation Description

This project defines a structured document architecture to feed knowledge to agents for workflow I/O characterization and optimization. It decomposes the problem space into five specialized documents with clear separation of concerns.

## Foundational Mandates

### 1. Document Architecture (WIDGET)
All workflow analysis and optimization MUST adhere to the 5-document architecture:
- **WDD (Workflow Definition Document):** Logical structure and task DAG. Schema: `wdd-4.0`.
- **GD (Goal Document):** Performance objectives and constraints.
- **DDD (Deployment Definition Document):** Execution strategy (parallelism, mapping, tiers).
- **HRD (Hardware Resource Document):** Physical hardware specifications.
- **IODD (I/O Definition Document):** Concrete I/O semantics and empirical behavior.

### 2. Dependency & Generation Order
Documents MUST be generated or consumed in the following order:
1.  **WDD** (from source code)
2.  **GD** (from operator/SLA)
3.  **HRD** (from system docs/profiling)
4.  **DDD** (from WDD + GD)
5.  **IODD** (from DDD + HRD via profiling or prediction)

### 3. Cross-Referencing Convention
Strict adherence to the shared ID namespace is mandatory:
- **Tasks:** `task:<name>` (e.g., `task:contact_map`)
- **Datasets:** `data:<name>` (e.g., `data:trajectory_frames`)
- **P-C Edges:** `pc:<producer>-><consumer>:<pattern>`
- **Hardware Tiers:** `tier:<name>` (e.g., `tier:node_ssd`)
- **Goals:** `goal:<name>` (e.g., `goal:throughput_10gbs`)

### 4. Taxonomy & Classification
Use the IPDPS '26 taxonomy for workflow patterns:
- `pipeline`, `scatter_gather`, `iterative`, `cascading`, `hybrid`.

## Engineering Standards

- **Document Format:** All definition documents MUST be valid YAML following the templates in `template_separate_docs/`.
- **Inference & Attribution:** Agents MUST record confidence levels and reasons for inferred fields in `translation_metadata`.
- **Surgical Updates:** When updating documents, preserve existing UUIDs (`workflow_lineage_id`) and increment versions only on structural changes.
- **Validation:** Before handoff (e.g., WDD to DDD), all `required_static` and `required_static_ask` fields MUST be non-null.

## Project Context

### Core Components
- `doc/`: Architectural specifications and design notes.
- `template_separate_docs/`: Canonical YAML templates for the 5-document stack.
- `workflows_repo/`: Reference workflow implementations (1000genome, DeepDriveMD).

### Agent Tiers
- **Tier 1 (Diagnosis):** Uses WDD + IODD to match patterns.
- **Tier 2 (Prescription):** Uses WDD + DDD + IODD + GD to recommend optimizations.
- **Tier 3 (Runtime Orchestration):** Uses DDD + IODD + HRD for live action.
