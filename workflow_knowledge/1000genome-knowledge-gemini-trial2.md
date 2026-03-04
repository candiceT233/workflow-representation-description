# Workflow Knowledge Report: 1000genome

**AGENT_NAME:** gemini
**TRIAL_ID:** trial2

This report details the static analysis of the 1000genome workflow. The analysis is based on the source code and configuration files found in the workflow repository, primarily the Pegasus DAG generator (`daxgen.py`) and the individual task scripts.

## 1. Workflow Stages and Tasks

The workflow is structured as a multi-stage pipeline that processes genomic data per chromosome. The primary stages and their constituent tasks are defined in the `daxgen.py` script.

### Stage 1: Individuals Data Processing (Scatter-Gather)

This stage processes large chromosome data files in parallel.

-   **Task `individuals` (Scatter):**
    -   **Description:** Reads a large VCF file for a single chromosome (`ALL.chr<C>.vcf`) and splits the processing into `N` parallel jobs. Each job processes a specific range of lines from the input file. It filters variants based on allele frequency and creates a set of per-individual mutation files within a compressed archive.
    -   **Inputs:**
        -   `data:ALL.chr<C>.vcf`: The primary VCF data for a chromosome.
        -   `data:columns.txt`: A file listing the individual sample IDs.
    -   **Outputs:**
        -   `data:chr<C>n-<start>-<stop>.tar.gz`: An intermediate compressed archive containing per-individual mutation files for a chunk of the chromosome data.

-   **Task `individuals_merge` (Gather):**
    -   **Description:** Collects the intermediate archives from the `individuals` tasks for a single chromosome and merges them into a final, consolidated archive of per-individual mutation files.
    -   **Inputs:**
        -   `data:chr<C>n-<start>-<stop>.tar.gz` (multiple): The set of intermediate archives from the scatter phase.
    -   **Outputs:**
        -   `data:chr<C>n.tar.gz`: A single compressed archive containing all per-individual mutation data for one chromosome.

### Stage 2: Variant Annotation

This stage runs in parallel with the Individuals Data Processing stage for each chromosome.

-   **Task `sifting`:**
    -   **Description:** Processes a VCF file containing functional annotations to extract SIFT scores. It filters for lines containing "deleterious" or "tolerated" and having an "rs" identifier, then extracts and formats relevant fields.
    -   **Inputs:**
        -   `data:ALL.chr<C>...sites.annotation.vcf`: The VCF file with SIFT annotation data.
    -   **Outputs:**
        -   `data:sifted.SIFT.chr<C>.txt`: A text file containing the filtered SIFT scores and associated variant identifiers for one chromosome.

### Stage 3: Analysis (Fan-Out)

This stage performs two parallel analyses for each chromosome, after the first two stages are complete.

-   **Task `mutation_overlap`:**
    -   **Description:** For a given chromosome and population, it calculates the overlap of mutations between pairs of individuals. It reads the merged individual data and the sifted scores, performs cross-matching, and generates plots and data files summarizing the overlap.
    -   **Inputs:**
        -   `data:chr<C>n.tar.gz`: Merged individual mutation data.
        -   `data:sifted.SIFT.chr<C>.txt`: SIFT scores for the chromosome.
        -   `data:<POP>`: A file containing a list of individuals in a specific population.
        -   `data:columns.txt`: A file listing all sample IDs.
    -   **Outputs:**
        -   `data:chr<C>-<POP>.tar.gz`: A compressed archive containing output data files and plots for the mutation overlap analysis.

-   **Task `frequency`:**
    -   **Description:** Similar to `mutation_overlap`, this task analyzes the frequency of overlapping mutations for a given chromosome and population by sampling random individuals.
    -   **Inputs:**
        -   `data:chr<C>n.tar.gz`: Merged individual mutation data.
        -   `data:sifted.SIFT.chr<C>.txt`: SIFT scores for the chromosome.
        -   `data:<POP>`: A file containing a list of individuals in a specific population.
        -   `data:columns.txt`: A file listing all sample IDs.
    -   **Outputs:**
        -
