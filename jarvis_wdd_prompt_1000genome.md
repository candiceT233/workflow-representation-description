Jarvis WDD Execution Prompt (1000genome)

You are an execution agent. Read the workflow definition document (WDD), then use Jarvis-MCP to create per-task packages, create a deployment pipeline, and run the workflow.

Inputs
- WDD path: `workflow_wdd/1000genome-wdd-gemini.yaml`
- Workflow name: `1000genome`
- Pipeline ID: `1000genome-workflow`
- Repository root for generated Jarvis package repo: `/home/mtang11/jarvis-work/repos/1000genome_repo`
- Repo name (python package root): `1000genome_repo`
- Run directory base: `/mnt/common/mtang11/scripts/1kgenome-pnnl/1000genome-workflow`
- Optional hostfile: `null`

Non-negotiable execution rules
1. Use Jarvis-MCP tools for Jarvis operations whenever available.
2. Do not run shell discovery commands such as `find`, `which`, `env | grep` to locate Jarvis binaries.
3. Do not create duplicate pipelines or duplicate package instances.
4. If target pipeline exists, clean/update it intentionally (do not silently duplicate).
5. Before destructive actions, print exactly what will be removed/overwritten.

Objective
From the WDD:
1. Create one Jarvis package (`pkg_type`) per WDD task.
2. Create the correct pipeline deployment in Jarvis following WDD task order and dependencies.
3. Run the workflow with Jarvis.

Required workflow

Step A: Parse and validate WDD
1. Read `workflow_wdd/1000genome-wdd-gemini.yaml`.
2. Extract at minimum:
   - `metadata.workflow_name`
   - `tasks[]` (`task_id`, `name`, `stage`, `executable`, `inputs`, `outputs`)
   - `pc_edges[]` (`producer`, `consumer`, `data_objects`, `coupling`, `pc_pattern`)
   - `workflow_graph.stage_execution_order` and `workflow_graph.dag_edges` (if present)
3. Build an internal task DAG and topological package execution order.
4. Print a short plan: task count, edge count, package names to create, final pipeline order.

Step B: Prepare Jarvis manager state
1. Load Jarvis configuration.
2. If needed, initialize config directories.
3. Hostfile is `null`; skip hostfile setup unless required by runtime environment.
4. List existing pipelines and repos.
5. If a pipeline with ID `1000genome-workflow` already exists, ask whether to:
   - reuse and reconcile, or
   - destroy and recreate.

Step C: Create repo and per-task packages
1. Ensure repository structure:
   - `/home/mtang11/jarvis-work/repos/1000genome_repo/1000genome_repo/__init__.py`
   - `/home/mtang11/jarvis-work/repos/1000genome_repo/1000genome_repo/<pkg_type>/pkg.py` for each task package
2. Package naming convention:
   - derive `pkg_type` from `task_id` (strip `task:` and normalize to snake_case).
   - ensure valid Python identifiers.
3. For each task, implement package class with:
   - `_init`
   - `_configure_menu`
   - `configure`
   - `start`
   - `stop`
   - `clean`
4. In `start`, call the task executable/command inferred from WDD (`tasks[].executable`) with configurable args/paths.
5. Add repo to Jarvis (or update if already present), then save config.

Step D: Create and configure pipeline
1. Create pipeline `1000genome-workflow` if absent.
2. For each task in topological order:
   - append corresponding `pkg_type` once
   - set deterministic `pkg_id` (default to same as `pkg_type`)
   - configure package using WDD-derived defaults and `/mnt/common/mtang11/scripts/1kgenome-pnnl/1000genome-workflow`
3. Validate no duplicate `pkg_id` entries exist.
4. Build pipeline environment.

Step E: Run and report
1. Run pipeline `1000genome-workflow`.
2. Stream key status updates (start, per-phase progress, completion/failure).
3. On error:
   - report failing package/task
   - show actionable fix
   - stop without destructive cleanup unless requested.

Tool preference (Jarvis-MCP)
Prefer this flow (when available):
- `jm_load_config`
- `jm_create_config` (if needed)
- `jm_list_repos` / `jm_add_repo` / `jm_save_config`
- `jm_list_pipelines`
- `create_pipeline` / `destroy_pipeline` (only with confirmation)
- `append_pkg` / `configure_pkg` / `get_pkg_config`
- `build_pipeline_env`
- `run_pipeline`

Output contract
Return:
1. Summary of what was created:
   - repo path
   - package list (`pkg_type -> task_id`)
   - pipeline id
2. Deployment mapping:
   - execution order
   - package configuration highlights
3. Run result:
   - success/failure
   - key logs/status
4. Next recommended actions (if failure or partial success).
