# Stripe A/B Result — Lustre stripe count on the corrected Montage pipeline

**Job:** 18738834 · **State:** COMPLETED (0:0) · **Nodes:** 25 (cn009…cn135) · **Elapsed:** 57 s
**Run dir:** `/projects/bekn/mtang9/widget/runs/Montage/stripe_ab_20260602T165755Z`
**Date:** 2026-06-02 · **Profiler:** none (un-profiled — this run answers a *performance* question, not an IODD)

## Purpose
Answer the question the optimized DataLife run could **not**: did the Lustre stripe
reduction (`-c 20` default → `-c 4` FITS / `-c 1` tables) actually improve wall-clock?
Run the **corrected** pipeline (per-tile `mBackground -t`, replacing the defective
`mBgExec` driver) 4× in one allocation, interleaved `base/opt/base/opt` into fresh
per-pass dirs so stripe count is the only variable and warmup is averaged.

## Raw data

| Pass | FITS stripe | runtime_s | corrected tiles | mosaic bytes |
|---|---:|---:|:--:|---:|
| base_rep1 | 20 | 13.182 | 25/25 | 29,401,920 |
| opt_rep1  |  4 | 11.915 | 25/25 | 29,401,920 |
| base_rep2 | 20 | 12.464 | 25/25 | 29,401,920 |
| opt_rep2  |  4 | 10.879 | 25/25 | 29,401,920 |

`mean_base = 12.823 s`, `mean_opt = 11.397 s`, **delta = 1.426 s, raw speedup = 11.12 %**.
All four passes satisfied the v8 completion criterion (`corrected_tiles == 25`, full 29.4 MB mosaic).

## Honest interpretation — **suggestive, not definitive**

- **Direction is solid:** worst-opt (11.915) < best-base (12.464) — the arms separate
  cleanly; opt was faster in *every* pairwise sense.
- **But ordering is confounded:** the design is `B/O/B/O`, so opt always followed base
  within a pair. The series trends down (13.18 → 11.92 → 12.46 → 10.88), implying a
  warmup/cache effect of ~0.36–0.52 s/position. Part of each within-pair base→opt drop
  is warmup, not stripe.
- **Net-of-warmup estimate:** subtracting ~one position of warmup (~0.4 s) from the
  ~1.4 s within-pair drop leaves **~1.0 s (~8 %)** attributable to striping.
- **Low n:** n = 2 per arm.

**Verdict:** the stripe reduction *does* help wall-clock on this pipeline — but the
honest claim is **~8–11 % wall-clock, `strength: suggestive`**, not a proven 11.12 %.

## How to make it definitive (next run)
Counterbalance order (`B/O/O/B` or alternate the leading arm), n ≥ 3 per arm, same
allocation; confirm `worst-opt < best-base` holds and that per-position warmup is
removed by symmetry. Optionally profile (Darshan) to attribute the gain to reduced
OST open/close metadata on the `diff` stage, the IODD-flagged hotspot.

## WIDGET feedback (drove iteration 3 / v8.1)
This result is recorded in the v8 IODD as
`optimization_opportunities[*].validation = {status: measured, baseline_ref: this A/B,
measured_delta: {value: "-11.1% raw", adjusted_value: "~-8% net of warmup",
n_reps_per_arm: 2, design: "B/O/B/O interleaved", confounds: ["opt always follows base
→ warmup conflated"], strength: suggestive}, how_to_validate: "counterbalanced n≥3/arm"}`.
The need for that structured `measured_delta` (vs a bare number) is **improvement #10**
(schema `iodd-8.1`).
