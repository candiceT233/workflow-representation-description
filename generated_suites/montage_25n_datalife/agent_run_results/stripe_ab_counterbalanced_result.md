# Counterbalanced Stripe A/B — overturns the apparent 11% (it was warmup)

**Job:** 18746307 · **State:** COMPLETED (0:0) · **Nodes:** 25 · **Elapsed:** 99 s
**Run dir:** `/projects/bekn/mtang9/widget/runs/Montage/stripe_ab_cb_20260602T210259Z`
**Date:** 2026-06-02 · **Profiler:** none · **Supersedes the interpretation in** `stripe_ab_result.md`

## Why this run
The first A/B (`stripe_ab_result.md`, job 18738834) used `B/O/B/O` ordering, so `opt`
always followed `base` within a pair and a per-position warmup (~0.4 s) was conflated
with the stripe effect — giving an apparent 11% that I flagged `suggestive`. This run
removes the confound: 8 passes in **`ABBA-ABBA`** order (`base opt opt base base opt opt
base`), n=4/arm, so each arm's mean position is identical (4.5) and warmup cancels by
symmetry.

## Raw data (corrected pipeline, full 25/25-tile mosaic every pass)

| Order | Pass | stripe | runtime_s |
|---:|---|---:|---:|
| 1 | base_1 | 20 | 11.770 |
| 2 | opt_1  |  4 | 11.405 |
| 3 | opt_2  |  4 | 11.001 |
| 4 | base_2 | 20 | 11.076 |
| 5 | base_3 | 20 | 10.976 |
| 6 | opt_3  |  4 | 10.973 |
| 7 | opt_4  |  4 | 10.418 |
| 8 | base_4 | 20 | 10.520 |

| Arm | n | mean | min | max |
|---|--:|--:|--:|--:|
| base (−c20) | 4 | 11.085 | 10.520 | 11.770 |
| opt (−c4)   | 4 | 10.949 | 10.418 | 11.405 |

`delta_mean = 0.136 s`, `speedup = 1.23 %`.

## Verdict — **no detectable effect**
- **Decision test fails:** worst-opt (11.405) is **not** < best-base (10.520) — the arms
  **overlap heavily**.
- Within-arm spread (base 1.25 s, opt 0.99 s) ≫ between-arm mean gap (0.136 s): the 1.23%
  is **run-to-run noise**, not a stripe effect.
- The downward trend by order (11.77 → … → 10.52) confirms a strong warmup that the
  earlier `B/O/B/O` design mistook for an optimization gain.

**Conclusion:** at Montage Scale-A on 25 nodes, the `-c20 → -c4` Lustre stripe change
yields **no measurable wall-clock improvement**. The theoretically-motivated, IODD-cited
optimization does effectively nothing here. (It is still harmless and arguably correct
hygiene — it does not *regress* — but it is not a performance win.)

## WIDGET feedback (drove iteration 4 / v8.2)
Recorded as `validation = {status: measured, strength: definitive (counterbalanced n=4,
position-balanced), outcome: no_detectable_effect, measured_delta: {value: "+1.23% mean",
n_reps_per_arm: 4, design: "ABBA-ABBA counterbalanced", confounds: ["none material —
warmup balanced by symmetry"], strength: definitive}}`. The need for an `outcome` field
distinct from `strength` (a rigorous measurement can show a null) is **improvement #11**,
schema `iodd-8.2`.

## Paper note
This is the clean cautionary arc: **recommended → applied_unvalidated → suggestive (~11%,
confounded) → measured / no_detectable_effect.** An LLM agent's plausible, profiler-grounded
optimization survived three weaker evidentiary bars and was only falsified by a
counterbalanced A/B — reinforcing the thesis that *execution + rigorous, confound-aware
measurement* must be first-class in representation evaluation, not optional.
