# Functional coverage and convergence

The final model implements all C01-C12 and X01-X05 targets in [`vplan.md`](../vplan.md): **50 coverpoint bins + 58 reachable cross bins = 108 bins per configuration**. Every normal run requires 100% closure. Missing coverage dependencies fail the test, and normal runs assert that no holes remain.

## Final measured closure

| Seed (decimal) | WIDTHxDEPTH | Random cycles | Covered | First complete cycle | Evidence |
|---|---|---:|---:|---:|---|
| 4701 | 8x8 | 5,000 | 108/108 | 400 | [JSON](../evidence/current/regression/seed-4701/coverage.json) |
| 17 | 8x8 | 5,000 | 108/108 | 484 | [JSON](../evidence/current/regression/seed-17/coverage.json) |
| 4702 | 8x8 | 5,000 | 108/108 | 425 | [JSON](../evidence/current/regression/seed-4702/coverage.json) |
| 4701 repeat | 8x8 | 5,000 | 108/108 | 400 | [JSON](../evidence/current/regression/seed-4701-repeat/coverage.json) |
| 4701 | 16x5 | 5,000 | 108/108 | 340 | [JSON](../evidence/current/regression/width16-depth5/coverage.json) |
| 4701 | 8x4 | 5,000 | 108/108 | 416 | [JSON](../evidence/current/regression/width8-depth4/coverage.json) |

All 108 bins were covered before the final deterministic drain in every run above. The initial synchronous reset is sampled at cycle 0. Subsequent random/reset transactions are numbered from 1; the final drain is also checked and sampled, but is not needed to close these measured runs. Same-seed replay produced identical full coverage JSON and the same stimulus hash `67d0635eb4ee4d097daaf8337db570b11961a8d21111cb5326dbb7fe3b921015`.

`coverage_report.yml` is a convenience copy of the final seed-4701 report. Its authoritative metadata, raw hit counts, first-hit cycles, holes and checkpoints are in the linked JSON. The reports do not infer coverage from RTL internals.

## Hole closure and tuning

The earlier committed report closed 70/70 bins but omitted planned coverage. That original report is preserved as [`coverage_initial_70.yml`](../evidence/history/coverage_initial_70.yml). The final model adds observed flags, FWFT head events, reset/recovery scenarios, configuration tracking, temporal wrap milestones and the missing crosses. Reachability exclusions are specified in the plan; normal boundary requests are never excluded.

The following experiment uses identical source, seed 4701, configuration 8x8 and 5,000 random cycles. It changes only the nonempty reset weight from 1/500 to 1/200. It retains every measured checkpoint, including incomplete prefixes.

| Random-cycle checkpoint | Reset weight 1/500 | Reset weight 1/200 |
|---:|---:|---:|
| 100 | 96/108 | 96/108 |
| 200 | 98/108 | 102/108 |
| 400 | 107/108 | 108/108 |
| 500 | 107/108 | 108/108 |
| 1000 | 107/108 | 108/108 |
| 5000 | 108/108 | 108/108 |

The 1/500 run closed at cycle **1031**; the 1/200 run closed at **400**. In the 1/500 run, the only hole remaining at cycles 400, 500 and 1,000 was `reset_plus_write`. Increasing the reset weight closed that hole sooner in this seed. Both variants ultimately reached 108/108. This is one controlled seed comparison, not a claim that every seed improves by the same factor. Full before/after evidence is in [`experiments/`](../evidence/current/experiments/).

The named late bins in the final default run were:

| Bin | First hit cycle |
|---|---:|
| fifo.transition_x_flags:('hold_full', 'full') | 125 |
| fifo.occ_x_request:('full', 'read') | 126 |
| fifo.occ_x_request:('full', 'write') | 212 |
| fifo.reset_control:reset_plus_write | 339 |
| fifo.reset_scenario:reset_when_nonempty | 339 |
| fifo.recovery_origin:reset_when_nonempty | 340 |
| fifo.reset_x_first_accept:('reset_when_nonempty', 'write_only') | 340 |
| fifo.occ_x_head:('full', 'head_after_wrap') | 400 |

All remaining holes were closed by constrained-random traffic within the saved budget; no directed patch was used to manufacture the final coverage percentage. The deterministic final drain remains as an ordering/data-integrity check.

## Distribution check and correction

A passing scoreboard and closed coverage did not by themselves establish the claimed stimulus bias. During completion, guarded distribution blocks produced fill-phase write requests of **61.07%** against a 90% target, and drain-phase read requests of **62.10%** against a 90% target. The observed mismatch is preserved in [`pre_distribution_fix/`](../evidence/history/pre_distribution_fix/), along with the earlier source and manifest.

The correction selects nonrandom weight values from live occupancy/phase before randomization and uses one unconditional `vsc.dist` per enable. The pyvsc solver still generates the transactions. This avoids relying on the earlier guarded weighting behavior. Normal signoff checks the observed request rates using six binomial standard errors plus two percentage points of tolerance, with at least 100 samples per rule. It also checks generated data-category rates. This is a finite-regression diagnostic, not a proof of the solver's probability law.

Measured default seed-4701 request distribution, including requests on reset cycles:

| Rule | Samples | Target write | Observed write | Target read | Observed read |
|---|---:|---:|---:|---:|---:|
| near_empty | 1401 | 70% | 69.88% | 60% | 59.74% |
| near_full | 1283 | 60% | 59.94% | 70% | 69.60% |
| fill | 1192 | 90% | 89.43% | 30% | 28.02% |
| drain | 1124 | 30% | 30.16% | 90% | 90.30% |

The data-category selector is explicit, so alternating values remain well exercised at WIDTH=16:

| Category | Target | Generated requests | Observed |
|---|---:|---:|---:|
| zero | 10% | 463 | 9.26% |
| all-one | 10% | 514 | 10.28% |
| alternating A | 10% | 492 | 9.84% |
| alternating B | 10% | 472 | 9.44% |
| other | 60% | 3059 | 61.18% |

There were 20 nonempty resets among 4707 eligible random cycles (0.425%, configured target 0.5%). The expected weights describe generated requests; accepted-write/data statistics can differ because full requests are dropped. Occupancy counts and boundary-event counts are retained in each JSON, not asserted to be uniform.

## Sampling and exclusions

- `_cycle` samples pre-edge occupancy/request/acceptance and observed post-edge flags after the scoreboard passes.
- X04 samples each actual checked head event using that same cycle's pre-edge occupancy. Multiple genuine head events can occur on a transaction.
- X05 remembers the reset origin until an actual accepted post-reset write; an empty read does not count as recovery.
- C10 counts accepted transactions modulo DEPTH. `both_wrapped` means both indices have completed a revolution since reset, on potentially different edges. A simultaneous-wrap target would be unreachable here.
- X02 excludes four impossible accepted-operation combinations; X03 excludes inconsistent transition/flag pairs; X04 excludes impossible occupancy/head-event pairs; X05 excludes reads before the first post-reset write. Every ignored combination is justified in the plan.
- An empty `rd_data` value is unspecified. An unresolved or incorrect head when required is a failure. Invalid count/flag states fail assertions.

## Reproduce

```bash
python scripts/run_verification.py --suite regression --output evidence/generated
python scripts/run_verification.py --suite experiments --output evidence/generated
```

Use the pinned dependencies and Icarus version in the manifests. New runs go to separate output directories; the script verifies XML outcomes and source hashes. The deliberately restricted survivor experiment disables closure explicitly and is excluded from normal coverage signoff.
