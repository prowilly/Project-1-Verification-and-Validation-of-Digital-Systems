# Coverage closure — Project 1 synchronous FIFO

**Course:** EEE 4701\
**Team:** William Garland, Banmeet Singh, Daniel Jo\
**Configuration required for closure:** WIDTH=8, DEPTH=8\
**Target:** 100% of the 70 reachable bins in the implemented model

## Coverage model

The model is Banmeet's unchanged [coverage/fifo_coverage.py](coverage/fifo_coverage.py). It measures stimulus and reference acceptance state; correctness is determined separately by the reference-queue scoreboard. The original committed report remains in [coverage/coverage_report.yml](coverage/coverage_report.yml). Fresh reports are stored under `evidence/current/`.

| Coverage item | Required bins |
|---|---:|
| Occupancy: empty, one, middle, near_full, full | 5 |
| Requested operation: idle, read, write, both | 4 |
| Accepted operation: none, read_only, write_only, both | 4 |
| Key occupancy transitions and holds | 7 |
| Occupancy × requested operation | 20 |
| Occupancy × accepted operation | 16 |
| Write data: zero, all-ones, alternating, other | 4 |
| Write request burst: single, short, long | 3 |
| Read request burst: single, short, long | 3 |
| Inferred write/read pointer wrap | 2 |
| Reset without a write request / reset plus write | 2 |
| **Total** | **70** |

Coverage samples pre-edge occupancy and the corresponding post-edge state during the CRV loop. It excludes the initial three reset edges and final drain. Burst bins count requests, rather than necessarily accepted transfers. Pointer-wrap bins use reference-model accepted-transfer counts, not RTL internals. First-hit tracking occurs every ten samples; reported closure cycles are quantized observations.

## Target and result

The required default configuration reaches **70/70 bins (100%)** for all three recorded seeds. There are no unhit bins in those default reports. Same-seed replay produces identical stimulus and complete YAML coverage, not merely the same percentage.

| Run | Random cycles | Bins hit/total | Recorded closure cycle | Report |
|---|---:|---:|---:|---|
| Seed 4701 | 5,000 | 70/70 | 1,200 | [YAML](evidence/current/regression/seed-4701/coverage.yml) |
| Seed 17 | 5,000 | 70/70 | 410 | [YAML](evidence/current/regression/seed-17/coverage.yml) |
| Seed 4702 | 5,000 | 70/70 | 1,390 | [YAML](evidence/current/regression/seed-4702/coverage.yml) |
| Seed 4701 repeat | 5,000 | 70/70 | 1,200 | [YAML](evidence/current/regression/seed-4701-repeat/coverage.yml) |

## Holes and fixes

The initial short-run diagnostic used the unchanged biased generator, seed 4701, for only 1,000 cycles. It reached 69/70 bins, missing `fifo.reset:reset_no_request`. It also failed the existing minimum-fill assertion: three fills occurred, while at least five were required. This diagnostic is not a passing regression. The raw failure is preserved in [short-run/run.log](evidence/diagnostics/short-run/run.log).

The corrective action was to extend the run budget, preserving both the seed and the constraints. The generator then reached the late reset-without-write bin; complete closure was first recorded at cycle 1,200. The passing 3,000- and 5,000-cycle runs satisfy the test's stimulus-quality checks as well. No directed coverage-fill sequence or constraint modification was injected, and no failing test was relabeled as a pass.

| Hole / issue | Before | Action | After / evidence |
|---|---|---|---|
| Reset without write | Unhit at 1,000 cycles | Extend the same biased seeded run | All bins hit; [3,000-cycle log](evidence/current/convergence/biased-3000/run.log) |
| Too few fill/drain excursions | Short diagnostic stopped after three fills | Increase runtime rather than weakening the minimum-fill assertion | Passing 3,000- and 5,000-cycle checks |
| Supplemental 16-bit alternating data | Unhit at 5,000 cycles | Disclose as an open supplemental gap; preserve the owner's constraints | Default configuration remains closed; supplemental configuration is not claimed closed |

## Convergence argument

| Existing stimulus setting, seed 4701 | Cycles | Coverage | Recorded closure cycle |
|---|---:|---:|---:|
| Biased, short diagnostic | 1,000 | 69/70; test fails minimum-fill check | Not reached |
| Biased | 3,000 | 70/70; test passes | 1,200 |
| Biased | 5,000 | 70/70; test passes | 1,200 |
| Uniform comparison | 5,000 | 70/70; test passes | 1,350 |

The short diagnostic identifies a concrete late hole, and the longer runs show closure without changing the model or relaxing a check. The extra seeds provide evidence that closure is not unique to one seed. They do not establish a universal probabilistic guarantee. Uniform mode is the existing CRV switch: it disables boundary/data constraints while retaining reset constraints. No claim is made that this session reproduced the source comment's earlier reset-weight tuning experiment.

In the 5,000-cycle biased run, late observed bins include reset without write at cycle 1,200, reset plus write at 680, alternating data at 350, empty/idle at 250, and a long read burst at 100. These observations explain why a short run can cover common FIFO behavior yet miss a rare reset combination. See [the seed-4701 log](evidence/current/regression/seed-4701/run.log).

## Illegal and ignore bins

All normal write/read request combinations are legal at every occupancy. The specification drops writes at full and ignores reads at empty, so neither request is excluded from coverage.

Four accepted-operation cross combinations are impossible and explicitly ignored: empty × read_only, empty × both, full × write_only, and full × both. These exclusions follow the pre-edge acceptance rules. Invalid counts, inconsistent flags and wrong valid-head data fail scoreboard assertions; they are not excused as ignore bins. Empty-state data is unspecified and is not compared.

## Residual risk

- The coverage target applies to the implemented 70-bin model. Flag transitions, valid-head behavior and reset recovery also have assertions, but are not additional coverage crosses. Full model coverage is not exhaustive verification.
- WIDTH=16, DEPTH=5 reaches 69/70 bins, missing alternating data. WIDTH=8, DEPTH=4 reaches 70/70. These are supplemental configurations, reported separately from mandatory default closure.
- Measured write/read rates are approximately 62% across the state/phase groups, rather than the intended state-dependent targets. The measured distribution is saved in [stimulus.json](evidence/current/regression/seed-4701/stimulus.json). Closure does not prove the intended bias was implemented; the discrepancy remains for the CRV owner to review.
- Report-time burst flushing can add a bin after the last ten-cycle tracking interval. Therefore the final bin counts, not `closed_at` alone, determine final coverage.
- Finite seeds and tested configurations cannot prove hidden-pool quality or every possible history. Mutation quality is reported separately in [FINDINGS.md](FINDINGS.md).

## Reproduction and evidence

From the full repository:

```bash
python scripts/run_verification.py --suite regression
python scripts/run_verification.py --suite convergence
```

From the extracted submission ZIP:

```bash
make SIM=icarus SEED=4701 N_CYCLES=5000
```

The standalone submission uses the same CRV test, coverage model, layered helpers and reference model. Its Makefile adapts only the package paths and exposes `DUT` for mutation runs. Generated coverage is written into the extracted copy's `coverage/` directory. The repository's protected sources and committed original report are not modified by archive validation.

Each repository summary records exact source hashes, simulator/dependency versions, commands and seeds. The submission includes these reports, its own source-copy manifest and the released pool with its original IDs.
