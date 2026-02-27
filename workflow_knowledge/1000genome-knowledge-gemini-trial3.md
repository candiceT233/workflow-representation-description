# Workflow Knowledge Report for 1000genome

**Agent:** gemini
**Analysis Date:** 2026-02-27
**Static Analysis Only:** This report is based exclusively on static analysis of the workflow repository files. No runtime or deployment details are included.

**NOTE:** The analysis was performed without access to file contents due to tool limitations. The report is based on file names, directory structure, and common patterns in bioinformatics workflows. All findings should be considered assumptions.

## 1. Workflow Stages and Tasks

The workflow is organized into two main stages: Pre-processing and Analysis.

### Stage: Pre-processing
- **task:prepare_input**
  - **Description:** [ASSUMPTION] Prepares the input data for the main analysis. Likely corresponds to the `prepare_input.sh` script.
  - **Inputs:** `unknown`
  - **Outputs:** `data:input_data`

### Stage: Analysis
- **task:individuals**
  - **Description:** [ASSUMPTION] Processes data for each individual in the cohort. This is likely a scatter operation where the work is parallelized. Corresponds to `bin/individuals.py`.
  - **Inputs:** `data:input_data`
  - **Outputs:** `data:individual_results`

- **task:individuals_merge**
  - **Description:** [ASSUMPTION] Merges the results from all `individuals` tasks into a single dataset. This is a gather operation. Corresponds to `bin/individuals_merge.py`. The presence of an MPI version (`individuals_merge_mpi.py`) suggests this can be a bottleneck.
  - **Inputs:** `data:individual_results`
  - **Outputs:** `data:merged_results`

- **task:frequency**
  - **Description:** [ASSUMPTION] Calculates frequencies (e.g., allele frequencies) from the merged results. Corresponds to `bin/frequency.py`.
  - **Inputs:** `data:merged_results`
  - **Outputs:** `data:frequencies`

- **task:mutation_overlap**
  - **Description:** [ASSUMPTION] Identifies overlapping mutations from the merged results. Corresponds to `bin/mutation_overlap.py`.
  - **Inputs:** `data:merged_results`
  - **Outputs:** `data:overlaps`

- **task:sifting**
  - **Description:** [ASSUMPTION] Filters the results based on frequency and overlap data. Corresponds to `bin/sifting.py`.
  - **Inputs:** `data:frequencies`, `data:overlaps`
  - **Outputs:** `data:sifted_results`

## 2. Data Object Registry

- **data:input_data**
  - **Description:** [ASSUMPTION] The initial dataset for the workflow, prepared by the `prepare_input` task.
  - **Format:** `unknown`

- **data:individual_results**
  - **Description:** [ASSUMPTION] Intermediate files, with one file per individual processed by the `individuals` task.
  - **Format:** `unknown`

- **data:merged_results**
  - **Description:** [ASSUMPTION] A single, aggregated dataset containing the results from all individuals.
  - **Format:** `unknown`

- **data:frequencies**
  - **Description:** [ASSUMPTION] A dataset containing frequency calculations.
  - **Format:** `unknown`

- **data:overlaps**
  - **Description:** [ASSUMPTION] A dataset containing information about overlapping mutations.
  - **Format:** `unknown`

- **data:sifted_results**
  - **Description:** [ASSUMPTION] The final, filtered output of the workflow.
  - **Format:** `unknown`

## 3. Producer-Consumer Edges

- **pc:prepare_input->individuals:input_data**
  - **Pattern:** `1-to-N (scatter)`
  - **Rationale:** The initial data is distributed to many `individuals` tasks.
- **pc:individuals->individuals_merge:individual_results**
  - **Pattern:** `N-to-1 (gather)`
  - **Rationale:** The `individuals_merge` task collects and combines results from all `individuals` tasks.
- **pc:individuals_merge->frequency:merged_results**
  - **Pattern:** `1-to-1`
  - **Rationale:** The `frequency` task processes the single merged results file.
- **pc:individuals_merge->mutation_overlap:merged_results**
  - **Pattern:** `1-to-1`
  - **Rationale:** The `mutation_overlap` task also processes the single merged results file. This is a fan-out from the merged results.
- **pc:frequency->sifting:frequencies**
  - **Pattern:** `1-to-1`
  - **Rationale:** The `sifting` task uses the output of the `frequency` task.
- **pc:mutation_overlap->sifting:overlaps**
  - **Pattern:** `1-to-1`
  - **Rationale:** The `sifting` task also uses the output of the `mutation_overlap` task. This is a fan-in to the sifting task.

## 4. Workflow-Level Pattern

- **Pattern:** `hybrid (scatter_gather, pipeline)`
- **Rationale:** The workflow starts with a `scatter_gather` pattern (`individuals` -> `individuals_merge`). The subsequent tasks (`frequency`, `mutation_overlap`, `sifting`) form a directed acyclic graph that can be characterized as a `pipeline` with some parallel branches.

## 5. I/O Behavioral Hints

- **Small-file overhead:** The `scatter` pattern (`individuals` task) is likely to generate a large number of intermediate files (`data:individual_results`). This can lead to inefficient I/O operations and strain on the file system, a classic "small file problem".
- **I/O Bottleneck (Gather):** The `individuals_merge` task needs to read all the intermediate files produced by the `individuals` tasks. This can be a significant I/O bottleneck. The existence of `individuals_merge_mpi.py` strongly suggests this is a known issue that has been addressed with a parallel I/O implementation using MPI-IO.
- **Data Reuse:** The `data:merged_results` object is reused by both the `frequency` and `mutation_overlap` tasks. Depending on the size of this data, caching it in memory could be beneficial.
