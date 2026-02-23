# WDD v2 — Supplementary Design Notes

Companion to `wdd_design-v2.md`. Contains design decisions and edge-case
documentation that are too detailed for the main spec but too important to lose.

---

## 1. Field Status Model

Every field in the WDD schema carries a `_status` annotation telling the generating agent what to do with it.

| Status | Meaning |
|--------|---------|
| `required_static` | Extract from source code via static analysis. If extraction fails, escalate to `required_static_ask`. |
| `required_static_ask` | Cannot be reliably inferred from code. Agent **must** prompt the scientist before proceeding. |
| `required_deploy` | Leave null at compile time. Deployment tooling (Jarvis-MCP) measures from filesystem or completed run outputs. |
| `optional_enrichment` | Leave null at compile time. DPM tracing populates after first run. Not required for initial deployment. |

**Agent Readiness Gate** — before handing the WDD to the DDD generator, verify:
- All `required_static` and `required_static_ask` fields are non-null
- `workflow_graph.integrity_hash` is current
- All `required_task_sets` in execution_profiles were auto-derived (never manually specified)
- `translation_metadata.field_confidence_records` has one entry per agent-inferred field
- Any `requires_human_review: true` field has been reviewed or explicitly deferred by the scientist

---

## 2. Corner Cases

**Multi-dataset edges.** A single P-C edge may carry multiple data objects simultaneously (e.g., the openmm→aggregate edge in DeepDriveMD carries four HDF5 datasets in one file). Use the `data_objects` list on pc_edges. Do not create one edge per dataset for a single task relationship.

**Config/parameter objects.** Use `category: config` for parameter files and run configs. This prevents agents from treating configs as intermediate data to be staged or cleaned up.

**Conditional patterns.** Workflows where tasks only execute based on a runtime condition should include `conditional` in `secondary_patterns` for hybrid workflows. Document the branch logic in `control_flow.conditional_description`.

**Partial file access.** When a task reads only a subset of a file's datasets, always create an `io_behavioral_hints` entry with `potential_concern: partial_access`. Requires reading both the file-creation code and the file-reading code side-by-side — the most commonly missed finding in static analysis.

**Broadcast vs. scatter.** Both are `1_to_n` patterns. Broadcast: each consumer reads the full dataset (add a `data_reuse` hint). Scatter: each consumer reads a different partition. Distinguish in `data_flow_description` and `pc_pattern_rationale`.

---

## 3. Open Design Decisions

The following fields have unresolved trade-offs. Current schema implements the pragmatic default for each.

| Field | Current default | Alternative | Trade-off summary |
|-------|-----------------|-------------|-------------------|
| Loop annotation | Prose `iteration_description` in `control_flow` | Structured schema: `loop_type`, `bound_type`, `convergence_condition`, `max_iterations_guard` | Prose is more accurate in practice; structured enables IODD machine-comparison and DDD safety guards |
| Temporal I/O annotation | Prose `behavioral_notes` per task | Structured `io_phase`, `burstiness`, `overlap_potential` per task | Prose is more accurate; structured enables `match_wrd_io_phase` in IODD |
| `contention_sensitivity` per task | Omitted | `high \| medium \| low \| unknown` | Nearly always `unknown` before profiling; DDD can derive from `io_dominance` + `pc_pattern` |
