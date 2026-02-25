Motivation

Question to anwer: how we structure the data so that the agent can answer our question better if they only have a code base
- what it means to be better

# new update:
* deploy same code on different series of input
* deploy same code same input on different hardwares
* deploy same code same input on same hardware --> same I/O pattern
- wdd = file(code) : 
    - input condition:
        - I/O objects being generated are input dependents?
        - other changes?
    - hardware condition:
        - if utilization of any hardware
- experiment definition document (EDD) = file(wdd, input)
- DDD = file(EDD, HRD)
- [IODocumeents] = execution (WDD, EDD DDD, HRD)
# next step:
* improve design of WDD (based on above note)
    - need to iterate through with architecutre document with other files
    - recheck the v2, move content out that does not belong to WDD
    - add conditional sementioncs to the WDD
* take this new v3 WDD fill in based on workflow repo only
* given the repo only and generate a document
* compare the document generated from pure workflow repo exploration vs. WDD
(make agent recheck: things missing in WDD v3, overexplaining, gaps, anything info in the workflow repo was not included in the WDD due to it's format)



# 1. qualitative
Use natrual language to asks information about the workflow, how much the agent know about the workflow already with just:
- understanding the workflow repo vs. 
- a claude detailed summary in natural language vs.
- the token of understanding the workflow from template_WDD.yaml

How transferable is the template_WDD.yml
- compare it with a claude detailed summary

# 2. qualitative
compare token of understanding the workflow repo vs. 
- a claude detailed summary in natural language
- the token of understanding the workflow from template_WDD.yaml

How transferable is the template_WDD.yml
- compare it with a claude detailed summary

# further down
If you have 200gb of I/O, those information being feed into agent is also huge.
If you have many hardware options in the system, what is a better way for agent 

use claude project to come up with workflow question prompt:
1. agent interception from Jaime's github
2. claude code hooks (pre tool use)
    - get all the info that claude what file it has accessed, token, context

GraphRAG (Graph Retrieval-Augmented Generation) is an advanced AI framework developed by Microsoft that enhances Retrieval-Augmented Generation (RAG) by using knowledge graphs to improve LLM reasoning over complex, private, or disconnected data.

Jaime's tool: paper to MD -> feed all my old papers to WIDGET claude project

# things to improve

## WDD schema improvements (repo-only static analysis friendly)
- Add `task_invocation_contract` under each task:
  - `entrypoint`
  - `arg_schema[]` with `name`, `position|flag`, `type`, `required`, `default`, `value_source`, `description`
- Add `partitioning_contract` under each task:
  - `partition_axis`, `index_start`, `index_end`, `window_size|step`
  - `end_rule` (inclusive/exclusive + clamp behavior)
  - `derived_from` (e.g., threshold/ind_jobs)
  - `constraints[]` (e.g., divisibility rules)
- Add `io_naming_contract` under each task:
  - `output_templates[]` with `data_id`, `template`, `variables`, `uniqueness_key`
- Add `edge_binding_contract` under each `pc_edge`:
  - `binding_type` (`all_shards`, `by_key`, `latest_only`, etc.)
  - `match_keys`
  - `required_producer_cardinality`
  - `selection_rule`
- Add workflow-level `parameter_constraints`:
  - `constraint_id`, `scope`, `expression`, `source_location`, `severity`

## WDD generation procedure improvements
- Explicitly parse orchestrator/generator code (e.g., `daxgen.py`) for:
  - loop bounds and arithmetic-derived ranges
  - argument assembly
  - output filename template construction
- Parse task source (`bin/*.py`) for argv semantics and output naming.
- Parse config/data files (`data.csv`, similar files) for thresholds/cardinality.
- Populate contracts above from static evidence only; mark missing fields as `unknown` with confidence metadata.

## WDD validation checklist additions
- Every task with dynamic args must have `task_invocation_contract`.
- Every sharded producer must have both `partitioning_contract` and `io_naming_contract`.
- Every gather/broadcast edge must have `edge_binding_contract`.
- Constraint expressions in contracts must be traceable to code/config source locations.
- Avoid free-text-only capture when structured values are derivable from static code.