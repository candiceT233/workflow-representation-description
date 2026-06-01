# WIDGET Suite Comparison — Montage Scale-A 25-node: DataLife vs Darshan IODD

## Experiment

This compares two WIDGET document suites generated for the **same** deployment —
Montage **Scale-A, 25 nodes** on NCSA Delta (`hrd:delta_ncsa_cpu`, tier
`tier:projects_lustre`). The two suites are intentionally identical in their
**five shared documents** (WDD, EDD, GD, HRD, DDD) and differ **only** in the
sixth document, the I/O Deployment Description (IODD), which is derived from a
specific profiler:

- **Set A — `montage_25n_datalife/`**: IODD built from **DataLife** data-flow
  traces (`iodd:deploy:montage_scale_a_25n:datalife`).
- **Set B — `montage_25n_darshan/`**: IODD built from **Darshan 3.4.6** STDIO
  logs (`iodd:deploy:montage_scale_a_25n:darshan`).

Holding WDD/EDD/GD/HRD/DDD byte-identical isolates the profiler as the only
variable, so any difference in the IODDs is attributable to the I/O
characterization tool, not to workflow or deployment drift. This is a clean
A/B on **what each profiler can and cannot reveal** about the same run.

---

## Validation Results

| # | Check | Result |
|---|-------|--------|
| 1 | All 12 files exist and parse as valid YAML | **PASS** — 12/12 parsed by `yaml.safe_load`; no parse errors |
| 2 | Five shared docs (wdd/edd/gd/hrd/ddd) byte-identical across dirs | **PASS** — `diff` reports MATCH on all 5; zero drift |
| 3 | Cross-reference integrity (task:/data:/stage: refs resolve to WDD) | **PASS** — WDD defines 33 IDs; edd (8 refs) and ddd (23 refs) fully resolve in both suites; both IODDs fully resolve. The only initial "dangling" hits (`task:imgtbl_corrected.`, `data:projected_fits.`) were valid IDs trailed by a sentence period inside prose; clean after punctuation strip |
| 4 | Both IODDs pin the same five input-doc IDs; differ only in profiler-derived content | **PASS** — `ddd_id`, `hrd_id`, `wrd_lineage_id`, `edd_lineage_id`, `edd_instance_id` are identical; only `iodd_id`, `profiling_tools`, run-timing, and profiler-measured fields differ |

**Detail for check 1** — files validated: `wdd.yaml, edd.yaml, gd.yaml, hrd.yaml,
ddd.yaml, iodd.yaml` in each of the two directories (12 total), all OK.

**Detail for check 4** — both IODDs cover the same **10 tasks** and **15
communication channels**. Their aggregate byte totals agree to **0.08%**:

| Aggregate | DataLife | Darshan | Delta |
|-----------|----------|---------|-------|
| Sum `bytes_read`  | 378,039,388 | 378,338,259 | +0.079% |
| Sum `bytes_written` | 204,280,001 | 204,401,618 | +0.060% |

Both reconcile to the stated ground-truth (~378.3 MB read / ~204.3 MB written),
confirming the two profilers measured the same physical run.

---

## Per-Profiler IODD Coverage Map

Side-by-side of what each profiler **populated** vs **marked "not captured"**,
section by section.

| IODD section / field group | DataLife populated | Darshan populated | Marked "not captured" |
|---|---|---|---|
| **header.run timing** (`run_start`/`run_end`/`wall_time_seconds`) | `wall_time_seconds: unknown` (no job-level clock) | `run_start`/`run_end` + `wall_time_seconds: 10` | **DataLife**: absolute wall time |
| **per_task_io_profile** — byte/op totals (`bytes_read/written`, `read/write_ops`, `open_ops`) | Yes — per binary, exact byte counts | Yes — per binary, exact byte counts | — |
| **per_task** — `close_ops`, per-op open/close times | `posix_open_time_s` + `posix_close_time_s` per task (cumulative libc-call time) | `close_ops: unknown`; only one aggregated `stdio_meta_time_s` per task | **Darshan**: separate close-op counts and per-op open/close times (STDIO collapses to one `meta_time`) |
| **per_task** — `access_pattern_observed` | `unknown` everywhere | `sequential` everywhere | **DataLife**: no seq/random classification |
| **per_task** — `io_phase_observed` | `unknown` everywhere | `mixed` / `streaming` per task | **DataLife**: no per-op wall-clock timeline |
| **per_task** — `compute_to_io_ratio` | `unknown` (no task wall time) | Numeric per task (uses stage wall span) | **DataLife**: not computable w/o wall time |
| **per_task** — `match_wrd_io_phase` | `unknown` | `true` (validated against WDD) | **DataLife**: cannot validate phase |
| **per_task** — per-task attribution for repeated binary (mImgtbl) | **Cannot separate** the 3 mImgtbl tasks — totals lumped onto `task:imgtbl_raw`; other two `unknown` | **Separates** imgtbl_raw / imgtbl_projected / imgtbl_corrected by directory scanned | **DataLife**: per-task split of a shared binary |
| **communication_channels** — `data_volume_bytes` | Populated where a producer/consumer byte total binds; small `.tbl` (fgets/text) channels left `unknown` (not byte-attributed) | Populated for **all 15 channels**, including small table edges | **DataLife**: text/`.tbl` channel byte volumes |
| **communication_channels** — `transfer_pattern` | `unknown` | `bulk_sequential` on all channels | **DataLife**: transfer pattern |
| **communication_channels** — `transfer_time_s` / `transfer_bandwidth_gbs` | `unknown` (no producer-write→consumer-read timeline) | `unknown` (no cross-task lineage) | **Both**: realized cross-task transfer wall time / bandwidth |
| **data_format_observations** — `observed_container` | Yes (binary/text) | Yes (binary/text) | — |
| **data_format_observations** — `observed_request_size_kb` | Yes — from per-file `_stat` block histograms (e.g. 4 KB-block FITS, 2 B header parse, 56/20 B `.tbl` records) | Yes — but **computed** as bytes/ops average (e.g. ~2.86 KB), not a true histogram | **DataLife**: no histogram (it has one); **Darshan**: no native request-size histogram — only derived averages |
| **data_format_observations** — `observed_access_pattern` | `unknown` | `contiguous_sequential` | **DataLife**: no access-pattern field |
| **data_format_observations** — `match_wrd_layout` | `unknown` (cannot confirm contiguous vs strided) | `true` | **DataLife**: layout confirmation |
| **temporal_io_behavior** — per-task offsets (`task_start/end_offset_s`, `io_start/end_offset_s`, `io_active_duration_s`, `pipeline_overlap_observed`) | Entire section `unknown` (only cumulative per-op time, no absolute offsets) | **Full 10-task timeline** with offsets, I/O fractions, overlap flags | **DataLife**: complete temporal timeline |
| **file_lifecycle_events** — per-file `created_at`/`first_read_at`/`last_read_at`/`deleted_at`, `idle_time_s`, `lifetime_s` | Not captured — **but** provides a file→data_id map with file globs + counts and per-file block-access histograms | Not captured — provides only a prose data-reuse note (FITS/.tbl created on Lustre, re-read by later stages) | **Both**: lifecycle timestamps / idle / lifetime (DataLife flags as its own future DFL-G capability; richer file→data_id map on the DataLife side) |
| **diagnosis_summary** — `overall_io_pattern` | `cascading` | `cascading` | — (both agree) |
| **diagnosis_summary** — `pattern_match_wrd` | `false` (caveat: cannot resolve full hybrid label) | `false` (sees only the sequential cascade, not embedded scatter/gather) | both note WDD is **hybrid**; neither can confirm the scatter/gather concurrency component |
| **diagnosis_summary** — bottleneck typing | `task:diff` typed `other` (cannot prove wall-time significance) | `task:diff` + `task:imgtbl_projected` typed **`metadata`** (backed by `STDIO_F_META_TIME`) | **DataLife**: cannot classify a metadata bottleneck definitively |
| **diagnosis_summary** — Lustre striping / device tuning | Not available — opportunity is generic node-local stage-in/caching | **`LUSTRE_COMP*_STRIPE_COUNT=1`** observed → concrete `lfs setstripe -c 4` recommendation | **DataLife**: Lustre OST/stripe layout |
| **diagnosis_summary** — anomalies | background coverage gap (2/25 traces); mImgtbl per-task non-separability | background coverage gap (2/25 logs); WDD-hybrid vs observed-cascading pattern note | both flag the 23-of-25 background trace-coverage gap as a profiling gap, not a workflow defect |

---

## Takeaways — what each profiler uniquely reveals

- **Darshan owns the wall-clock and access-classification dimension.** It alone
  populated the full `temporal_io_behavior` per-task offset timeline, the
  `access_pattern_observed`/`io_phase_observed` fields, and a numeric
  `compute_to_io_ratio`. DataLife left all of these `unknown` because it records
  cumulative per-libc-call time, not absolute offsets — so any
  scheduling/overlap or "is this stage I/O-bound in wall time" question is a
  Darshan answer.

- **Darshan exposes the storage substrate; DataLife does not.** Only the Darshan
  IODD surfaced Lustre `STRIPE_COUNT=1` and the `STDIO_F_META_TIME` breakdown,
  letting it type `task:diff`/`task:imgtbl_projected` as **metadata-bound**
  bottlenecks and recommend a concrete `lfs setstripe` change. DataLife could
  only flag diff as a generic high-volume hotspot.

- **DataLife gives finer, ground-truth data-flow attribution.** Its per-file
  `_stat` histograms captured true request-size structure (4 KB FITS blocks, 2 B
  char-by-char `region.hdr` parse, 56/20 B `.tbl` records) and a richer
  file→data_id lifecycle map; its byte totals are treated as the reconciliation
  ground truth that Darshan matches to within 0.08%. Darshan's request sizes are
  only bytes/ops averages and it lumps text-table channels it cannot
  byte-attribute.

- **They trade off on per-task vs per-binary attribution.** Darshan separated the
  three `mImgtbl` invocations by the directory each scanned (raw / projected /
  corrected) into distinct WDD tasks; DataLife aggregates by binary name and had
  to lump all three onto `task:imgtbl_raw`, leaving two tasks `unknown`.

- **Neither captures realized cross-task transfer timing, and both hit the same
  coverage gap.** `transfer_time_s` / `transfer_bandwidth_gbs` and true
  producer→consumer lineage timing are `unknown` in both (both note this is a
  DataLife/DaYu DFL-style capability not realized here), and both independently
  flagged the identical 2-of-25 background-shard trace-coverage gap — a profiling
  artifact, not a workflow defect.

---

*Report path: `/u/mtang9/widget_eval/widget-v1/workflow-representation-description/generated_suites/COMPARISON.md`*
