# **Technical Evaluation and Architectural Analysis of the Pegasus 1000 Genomes Workflow in High-Performance Computing Environments**

The characterization of human genetic variation stands as a primary objective in the contemporary genomic era, necessitating computational infrastructures capable of processing petascale datasets with high degrees of reproducibility and efficiency. The 1000 Genomes Project, which successfully mapped the genetic diversity of 2,504 individuals across 26 distinct global populations, represents a landmark in this field.1 To manage the immense computational burden of analyzing these data, the Pegasus Workflow Management System (WMS) has been employed to implement a robust pipeline that identifies mutational overlaps and establishes statistical null distributions for disease-related research.1 This report provides an exhaustive technical dissection of the Pegasus 1000 Genomes workflow, evaluating its historical context within the project's phases, its architectural mapping to High-Performance Computing (HPC) resources, and the specific resource management challenges encountered during its execution.

## **Historical Evolution and Data Semantics of the 1000 Genomes Project**

The 1000 Genomes Project was the first large-scale effort to sequence the genomes of a diverse set of individuals to provide a comprehensive resource on human genetic variation.3 Its development followed a structured progression through a pilot phase and three main phases, each marked by technological advancements and refined analytical methodologies.3 The pilot phase focused on assessing data-sharing strategies through low-coverage whole-genome sequencing (2-4X) of 180 samples and high-coverage sequencing (20-60X) of two mother-father-child trios.3 These early efforts established the feasibility of identifying variants with frequencies as low as 1% by combining data across multiple samples.3

As the project transitioned through Phase 1 and ultimately to Phase 3, the scale and complexity of the data increased significantly.3 Phase 3 analysis, which remains the definitive call set for the project, reconstructed the genomes of 2,504 individuals using only Illumina platform data with read lengths of 70 base pairs or longer.6 This strategic shift from the multi-platform approach of Phase 1—which included ABI SOLiD and 454 technologies—was driven by the need for higher-quality variant calling and more consistent error profiles.6 Furthermore, Phase 3 introduced multi-allelic variant calling, encompassing single nucleotide polymorphisms (SNPs), insertions/deletions (INDELs), and complex structural variants (SVs).6

The transition to the GRCh38 human genome assembly, facilitated by the International Genome Sample Resource (IGSR), represents a critical post-project development.5 GRCh38 corrected over 1,000 issues found in the previous GRCh37 assembly and incorporated alternative loci to better reflect global diversity.9 The analysis pipeline for Phase 3 utilized a multi-caller approach, integrating results from GATK, FreeBayes, and BCFtools, followed by imputation and phasing using Beagle and SHAPEIT2.5 Phasing is a critical component of the data semantics, allowing researchers to determine the parental origin of alleles and calculate genotype dosage values.6 The dosage, representing the predicted number of non-reference alleles, is calculated using the following mathematical relationship:

![][image1]  
This value, derived from the Mach/Thunder imputation engines, provides a quantitative measure of confidence in a genotype call, complementing the standard genotype likelihoods based directly on sequencing data.8

| Project Phase | Focus | Sample Count | Technology | Key Outputs |
| :---- | :---- | :---- | :---- | :---- |
| Pilot | Feasibility | 180 | Mixed Platforms | 2-4X WGS strategy validation 3 |
| Phase 1 | Integrated Calls | 1,092 | Illumina, SOLiD, 454 | Integrated bi-allelic SNPs/INDELs 6 |
| Phase 3 | Final Release | 2,504 | Illumina 70bp+ | Phased multi-allelic call set 6 |
| NYGC | High Coverage | 3,202 | Illumina 30X | GRCh38 realignment and SVs 5 |

## **Architectural Mapping with the Pegasus Workflow Management System**

The Pegasus WMS is designed to bridge the gap between abstract scientific workflow descriptions and the heterogeneous execution environments of modern HPC systems.11 It accomplishes this through a transformation process known as mapping or planning, which converts a logical Directed Acyclic Graph (DAG) into a concrete, executable workflow.12 This mapping process is facilitated by three primary catalogs that manage metadata about files, executables, and hardware resources.13

The Replica Catalog (RC) is fundamental for data management, mapping logical file names (LFNs) used in the abstract workflow to their physical file locations (PFNs) on storage systems.13 The Transformation Catalog (TC) identifies the physical locations of the software executables required for each task, specifying whether they are installed on the remote execution site or need to be staged in.13 Finally, the Site Catalog (SC) defines the architectural layout of the execution resources, including the operating system, queue manager, and storage protocols available at a site like NERSC.13

During the planning phase, Pegasus augments the workflow by adding auxiliary jobs that ensure a successful execution environment.13 These include create\_dir jobs for establishing remote working directories, stage\_in jobs for transferring input data to compute nodes, and stage\_out jobs for moving final data products to a permanent storage location.14 To maintain rigorous scientific provenance, every job is wrapped in the "kickstart" executable, which captures comprehensive runtime information, including exact software versions, hardware metrics, and command-line arguments.11

### **Systematic Task Decomposition and Dependency Logic**

The 1000 Genomes workflow implemented in Pegasus consists of five core task classes that perform sequential data retrieval, parsing, and statistical analysis.1 The dependency structure of these tasks ensures that biological insights are derived through a systematic pipeline of data refinement.15

The first and most intensive step involves the **Individuals** task, which fetches and parses Phase 3 VCF data by chromosome.1 Because human chromosomes contain hundreds of thousands of variants, the VCF files are exceptionally large—often exceeding 250,000 lines for a single chromosomal release.1 To handle this scale, the workflow employs a Scatter/Gather pattern.1 The input file is divided into manageable chunks, and multiple "Individuals" jobs are executed in parallel to identify SNPs and determine which individuals possess mutations on both alleles for specific rs numbers.1

Following the parsing of these chunks, the **Individuals\_Merge** task acts as a synchronization point, gathering the outputs of the parallel chunks and merging them into a single mutations file per chromosome.1 This merged file serves as the input for subsequent analytical steps. Simultaneously, the **Populations** task downloads demographic metadata for the 26 global populations, providing the categorical framework for the analysis.1

The **Sifting** task adds a functional annotation layer to the genomic data by utilizing the Variant Effect Predictor (VEP) to compute SIFT scores.1 SIFT, or "Sorts Intolerant From Tolerant," is a sequence homology-based tool that predicts whether an amino acid substitution will impact protein function.1 This task specifically filters for variants with SIFT scores, recording their rs numbers, ENSEMBL GEN IDs, and HGNC IDs.1

The final stages of the workflow involve the **Mutations\_Overlap** and **Frequency** tasks.1 The overlap task calculates the frequency of shared mutations among pairs of individuals, categorized by their population and chromosome.1 The frequency task then establishes a null distribution by selecting random individuals and analyzing variants without regard for their SIFT scores.1 This comparison allows scientists to distinguish between common variation and mutations that may be statistically enriched in disease-associated cohorts.1

| Task Name | Complexity | Primary Input | Primary Output | Dependencies |
| :---- | :---- | :---- | :---- | :---- |
| Individuals | High | Chromosome VCF | Chunked SNP lists | None (Root task) 1 |
| Individuals\_Merge | Moderate | Chunked SNP lists | Merged mutations file | Individuals 1 |
| Populations | Low | Population metadata | Categorized individuals | None (Root task) 1 |
| Sifting | Moderate | VEP/VEP outputs | Phased SIFT scores | None (Root task) 1 |
| Mutations\_Overlap | Moderate | Merged mutations | Overlap metrics | Individuals\_Merge, Populations 1 |
| Frequency | Moderate | Random sample | Null distribution | Individuals\_Merge, Sifting 1 |

## **Resource Management and HPC Optimization Strategies**

Execution of the 1000 Genomes workflow on large-scale supercomputers like Cori at NERSC requires careful tuning of resource allocations and scheduling parameters.1 The "Individuals" jobs are the primary drivers of memory consumption, and their requirements scale with the size of the VCF chunks being processed.1 Benchmarking on NERSC Haswell nodes indicates that as the number of parallel jobs per chromosome increases, the memory required per job decreases, allowing for more efficient slot utilization in a shared compute environment.1

| Parallel Jobs per Chromosome | Lines per Chunk | Memory Required per Job (GB) |
| :---- | :---- | :---- |
| 2 | 125,000 | 6.10 1 |
| 5 | 50,000 | 3.93 1 |
| 10 | 25,000 | 3.17 1 |
| 16 | 15,625 | 2.93 1 |

A common failure mode in HPC environments is the termination of tasks by the queue manager (e.g., HTCondor or SLURM) when memory limits are exceeded.1 In HTCondor, this often results in a SIGKILL (code \-9).1 To mitigate this, practitioners configure dynamic slot allocation, where slots can expand to consume more of a node's resources on demand.1 This is typically managed by setting SLOT\_TYPE\_1\_PARTITIONABLE \= TRUE within the HTCondor configuration, ensuring that the heavy "Individuals" jobs do not stall the entire pipeline.1

### **Job Clustering and In-Situ Messaging**

In workflows with thousands of short-running tasks, the overhead of the workflow engine—including scheduling, authentication, and directory setup—can often exceed the execution time of the scientific code itself.1 Pegasus addresses this through job clustering, an optimization that merges multiple small, independent tasks into a single larger "clustered job".1 This can be implemented using the Pegasus MPI Cluster (PMC), which uses a master/worker approach to distribute clustered tasks across multiple compute nodes using MPI ranks.1

Beyond standard job clustering, the integration of *in-situ* dataflow frameworks like Decaf offers a revolutionary approach to bypassing storage-related bottlenecks.17 Traditional workflows communicate between jobs using the parallel filesystem, but Decaf replaces these disk-based operations with faster MPI messaging between ranks.17 Experiments on the 1000 Genomes workflow have shown that replacing file communication with in-memory MPI messaging can improve total execution time by 22% to 30%.17 This optimization is particularly relevant for the "Individuals" and "Individuals\_Merge" sequence, where large volumes of intermediate SNP data are generated and consumed.17

## **Benchmark Performance and Deployment in Federated Environments**

The performance of the Pegasus 1000 Genomes workflow has been analyzed across diverse execution environments, including local HTCondor pools, HPC supercomputers, and Kubernetes-based cloud platforms.1 Benchmarks on a single node of Cori at NERSC for 10 "Individuals" jobs and one chromosome reveal that the workflow spends the vast majority of its time in the parsing phase.1

| Job Class | Duration (Seconds) | Fraction of Workflow (%) |
| :---- | :---- | :---- |
| Individuals | 11,431 | 81.85 1 |
| Frequency | 1,492 | 10.68 1 |
| Individuals\_Merge | 500 | 3.58 1 |
| Mutation\_Overlap | 468 | 3.35 1 |
| Stage\_Out | 34 | 0.24 1 |
| Stage\_In | 21 | 0.15 1 |
| Auxiliary (cleanup/dir) | 16 | 0.11 1 |
| Sifting | 6 | 0.05 1 |
| **Total** | **13,967 (3.9 hours)** | **100.00** 1 |

In cloud-native deployments using Kubernetes, the workflow exhibits strong scaling up to 250 concurrent containers, but performance degradation occurs beyond this point due to bottlenecks in the Kubernetes master for data distribution.15 These results underscore the importance of choosing an execution site that aligns with the specific bottlenecks of the pipeline; for data-intensive VCF parsing, high-throughput storage and memory-rich nodes are paramount.1

## **Systematic Inquiries for Scientific Workflow Validation**

To ensure the technical and scientific integrity of the 1000 Genomes workflow within a production HPC environment, researchers must engage in a rigorous evaluation of the pipeline's configuration and execution semantics. The following inquiries provide a framework for a domain expert to validate the scientist's approach to resource management, task dependency, and genomic data integrity.

### **Execution Details and Performance Logic**

The first series of questions addresses the efficiency of the workflow's mapping to the underlying hardware. Scientific rigor requires that the overhead of the WMS does not overwhelm the actual computation.

* How is the optimal task granularity for the "Individuals" step determined in relation to the specific core counts and memory limits of the NERSC Cori nodes to avoid over-subscription while minimizing idle cycles? 1  
* What specific logic governs the dynamic generation of dependencies in the daxgen.py script, particularly when handling the transition between parallelized VCF chunks and the synchronized "Individuals\_Merge" task? 1  
* In cases of transient hardware failure or network timeouts during the data retrieval phase from the IGSR FTP, how is the Pegasus "rescue workflow" utilized to resume processing from the last successful checkpoint without redundant VCF parsing? 1  
* Given that the "Individuals" task dominates the makespan, what profiling tools—such as Pegasus Panorama or HTCondor's job logs—are being used to identify and mitigate I/O wait times on the Lustre parallel filesystem? 1  
* Does the workflow implementation account for the computational overhead introduced by the "kickstart" provenance tracker, and is this overhead factored into the resource requests for shorter tasks like "Sifting" or "Mutation\_Overlap"? 11

### **Resource Management and Scaling Strategies**

Effective resource management is critical to preventing job failures and ensuring that the workflow remains economically viable on cloud or billable HPC resources.

* What is the specific memory allocation strategy for the "Individuals" jobs to prevent SIGKILL events, and has the HTCondor pool been configured with dynamic slots to allow for variable chunk sizes? 1  
* If the Pegasus MPI Cluster (PMC) is active, what method is used for load balancing the worker ranks to ensure that one large chromosome does not become a straggler that holds up the entire MPI job? 1  
* Has an *in-situ* framework like Decaf been considered for the "Individuals" to "Individuals\_Merge" pipeline to reduce the 30% overhead associated with temporary file I/O? 17  
* What parameters are defined in the Pegasus properties for "Horizontal Clustering" to group the high volume of short tasks into efficient execution blocks? 1  
* Is "label-based clustering" employed to ensure that data-heavy parent and child jobs are co-located on the same compute node, thereby minimizing inter-node data transfer latency? 1

### **Task Dependencies and Biological Semantics**

Finally, the scientific validity of the results depends on an accurate interpretation of the 1000 Genomes data formats and the biological logic embedded in the tasks.

* How does the "Sifting" task handle the multi-allelic variants found in Phase 3 call sets, and is the VEP configured to calculate separate SIFT scores for each alternative allele at a single locus? 1  
* What validation checks are performed to verify that the VCF files and the reference genomes (GRCh37 vs. GRCh38) used in the workflow are consistent across all chromosomal partitions? 6  
* In the "Mutations\_Overlap" analysis, how are the pairwise comparisons scaled as the cohort size expands from the project's original 2,504 samples to the high-coverage 3,202 set from the New York Genome Center? 1  
* Are the "genotype dosage" and "genotype likelihood" values extracted from the Phase 3 VCFs being utilized to weight the mutation overlap scores, or is the analysis based strictly on binary call presence? 8  
* How are "accessibility masks" integrated into the workflow to ensure that mutational overlaps are only calculated in regions where variant calling was consistent and reliable? 10

To complete this technical evaluation, is any additional information required regarding the specific software versions of VEP or the network throughput between the HPC staging area and the IGSR primary data mirrors? 1

## **Comprehensive Synthesis and Future Implications for Genomic Workflows**

The Pegasus implementation of the 1000 Genomes workflow represents a critical paradigm in bioinformatics, demonstrating how complex data flow patterns can be automated and optimized for high-performance execution. The success of the pipeline is deeply tied to its ability to handle the data semantics of Phase 3, where the shift to Illumina-only, phased, and multi-allelic data increased the precision of variant calling while simultaneously raising the computational barrier.6 The use of the Scatter/Gather pattern for "Individuals" tasks remains the most effective strategy for managing the sheer scale of the genomic releases, provided that memory allocations are carefully tuned to avoid scheduler-driven job terminations.1

Looking toward the future, the convergence of HPC and cloud technologies will likely see the 1000 Genomes workflow ported to serverless and Function-as-a-Service (FaaS) platforms.19 While the serverless model offers advantages in abstraction and rapid scaling, researchers must remain vigilant about the unique data flow patterns of genomic pipelines, which are often better suited for the high-bandwidth, tightly-coupled environments of supercomputers.21 Furthermore, the ongoing efforts of the International Genome Sample Resource (IGSR) to incorporate long-read sequencing and structural variant data from 1,019 samples will require that workflows like this one continue to evolve to handle increasingly complex graph-based genome representations.5

Ultimately, the architectural flexibility of Pegasus, combined with the comprehensive foundational data from the 1000 Genomes Project, provides a powerful engine for discovery. By addressing the critical questions of resource management and semantic integrity, scientists can ensure that their computational results are as robust and globally representative as the human populations they seek to understand. The integration of advanced features like in-memory MPI messaging and dynamic slotting further ensures that as genomic datasets grow into the exascale range, the analytical pipelines will remain both efficient and resilient.1

#### **Works cited**

1. pegasus-isi/1000genome-workflow: Bioinformatics workflow that identifies mutational overlaps using data from the 1000 genomes project \- GitHub, accessed February 25, 2026, [https://github.com/pegasus-isi/1000genome-workflow](https://github.com/pegasus-isi/1000genome-workflow)  
2. Flow-Bench: A Dataset for Computational Workflow Anomaly Detection \- arXiv.org, accessed February 25, 2026, [https://arxiv.org/html/2306.09930v2](https://arxiv.org/html/2306.09930v2)  
3. 1000 Genomes Project summary, accessed February 25, 2026, [https://www.internationalgenome.org/1000-genomes-summary/](https://www.internationalgenome.org/1000-genomes-summary/)  
4. 1000 Genomes Project (Phase 3 release) \- MSK Data Catalog, accessed February 25, 2026, [https://datacatalog.mskcc.org/dataset/11499](https://datacatalog.mskcc.org/dataset/11499)  
5. Announcements \- 1000 Genomes, accessed February 25, 2026, [https://www.internationalgenome.org/announcements/](https://www.internationalgenome.org/announcements/)  
6. Variants \- 1000 Genomes, accessed February 25, 2026, [https://www.internationalgenome.org/category/variants/](https://www.internationalgenome.org/category/variants/)  
7. Data access | 1000 Genomes, accessed February 25, 2026, [https://www.internationalgenome.org/category/data-access/](https://www.internationalgenome.org/category/data-access/)  
8. VCF \- 1000 Genomes, accessed February 25, 2026, [https://www.internationalgenome.org/category/vcf/](https://www.internationalgenome.org/category/vcf/)  
9. 1000 Genomes | A Deep Catalog of Human Genetic Variation, accessed February 25, 2026, [https://www.internationalgenome.org/](https://www.internationalgenome.org/)  
10. Data analysis | 1000 Genomes, accessed February 25, 2026, [https://www.internationalgenome.org/category/data-analysis/](https://www.internationalgenome.org/category/data-analysis/)  
11. Executing Workflows using Pegasus WMS, accessed February 25, 2026, [https://arokem.github.io/2013-09-16-ISI/lessons/pegasus-workflows/tutorial.html](https://arokem.github.io/2013-09-16-ISI/lessons/pegasus-workflows/tutorial.html)  
12. Workflow Anomaly Detection with Graph Neural Networks \- IEEE Computer Society, accessed February 25, 2026, [https://www.computer.org/csdl/proceedings-article/works/2022/519100a035/1KckpWdYlA4](https://www.computer.org/csdl/proceedings-article/works/2022/519100a035/1KckpWdYlA4)  
13. Pegasus | 80060-09-9 \- Benchchem, accessed February 25, 2026, [https://www.benchchem.com/fr/product/b39198](https://www.benchchem.com/fr/product/b39198)  
14. 7\. Running Workflows — Pegasus WMS 5.1.2 documentation, accessed February 25, 2026, [https://pegasus.isi.edu/documentation/user-guide/running-workflows.html](https://pegasus.isi.edu/documentation/user-guide/running-workflows.html)  
15. 1000-genome workflow on Kubernetes, accessed February 25, 2026, [https://jupyter-workflow.di.unito.it/2021/10/15/1000-genome-workflow-on-kubernetes/](https://jupyter-workflow.di.unito.it/2021/10/15/1000-genome-workflow-on-kubernetes/)  
16. Formal Methods \- ResearchGate, accessed February 25, 2026, [https://www.researchgate.net/publication/386177019\_Sound\_and\_Complete\_Witnesses\_for\_Template-Based\_Verification\_of\_LTL\_Properties\_on\_Polynomial\_Programs/fulltext/6747bf3a790d154bf9afa043/Sound-and-Complete-Witnesses-for-Template-Based-Verification-of-LTL-Properties-on-Polynomial-Programs.pdf?origin=scientificContributions](https://www.researchgate.net/publication/386177019_Sound_and_Complete_Witnesses_for_Template-Based_Verification_of_LTL_Properties_on_Polynomial_Programs/fulltext/6747bf3a790d154bf9afa043/Sound-and-Complete-Witnesses-for-Template-Based-Verification-of-LTL-Properties-on-Polynomial-Programs.pdf?origin=scientificContributions)  
17. Accelerating Scientific Workflows on HPC Platforms with In Situ Processing, accessed February 25, 2026, [https://par.nsf.gov/servlets/purl/10355276](https://par.nsf.gov/servlets/purl/10355276)  
18. WfBench: Automated Generation of Scientific Workflow Benchmarks \- arXiv, accessed February 25, 2026, [https://arxiv.org/pdf/2210.03170](https://arxiv.org/pdf/2210.03170)  
19. Usability Evaluation of Cloud for HPC Applications \- arXiv, accessed February 25, 2026, [https://arxiv.org/pdf/2506.02709](https://arxiv.org/pdf/2506.02709)  
20. An Empirical Evaluation of the Viability of the Serverless Paradigm for Scientific Workflows \- UWSpace \- University of Waterloo, accessed February 25, 2026, [https://uwspace.uwaterloo.ca/bitstreams/f6849525-1209-428b-887a-0b26f1f8c695/download](https://uwspace.uwaterloo.ca/bitstreams/f6849525-1209-428b-887a-0b26f1f8c695/download)  
21. Object Proxy Patterns for Accelerating Distributed Applications \- Greg Pauloski, accessed February 25, 2026, [https://gregpauloski.com/publications/pauloski2024proxystore-preprint.pdf](https://gregpauloski.com/publications/pauloski2024proxystore-preprint.pdf)

[image1]: <data:image/png;base64,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>