# Gemini Trials: 1000genome WDD vs. Knowledge (Trials 1–3)

This document summarizes the three Gemini-generated outputs for the 1000genome workflow in both representation formats — Workflow Design Documents (WDD, YAML) and workflow knowledge (Markdown) — and compares them.

---

## Part 1: WDD Document Quality

### WDD Quality Comparison Table

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
| **Executable paths** | name only | name only | name only |
| **Population counts (2504/26)** | ❌ | ✅ | ✅ |
| **Execution profiles** | 1 | 2 | 2 |
| **translation_metadata quality** | ✅ detailed | ✅ detailed | ✅ detailed |
| **Hardware_path (Decaf/PMC)** | ❌ | ❌ | ✅ |

### WDD Trial Summaries

**Trial 1:** Template-heavy, daxgen.py source. Correct source file, full schema coverage, 5 task-to-task PC edges, 10 data objects. Weaknesses: missing population stats; no Decaf/PMC paths; no `bin/` prefix on executables.

**Trial 2:** sbatch-based, wrong source. Clean YAML, population counts (2504/26), 2 execution profiles, `1_to_n` broadcast edges. Weakness: wrong source file (sbatch instead of daxgen.py) can cause Q&A mismatches.

**Trial 3:** daxgen.py, most complete. 12 PC edges (incl. config broadcast flows), Decaf/PMC execution_alternatives, loop_groups, conditional branching. Weakness: same 2 I/O hints as t1/t2; no `bin/` prefix.

---

## Part 2: Knowledge Document Quality

### Knowledge Quality Comparison Table

| | gemini-t1 | gemini-t2 | gemini-t3 |
|---|---|---|---|
| **Lines / Words** | 196 / ~1,990 | 65 / ~515 | 102 / ~652 |
| **Successfully generated** | ✅ | ⚠️ truncated | ⚠️ |
| **Failure reason** | — | truncated | no file access |
| **Task structure correct** | ✅ 5 tasks, correct order | ✅ 5 tasks, correct order | ❌ wrong order |
| **Executable paths (bin/)** | ✅ `bin/individuals`, etc. | ✅ implied | ✅ `bin/individuals.py` |
| **Data formats specified** | ✅ VCF, CSV, tar.gz, text | ⚠️ partial | ❌ all unknown |
| **PC edges with patterns** | ✅ scatter_gather, data_dependency | ❌ truncated | ❌ wrong dependencies |
| **I/O behavioral hints** | ✅ 8 detailed | ❌ | ✅ 3 (wrong context) |
| **Population stats (2504/26)** | ❌ | ❌ | ❌ |
| **Assumption count** | 0 | 0 | 12 |
| **Actual filenames** | ✅ | ❌ | ❌ |
| **CLI parameters** | ✅ -c, -pop, start_line, end_line | ❌ | ❌ |
| **Usable as eval baseline** | ✅ best | ⚠️ partial | ❌ unreliable |

### Knowledge Trial Summaries

**Trial 1:** Best quality, full static analysis. Actual Pegasus filenames, CLI parameters, executable paths with `bin/`, explicit staging, data reuse, Decaf/PMC hints. Weakness: no population stats.

**Trial 2:** Truncated at line 65. Correct task order and structure until cut; no PC edges, data registry, or I/O hints.

**Trial 3:** Wrong task order; assumption-heavy. Generated without file access; introduces `prepare_input`; places sifting after frequency/mutation_overlap (reversed data flow); PC edges describe incorrect dependencies (e.g. `frequency->sifting` instead of `sifting->frequency`).

---

## Part 3: Cross-Representation Analysis

### Coverage Comparison: What Each Format Captures

| Information Category | WDD (best: t3) | Knowledge (best: t1) |
|---------------------|----------------|----------------------|
| **Scientific purpose / 2504/26** | ✅ t2/t3 | ❌ all trials |
| **Task names and count** | ✅ 5 | ✅ 5 |
| **Executable paths (bin/)** | ❌ name only | ✅ `bin/individuals`, etc. |
| **Task CLI parameters (-c, -pop, start_line)** | ❌ | ✅ |
| **Actual filenames (ALL.chrX.vcf, sifted.SIFT.chrX.txt)** | ❌ abstract IDs | ✅ Pegasus filenames |
| **PC patterns (n_to_1, 1_to_n)** | ✅ structured, 5–12 edges | ✅ prose + scatter-gather |
| **Config broadcast flows** | ✅ t3 only | ❌ |
| **data.csv as manifest** | ⚠️ t1 only | ✅ |
| **Decaf/PMC execution paths** | ✅ t3 hardware_path | ✅ mentioned in hints |
| **stage_out / staging behavior** | ❌ | ✅ explicit True/False |
| **Lifecycle per data object** | ✅ retention_window | ❌ |
| **Data reuse hint** | ✅ | ✅ |
| **Small-file overhead** | ✅ | ✅ |
| **Execution profiles** | ✅ 1–2 | ❌ |
| **Per-field confidence** | ✅ field_confidence_records | ❌ |
| **Loop groups / iteration** | ✅ t3 | ✅ prose |

### Trial Consistency Across Formats

| Trial | WDD source | Knowledge source | Consistent? |
|-------|------------|------------------|-------------|
| **t1** | daxgen.py | daxgen.py | ✅ Both correct; WDD has template stubs, Knowledge is complete |
| **t2** | sbatch | daxgen.py | ⚠️ Different sources; Knowledge truncated |
| **t3** | daxgen.py | no file access | ❌ WDD correct; Knowledge wrong (assumptions, reversed flow) |

### Structural Gaps: WDD vs. Knowledge

**WDD captures but Knowledge does not:**
- Population counts (2504 individuals, 26 populations) — in t2/t3 WDD
- Lifecycle/retention_window per data object
- Execution profiles (stopping points)
- Per-field confidence records
- Config broadcast PC edges (t3)
- Loop groups and conditional branching (t3)

**Knowledge captures but WDD does not:**
- Actual Pegasus filenames (`ALL.chrX.250000.vcf`, `chrXn-start-stop.tar.gz`)
- CLI parameters (`-c`, `-pop`, `start_line`, `end_line`)
- Executable paths with `bin/` prefix
- Explicit stage_out True/False per file
- `data.csv` as chromosome manifest (in prose)
- `use_bash` / `--bash-jobs` I/O tuning context

### Which Format for Which Use Case?

| Use Case | Better Format | Reason |
|----------|---------------|--------|
| **Q&A about filenames, CLI args** | Knowledge | WDD uses abstract data IDs; Knowledge has concrete names |
| **Q&A about population/counts** | WDD | Knowledge trials omit 2504/26 |
| **Machine-readable structure** | WDD | YAML schema; Knowledge is prose |
| **I/O tuning / staging decisions** | Knowledge | Explicit stage_out, use_bash, Decaf hints |
| **Execution checkpointing** | WDD | execution_profiles |
| **Confidence / provenance** | WDD | field_confidence_records |

### Key Takeaways

1. **Complementary strengths:** WDD excels at structured metadata, lifecycle, and execution profiles; Knowledge excels at concrete filenames, CLI parameters, and staging behavior.
2. **Template gap:** Neither WDD schema prompts for `filename_pattern` on data objects or `cli_parameters` on tasks — adding these would close the gap.
3. **Source consistency matters:** t2 WDD used sbatch; t3 Knowledge had no file access. Both produced lower-quality or wrong outputs.
4. **Best combined baseline:** WDD gemini-t3 + Knowledge gemini-t1 covers the most ground for evaluation.
