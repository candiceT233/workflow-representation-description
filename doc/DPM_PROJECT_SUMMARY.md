# DPM (Dataflow Performance Matching) - Project Summary

**Project Name:** DPM (Dataflow Performance Matching)  
**Version:** V3 (Design Complete, Implementation In Progress)  
**Last Updated:** January 2026

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Input Data Formats](#input-data-formats)
4. [Output Data Formats](#output-data-formats)
5. [I/O Parameters Reference](#io-parameters-reference)
6. [MCP Tools and APIs](#mcp-tools-and-apis)
7. [Key Components](#key-components)
8. [Data Flow Pipeline](#data-flow-pipeline)

---

## Project Overview

DPM (Dataflow Performance Matching) is a Model Context Protocol (MCP) server system for analyzing, visualizing, and optimizing data flow performance in scientific workflows. The system processes workflow execution traces, benchmark data, and storage performance profiles to:

- **Visualize** workflow data flows with interactive diagrams
- **Analyze** I/O patterns, bottlenecks, and critical paths
- **Predict** performance across different storage and parallelism configurations
- **Optimize** workflow deployment strategies using DPM (Data Pipeline Metric) calculations

### Core Capabilities

1. **Workflow Visualization** (V1): Interactive dataflow diagrams, critical path analysis, I/O statistics
2. **Performance Profiling** (V3): Benchmark data processing, coverage analysis, quality validation
3. **DPM Analysis** (V3): Performance prediction, storage optimization, configuration ranking

---

## System Architecture

### Shared Foundation: Workflow Graph Builder

Both visualization and DPM analysis share a common graph construction foundation:

```
┌─────────────────────────────────────────────────────────────┐
│         Shared Foundation: Workflow Graph Builder            │
│                                                              │
│  Input:                                                      │
│    • Workflow traces (BlockTrace + DatalifeTrace JSON)      │
│    • Workflow schema (task definitions, file patterns)      │
│                                                              │
│  Core Components:                                           │
│    • data_parser.py  - Trace parsing & correlation          │
│    • graph_builder.py - DFL-DAG construction                │
│       - Task Name Priority System                           │
│       - Adaptive Parallelism                                │
│       - PID tracking (task PIDs, file read/write PIDs)     │
│                                                              │
│  Output: NetworkX DiGraph (Bipartite: Tasks ↔ Files)        │
└─────────────────────────────────────────────────────────────┘
```

### Graph Structure

The system builds a bipartite directed graph (DFL-DAG) with:

- **Task Nodes**: Represent workflow tasks with attributes:
  - `type`: 'task'
  - `task_name`: Task name (e.g., "openmm", "aggregate")
  - `task_instance`: Instance number (0, 1, 2, ...)
  - `pid`: Process ID
  - `stage_order`: Sequential position in workflow
  - `pos`: (x, y) position for visualization

- **File Nodes**: Represent data files with attributes:
  - `type`: 'file'
  - `write_pids`: List of PIDs that wrote to this file
  - `read_pids`: List of PIDs that read from this file
  - `pos`: (x, y) position for visualization

- **Edges**: Represent data flow with attributes:
  - `op_type`: 'read' or 'write'
  - `volume`: Total bytes transferred (int)
  - `op_count`: Number of I/O operations (int)
  - `io_time`: Total I/O time in seconds (float)
  - `rate`: Transfer rate in bytes/sec (float)
  - `sequential_ops`: Count of sequential operations (int)
  - `random_ops`: Count of random operations (int)

---

## Input Data Formats

### 1. Workflow Schema (JSON)

**Location:** `workflow_traces/<workflow_name>/<workflow_name>_*_schema.json`

**Format:**
```json
{
  "<task_name>": {
    "stage_order": 0,
    "parallelism": 12,
    "num_tasks": 12,
    "predecessors": {
      "<prev_task_name>": {
        "files": ["pattern1", "pattern2"]
      }
    },
    "outputs": ["output_pattern1", "output_pattern2"]
  }
}
```

**Fields:**
- `stage_order`: Integer, sequential position (0-based)
- `parallelism`: Integer, number of parallel instances
- `num_tasks`: Integer, total number of task instances
- `predecessors`: Dict mapping previous task names to file patterns
- `outputs`: List of regex patterns for output files

### 2. BlockTrace Files (JSON)

**Location:** `workflow_traces/<workflow_name>/<trace_dir>/*.r_blk_trace.json` or `*.w_blk_trace.json`

**Format:**
```json
{
  "io_blk_range": [start_block, end_block, total_blocks, access_pattern],
  "task_name": "optional_task_name"
}
```

**Fields:**
- `io_blk_range[0]`: Start block number (int)
- `io_blk_range[1]`: End block number (int)
- `io_blk_range[2]`: Total blocks accessed (int)
- `io_blk_range[3]`: Access pattern (int: -1=sequential, -2=random) or (str: "sequential", "random")
- `task_name`: Optional task name string

**Filename Pattern:**
- Read: `<filename>.<pid>-<hostname>.r_blk_trace.json`
- Write: `<filename>.<pid>-<hostname>.w_blk_trace.json`

### 3. DatalifeTrace Files (JSON)

**Location:** `workflow_traces/<workflow_name>/<trace_dir>/monitor_timer.<pid>-<hostname>.datalife.json`

**Format:**
```json
{
  "<process_name>": {
    "monitor": {
      "read": [io_time, op_count, total_bytes],
      "write": [io_time, op_count, total_bytes]
    }
  }
}
```

**Fields:**
- `read[0]`: I/O time in seconds (float)
- `read[1]`: Operation count (int)
- `read[2]`: Total bytes (int)
- `write[0]`: I/O time in seconds (float)
- `write[1]`: Operation count (int)
- `write[2]`: Total bytes (int)

**Filename Pattern:**
`monitor_timer.<pid>-<hostname>.datalife.json`

### 4. IOR Benchmark Files (JSON)

**Location:** `input/ior_data/`

**Format:**
```json
{
  "operation": "write",
  "randomOffset": 0,
  "transferSize": 1048576,
  "aggregateFilesizeMB": 1024.0,
  "numTasks": 12,
  "totalTime": 45.23,
  "numNodes": 4,
  "tasksPerNode": 3,
  "trMiB": 350.5,
  "storageType": "beegfs"
}
```

**Fields:**
- `operation`: "read", "write", "cp", "scp"
- `randomOffset`: 0 (sequential) or 1 (random)
- `transferSize`: Transfer size in bytes (int)
- `aggregateFilesizeMB`: Total file size in MB (float)
- `numTasks`: Number of parallel tasks (int)
- `totalTime`: Total time in seconds (float)
- `numNodes`: Number of compute nodes (int)
- `tasksPerNode`: Tasks per node (int)
- `trMiB`: Throughput in MiB/s (float)
- `storageType`: Storage system type (str)

### 5. Performance Profile Database (CSV)

**Location:** `input/updated_master_ior_df.csv`

**Schema:**
```python
operation: str              # 'write', 'read', 'cp', 'scp'
randomOffset: int           # 0 (sequential) or 1 (random)
transferSize: int           # Transfer size in bytes
aggregateFilesizeMB: float  # Total file size in MB
numTasks: int               # Number of parallel tasks
totalTime: float            # Total time in seconds
numNodes: int               # Number of compute nodes
tasksPerNode: int           # Tasks per node
parallelism: int            # Total parallelism (numNodes × tasksPerNode)
trMiB: float                # Throughput in MiB/s
storageType: str            # Storage system type
```

---

## Output Data Formats

### 1. Dataflow Diagram (HTML)

**Location:** `output/<workflow_name>_<timestamp>.html`

**Format:** Interactive Plotly HTML visualization

**Features:**
- Interactive Sankey diagram
- Hover tooltips with edge details
- Critical path highlighting
- Customizable canvas size

**Edge Tooltip Format:**
```
Edge: task_0 -> file.h5
Volume: 1024.50 MB
Op Count: 1,234
Rate: 350.50 MB/sec
```

### 2. I/O Summary Statistics (Text)

**Location:** `output/<workflow_name>_summary.txt`

**Format:** Human-readable text report

**Structure:**
```
Workflow: <workflow_name>
================================================================================

WORKFLOW TOTALS
--------------------------------------------------------------------------------
All Operations:
  Volume: X.XX GiB (X.XX GiB)
  Operations: X,XXX
  I/O Time: X.XX s
  Access Pattern: sequential/mixed/random
    - Sequential: X,XXX ops
    - Random: X,XXX ops
  Bandwidth: X.XX MiB/s

Read Operations:
  ...

Write Operations:
  ...

================================================================================
PER-TASK STATISTICS
================================================================================

Task Group: <task_name>
  Parallelism: X instance(s)
  Instances: <task_name>_0, <task_name>_1, ...
  Total Task Time: X.XX s
  
  All Operations:
    Volume: X.XX GiB (X.XX GiB)
    Operations: X,XXX
    I/O Time: X.XX s
    Access Pattern: sequential/mixed/random
    Bandwidth: X.XX MiB/s
  
  Read Operations:
    ...
  
  Write Operations:
    ...
```

### 3. I/O Summary Statistics (JSON)

**Location:** `output/logs/results/get_flow_summary_stats_<timestamp>.json`

**Format:**
```json
{
  "workflow_name": "ddmd",
  "selected_tasks": [],
  "selected_files": [],
  "output_file": "output/ddmd_summary.txt",
  "totals": {
    "all": {
      "volume_bytes": 5368709120,
      "volume_gb": 5.0,
      "op_count": 1000,
      "io_time_seconds": 45.23,
      "access_pattern": "sequential",
      "sequential_ops": 1000,
      "random_ops": 0,
      "bandwidth_bytes_per_sec": 118700000.0
    },
    "read": { ... },
    "write": { ... }
  },
  "per_task": {
    "<task_name>": {
      "parallelism": 12,
      "task_instances": [0, 1, 2, ...],
      "read": { ... },
      "write": { ... },
      "all": { ... },
      "total_task_time_seconds": 45.23
    }
  },
  "timestamp": "2026-01-20T12:34:56-789012"
}
```

### 4. DPM Analysis Results (JSON)

**Location:** `output/logs/results/analyze_workflow_dpm_<timestamp>.json`

**Format:**
```json
{
  "node_count": 4,
  "total_edges": 15,
  "edges_analyzed": 15,
  "prediction_method": "interpolation",
  "task_group_results": [
    {
      "producer_task_name": "openmm",
      "consumer_task_name": "aggregate",
      "producer_total_tasks": 12,
      "consumer_total_tasks": 1,
      "file_count": 12,
      "edge_count": 12,
      "top_5_storage_configs": [
        {
          "producer_storage": "ssd",
          "consumer_storage": "beegfs",
          "num_nodes": 4,
          "dpm": 45.23,
          "workflow_io_time": 40.0,
          "data_movement_time": 5.23
        }
      ],
      "all_dpm_scores": { ... }
    }
  ],
  "summary": {
    "total_edges": 15,
    "edges_analyzed": 15,
    "task_groups": 3,
    "best_overall_storage": "ssd_x_beegfs"
  }
}
```

### 5. Critical Path Analysis (JSON)

**Format:**
```json
{
  "critical_path": ["task_0", "file_A", "task_1", "file_B", "task_2"],
  "critical_path_length": 120.5,
  "metric": "volume",
  "bottlenecks": [
    {
      "edge": ["task_0", "file_A"],
      "weight": 50.2,
      "reason": "High volume transfer"
    }
  ]
}
```

### 6. Performance Profile Coverage Report (JSON)

**Format:**
```json
{
  "total_records": 21918,
  "storage_types": ["beegfs", "ssd", "tmpfs", ...],
  "coverage_matrix": {
    "beegfs": {
      "read": { "coverage": 0.85, "gaps": [...] },
      "write": { "coverage": 0.90, "gaps": [...] }
    }
  },
  "recommendations": [...]
}
```

---

## I/O Parameters Reference

### Workflow Trace Parameters

#### BlockTrace Parameters
- `file_name`: String, name of the file being accessed
- `pid`: Integer, process ID
- `hostname`: String, hostname where process ran
- `operation`: String, 'read' or 'write'
- `start_block`: Integer, starting block number
- `end_block`: Integer, ending block number
- `total_blocks_accessed`: Integer, total number of blocks
- `access_pattern`: Integer (-1=sequential, -2=random) or String ("sequential", "random")
- `task_name`: Optional string, task name from trace

#### DatalifeTrace Parameters
- `pid`: Integer, process ID
- `hostname`: String, hostname where process ran
- `io_time`: Float, I/O time in seconds
- `op_count`: Integer, number of I/O operations
- `total_bytes`: Integer, total bytes transferred
- `operation`: String, 'read' or 'write'

#### CorrelatedTrace Parameters
Combines BlockTrace and DatalifeTrace:
- All BlockTrace parameters
- All DatalifeTrace parameters
- Correlated by: `(pid, hostname, operation)`

### Graph Edge Parameters

#### Basic Edge Attributes
- `op_type`: String, 'read' or 'write'
- `volume`: Integer, total bytes transferred
- `op_count`: Integer, total number of operations
- `io_time`: Float, total I/O time in seconds (summed across traces)
- `rate`: Float, transfer rate in bytes/sec (calculated if io_time > 0)
- `sequential_ops`: Integer, count of sequential operations
- `random_ops`: Integer, count of random operations

#### DPM Edge Attributes (V3)
- `producer_total_tasks`: Integer, total producer task instances
- `consumer_total_tasks`: Integer, total consumer task instances
- `dpm_prediction_scores`: Dict, nested structure:
  ```python
  {
    "<N>_nodes": {
      "<P_STORAGE>_x_<C_STORAGE>": {
        "estT_prod": float,
        "estT_cons": float,
        "DPM": float,
        "workflow_io_time": float,
        "data_movement_time": float
      }
    }
  }
  ```

### DPM Calculation Parameters

#### Data Size Parameters
- `aggregateFilesizeMBtask`: Float, per-task I/O size in MB (single task PID entry)
- `aggregateFilesizeMB`: Float, task-per-node I/O size in MB (after preprocessing)
  - Formula: `sum(aggregateFilesizeMBtask for same taskName) / numNodes`

#### Task Identification Parameters
- `taskName`: String, task name in workflow (e.g., "openmm", "aggregate")
- `taskPID`: Integer, process ID distinguishing parallel instances
- `fileName`: String, file name(s), may be comma-delimited for cp/scp
- `stageOrder`: Integer, sequential position of task in workflow
- `prevTask`: String, previous task name in dependency chain

#### System Configuration Parameters
- `numNodes`: Integer, number of compute nodes
- `parallelism`: Integer, total parallel tasks/processes (single-node)
- `tasksPerNode`: Integer, tasks per node (multi-node)
- `n_prod` / `n_cons`: Integer, producer/consumer parallelism levels

#### I/O Operation Parameters
- `operation`: String, 'read', 'write', 'cp', 'scp', or 'none'
- `transferSize`: Integer, size of each I/O transfer in bytes
- `storageType`: String, storage system type (e.g., "ssd", "beegfs", "tmpfs")
- `prod_storage` / `cons_storage`: String, producer/consumer storage types

#### Transfer Rate Parameters
- `estimated_trMiB_{storage}_{parallelism}p`: Float, estimated transfer rate in MiB/s
  - Example: `estimated_trMiB_ssd_15p` = 350.5
- `prod_estimated_trMiB` / `cons_estimated_trMiB`: Float, producer/consumer estimated transfer rates

#### Time Calculation Parameters
- `estT_prod`: Float, estimated producer time (seconds)
  - Formula: `prod_aggregateFilesizeMBtask / prod_estimated_trMiB`
- `estT_cons`: Float, estimated consumer time (seconds)
  - Formula: `cons_aggregateFilesizeMBtask / cons_estimated_trMiB`
- `DPM`: Float, Data Pipeline Metric
  - Per entry: `estT_prod + estT_cons`
  - Aggregated: `average(producer-task-groups DPM) + average(consumer-task-groups DPM)`

#### Storage Tier Parameters
- **Canonical Storage Tiers:**
  - `tmpfs`: In-memory, fast, volatile (node-local)
  - `ssd`: Solid-state, fast, persistent (node-local)
  - `beegfs`: Parallel filesystem, shared storage (remote)

- **Valid Storage Transitions (6 pairs):**
  1. `tmpfs` ↔ `beegfs` (remote movement)
  2. `ssd` ↔ `beegfs` (remote movement)
  3. `tmpfs` ↔ `tmpfs` (local node-to-node)
  4. `ssd` ↔ `ssd` (local node-to-node)
  5. ❌ NOT VALID: `tmpfs` ↔ `ssd` (both local, no movement needed)

#### Data Movement Parameters
- `source_storage`: String, source storage tier
- `dest_storage`: String, destination storage tier
- `total_files`: Integer, number of files to move
- `stage`: Float, fractional stage number (0.5, 1.5, 2.5, ...)
- `parallelism_levels`: Integer, number of sequential levels (default: 5)
- `operation`: String, 'cp' for copy operations

---

## MCP Tools and APIs

### V1: Visualization Tools

#### `get_sankey_data`
**Purpose:** Generate interactive dataflow diagram HTML

**Input Parameters:**
- `workflow_name`: String (optional if current workflow set)
- `start_task_id`: String (optional, start of task range)
- `end_task_id`: String (optional, end of task range)
- `selected_files`: List[str] (optional, file filter)
- `metric`: String, 'volume' | 'op_count' | 'rate' (default: 'volume')
- `output_file`: String (optional, default: auto-generated)
- `highlight_critical_path`: Boolean (default: True)
- `font_size`: Integer (default: 10)
- `node_pad`: Integer (default: 15)
- `transform_link_value`: Boolean (default: False)

**Output:**
- HTML file path (String)
- Interactive Plotly visualization

#### `get_flow_summary_stats`
**Purpose:** Calculate comprehensive workflow I/O statistics with per-task-group breakdown

**Input Parameters:**
- `workflow_name`: String (optional if current workflow set)
- `selected_tasks`: List[str] (optional, task filter)
- `selected_files`: List[str] (optional, file filter)
- `output_file`: String (optional, default: auto-generated)

**Output:**
- Text summary file path (String)
- JSON results file: `output/logs/results/get_flow_summary_stats_<timestamp>.json`
- Formatted text summary with:
  - Workflow-level totals (all, read, write)
  - Per-task-group statistics (parallelism, volumes, I/O times, bandwidth, access patterns)

#### `analyze_critical_path`
**Purpose:** Identify critical path and optimization opportunities

**Input Parameters:**
- `workflow_name`: String (optional if current workflow set)
- `weight_property`: String, 'volume' | 'op_count' | 'rate' (default: 'volume')

**Output:**
- JSON dict with critical path, length, bottlenecks

#### `adjust_sankey_canvas_size`
**Purpose:** Adjust canvas size of last generated diagram

**Input Parameters:**
- `width`: Integer
- `height`: Integer
- `font_size`: Integer (default: 10)
- `node_pad`: Integer (default: 15)
- `transform_link_value`: Boolean (default: False)

**Output:**
- Confirmation message (String)

### V3: Performance Profile Tools

#### `process_benchmarks`
**Purpose:** Process raw IOR and cp benchmark data into performance profile

**Input Parameters:**
- `ior_data_dir`: String (default: 'input/ior_data/')
- `cp_data_dir`: String (default: 'input/cp_data/')
- `output_file`: String (optional, default: 'input/updated_master_ior_df.csv')

**Output:**
- CSV file path (String)
- Updated performance profile database

#### `analyze_benchmark_coverage`
**Purpose:** Analyze performance profile coverage across storage×parallelism space

**Input Parameters:**
- `profile_file`: String (default: 'input/updated_master_ior_df.csv')

**Output:**
- JSON dict with coverage matrix, gaps, recommendations

#### `validate_benchmark_quality`
**Purpose:** Validate benchmark data quality and detect anomalies

**Input Parameters:**
- `profile_file`: String (default: 'input/updated_master_ior_df.csv')

**Output:**
- JSON dict with quality metrics, outliers, variance analysis

#### `plot_benchmark_performance`
**Purpose:** Plot performance curves with filtering (interactive HTML line graphs)

**Input Parameters:**
- `profile_file`: String (default: 'input/updated_master_ior_df.csv')
- `storage_types`: List[str] (optional)
- `operations`: List[str] (optional)
- `x_axis`: String, 'numNodes' | 'tasksPerNode' | 'aggregateFilesizeMB' | 'transferSize'
- `tasks_per_node`: Integer (optional)
- `aggregate_filesize_mb`: Float (optional)
- `transfer_size`: Integer (optional)
- `output_file`: String (optional)

**Output:**
- HTML file path (String)
- Interactive Plotly line graph

#### `list_benchmark_parameters`
**Purpose:** List available parameter values in benchmark database

**Input Parameters:**
- `profile_file`: String (default: 'input/updated_master_ior_df.csv')

**Output:**
- JSON dict with available values for each parameter

#### `get_plottable_scenarios`
**Purpose:** Get suggested plottable parameter combinations

**Input Parameters:**
- `profile_file`: String (default: 'input/updated_master_ior_df.csv')

**Output:**
- JSON list of suggested plotting scenarios

### V3: DPM Analysis Tools

#### `analyze_workflow_dpm`
**Purpose:** Full workflow DPM analysis with storage optimization

**Input Parameters:**
- `workflow_name`: String (optional if current workflow set)
- `prediction_method`: String, 'interpolation' | 'random_forest' (default: 'interpolation')
- `storage_tiers`: List[str] (optional, default: ['tmpfs', 'ssd', 'beegfs'])
- `node_deployment_options`: List[int] (optional, auto-calculated)
- `top_k`: Integer (default: 5)
- `benchmark_file`: String (default: 'input/updated_master_ior_df.csv')

**Output:**
- JSON dict with:
  - Task group results
  - Top-K storage configurations per group
  - Best overall configuration
  - Results file: `output/logs/results/analyze_workflow_dpm_<timestamp>.json`

#### `predict_dpm_space`
**Purpose:** Calculate DPM for a specific edge

**Input Parameters:**
- `producer_task_id`: String
- `consumer_task_id`: String
- `workflow_name`: String (optional if current workflow set)
- `prediction_method`: String, 'interpolation' | 'random_forest' (default: 'interpolation')
- `storage_tiers`: List[str] (optional)
- `node_deployment_options`: List[int] (optional)
- `benchmark_file`: String (default: 'input/updated_master_ior_df.csv')

**Output:**
- JSON dict with DPM prediction scores for all configurations

#### `get_workflow_node_options`
**Purpose:** Calculate node deployment options for workflow

**Input Parameters:**
- `workflow_name`: String (optional if current workflow set)

**Output:**
- JSON list of node count options

#### `train_random_forest_models`
**Purpose:** Train Random Forest models for DPM prediction

**Input Parameters:**
- `benchmark_file`: String (default: 'input/updated_master_ior_df.csv')
- `n_estimators`: Integer (default: 100)
- `output_dir`: String (default: 'models/random_forest/')

**Output:**
- JSON dict with training results, model paths

### Utility Tools

#### `list_workflows`
**Purpose:** List all available workflows

**Input Parameters:** None

**Output:**
- JSON list of workflow names

#### `set_current_workflow`
**Purpose:** Set current workflow for subsequent tool calls

**Input Parameters:**
- `workflow_name`: String

**Output:**
- Confirmation message (String)

#### `get_current_workflow`
**Purpose:** Get currently registered workflow

**Input Parameters:** None

**Output:**
- Current workflow name (String) or None

---

## Key Components

### 1. Data Parser (`src/dfl_mcp/data_parser.py`)

**Classes:**
- `SchemaLoader`: Loads workflow schema from JSON
- `TraceParser`: Parses and correlates BlockTrace and DatalifeTrace files

**Key Methods:**
- `load_schema(file_path)`: Load workflow schema
- `parse_and_correlate_traces(dir_path)`: Parse and correlate trace files

### 2. Graph Builder (`src/dfl_mcp/graph_builder.py`)

**Key Functions:**
- `build_dfl_dag(schema, traces)`: Build NetworkX DiGraph from schema and traces
- `_get_pid_to_task_name_map()`: Map PIDs to task names (Task Name Priority System)
- `_add_task_nodes()`: Add task nodes with PID tracking
- `_add_file_nodes()`: Add file nodes with PID tracking
- `_add_edges_and_annotate()`: Add edges with I/O attributes

**Features:**
- Task Name Priority System (3-tier priority)
- Adaptive Parallelism (actual PID count vs schema)
- On-demand file node creation
- Edge attribute aggregation (volume, op_count, io_time, access_pattern)

### 3. Metrics Calculator (`src/dfl_mcp/analysis/metrics.py`)

**Key Functions:**
- `calculate_flow_summary_stats(G, output_file, workflow_name)`: Calculate comprehensive I/O statistics

**Features:**
- Per-task-group aggregation (groups parallel instances by task name)
- Read/write operation breakdown
- Access pattern detection (sequential/random/mixed)
- Bandwidth calculation
- I/O time tracking (maximum for parallel execution)

### 4. DPM Predictor (`src/dfl_mcp/dpm/predictor.py`)

**Classes:**
- `DPMPredictor`: Main DPM prediction engine

**Key Methods:**
- `predict_dpm_space()`: Calculate DPM for all storage×parallelism configurations
- `_calculate_task_per_node_io_size()`: Preprocess I/O sizes
- `_interpolate_transfer_rate()`: 4D interpolation for transfer rate estimation

**Prediction Methods:**
- 4D Interpolation (default): Uses scipy griddata
- Random Forest: ML-based prediction (trainable, saveable)

### 5. Workflow Analyzer (`src/dfl_mcp/dpm/workflow_analyzer.py`)

**Key Functions:**
- `analyze_workflow_dpm()`: Full workflow DPM analysis
- `get_workflow_dpm_summary()`: Summary statistics

**Features:**
- Task group aggregation
- Configuration ranking
- Best storage identification

### 6. Performance Profile Processor (`src/dfl_mcp/perf_profile/processor.py`)

**Key Functions:**
- `process_raw_benchmarks()`: Process IOR and cp benchmark data
- `add_benchmarks()`: Incremental benchmark addition

**Features:**
- IOR JSON parsing
- cp log parsing
- Data aggregation and averaging
- CSV database management

---

## Data Flow Pipeline

### V1: Visualization Pipeline

```
1. Load Workflow Schema (JSON)
   ↓
2. Parse Trace Files (BlockTrace + DatalifeTrace)
   ↓
3. Correlate Traces (by PID, hostname, operation)
   ↓
4. Build DFL-DAG (NetworkX DiGraph)
   ↓
5. Filter Subgraph (optional)
   ↓
6. Calculate Metrics / Generate Visualization
   ↓
7. Output (HTML diagram / Text summary / JSON)
```

### V3: DPM Analysis Pipeline

```
1. Load Workflow DAG (from cache or build)
   ↓
2. Load Benchmark Data (CSV performance profile)
   ↓
3. Identify Workflow Stages
   ↓
4. INSERT DATA MOVEMENT STAGES (CRITICAL: Step 4 FIRST)
   ↓
5. AUGMENT WITH DPM SCORES (CRITICAL: Step 5 SECOND)
   ↓
6. Aggregate by Task Groups
   ↓
7. Rank Configurations
   ↓
8. Output (JSON results + log file)
```

**⚠️ CRITICAL EXECUTION ORDER:**
- Data movement insertion MUST happen BEFORE DPM augmentation
- Violating this order causes incorrect DPM scores

---

## Storage and Caching

### Cache Strategy (3-Tier)

1. **In-Memory Cache**: Fast access for current session
2. **Persistent JSON Cache**: `src/dfl_mcp/cache/dags/<workflow_name>.json`
3. **Build from Traces**: If cache miss, build from schema/traces

### Logging

**Log Files:**
- Location: `output/logs/workflow_mcp_<timestamp>.log`
- Format: Timestamped log entries with activity tracking

**Results Files:**
- Location: `output/logs/results/`
- Format: JSON files with timestamps
  - `get_flow_summary_stats_<timestamp>.json`
  - `analyze_workflow_dpm_<timestamp>.json`

---

## Project Structure

```
dpm/
├── README.md                    # Project overview
├── pyproject.toml               # Python dependencies
├── run_server.py                # MCP server launcher (stdio)
├── run_server_http.py           # MCP server launcher (HTTP/SSE)
├── interactive_cli.py            # Interactive CLI
│
├── docs/                        # Documentation
│   ├── DPM_PROJECT_SUMMARY.md   # This document
│   ├── DPM_Calculation_Reference.md
│   ├── DATA_MOVEMENT_STAGES.md
│   ├── PERFORMANCE_PROFILE_COMPONENT.md
│   └── ...
│
├── src/dfl_mcp/                 # Main source code
│   ├── server.py                # MCP server implementation
│   ├── data_parser.py           # Trace parsing
│   ├── graph_builder.py         # DFL-DAG construction
│   ├── models.py                # Data models
│   ├── analysis/                # Analysis modules
│   │   ├── metrics.py          # I/O statistics
│   │   ├── sankey_utils.py     # Visualization
│   │   └── critical_path.py    # Critical path analysis
│   ├── dpm/                     # DPM analysis
│   │   ├── predictor.py        # DPM prediction engine
│   │   ├── workflow_analyzer.py
│   │   └── predictors/         # Prediction methods
│   └── perf_profile/            # Performance profiling
│       ├── processor.py
│       ├── analyzer.py
│       └── visualizer.py
│
├── workflow_traces/             # Workflow trace data
│   └── <workflow_name>/
│       ├── <workflow>_schema.json
│       └── <trace_dir>/
│           ├── *.BlockTrace.json
│           └── *.DatalifeTrace.json
│
├── input/                       # Input data
│   ├── ior_data/                # IOR benchmark files
│   ├── cp_data/                 # cp benchmark files
│   └── updated_master_ior_df.csv  # Performance profile database
│
└── output/                      # Generated outputs
    ├── logs/                    # Log files and results
    ├── *.html                   # Visualizations
    └── *_summary.txt            # Text summaries
```

---

## Dependencies

**Core:**
- Python 3.10+
- networkx: Graph data structures
- fastmcp: MCP server framework
- pandas: Data manipulation
- plotly: Interactive visualizations

**DPM Analysis:**
- scipy>=1.15.3: 4D interpolation
- scikit-learn>=1.0.0: Random Forest models
- joblib>=1.0.0: Model serialization

**Server:**
- fastapi: HTTP server (optional)
- uvicorn: ASGI server (optional)
- sse-starlette: Server-Sent Events (optional)

---

## Version History

- **V1**: Visualization and analysis (✅ Implemented)
- **V3**: DPM analysis and performance profiling (🔄 In Progress)
  - Phase 1: Performance Profile Component (✅ Complete)
  - Phase 2: DPM Prediction Engine (✅ Complete)
  - Phase 3: Data Movement Stages (✅ Complete)
  - Phase 4: Integration and Ranking (✅ Complete)

---

## References

- **DPM Calculation Reference**: `docs/DPM_Calculation_Reference.md`
- **Data Movement Stages**: `docs/DATA_MOVEMENT_STAGES.md`
- **Performance Profile Component**: `docs/PERFORMANCE_PROFILE_COMPONENT.md`
- **Execution Order**: `docs/EXECUTION_ORDER_CRITICAL.md`
- **V3 Specification**: `imp_doc/v3_spec.md`

---

**Document Version:** 1.0  
**Last Updated:** January 2026
