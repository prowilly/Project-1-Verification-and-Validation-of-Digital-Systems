# Verification plan — synchronous FWFT FIFO (Project 1)

**Course:** EEE 4701 / EEE 5703 — Verification and Validation of Digital Systems  
**Team / authors:** Project 1 team — enter all team member names and reviewer initials in `CONTRIBUTIONS.md`  
**Specification:** `dut/specs/fifo.md`, *FIFO specification (dut/fifo.sv)*; file does not state a separate revision  
**DUT:** `dut/fifo.sv`; **independent expected-behavior review:** `lib/models/fifo_model.py`  
**Plan revision:** 1.0 (specification-grounded planning document)  
**Date:** 2026-11-03  
**Status:** Ready for team review; **Project 1 CRV, coverage, and regression results are not yet measured**.

> **Verification intent:** Establish, before running Project 1 tests, exactly what FIFO behavior we will check, which input/state combinations we will cover, how we will measure closure, and what evidence will justify signoff. The written FIFO specification is the behavioral authority. The RTL and model are implementation/reference artifacts to check **against** it, not replacements for the spec.

## 1. Scope

**In scope.** Verify the **synchronous, first-word fall-through (FWFT)** FIFO at its public pins (`clk`, `rst_n`, `wr_en`, `wr_data`, `rd_en`, `rd_data`, `full`, `empty`, and `count`). At the baseline `WIDTH=8`, `DEPTH=8`, check synchronous reset, accepted and rejected operations, occupancy and flags, data integrity and FIFO ordering, output-head visibility, simultaneous traffic at interior and boundary occupancies, idle/hold behavior, repeated pointer wraparound, and reproducible seeded constrained-random traffic. Include a spec-based reference-queue scoreboard, functional coverage with crosses, a mutation-quality regression, and a control-corner security/trust check. Exercise additional parameter combinations where the course runner supports them; report their results separately.

**Out of scope / interface differences.** This particular `fifo.sv` has **no `almost_full` port or threshold** and **no parameter to disable FWFT**. Although the broad Project 1 handout mentions almost-full and optional FWFT, neither is implemented in the supplied FIFO interface. Do not invent signals or promise tests for nonexistent configurations; record the discrepancy as risk R01. Also out of scope: asynchronous FIFO/clock-domain crossing, internal-memory implementation details, formal exhaustive proof, synthesis/timing/power, and the value of `rd_data` while `empty=1` (unspecified by the spec).

**Protocol and observation assumptions (confirmed by specification):**

- `clk` is a rising-edge clock and `rst_n` is **active-low, synchronous reset**: on a rising edge with reset asserted, `count=0`, `empty=1`, `full=0` afterward (**spec §Ports; §Behavior 1**). Reset is not assumed to act asynchronously.
- Accepted write = `wr_en && !full` **before** the edge; a write request at full is dropped. Accepted read = `rd_en && !empty` **before** the edge; a read request at empty is ignored (**§Behavior 2–3**). Both requests may be asserted together; those requests are **defined**, including at the boundaries.
- When both requests are asserted with `0 < count < DEPTH`, both transfers occur and occupancy is unchanged (**§Behavior 4**). By the per-request acceptance rules, at **empty**, simultaneous requests accept only the write; at **full**, they accept only the read. The spec explicitly calls out both boundary combinations (**§Corner cases**).
- After outputs settle, `full==(count==DEPTH)`, `empty==(count==0)` and `0<=count<=DEPTH` (**§Ports; §Behavior 5**). `rd_data` shows the **current head whenever not empty**; it is not checked while empty (**§Ports; §Behavior 3**).
- **Bench timing (testbench choice, not a spec timing requirement):** run a 10 ns clock, drive inputs at falling edges, compute model acceptance using pre-rising-edge occupancy, then sample outputs 1 ns after the rising edge to allow sequential updates to settle. Sample pre/post states separately so a boundary request is not judged using post-edge flags.

**HW4 baseline available for reuse (not new Project 1 evidence):** `HW4.zip` contains `test_fifo.py` with `FifoDriver`, `FifoMonitor`, `FifoScoreboard`, and `FifoBench`; the imported `FifoModel` has now been reviewed against spec §Behavior 1–6. The three existing tests are `test_fifo_directed_corners`, `test_fifo_pointer_wrap_and_reset`, and `test_fifo_seeded_random_interleave` (1,200 `random.Random` cycles, seed `0x4701`). Its `FINDINGS.md` reports **3/3 passing tests and 8/8 released mutants detected** on Eustis/Icarus. These are **HW4 historical results**; they are **not** Project 1 pyvsc, functional-coverage, or mutation results. The HW4 model/testbench currently hardcode `WIDTH=8`, `DEPTH=8` and will require refactoring for parameter sweeps.

## 2. Feature list

`Req` references the **official** `dut/specs/fifo.md`. **H** means mandatory baseline signoff; **M** means supplemental/configuration coverage. `HW4` means the test exists in supplied HW4 source, not that we reran it during preparation of this plan.

| ID | Feature / observable requirement | Req | Priority | Verification method |
|---|---|---|---|---|
| F01 | Synchronous low-active reset makes count zero, empty true, full false at the next rising edge; recovery after reset | §Ports (`rst_n`), §Behavior 1 | H | Initial and nonempty reset; scoreboard and reset checks (HW4 + extension) |
| F02 | Accepted write stores a WIDTH-bit value and increments count by one when not full | §Ports (`wr_*`), §Behavior 2, 6 | H | Write-only, distinct patterns; queue comparison (HW4) |
| F03 | Write requested while full is dropped without overflow/corruption | §Behavior 2; §Corner cases | H | Full-boundary writes followed by full drain (HW4 + coverage) |
| F04 | Accepted read removes exactly the oldest queued value and decreases count by one when not empty | §Behavior 3, 6 | H | Read-only and head/queue checks (HW4) |
| F05 | Read requested while empty is ignored without underflow | §Behavior 3; §Corner cases | H | Repeated empty reads, subsequent write/read recovery (HW4) |
| F06 | Full and empty flags track occupancy correctly on every observed cycle | §Ports (`count`, `full`, `empty`), §Behavior 5 | H | Per-edge count + flag assertions; 0/1/7/8 boundaries (HW4) |
| F07 | FWFT output continuously indicates the front element whenever not empty | §Ports (`rd_data`); §Behavior 3 | H | Compare post-edge valid head to queue; first write, pop, replace head (HW4) |
| F08 | FIFO preserves ordering and stored data through all mixes of traffic | §Behavior 6 | H | Unique and edge-case patterns, burst/drain, queue scoreboard (HW4 + CRV) |
| F09 | Simultaneous read+write at interior occupancy accept both and hold count | §Behavior 4 | H | Occupancy 1, middle, DEPTH−1; extended overlap sequences (HW4 + CRV) |
| F10 | Simultaneous requests at empty accept write only; at full accept read only | §Behavior 2–3; §Corner cases | H | Targeted boundary crossed with both enables; post-edge count/head (HW4 + CRV) |
| F11 | Idle cycles leave occupancy and valid data/flags stable | §Behavior 2–5 (no accepted transfer) | H | Idle at 0, middle, full; state stability checks (HW4 + extension) |
| F12 | Correct behavior after repeated logical pointer wrap / full-depth fill-drain rounds | §Behavior 6; §Corner cases | H | Multi-revolution unique patterns and queue checks (HW4 + CRV) |
| F13 | WIDTH/DEPTH parameterization retains specified behavior for selected supported configurations | §Parameters; §Ports; §Behavior 1–6 | M | Reconfigure and rerun spec-independent tests (new; do not claim until run) |
| F14 | A control combination not explicitly specified during reset is recorded and safely analyzed | §Behavior 1 vs. no stated reset/input precedence | H | Observable `rst_n=0 && wr_en=1` coverpoint; check reset outputs only, log unspecified input effect (new) |

**Scope boundary:** No test ID or coverage credit is assigned to nonexistent `almost_full` or non-FWFT controls. The spec lists WIDTH and DEPTH but does not state the admissible minimum or maximum values; proposed extra configurations require a separate, documented simulator run.

## 3. Coverage model

**Sampling, collection, and denominator.** Use `cocotb-coverage` for functional coverpoints/crosses; use `pyvsc` for a seeded transaction class. At each nonreset clock edge record pre-edge model occupancy, control requests, and predicted accepted operations; after the edge record post-edge outputs and check them against `FifoModel`. Sample reset cases separately. All specified requests are legal: **attempted writes at full, reads at empty, and both enables at either boundary are defined behavior**, not forbidden transactions. Track raw hit counts and compute percent as `hit reachable bins / total reachable bins` **for the selected parameter configuration**; print unhit bins and never count a bin solely because stimulus was attempted when no check was made.

**Baseline bins for WIDTH=8, DEPTH=8:**

| ID | Coverpoint | Bins | Reason / bug class |
|---|---|---|---|
| C01 | **Pre-edge occupancy** | `empty=0`, `one=1`, `middle=2..6`, `near_full=7`, `full=8` | Boundary off-by-one, access gating, and state pressure |
| C02 | **Requested operation** (`wr_en`, `rd_en`) | `idle=00`, `read=01`, `write=10`, `both=11` | Distinguish requested commands from accepted transfers |
| C03 | **Accepted operation** (model-predicted) | `none`, `read_only`, `write_only`, `both` | Expose overflow/underflow suppression and overlap acceptance |
| C04 | **Important occupancy transitions** | `0→1`, `1→0`, `7→8`, `8→7`, `hold_empty`, `hold_full`, `hold_interior` | Boundary timing, dropped operations, and count stability |
| C05 | **Post-edge flag state** | `empty`, `interior`, `full` | Observe both assertion and deassertion of each flag |
| C06 | **FWFT head event** | `first_write_from_empty`, `read_reveals_next`, `simultaneous_replaces_one_entry`, `idle_head_stable`, `head_after_wrap` | Head selection, stale data, and read/write pointer mistakes |
| C07 | **Write data pattern** | `all_zero`, `all_one`, `alternating_55_or_AA`, `other` | Stuck bits, corruption, aliasing, and accidental equality |
| C08 | **Consecutive request burst length** (track read/write separately) | `single`, `short=2..7`, `long>=8` | Uninterrupted reads/writes and long pointer histories |
| C09 | **Reset scenario** | `initial_reset`, `reset_when_nonempty`, `post_reset_first_write` | Reset state, stale-head/pointer recovery |
| C10 | **Independent logical wrap event** | `no_wrap`, `write_wrap`, `read_wrap`, `both_wrapped` | Detect depth/modulo mistakes; use scoreboard's transaction indices, **not** RTL internals |
| C11 | **Undefined/underspecified control overlap** | `reset_only`, `reset_plus_write` | Meets security/trust requirement: reset coincident with write; observe/reset-check but do not invent unspecified behavior |
| C12 | **Selected parameter configuration** | `8x8_baseline`; additional `WIDTHxDEPTH` bins **only if actually run** | Track configuration-specific reachability without inflating baseline percentage |

**Crosses (only reachable target combinations count):**

| ID | Cross | Target set / why it matters |
|---|---|---|
| X01 | C01 pre-edge occupancy × C02 requested operation | **All 5 × 4 = 20 baseline combinations** are reachable; especially `both@empty`, `both@full`, `write@full`, `read@empty` |
| X02 | C01 pre-edge occupancy × C03 accepted operation | **16 reachable baseline combinations:** 2 for empty (`none`,`write`), 4 for each of 1/middle/7, 2 for full (`none`,`read`); catches misgating |
| X03 | C04 important transition × C05 post-edge flag state | Score only the expected pair for each transition: `0→1:interior`, `1→0:empty`, `7→8:full`, `8→7:interior`, and respective `hold_*` cases; catches flag/count latency |
| X04 | C01 occupancy × C06 FWFT head event | Explicitly target `empty×first_write`, `one×simultaneous_replaces_one_entry`, `interior×read_reveals_next`, and `interior/near_full×head_after_wrap`; catches head selection under pressure |
| X05 | C09 reset scenario × first subsequent accepted operation | `initial_reset→write`, `reset_when_nonempty→write`, `post_reset_first_write` witness; guards against stale state after reset |

**Illegal / ignore bins and specification authority.** The written spec defines **no prohibited `wr_en`/`rd_en` combinations** in normal operation. Therefore do **not** declare full writes, empty reads, or boundary `both` requests illegal or exclude them from request coverage. States with `count<0`, `count>DEPTH`, `full && empty` for DEPTH>0, or flags inconsistent with count are **failures to assert/check**, not bins to excuse from coverage. Ignore comparison of `rd_data` when `empty=1` because its valid-data contract is limited to `!empty` (**§Ports; §Behavior 3**). Reset with a write request is covered as an underspecified control overlap: assert the *specified* reset count/flags but do not assume the spec defines write acceptance on that edge. For other depths, regenerate occupancy/transition bins; do not demand a nonexistent middle range for very small DEPTH.

**CRV strategy and convergence evidence.** Define a pyvsc transaction with `wr_en`, `rd_en`, and WIDTH-bit `wr_data`; constrain bit widths, and bias the **sequence according to model occupancy** rather than treating transactions independently. Initial proposed phases: write-heavy to reach near-full/full, read-heavy to reach near-empty/empty, overlap-heavy to maintain active occupancy, and balanced traffic for interleavings. Retain legal boundary requests because the spec defines their ignored/dropped outcomes. Use saved seeds (initial proposal `0x4701`–`0x4705`; Project 1 pyvsc seeds are **not yet run**), monitor empirical probabilities by phase, and add directed closure only when a corner cannot reasonably be reached by tuned constraints. For each run, record before/after hit counts, uncovered bins/crosses, changed weights/constraints, observed stimulus distribution, and which mutants new coverage detects. Sample all monitored cycles including post-random drain; label directed-only closure honestly. Target **100% reachable mandatory baseline bins and crosses** with no undiagnosed holes.

## 4. Test matrix

Every feature in §2 maps to a test below. Existing HW4 names refer to the source supplied in `HW4.zip`, **not** new Project 1 passes. Each test must fail on scoreboard discrepancies and record seed/command/configuration.

| Test | Mapped features | Kind / implementation | Pass criterion |
|---|---|---|---|
| T01 `test_fifo_directed_corners` | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 | Directed — **reuse HW4** | Drops full writes, ignores empty reads, handles boundary and interior both; all count/flag/valid-head checks pass |
| T02 `test_fifo_pointer_wrap_and_reset` | F01, F06, F07, F08, F11, F12 | Directed — **reuse HW4** | Repeated wraps and nonempty reset preserve ordered output and restore empty state |
| T03 `test_fifo_seeded_random_interleave` | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11, F12 | Python pseudo-random — **HW4 baseline only** | Old 1,200-cycle sequence (seed `0x4701`) passes and final drain exposes no stale/corrupted entries; **does not satisfy pyvsc requirement** |
| T04 pyvsc transaction legality and seed test | F02, F03, F04, F05, F09, F10 | CRV — **new** | Reproducible transaction generation; all control requests are within spec and data in `0..2^WIDTH-1`; observed distribution reported |
| T05 occupancy-weighted boundary regression | F02, F03, F04, F05, F06, F09, F10, F11 | Seeded CRV — **new** | All X01/X02 reachable occupancy/operation combinations hit and checked, including boundary overlap |
| T06 sustained simultaneous traffic and head updates | F06, F07, F08, F09, F12 | Seeded CRV — **new** | Both accepted at occupancy 1/interior/7, count holds, head and ordering correct over long bursts |
| T07 data integrity and wrap stress | F02, F04, F07, F08, F12 | CRV + directed — **new/extend** | Edge/alternating/distinct data survive full FIFO fills, drains, and repeated wraps |
| T08 reset timing/recovery/underspecified overlap | F01, F06, F07, F14 | Directed + assertion/cover — **new/extend** | Observe reset on a rising edge, nonempty reset and postreset restart; record `rst_n=0 && wr_en=1` hit; assert only specified reset results |
| T09 idle, FWFT, and flag-transition coverage | F06, F07, F08, F11 | Directed/coverage — **new** | Witness all specified C04/C05 transitions and key C06 head events without unverified head checks at empty |
| T10 additional parameter configurations | F02, F04, F06, F07, F08, F12, F13 | Parameter regression — **planned** | If runner supports it, e.g. `WIDTH=16,DEPTH=5` and/or `WIDTH=8,DEPTH=4`; rerun with parameterized scoreboard and separate coverage/report; do not claim runs in advance |
| T11 released mutation-quality run | All applicable F01–F14 | Mutation — **new Project 1 measurement** | Clean DUT passes, released found/total recorded with current commit and command, causes of surviving mutants analyzed honestly |
| T12 coverpoint/cross convergence regression | All applicable F01–F14 | Coverage closure — **new** | 100% reachable mandatory baseline target hit and checked; each initial hole has a recorded closure action and evidence |

**Reproducible known HW4 commands (reconfirm with current course runner):**

```bash
cd ~/craft-vv-student/code
source /opt/course/cocotb-env/bin/activate
just test fifo icarus
just mutate fifo
```

The HW4 report indicates the default Verilator invocation stopped on an existing width warning, while the **explicit Icarus** invocation passed. Use the actual Project 1 runner and saved parameters when generating new evidence; do **not** substitute HW4 scores for the new Project 1 results.

## 5. Risk and spec ambiguity

| # | Ambiguity or risk | Where in source | Resolution / residual risk |
|---|---|---|---|
| R01 | **Handout/interface mismatch:** handout mentions `almost_full` and optional FWFT, but supplied FIFO exposes neither | Project 1 handout, DUT `fifo.sv` module ports and parameters, `dut/specs/fifo.md` | **Resolved for this DUT:** verify fixed FWFT only; `almost_full` and non-FWFT excluded. Ask instructor if a *different* Project 1 DUT is expected |
| R02 | Reset precedence for `wr_en`/`rd_en` asserted during `rst_n=0` is not specified beyond reset outputs | Spec §Behavior 1 vs §Behavior 2–3 | Test/cover the overlap for trust purposes; assert count/flags on reset edge; document write/read acceptance as undefined pending clarification |
| R03 | WIDTH/DEPTH bounds are not documented; narrow DEPTH could expose zero-width pointer declarations | Spec §Parameters; DUT uses `$clog2(DEPTH)` | Run default 8×8 first; choose supported extra values (prefer DEPTH≥2, nonpower-of-two DEPTH=5 if allowed), then report exact configurations. **Do not assume DEPTH=1 is supported** |
| R04 | Existing bench constants and model instantiation are hardcoded 8×8 | HW4 `test_fifo.py` (`WIDTH`, `DEPTH`, `FifoScoreboard`) | Refactor before T10; all bins and scoreboard sizes must follow the actual simulator parameter override |
| R05 | HW4 randomized traffic uses `random.Random` rather than pyvsc; no functional coverage closure report exists | HW4 `test_fifo.py` | Add real pyvsc generator, cocotb-coverage, saved seeds, empirical distribution, and convergence logs |
| R06 | Existing scoreboard may miss bugs that require different sampling moments or observing unexposed internals | HW4 monitor samples rising edge+1 ns; spec only defines valid head | Explicitly document sampling; maintain expected observable outputs per edge; avoid claims of glitch/internal verification |
| R07 | HW4 **final** released-pool mutation results have **zero survivors**, while Project 1 requests analysis of at least two survivors | HW4 `FINDINGS.md` vs Project 1 §Tasks 5 | Rerun current Project 1 pool; honestly report actual final survivors. If still 0, analyze **two historical starter-suite survivors** with before/after evidence (e.g. `rd_data_wrptr`, `wrptr_wrap_early`) and label them **formerly surviving**, not final surviving; confirm this treatment with instructor if needed |
| R08 | Default Verilator path previously failed to compile due to width warning; Icarus path passed | HW4 `FINDINGS.md` | Save simulator choice/version and exact invocation; fix environment/build problems separately from actual functional verification failures |
| R09 | Randomization may neglect rare occupancy transitions or correlated bursts despite many total cycles | Project 1 §Tasks 3–4 | Coverage-guided weights, seeded phases, focused crosses, reported holes and empirical distribution; directed-only bins separately identified |
| R10 | Team merges or stale test logs might make evidence irreproducible | GitHub team workflow | Single approved integration branch, all teammates commit, peer-review behavior changes, save SHA+seed+simulator+commands and write `CONTRIBUTIONS.md` |

**Mutation-analysis plan.** Keep baseline and mutation results distinct. The uploaded HW4 `FINDINGS.md` reports a weak *starter suite* at **1/8**, leaving seven mutants, and a stronger final HW4 suite at **8/8**, leaving none. Historical examples: `rd_data_wrptr` needs a valid FWFT head comparison with distinct values, and `wrptr_wrap_early` needs multi-round wraparound and ordering checks. These **were detected** by the finished HW4 suite. Project 1 should save a genuine current initial-vs-improved comparison and analyze at least two actually observed survivors from a weaker/initial run, or disclose that the final regression has no survivors. Never fabricate survivor names, results, or new mutation scores.

## 6. Closure criteria

- **Functional coverage:** Reach **100% of reachable, applicable mandatory baseline coverpoint and cross bins** defined in §3 for `WIDTH=8`, `DEPTH=8`, with hit counts and each coverage hole/closure action reported. Excluded/unreachable combinations require a spec or logical justification. Optional configuration bins count only after execution and are reported separately.
- **Scoreboard and correctness:** Every nonreset transaction is checked against spec-derived `FifoModel` behavior for occupancy/flags and valid FWFT head; reset count/flags checked after the reset clock edge; queue ordering and all acceptance rules checked. All baseline and added tests must pass locally.
- **Mutation quality:** Team goal **≥90%** detection (`found/total`) on the currently released pool. The Project 1 grading contract awards full mutation-quality credit at 90% on the *hidden* pool, whose outcome is not available before grading. Preserve raw mutant statuses, exact commands, and a frank analysis of **at least two documented initial/current survivors**; if final released survivors are zero, state so.
- **CRV legality and reproducibility:** The suite uses `pyvsc` (not only Python's `random`), logs the constraints, predicted/observed generation distribution, seeds, simulator, parameter settings, commit hash, and any hole-closing adjustments. Same commit/seed/commands reproduce test and coverage results.
- **Security/trust check:** At least one observable, exercised `reset_plus_write` coverpoint or equivalent control-corner assertion; distinguish the specified reset output guarantees from unspecified simultaneous command acceptance. No vacuous assertion claims.
- **Report and artifacts:** Team repository contains `vplan.md`; layered `tb/` (driver, monitor, reference-queue scoreboard); `crv/` (pyvsc transactions/constraints/seeded regression); functional coverage model **and measured report**; `FINDINGS.md` (found/total, survivors, limitations); `REPORT.pdf` (4–6 pages); demo link; `CONTRIBUTIONS.md` (every teammate's actual work/commits); and `ai_log.md`. Required checks green locally before submitting via Webcourses.
- **Check the Machine / AI evaluation:** `ai_log.md` records an AI prompt for coverage or constraints, **a prediction written before execution** about missing cross/illegal behavior/distribution, the actual measured evidence, and every correction. A generated vplan alone does not fulfill this requirement.
- **Honest residuals:** The report explicitly lists unrun parameter choices, unclosed bins, surviving mutants, any specification uncertainties, and unsupported features (`almost_full`, non-FWFT). No historical HW4 result or projected percentage is presented as a new Project 1 measurement.

**Team review gate:** [ ] all team members reviewed this vplan  [ ] test IDs linked to assigned owners  [ ] parameter regression feasibility checked on Eustis  [ ] pyvsc and coverage installed  [ ] first coverage/mutation baseline captured.
