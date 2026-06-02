# WIDGET Template Suite — v8 CHANGELOG

**Date:** 2026-06-02
**Architecture:** v7 → **v8**
**Schema versions:** `wrd-8.0`, `edd-3.0`, `ddd-8.0`, `gd-8.0`, `hrd-8.0`, `iodd-8.0`
**Predecessor templates:** preserved under [`archive/v7/`](archive/v7/)

> **Why v8 exists.** Every change below was forced by a single real deployment:
> the Montage Scale-A 25-node run on NCSA Delta (job 18681933). Executing the
> workflow surfaced a **reproducible `mBgExec` binary defect** (background-apply
> aborts with `free(): invalid size` on 23/25 shards) that the DataLife IODD had
> recorded but **mislabeled** as a benign *"profiling-coverage gap."* The final
> `mosaic.fits` was built from only **3 of 25** tiles, yet a file-existence check
> reported `SUCCESS`. v8 makes the representation able to *express* what only
> execution could previously reveal. Full detail:
> `generated_suites/montage_25n_datalife/agent_run_results/run_report.md` and
> `docs/WIDGET_INTERMEDIATE_REPORT_*.md` §6.0.

---

## Substantive changes

### IODD (`iodd-7.0` → `iodd-8.0`)

| # | Field added | What it fixes |
|---|---|---|
| 1 | `diagnosis_summary.optimization_opportunities[*].constraint_feasibility` + `.quantifiable` | Optimizations were named with no check against GD hard constraints. Montage's #1 opportunity (node-local staging) was actually *blocked* by `goal:outputs_on_projects_lustre`, and *unquantifiable* under DataLife (no wall-clock). Now each opportunity links the GD constraint IDs it must clear and states whether this suite's profiler can size it. |
| 2 | `per_task_io_profile[*].coverage = {traces_captured, traces_expected, complete, shortfall_cause}` | A profiler emits records only for processes that *finish*. "2 of 25 mBgExec traces" was ambiguous between under-instrumentation and crashes. Coverage is now first-class; the shortfall cause must be named (or honestly `unknown` and raised as an anomaly). |
| 3 | `per_task_io_profile[*].attribution_scope` (`per_task`\|`per_binary`) + `attribution_note` | DataLife lumped the three `mImgtbl` calls onto one task; Darshan split them by directory. Pooled numbers are now flagged, not silently presented as per-task. |
| 5 | `communication_channels[*].realized_transfer = {measurable, measured_by, transfer_time_s, transfer_bandwidth_gbs}` | Realized cross-task transfer time was measured by *neither* profiler. Making it a block means its absence is queryable (`measurable:false`), not an implicit gap. |
| 6 | `diagnosis_summary.pattern_match_wrd` → `{matches, confirmable_dimensions, unconfirmable_dimensions}` | A byte/op profiler can confirm the *cascade* but not the embedded *scatter concurrency*; a bare boolean over-claimed. Now splits confirmable from unconfirmable structure. |
| 7 | `diagnosis_summary.anomalies[*].interpretation = {hypothesis, confidence, disambiguated_by, resolved, resolution}` | **The headline fix.** A profiler-inferred *cause* is a falsifiable hypothesis, not ground truth. The `mBgExec` mislabel is the cautionary case; v8 forbids asserting a cause as fact and records how it would be settled (default `disambiguated_by: execution`). |
| 9 | `diagnosis_summary.optimization_opportunities[*].validation = {status, baseline_ref, measured_delta, how_to_validate}` | Separates *recommended* from *proven*. The Montage stripe-reduction was **applied but unvalidated** — one run, no default-stripe baseline, no wall-clock — so no speedup may be claimed. Forces a WIDGET evaluator to record `applied_unvalidated` and the A/B that would settle it, instead of reporting an unmeasured improvement. *(Found by re-reading the report in iteration 2 of the improvement loop; folded into v8.)* |
| — | `profiler_capability_matrix` (new Section 1b) + `fusion_note` | Structured per-tool can/can't-measure map. Turns the v7 free-text `field_confidence` notes into a queryable capability matrix and makes multi-profiler fusion mechanical. |
| — | `anomaly_type` gains `trace_coverage_shortfall` | Names the coverage gap as a typed anomaly. |

### GD (`gd-7.0` → `gd-8.0`)

| # | Field added | What it fixes |
|---|---|---|
| 8 | `completion_criteria` (new Section 5) | Semantic success conditions (`count_equals`, `all_exit_zero`, `table_rows_equal`, …) checked *after* the run. `mosaic.fits exists` was a false positive on a 3/25-tile mosaic; `corrected_tiles == n_tiles` would have failed loudly. `artifact_existence_is_insufficient` is hard-set `true`. |

### Conventions

- `WIDGET_conventions.md` "Applies to" line and Key Design Principles updated; three v8 principles added (profiler-inference-is-hypothesis; profiler-reach-is-queryable; success-is-semantic).

## Version-only bumps (no schema change)

`WDD` (`wrd-8.0`), `HRD` (`hrd-8.0`), `DDD` (`ddd-8.0`), `EDD` (`edd-3.0`) were bumped
for suite coherence only — a v8 suite reads as a single coherent generation. Each
carries an inline header note to that effect.

## Migration notes (v7 → v8)

- v7 suites remain valid input to v8-aware agents; the new IODD/GD fields are
  additive. A v7 IODD simply lacks `coverage`, `interpretation`, etc.
- A v8-aware evaluator should treat a missing `completion_criteria` as "criteria
  unspecified → fall back to artifact existence, but warn" rather than silent pass.
- To regenerate a v8 suite, point the generation prompt at these templates; the
  six output docs will carry the `*-8.0` schema versions.
