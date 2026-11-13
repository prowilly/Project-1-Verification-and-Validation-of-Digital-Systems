# Project 1 findings — synchronous FIFO

**Course:** EEE 4701 — Verification and Validation of Digital Systems\
**Team:** William Garland, Banmeet Singh, Daniel Jo\
**Updated:** November 13, 2026

## Score

**Found/total: 8/8 (100%).**

The submitted constrained-random suite detects eight of the eight released mutants. There are zero current released-pool survivors. The hidden grading pool has not been run. The separate five-test directed baseline also detects all eight released mutants, but it is not a second test module in the submission ZIP.

Evidence: [CRV mutation summary](evidence/current/mutations/summary.json) and [clean CRV control](evidence/current/mutations/crv/clean/run.log). Each mutation is applied independently using the exact IDs and replacements in [mutants_released.yaml](tb/mutants_released.yaml). Missing XML, build failures, skipped tests and non-assertion failures are not counted as detected mutants. Coverage holes alone do not kill a mutant.

The score above is a mutation score. Unit-test pass counts, coverage-bin counts and historical scores are different measurements; coverage and its convergence argument are in [closure.md](closure.md).

## Tests

The submission entry point is `test_crv_seeded_regression` in `test_fifo.py`, copied unchanged from Banmeet's `crv/test_fifo.py`. It uses the shared driver, monitor and independent reference-queue scoreboard. The driver applies inputs at falling edges; the monitor observes settled outputs after rising edges. Non-reset transactions are also checked before the active edge. Count, full/empty flags and the valid FWFT head are checked against the queue. Empty-state data is deliberately not compared.

The regression exercises fill/drain, dropped full writes, ignored empty reads, simultaneous requests at the boundaries and interior, reset/recovery, pointer wraps, data ordering and final draining. Default runs use WIDTH=8, DEPTH=8, seeds 4701, 17 and 4702, and 5,000 random cycles. Seed 4701 reproduces the same stimulus and coverage when repeated. The repository additionally retains five directed baseline tests; all pass in the recorded baseline run.

Unzip the submission and run `make SIM=icarus SEED=4701 N_CYCLES=5000`. The archive has one Makefile and one cocotb test module. The full repository can reproduce the campaigns with `python scripts/run_verification.py --suite mutations`; the upload itself does not depend on that repository runner.

## Survivors

**Current released-pool survivors: none.** The following are two historical survivors recorded in Daniel's unchanged [ai_log.md](ai_log.md), not survivors of the current suite. His earlier run found six of eight mutants. The original generated source and seed for that earlier run are not supplied in the log, so this is an analysis of his recorded result, not a claimed exact rerun of it.

| Mutant ID | Why it survived historically | What would catch it | Gap type |
|---|---|---|---|
| ignore_full | The historical stimulus excluded write requests when full, leaving the faulty write-acceptance path unexercised | Fill to DEPTH, request a write alone and with a read, check count/flags, then drain and compare ordering; the current suite detects this mutant | reachability |
| ignore_empty | The historical stimulus excluded read requests when empty, leaving faulty underflow acceptance unexercised | Drain to empty, request a read alone and with a write, check count/flags and subsequent valid-head recovery; the current suite detects this mutant | reachability |

The IDs above exactly match the released pool. The written specification makes full writes and empty reads legal requests whose outcomes are dropped or ignored. Excluding them prevents the scoreboard from observing the associated faults. This clarifies the specification without editing Daniel's original record.

## What I changed, and what it bought

The current team environment combines a reference-queue scoreboard with stimulus that includes boundary requests. All eight released faults are now detected: early full/empty flags, ignored full/empty gating, incorrect write-count updates, wrong head-pointer selection, data corruption and early pointer wrap.

The earlier historical suite missed the two boundary-gating faults described above. Their detection by the current suite is consistent with exercising those paths and comparing the resulting state. Because the historical and current sources differ in more than one respect, this is not presented as an isolated before/after experiment proving one change caused the entire improvement.

The integration adds isolated regression execution, explicit unresolved-value assertions and passive stimulus measurement. It preserves Banmeet's CRV/coverage implementation and Daniel's AI log. A short-run diagnostic is retained separately as a failed stimulus-quality experiment; it is not counted as a mutant detection. The default and supplemental coverage results are documented in [closure.md](closure.md).

## Residual risk

1. **reachability — distribution mismatch.** Measured write/read rates are approximately sixty-two percent across state/phase groups, rather than the declared state-dependent targets. The default coverage model closes, but the intended bias is not demonstrated. The CRV owner can inspect solver behavior and approve a correction; this submission does not claim a verified fix.
2. **reachability — supplemental data corner.** WIDTH=16, DEPTH=5 passes functional checks but misses the alternating-data coverage bin in the recorded run. Additional directed alternating patterns or an owner-approved constraint change could target it. Default WIDTH=8, DEPTH=8 coverage is closed.
3. **reachability — finite histories and parameters.** Only the stated seeds and configurations were measured. Rare histories, other parameters and the hidden mutant pool remain untested; additional seed/configuration sweeps would reduce this gap.
4. **observability — temporal sampling.** Before-edge and settled after-edge observations do not prove freedom from every subcycle glitch. Additional timing assertions would be needed if that were a requirement.
5. **observability — unspecified outputs.** Empty-state data and reset-time transfer semantics beyond the stated reset outputs are not defined by the contract. The scoreboard does not invent requirements for them. The supplied interface also has no almost-full signal or non-FWFT mode.

## If I had another day

I would coordinate a review of the declared-versus-measured CRV distribution with its owner, target the supplemental alternating-data hole, and use any available hidden-pool feedback to decide whether further stimulus or observations are needed. These are prospective improvements, not claimed completed work.

## AI disclosure

AI-assisted integration, documentation and validation are described in [CONTRIBUTIONS.md](CONTRIBUTIONS.md). Daniel's Check the Machine record remains in [ai_log.md](ai_log.md). The uploaded report and demo link are linked from [README.md](README.md).
