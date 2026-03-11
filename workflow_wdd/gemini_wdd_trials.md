# Gemini WDD Trials: 1000genome (Trials 1–3)

This document summarizes the three Gemini-generated Workflow Design Documents (WDDs) for the 1000genome workflow.

---

## WDD Document Quality Comparison

| | gemini-t1 | gemini-t2 | gemini-t3 |
|---|---|---|---|
| **Lines** | 852 | 871 | 1,212 |
| **Source file** | daxgen.py | ares_1kgenome_parallel.sbatch | daxgen.py |
| **Source format** | compiled_from_pegasus_dax | native | compiled_from_pegasus_dax |
| **Tasks count** | 5 | 5 | 5 |
| **Data objects count** | 10 | 9 | 9 |
| **PC edges count** | 5 | 5 | 12 |
| **I/O behavioral hints** | 2 | 2 | 2 |
| **workflow_description** | ✅ filled | ✅ filled (includes 2504/26) | ✅ filled (includes 2504/26) |
| **primary_pattern** | hybrid | hybrid | hybrid |
| **Executable paths** | name only (e.g. `individuals.py`) | name only | name only |
| **Population counts (2504/26)** | ❌ | ✅ | ✅ |
| **Execution profiles** | 1 | 2 | 2 |
| **translation_metadata quality** | ✅ detailed field_confidence | ✅ detailed field_confidence | ✅ detailed field_confidence |
| **Hardware_path (Decaf/PMC)** | ❌ | ❌ | ✅ execution_alternatives |

---

## Trial-by-Trial Summary

### Trial 1: Template-heavy, daxgen.py source

- **Source:** `daxgen.py` (correct Pegasus DAG generator)
- **Format:** Uses `_status: required_static` and `_value` placeholders throughout metadata; many fields have `_prompt` and `_quality_check` stubs
- **Strengths:** Correct source file, full schema coverage, 5 task-to-task PC edges, 10 data objects (includes `data:data_csv` as manifest)
- **Weaknesses:** Missing population stats (2504 individuals, 26 populations); no Decaf/PMC alternative execution paths; no `bin/` prefix on executables

### Trial 2: sbatch-based, wrong source

- **Source:** `ares_1kgenome_parallel.sbatch` (wrapper script, not the DAG generator)
- **Format:** Cleaner YAML; no `_status` placeholders; values are concrete
- **Strengths:** Correct population counts (2504/26), 2 execution profiles, detailed `field_confidence_records`; `1_to_n` broadcast edges for merged/sifted data
- **Weaknesses:** Wrong source file — analysis was driven by sbatch rather than `daxgen.py`, which can cause downstream Q&A mismatches (e.g. q017 scoring failure)

### Trial 3: daxgen.py, most complete

- **Source:** `daxgen.py` (correct)
- **Format:** Clean YAML; no `_status` placeholders
- **Strengths:** Correct source; 12 PC edges (includes config broadcast flows: `columns_config`, `population_file`, `vep_annotation_vcf`); Decaf/PMC `execution_alternatives` in `hardware_path`; `loop_groups` for chromosome_processing, individuals_chunking, population_analysis; `has_conditional_branches: true` for Decaf/PMC
- **Weaknesses:** Same 2 I/O hints as t1/t2; no `bin/` prefix on executables

---

## PC Edge Comparison

| Edge type | t1 | t2 | t3 |
|-----------|----|----|-----|
| Task-to-task (n_to_1, 1_to_n) | 5 | 5 | 5 |
| **Config broadcast** (columns, population, VEP) | 0 | 0 | 7 |
| **Total** | 5 | 5 | 12 |

Trial 3 adds edges for `data:vcf_chromosome_chunk`, `data:columns_config`, `data:vep_annotation_vcf`, and `data:population_file` flowing into tasks, which better captures shared-read contention and broadcast patterns.

---

## Key Takeaways

1. **Source file matters:** t1 and t3 use `daxgen.py`; t2 uses the sbatch wrapper. For Q&A evaluation against the canonical workflow, t1 or t3 are preferable.
2. **Trial 3 is most complete:** 12 PC edges, Decaf/PMC paths, loop_groups, and conditional branching.
3. **Template vs. concrete:** t1 retains template placeholders; t2 and t3 are fully concrete.
4. **Common gap:** None of the three use `bin/` executable paths (e.g. `bin/individuals.py`); all use bare names like `individuals.py`.
