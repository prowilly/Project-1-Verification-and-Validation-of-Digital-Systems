# Verification plan — Project 1 synchronous FWFT FIFO

**Course:** EEE 4701, Verification and Validation of Digital Systems, UCF, Fall 2026.\
**Revision:** 2, November 13, 2026.\
**Behavioral authority:** [`dut/specs/fifo.md`](dut/specs/fifo.md).\
**Execution evidence:** [`evidence/current/`](evidence/current/) and [`FINDINGS.md`](FINDINGS.md).

## 1. Scope and protocol

Verify the supplied synchronous, first-word-fall-through FIFO through its public ports. The primary configuration is WIDTH=8, DEPTH=8. Supplemental CRV configurations are WIDTH=16, DEPTH=5 (non-power-of-two depth) and WIDTH=8, DEPTH=4. Each has its own elaboration, reference queue and coverage report. The current coverage partition supports WIDTH>=3 and DEPTH>=4; other configurations are not claimed verified.

- Reset is active-low and synchronous. Count/flags change on the rising edge, not when reset is asserted between edges.
- A write is accepted iff `wr_en && !full` in the pre-edge state; a full write request is dropped.
- A read is accepted iff `rd_en && !empty` in the pre-edge state; an empty read request is ignored.
- All four enable combinations are legal requests. At empty, simultaneous requests accept only the write; at full, they accept only the read; in the interior, both are accepted.
- Count, full and empty are checked every sampled cycle. `rd_data` is checked against the oldest queued word whenever the expected FIFO is nonempty. Empty-state data is unspecified and is not compared.
- The supplied interface has no `almost_full` port and no non-FWFT mode. These features, CDC/asynchronous FIFOs, internal-memory implementation, formal proof, synthesis and timing closure are outside this design's verification scope.

The driver applies requests on falling edges of a 10 ns clock. The CRV checks the unchanged state 1 ns later, predicts accepted transfers from the pre-edge queue, and checks settled outputs 1 ns after the rising edge. Reset tests also verify no asynchronous reset effect. Functional coverage is sampled only after the relevant scoreboard check passes.

## 2. Requirements and test traceability

H means required in the baseline. M means supplemental parameter coverage.

| ID | Requirement and specification reference | Priority | Tests/checks |
|---|---|---|---|
| F01 | Synchronous reset and recovery; Ports/reset, Behavior 1 | H | T02, T05; pre/post-reset checks; C09, X05 |
| F02 | Accepted write stores data and increments count; Behavior 2, 6 | H | T01, T03, T06; queue scoreboard |
| F03 | Full write request is dropped; Behavior 2 | H | T01, T03, T06; X01/X02 full boundary |
| F04 | Accepted read removes oldest entry; Behavior 3, 6 | H | T01-T03, T06; valid-head comparison |
| F05 | Empty read request is ignored; Behavior 3 | H | T01, T03, T06; X01/X02 empty boundary |
| F06 | Flags and count agree with occupancy; Ports, Behavior 5 | H | Every checked cycle; T04; C04/C05, X03 |
| F07 | Valid FWFT head follows current oldest value; Ports, Behavior 3 | H | T01-T06; C06, X04 |
| F08 | Data integrity and FIFO ordering; Behavior 6 | H | All queue checks, patterned data, final drain |
| F09 | Interior simultaneous transfers hold occupancy; Behavior 4 | H | T01, T02, T03, T06; C03 and X01/X02 |
| F10 | Boundary simultaneous requests accept only available operation; Behavior 2-3, Corners | H | T01, T06; X01/X02 |
| F11 | Idle count, flags and valid head remain stable; Behavior 2-5 | H | T04, T06; C04/C06 |
| F12 | Ordering remains correct through repeated wraps; Behavior 6, Corners | H | T02, T06; C10 and X04 |
| F13 | Selected WIDTH/DEPTH configurations preserve behavior; Parameters | M | T07, separate configuration evidence |
| F14 | Reset overlapping a write is observed and reset outputs checked; Behavior 1 | H | T05, T06; C11; no unsupported claim about accepted reset-time transfers |

| Test ID | Executable test or command | Pass condition |
|---|---|---|
| T01 | `tb/test_fifo.py::test_fifo_directed_corners` | Full/empty rejection, boundary/interior overlap and ordering pass |
| T02 | `test_fifo_pointer_wrap_and_reset` | Repeated wraps, nonempty reset and recovery pass |
| T03 | `test_fifo_seeded_random_interleave` | 1,200 cycles using Python seed `0x4701` and final drain pass; supplemental to pyvsc |
| T04 | `test_fifo_idle_hold_and_flag_transitions` | Idle holds and 0→1, 1→0, 7→8, 8→7 transitions pass |
| T05 | `test_fifo_synchronous_reset_with_requests` | Reset timing, asserted enables, and restart pass |
| T06 | `crv/test_fifo.py::test_crv_seeded_regression` | pyvsc seeds 4701, 17, 4702; 5,000 cycles each; scoreboard, corner self-checks and coverage closure pass |
| T07 | Same CRV with 16x5 and 8x4 parameters | Separate elaboration and 108-bin model close; scoreboard passes |
| T08 | `python scripts/run_verification.py --suite mutations` | Passing clean controls; final baseline and CRV each detect all 8 released mutants; controlled restricted experiment has exactly the two predicted survivors |
| T09 | `python scripts/run_verification.py --suite experiments` | Save measured 1/500 vs 1/200 reset-weight coverage checkpoints; no assumed improvement |
| T10 | Unit checks and repeated seed 4701 in the regression runner | Correct temporal sampling and JUnit failure detection; identical full coverage JSON and stimulus hash on replay |

## 3. Functional coverage model

The model is [`coverage/fifo_coverage.py`](coverage/fifo_coverage.py). Every selected configuration has **108 required bins**, with target 108/108. A bin receives credit only after its associated observation has passed the scoreboard. The initial reset is sampled at cycle 0; subsequent random/reset edges and the final drain are sampled. The random-only snapshot is preserved separately from the deterministic drain.

| ID | Coverpoint | Bins |
|---|---|---|
| C01 | Pre-edge occupancy | empty=0, one=1, middle=2..DEPTH-2, near_full=DEPTH-1, full=DEPTH |
| C02 | Requested operation | idle, read, write, both |
| C03 | Predicted accepted operation | none, read_only, write_only, both |
| C04 | Key occupancy transition | empty_to_one, one_to_empty, near_full_to_full, full_to_near_full, hold_empty, hold_full, hold_interior |
| C05 | Observed post-edge flags | empty, interior, full |
| C06 | Checked head event | first_write_from_empty, read_reveals_next, simultaneous_replaces_one_entry, idle_head_stable, head_after_wrap |
| C07 | Accepted write pattern | all_zero, all_one, alternating, other |
| C08 | Consecutive requested write/read burst, separately | single=1, short=2..DEPTH-1, long>=DEPTH |
| C09 | Reset/recovery scenario | initial_reset, reset_when_nonempty, post_reset_first_write |
| C10 | Logical pointer event/milestone | no_wrap, write_wrap, read_wrap, both_wrapped |
| C11 | Reset/control overlap | reset_only, reset_plus_write |
| C12 | Selected elaboration configuration | one bin for the actual WIDTHxDEPTH of this process |

`read_reveals_next` requires a pre-edge count of at least two and an accepted read. `head_after_wrap` requires an accepted read that completes a logical read-index revolution and a nonempty post-state; the resulting head has already been checked. The logical indices restart on reset. **`both_wrapped` means both indices have completed at least one revolution since the last reset, possibly on different edges.** It does not mean they wrap simultaneously, which is unreachable for accepted operations in this FIFO. Its first occurrence per reset epoch is sampled. `no_wrap` means neither index wraps on this transaction.

Two additional `recovery_origin` bins identify initial versus nonempty reset for X05. Combined counts: 50 coverpoint bins and 58 cross bins = 108.

| ID | Cross | Reachable bins and exclusions |
|---|---|---|
| X01 | Occupancy × requested operation | All 5×4=20 combinations; boundary requests remain included |
| X02 | Occupancy × accepted operation | 16 combinations; ignore empty×read_only/both and full×write_only/both because the spec prevents them |
| X03 | Key transition × observed post-state flags | 7 combinations; each transition has exactly one valid flag state |
| X04 | Occupancy × checked head event | 13 combinations: first write only at empty; replacement only at one; reveal-next at middle/near-full/full; idle-head and head-after-wrap at any nonempty occupancy |
| X05 | Reset origin × first subsequent accepted operation | 2 combinations: each reset origin followed by write_only; an empty reset queue cannot accept a read before its first write |

No normal request combination is illegal. Count outside 0..DEPTH, inconsistent flags, unresolved required values and incorrect valid-head data are assertion failures, not ignored bins. Reset-plus-write meets the control-corner requirement while asserting only the specified reset state. The absence of an empty-state data promise is not used to excuse errors when the FIFO should be nonempty.

## 4. Constraints, distribution and convergence

The transaction keeps live pre-edge occupancy and fill/drain phase as nonrandom state. Before each solve, that state selects nonrandom write/read weight values used by one unconditional distribution constraint per enable. Each enable is one bit, data is WIDTH bits, and all specified boundary requests remain enabled in normal mode. Default request weights are:

| Rule | Condition, in precedence order | P(write request) | P(read request) |
|---|---|---:|---:|
| near_empty | count<=1 | 0.70 | 0.60 |
| near_full | count>=DEPTH-1 | 0.60 | 0.70 |
| fill | interior and fill phase | 0.90 | 0.30 |
| drain | interior and drain phase | 0.30 | 0.90 |

These are configured marginal weights, not a promise of exact finite-sample proportions. Normal signoff requires at least 100 observations per rule and checks each observed request rate within six binomial standard errors plus two percentage points of its target; the data-category rates are checked the same way. This is a regression diagnostic, not a proof of solver uniformity. The phase reverses at a reached full/empty boundary. A nonempty reset can also end a drain phase, so `drains` is a phase-completion count, not a claim that every phase removed every word by reading.

Data categories are selected with weights 1:1:1:1:6 for zero, all-one, alternating A, alternating B, and other. Thus their expected request frequencies are 10%, 10%, 10%, 10%, and 60%; C07 combines the two alternating categories. Other values exclude all four named constants. This explicit selection keeps alternating patterns reachable at WIDTH=16. Accepted-write frequencies can differ from generated-request frequencies.

Reset has probability 0 at empty and configured weight 1/200 when nonempty. The convergence experiment compares 1/500 with 1/200 using the same seed and cycle budget. The report stores first-hit cycles, every 100-cycle checkpoint, all remaining holes, per-rule request counts, pattern counts and reset-eligible cycles. [`coverage/README.md`](coverage/README.md) explains the measured outcome. No result from a different source version substitutes for current evidence.

The `restricted` mode deliberately forbids empty reads and full writes for the two-survivor experiment. It is explicitly diagnostic, requires closure checking to be disabled, and is never used for normal signoff.

## 5. Reproducibility and acceptance

Run `python scripts/run_verification.py --output evidence/generated`. It checks the five-test baseline, three CRV seeds, exact same-seed replay, two supplemental configurations, sampler/result-parser unit checks, convergence experiments and released mutation controls. It reads JUnit results instead of assuming a zero `make` exit means passing tests. Each case uses a fresh build and separate results/coverage files. Missing results, skips, infrastructure errors, functional failures, incomplete normal coverage and unexpected survivors make the runner exit nonzero.

Each manifest records exact commands, environment versions, the starting commit and SHA-256 hashes of the actual verification source files. The code hash identifies the tested source even when evidence is generated before the final documentation commit. Compare manifests before comparing scores.

## 6. Residual risk and submission boundary

The hidden pool is unavailable; an 8/8 released score does not establish its outcome. Finite seeded tests cannot prove every data history or parameter choice. Outputs are checked at specified sampling points; subcycle glitches are not exhaustively monitored. Undefined empty-state data and unspecified transfer acceptance on reset remain outside asserted semantics.

The repository work includes current findings, contributions, AI evaluation, coverage evidence and reproducible commands. The team report PDF and demo link are separate deliverables that the owner is completing; the README tracks them explicitly. Team members should understand and defend the recorded evidence; no human-review attestation is inferred from an automated run.
