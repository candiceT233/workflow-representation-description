TASK: Generate a Workflow Definition Document (WDD) (Schema: wdd-5.0)
You are analyzing a scientific workflow codebase to produce a Workflow Definition Document (WDD) as defined in `doc/wdd_design-v2.md`.

Purpose
The WDD captures workflow logical structure only (what the workflow is), independent of deployment/hardware/runtime behavior.

Hard Scope Rules
- Use static code analysis only.
- Do not include deployment details (node counts, storage tiers, placement policy, hardware constraints, runtime bandwidth, performance targets).
- If a value cannot be determined, use `"unknown"` and explain why in the relevant field.
- Mark assumptions inline with `[ASSUMPTION]` and also add a corresponding `translation_metadata.field_confidence_records` entry.

Output
Produce exactly one YAML file: `wdd.yaml`.

Required Top-Level Sections (all required)
1. `metadata`
2. `stages`
3. `tasks`
4. `data_objects`
5. `pc_edges`
6. `workflow_graph`
7. `workflow_patterns`
8. `io_behavioral_hints`
9. `execution_profiles`
10. `translation_metadata`

Required ID Conventions
- `stage_id`: `stage:<descriptor>`
- `task_id`: `task:<descriptor>`
- `data_id`: `data:<descriptor>`
- `edge_id`: `pc:<producer_task>-><consumer_task>:<pattern>`
- `hint_id`: `hint:<short_name>`

Schema-Critical Enums (must match exactly)
- `pc_edges[].pc_pattern`: `1_to_1 | 1_to_n | n_to_1 | n_to_n`
- `pc_edges[].coupling`: `tight | loose`
- `pc_edges[].communication_pattern`: `shared_file | file_per_producer | in_memory | streaming_channel`
- `pc_edges[].data_volume_class`: `small | medium | large`
- `pc_edges[].co_scheduling_hint`: `beneficial | neutral | harmful`
- `workflow_patterns.primary_pattern`: `cascading | iterative | scatter_gather | pipeline | broadcast | checkpointing | conditional | hybrid`
- `tasks[].parallelism_model.type`: `serial | embarrassingly_parallel | data_parallel | task_parallel`
- `tasks[].io_dominance`: `compute_bound | io_bound | balanced | unknown`
- `tasks[].output_class`: `intermediate | checkpoint`
- `data_objects[].category`: `input | intermediate | output | checkpoint | config`
- `data_objects[].persistence`: `transient | stage_scoped | workflow_scoped | persistent`

Required Metadata Fields
`metadata` must include at least:
- `workflow_lineage_id`
- `version`
- `version_notes`
- `deprecated`
- `workflow_name`
- `workflow_description`
- `source_repository`
- `source_commit`
- `source_format`
- `source_file`
- `schema_version` (must be `"wdd-5.0"`)
- `generated_by`
- `generated_at`
- `last_modified_at`

Special Requirements from Design Spec
- `pc_edges[].data_objects` is a list and may include multiple datasets for one producer-consumer relationship; do not duplicate edges per dataset when the task relationship is the same.
- `workflow_graph` is derived from `pc_edges`/tasks and must include:
  - `integrity_hash` (SHA-256 of canonical `pc_edges` serialization)
  - `last_generated`
  - `dag_edges`
  - `loop_groups`
  - `critical_path_hint`
  - `control_flow` (`has_iteration`, `iteration_description`, `has_conditional_branches`, `conditional_description`)
  - `stage_execution_order`
  - `cross_reference` (`task_to_stage`, `data_to_producer`, `data_to_consumers`)
- `workflow_patterns` must include `primary_pattern`, `secondary_patterns`, `classification_rationale`, and `pattern_table_row`.
- `io_behavioral_hints[].potential_concern` must use:
  `partial_access | format_mismatch | small_file_overhead | unnecessary_serialization | data_reuse | checkpoint_waste | metadata_overhead | unknown`.
- `execution_profiles[].required_task_set` must be auto-derived by backward DAG traversal from `terminal_task_id`.

Required Human-Ask Fields (`required_static_ask`)
If not reliably inferable from code, ask and record answers for:
- `metadata.workflow_description`
- `tasks[].description`
- `tasks[].output_class`
- `data_objects[].description`
- `execution_profiles[].profile_name`
- `execution_profiles[].description`

Minimum Confidence Tracking Requirements
`translation_metadata.field_confidence_records` must include at least:
- all description fields
- all `pc_pattern` fields
- `workflow_patterns` classification fields
- each task `io_dominance`
- each task `behavioral_notes`

Generation Procedure
Step 1 — Survey codebase structure
- Read top-level files, README, orchestration files (Makefile, shell scripts, Nextflow, Pegasus DAX, Parsl, Snakemake, Slurm, Swift/T).
- Identify entry point, task definition mechanism, and key config files.

Step 2 — Enumerate stages and tasks
- Identify all distinct executable units and their stage membership.
- Record per-task inputs/outputs and executable names.

Step 3 — Build data object registry
- Deduplicate all workflow data objects.
- Classify category/persistence.
- For HDF5/netCDF4, extract dataset names/dtypes/shapes where visible.
- Derive lifecycle fields from DAG topology.

Step 4 — Build producer-consumer edges
- Map producers/consumers per data object.
- Classify `pc_pattern`, `coupling`, communication mode, data volume class, and co-scheduling hint with rationale.
- Capture multi-dataset edges correctly with `data_objects` list.

Step 5 — Build workflow graph and pattern classification
- Derive `workflow_graph` (including integrity hash and cross-reference tables).
- Classify primary/secondary workflow patterns with rationale.
- Fill pattern summary row.

Step 6 — Extract I/O behavioral hints
- Look for: partial_access, format_mismatch, small_file_overhead, unnecessary_serialization, data_reuse, checkpoint_waste, metadata_overhead, unknown.
- Include affected tasks and affected data objects.

Step 7 — Build execution profiles
- Propose profile(s) around scientifically meaningful stopping points.
- Ensure `required_task_set` is DAG-derived from `terminal_task_id`.
- Populate `output_dataset_ids`.

Step 8 — Assemble translation metadata
- Fill source translation metadata, unmapped fields, round-trip gaps, quality warnings, and confidence records.

Step 9 — Validate before finalizing
- Completeness: every file read/written is represented in `data_objects`.
- Consistency: all references resolve across tasks/data/edges/stages.
- Pattern accuracy: P-C cardinality matches `pc_pattern`.
- No deployment leakage.
- Cross-reference integrity matches body content.
- Stage ordering matches DAG.
- `workflow_graph.integrity_hash` is current against `pc_edges`.
- Every assumption has `[ASSUMPTION]` and a confidence record.
- Multi-dataset edges are modeled via `pc_edges[].data_objects`.

## Reference: Pattern Taxonomy

### P-C Patterns (per-edge)

| Pattern | Description | Example |
| --- | --- | --- |
| `1_to_1` | One producer, one consumer | Simulation -> post-processing |
| `1_to_n` | One producer shared across multiple consumers | Static input -> many analysis tasks; scatter fan-out |
| `n_to_1` | Several producers -> one consumer | Aggregation of parallel outputs |
| `n_to_n` | Multiple producers and consumers with shared I/O | Parallel ML training, ensemble workflows |

### Workflow-Level Patterns

| Pattern | Description | Typical P-C Structures |
| --- | --- | --- |
| `cascading` | Linear chain of stages | Any |
| `iterative` | Repeats computation with prior output as input | Often 1_to_1; may include others |
| `scatter_gather` | Fan-out to parallel tasks, fan-in to aggregator | 1_to_n scatter; n_to_1 gather |
| `pipeline` | Stages overlap in time with streaming data | 1_to_1 or 1_to_n with loose coupling |
| `broadcast` | One task provides shared input to many | 1_to_n |
| `checkpointing` | Saves task state for restart/recovery | Usually 1_to_1 or n_to_1 |
| `conditional` | Tasks execute only if a runtime condition is met | Usually 1_to_1 or 1_to_n |
| `hybrid` | Combination of the above | Mixed |