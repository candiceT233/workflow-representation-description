TASK: Deploy and Run a Workflow from WDD with Jarvis-MCP
You are an execution agent. Read a Workflow Definition Document (WDD), create one Jarvis package per workflow task, construct the pipeline deployment, and run it.

Purpose
Use WDD as the source of truth to build a reproducible Jarvis deployment pipeline without introducing duplicate pipelines or duplicate package instances.

Hard Scope Rules
- Use Jarvis-MCP tools for Jarvis operations whenever available.
- Do not run shell discovery commands such as `find`, `which`, or `env | grep` to locate Jarvis binaries.
- Do not invent workflow tasks or dependencies not present in WDD.
- If any required value cannot be inferred from WDD, use explicit placeholders and report what is missing.
- Before destructive actions (destroy pipeline, remove package), print exactly what will be changed and require explicit confirmation.
- If any Jarvis CLI command is used, load environment first with `source ~/iowarp/load-jarvis.sh`.
- For shell-based Jarvis commands, run in one command chain, for example:
  `source ~/iowarp/load-jarvis.sh && jarvis pipeline list`

Inputs
- `WDD_PATH`: `workflow_wdd/1000genome-wdd-gemini.yaml`
- `WORKFLOW_NAME`: `1000genome`
- `PIPELINE_ID`: `1000genome-workflow`
- `REPO_ROOT_PATH`: `/home/mtang11/jarvis-work/repos/1000genome_repo`
- `REPO_NAME`: `1000genome_repo`
- `RUN_DIR_BASE`: `/home/mtang11/scripts/workflow-representation-description/workflows_repo/1000genome-workflow`
- `WORKFLOW_INPUT_DATA_PATHS`:
  - `/home/mtang11/scripts/workflow-representation-description/workflows_repo/1000genome-workflow/data/20130502`
  - `/home/mtang11/scripts/workflow-representation-description/workflows_repo/1000genome-workflow/data/populations`
- `HOSTFILE_OR_NULL`: `null`

Output
Perform deployment actions and return a final execution report. Do not create a new design document. Primary output is deployed pipeline state + run result.

Required Deployment Artifacts
1. A Jarvis repository at `REPO_ROOT_PATH/REPO_NAME`
2. One package (`pkg_type`) per WDD `task_id`
3. One pipeline identified by `PIPELINE_ID`
4. Pipeline package order matching WDD DAG topological order
5. Built pipeline environment
6. Run execution result (success/failure with actionable details)

Required Naming Conventions
- Derive `pkg_type` from WDD `task_id` by stripping `task:` and normalizing to snake_case.
- Use deterministic `pkg_id` equal to `pkg_type` unless user requests otherwise.
- Ensure Python class names generated from `pkg_type` are valid identifiers.

Required WDD Fields to Read
At minimum, parse and use:
- `metadata.workflow_name`
- `tasks[]` (`task_id`, `name`, `stage`, `executable`, `inputs`, `outputs`)
- `pc_edges[]` (`producer`, `consumer`, `data_objects`, `coupling`, `pc_pattern`)
- `workflow_graph.stage_execution_order` and `workflow_graph.dag_edges` when present

Tool Preference (Jarvis-MCP)
Prefer this flow when available:
- `jm_load_config`
- `jm_create_config` (if needed)
- `jm_set_hostfile` (if `HOSTFILE_OR_NULL` is not null)
- `jm_list_repos` / `jm_add_repo` / `jm_save_config`
- `jm_list_pipelines`
- `create_pipeline` / `destroy_pipeline` (only with confirmation)
- `append_pkg` / `configure_pkg` / `get_pkg_config` / `remove_pkg`
- `build_pipeline_env`
- `run_pipeline`

Deployment Procedure
Follow this sequence. Do not skip steps.

Step 1 — Parse and validate WDD
- Read `WDD_PATH`.
- Build internal DAG and topological task order from `pc_edges` or `workflow_graph.dag_edges`.
- Print a short plan: task count, edge count, derived package list, proposed pipeline order.

Step 2 — Prepare Jarvis manager state
- Environment bootstrap (required before any Jarvis CLI fallback):
  - Run `source ~/iowarp/load-jarvis.sh`
  - Verify with `command -v jarvis`
  - If `jarvis` is still unavailable, stop and report environment failure.
- Load Jarvis configuration.
- Initialize config dirs if needed.
- If `HOSTFILE_OR_NULL` is not null, set hostfile.
- List existing repos and pipelines.
- If `PIPELINE_ID` exists, ask: reconcile existing vs destroy/recreate.

Step 3 — Create repository and package skeletons
- Ensure repository structure:
  - `REPO_ROOT_PATH/REPO_NAME/__init__.py`
  - `REPO_ROOT_PATH/REPO_NAME/<pkg_type>/pkg.py` for each task
- For each task package, implement:
  - `_init`, `_configure_menu`, `configure`, `start`, `stop`, `clean`
- In `start`, execute the task command based on WDD `tasks[].executable` with configurable arguments and paths.

Step 4 — Register repo and persist config
- Add or update repository in Jarvis.
- Save Jarvis config.
- Verify repo is visible after save.

Step 5 — Create and configure pipeline
- Create `PIPELINE_ID` if absent.
- Append each `pkg_type` exactly once in topological order.
- Configure package defaults using `RUN_DIR_BASE`, WDD task metadata, and `WORKFLOW_INPUT_DATA_PATHS`.
- Ensure package configs that require raw workflow inputs explicitly reference:
  - `/home/mtang11/scripts/workflow-representation-description/workflows_repo/1000genome-workflow/data/20130502`
  - `/home/mtang11/scripts/workflow-representation-description/workflows_repo/1000genome-workflow/data/populations`
- Validate no duplicate `pkg_id`s in pipeline.

Step 6 — Build and run
- Build pipeline environment.
- Run pipeline.
- Stream key state changes: start, package progression, completion/failure.

Step 7 — Report
- Provide:
  - Repo path and package mapping (`pkg_type -> task_id`)
  - Final pipeline package order
  - Effective key package configs
  - Run status and major logs/errors
  - Next actions if failed

Validation Checklist Before Run
- Every WDD task has exactly one pipeline package mapping.
- Package order is consistent with DAG dependencies.
- No duplicate pipeline IDs created.
- No duplicate package instances unless explicitly requested.
- Jarvis repo registration is persisted (`jm_save_config` done).

Failure Handling Rules
- If parse or config fails, stop and report exact missing field or tool failure.
- If run fails, identify failing package/task, include error summary, and provide next corrective command(s).
- Do not destroy pipeline or remove packages unless explicitly approved.
