# Project 1 findings — synchronous FIFO

**Date:** November 13, 2026. **Course:** EEE 4701. **Scope:** all repository verification work; the team report PDF and demo link remain separate deliverables.

The final baseline passes 5/5 tests. The pyvsc suite closes all **108/108 required bins** for three baseline seeds and two supplemental configurations, with exact same-seed reproduction. Both final suites detect **8/8 released mutants**. The hidden grading pool is unavailable and is not claimed tested.

## Current mutation quality

| Suite | Released found/total | Survivors | Purpose |
|---|---:|---|---|
| Five-test layered baseline | 8/8 (100%) | None | Directed/seeded regression |
| Final pyvsc suite, seed 4701 | 8/8 (100%) | None | State-biased CRV |
| Deliberately restricted pyvsc suite, seed 4701 | 6/8 (75%) | `ignore_full`, `ignore_empty` | Controlled survivor experiment |

Each group first ran a passing clean control, then applied each released mutation independently to an isolated RTL file. All variants compiled and produced the expected number of XML test results. Expected assertion failures count as detections; missing XML, skipped tests and infrastructure errors are rejected separately. Functional coverage is collected but not enforced during mutation experiments, so lack of coverage alone cannot kill a mutant. Normal signoff uses the separate closure-enforcing regressions.

Evidence: [`mutation summary`](evidence/current/mutations/summary.json), including exact commands and per-case logs/XML. The runner is [`scripts/run_verification.py`](scripts/run_verification.py), and the supplied pool is [`tb/mutants_released.yaml`](tb/mutants_released.yaml).

## Two observed survivors and what catches them

The final released suite has no survivors. The following two genuinely survived the saved **controlled restricted-input experiment**, which intentionally removes the boundary requests needed to expose them. This is an ablation of the current suite, not a claim that the final suite missed them, and not a reconstruction of an unrecorded earlier run.

| Survivor in restricted experiment | Why it survives | Spec violation and detecting stimulus | Final result |
|---|---|---|---|
| `ignore_full` | The weakened constraints force `wr_en=0` whenever the reference queue is full, so the faulty write-acceptance path is never exercised. | Fill to DEPTH; request a write while full (alone or with a read). The spec drops the write. Compare count/flags and queued head/order; drain the remainder to reveal corruption. | Detected by both final suites |
| `ignore_empty` | The weakened constraints force `rd_en=0` when the queue is empty, so incorrect underflow acceptance is never exercised. | Drain to empty; request a read, including simultaneous read/write at empty. The spec ignores the read. Check count/flags, first valid head and subsequent ordering. | Detected by both final suites |

These are stimulus-reachability gaps. The same independent queue scoreboard remains in all experiments. Restoring the legal rejected-request cases raises the measured score from 6/8 to 8/8; it does not require permitting out-of-range signals or inventing illegal transactions. The restricted clean run covers 104/108 bins and is explicitly excluded from signoff.

## Released-pool result by mutation

| Mutant | Fault | Final baseline | Final CRV | Observable check |
|---|---|---|---|---|
| `full_offbyone` | Full one entry early | Found | Found | Flag/count agreement near full |
| `empty_offbyone` | Empty asserted at count one | Found | Found | Reset/empty flag and valid-head checks |
| `ignore_full` | Accept full writes | Found | Found | Dropped-write occupancy and ordering |
| `ignore_empty` | Accept empty reads | Found | Found | No-underflow count/flags and recovery |
| `count_wr_dec` | Decrement on write | Found | Found | Reference occupancy/range |
| `rd_data_wrptr` | Read head from write pointer | Found | Found | Known, correct FWFT head |
| `mem_corrupt` | Add one to written data | Found | Found | Exact valid-head data |
| `wrptr_wrap_early` | Wrap write pointer early | Found | Found | Distinct data/order through wraps |

The monitor now reports unresolved required values as explicit assertion failures. It continues to ignore unspecified empty-state data.

## Coverage, correctness and reproducibility

The environment keeps separate driver, monitor, reference-queue scoreboard and stimulus/coverage layers. CRV checks both pre-edge stability and settled post-edge behavior. Reset is tested synchronously and with asserted requests. Every requested signal is in range; all normal boundary request combinations are legal.

See [`coverage/README.md`](coverage/README.md) for the complete coverage table, first-hit evidence, measured distribution, the corrected conditional-weight issue and the 1/500-to-1/200 reset-weight experiment. All final normal runs close during random traffic; final draining is not needed for coverage closure. The source content hash is `5351bff7374d0b2c614c479b728d1c2e1b5642a7b888c7ed8823ff9b6a2dce42` and is recorded with file-level hashes in every current manifest. Same-seed replay compares the entire coverage JSON, including its stimulus hash.

```bash
python scripts/run_verification.py --output evidence/generated
```

This runs focused unit checks, baseline, three seeds, replay, 16x5 and 8x4 parameter cases, convergence experiments and the three released mutation groups. It exits nonzero on failed signoff criteria. See README for environment setup.

## Residual risk

Finite runs cannot prove all data histories or parameter combinations, and the hidden pool may contain other faults. Only 8x8, 16x5 and 8x4 are measured; smaller coverage partitions need redesign. The monitor does not exhaustively check subcycle glitches. Empty-state head data and reset-time transfer acceptance are not specified beyond the reset-state contract. These limitations are stated rather than counted as covered behavior.

Historical HW4 results and the original AI evaluation are retained in [`evidence/history/`](evidence/history/). Their scores and source versions are distinct from the results above. AI-assisted changes and validation are disclosed in [`ai_log.md`](ai_log.md) and [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md).
