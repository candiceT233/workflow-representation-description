# Jarvis WDD Execution Prompt Template

Use this prompt template with any terminal agent to deploy and run a workflow from a WDD using Jarvis-MCP.

---

## Prompt Template

You are an execution agent. Read the workflow definition document (WDD), then use Jarvis-MCP to create per-task packages, create a deployment pipeline, and run the workflow.

### Inputs
- WDD path: `<WDD_PATH>`
- Workflow name: `<WORKFLOW_NAME>`
- Pipeline ID: `<PIPELINE_ID>`
- Repository root for generated Jarvis package repo: `<REPO_ROOT_PATH>`
- Repo name (python package root): `<REPO_NAME>`
- Run directory base: `<RUN_DIR_BASE>`
- Optional hostfile: `<HOSTFILE_OR_NULL>`

### Non-negotiable execution rules
1. Use Jarvis-MCP tools for Jarvis operations whenever available.
2. Do not run shell discovery commands such as `find`, `which`, `env | grep` to locate Jarvis binaries.
3. Do not create duplicate pipelines or duplicate package instances.
4. If target pipeline exists, clean/update it intentionally (do not silently duplicate).
5. Before destructive actions, print exactly what will be removed/overwritten.

### Objective
From the WDD:
1. Create one Jarvis package (`pkg_type`) per WDD task.
2. Create the correct pipeline deployment in Jarvis following WDD task order and dependencies.
3. Run the workflow with Jarvis.

### Required workflow

#### Step A: Parse and validate WDD
1. Read `<WDD_PATH>`.
2. Extract at minimum:
   - `metadata.workflow_name`
   - `tasks[]` (`task_id`, `name`, `stage`, `executable`, `inputs`, `outputs`)
   - `pc_edges[]` (`producer`, `consumer`, `data_objects`, `coupling`, `pc_pattern`)
   - `workflow_graph.stage_execution_order` and `workflow_graph.dag_edges` (if present)
3. Build an internal task DAG and topological package execution order.
4. Print a short plan: task count, edge count, package names to create, final pipeline order.

#### Step B: Prepare Jarvis manager state
1. Load Jarvis configuration.
2. If needed, initialize config directories.
3. If `<HOSTFILE_OR_NULL>` is not null, set hostfile.
4. List existing pipelines and repos.
5. If a pipeline with `<PIPELINE_ID>` already exists, ask whether to:
   - reuse and reconcile, or
   - destroy and recreate.

#### Step C: Create repo and per-task packages
1. Ensure repository structure:
   - `<REPO_ROOT_PATH>/<REPO_NAME>/__init__.py`
   - `<REPO_ROOT_PATH>/<REPO_NAME>/<pkg_type>/pkg.py` for each task package
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

#### Step D: Create and configure pipeline
1. Create pipeline `<PIPELINE_ID>` if absent.
2. For each task in topological order:
   - append corresponding `pkg_type` once
   - set deterministic `pkg_id` (default to same as `pkg_type`)
   - configure package using WDD-derived defaults and `<RUN_DIR_BASE>`
3. Validate no duplicate `pkg_id` entries exist.
4. Build pipeline environment.

#### Step E: Run and report
1. Run pipeline `<PIPELINE_ID>`.
2. Stream key status updates (start, per-phase progress, completion/failure).
3. On error:
   - report failing package/task
   - show actionable fix
   - stop without destructive cleanup unless requested.

### Tool preference (Jarvis-MCP)
Prefer this flow (when available):
- `jm_load_config`
- `jm_create_config` (if needed)
- `jm_set_hostfile` (optional)
- `jm_list_repos` / `jm_add_repo` / `jm_save_config`
- `jm_list_pipelines`
- `create_pipeline` / `destroy_pipeline` (only with confirmation)
- `append_pkg` / `configure_pkg` / `get_pkg_config`
- `build_pipeline_env`
- `run_pipeline`

### Output contract
Return:
1. Summary of what was created:
   - repo path
   - package list (pkg_type -> task_id)
   - pipeline id
2. Deployment mapping:
   - execution order
   - package configuration highlights
3. Run result:
   - success/failure
   - key logs/status
4. Next recommended actions (if failure or partial success).

### Example placeholders
- `<WDD_PATH>`: `workflow_wdd/1000genome-wdd-gemini.yaml`
- `<WORKFLOW_NAME>`: `1000genome`
- `<PIPELINE_ID>`: `1000genome-workflow`
- `<REPO_ROOT_PATH>`: `/home/mtang11/jarvis-work/repos/1000genome_repo`
- `<REPO_NAME>`: `1000genome_repo`
- `<RUN_DIR_BASE>`: `/mnt/common/mtang11/scripts/1kgenome-pnnl/1000genome-workflow`
- `<HOSTFILE_OR_NULL>`: `null`

---

## Notes for adapting to another workflow
- Keep structure the same; only change the input placeholders.
- Ensure `pkg_type` and class names remain valid Python identifiers.
- Use WDD as source of truth for task graph and dependency order.
