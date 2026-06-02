# Run Report — Montage Scale-A 25-node, I/O-Optimized (DataLife IODD)

**Agent:** claude-code (Opus 4.8, 1M ctx) · **Profiler suite:** DataLife
**Run dir:** `/projects/bekn/mtang9/widget/runs/Montage/opt_datalife_20260601T153132Z`
**SLURM job:** `18681933` · **State:** COMPLETED (exit 0:0) · **Nodes:** 25

---

## 1. What was run

The full 10-stage Montage pipeline (`full_mosaic` profile) constructed **solely** from the
WIDGET suite, with the DDD's Class-A `srun` fan-out: 25-way per-node scatter for
`project`/`diff`/`fit`/`background`, single-task batch-node execution for the three `mImgtbl`
calls + `mOverlaps`/`mBgModel`/`mAdd`. Submitted as a raw `sbatch` script
(`run_montage_opt.slurm`) — Jarvis-MCP was not available in the session.

**Scheduler directives (honoring GD/DDD):** `--account=bekn-delta-cpu --partition=cpu
--nodes=25 --ntasks-per-node=1 --cpus-per-task=128 --mem=0 --exclusive`, `--time=00:10:00`.

## 2. Optimizations applied (from `deployment_plan.md`)

| # | Optimization | Status | Evidence it took effect |
|---|---|---|---|
| A | **Lustre stripe reduction**: `lfs setstripe -c 4` on `projected/diffs/corrected/mosaic`, `-c 1` on `tbls/` (fs **default was `-c 20`** — over-striping small Montage files) | **APPLIED** | `lfs getstripe -c` verified 4/4/4/4/1 before launch |
| B | Requested walltime 50 min → 10 min | APPLIED | job ran in `--time=00:10:00`; elapsed 23 s |

> The IODD's headline opportunity (node-local `/tmp` staging of `projected_fits`) was **not
> applied** — blocked by the `outputs_on_projects_lustre` hard constraint and unquantifiable
> under DataLife (no wall-clock). See `deployment_plan.md` §7.

## 3. Result — PARTIAL SUCCESS (one stage defective)

| Stage | Outcome |
|---|---|
| 1 `mImgtbl` raw | OK — 25 tiles scanned |
| 2 `mProjExec` (×25) | OK — 50 files (25 projected + 25 area) |
| 3 `mImgtbl` projected | OK — 25 |
| 4 `mOverlaps` | OK — 72 overlap pairs |
| 5 `mDiffExec` (×25) | OK — 144 diff files |
| 6 `mFitExec` (×25) + concat | OK — fits.tbl 72 rows |
| 7 `mBgModel` | OK — corrections.tbl (cmin −4.25, cmax 5.40) |
| 8 `mBgExec` (×25) | **FAIL — 23/25 aborted** (`free(): invalid size`, SIGABRT); only 3 tiles corrected |
| 9 `mImgtbl` corrected | OK but saw only **3** tiles |
| 10 `mAdd` | OK — coadded **3/25** tiles → `mosaic.fits` present but **scientifically incomplete** |

`mosaic.fits` (11,151,360 B) and `mosaic_area.fits` were produced, so the script's
existence-check reported `SUCCESS` — but the mosaic is built from **3 of 25** background-
corrected tiles (a smaller covered bounding box; the full mosaic is ~29.4 MB, see §5).

## 4. Root-cause diagnosis — `mBgExec` is defective (not a profiling gap)

- **23/25 `mBgExec` instances aborted** with `free(): invalid size` across distinct nodes
  (cn008, cn009, cn042, …) → heap corruption in the binary.
- **Deterministic, not a concurrency artifact:** running a single `mBgExec` shard serially
  by hand reproduces `free(): invalid size` (rc=134) with **0 output**.
- **The worker is fine:** `mBackground -t in.fits out.fits pimages.tbl corrections.tbl`
  (the per-tile binary that `mBgExec` drives) returns OK on the same inputs.
- ⇒ The defect is in the **`mBgExec` fan-out driver**, not in `mBackground` or the data.

**This contradicts the DataLife IODD's own interpretation.** The IODD recorded
`anomalies: task:background — expected 25 mBgExec instances, observed only 2 … "Not a workflow
defect — a profiling-coverage gap."` This un-profiled re-run shows the "2 of 25" is the
**crash survivors**, not a tracing gap: `mBgExec` genuinely fails on ~23/25 shards. A profiler
that only emits traces for processes that run to completion **cannot distinguish "not
instrumented" from "crashed,"** and here it mislabeled a real defect as benign. (See the
WIDGET diagnosis in `docs/WIDGET_INTERMEDIATE_REPORT.md` §6.)

## 5. Corrected deployment (post-hoc verification)

Because `mBgExec` is broken but `mBackground` works, a correct background-apply is to invoke
`mBackground` per tile (the same binary the WDD names: `executable: mBgExec (mBackground)`).
Run serially into `corrected_fixed/` + `mosaic_fixed/` (not the timed-run outputs):

- `mBackground` per tile: **25/25 OK**
- `mImgtbl corrected_fixed`: **25 tiles**
- `mAdd` → `mosaic_fixed/mosaic.fits` = **29,401,920 B (full 25-tile mosaic)**

The full mosaic (29.4 MB) vs the defective one (11.2 MB) confirms the original covered only a
corner of the region. This is a **deployment-level fix** (no source edits): swap the
`mBgExec` driver for a per-tile `mBackground` fan-out.

## 6. Timing & node spread

| Metric | Value |
|---|---|
| `queue_wait_seconds` | **34,783** (~9.7 h; submit 2026-06-01T15:33:17Z → start 2026-06-02T01:13:00Z). 25-node job on a partition with ~10 idle nodes — expected per HRD, not a failure |
| `workflow_runtime_seconds` (pipeline-internal) | **13.112** |
| job elapsed (`sacct`) | **23 s** (includes srun step launch + verification block) |
| distinct nodes | **25 / 25** (`logs/distinct_nodes.txt`; cn008…cn135) |
| node-hours | 25 × 23 s ≈ **0.16** (≪ 21 soft target) |

## 7. Hard-constraint compliance

| GD hard constraint | Status |
|---|---|
| 25 distinct nodes run work | **PASS** — all 4 fan-out stages dispatched to 25 distinct nodes (background nodes started work before crashing) |
| `mosaic.fits` produced | **PASS literally / FAIL in spirit** — file present but from 3/25 tiles; the GD uses presence as proof of correct end-to-end execution, which is a **false positive** here (full mosaic only via the §5 fix) |
| outputs on `/projects` Lustre | **PASS** — entire run dir on `tier:projects_lustre` |
| partition `cpu` / account `bekn-delta-cpu` | **PASS** |
| wall ≤ 50 min | **PASS** — 23 s |
| node budget ≤ 25 | **PASS** — 25 |

## 8. Deviations from plan

1. **Unplanned stage failure:** the `background` stage failed (`mBgExec` defect). The DataLife
   IODD gave no warning — it labeled the relevant signal (2/25) benign — so the plan could not
   have anticipated it from the suite. Surfaced only by *executing* the workflow.
2. **Corrective action (post-hoc, §5):** demonstrated a working background-apply via per-tile
   `mBackground`, yielding the full 25-tile mosaic. Not part of the timed 25-node run.
3. The script's `RUN_RESULT=SUCCESS` is a **weak check** (file existence). Recommend
   strengthening to "corrected tile count == 25" / "cimages.tbl rows == #tiles".
