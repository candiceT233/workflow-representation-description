# Gemini Knowledge Trials: 1000genome (Trials 1–3)

This document summarizes the three Gemini-generated workflow knowledge reports for the 1000genome workflow.

---

## Knowledge Document Quality Comparison

| | gemini-t1 | gemini-t2 | gemini-t3 |
|---|---|---|---|
| **Lines / Words** | 196 / ~1,990 | 65 / ~515 | 102 / ~652 |
| **Successfully generated** | ✅ | ⚠️ truncated | ⚠️ |
| **Failure reason** | — | truncated | no file access |
| **Task structure correct** | ✅ 5 tasks, correct order | ✅ 5 tasks, correct order | ❌ wrong order |
| **Executable paths (bin/)** | ✅ `bin/individuals`, `bin/sifting` | ✅ `bin/` implied | ✅ `bin/individuals.py` |
| **Data formats specified** | ✅ VCF, CSV, tar.gz, text | ⚠️ partial | ❌ all unknown |
| **PC edges with patterns** | ✅ scatter_gather, data_dependency | ❌ truncated | ❌ wrong dependencies |
| **I/O behavioral hints** | ✅ 8 detailed | ❌ | ✅ 3 with assumptions |
| **Population stats (2504/26)** | ❌ | ❌ | ❌ |
| **Assumption count** | 0 | 0 | 12 |
| **Actual filenames** | ✅ | ❌ | ❌ |
| **CLI parameters** | ✅ -c, -pop, start_line, end_line | ❌ | ❌ |
| **Usable as eval baseline** | ✅ best | ⚠️ partial | ❌ unreliable |

---

## Trial-by-Trial Summary

### Trial 1: Best quality, full static analysis

- **Source:** Static analysis of `daxgen.py` and related files
- **Content:** Complete report with stages, tasks, data objects registry, producer-consumer dependencies, workflow pattern, and I/O behavioral hints
- **Strengths:**
  - Actual Pegasus filenames: `ALL.chrX.250000.vcf`, `chrXn-start-stop.tar.gz`, `sifted.SIFT.chrX.txt`, `chrX-POPNAME.tar.gz` (etc.)
  - CLI parameters: `-c`, `-pop`, `chromosome_number`, `start_line`, `end_line`, `total_lines`
  - Executable paths: `bin/individuals`, `bin/individuals_merge`, `bin/sifting`, `bin/mutation_overlap`; Decaf/PMC variants noted
  - Explicit staging: `stage_out=True` for final outputs, `stage_out=False` for intermediates
  - Data reuse: merged chr data and sifted data reused by both `mutation_overlap` and `frequency`
  - `use_bash` / `--bash-jobs` and Decaf/PMC hints for I/O tuning
- **Weaknesses:** No population stats (2504 individuals, 26 populations); no scientific purpose/domain context in prose

### Trial 2: Truncated; good structure until cut

- **Source:** `daxgen.py` and task scripts
- **Content:** Report cuts off mid-sentence at the end of the `frequency` task outputs section (line 65)
- **Strengths:** Correct task order (individuals → individuals_merge → sifting → mutation_overlap, frequency); stage names; data object IDs with placeholders (`chr<C>`, `<POP>`)
- **Weaknesses:** Incomplete; no PC edges, data registry, or I/O hints; only partial coverage of mutation_overlap and frequency

### Trial 3: Wrong task order; assumption-heavy

- **Source:** "Analysis performed without access to file contents due to tool limitations"
- **Content:** Report based on file names and directory structure only; 12 explicit `[ASSUMPTION]` markers
- **Strengths:** I/O hints (small-file overhead, bottleneck at gather, data reuse); MPI-IO hint for `individuals_merge_mpi.py`
- **Weaknesses:**
  - **Wrong task order:** `prepare_input` (does not exist); `sifting` placed after `frequency` and `mutation_overlap`; data flow reversed (sifting consumes frequency/overlap outputs instead of feeding them)
  - All data formats `unknown`
  - Task IDs like `data:individual_results`, `data:merged_results` are generic, not Pegasus filenames
  - PC edges describe incorrect dependencies (e.g. `pc:frequency->sifting`, `pc:mutation_overlap->sifting`)

---

## Coverage Matrix

| Information Category | t1 | t2 | t3 |
|---------------------|----|----|-----|
| Task names and count | ✅ 5 | ✅ 5 | ⚠️ 6 (wrong) |
| Task order | ✅ | ✅ | ❌ |
| Executable paths (bin/) | ✅ | ⚠️ | ✅ |
| Data formats | ✅ | ⚠️ | ❌ |
| Actual filenames | ✅ | ⚠️ | ❌ |
| CLI parameters | ✅ | ❌ | ❌ |
| PC patterns | ✅ | ❌ truncated | ❌ |
| I/O behavioral hints | ✅ | ❌ | ✅ (wrong context) |
| Stage-out / staging | ✅ | ❌ | ❌ |
| data.csv as manifest | ✅ | ❌ | ❌ |


---

## Key Takeaways

1. **Trial 1 is the only reliable baseline** for Q&A evaluation: it has correct structure, filenames, CLI parameters, and I/O hints.
2. **Trial 2 is truncated** — likely a generation limit or timeout; the structure is correct up to the cut.
3. **Trial 3 is unreliable** — generated without file access; task order and data flow are wrong.
