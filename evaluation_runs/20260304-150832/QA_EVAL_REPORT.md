# Q&A Evaluation Report: WDD vs Workflow Knowledge

**Run folder:** `evaluation_runs/20260304-150832`  
**Date:** 2026-03-06  
**Scope:** 74 questions × 2 context types × 1 agent (Claude)  
**Trial used:** 3 — `1000genome-wdd-gemini-trial3.yaml`, `1000genome-knowledge-gemini-trial3.md`

---

## 1. Executive Summary

The **20260304-150832** run produced **67 successful answers** out of 74 per context type. **WDD significantly outperformed workflow knowledge** across all question sections:

| Context Type       | Success | Judge Mean | Std   |
|--------------------|---------|------------|-------|
| wdd_yaml           | 67/74   | **2.52**   | 1.52  |
| workflow_knowledge | 67/74   | 1.69       | 1.22  |

**Mean score difference: +0.84** (WDD better). WDD scored higher on 32 questions, workflow knowledge on 8, and 27 were ties.

The workflow knowledge document (trial3) was generated "without access to file contents" and relied on directory structure and assumptions. It contained structural inaccuracies (wrong task order, extra tasks, unknown inputs). The WDD (trial3) had richer metadata and correct task structure from static analysis of the Pegasus DAX generator.

---

## 2. Error Types

### 2.1 Infrastructure Failures (7 questions: q068–q074)

| QID Range | Context Types | Success | Error Type | Example |
|-----------|---------------|---------|------------|---------|
| q068–q074 | Both          | 0/7 each| Exit 1     | `exit 1: "` (truncated/empty) |

All 7 failures occurred on both wdd_yaml and workflow_knowledge. The error message is truncated to `exit 1: "` — likely a rate limit, timeout, or transient API error toward the end of the run (questions 68–74 are from `1000genome-workflow-knowledge-eval-3.txt`).

### 2.2 Semantic Error Types (from 67 successful pairs)

| Error Type | Description | WDD vs Knowledge |
|------------|-------------|------------------|
| **Missing project metadata** | Dataset stats (2,504 individuals, 26 populations) | WDD has it in `workflow_description`; Knowledge lacks it |
| **Wrong task structure** | Task order, dependencies, task count | WDD correct from DAX; Knowledge has prepare_input, wrong edges |
| **Missing data source** | Where input comes from (IGSR, Phase 3 VCF) | WDD has it in task descriptions; Knowledge says "unknown" |
| **Missing executable path** | Location of scripts (e.g., `bin/`) | Knowledge has it from directory structure; WDD has executable name only |
| **Missing design pattern** | Scatter/Gather, etc. | WDD has it in `workflow_patterns` / `pc_pattern`; Knowledge less explicit |

---

## 3. Section-by-Section Analysis

### 3.1 Section Breakdown (Mean Score)

| Section | WDD Mean | WK Mean | Diff | WDD Advantage |
|---------|----------|---------|------|---------------|
| SECTION 1: SCIENTIFIC PURPOSE AND BIOLOGICAL SEMANTICS | 1.62 | 1.19 | +0.42 | Project stats in workflow_description |
| SECTION 2: WORKFLOW DATAFLOW AND TASK DEPENDENCIES | **3.55** | 2.30 | **+1.25** | Correct task order, P-C patterns, scatter/gather |
| SECTION 3: REPOSITORY USAGE AND SYSTEM MECHANICS | 2.09 | 1.36 | +0.73 | Structural clarity |
| SECTION 4: INPUT FILES, OUTPUT FILES, AND DATA FORMATS | **3.30** | 2.10 | **+1.20** | Data source, formats, data objects |

**Largest WDD gains:** Section 2 (dataflow) and Section 4 (inputs/outputs), where structured WDD fields (stages, tasks, data_objects, pc_edges) provide precise answers.

---

## 4. Example Comparisons

### 4.1 WDD Wins (WDD >> Knowledge)

#### q051: How many individuals and distinct populations were successfully mapped?

| Context | Score | Model Answer |
|---------|-------|--------------|
| **WDD** | 5 | "Based on the `metadata.workflow_description` field: **2,504 individuals** across **26 distinct populations** were successfully mapped." |
| Knowledge | 1 | "The provided workflow knowledge context does not contain information about how many individuals or distinct populations were successfully mapped." |

**Why:** Trial3 WDD `workflow_description` includes "2,504 individuals across 26 different populations." Trial3 knowledge states it was "without access to file contents" and covers only technical structure.

#### q022: Where does the workflow retrieve its primary genomic input data from?

| Context | Score | Model Answer |
|---------|-------|--------------|
| **WDD** | 5 | "The workflow retrieves its primary genomic input from the **1000 Genomes Project**, specifically **Phase 3 data**, processed as VCF files... `data:vcf_chromosome_chunk`... `data:vep_annotation_vcf`... From the `task:individuals` description: *'Fetches and parses Phase3 data from the 1000 Genomes Project by chromosome.'*" |
| Knowledge | 1 | "The context does not contain enough information... The report notes that the `prepare_input` task's inputs are listed as `unknown`... No information about the actual data source (e.g., URLs, databases, file paths) is available." |

**Why:** WDD task descriptions and data_objects specify sources; knowledge has "unknown" inputs and no data source.

#### q038: How does the workflow manage the exceptionally large size of the chromosome VCF files?

| Context | Score |
|---------|-------|
| **WDD** | 5 |
| Knowledge | 1 |

**Why:** WDD encodes scatter/gather in `workflow_patterns`, `pc_pattern` (n_to_1), and `parallelism_model`; knowledge does not describe this pattern clearly.

### 4.2 WDD Losses (Knowledge >> WDD)

#### q030: Where are the core executable scripts located in the repository?

| Context | Score | Model Answer |
|---------|-------|--------------|
| WDD | 3 | "The core executable scripts identified are: `individuals.py`, `individuals_merge.py`, etc. However, **the WDD does not specify the exact subdirectory** within the repository where these scripts reside." |
| **Knowledge** | 5 | "The core executable scripts are located in the `bin/` directory... `bin/individuals.py`, `bin/individuals_merge.py`, `bin/frequency.py`, etc." |

**Why:** Knowledge was derived from directory structure and explicitly mentions `bin/`. WDD `executable` fields give script names only, not paths.

#### q008: What are the five core task classes?

| Context | Score | Notes |
|---------|-------|-------|
| WDD | 3 | Lists 5 correct tasks but omits "Populations" (reference includes it). |
| Knowledge | 4 | Lists 6 tasks (includes prepare_input); task order differs from reference. |

**Why:** Reference expects "Individuals, Individuals_Merge, Populations, Sifting, Mutations_Overlap, Frequency." Trial3 WDD has no Populations task; trial3 knowledge has a different structure. Both deviate from the reference in different ways.

---

## 5. WDD-Focused Analysis

### 5.1 What the WDD Did Well (Trial 3)

1. **`workflow_description`** — Project-level facts (2,504 individuals, 26 populations, null distribution, disease-related mutations).
2. **Task structure** — Correct task set, order, and dependencies from DAX analysis.
3. **Data flow** — `data_objects`, `pc_edges`, `pc_pattern` (scatter/gather, n_to_1).
4. **Data sources** — External inputs and Phase 3 VCF described in task and data_objects.
5. **Design patterns** — `workflow_patterns`, `parallelism_model` for scatter/gather.

### 5.2 Where the WDD Fell Short

1. **Executable path** — `executable` is script name only (e.g., `individuals.py`), not path (e.g., `bin/individuals.py`). Template could add `executable_path` or similar.
2. **Populations task** — Trial3 WDD omits a distinct "Populations" task present in the reference; this may be a DAX vs. reference mismatch.
3. **IGSR/FTP** — Reference mentions "IGSR FTP mirrors"; WDD has "1000 Genomes Project" and Phase 3 but not the specific mirror.

### 5.3 Workflow Knowledge (Trial 3) Limitations

The trial3 knowledge document states:

> "The analysis was performed **without access to file contents** due to tool limitations. The report is based on file names, directory structure, and common patterns... All findings should be considered **assumptions**."

As a result:
- Task dependencies and order differ from the actual workflow.
- Inputs are often "unknown."
- It includes `prepare_input` and different data flow.
- It does capture `bin/` paths from directory structure, which the WDD does not.

---

## 6. Recommendations for template_WDD.yml

### 6.1 Add Executable Path / Location

**Recommendation:** Extend task extraction to include script location when derivable:

```yaml
executable_path:
  _status: required_static
  _extract: >
    Relative path from repository root to the script/binary, when determinable.
    E.g., "bin/individuals.py", "scripts/train.py". Infer from: process script path
    in Nextflow, path in Pegasus Transformation, Snakemake rule script directive.
    Null if not in source.
  _value: null
```

**Rationale:** Addresses q030-style questions about where executables live.

### 6.2 Enrich workflow_description with Project Stats

**Recommendation:** In `workflow_description` extraction, add:

```yaml
_extract: >
  ... If README, manifest, or project docs state dataset scale (e.g., "2,504 individuals",
  "26 populations"), include these in the description. Supports Q&A on project scope.
```

**Rationale:** Trial3’s inclusion of 2,504/26 in `workflow_description` drove strong performance on q051.

### 6.3 Optional data_source_url for External Inputs

**Recommendation:** For `data_objects` with `category: input` and `producer_task: null`:

```yaml
source_hint:
  _status: optional_static
  _extract: >
    If code or config references a URL, FTP path, or database (e.g., IGSR FTP,
    SRA accession), record it here. Enables "where does data come from?" Q&A.
  _value: null
```

**Rationale:** Would help answer questions like q022 with more precision (e.g., IGSR FTP).

---

## 7. Summary Table: Question Types vs. Context (20260304-150832)

| Question Type | WDD Strength | Knowledge Strength | Typical Outcome |
|---------------|-------------|-------------------|-----------------|
| Project stats (individuals, populations) | Strong | Weak | WDD wins |
| Data source, input origin | Strong | Weak | WDD wins |
| Task sequence, dataflow, P-C patterns | Strong | Weak (wrong structure) | WDD wins |
| Scatter/Gather, design patterns | Strong | Weak | WDD wins |
| Executable script location (bin/) | Weak | Strong | Knowledge wins |
| Primary scientific objective | Strong | Moderate | WDD wins |

---

## 8. Appendix: Files Referenced

- **Evaluation run:** `evaluation_runs/20260304-150832/qa_eval/`
- **Summary:** `evaluation_runs/20260304-150832/qa_eval/summary.json`
- **WDD used:** `workflow_wdd/1000genome-wdd-gemini-trial3.yaml`
- **Workflow knowledge used:** `workflow_knowledge/1000genome-knowledge-gemini-trial3.md`
- **Q&A prompts:** `doc/1000genome-workflow-knowledge-eval-{1,2,3}.txt`
- **Template:** `template_separate_docs/template_WDD.yml`
