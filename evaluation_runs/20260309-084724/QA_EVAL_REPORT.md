# Q&A Evaluation Report: WDD vs Workflow Knowledge

**Run folder:** `evaluation_runs/20260309-084724`  
**Date:** 2026-03-09  
**Scope:** 74 questions × 2 context types × 1 agent (Gemini)  
**Model:** gemini-2.5-flash  
**Trial used:** 2 — `1000genome-wdd-gemini-trial2.yaml`, `1000genome-knowledge-gemini-trial2.md`

---

## 1. Executive Summary

The **20260309-084724** run produced **73 successful WDD answers** and **74 successful workflow knowledge answers** out of 74 per context type. **WDD outperformed workflow knowledge** overall:

| Context Type       | Success | Judge Mean | Std   |
|--------------------|---------|------------|-------|
| wdd_yaml           | 73/74   | **2.68**   | 1.35  |
| workflow_knowledge | 74/74   | 2.39       | 1.38  |

**Mean score difference: +0.29** (WDD better). WDD scored higher on 21 questions, workflow knowledge on 14, and 37 were ties.

Trial 2 uses different source files: the WDD was compiled from `ares_1kgenome_parallel.sbatch` (source_file in metadata), while the workflow knowledge explicitly references `daxgen.py` (Pegasus DAG generator). This affects repository-mechanics questions. Both documents include project stats (2,504 individuals, 26 populations) and describe scatter/gather patterns, but the knowledge document uses more explicit "Scatter-Gather" phrasing that aligns with reference answers.

---

## 2. Error Types

### 2.1 Infrastructure Failures (1 question: q057)

| QID  | Context Type | Success | Error Type | Example   |
|------|--------------|---------|------------|-----------|
| q057 | wdd_yaml     | 0/1     | Timeout    | `timeout` (300s limit) |

One WDD run timed out; the corresponding workflow knowledge run succeeded. No other failures.

### 2.2 Semantic Error Types (from 73 successful WDD pairs)

| Error Type              | Description                          | WDD vs Knowledge        |
|-------------------------|--------------------------------------|--------------------------|
| **Wrong source file**   | Which script generates dependencies  | WDD says sbatch; Knowledge says daxgen.py (correct) |
| **Pattern naming**      | "Scatter/Gather" vs "scatter_gather" | Knowledge uses explicit phrasing; WDD uses schema terms |
| **Missing domain narrative** | Broader genomic-era objectives  | WDD has workflow_description; Knowledge lacks it |
| **Missing executable path**   | Script location (bin/)        | Knowledge may include paths; WDD has executable name only |

---

## 3. Section-by-Section Analysis

### 3.1 Section Breakdown (Mean Score)

| Section | WDD Mean | WK Mean | Diff  | Notes                                      |
|---------|----------|---------|-------|--------------------------------------------|
| SECTION 1: SCIENTIFIC PURPOSE AND BIOLOGICAL SEMANTICS | 1.92 | 1.48 | +0.44 | WDD workflow_description has project scope |
| SECTION 2: WORKFLOW DATAFLOW AND TASK DEPENDENCIES    | **3.56** | 3.30 | +0.26 | Both strong; WDD slightly ahead             |
| SECTION 3: REPOSITORY USAGE AND SYSTEM MECHANICS      | 1.82 | **1.91** | -0.09 | Knowledge slightly better (daxgen.py, scatter-gather phrasing) |
| SECTION 4: INPUT FILES, OUTPUT FILES, AND DATA FORMATS| 3.22 | 3.11 | +0.11 | Both strong                               |

**Notable:** Section 3 is the only section where workflow knowledge slightly outperforms WDD, driven by correct identification of `daxgen.py` and explicit "Scatter-Gather" wording.

---

## 4. Example Comparisons

### 4.1 WDD Wins (WDD >> Knowledge)

#### q050: What is a primary objective of the contemporary genomic era as demonstrated by this project?

| Context | Score | Model Answer |
|---------|-------|--------------|
| **WDD** | 5 | "The 1000 Genomes project, as demonstrated by this workflow, aims to provide a reference for human variation and identifies mutational overlaps to establish a null distribution for rigorous statistical evaluation of potential disease-related mutations." |
| Knowledge | 1 | "The provided context does not contain enough information to answer what the primary objective of the contemporary genomic era is. It describes the technical process of the 1000genome workflow but does not state its broader scientific goals or objectives." |

**Why:** Trial2 WDD `workflow_description` includes "reference for human variation," "null distribution," and "disease-related mutations." Trial2 knowledge focuses on technical structure and does not state broader genomic-era objectives.

#### q031: What is the primary scientific objective of the 1000 Genomes workflow?

| Context | Score |
|---------|-------|
| **WDD** | 4 |
| Knowledge | 1 |

**Why:** WDD `workflow_description` provides the high-level purpose; knowledge abstains.

#### q019: How does the system locate the specific software executables?

| Context | Score |
|---------|-------|
| **WDD** | 4 |
| Knowledge | 1 |

**Why:** WDD task catalog lists executables; knowledge lacks this detail.

### 4.2 WDD Losses (Knowledge >> WDD)

#### q017: Which script is responsible for the dynamic generation of workflow dependencies?

| Context | Score | Model Answer |
|---------|-------|--------------|
| WDD | 2 | "The `ares_1kgenome_parallel.sbatch` script is responsible... The WDD was compiled from this script." |
| **Knowledge** | 4 | "The `daxgen.py` script (Pegasus DAG generator) is responsible for the dynamic generation of workflow dependencies." |

**Why:** Trial2 WDD metadata lists `source_file: ares_1kgenome_parallel.sbatch` and `version_notes: "Initial WDD compiled from ares_1kgenome_parallel.sbatch."` The reference expects `daxgen.py`, which the knowledge document correctly identifies. The WDD was generated from the sbatch wrapper, not the Pegasus DAX generator.

#### q045: What design pattern is used to process the massive genomic releases at scale?

| Context | Score | Model Answer |
|---------|-------|--------------|
| WDD | 3 | "The 1000 Genomes workflow uses a **hybrid** design pattern, incorporating **scatter_gather** and **broadcast** secondary patterns." |
| **Knowledge** | 5 | "The workflow uses a Scatter-Gather design pattern... The `individuals` task scatters the processing... and the `individuals_merge` task gathers the results." |

**Why:** Trial2 knowledge explicitly labels the stage "Scatter-Gather" and describes scatter/gather in plain language. The WDD encodes this in `workflow_patterns` (e.g., `scatter_gather`), but the model answered "hybrid" with secondary patterns, which the judge scored lower than the direct "Scatter-Gather" phrasing.

#### q010: How does the workflow architecture handle the massive scale of chromosome VCF files?

| Context | Score |
|---------|-------|
| WDD | 4 |
| **Knowledge** | 5 |

**Why:** Both describe parallel processing; knowledge's explicit "scatter-gather" and line-range splitting matches the reference more closely.

---

## 5. WDD-Focused Analysis

### 5.1 What the WDD Did Well (Trial 2)

1. **`workflow_description`** — Project-level facts (2,504 individuals, 26 populations, null distribution, disease-related mutations, FTP URL).
2. **Task structure** — Correct task set, order, and dependencies.
3. **Data flow** — `data_objects`, `pc_edges`, `parallelism_model`.
4. **Design patterns** — `workflow_patterns` with scatter_gather, broadcast.
5. **Executable names** — Task catalog lists `individuals.py`, `individuals_merge.py`, etc.

### 5.2 Where the WDD Fell Short

1. **Source file mismatch** — WDD was compiled from `ares_1kgenome_parallel.sbatch`; reference and knowledge expect `daxgen.py`. Template could encourage identifying the primary orchestration/DAX generator.
2. **Pattern naming** — Schema uses `scatter_gather`; reference expects "Scatter/Gather." Adding a human-readable pattern summary could help.
3. **Executable path** — `executable` is script name only; no `bin/` or path when relevant.

### 5.3 Workflow Knowledge (Trial 2) Strengths

Trial2 knowledge:
- Explicitly references `daxgen.py` as the Pegasus DAG generator.
- Uses "Scatter-Gather" in stage and task descriptions.
- Describes line-range splitting and gather merge clearly.
- Was generated from code analysis (unlike trial3's "without access to file contents").

---

## 6. Recommendations for template_WDD.yml

### 6.1 Identify Primary Orchestration Source

**Recommendation:** When multiple files define the workflow (e.g., sbatch + daxgen.py), add guidance to identify the primary orchestration source:

```yaml
primary_orchestration_source:
  _status: required_static
  _extract: >
    The file that defines the workflow graph (e.g., daxgen.py for Pegasus,
    main.nf for Nextflow). May differ from the file that invokes execution
    (e.g., sbatch script). Used for "which script generates dependencies?" Q&A.
  _value: null
```

**Rationale:** Addresses q017-style mismatches when WDD is compiled from a wrapper rather than the DAG generator.

### 6.2 Add Human-Readable Pattern Summary

**Recommendation:** In `workflow_patterns`, add a short narrative field:

```yaml
pattern_summary:
  _status: required_static
  _extract: >
    One-sentence summary using standard pattern names (e.g., "Scatter-Gather",
    "Pipeline") that match common Q&A phrasing. Enables alignment with
    reference answers that use these terms.
  _value: null
```

**Rationale:** Reduces q045-style scoring gaps when schema uses `scatter_gather` but reference expects "Scatter/Gather."

### 6.3 Executable Path (same as 20260304 report)

Add `executable_path` or similar to capture script location when derivable from source.

---

## 7. Summary Table: Question Types vs. Context (20260309-084724)

| Question Type | WDD Strength | Knowledge Strength | Typical Outcome |
|---------------|-------------|-------------------|-----------------|
| Primary objective, genomic-era goals | Strong | Weak | WDD wins |
| Project stats (individuals, populations) | Strong | Moderate | WDD wins |
| Task sequence, dataflow | Strong | Strong | Both good |
| Scatter/Gather design pattern | Moderate | Strong (explicit phrasing) | Knowledge wins |
| Which script generates dependencies | Weak (wrong source_file) | Strong | Knowledge wins |
| Executable location | Weak | Moderate | Knowledge wins |

---

## 8. Appendix: Files Referenced

- **Evaluation run:** `evaluation_runs/20260309-084724/qa_eval/`
- **Summary:** `evaluation_runs/20260309-084724/qa_eval/summary.json`
- **WDD used:** `workflow_wdd/1000genome-wdd-gemini-trial2.yaml`
- **Workflow knowledge used:** `workflow_knowledge/1000genome-knowledge-gemini-trial2.md`
- **Q&A prompts:** `doc/1000genome-workflow-knowledge-eval-{1,2,3}.txt`
- **Template:** `template_separate_docs/template_WDD.yml`
