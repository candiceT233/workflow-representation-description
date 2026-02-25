TASK: Generate a Workflow Definition Document (WDD)
You are analyzing a scientific workflow codebase to produce a Workflow Definition Document (WDD) — a structured YAML document that captures the logical structure of the workflow independent of how it is executed.

What You Are Producing
A single YAML file (wdd.yaml) that fully describes:
1. What stages and tasks exist in this workflow
2. What data objects flow between tasks
3. How tasks depend on each other (producer–consumer edges with pattern classification)
4. The overall workflow structure and pattern classification
5. I/O behavioral hints visible from static code analysis

Critical Constraints
Only include what is derivable from the source code. Do not speculate about runtime performance, hardware, or deployment strategy.
Every entity gets a stable ID following the convention: task:<name>, data:<name>, stage:<name>, pc:<producer>-><consumer>:<pattern>, hint:<name>.
Classify every P–C edge using the pattern taxonomy: 1-1 (one producer, one consumer), 1-n (one producer, many consumers), n-1 (many producers, one consumer), n-n (many producers, many consumers). Always include a rationale.
Classify the overall workflow using the pattern taxonomy: cascading, iterative, scatter_gather, pipeline, broadcast, checkpointing, conditional, or hybrid. Always include a rationale.
For data objects, capture format hints if visible in code (HDF5 dataset names, data types, shapes) but mark as unknown what you cannot determine.
Write behavioral notes for every task focusing on I/O-relevant behavior: how it reads input, how it writes output, whether it streams or batches, internal iteration, memory patterns.
Analysis Procedure
Follow this sequence. Do not skip steps.

Step 1: Survey the codebase structure
Read the top-level directory, README, and any workflow orchestration files (e.g., Makefiles, shell scripts, workflow manager configs like Pegasus, Nextflow, Snakemake, Parsl, or custom launchers). Identify:
- The workflow entry point
- How stages/tasks are defined and launched
- Configuration files that parameterize the workflow

Step 2: Identify all stages and tasks
Walk the orchestration layer to enumerate every distinct executable unit. For each:
- Determine its stage membership (what logical phase it belongs to)
- Read its source code to understand what it does
- Note its inputs and outputs (files read and written)

Step 3: Build the data object registry
From Step 2, compile a deduplicated list of all data objects. For each:
- Classify as input, intermediate, output, checkpoint, or config
- Determine persistence scope (transient, stage-scoped, workflow-scoped, persistent)
- If the code uses structured formats (HDF5, netCDF), read the file-creation code to extract dataset names, types, and shapes
- Estimate cardinality (how many instances exist) from loop structures or parallelism

Step 4: Map producer–consumer edges
For each data object, identify which task(s) produce it and which task(s) consume it. For each edge:
- Classify the P–C pattern (1-1, 1-n, n-1, n-n) based on the cardinality of producers and consumers
- Determine coupling (tight vs. loose) by examining whether the consumer requires the producer to fully complete
- Describe what data moves and how it is accessed

Step 5: Analyze workflow-level patterns
Using the DAG from Step 4:
- Determine if the workflow is cascading (linear chain), iterative (loop), scatter-gather, pipeline, broadcast, conditional, checkpointing, or hybrid
- Identify the critical path if determinable
- Note any iteration/looping control flow

Step 6: Extract I/O behavioral hints
Re-read the task source code looking for patterns that suggest I/O concerns:
- Partial file access: Task opens a file but reads only a subset of its contents
- Format mismatch: Task uses chunked HDF5 for small, sequentially-accessed data (or contiguous for random access)
- Small file overhead: Many small files created where a single larger file could suffice
- Unnecessary serialization: Aggregation step that exists only to combine files for a single consumer
- Data reuse: Same data read by multiple tasks (inter-task reuse) or re-read by the same task (intra-task reuse)
- Checkpoint waste: Checkpoint files written but rarely/never read in the normal execution path
- Metadata overhead: Many datasets per file or many small files causing metadata-heavy I/O

Step 7: Assemble and validate
Write the complete wdd.yaml. Then validate:
- Every task references valid data_ids in its inputs/outputs
- Every data_id appears in at least one task's inputs or outputs
- Every pc_edge references valid task_ids and data_ids
- The cross-reference index is consistent with the body
- The stage execution order matches the DAG dependencies

Output
Produce a single file: wdd.yaml
If any section requires assumptions, state them explicitly in the relevant description or rationale field with the prefix [ASSUMPTION].
If the codebase is incomplete or you cannot determine a value, use "unknown" and add a note explaining what information is missing.

## Reference: Pattern Taxonomy

### P-C Patterns (per-edge)

| Pattern | Description | Example |
| --- | --- | --- |
| 1-1 | One producer writes data read by one consumer | Simulation -> post-processing |
| 1-n | One producer's data shared across multiple consumers | Static input used by many analysis tasks |
| n-1 | Several producers write parts consumed by one task | Aggregation of parallel task outputs |
| n-n | Multiple producers and consumers with shared I/O | Parallel ML training, ensemble workflows |

### Workflow-Level Patterns

| Pattern | Description | Typical P-C Structures |
| --- | --- | --- |
| Cascading | Linear chain of stages | Any |
| Iterative | Repeats computation with prior output as input | Often 1-1; may include others |
| Conditional | Tasks access data only if conditions are met | Usually 1-1 or 1-n |
| Checkpointing | Saves task state for restart/recovery | Usually 1-1; may be n-1 |
| Broadcast | One task provides shared input to many | Typical 1-n |
| Scatter-Gather | Data distributed to parallel tasks, then merged | 1-n scatter; n-1 or n-n gather |
| Pipeline | Stages overlap in time with streaming data | 1-1 or 1-n with loose coupling |
| Hybrid | Combination of the above | Mixed |