# Project 1 findings — synchronous FIFO

**Course:** EEE 4701\
**Team:** William Garland, Banmeet Singh, Daniel Jo\
**Updated:** November 13, 2026

The layered baseline passes 5/5 tests. The existing pyvsc suite reaches all **70/70 implemented coverage bins** for three default-configuration seeds. Two supplemental parameter configurations also pass their functional checks; their coverage totals are reported separately below. Replaying seed 4701 produces identical generated stimulus and coverage. Both baseline and CRV detect **8/8 released mutants**. The final report PDF and demo link remain pending separately.

The runs use Banmeet's original `crv/` and `coverage/` files. Daniel's `ai_log.md` is also unchanged. The added runner executes temporary copies and saves fresh evidence outside those paths. The monitor adds explicit unresolved-value assertions and optional passive tracing; it does not tune or replace the CRV generator or coverage model.

## Reproduction and evidence

```bash
python scripts/run_verification.py --output evidence/generated
```

Install `requirements.txt` into a Python 3.12 environment with Icarus Verilog 12.0 available. See [README.md](README.md) for setup and individual commands. Evidence is in the [regression](evidence/current/regression/summary.json), [convergence](evidence/current/convergence/summary.json), and [mutation](evidence/current/mutations/summary.json) summaries. Each includes source hashes, protected-file hashes, tool versions, seed and exact invocation. Per-case logs and XML are retained.

A matching seed is set before cocotb imports pyvsc (`RANDOM_SEED`), in the existing test (`SEED`), and with `PYTHONHASHSEED=0`. The runner's RTL width/depth overrides match the values exported to the existing CRV model. Build arguments are supplied through the environment so cocotb can still append its simulator-timescale configuration.

The replay check compares both the entire YAML coverage report and the stimulus summary, including the SHA-256 of the 5,000 generated transactions. It is stronger than comparing the final coverage percentage alone. The five-test baseline's Python-random seed is separately `0x4701` (18177 decimal).

The manifest's base commit identifies the starting checkout; file-level hashes identify the exact tested additions and edits. Fresh evidence does not reuse the older Eustis log results.

## Functional coverage and convergence

Banmeet's model covers occupancy, requested and accepted operations, important occupancy transitions, write-data classes, read/write request bursts, inferred pointer wraps, reset/control overlap, and two occupancy crosses. The model has 70 reachable bins. The four ignored accepted-operation combinations are impossible under the FIFO contract; all full/empty **requests** remain included.

| Regression | WIDTH×DEPTH | Bins hit/total | First recorded closure cycle |
|---|---|---:|---:|
| seed-4701 | 8×8 | 70/70 | 1200 |
| seed-17 | 8×8 | 70/70 | 410 |
| seed-4702 | 8×8 | 70/70 | 1390 |
| seed-4701-repeat | 8×8 | 70/70 | 1200 |
| width16-depth5 | 16×5 | 69/70 | Not reached |
| width8-depth4 | 8×4 | 70/70 | 1200 |

Closure tracking checks every ten samples; the cycle is an upper bound within that interval, not an exact first-hit timestamp. Normal-loop coverage excludes initial reset and final drain. Pointer wraps are inferred from the reference model's accepted transfers; burst categories count requested operations.

The following uses the existing generator settings without source edits or directed coverage injection:

| Experiment, seed 4701 | Final bins | First recorded closure cycle | Remaining holes |
|---|---:|---:|---|
| uniform-5000 | 70/70 | 1350 | None |
| biased-3000 | 70/70 | 1200 | None |
| biased-5000 | 70/70 | 1200 | None |

The diagnostic 1,000-cycle run reached only 69/70 bins and failed the existing minimum-fill check (3 fills; at least 5 required). It is explicitly not a passing regression. Its reset-without-write bin remained open. Extending the run closes that bin; the tracker first observes full closure at cycle 1,200. The passing convergence runs use 3,000 and 5,000 cycles. This demonstrates why both coverage and stimulus-quality checks need sufficient run length. See [the retained short-run diagnostic](evidence/diagnostics/short-run/run.log). No claim is made that this session tuned the original constraints or independently reproduced the code comment's earlier 1/500-to-1/200 comparison. Uniform mode is an existing comparison setting, not a replacement for the required biased regression; it disables boundary/data constraints while retaining reset constraints.

Flags, FWFT head transitions and reset recovery are asserted by the layered tests but are not additional bins in this model. The revised [vplan.md](vplan.md) explicitly maps those checks rather than claiming the earlier proposed extra crosses were implemented. Reaching 70/70 is closure of this finite model, not proof of exhaustive verification.

## Stimulus distribution review

The code declares state-dependent write/read weights. Passive observations of seed 4701's 5,000 random-loop transactions show:

| State/phase | Draws | Declared write / read | Measured write / read |
|---|---:|---:|---:|
| near_empty | 1147 | 70% / 60% | 61.55% / 61.73% |
| near_full | 712 | 60% / 70% | 61.10% / 61.52% |
| middle_fill | 1966 | 90% / 30% | 61.95% / 61.90% |
| middle_drain | 1175 | 30% / 90% | 62.38% / 61.36% |

Source: [seed-4701/stimulus.json](evidence/current/regression/seed-4701/stimulus.json). Counts include reset draws, matching the transaction generator; initial reset and final drain are excluded. Regions and fill/drain transitions follow the existing class's conditions.

The measured probabilities are much closer to each other than the declared state-dependent targets. Thus the intended 90%/30% interior bias is **not demonstrated by this run**. Coverage still closes and the released mutants are detected, but neither result validates those probability claims. The mismatch is retained as an implementation limitation for the CRV owner to review; this integration deliberately does not change Banmeet's constraints. The evidence establishes a discrepancy, not its exact solver-level cause or a verified fix.

## Current mutation quality

| Suite | Released found/total | Final survivors |
|---|---:|---|
| Five-test layered baseline | 8/8 (100%) | None |
| Existing pyvsc regression, seed 4701 | 8/8 (100%) | None |

Each campaign starts with a passing clean control, then independently applies each replacement in `tb/mutants_released.yaml` to a disposable RTL copy. All variants compile and produce the expected test XML. Mutation detections require failed tests with assertion diagnostics. Missing XML, skipped tests, build failures or non-assertion failures are infrastructure errors, not detections. Coverage is not required to close in mutant runs; a coverage hole cannot kill a mutant.

| Mutant | Fault | Detecting behavior in the current suites |
|---|---|---|
| `full_offbyone` | Full asserted at DEPTH−1 | Reach near-full and compare flag/count to the queue |
| `empty_offbyone` | Empty asserted at count one | Reach one/empty and check flags/valid head |
| `ignore_full` | Accept writes at full | Full write or full simultaneous request; count/order comparison |
| `ignore_empty` | Accept reads at empty | Empty read or empty simultaneous request; count/flags and recovery |
| `count_wr_dec` | Decrement count on write | Write-only transaction versus queue occupancy |
| `rd_data_wrptr` | Head selected by write pointer | Valid-head comparison and unresolved-data assertion |
| `mem_corrupt` | Increment stored data | Exact valid-head data comparison |
| `wrptr_wrap_early` | Wrap write pointer early | Repeated pointer wrap with distinct values and queue ordering |

## Two documented historical survivors

Daniel's unchanged [Check the Machine log](ai_log.md) records a **6/8 (75%)** run with `ignore_full` and `ignore_empty` surviving. They are historical survivors, not survivors of the fresh 8/8 campaigns. The original AI-generated test version and seed are not present in that log, so this section analyzes his recorded evidence and explanation rather than claiming an exact reproduction of that earlier run.

| Historical survivor | Why the recorded stimulus missed it | What exposes the fault | Current result |
|---|---|---|---|
| `ignore_full` | The historical generator excluded write requests at full, leaving the erroneous acceptance path unexercised | Fill to DEPTH, request another write (alone and with a read), compare count/flags and drain the queue to check corruption | Detected by baseline and CRV |
| `ignore_empty` | The historical generator excluded read requests at empty, leaving underflow behavior unexercised | Drain to empty, request reads (alone and with a write), check count/flags, first valid head and recovery | Detected by baseline and CRV |

These are stimulus-reachability gaps: a correct scoreboard cannot expose a faulty path that is never exercised. The current suites include the required boundary requests. This supports the explanation, but the differing historical/current implementations mean the 6/8-to-8/8 comparison is not a controlled, isolated measurement of one change.

The written contract defines a full write as dropped and an empty read as ignored. Such requests are **legal tests of rejection behavior**, not illegal signals. This specification clarification supplements the wording in Daniel's original AI prompt and takeaway without editing his record.

## Remaining limitations and submission work

- The hidden mutation pool is unavailable; 8/8 released detection does not establish the hidden score.
- The declared-versus-measured CRV distribution mismatch above remains for the constraint owner to address if exact bias behavior is required.
- The supplemental 16×5 run reaches 69/70 bins; the alternating write-data bin is unhit. Two alternating 16-bit patterns occupy a much smaller part of the unconcentrated interior data range than at width 8. This optional configuration is not claimed coverage-closed. Default 8×8 closure remains mandatory in the runner.
- Only WIDTH/DEPTH 8×8, 16×5 and 8×4 are measured. Other sizes, particularly DEPTH=1, are not claimed supported or covered.
- Finite sequences and a finite 70-bin model cannot prove every history or temporal cross. Subcycle glitch freedom is not exhaustively checked.
- Empty-state data is unspecified. Reset-time transfers are not given semantics beyond the specified reset count/flags. The supplied interface has no almost-full signal or non-FWFT mode.
- The two-survivor analysis uses a clearly attributed historical record because the final released suites have no survivors.
- `REPORT.pdf`, the demo link and team review remain separate responsibilities. Automated execution is not a teammate attestation.

AI assistance in the new runner, documentation and validation is disclosed in [CONTRIBUTIONS.md](CONTRIBUTIONS.md). Daniel's Check the Machine record and Banmeet's original implementation/report retain their ownership and exact contents.
