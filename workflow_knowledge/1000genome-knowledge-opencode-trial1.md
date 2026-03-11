# Workflow Knowledge Report: 1000genome

**Agent:** opencode  
**Date:** 2026-03-10  
**Workflow Name:** 1000genome  
**Workflow Type:** Scientific/Genomics - Pegasus WMS  

---

## 1. Overview

The 1000 Genomes workflow identifies mutational overlaps using data from the 1000 Genomes Project to provide a null distribution for rigorous statistical evaluation of potential disease-related mutations. The workflow fetches, parses, and analyzes genomic data, cross-matches extracted data (which individual has which mutations) with mutation SIFT scores (functional impact prediction), and performs statistical analyses.

---

## 2. Stages and Tasks

### Stage 1: Individual Parsing

| Task | Description | Executable | Inputs | Outputs |
|------|-------------|------------|--------|---------|
| **individuals** | Parses VCF files per chromosome, extracts SNP data for each individual (only homozygous variants with allele frequency >= 0.5 or < 0.5 depending on genotype) | `bin/individuals.py` | VCF file (ALL.chr{X}.250000.vcf), columns.txt | Per-individual tar.gz files (chr{X}n-{counter}-{stop}.tar.gz) |

| Task | Description | Executable | Inputs | Outputs |
|------|-------------|------------|--------|---------|
| **individuals_merge** | Merges per-chunk individual files into a single chromosome archive | `bin/individuals_merge.py` | Multiple chr{X}n-{counter}-{stop}.tar.gz files | chr{X}n.tar.gz (merged per-chromosome individuals) |

### Stage 2: Sifting

| Task | Description | Executable | Inputs | Outputs |
|------|-------------|------------|--------|---------|
| **sifting** | Filters VEP annotation files for SNPs with SIFT scores (deleterious/tolerated), extracts rs numbers, ENSG IDs, and SIFT scores | `bin/sifting.py` | VEP annotation VCF (ALL.chr{X}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf) | sifted.SIFT.chr{X}.txt |

### Stage 3: Analysis

| Task | Description | Executable | Inputs | Outputs |
|------|-------------|------------|--------|---------|
| **mutation_overlap** | Measures mutation overlap among pairs of individuals by population and chromosome. Computes cross-correlations, generates plots and statistical summaries | `bin/mutation_overlap.py` | chr{X}n.tar.gz, sifted.SIFT.chr{X}.txt, population file, columns.txt | chr{X}-{population}.tar.gz (with output data and plots) |

| Task | Description | Executable | Inputs | Outputs |
|------|-------------|------------|--------|---------|
| **frequency** | Measures frequency of overlapping mutations by selecting random individuals (52 at a time), runs 1000 iterations, computes histograms | `bin/frequency.py` | chr{X}n.tar.gz, sifted.SIFT.chr{X}.txt, population file, columns.txt | chr{X}-{population}-freq.tar.gz (with histogram data and plots) |

---

## 3. Data Objects Registry

### Input Data Objects

| Object | Type | Format | Location | Description |
|--------|------|--------|----------|-------------|
| ALL.chr{1-10}.250000.vcf | Input | VCF (plain text) | data/20130502/ | Phase3 variant call data, 250k lines per chromosome |
| ALL.chr{1-10}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf | Input | VCF (plain text) | data/20130502/ | VEP functional annotation with SIFT scores |
| columns.txt | Input | Text | data/ | Tab-separated list of 2504 individual IDs |
| {AFR,AMR,EAS,EUR,GBR,SAS,ALL} | Input | Text | data/populations/ | Population membership files |

### Intermediate Data Objects

| Object | Type | Format | Description |
|--------|------|--------|-------------|
| chr{X}n-{counter}-{stop}.tar.gz | Intermediate | tar.gz | Per-chunk individual mutation data |
| chr{X}n.tar.gz | Intermediate | tar.gz | Merged individual data per chromosome |
| sifted.SIFT.chr{X}.txt | Intermediate | Text | Filtered SIFT scores per chromosome |

### Output Data Objects

| Object | Type | Format | Description |
|--------|------|--------|-------------|
| chr{X}-{population}.tar.gz | Output | tar.gz | Mutation overlap results and plots |
| chr{X}-{population}-freq.tar.gz | Output | tar.gz | Frequency analysis results and plots |

---

## 4. Producer-Consumer Dependencies

### Dependency Graph

```
individuals (per-chunk) ──┐
                         ├──► individuals_merge ──► ┐
individuals (per-chunk) ──┘                         │
                                                   │
sifting ───────────────────────────────────────────┼──► mutation_overlap
                                                   │    (per chr-pop)
                                                   │
sifting ───────────────────────────────────────────┼──► frequency
                                                   │    (per chr-pop)
columns.txt ───────────────────────────────────────┤
population files ──────────────────────────────────┘
```

### Edge Classification

| From | To | Edge Type | Rationale |
|------|-----|-----------|-----------|
| individuals (chunks) | individuals_merge | **Fan-in merge** | Multiple parallel chunks processed per chromosome are merged |
| individuals_merge | mutation_overlap | **Data dependency** | Analysis requires merged individual data |
| individuals_merge | frequency | **Data dependency** | Analysis requires merged individual data |
| sifting | mutation_overlap | **Data dependency** | SIFT-filtered variants required for overlap analysis |
| sifting | frequency | **Data dependency** | SIFT-filtered variants required for frequency analysis |
| columns.txt | individuals | **Static input** | Required for all parsing tasks |
| population files | mutation_overlap | **Static input** | Population membership required for per-population analysis |
| population files | frequency | **Static input** | Population membership required for per-population analysis |

---

## 5. Workflow Structure

### High-Level Pattern

The workflow exhibits a **directed acyclic graph (DAG) with nested parallelism**:

1. **Chromosome-level parallelism**: Each chromosome (1-10) is processed independently
2. **Chunk-level parallelism**: Each chromosome can be split into N parallel individuals jobs (configurable via `-i` flag, default 250)
3. **Population-level parallelism**: Each chromosome has 7 analysis tasks (one per population: AFR, AMR, EAS, EUR, GBR, SAS, ALL)

### Control Flow

- **Sequential within stage**: individuals jobs within a chromosome run sequentially to process different line ranges; individuals_merge waits for all chunks
- **Parallel across dimensions**: Different chromosomes, different population analyses run in parallel
- **No iteration/branching**: All control flow is static, defined at workflow generation time

### Workflow Generation

The workflow is generated by `daxgen.py` which:
- Parses `data.csv` to determine chromosomes and thresholds
- Creates parallel individuals jobs per chromosome based on `ind_jobs` parameter
- Creates one individuals_merge job per chromosome
- Creates one sifting job per chromosome
- Creates 7 mutation_overlap and 7 frequency jobs per chromosome (one per population)

---

## 6. I/O Behavioral Hints

### Static Analysis Observations

| Pattern | Evidence | Impact |
|---------|----------|--------|
| **Small-file overhead** | individuals.py creates one file per individual (~2504 files per chromosome chunk), then packages into tar.gz | Large number of small file creates/opens; potential I/O overhead |
| **Compressed archives** | All intermediate and final outputs use tar.gz compression | Compression/decompression overhead; sequential access required |
| **Full-file reads** | individuals.py reads entire VCF file into memory (`rawdata = readfile(inputfile)`) then filters in Python | Memory pressure proportional to VCF size (250k lines) |
| **Repeated untar** | mutation_overlap.py and frequency.py both extract chr{X}n.tar.gz to disk | Duplicate extraction of same data |
| **String processing** | Heavy regex filtering in sifting.py, line-by-line parsing | CPU-bound, not I/O-bound |
| **Temporary directory creation** | individuals_merge.py uses tempfile.TemporaryDirectory for extraction | Filesystem operations per merge |
| **Subset extraction** | individuals.py processes line range [counter:stop], not entire file | Demonstrates awareness of data partitioning |

### Data Reuse Opportunities

- The same `chr{X}n.tar.gz` is read by both mutation_overlap and frequency (could share extracted data)
- The same `sifted.SIFT.chr{X}.txt` is read by both analysis tasks
- [ASSUMPTION] Population files and columns.txt could be staged once and shared

---

## 7. Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| dataset | 20130502 | Dataset folder name |
| datafile | data.csv | CSV file listing chromosomes and thresholds |
| ind_jobs | 250 | Number of parallel individuals jobs per chromosome |
| exec_site | condorpool | Execution site (condorpool, cori) |
| use_bash | False | Use bash scripts instead of Python |
| use_decaf | False | Use Decaf in-situ framework |
| use_pmc | False | Use Pegasus MPI Cluster |

---

## 8. Summary

The 1000genome workflow is a genomics pipeline that processes 1000 Genomes Project VCF data to compute mutation overlap statistics across individuals and populations. It uses Pegasus WMS for workflow orchestration with significant parallelism at chromosome, chunk, and population levels. The workflow demonstrates classic bioinformatics patterns: VCF parsing, functional annotation filtering (SIFT), and statistical analysis of genetic variation overlap.

---

*Generated by opencode agent - static analysis only*
