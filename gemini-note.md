# Jarvis Pipeline Creation: Challenges & Resolutions

This document summarizes the technical obstacles encountered while deploying the `1000genome` workflow via Jarvis-MCP and the surgical fixes applied.

## 1. Abstract Method Mismatches
*   **Issue:** The initial `pkg.py` implementation failed with `Can't instantiate abstract class ... with abstract method _configure`.
*   **Resolution:** Introspection of the environment's `Application` class revealed that both `_configure` (internal) and `_configure_menu` are strictly required. I updated all `pkg.py` files to implement the full suite: `_init`, `_configure_menu`, `_configure`, `start`, `stop`, and `clean`.

## 2. MCP Server Module Caching
*   **Issue:** Even after updating `pkg.py` on disk, the MCP tool `append_pkg` continued to report abstract method errors. This indicated the MCP server's Python process had cached the old module definitions.
*   **Resolution:** Switched to using the Jarvis CLI (`jarvis pipeline append ...`) within a single shell command chain. This ensured a fresh process was used for each command, bypassing the server-side cache.

## 3. Command-Line Argument Inference
*   **Issue:** The WDD lacked the specific positional arguments required by the Python scripts in `bin/`.
*   **Resolution:** Analyzed the source `daxgen.py` and `data.csv` to derive the necessary parameters (chromosome numbers, line ranges, and file paths) for each stage of the pipeline.

## 4. Local File Dependencies
*   **Issue:** `individuals.py` and other scripts expected `columns.txt` to exist in the local working directory.
*   **Resolution:** Updated the Jarvis package `start()` method to automatically symlink `columns.txt` from the input data directory into the designated `work_dir` (`/tmp/1000genome_run`) before execution.

## 5. Dependency Management (Matplotlib)
*   **Issue:** Analysis tasks failed due to a missing `matplotlib` dependency, and standard `pip install` was blocked by virtualenv/system permissions.
*   **Resolution:** Performed a targeted installation of `matplotlib` to a user-accessible directory (`/tmp/matplotlib_lib`) and programmatically injected this path into the `PYTHONPATH` environment variable within the package `start()` method using `LocalExecInfo`.

## 6. Execution Optimization
*   **Issue:** The default workflow configuration processed 250,000 lines, leading to long execution times and tool timeouts.
*   **Resolution:** Reduced the test range to 1000 lines in the `individuals` and `individuals_merge` tasks to allow for rapid end-to-end verification of the pipeline logic.
