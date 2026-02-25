# Pegasus 1000 Genomes Workflow: Evaluation Prompt Suite

## Project Context & Biological Semantics

**1. What is the primary analytical objective of the Pegasus 1000 Genomes workflow?**
* [cite_start]**Answer:** The workflow is designed to manage large-scale computational analysis to identify mutational overlaps and establish statistical null distributions for disease-related research[cite: 3].

**2. How did the sequencing methodologies evolve between Phase 1 and Phase 3 of the project?**
* [cite_start]**Answer:** Phase 1 utilized a multi-platform approach including Illumina, ABI SOLiD, and 454 technologies[cite: 6]. [cite_start]Phase 3 shifted entirely to the Illumina platform utilizing read lengths of 70 base pairs or longer to achieve higher-quality variant calling and consistent error profiles[cite: 6].

**3. What specific formula is used to calculate the predicted number of non-reference alleles (genotype dosage)?**
* [cite_start]**Answer:** The genotype dosage is calculated using the equation $Dosage = Pr(Het|Data) + 2 \times Pr(Alt|Data)$[cite: 9]. [cite_start]This provides a quantitative measure of confidence in a genotype call[cite: 10].

**4. Why was the transition to the GRCh38 human genome assembly considered a critical post-project development?**
* [cite_start]**Answer:** The GRCh38 assembly corrected over 1,000 issues found in the previous GRCh37 assembly and incorporated alternative loci to better reflect global genetic diversity[cite: 8].

**5. What is the biological function of the "Sifting" task within the workflow?**
* [cite_start]**Answer:** The Sifting task provides a functional annotation layer by utilizing the Variant Effect Predictor (VEP) to compute SIFT scores[cite: 21]. [cite_start]These scores predict whether an amino acid substitution will impact protein function[cite: 21].

**6. How does the workflow generate a null distribution for statistical comparison?**
* [cite_start]**Answer:** The Frequency task establishes a null distribution by selecting random individuals and analyzing their variants without regard for their functional SIFT scores[cite: 22].

---

## Architectural Mapping & Provenance



**7. What three primary catalogs does Pegasus utilize to map an abstract workflow into an executable one?**
* [cite_start]**Answer:** Pegasus uses the Replica Catalog (RC) for data management, the Transformation Catalog (TC) to identify executable locations, and the Site Catalog (SC) to define the execution environment's architectural layout[cite: 14].

**8. What mechanism does Pegasus use to guarantee rigorous scientific provenance for every executed task?**
* [cite_start]**Answer:** Every job within the workflow is wrapped in the "kickstart" executable, which captures comprehensive runtime information, exact software versions, hardware metrics, and command-line arguments[cite: 15].

**9. What types of auxiliary jobs does Pegasus automatically append during the workflow planning phase?**
* [cite_start]**Answer:** Pegasus adds `create_dir` jobs to establish remote working directories, `stage_in` jobs to transfer input data to compute nodes, and `stage_out` jobs to move the final data products to permanent storage[cite: 15].

---

## Task Dependency & Dataflow Logic

**10. What design pattern does the workflow employ to process the exceptionally large Phase 3 VCF files?**
* [cite_start]**Answer:** The workflow uses a Scatter/Gather pattern[cite: 18]. [cite_start]The massive VCF files are divided into manageable chunks so that multiple "Individuals" tasks can execute in parallel[cite: 18].

**11. What is the primary role of the "Individuals_Merge" task?**
* [cite_start]**Answer:** It functions as a synchronization point in the workflow by gathering the outputs from the parallel "Individuals" chunks and merging them into a single mutations file per chromosome[cite: 19].

**12. Based on the workflow's dependency logic, which two tasks are prerequisites for executing the "Mutations_Overlap" task?**
* [cite_start]**Answer:** The "Mutations_Overlap" task depends on the successful completion of both the "Individuals_Merge" task and the "Populations" task[cite: 23].

**13. Which task dominates the workflow's makespan, and what percentage of the total execution time does it consume?**
* [cite_start]**Answer:** The "Individuals" task is the most time-intensive [cite: 18][cite_start], consuming 81.85% of the total workflow duration during single-node benchmarking[cite: 33].

---

## HPC Optimization & Resource Bottlenecks

**14. How does memory consumption scale relative to the number of parallel "Individuals" jobs processing a chromosome?**
* [cite_start]**Answer:** As the number of parallel jobs per chromosome increases, the memory required per individual job decreases[cite: 25]. [cite_start]For example, running 2 parallel jobs requires 6.10 GB per job, while 16 jobs require only 2.93 GB per job[cite: 26].

**15. How can practitioners prevent the HTCondor queue manager from terminating memory-heavy tasks with a SIGKILL (code -9)?**
* [cite_start]**Answer:** Practitioners can mitigate this by configuring dynamic slot allocation (setting `SLOT_TYPE_1_PARTITIONABLE = TRUE`), which allows slots to expand on demand to consume more of a node's resources[cite: 27].

**16. What optimization strategy does Pegasus use to overcome the engine overhead associated with scheduling thousands of short-running tasks?**
* [cite_start]**Answer:** Pegasus utilizes job clustering to merge multiple small, independent tasks into a single larger "clustered job," often deployed via the Pegasus MPI Cluster (PMC)[cite: 29].

**17. What performance benefit is achieved by replacing traditional file I/O with in-situ frameworks like Decaf?**
* [cite_start]**Answer:** Replacing disk-based filesystem communication with in-memory MPI messaging between ranks can improve the total workflow execution time by 22% to 30%[cite: 30].

**18. Why is in-memory messaging particularly relevant for the transition between the "Individuals" and "Individuals_Merge" tasks?**
* [cite_start]**Answer:** This sequence generates and consumes large volumes of intermediate SNP data, creating a significant storage bottleneck that is bypassed by using in-situ messaging[cite: 30].

**19. What scalability limitation was observed when executing this genomic pipeline on cloud-native Kubernetes platforms?**
* [cite_start]**Answer:** The workflow scales effectively up to 250 concurrent containers, but experiences performance degradation beyond that point due to data distribution bottlenecks at the Kubernetes master[cite: 34].

**20. What architectural tension exists when porting traditional genomic workflows to serverless or Function-as-a-Service (FaaS) platforms?**
* [cite_start]**Answer:** While serverless models offer rapid scaling, the unique, data-intensive flow patterns of genomic pipelines are often better suited for the high-bandwidth, tightly coupled environments of traditional supercomputers[cite: 81].