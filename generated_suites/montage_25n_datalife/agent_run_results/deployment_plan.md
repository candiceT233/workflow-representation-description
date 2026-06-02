# I/O-Optimized Deployment Plan — Montage Scale-A (25 nodes), DataLife IODD

**Agent:** claude-code (Opus 4.8, 1M ctx) — autonomous deployment+execution agent
**Profiler suite basis:** DataLife (`iodd.yaml`)
**Knowledge boundary:** every statement below is derived **only** from the six YAMLs in
`generated_suites/montage_25n_datalife/`. No source code, raw traces, README, or campaign
notes were consulted to understand the workflow.

---

## 1. Workflow summary (from `wdd.yaml`)

Montage is an astronomical image-mosaic engine: it reprojects overlapping FITS sky tiles
onto a common WCS (`region.hdr`), computes pairwise overlap differences, fits planes, solves
a global background-correction model, applies it, and coadds the corrected tiles into a final
`mosaic.fits` (+ `mosaic_area.fits`).

**Primary pattern:** `hybrid` = `scatter_gather` fan-out/gather embedded in a `cascading`
10-stage chain. **Control flow:** no iteration, no conditional branches.

**Stages / tasks / topological (DAG) order** — linear cascade
(`workflow_graph.stage_execution_order`, `critical_path_hint`):

| # | stage | task | executable | parallelism (WDD) | io_dominance |
|---|-------|------|-----------|-------------------|--------------|
| 1 | build_image_table | `imgtbl_raw` | `mImgtbl` | serial | io_bound |
| 2 | reproject | `project` | `mProjExec`(mProject) | embarrassingly_parallel | balanced |
| 3 | table_projected | `imgtbl_projected` | `mImgtbl` | serial | io_bound |
| 4 | overlaps | `overlaps` | `mOverlaps` | serial | compute_bound |
| 5 | difference | `diff` | `mDiffExec`(mDiff) | embarrassingly_parallel | balanced |
| 6 | fit_planes | `fit` | `mFitExec`(mFitplane) | embarrassingly_parallel | balanced |
| 7 | background_model | `bgmodel` | `mBgModel` | serial (n_to_1 gather) | compute_bound |
| 8 | background_apply | `background` | `mBgExec`(mBackground) | embarrassingly_parallel | balanced |
| 9 | table_corrected | `imgtbl_corrected` | `mImgtbl` | serial | io_bound |
| 10 | coadd | `add` | `mAdd` | serial (n_to_1 gather) | io_bound |

**P–C patterns (`pc_edges`):** `1_to_n` table-sharding into the four `*Exec` fan-outs;
`n_to_1` gathers at `imgtbl_projected`, `bgmodel` (fit→fits.tbl concat), `imgtbl_corrected`,
and `add`; **`n_to_n`** on `project→diff`, `diff→fit`, `project→background` (sharded
producers AND sharded consumers both touch the shared FITS directories — any consumer node
may read any producer node's output). Every edge `coupling: tight` — each consumer starts
only after its producer fully completes (strictly sequential stage chain).

**`io_behavioral_hints` (WDD):**
- `hint:small_file_table_sharding` → `small_file_overhead`: `tbl_tool` splits images/diffs(×2)/pimages into many tiny per-node `.tbl` shards and concats per-shard fit tables.
- `hint:projected_fits_reuse` → `data_reuse`: projected FITS read **3×** (imgtbl_projected, diff, background).
- `hint:corrections_broadcast_metadata` → `metadata_overhead`: single `corrections.tbl` opened by all N `mBgExec`; per-stage `mImgtbl` directory-wide header scans.

---

## 2. Current deployment (from `ddd.yaml`)

- **Per-task parallelism:** `project`, `diff`, `fit`, `background` = **25 instances** each
  (1 task/node, `ranks_per_instance:1`, `threads_per_rank:1`, whole-node `cpus-per-task=128`);
  all six single-task stages (`mImgtbl`×3, `mOverlaps`, `mBgModel`, `mAdd`) = **1 instance**
  on the batch node.
- **Storage-tier assignments:** **every** dataset → `tier:projects_lustre`.
  `caching_policy: cache_on_first_read` only for `data:projected_fits` and
  `data:corrections_tbl`; `none` for all others. `staging_plan` is **empty**
  (`stage_in_steps: []`, `stage_out_steps: []`, `stripe_setup_commands: []`).
- **Task placement:** `pg:montage_exec_fanout_spread` (the 4 `*Exec` tasks) →
  `placement_policy: spread`, one pinned `srun --exclusive --nodes=1 --ntasks=1
  --cpus-per-task=128 --nodelist=NODE[i]` per distinct node;
  `pg:montage_exception_batchnode` (the 6 single-task stages) → `no_constraint`, inline on
  the batch node.
- **Scheduler directives (`job_script`):** `--account=bekn-delta-cpu --partition=cpu
  --nodes=25 --ntasks-per-node=1 --cpus-per-task=128 --mem=0 --time=00:50:00`, exclusive
  nodes. `RUNDIR=/projects/bekn/mtang9/widget/runs/Montage/scale_a_25n` (I will use a
  fresh dir — see §6). Restart: `full_restart` (idempotent tasks, rm -rf + rerun).

---

## 3. Observed I/O facts to optimize against (from `iodd.yaml`, DataLife)

Reconciled run aggregates: **378,039,388 B read / 204,280,001 B written.** All I/O is
**4 KB-block STDIO** on cfitsio FITS + tiny-record POSIX `.tbl`, all on `tier:projects_lustre`.

Per-task byte/op facts I rely on (quoted fields):

| task | bytes_read | bytes_written | read_ops | write_ops | open_ops | close_ops | cum. close_s |
|------|-----------:|--------------:|---------:|----------:|---------:|----------:|------:|
| `project` (25) | 52,859,950 | **106,554,240** | 18,525 | 36,998 | 525 | 475 | 17.07 |
| `diff` (25) | **270,329,324** | 66,965,760 | 94,626 | 23,252 | 1,947 | 1,803 | **61.95** |
| `fit` (25) | 33,483,024 | 0* | 11,698 | 0* | 169 | 144 | 5.52 |
| `background` (25) | 8,484,496† | 8,455,680† | 2,954 | 2,936 | 26 | 22 | 1.00 |
| `add` (1) | 12,729,848 | 22,302,720 | 4,428 | 7,744 | 23 | 19 | 0.85 |
| `mImgtbl` (×3 agg) | 152,746 | 1,545 | 106 | 21 | 115 | 115 | 3.67 |
| `overlaps`,`bgmodel` | ~0* | ~0/56* | — | — | — | — | — |

`*` zero = text fgets/fputs **not byte-attributed by datalife**, not truly zero.
`†` `background` totals are an **undercount — only 2 of 25 `mBgExec` traces captured by datalife.**

**`bottleneck_summary`:**
- `task:diff` (severity medium): dominant reader **270.3 MB = 71 % of all read bytes**;
  largest cumulative open+close time (**8.70 s open + 61.95 s close** summed across 25 shards,
  **1803 fopen** events) re-reading projected FITS pairs — a **metadata/open-heavy + data-reuse
  hotspot**. *DataLife caveat: "whether this is wall-time-significant cannot be confirmed
  because task wall time and bandwidth-vs-tier-peak are not captured by datalife."*
- `data:projected_fits` (severity medium): produced once (**107 MB**) and re-read across
  `diff` (270 MB), `background`, and `imgtbl_projected` — confirms `hint:projected_fits_reuse`.

**`optimization_opportunities`:**
- `prefetch_input_data` on `[task:diff, data:projected_fits]`: "Caching or **node-local
  staging** of projected FITS tiles before the diff fan-out could cut the 270 MB re-read and
  the 1803 cross-node fopen events; **magnitude not quantifiable without wall-clock timeline
  (not captured by datalife)**." `ddd_change_required: storage_tier_assignments
  [data:projected_fits].caching_policy / assigned_tier (e.g. node-local stage-in)`.

**Request sizes (`data_format_observations`):** dominant **4096 B** for all FITS
(`projected_fits`: 187,994 read / 67,704 write ops at 4 KB); `region.hdr` read in **55,390
ops of 2 B each** (char-by-char WCS parse); `.tbl` are 20–56 B records;
`corrections.tbl` = uniform 56 B (84 broadcast read ops).

**Anomalies:** (a) `background`: only 2/25 `mBgExec` traces captured — **profiling-coverage
gap, not a workflow defect**; (b) `mImgtbl` totals aggregated by binary name, **not separable
per WDD task**.

**Explicitly NOT captured by datalife** (so unavailable to me): per-op wall-clock
timeline / offsets, `workflow_wall_time_s`, sequential-vs-random access classification,
request-size *distributions* beyond the dominant block, bandwidth-vs-peak, file-lifecycle
timestamps, and per-task compute-to-IO ratio.

---

## 4. Hardware levers actually available (from `hrd.yaml`)

| tier | mount | class | usable here? |
|------|-------|-------|--------------|
| `tier:home` | `/u/mtang9` | low BW, ~102 GB | **No** — facility/GD policy forbids outputs on home |
| `tier:projects_lustre` | `/projects/bekn` | high BW parallel, 1 TB; **`stripe_tuning`: `lfs setstripe -c 4..16`** | **Yes** — mandated target tier |
| `tier:work_nvme` | `/work/nvme/bekn` | "very high (NVMe, faster than Lustre)" | **No for residence** — not `/projects` (violates GD hard constraint, see §5) |
| `tier:node_local` | `/tmp` | "highest" BW, per-node, **volatile**, no cross-node contention | **Constrained** — not shared across nodes; residence forbidden (see §5/§7) |

Network: Slingshot-11 dragonfly; **per-node injection BW / bisection BW unknown** (no OSU
micro-benchmark). `empirical_benchmarks: []` — **no measured bandwidth ceilings on any tier.**

The single concrete, on-`/projects` hardware lever the HRD sanctions is **Lustre stripe
tuning** (`tier:projects_lustre.stripe_tuning`).

---

## 5. Goals & HARD constraints (from `gd.yaml`)

This is a **benchmarking/validation** run; **throughput/latency are explicitly NOT primary
objectives**. The only optimization target is the soft cost goal.

**HARD constraints (all must hold):**
1. `goal:multinode_25_distinct` / `must_reach_25_distinct_nodes` — **exactly 25 distinct
   nodes** run work (single-task aggregation stages are the only permitted single-node exceptions).
2. `goal:max_25_nodes` — **≤ 25 nodes**, partition `cpu`, account `bekn-delta-cpu`.
3. `goal:produce_mosaic_fits` / `must_produce_mosaic_fits` — **`mosaic.fits` must be produced.**
4. `goal:wall_time_50min` — end-to-end wall **≤ 50 min**.
5. `outputs_on_projects_lustre` — **all inputs, intermediates, run dirs, and trace outputs
   must reside on `/projects` Lustre** (`/projects/bekn/mtang9/widget/`), not home.
6. `partition_cpu_account_bekn` — partition `cpu`, account `bekn-delta-cpu`.
7. `goal:nonempty_io_traces` (hard, campaign goal) — non-empty profiler traces.

**SOFT (the only optimization target):** `goal:efficient_node_hours` (priority 1) — minimize
node-hours within budget (target 21 node-hrs). With the 25-distinct-node hard floor and a
~20 s pipeline, node-hours ≈ 25 × wall/3600 ≪ 21, so the lever reduces to **minimizing wall
time / requested allocation**, never below 25 nodes.

---

## 6. The I/O-optimized deployment plan (changes vs §2 DDD)

> Hard-constraint note that governs everything below: **constraint #5 forces every byte of
> intermediate data to reside on `/projects` Lustre.** This directly bounds the strongest
> I/O lever DataLife points at (node-local staging), as detailed in §7.

### APPLIED change A — Lustre stripe tuning of the run directory *(IODD + HRD grounded, on-Lustre)*
- **What:** before any file is written, create the fresh RUNDIR on `/projects` Lustre and set
  a moderate stripe count `lfs setstripe -c 4` on the FITS-bearing subdirectories
  (`projected/`, `diffs/`, `corrected/`, `mosaic/`) so the large/ re-read FITS inherit a
  4-way OST stripe; **leave the `.tbl` directory at the filesystem default (`-c 1`)** so the
  many tiny shard tables are not over-striped.
- **(a) IODD evidence:** the two largest data channels are `project` writes
  (`bytes_written = 106,554,240`, edge `pc:project->imgtbl_projected` 106.5 MB) and `diff`
  reads of projected FITS (`task:diff.bytes_read = 270,329,324`, edge `pc:project->diff` =
  270.3 MB), all `observed_request_size_kb: 4` (4 KB block). Spreading those files across 4
  OSTs parallelises the large sequential read/write volume.
- **(b) GD goal served:** `goal:efficient_node_hours` (soft, only target) — faster bulk
  transfer ⇒ lower wall ⇒ lower node-hours.
- **(c) Hard-constraint check:** stays entirely on `tier:projects_lustre` ⇒ honors #5;
  changes nothing about node count (#1/#2), the mosaic (#3), wall budget (#4 — only reduces
  it), or partition/account (#6). `staging_plan.stripe_setup_commands` was empty in the DDD;
  this populates it.
- **Honest magnitude caveat:** individual projected tiles are ~2 MB (107 MB / 50 files), so a
  4-way stripe touches only ~2 OSTs per file; and the IODD's actual `diff` hotspot is
  **metadata/open overhead** (62 s cumulative close, 1803 fopen), which **stripe count does
  not address**. Expected benefit is therefore **modest and bounded**, and with no
  `empirical_benchmarks` and no wall-clock in DataLife it **cannot be quantified ex ante**.
  `-c 4` (low end of HRD's 4..16) is chosen deliberately to avoid harming the small-file
  population.

### APPLIED change B — tighten requested walltime *(scheduling, serves soft goal)*
- **What:** request `--time=00:10:00` instead of `--time=00:50:00`. A verified run completes
  in ~20 s (EDD/DDD), and 10 min is still 5× margin and well under the 50-min hard cap.
- **(a) evidence:** EDD `execution_context.notes` / DDD rationale: "verified run completes in
  ~20 s." **(b) goal:** `goal:efficient_node_hours` — a smaller job backfills sooner.
  **(c) hard-constraint check:** 10 min ≤ 50 min ⇒ honors #4; all other constraints unchanged.
  (Charged node-hours are by *elapsed*, not requested, so this is a schedulability tweak, not
  a node-hour reduction — stated honestly.)

### UNCHANGED (and why no further optimization is possible)
- **Parallelism stays 25-way** for the 4 `*Exec` stages and 1 for the six exception stages.
  The EDD `hardware_floor` sets a floor of 25 nodes for `project/diff/fit/background`, and
  hard constraint #1 requires *exactly* 25 distinct nodes; #tiles (25) == #nodes (25), so the
  fan-out cannot be widened or narrowed. **No parallelism optimization is available.**
- **All datasets stay on `tier:projects_lustre`** (constraint #5). Keep the DDD's
  `cache_on_first_read` on `projected_fits`/`corrections_tbl` — OS page-cache gives free
  *within-node* reuse (helps the batch-node `mImgtbl` re-scan and the corrections broadcast),
  though it does **not** help the *cross-node* `n_to_n` `project→diff` reuse.
- **No stage overlap.** Every `pc_edge.coupling` is `tight` and the WDD marks the chain
  strictly sequential; DataLife captured **no timeline**, so there is no basis to introduce
  overlap safely.

---

## 7. Optimizations BLOCKED by a hard constraint or by a DataLife capture gap
*(reported as results, not failures — per the experimental protocol)*

**B1 — Node-local (`/tmp`) staging / prefetch of `projected_fits`.** This is DataLife's
**explicit #1 `optimization_opportunity`** (`prefetch_input_data`, "node-local staging … cut
the 270 MB re-read and the 1803 cross-node fopen"). **Blocked / not applied because:**
  1. **Hard constraint #5** (`outputs_on_projects_lustre`) requires intermediate data to
     **reside on `/projects` Lustre**; `/tmp` is volatile node-local and not `/projects`.
  2. **`project→diff` is `n_to_n`** (WDD): any diff node may read any project node's output.
     Node-local staging would therefore require **replicating all 50 projected files to all 25
     nodes** (a full broadcast), and DataLife captured **no wall-clock timeline and no
     bandwidth-vs-peak**, so the stage-in cost vs the saved re-read is **unquantifiable** — its
     own opportunity text says "magnitude not quantifiable without wall-clock timeline (not
     captured by datalife)." **This is a gap, not a failure.**

**B2 — Move intermediates to the faster `tier:work_nvme`.** HRD rates `work_nvme` "faster than
Lustre," which would help the 270 MB `diff` read. **Blocked:** `/work/nvme/bekn` is **not
`/projects` Lustre** ⇒ violates hard constraint #5. Not applied.

**B3 — Request-size aggregation / larger I/O blocks.** All FITS I/O is 4 KB blocks and
`region.hdr` is read 2 B-at-a-time (55,390 ops). **Blocked / gap:** DataLife provides only
the *dominant* request size, **no request-size distribution, no seq/random classification, no
bandwidth-vs-peak**; and changing cfitsio/Montage buffering means touching workflow source,
which is out of scope (and not exposed by the YAMLs). Unquantifiable + unactionable.

**B4 — Attack the true `diff` metadata/open bottleneck (62 s cumulative close, 1803 fopen).**
The only real fix is file aggregation / fewer-larger files, i.e. **re-architecting Montage's
file-per-tile / file-per-pair I/O** — not exposed by the suite and out of scope. DataLife also
warns this bottleneck's **wall-time significance "cannot be confirmed"** (no task wall time).
Gap.

**B5 — Validating any optimization's effect against the profile.** Because the
`background` stage profile is an **undercount (2/25 `mBgExec` traces)** and `mImgtbl` is not
per-task separable, and because `workflow_wall_time_s` / per-task timelines are `unknown`,
**no DataLife-based before/after wall-clock comparison is possible.** Runtime effect must be
read from the run's own timing + `sacct` (Phase 2), not from the IODD.

---

## 8. Net plan

Run the **unchanged 10-stage Montage pipeline** at the DDD's 25-way `*Exec` fan-out /
6 single-task exception stages, on `--nodes=25 --ntasks-per-node=1 --cpus-per-task=128
--partition=cpu --account=bekn-delta-cpu`, **with two on-Lustre optimizations applied**:
(A) `lfs setstripe -c 4` on the FITS subdirs of a fresh `/projects` Lustre RUNDIR
(populating the DDD's empty `stripe_setup_commands`), and (B) a tightened `--time=00:10:00`.
The strongest DataLife-indicated lever (node-local staging of `projected_fits`) is **reported
as blocked** by the `/projects`-residence hard constraint and by DataLife's missing wall-clock
evidence. All seven hard constraints are honored; the soft node-hours goal is the only
optimization target and is served by (A)+(B). Success is judged by: `mosaic.fits` produced,
**25/25 distinct nodes**, wall ≤ 50 min, all I/O on `/projects` Lustre.
