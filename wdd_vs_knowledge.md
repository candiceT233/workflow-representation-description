Now I have everything. Let me build both tables.

---

## WDD Document Quality

| | claude-t1 | claude-t2 | claude-t3 | gemini-t1 | gemini-t2 | gemini-t3 | opencode-t3 |
|---|---|---|---|---|---|---|---|
| **Successfully generated** | ✅ | ❌ | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| **Lines** | 353 | 1 | 522 | 851 | 870 | 1,211 | 661 |
| **Source file correct** | ❌ empty | ❌ | ✅ daxgen.py | ❌ empty | ❌ sbatch | ✅ daxgen.py | ✅ daxgen.py |
| **Executable paths (bin/)** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Tasks count** | 5 | 0 | 5 | 6 | 7 | 7 | 6 |
| **Data objects count** | 9 | 0 | 9 | 10 | 9 | 9 | 9 |
| **PC edges count** | 4 | 0 | 5 | 5 | 5 | 12 | 5 |
| **I/O behavioral hints** | 5 | 0 | 5 | 2 | 2 | 2 | 3 |
| **workflow_description filled** | ✅ | ❌ | ✅ | ❌ template stub | ✅ | ✅ | ⚠️ garbled |
| **primary_pattern** | scatter_gather | EMPTY | scatter_gather | EMPTY | hybrid | hybrid | scatter_gather |
| **Pattern correctness** | ✅ | — | ✅ | — | ⚠️ debatable | ⚠️ debatable | ✅ |
| **Population counts (2504/26)** | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ⚠️ partial |
| **Execution profiles** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **translation_metadata quality** | ✅ detailed | ❌ | ✅ detailed | ⚠️ partial | ✅ detailed | ✅ detailed | ⚠️ minimal |

**Notes:** claude-t2 is a single-line hash computation stub — the write completely failed. gemini-t1 was generated from the template but most key fields left as `null` or empty stubs. gemini-t2 used the wrong source file (sbatch wrapper instead of the DAG generator), which caused the q017 scoring failure. opencode-t3's workflow_description contains a sentence fragment ("statistical-related mutations. It evaluation of disease fetches...") suggesting a generation glitch mid-sentence.

---

## Knowledge Document Quality

| | claude-t1 | claude-t2 | claude-t3 | gemini-t1 | gemini-t2 | gemini-t3 | opencode-t1 | opencode-t2 |
|---|---|---|---|---|---|---|---|---|
| **Successfully generated** | ❌ | ❌ | ❌ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ |
| **Lines / Words** | 14 / 105 | 22 / 197 | 8 / 76 | 195 / 1,990 | 64 / 515 | 101 / 652 | 1 / 19 | 1 / 19 |
| **Failure reason** | write permission | write permission | write permission | — | truncated | no file access | write stub | write stub |
| **Task structure correct** | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ wrong order | ❌ | ❌ |
| **Executable paths (bin/)** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Data formats specified** | ❌ | ❌ | ❌ | ✅ | ⚠️ partial | ❌ all unknown | ❌ | ❌ |
| **PC edges with patterns** | ❌ | ❌ | ❌ | ✅ | ⚠️ partial | ✅ (but wrong) | ❌ | ❌ |
| **I/O behavioral hints** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Population stats (2504/26)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Assumption count** | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 |
| **Usable as eval baseline** | ❌ | ❌ | ❌ | ✅ best | ⚠️ partial | ⚠️ unreliable | ❌ | ❌ |

---

**The big picture from both tables:** you have only one agent (gemini) that reliably completes both documents, and only trial1 produced a high-quality knowledge doc. Claude Code fails on knowledge docs across all three trials due to write permission not being granted in the evaluation harness — this is a tooling issue, not a model quality issue, and it's fixable by adding `--dangerously-skip-permissions` to the eval script invocation as Claude itself suggested in trial2. OpenCode fails identically on knowledge docs. The practical implication: for any multi-agent WDD comparison to be valid, you need to fix the write permission problem for Claude and OpenCode first.


---

## Quality Comparison: claude-t3 WDD vs. gemini-t3 WDD vs. gemini-t1 Knowledge

### Coverage Matrix

| Information Category | WDD claude-t3 | WDD gemini-t3 | Knowledge gemini-t1 |
|---|---|---|---|
| **Scientific purpose / domain context** | ✅ full narrative | ✅ full narrative | ❌ not stated |
| **2504 individuals / 26 populations** | ✅ | ✅ | ❌ |
| **Task names and count** | ✅ 5 correct | ✅ 5 correct | ✅ 5 correct |
| **Executable paths (bin/)** | ✅ `bin/individuals.py` | ❌ name only | ✅ `bin/individuals` |
| **Task CLI parameters (-c, -pop, start_line)** | ❌ | ❌ | ✅ explicitly listed |
| **Actual filenames (ALL.chrX.vcf, sifted.SIFT.chrX.txt)** | ❌ abstract IDs | ❌ abstract IDs | ✅ Pegasus filenames |
| **PC patterns (n_to_1, 1_to_n)** | ✅ 5 edges, structured | ✅ 12 edges, incl. config flows | ✅ prose + scatter-gather label |
| **ind_jobs parallelism parameter** | ✅ | ✅ | ✅ |
| **data.csv as chromosome manifest** | ❌ | ✅ as `config_file` | ✅ described in detail |
| **Decaf/PMC alternative execution paths** | ✅ hardware_path section | ✅ hardware_path section | ✅ mentioned in hints |
| **stage_out / staging behavior** | ❌ | ❌ | ✅ explicit True/False per file |
| **Population file breakdown (AFR, AMR…)** | ✅ 7 files with counts (661, 347…) | ⚠️ "7 per super population", no counts | ✅ lists files, no counts |
| **Lifecycle per data object** | ✅ retention_window | ✅ retention_window | ❌ |
| **Data reuse hint** | ✅ with staging recommendation | ❌ | ✅ mentioned |
| **Small-file overhead hint** | ✅ severity: high, 2504 files/chunk | ✅ noted | ✅ noted |
| **Unnecessary serialization insight** | ✅ compress→decompress→recompress | ❌ | ❌ |
| **Monte Carlo detail (1000 runs, 52 individuals)** | ✅ in task description | ✅ in task description | ❌ |
| **O(N²) pairwise complexity** | ✅ | ❌ | ❌ |
| **Severity ratings on hints** | ✅ high/medium/low | ❌ | ❌ |
| **Number of I/O hints** | 5 | 2 | 8 (prose) |
| **Number of PC edges** | 5 (task-to-task) | 12 (incl. all inputs) | 5 + 4 control-flow |
| **Execution profiles** | ✅ 3 with memory estimates | ✅ 2, no memory estimates | ❌ |
| **Per-field confidence records** | ✅ detailed | ✅ detailed | ❌ |
| **Workflow pattern label** | ✅ `scatter_gather` | ⚠️ `hybrid` | ⚠️ `hybrid` (better reasoning) |
| **use_bash / I/O tuning flags context** | ❌ | ❌ | ✅ |

---

### Key Takeaways from Adding gemini-t3

The two WDDs are structurally very similar — same source file, same 5 tasks, same lifecycle fields — which confirms the template is doing its job of enforcing consistency across agents. The differences are analytical depth, not structural gaps.

Claude-t3 beats gemini-t3 on **analytical precision**: O(N²) callout, severity ratings, population-level counts, unnecessary serialization, and more hints (5 vs. 2). Gemini-t3 beats claude-t3 on **edge completeness**: 12 PC edges vs. 5, capturing config file broadcast flows that matter for understanding shared-read contention.

Both WDDs lose to the knowledge doc on the same two categories: actual filenames and CLI parameters. This is a structural template gap, not an agent quality gap — neither WDD was prompted to capture these, but both agents clearly had access to them (gemini-t1 pulled them from the same daxgen.py). Adding `filename_pattern` to data objects and `cli_parameters` to tasks would close this gap for both agents simultaneously.

---

## OpenCode Trials: WDD and Knowledge (Trials 1–3)

*Added after fixing OpenCode permission issues (opencode.json, OPENCODE_YOLO env). All three trials now complete successfully.*

### OpenCode WDD Document Quality

| | opencode-t1 | opencode-t2 | opencode-t3 |
|---|---|---|---|
| **Lines** | 723 | 769 | 651 |
| **Source file** | daxgen.py | daxgen.py | daxgen.py |
| **Tasks count** | 5 | 5 | 5 |
| **Data objects count** | 9 | 9 | 9 |
| **PC edges count** | 5 | 5 | 5 |
| **I/O behavioral hints** | 3 | 3 | 2 |
| **workflow_description** | ✅ filled | ✅ filled | ✅ filled |
| **primary_pattern** | scatter_gather | scatter_gather | scatter_gather |
| **Executable paths (bin/)** | ✅ `bin/individuals.py` | ✅ | ✅ |
| **Population counts (2504/26)** | ✅ 2504 in description | ✅ | ✅ |
| **Execution profiles** | ✅ | ✅ | ✅ |
| **translation_metadata** | ✅ | ✅ | ✅ |
| **Empty stage** | ❌ | ❌ | ⚠️ `stage:data_loading` has tasks: [] |

**Notes:** OpenCode WDDs are structurally solid and consistent across trials. All use correct source (daxgen.py), correct task count (5), and include `bin/` executable paths — a gap in Gemini WDDs. Trial 3 introduces an empty `stage:data_loading` for "external input data" which is unusual.

### OpenCode Knowledge Document Quality

| | opencode-t1 | opencode-t2 | opencode-t3 |
|---|---|---|---|
| **Lines / Words** | 176 / ~1,800 | 267 / ~2,500 | 164 / ~1,600 |
| **Successfully generated** | ✅ | ✅ | ✅ |
| **Task structure correct** | ✅ 5 tasks, correct order | ✅ 5 tasks, correct order | ✅ 5 tasks, correct order |
| **Executable paths (bin/)** | ✅ `bin/individuals.py` | ✅ | ✅ |
| **Data formats specified** | ✅ VCF, tar.gz, text | ✅ | ✅ |
| **PC edges with patterns** | ✅ scatter_gather, data_dependency | ✅ | ✅ |
| **I/O behavioral hints** | ✅ 8 detailed | ✅ | ✅ |
| **Actual filenames** | ✅ | ✅ | ✅ |
| **CLI parameters** | ✅ -i, -c, -pop | ✅ -c, -pop, start_line, stop_line | ⚠️ partial |
| **Population stats (2504/26)** | ✅ 2504 in columns.txt | ✅ 2,504 individuals | ✅ 2504 |
| **Data reuse hint** | ✅ | ✅ | ✅ |
| **Usable as eval baseline** | ✅ | ✅ | ✅ |

**Notes:** OpenCode knowledge docs are now complete and high quality. All three include actual Pegasus filenames, `bin/` paths, CLI parameters, and I/O hints. Trial 2 is the most detailed (268 lines, explicit CLI args). Trial 1 has the strongest I/O behavioral hints section (8 patterns with evidence).

### OpenCode vs. Gemini Comparison

| Information Category | OpenCode WDD | OpenCode Knowledge | Gemini WDD | Gemini Knowledge |
|---|---|---|---|---|
| **Executable paths (bin/)** | ✅ | ✅ | ❌ name only | ✅ |
| **Source file correct** | ✅ daxgen.py | ✅ | ⚠️ t2 used sbatch | ✅ |
| **Population counts (2504/26)** | ✅ | ✅ | ⚠️ t1 missing | ❌ |
| **Actual filenames** | ❌ abstract IDs | ✅ | ❌ | ✅ t1 |
| **CLI parameters** | ❌ | ✅ | ❌ | ✅ t1 |
| **Consistency across trials** | ✅ | ✅ | ⚠️ t1 template, t2 wrong source | ⚠️ t2 truncated, t3 wrong |

**Key takeaway:** OpenCode now matches or exceeds Gemini on both WDD and knowledge. OpenCode's WDDs uniquely include `bin/` executable paths. OpenCode knowledge docs are consistently complete across all three trials, unlike Gemini (t2 truncated, t3 wrong order).