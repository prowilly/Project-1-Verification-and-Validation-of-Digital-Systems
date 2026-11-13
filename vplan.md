# Verification plan — synchronous FWFT FIFO

**Course:** EEE 4701 — Verification and Validation of Digital Systems\
**Team:** William Garland, Banmeet Singh, Daniel Jo\
**Revision:** November 13, 2026\
**Contract:** [`dut/specs/fifo.md`](dut/specs/fifo.md)\
**Implementation and evidence:** [`FINDINGS.md`](FINDINGS.md), [`evidence/current/`](evidence/current/)

## Scope

Verify the supplied synchronous first-word-fall-through FIFO through its public pins. Default configuration is WIDTH=8, DEPTH=8. Additional measured configurations are listed separately in the regression summary. The reference queue derives expected behavior from the written specification, independently of RTL pointers and memory.

Drive inputs at falling edges of a 10 ns clock; predict acceptance from pre-rising-edge occupancy; observe outputs 1 ns after rising edges. CRV also checks the public interface before the active edge. The reset check asserts reset between edges, verifies that state has not changed early, then checks count=0, empty=1 and full=0 after the resetting edge. Empty-state data is unspecified and is not compared.

Out of scope: This plan does not verify asynchronous clock-domain crossings, synthesis, timing closure, power, internal RTL implementation coverage, or exhaustive correctness over every possible history. It does not verify unspecified empty-state data or reset-time transfer acceptance beyond the specified reset outputs. The supplied interface has no `almost_full` port or switch to disable FWFT, so this plan does not cover either feature. DEPTH=1 and unrun width/depth settings are not verified.

## Feature list

H = required functional behavior; M = supplemental parameter testing. Every test listed below runs the reference-queue scoreboard.

| ID | Feature | Spec requirement | Priority | Test or check |
|---|---|---|---|---|
| F01 | Synchronous reset and recovery | Behavior 1 | H | `test_fifo_pointer_wrap_and_reset`, `test_fifo_synchronous_reset_with_requests`, CRV reset cycles |
| F02 | Accepted write stores data and increments count | Behavior 2, 6 | H | `test_fifo_directed_corners`, CRV |
| F03 | Full write is dropped without corruption | Behavior 2; Corner cases | H | Directed overflow requests followed by drain; CRV full requests |
| F04 | Accepted read removes the oldest entry | Behavior 3, 6 | H | Directed fill/drain, CRV, per-cycle head comparison |
| F05 | Empty read is ignored | Behavior 3; Corner cases | H | Directed underflow and recovery; CRV empty requests |
| F06 | Count bounds and correct full/empty flags | Ports; Behavior 5 | H | Scoreboard on every checked observation |
| F07 | Current head is valid whenever nonempty | Ports; Behavior 3 | H | Valid-head comparison; first write and simultaneous replacement at occupancy one |
| F08 | Data integrity and FIFO ordering | Behavior 6 | H | Distinct patterns, seeded traffic, full final drain |
| F09 | Interior simultaneous transfers preserve count | Behavior 4 | H | Directed overlap and CRV `both` requests |
| F10 | Empty/full simultaneous request semantics | Behavior 2–3; Corner cases | H | At empty accept write only; at full accept read only |
| F11 | Idle preserves occupancy and valid head | Behavior 2–5 | H | `test_fifo_idle_hold_and_flag_transitions` |
| F12 | Pointer wrap preserves ordering | Corner cases; Behavior 6 | H | `test_fifo_pointer_wrap_and_reset`, sustained CRV fill/drain |
| F13 | Other width/depth settings | Parameters | M | CRV 16×5 and 8×4 with matching RTL and model settings |
| F14 | Reset with asserted controls | Behavior 1; security/trust task | H | `test_fifo_synchronous_reset_with_requests`, `fifo.reset` bins |

## Functional coverage model

The implemented model is Banmeet's unchanged [`coverage/fifo_coverage.py`](coverage/fifo_coverage.py). Target: **70/70 reachable bins** per required default regression. Coverage records stimulus/state; the scoreboard separately determines correctness. No coverage miss alone counts as a mutation detection.

| Coverage item | Bins | Count |
|---|---|---:|
| `fifo.occupancy` | empty, one, middle, near_full, full | 5 |
| `fifo.request` | idle, read, write, both | 4 |
| `fifo.accepted` | none, read_only, write_only, both | 4 |
| `fifo.transition` | empty→one, one→empty, near_full→full, full→near_full, hold_empty, hold_full, hold_interior | 7 |
| `fifo.occ_x_request` | All occupancy × request combinations | 20 |
| `fifo.occ_x_accepted` | Occupancy × accepted operation; four impossible combinations ignored | 16 |
| `fifo.write_data` | all_zero, all_one, alternating, other | 4 |
| `fifo.write_burst` | single, short (2–7), long (≥8) requests | 3 |
| `fifo.read_burst` | single, short (2–7), long (≥8) requests | 3 |
| `fifo.pointer_wrap` | write_wrap, read_wrap inferred from accepted transfer counts | 2 |
| `fifo.reset` | reset_no_request, reset_plus_write | 2 |
| **Total** | | **70** |

Cross ignore bins are `empty×read_only`, `empty×both`, `full×write_only`, and `full×both` for **accepted** operations. They are impossible under the contract. All four **requested** operations remain legal at every occupancy: full writes are dropped and empty reads are ignored. Never exclude these requests from coverage.

Count outside 0..DEPTH, inconsistent flags and a mismatched valid head fail assertions. Flags, head transitions and reset recovery are checked by directed tests and the scoreboard; they are **not extra coverpoints/crosses in this 70-bin model**. This revision replaces the earlier plan's unimplemented C05/C06/C09 and X03–X05 coverage commitments with the actual assertion/test mapping above. It does not claim the removed proposals were measured or that 70 bins exhaust every useful scenario.

Coverage uses pre-edge occupancy and post-edge transition state. Burst bins describe request runs, not necessarily accepted-transfer runs. Pointer wrap is inferred from reference acceptance counts; no RTL internals are inspected. CRV coverage excludes the initial three reset cycles and final drain. First-hit tracking is quantized to ten sampled cycles; report-time burst flushing can add a bin after the last tracking interval, so `closed_at=None` does not alone imply final coverage is incomplete.

## Constrained stimulus and distribution

The unchanged `FifoTxn` in `crv/test_fifo.py` uses pyvsc bit fields for controls and WIDTH-bit write data. Occupancy and fill/drain phase are nonrandom state, refreshed from the scoreboard. All request combinations are contract-legal. A fill phase becomes drain at full; a drain phase becomes fill at empty.

| State/phase | Declared P(write) | Declared P(read) |
|---|---:|---:|
| Occupancy ≤1 | 70% | 60% |
| Occupancy ≥DEPTH−1 | 60% | 70% |
| Interior, fill phase | 90% | 30% |
| Interior, drain phase | 30% | 90% |

The data constraint gives weight 1 each to zero and all-ones, and weight 6 to the interior range. The reset constraint declares no reset at empty and weight 1:199 for reset:no-reset when nonempty. These are **declared solver weights**, not proof of observed probabilities. The passive monitor trace measures actual transactions; `stimulus.json` stores counts by state/phase and a SHA-256 of the generated sequence. Findings distinguish measured behavior from the declarations.

The convergence experiment uses the existing `STIM` switch and run length: unchanged biased stimulus at 3,000 and 5,000 cycles, plus the existing uniform mode at 5,000. Uniform disables boundary/data constraints but retains the reset constraint. No constraints are rewritten, and no directed coverage fill is injected. Record holes, first-hit observations and final bins; retain measured closure limitations rather than invent tuning results.

## Test matrix

The upload contains one cocotb test module, `test_fifo.py`, copied unchanged from `crv/test_fifo.py`. Its test function is `test_crv_seeded_regression`. The five directed baseline tests remain in the repository for supplementary evidence; they are not a second uploaded test module.

| Test | Features / requirements | Configuration | Checks and pass criterion |
|---|---|---|---|
| test_crv_seeded_regression | F01–F12, F14; spec Behavior 1–6 and Corner cases | WIDTH=8, DEPTH=8; seed 4701; 5,000 cycles | Reset/recovery, queue ordering, valid head, count/flags, full/empty requests, overlap, wraps; one test passes and all 70 coverage bins hit |
| test_crv_seeded_regression | F01–F12, F14; same contract | Seeds 17 and 4702; 5,000 cycles each | Same checks and full baseline coverage for each seed |
| test_crv_seeded_regression | Reproducibility | Repeat seed 4701 with identical tools/settings | Identical stimulus hash and complete coverage report |
| test_crv_seeded_regression | F13; Parameters and Behavior 1–6 | WIDTH=16 DEPTH=5; WIDTH=8 DEPTH=4 | Correct model/RTL parameter match; functional checks pass; supplemental coverage holes reported separately |
| test_crv_seeded_regression | All applicable features; mutation sensitivity | Clean control plus eight released mutants, individually | Clean control passes; record found/total from assertion failures; build errors do not count as detections |

The submitted directory runs with `make SIM=icarus SEED=4701 N_CYCLES=5000`. Its Makefile exposes `DUT` for the released/hidden mutant harness. See `submission/README.md` for ZIP contents and reproduction steps. In the full repository, the runner below additionally executes the five directed baseline tests and convergence experiments.

Run `python scripts/run_verification.py --output evidence/generated` from the repository root after installing `requirements.txt` and Icarus Verilog. The runner copies source files into a temporary directory for each run. It records Python/dependency/simulator versions, source hashes, seed, commands, XML outcomes, actual stimulus and coverage. It rejects missing/empty XML, skips, infrastructure errors, failed clean controls and incomplete required coverage. Mutation failures must contain assertion diagnostics.

## Risk and spec ambiguity

- **Distribution versus declared weights:** pyvsc implementation details can change the induced distribution. Measure it, disclose discrepancies, and retain teammate ownership of constraint changes.
- **Finite model:** 70/70 describes the implemented bins, not exhaustive behavioral proof; some planned observations remain assertion-only. Small depths need new occupancy partitions; DEPTH=1 is not claimed supported.
- **Observation window:** checks do not prove absence of all subcycle glitches. Reset-time transfer acceptance beyond the specified reset outputs and empty-state data remain unspecified.
- **Mutation limits:** released-pool results do not predict hidden-pool scores. If the final released run has zero survivors, analyze the two documented historical survivors in Daniel's `ai_log.md` and label them historical.
- **Evidence provenance:** old HW4 logs, Daniel's original Check the Machine run and fresh `evidence/current/` results are separate records. Do not present one as the other's rerun.
- **Team ownership:** preserve `crv/`, `coverage/`, and `ai_log.md`. New evidence belongs outside those paths. Any future behavioral changes in those files require coordination with their authors.

## Closure criteria

Repository closure requires passing baseline/CRV, 70-bin closure, reproducible replay, current released-mutation evidence, an honest two-survivor analysis, this traceability plan, a contributions record and the original Check the Machine log. The uploaded `REPORT.pdf` and demo link are included; their presence is separate from functional verification results. Automated checks do not attest teammate review or guarantee a course grade.
