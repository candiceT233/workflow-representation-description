# Q&A Evaluation Report: WDD vs Workflow Knowledge

**Run folder:** `evaluation_runs/20260311-083828`  
**Date:** 2026-03-11  
**Scope:** 74 questions × 2 context types × 1 agent (OpenCode)  
**Trial used:** 1 — `1000genome-wdd-opencode-trial1.yaml`, `1000genome-knowledge-opencode-trial1.md`

---

## 1. Executive Summary

The **20260311-083828** run produced **74 successful answers** out of 74 per context type (100% success). **WDD slightly outperformed workflow knowledge** overall:

| Context Type       | Success | Judge Mean | Std   |
|--------------------|---------|------------|-------|
| wdd_yaml           | 74/74   | **2.78**   | 1.47  |
| workflow_knowledge | 74/74   | 2.69       | 1.41  |

**Mean score difference: +0.09** (WDD better). WDD scored higher on 26 questions, workflow knowledge on 21, and 27 were ties.

Both OpenCode trial1 documents were generated with access to the repository. The WDD includes `source_file: daxgen.py`, `executable: bin/individuals.py` (full paths), and structured metadata. The workflow knowledge document has detailed task tables, data object registry, and producer-consumer dependencies. The smaller gap compared to the 20260304 run (Gemini trial3) reflects that both representations in this run are relatively complete.

---

## 2. Error Types

### 2.1 Infrastructure Failures

**None.** All 148 evaluations (74 questions × 2 context types) completed successfully.

### 2.2 Semantic Error Types (from 74 successful pairs)

| Error Type | Description | WDD vs Knowledge |
|------------|-------------|------------------|
| **Project metadata** | Dataset stats (2,504 individuals, 26 populations) | Both list 2,504; both confused super-populations (7) with distinct populations (26) on q051 |
| **Task structure** | Task order, dependencies, scatter/gather | Both have correct structure; WDD has richer `pc_edges` and `workflow_patterns` |
| **Executable path** | Location of scripts (e.g., `bin/`) | Both include `bin/` — OpenCode WDD trial1 has `executable: bin/individuals.py` |
| **Answer verbosity** | Bare task name vs. full explanation | Knowledge sometimes gave fuller prose; WDD sometimes produced terse answers (e.g., q011) |

---

## 3. Section-by-Section Analysis

### 3.1 Section Breakdown (Mean Score)

| Section | WDD Mean | WK Mean | Diff | Notes |
|---------|----------|---------|------|------|
| SECTION 1: SCIENTIFIC PURPOSE AND BIOLOGICAL SEMANTICS | 1.96 | 2.04 | -0.08 | Knowledge slightly better; both lack 26 populations in metadata |
| SECTION 2: WORKFLOW DATAFLOW AND TASK DEPENDENCIES | **3.52** | 3.33 | +0.19 | WDD advantage from structured stages/tasks |
| SECTION 3: REPOSITORY USAGE AND SYSTEM MECHANICS | **1.82** | 1.45 | **+0.36** | Largest WDD gain; `source_file`, `cardinality_source` help |
| SECTION 4: INPUT FILES, OUTPUT FILES, AND DATA FORMATS | **3.40** | 3.20 | +0.20 | WDD `data_objects` and format hints support answers |

**Largest WDD gain:** Section 3 (repository usage), where `source_file`, `source_format`, and `cardinality_source` in the WDD provide direct answers about daxgen.py and configuration-driven behavior.

---

## 4. Example Comparisons

### 4.1 WDD Wins (WDD >> Knowledge)

#### q017: Which script is responsible for dynamic generation of workflow dependencies?

| Context | Score | Model Answer |
|---------|-------|--------------|
| **WDD** | 4 | "**daxgen.py** is responsible... Key evidence from the wdd_yaml: `source_file: daxgen.py`, `source_format: compiled_from_pegasus_dax`... The workflow has 'data-driven' iteration based on configuration (data.csv rows and population file count)." |
| Knowledge | — | "`daxgen.py` is responsible for the dynamic generation of workflow dependencies." (Minimal; judge score not recorded) |

**Why:** WDD metadata (`source_file`, `source_format`, `cardinality_source`) gives explicit evidence. Knowledge mentions daxgen.py but the answer was too terse for full credit. Three workflow_knowledge results (q017, q043, q066) had no judge score recorded in the run.

#### q051: How many individuals and distinct populations were successfully mapped?

| Context | Score | Model Answer |
|---------|-------|--------------|
| **WDD** | 3 | "**2,504 individuals**... **7 distinct populations** — as stated in the `data:population_file` description: 'Seven super populations: ALL, AFR, AMR, EAS, EUR, GBR, SAS.'" |
| Knowledge | 2 | "**Individuals**: 2504... **Distinct populations**: 7 populations (AFR, AMR, EAS, EUR, GBR, SAS, ALL)" |

**Why:** Both correctly identified 2,504 individuals. Both confused super-populations (7) with the reference answer (26 distinct global populations). WDD scored slightly higher for citing the WDD field explicitly.

#### q030: Where are the core executable scripts located in the repository?

| Context | Score | Model Answer |
|---------|-------|--------------|
| **WDD** | 5 | "The core executable scripts are located in the `bin/` directory... `bin/individuals.py`, `bin/individuals_merge.py`, `bin/sifting.py`, etc." |
| **Knowledge** | 5 | "The core executable scripts are located in the `bin/` directory... `bin/individuals.py`, `bin/individuals_merge.py`, `bin/frequency.py`, etc." |

**Why:** Tie. OpenCode trial1 WDD includes `executable: bin/individuals.py` (full path), unlike the Gemini trial3 WDD in the 20260304 run.

### 4.2 WDD Losses (Knowledge >> WDD)

#### q011: What task acts as the synchronization barrier after parallel VCF parsing?

| Context | Score | Model Answer |
|---------|-------|--------------|
| WDD | 1 | "task:individuals_merge" (bare task ID only) |
| **Knowledge** | 4 | "**individuals_merge** acts as the synchronization barrier. It waits for all parallel `individuals` chunk tasks to complete before merging the per-chunk individual files into a single chromosome archive." |

**Why:** Both contexts contain the correct answer. The model produced a terse, non-explanatory response with WDD; with Knowledge it produced a full explanation that matched the reference.

#### q009: What is the specific role of the "Individuals" task at the start of the pipeline?

| Context | Score | Model Answer |
|---------|-------|--------------|
| WDD | 3 | "The **Individuals** task... processes VCF files from the 1000 Genomes Phase3 release... Read chromosome VCF files, filter for SNPs with allele frequency ≥ 0.5, write per-individual mutation files..." |
| **Knowledge** | 5 | "The **individuals** task... parse VCF files per chromosome and extract SNP data... filters for only homozygous variants (with allele frequency >= 0.5 or < 0.5 depending on genotype), then outputs per-individual data as tar.gz files..." |

**Why:** Knowledge's prose better matched the reference (e.g., "homozygous variants", genotype-dependent filtering). WDD's structured description was accurate but scored lower for completeness.

---

## 5. WDD-Focused Analysis

### 5.1 What the WDD Did Well (OpenCode Trial 1)

1. **`source_file` / `source_format`** — Direct answers for daxgen.py and Pegasus DAX (q017).
2. **`executable` with path** — `bin/individuals.py` etc. support q030-style questions (unlike Gemini trial3).
3. **Task structure** — Stages, tasks, `pc_edges`, and `workflow_patterns` support dataflow questions.
4. **`data_objects`** — Format hints, producer/consumer, and cardinality support Section 4 questions.
5. **`cardinality_source`** — Config-driven iteration (data.csv, population files) supports repository-mechanics questions.

### 5.2 Where the WDD Fell Short

1. **Answer verbosity** — Model sometimes produced minimal answers (e.g., "task:individuals_merge") when using WDD, suggesting the structured format may encourage extraction over explanation.
2. **Project stats** — `workflow_description` does not include "26 distinct populations"; both WDD and Knowledge confused 7 super-populations with 26.
3. **Replica Catalog** — q018 (LFN→PFN mapping) was not well answered by either context; WDD has logical IDs but not RC semantics.

### 5.3 Workflow Knowledge (OpenCode Trial 1) Strengths

The trial1 knowledge document:
- Has detailed task tables with executables, inputs, outputs.
- Includes a Data Objects Registry with locations (e.g., `data/20130502/`).
- Describes producer-consumer dependencies in prose and a dependency graph.
- Was generated with repository access, so it reflects actual structure.

---

## 6. Recommendations for template_WDD.yml

### 6.1 Enrich workflow_description with Population Count

**Recommendation:** When project docs state "26 distinct populations" (vs. 7 super-populations), include both in `workflow_description`:

```yaml
_extract: >
  ... If README or project docs state dataset scale (e.g., "2,504 individuals",
  "26 distinct populations", "7 super-populations"), include these. Distinguish
  super-populations from the full set of distinct populations when documented.
```

**Rationale:** q051 asks for "distinct populations"; 7 vs. 26 confusion is common without explicit documentation.

### 6.2 Preserve Executable Path in Extraction

**Recommendation:** Ensure the extraction pipeline preserves full paths (e.g., `bin/individuals.py`) when available from the workflow definition. OpenCode trial1 did this; Gemini trial3 did not.

**Rationale:** Addresses "where are executables located?" questions consistently across agents.

### 6.3 Optional: Replica Catalog / LFN Mapping

**Recommendation:** For Pegasus workflows, consider an optional field describing how logical file names map to physical locations (Replica Catalog, staging, etc.) when this is derivable from the codebase.

**Rationale:** Would help answer q018-style questions about LFN→PFN mapping.

---

## 7. Summary Table: Question Types vs. Context (20260311-083828)

| Question Type | WDD Strength | Knowledge Strength | Typical Outcome |
|---------------|-------------|-------------------|-----------------|
| Script responsible for DAG generation (daxgen.py) | Strong | Moderate | WDD wins |
| Executable script location (bin/) | Strong | Strong | Tie (both have paths) |
| Task role, dataflow, synchronization | Strong | Strong | Mixed (verbosity varies) |
| Project stats (individuals, populations) | Moderate | Moderate | Both confused 7 vs 26 |
| LFN→PFN mapping (Replica Catalog) | Weak | Weak | Both struggle |
| Primary scientific objective | Strong | Strong | Tie |

---

## 8. Appendix: Files Referenced

- **Evaluation run:** `evaluation_runs/20260311-083828/qa_eval/`
- **Summary:** `evaluation_runs/20260311-083828/qa_eval/summary.json`
- **WDD used:** `workflow_wdd/1000genome-wdd-opencode-trial1.yaml`
- **Workflow knowledge used:** `workflow_knowledge/1000genome-knowledge-opencode-trial1.md`
- **Q&A prompts:** `doc/1000genome-workflow-knowledge-eval-{1,2,3}.txt`
- **Template:** `template_separate_docs/template_WDD.yml`
