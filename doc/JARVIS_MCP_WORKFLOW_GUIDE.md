# Jarvis-MCP Workflow Creation Guide

**Purpose**: This guide explains how to create new workflow packages (`pkg_type`) and add them to Jarvis-CD pipelines using jarvis-mcp. Use this when adding new workflows or when an agent needs to understand the process.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Components Required](#components-required)
3. [Creating a New Package Type (`pkg_type`)](#creating-a-new-package-type-pkg_type)
4. [Registering the Package Repository](#registering-the-package-repository)
5. [Adding Packages to Pipelines](#adding-packages-to-pipelines)
6. [Information to Collect from Users](#information-to-collect-from-users)
7. [Complete Example: 1000genome Workflow](#complete-example-1000genome-workflow)
8. [Troubleshooting](#troubleshooting)

---

## Core Concepts

### Package Type (`pkg_type`)
- A **`pkg_type`** is a reusable workflow component (e.g., `ior`, `my_shell`, `thousand_genome_workflow`).
- Each `pkg_type` is defined by a Python class in a repository.
- Jarvis searches registered repositories to find `pkg_type` definitions.

### Package Instance (`pkg_id`)
- A **`pkg_id`** is a specific instance of a `pkg_type` within a pipeline.
- Multiple instances of the same `pkg_type` can exist in one pipeline (with different `pkg_id` values).
- Example: Pipeline can have `pkg_type="my_shell"` with `pkg_id="loader1"` and `pkg_id="loader2"`.

### Pipeline
- A **pipeline** is a sequence of packages (`pkg_type` instances) that run together.
- Pipelines are identified by a `pipeline_id` (e.g., `"1000genome-workflow"`).

### Repository (`repo`)
- A **repository** is a directory containing one or more `pkg_type` definitions.
- Structure: `<repo_path>/<repo_name>/<pkg_type>/pkg.py`
- Repositories must be registered with Jarvis before their `pkg_type`s can be used.

---

## Components Required

### 1. Repository Structure

```
<repo_path>/
└── <repo_name>/                    # repo_name = basename(repo_path)
    ├── __init__.py                 # Empty file to make it a Python package
    └── <pkg_type>/                 # e.g., "thousand_genome_workflow"
        ├── __init__.py             # Empty file
        ├── pkg.py                  # Contains the Application/Service class
        └── README.md               # Documentation (optional)
```

**Key Points**:
- `repo_name` = `os.path.basename(repo_path)` (e.g., if path is `/home/user/repos/my_repo`, then `repo_name = "my_repo"`).
- The Python module path is: `{repo_name}.{pkg_type}.pkg`.
- The class name should match `to_camel_case(pkg_type)` (e.g., `thousand_genome_workflow` → `ThousandGenomeWorkflow`).

### 2. Package Class (`pkg.py`)

Must inherit from `Application` or `Service` (from `jarvis_cd.basic.pkg`).

**Required Methods**:
- `_init()`: Initialize paths/resources.
- `_configure_menu()`: Return list of config parameters (CLI menu).
- `configure(**kwargs)`: Process configuration parameters.
- `start()`: Launch the workflow/application.
- `stop()`: Stop the workflow (optional, can be `pass`).
- `clean()`: Clean up data (optional, can be `pass`).

**Example Structure**:
```python
from jarvis_cd.basic.pkg import Application
from jarvis_util import *

class MyWorkflow(Application):
    def _init(self):
        pass

    def _configure_menu(self):
        return [
            {
                "name": "script_path",
                "msg": "Path to the script to run",
                "type": str,
                "default": None,
            },
            # ... more config params
        ]

    def configure(self, **kwargs):
        self.update_config(kwargs, rebuild=False)
        # Process and validate config

    def start(self):
        # Execute the workflow
        Exec(f"python {self.config['script_path']}")

    def stop(self):
        pass

    def clean(self):
        pass
```

### 3. Jarvis Configuration

- Repositories are stored in Jarvis config: `~/.jarvis/config/jarvis_config.yaml` (or similar).
- After adding a repo, Jarvis must save the config for persistence.

---

## Creating a New Package Type (`pkg_type`)

### Step 1: Choose Repository Location

**Ask the user**:
- Where should the repository be located? (e.g., `/home/user/jarvis-work/repos/my_repo`)
- What should the repository name be? (typically the basename of the path)

### Step 2: Create Directory Structure

```bash
mkdir -p <repo_path>/<repo_name>/<pkg_type>
touch <repo_path>/<repo_name>/__init__.py
touch <repo_path>/<repo_name>/<pkg_type>/__init__.py
```

### Step 3: Write `pkg.py`

**Ask the user**:
- What scripts/commands does this workflow run?
- What configuration parameters are needed? (paths, node counts, flags, etc.)
- What are the default values?
- How should the workflow be executed? (`start()` method)

**Create `pkg.py`** with:
- Class name = `to_camel_case(pkg_type)` (e.g., `thousand_genome_workflow` → `ThousandGenomeWorkflow`).
- `_configure_menu()` returning all config parameters.
- `configure()` processing and validating inputs.
- `start()` executing the workflow (using `Exec()` from `jarvis_util`).

### Step 4: Add Documentation (Optional)

Create `README.md` in the `pkg_type` directory with:
- Description of what the workflow does.
- Required inputs/outputs.
- Configuration parameters.
- Usage examples.

---

## Registering the Package Repository

### Option A: CLI (Recommended for Initial Setup)

```bash
jarvis repo add <repo_path>
```

**Example**:
```bash
jarvis repo add /home/mtang11/jarvis-work/repos/1000genome_repo
```

This automatically saves the config.

### Option B: MCP (If Available)

```python
jm_add_repo(path="/home/user/repos/my_repo")
jm_save_config()  # Important: save to persist
```

**Note**: MCP repo tools may not always be available; CLI is more reliable for initial registration.

### Verification

**CLI**:
```bash
jarvis repo list <repo_name>  # List pkg_types in repo
```

**MCP**:
```python
jm_list_repos()  # List all repos
jm_get_repo(repo_name="my_repo")  # Get repo info
```

---

## Adding Packages to Pipelines

### Using CLI

```bash
# Set current pipeline context
jarvis pipeline cd <pipeline_id>

# Append a package
jarvis pipeline append <pkg_type> [pkg_id] [config_key=value ...]

# Example:
jarvis pipeline append thousand_genome_workflow num_nodes=2
```

### Using MCP

```python
append_pkg(
    pipeline_id="my-pipeline",
    pkg_type="thousand_genome_workflow",
    pkg_id="thousand_genome_workflow",  # Optional
    do_configure=True,  # Default: True
    extra_args={  # Dict of config parameters
        "num_nodes": 2,
        "workflow_dir": "/path/to/workflow",
    }
)
```

**Parameters**:
- **`pipeline_id`**: Name of the pipeline (must exist or be created first).
- **`pkg_type`**: The package type (must exist in a registered repo).
- **`pkg_id`**: Optional instance name (defaults to `pkg_type` if not provided).
- **`do_configure`**: Whether to run `configure()` immediately (default: `True`).
- **`extra_args`**: Dictionary of configuration parameters (keys match `_configure_menu()` names).

### Creating a New Pipeline

**CLI**:
```bash
jarvis pipeline create <pipeline_id>
```

**MCP**:
```python
create_pipeline(pipeline_id="my-pipeline")
```

---

## Information to Collect from Users

When creating a new workflow package, **ask the user for**:

### 1. Workflow Details
- **What does this workflow do?** (description)
- **What scripts/executables does it run?** (paths and names)
- **What are the input/output files/directories?**
- **How is it currently executed?** (command line, sbatch, etc.)

### 2. Repository Location
- **Where should the repository be created?** (e.g., `/home/user/jarvis-work/repos/my_repo`)
- **What should the repository name be?** (typically basename of path)

### 3. Package Type Name
- **What should the `pkg_type` be called?** (e.g., `thousand_genome_workflow`, `my_analysis`)
- **Note**: Must be a valid Python identifier (no leading digits, use underscores).

### 4. Configuration Parameters
For each config parameter, ask:
- **Parameter name** (e.g., `script_path`, `num_nodes`)
- **Description** (what it does)
- **Type** (`str`, `int`, `bool`, `list`, etc.)
- **Default value** (if any)
- **Is it required?** (`required: True` or `default: None`)

### 5. Execution Details
- **How should `start()` execute the workflow?**
  - Direct command? (e.g., `Exec("python script.py")`)
  - Sbatch submission? (e.g., `Exec("sbatch script.sbatch")`)
  - With environment variables? (set `self.env` first)
- **Does it need `stop()` or `clean()` methods?** (or can they be `pass`?)

### 6. Pipeline Integration
- **What is the target pipeline ID?** (e.g., `"1000genome-workflow"`)
- **Should this be a new pipeline or added to an existing one?**
- **What `pkg_id` should be used?** (optional, defaults to `pkg_type`)

---

## Complete Example: 1000genome Workflow

### User Provides:
- **Workflow**: Runs 1000 Genomes analysis via sbatch script
- **Scripts**: `/mnt/common/mtang11/scripts/1kgenome-pnnl/1000genome-workflow/bin/*.py`
- **Sbatch**: `ares_1kgenome_parallel.sbatch` in workflow directory
- **Repo path**: `/home/mtang11/jarvis-work/repos/1000genome_repo`
- **Repo name**: `1000genome_repo` (from basename)
- **pkg_type**: `thousand_genome_workflow`
- **Config**: `workflow_dir`, `bin_dir`, `sbatch_script`, `num_nodes`, `run_dir`

### Created Structure:

```
/home/mtang11/jarvis-work/repos/1000genome_repo/
└── 1000genome_repo/
    ├── __init__.py
    └── thousand_genome_workflow/
        ├── __init__.py
        ├── pkg.py                    # Class: ThousandGenomeWorkflow
        └── README.md
```

### Registration:

```bash
jarvis repo add /home/mtang11/jarvis-work/repos/1000genome_repo
```

### Adding to Pipeline:

**CLI**:
```bash
jarvis pipeline cd 1000genome-workflow
jarvis pipeline append thousand_genome_workflow num_nodes=2
```

**MCP**:
```python
append_pkg(
    pipeline_id="1000genome-workflow",
    pkg_type="thousand_genome_workflow",
    pkg_id="thousand_genome_workflow",
    extra_args={"num_nodes": 2}
)
```

### Running:

**CLI**:
```bash
jarvis pipeline start
# or
jarvis pipeline run
```

**MCP**:
```python
run_pipeline(pipeline_id="1000genome-workflow")
```

---

## Troubleshooting

### Error: "Could not find pkg: <pkg_type>"

**Causes**:
1. Repository not registered → Run `jarvis repo add <repo_path>`.
2. Wrong `pkg_type` name → Check `jarvis repo list <repo_name>`.
3. Class name mismatch → Ensure class name matches `to_camel_case(pkg_type)`.
4. Missing `__init__.py` → Add empty `__init__.py` files.

**Fix**:
- Verify repo is registered: `jarvis repo list`.
- Check directory structure matches: `<repo_path>/<repo_name>/<pkg_type>/pkg.py`.
- Verify class name in `pkg.py` matches expected camel case.

### Error: "Input should be a valid dictionary" (extra_args)

**Cause**: MCP client sending `extra_args` as string instead of dict.

**Fix**: Ensure `extra_args` is a real Python dict:
```python
extra_args={"key": "value"}  # ✅ Correct
extra_args='{"key": "value"}'  # ❌ Wrong (string)
```

### Error: Invalid Python class name (e.g., `1000GenomeWorkflow`)

**Cause**: `pkg_type` starts with a digit, so `to_camel_case()` produces invalid class name.

**Fix**: Rename `pkg_type` to avoid leading digits:
- `1000genome_workflow` → `thousand_genome_workflow` or `one_k_genome_workflow`
- Update directory name and class name accordingly.

### Package Not Found After Adding Repo

**Cause**: Config not saved after `jm_add_repo()`.

**Fix**: Run `jm_save_config()` after adding repo (or use CLI `jarvis repo add` which auto-saves).

---

## Summary Checklist

When creating a new workflow package:

- [ ] **Collect workflow details** from user (scripts, execution method, config params)
- [ ] **Create repository structure** (`<repo_path>/<repo_name>/<pkg_type>/`)
- [ ] **Write `pkg.py`** with Application/Service class
- [ ] **Add `__init__.py`** files to make it a Python package
- [ ] **Register repository** (`jarvis repo add` or `jm_add_repo` + `jm_save_config`)
- [ ] **Verify package is discoverable** (`jarvis repo list <repo_name>`)
- [ ] **Add package to pipeline** (`append_pkg` or `jarvis pipeline append`)
- [ ] **Test execution** (`run_pipeline` or `jarvis pipeline start`)

---

## References

- Jarvis-CD documentation: See `jarvis.help` or `/home/mtang11/jarvis-cd/`
- Example packages: `/home/mtang11/jarvis-cd/builtin/builtin/`
- MCP server: `/home/mtang11/scripts/agent-toolkit/agent-toolkit-mcp-servers/jarvis/`
