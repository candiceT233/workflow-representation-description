# Workflow Knowledge Report: 1000genome

**Agent:** opencode  
**Date:** 2026-03-10  
**Workflow:** 1000genome (1000 Genomes Project Mutation Overlap Workflow)  
**Framework:** Pegasus WMS  

---

## 1. Stages and Tasks

### Stage 1: Individuals Processing
Parses VCF files to extract SNP variants for each individual.

| Task | Description | Executable |
|------|-------------|------------|
| `individuals` | Parses chromosome VCF file, extracts SNP data per individual based on allele frequency thresholds. Splits large VCF files into chunks for parallel processing. | `bin/individuals.py` |
| `individuals_merge` | Merges output from multiple individuals jobs for the same chromosome. Concatenates individual SNP files from chunked tar archives. | `bin/individuals_merge.py` |

### Stage 2: Sifting
Processes Variant Effect Predictor (VEP) annotations to compute SIFT scores.

| Task | Description | Executable |
|------|-------------|------------|
| `sifting` | Filters VEP annotation files to extract SIFT scores and rs numbers for each chromosome. Uses grep to find deleterious/tolerated variants. | `bin/sifting.py` |

### Stage 3: Analysis
Performs mutation overlap and frequency analysis by population.

| Task | Description | Executable |
|------|-------------|------------|
| `mutation_overlap` | Measures overlap in mutations (SNPs) among pairs of individuals by population and chromosome. Computes pairwise mutations, generates histograms and colormap visualizations. | `bin/mutation_overlap.py` |
| `frequency` | Measures frequency of overlapping mutations by randomly sampling individuals. Runs 1000 iterations with 52 individuals per sample. Generates statistical distribution of mutation overlaps. | `bin/frequency.py` |

---

## 2. Data Objects

### Input Files
| Data Object | Format | Description |
|-------------|--------|-------------|
| `ALL.chr{1-10}.250000.vcf` | VCF (uncompressed) | Phase3 VCF data per chromosome, 250k lines each |
| `ALL.chr{1-10}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf` | VCF (gzipped) | VEP annotation files with SIFT scores |
| `columns.txt` | TSV | List of all 2504 individual genome IDs in dataset |
| `populations/{EUR,AMR,EAS,AFR,SAS,GBR}` | Plain text | Individual IDs belonging to each super population |

### Intermediate Files
| Data Object | Format | Description |
|-------------|--------|-------------|
| `chr{N}n-{start}-{stop}.tar.gz` | tar.gz | Chunked output from individuals job: contains per-individual SNP files for a line range |
| `chr{N}n.tar.gz` | tar.gz | Merged individuals output: all per-individual SNP files for a chromosome |
| `sifted.SIFT.chr{N}.txt` | Plain text | SIFT scores and rs numbers per chromosome |

### Output Files
| Data Object | Format | Description |
|-------------|--------|-------------|
| `chr{N}-{POP}.tar.gz` | tar.gz | Mutation overlap results (txt files + png plots) |
| `chr{N}-{POP}-freq.tar.gz` | tar.gz | Frequency analysis results (histograms + plots) |

---

## 3. Producer-Consumer Dependencies

### Dependency Graph (Task-Level)

```
                    columns.txt
                        |
    +-------------------+-------------------+
    |                                       |
    v                                       v
individuals (chunks)  ----->  individuals_merge  -->  mutation_overlap
    |                                       |                   |
    |                                       |                   |
    v                                       v                   v
VCF file                              sifted.SIFT.chrN   columns.txt
                                        |                   |
                                        v                   v
                                  sifting             population files
                                        |
                                        v
                              annotation VCF
```

### Edge Classification

| Producer | Consumer | Pattern | Rationale |
|----------|----------|---------|-----------|
| `individuals` (chunk) | `individuals_merge` | **Fan-in merge** | Multiple parallel chunks must be combined per chromosome |
| `individuals_merge` | `mutation_overlap` | **Broadcast** | Same merged data used for all populations |
| `individuals_merge` | `frequency` | **Broadcast** | Same merged data used for all populations |
| `sifting` | `mutation_overlap` | **Broadcast** | SIFT scores required by all population analyses |
| `sifting` | `frequency` | **Broadcast** | SIFT scores required for frequency analysis |
| `columns.txt` | `individuals` | **Static input** | Referenced by all individuals jobs |
| `columns.txt` | `mutation_overlap` | **Static input** | Required for individual ID mapping |
| `columns.txt` | `frequency` | **Static input** | Required for individual ID mapping |
| `population files` | `mutation_overlap` | **Parameter sweep** | One job per (chromosome, population) pair |
| `population files` | `frequency` | **Parameter sweep** | One job per (chromosome, population) pair |

---

## 4. Workflow Structure

### High-Level Pattern: **Fork-Join with Parameter Sweep**

1. **Fork Stage**: `individuals` tasks run in parallel, one per chunk per chromosome (configurable via `-i` flag)
2. **Join Stage**: `individuals_merge` aggregates chunks into single merged file per chromosome
3. **Parallel Stage**: `sifting` runs independently per chromosome
4. **Parameter Sweep**: For each chromosome, spawn (6 populations × 2 job types) = 12 analysis jobs

### Topology Characteristics

- **Parallelism**: 
  - Individuals jobs: N chromosomes × M chunks per chromosome (default M=1, configurable)
  - Analysis jobs: N chromosomes × 6 populations × 2 types = 12N jobs
  - Sifting jobs: N chromosomes (1 per chromosome)

- **Data Flow**: 
  - Each chromosome follows: individuals -> merge -> (mutation_overlap + frequency) per population
  - Sifting is independent of individuals processing but feeds analysis

- **Iteration**: 
  - No explicit loops; parameter sweep generates multiple jobs
  - `frequency` task performs internal iteration (1000 random samples)

---

## 5. I/O Behavioral Hints

### Small-File Overhead
- **High concern**: Individuals jobs create one file per individual (2504 files per chromosome chunk), then archive to tar.gz
- **Impact**: Filesystem operations for individual file creation/deletion may dominate runtime
- **Evidence**: `individuals.py:69-107` creates files per individual, then `compress()` archives them

### Partial Reads
- **Medium concern**: VCF files processed line-by-line; individuals job reads specific line ranges
- **Evidence**: `individuals.py:53` uses `rawdata[counter:ending]` slice
- **Mitigation**: Chunking reduces per-job file size but increases file count

### Format Mismatch Risk
- **Low concern**: VCF format is standardized; code handles both .vcf and .vcf.gz
- **Evidence**: individuals.py uses `shutil` for potential decompression

### Unnecessary Serialization
- **Medium concern**: Data passed through tar archives between stages
- **Evidence**: `individuals_merge` extracts all files, processes, then re-archives
- **Impact**: CPU time spent on compression/decompression

### Data Reuse
- **Observed**: Merged individuals file (`chrNn.tar.gz`) is reused across all populations for same chromosome
- **Positive**: Avoids recomputation; only read once per analysis job

### Metadata-Heavy Patterns
- **High concern**: VCF files contain extensive metadata (headers, annotations)
- **Evidence**: sifting.py filters out header lines (# prefix) at `sifting.py:49-50`
- **Evidence**: individuals.py skips non-data lines at `individuals.py:53`

---

## 6. Notes

- **Static Analysis Limitations**: Memory requirements, runtime estimates, and execution site configurations are deployment-specific and excluded per instructions
- **Assumption**: Default configuration with 10 chromosomes, 6 populations, 1 individuals job per chromosome
- **Input Data**: Uses 1000 Genomes Phase3 release (20130502), 2504 individuals across 26 populations
