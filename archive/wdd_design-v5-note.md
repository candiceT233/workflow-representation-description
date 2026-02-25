WIDGET v5 — Summary of All Changes
This covers changes across two artifacts: wdd_design.md (the design specification) and the five agent templates (WRD, DDD, GD, HRD, IODD).

Core Design Principle Added
The central change driving everything else: strict separation of concerns. The WDD/WRD now captures only what is derivable from static analysis of workflow source code. Any field that required profiling, deployment reasoning, or hardware knowledge was removed and reassigned to the appropriate document.

wdd_design.md (v4 → v5)
Field Status Model simplified. required_deploy and optional_enrichment statuses were removed. The WDD now only has required_static and required_static_ask. "Agent Readiness Gate" renamed to "Completeness Gate" with all DDD-handoff language removed.
Section A: Stage Catalog added. Stages are now first-class citizens in the schema — a stages list with stage_id, name, order, description, and tasks. This gives agents a coarser reasoning granularity above the task level, and aligns the schema with the IPDPS '26 paper's Table III stage counts.
Section B: Tasks. Two fields added per task: behavioral_notes (I/O-relevant behaviors from code: upfront vs. streaming read/write, memory patterns, access patterns) and parallelism_model (type + description of how instances relate). io_dominance comment cleaned up — removed "Refined by profiling after first run." contention_sensitivity removed entirely (now agent-assessed in DDD).
Section C: Data Objects. Added persistence (transient / stage_scoped / workflow_scoped / persistent), cardinality (how many instances at runtime), estimated_size_hint (order-of-magnitude from code), and config as a valid category. The lifecycle layer (Section C.2) was cleaned up: the three deployment/profiling fields (size_measured_bytes, size_measurement_run_id, size_measurement_confidence) were removed. The retention_window comment no longer mentions DDD tier cleanup. The lifecycle layer now contains only DAG-derivable fields.
Section D: Producer-Consumer Edges. co_scheduling_hint removed (was a DDD optimization signal, not a static workflow property). Section header comment updated to explain coupling as a structural code property only.
Section G: I/O Behavioral Hints added. New section capturing static-analysis-visible I/O concerns before any profiling runs. Eight concern types: partial_access, format_mismatch, small_file_overhead, unnecessary_serialization, data_reuse, checkpoint_waste, metadata_overhead, unknown. Each hint references affected tasks, affected data, and a classified concern type.
Section 10: Open Design Decisions reduced. contention_sensitivity row removed (it's a deployment field). Two decisions remain: loop annotation (prose vs. structured) and temporal I/O annotation (prose vs. structured). References to "DDD safety guards" and "IODD machine-comparison" removed from rationale.

template_WRD.yaml (wrd-4.0 → wrd-5.0)
Complete rewrite. All structural changes from the design spec are reflected:

Status model reduced to required_static / required_static_ask only
stages section added as Section A
task_registry renamed to tasks; added behavioral_notes, parallelism_model, source_commit, generated_by
contention_sensitivity and co_scheduling_hint removed from task and relationship schemas
data_flow.semantic renamed to data_objects; added persistence, cardinality, estimated_size_hint, config category
data_flow.lifecycle folded into each data_objects entry as a lifecycle sub-object; three size measurement fields removed
relationships on tasks replaced by standalone pc_edges section
io_behavioral_hints added as Section G with full schema
execution_graphs → workflow_graph field name alignment


template_DDD.yaml (ddd-4.0 → ddd-5.0)

Readiness gate updated: task_registry → tasks, data_flow.semantic → data_objects
Parallelism reasoning protocol rewritten: no longer reads contention_sensitivity from WRD. Added explicit 4-step agent assessment rule: infer contention risk from io_dominance + pc_pattern + parallelism instance count
Storage tier reasoning protocol updated: reads category, lifecycle.retention_window, estimated_size_hint from WRD; added config datasets to assignment rules (never stage to volatile tiers)
feasibility_check updated: uses estimated_size_hint × cardinality instead of size_measured_bytes; notes that IODD can refine after first run
Task placement section rewritten: no longer reads co_scheduling_hint from WRD. Added explicit reasoning rules: assess beneficial/neutral/harmful co-location from coupling, pc_pattern, data_volume_class, and behavioral_notes patterns
Pipelining reasoning protocol updated: reads streaming vs. deferred patterns from behavioral_notes instead of temporal_io_annotation.io_phase
capacity_checks and bandwidth_checks updated to reference pc_edges instead of execution_graph


template_GD.yaml (gd-4.0 → gd-5.0)
template_HRD.yaml (hrd-4.0 → hrd-5.0)
Schema version bump only. No structural changes — these documents describe operator goals and physical hardware, which are independent of WRD separation.

template_IODD.yaml (iodd-4.0 → iodd-5.0)
All stale WRD field name references updated:

task_registry → tasks
data_flow.semantic → data_objects
data_flow.lifecycle.retention_window → data_objects[*].lifecycle.retention_window
execution_graph.edges → pc_edges
temporal_io_annotation.io_phase → behavioral_notes (in three places: io_phase_observed comparison, match_wrd_io_phase, anomaly recommendation example)

Size field references updated:

All size_measured_bytes predictive estimates replaced with estimated_size_hint × cardinality (with null fallback when hint is "unknown")

Bottleneck detection heuristic updated:

Pipeline stall detection no longer looks for co_scheduling_hint = beneficial on WRD edges; now looks for DDD task_placement entries with co_schedule = true