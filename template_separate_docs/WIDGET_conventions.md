# WIDGET Architecture Conventions
## Applies to: All v8 documents (wrd-8.0, edd-3.0, ddd-8.0, gd-8.0, hrd-8.0, **iodd-8.1**)
<!-- v8 (2026-06-02): IODD + GD gained schema fields motivated by the Montage
     25-node deployment (see CHANGELOG-v8.md). WDD/HRD/DDD/EDD are version-only
     bumps for suite coherence. v7 templates preserved under archive/v7/. -->

> **v8 in one line:** an IODD's profiler-inferred causes are now *hypotheses*
> (not facts), trace coverage and profiler reach are *queryable* (not prose),
> optimizations carry a *constraint-feasibility* check, and a run is "successful"
> only when *completion_criteria* pass — not merely when an output file exists.

---

## 1. Six-Document Architecture

```
EDD  = f(WDD, scientist_input)
DDD  = prescription(WDD, EDD, GD, HRD)
IODD = execution(WDD, EDD, DDD, HRD, GD)   — one record per run
```

| Document | Who authors it | Changes when |
|---|---|---|
| WDD | AI agent (static analysis) | Workflow source code changes |
| EDD | AI agent (static) + scientist (instance) | Experiment parameters change |
| GD  | Operator / HPC facility staff | Performance objectives change |
| HRD | Sysadmin / facility staff | Hardware configuration changes |
| DDD | AI prescription agent | Strategy or any input doc changes |
| IODD | Profiling tools + AI agent | Every run produces one record |

---

## 2. ID Namespace (all documents share this table)

| Entity | Prefix | Example |
|---|---|---|
| Workflow lineage | `wrd:` | `wrd:deepdrivemd` |
| Experiment lineage | `edd:` | `edd:deepdrivemd:12sim_40gpu` |
| Stage | `stage:` | `stage:simulation` |
| Task | `task:` | `task:openmm` |
| Data object | `data:` | `data:sim_output_h5` |
| P-C edge | `pc:` | `pc:openmm->aggregate:n_to_1` |
| Loop | `loop:` | `loop:ddmd_main` |
| Goal / hard constraint | `goal:` | `goal:throughput_10gbs` |
| Storage tier | `tier:` | `tier:burst_buffer` |
| Compute class | `compute:` | `compute:gpu_node` |
| Network fabric | `net:` | `net:slingshot` |
| Placement group | `pg:` | `pg:sim_agg_collocate` |
| Pipeline group | `pipe:` | `pipe:sim_to_agg` |
| Parameter | `param:` | `param:n_simulations` |
| Benchmark measurement | `bench:` | `bench:perlmutter:pfs_read` |
| HRD | `hrd:` | `hrd:perlmutter_nersc` |
| GD  | `gd:` | `gd:deepdrivemd:production_run` |
| DDD | `deploy:` | `deploy:f3a9c2e1:7a3b2c1d:throughput_opt` |
| IODD | `iodd:` | `iodd:deploy:f3a9:thru:edd-inst-7a3b` |

**All IDs are lowercase snake_case. No spaces.**

---

## 3. Field Status Codes

Each template uses `# [STATUS]` inline comments. Downstream consumer agents reading a *completed* document can ignore all metadata annotations — only `_value` fields carry content.

### WDD field statuses
- `required_static` — extract from code via static analysis
- `required_static_ask` — cannot be reliably inferred; agent must prompt scientist

### EDD field statuses
- `required_static` — populated during static phase alongside WDD
- `required_instance` — scientist must provide before DDD generation
- `required_derived` — auto-computed once all `required_instance` fields are filled

### GD / HRD field statuses
- `required_operator` / `required_sysadmin` — human must provide
- `required_benchmark` — must come from empirical measurement (IOR, mdtest, STREAM)
- `optional_benchmark` — improves quality; proceed if unavailable
- `auto_derived` — computed from other fields in the same document

### DDD field statuses
- `required_agent` — agent derives from WDD + EDD + GD + HRD
- `required_agent_ask` — agent proposes; operator must confirm
- `auto_validated` — computed consistency check; never manually set

### IODD field statuses
- `required_profiler` — populated from profiling tools (Darshan, DataLife, DaYu)
- `required_agent` — derived or computed by agent
- `optional_profiler` — enriches diagnosis; not required
- `predictive_estimate` — agent estimate in predictive mode; carries confidence record

---

## 4. Compact vs. Full Document Format

Every template is the **authoring format**: it carries `# [STATUS]` comments, `# _reasoning:` hints, and `# _prompt:` elicitation scripts in comments, plus YAML fields such as `_status`, `_prompt`, `_quality_check`, `_extract`. These annotations guide the authoring agent but are **not document content**.

**Authoring agents MUST emit the canonical form.** When producing a completed WDD (or EDD, DDD, etc.), do not include authoring-only fields in the output. Apply these rules:

- **Flatten `_value` fields:** For any field that uses `{ _status: ..., _prompt: ..., _value: X }`, emit only the parent key with the value: `field_name: X` (e.g. `workflow_description: "..."` not the nested structure)
- **Omit authoring-only keys:** Do not emit `_status`, `_prompt`, `_quality_check`, `_extract`, `_entry`, or any other `_*` keys — they are generation instructions, not document content
- **Omit `filled_by`** in `translation_metadata.field_confidence_records` — provenance is in `metadata.generated_by` or `translation_metadata.translation_tool`
- **Omit comment lines** (lines beginning with `#`) in the output
- Retain only `key: value` pairs where `value` is non-null
- Retain document header (schema_version, all IDs, version)

This reduces token consumption by approximately 60% for completed documents.

---

## 5. Cross-Run Comparison Model

The IODD cross-run comparison model is enabled by pinning all five input documents by ID:

| What changes | What is fixed | What you learn |
|---|---|---|
| DDD (different strategy) | WDD + EDD | Effect of storage/parallelism on I/O |
| EDD (different parameters) | WDD | Effect of experiment scale on I/O |
| Nothing (repeated runs) | All five | Run-to-run variability |

---

## 6. Key Design Principles (v8)

1. **Scientist-friendly WDD/EDD**: Scientists describe workflow semantics. AI agents derive all HPC-specific details (parallelism, storage tiers, job directives).
2. **Immutable WDD**: The WDD is a stable description of what the workflow *is*. No deployment decisions leak into the WDD.
3. **EDD resolves variability**: Everything in the WDD that cannot be known without a specific experiment instance lives in the EDD.
4. **DDD is fully justified**: Every DDD decision references a `goal_id`. A DDD without `goal_ref` entries is incomplete.
5. **IODD closes the loop**: Observed vs. planned comparisons in the IODD feed back into WDD updates and new DDD strategies.
6. **Scheduler layer is explicit**: The DDD now emits concrete job script directives. Agents should not assume Jarvis-MCP knows what directives to use.
7. **(v8) Profiler inference is a hypothesis, not ground truth**: An IODD `anomalies[*].interpretation` records a *falsifiable* cause with a `disambiguated_by` field. A trace shortfall (`coverage.complete=false`) must not be silently labeled benign — only execution, cross-profiler agreement, or source inspection can resolve it.
8. **(v8) Profiler reach is queryable**: `profiler_capability_matrix` states what each tool can/can't measure, so a `null` field maps to a known capability gap (not an oversight) and multi-profiler fusion is mechanical.
9. **(v8) Success is semantic, not file-presence**: GD `completion_criteria` define a correct run with checkable predicates (e.g. `corrected_tiles == n_tiles`). Producing an output file does NOT by itself constitute success. Optimizations in the IODD carry a `constraint_feasibility` check against GD hard constraints before they are presented as actionable.
10. **(v8) Recommended ≠ proven**: an optimization carries a `validation.status` (`recommended` / `applied_unvalidated` / `measured` / `unmeasurable`). An improvement may be *claimed* only when `status=measured` against a recorded `baseline_ref`. Applying a change and observing a single uncontrolled run is `applied_unvalidated`, never a measured speedup.
11. **(v8.1) Measured ≠ definitive**: a `measured_delta` carries its `strength` (`definitive`/`suggestive`/`anecdotal`), `design`, and `confounds`. A confounded or low-n A/B (e.g. the stripe result: ~11% raw / ~8% net, n=2, order-confounded) is recorded as `suggestive` with a `how_to_validate` plan — never reported as a proven number.