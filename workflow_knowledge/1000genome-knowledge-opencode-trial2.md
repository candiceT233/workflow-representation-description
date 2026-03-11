# 1000Genome Workflow Knowledge Report

**Workflow Name:** 1000-genome  
**Agent:** opencode  
**Analysis Method:** Static code analysis  

---

## 1. Workflow Overview

The 1000Genome workflow analyzes genomic data from the 1000 Genomes Project to identify mutational overlaps among individuals across different populations. It processes Variant Call Format (VCF) files containing Single Nucleotide Polymorphisms (SNPs) and performs cross-population mutation analysis using SIFT (Sorting Intolerant From Tolerant) scores for variant pathogenicity filtering.

**Workflow Framework:** Pegasus WMS (Workflow Management System)  
**Entry Point:** `daxgen.py` - Generates workflow DAG using Pegasus API  

---

## 2. Stages and Tasks

### Stage 1: Individual Extraction (per chromosome, parallelizable)

#### Task: `individuals`
- **Purpose:** Extract individual-specific mutation data from VCF files
- **Executable:** `bin/individuals.py` or `bin/individuals` (bash version)
- **Inputs:**
  - `ALL.chrX.250000.vcf` - VCF file for chromosome X (250,000 lines)
  - `columns.txt` - Tab-separated list of individual sample IDs (2,504 individuals)
- **Arguments:** `<vcf_file> <chromosome_number> <start_line> <stop_line> <total_lines>`
- **Processing:**
  - Reads VCF file lines within specified range
  - For each individual, extracts: position, REF, ALT, QUAL, AF (allele frequency)
  - Filters by allele frequency threshold (AF >= 0.5 or AF < 0.5 with homozygous alternative)
  - Creates one file per individual containing their mutations
- **Outputs:**
  - `chrXn-counter-stop.tar.gz` - Compressed tarball containing per-individual mutation files
- **Parallelism:** Configurable via `-i` flag (default: splits each chromosome into multiple jobs)

#### Task: `individuals_merge`
- **Purpose:** Merge chunked individual files from parallel individuals jobs
- **Executable:** `bin/individuals_merge.py` or `bin/individuals_merge`
- **Arguments:** `<chromosome_number> <tar_file1> <tar_file2> ...`
- **Processing:**
  - Extracts all chunked tar files
  - Concatenates per-individual files with same filename
  - Re-archives into single merged tarball
- **Outputs:**
  - `chrXn.tar.gz` - Merged individual mutations for chromosome

### Stage 2: Sifting (per chromosome)

#### Task: `sifting`
- **Purpose:** Filter variants using SIFT scores from VEP (Variant Effect Predictor) annotations
- **Executable:** `bin/sifting.py` or `bin/sifting`
- **Inputs:**
  - `ALL.chrX.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf` - VEP-annotated VCF
- **Arguments:** `<vep_vcf_file> <chromosome_number>`
- **Processing:**
  - Uses grep to filter for "deleterious" or "tolerated" keywords
  - Extracts: line number, rs ID, ENSG gene ID, SIFT score, phenotype
  - Parses VEP INFO field (pipe-delimited)
- **Outputs:**
  - `sifted.SIFT.chrX.txt` - Text file with filtered variants per chromosome

### Stage 3: Mutation Analysis (per chromosome × per population)

#### Task: `mutation_overlap`
- **Purpose:** Measure mutation overlap between pairs of individuals within a population
- **Executable:** `bin/mutation_overlap.py`
- **Inputs:**
  - `chrXn.tar.gz` - Merged individual data
  - `sifted.SIFT.chrX.txt` - SIFT-filtered variants
  - `population_file` (e.g., AFR, EUR, EAS, AMR, SAS, GBR, ALL)
  - `columns.txt` - Individual sample IDs
- **Arguments:** `-c <chromosome_number> -pop <population>`
- **Processing:**
  - Extracts tarball to access per-individual files
  - Reads population membership from population file
  - Filters individuals by population
  - Reads SIFT-scored rs numbers
  - Computes pairwise mutation overlaps (set intersection)
  - Generates multiple analysis outputs:
    - Half-pair overlaps
    - Total pairwise overlaps
    - Random sampling overlaps (n_runs=1)
    - Gene pair combinations
  - Creates PNG visualizations (histograms, colormaps)
- **Outputs:**
  - `chrX-population.tar.gz` - Contains:
    - `output_no_sift/` - Text files with overlap results
    - `plots_no_sift/` - PNG visualization files

#### Task: `frequency`
- **Purpose:** Measure frequency distribution of overlapping mutations via random sampling
- **Executable:** `bin/frequency.py`
- **Inputs:**
  - `chrXn.tar.gz` - Merged individual data
  - `sifted.SIFT.chrX.txt` - SIFT-filtered variants
  - `population_file`
  - `columns.txt`
- **Arguments:** `-c <chromosome_number> -pop <population>`
- **Processing:**
  - Similar data extraction as mutation_overlap
  - Runs 1000 Monte Carlo iterations (n_runs=1000)
  - Each iteration selects 52 random individuals
  - Computes mutation overlap counts
  - Generates histogram distributions
- **Outputs:**
  - `chrX-population-freq.tar.gz` - Contains:
    - `output_no_sift/` - Histogram data files
    - `plots_no_sift/` - Histogram PNG plots

---

## 3. Data Object Registry

| Object Type | Filename Pattern | Format | Description |
|-------------|------------------|--------|-------------|
| **Input** | `ALL.chr{1-10}.250000.vcf` | VCF (gzipped) | Raw variant calls per chromosome |
| **Input** | `ALL.chr{1-10}.phase3_*.vcf` | VCF (text) | VEP-annotated variants with SIFT scores |
| **Input** | `columns.txt` | TSV | List of 2,504 individual sample IDs |
| **Input** | `{AFR,AMR,EAS,EUR,GBR,SAS,ALL}` | Text | Population membership files |
| **Intermediate** | `chr{n}n-{start}-{stop}.tar.gz` | tar.gz | Per-chunk individual mutations |
| **Intermediate** | `chr{n}n.tar.gz` | tar.gz | Merged individual mutations per chromosome |
| **Intermediate** | `sifted.SIFT.chr{n}.txt` | Text | SIFT-filtered variants (rs IDs, scores) |
| **Output** | `chr{n}-{pop}.tar.gz` | tar.gz | Mutation overlap results + plots |
| **Output** | `chr{n}-{pop}-freq.tar.gz` | tar.gz | Frequency analysis results + plots |

---

## 4. Producer-Consumer Dependencies

### Dependency Graph (per chromosome)

```
                    columns.txt
                        |
                        v
    +-------------------+-------------------+
    |                                       |
    v                                       v
individuals (chunk 1)              individuals (chunk N)
    |                                       |
    v                                       v
chr1n-1-50000.tar.gz           chr1n-200000-250000.tar.gz
    |                                       |
    +-------------------+-------------------+
                        |
                        v
              individuals_merge
                        |
                        v
                   chr1n.tar.gz
                        |
        +---------------+---------------+
        |                               |
        v                               v
   mutation_overlap              frequency
   (per pop)                    (per pop)
```

### Edge Classification

| From Task | To Task | Edge Type | Rationale |
|-----------|---------|------------|-----------|
| `individuals` (chunk i) | `individuals_merge` | Data dependency | Merge input requires all chunk outputs |
| `individuals_merge` | `mutation_overlap` | Data dependency | Analysis requires merged individual data |
| `individuals_merge` | `frequency` | Data dependency | Frequency requires merged individual data |
| `sifting` | `mutation_overlap` | Data dependency | Overlap analysis uses SIFT-filtered variants |
| `sifting` | `frequency` | Data dependency | Frequency uses SIFT-filtered variants |

### Job Counts (for default data.csv with 10 chromosomes × 7 populations)

- **individuals** tasks: 10 × N_chunks (configurable, default N_chunks=1)
- **individuals_merge** tasks: 10
- **sifting** tasks: 10
- **mutation_overlap** tasks: 10 × 7 = 70
- **frequency** tasks: 10 × 7 = 70

---

## 5. Workflow Structure and Pattern

### High-Level Pattern: **DAG with Parallel Fan-out/Fan-in**

The workflow exhibits a **three-stage pipeline** structure:

1. **Stage 1 (Parallel per chromosome):** 
   - `individuals` tasks fan out from single VCF input to N chunk outputs
   - `individuals_merge` fans in chunks to single merged output
   - `sifting` runs independently per chromosome

2. **Stage 2 (Analysis matrix):**
   - Cartesian product of chromosomes (10) × populations (7)
   - Creates 70 parallel analysis branches
   - Each branch runs both `mutation_overlap` and `frequency`

3. **Stage 3 (Output aggregation):**
   - Results staged out to output directory
   - No final merge step

### Control Flow

- **Iteration:** No explicit iteration; workflow generates all combinations via DAG generation loop in `daxgen.py`
- **Branching:** 70 parallel branches for analysis stage
- **Merging:** Fan-in pattern for `individuals_merge` (N → 1 per chromosome)
- **No conditional execution:** All tasks generated statically

---

## 6. I/O Behavioral Hints (Static Analysis)

### File Access Patterns

| Task | Read Pattern | Write Pattern | Notes |
|------|--------------|---------------|-------|
| individuals | Sequential line read of VCF | Random access (per-individual files) | Large file sequential scan, creates 2504 files |
| individuals_merge | Sequential tar extraction | Sequential write | Full dataset extraction/rewrap |
| sifting | Sequential + grep subprocess | Sequential | External grep process spawning |
| mutation_overlap | Full tar extraction | Multiple files + PNG plots | Heavy extraction, matplotlib I/O |
| frequency | Full tar extraction | Many small files (1000 runs) | High iteration count |

### Potential I/O Concerns

1. **Small-file overhead (individuals):** Creates ~2504 small files per chromosome chunk; filesystem metadata operations may dominate
   - Evidence: Individual files named `chrX.sampleID` created in loop

2. **Full dataset extraction (analysis tasks):** Both mutation_overlap and frequency extract entire tarball before processing
   - Evidence: `tar.extractall()` in both scripts

3. **Format parsing overhead (sifting):** Uses subprocess grep + manual parsing
   - Evidence: `subprocess.run(["grep..."])` in `sifting.py`

4. **Repeated SIFT file reads (analysis):** Both mutation_overlap and frequency independently read the same sifted.SIFT.chrX.txt
   - Evidence: Both scripts call `read_rs_numbers(siftfile)`

5. **Serialized output (frequency):** 1000 iterations writing separate files per run
   - Evidence: Loop `for run in range(n_runs)` with file-per-run output

6. **In-memory data structures (mutation_overlap):** Loads entire pairwise overlap matrix
   - Evidence: `np.zeros((n_p, n_p))` creates N×N matrix

---

## 7. Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-D` / `--dataset` | `20130502` | Dataset folder name |
| `-f` / `--datafile` | `data.csv` | CSV file listing chromosomes |
| `-i` / `--individuals-jobs` | `1` | Number of parallel individuals jobs per chromosome |
| `-e` / `--execution-site` | `local` | Execution site (local/condorpool/cori) |
| `-b` / `--bash-jobs` | False | Use bash scripts instead of Python |
| `-d` / `--decaf` | False | Use Decaf in-situ framework |
| `-c` / `--pmc` | False | Use Pegasus MPI Cluster |

---

## 8. Input Data Summary

- **VCF files:** 10 chromosomes (chr1-chr10), 250,000 lines each
- **Populations:** 7 (AFR, AMR, EAS, EUR, GBR, SAS, ALL)
- **Individuals:** 2,504 total samples
- **Annotation files:** VEP-annotated VCF files with SIFT scores

---

*Generated by static analysis of workflow repository code.*
