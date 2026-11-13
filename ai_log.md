# Project 1 — Check the Machine and AI assistance log

## 1. Original team experiment

Daniel Jo's original prompt, predictions, reported output and correction list are preserved unchanged in [`evidence/history/ai_log_initial.md`](evidence/history/ai_log_initial.md), from commit `2aff308`. The original prompt was:

```text
Write a `pyvsc` transaction class for a synchronous FIFO (width=8, depth=8). Include constraints that ensure every transaction is legal (no writing when full, no reading when empty). Add constraints to specifically stress the near-full and near-empty occupancy corners, empty reads and over writes, and simultaneous read and write operations. The constraints should induce a distribution that hits these corners frequently over a 3000-cycle test.
```

The original record predicted a live-state/legality problem and missed full-boundary overlap, and reported 6/8 released detections with `ignore_full` and `ignore_empty` surviving. That is historical reported evidence, not the current suite's score. Its shown mutation output does not by itself establish a solver contradiction, and the exact old generated source/seed is not present in that record.

**Correction to the interpretation:** the written FIFO specification permits full-write and empty-read requests and defines their dropped/ignored outcomes. Those requests are not illegal transactions. The prompt's parenthetical legality definition over-constrains the stimulus and conflicts with its requested boundary tests. Likewise, off-by-one/pointer detections do not prove that the full-boundary simultaneous cross was hit; that requires actual coverage evidence.

## 2. Completion request and before-run predictions

On November 13, William requested:

```text
Complete everything besides the REPORT.pdf and demo link. Push them to the github and update the README on the front page when it's done.
```

ChatGPT/Codex drafted the missing coverage and constraint changes as part of that request. Before running those new changes, the assistant recorded predictions in [`evidence/ctm_pre_run.md`](evidence/ctm_pre_run.md). These predictions are explicitly assistant-authored, not retroactively attributed to a teammate.

| Prediction | Measured outcome | Assessment |
|---|---|---|
| Suppressing legal boundary requests should leave `ignore_full` and `ignore_empty` alive; restoring them should detect 8/8. | Restricted experiment: 6/8 with exactly those two survivors. Final baseline and CRV: 8/8 each. | Confirmed by separate clean controls and released runs |
| A simultaneous accepted-pointer-wrap bin would be unreachable; a temporal both-wrapped-since-reset milestone is needed. | Focused sampler test observes adjacent-edge wraps, one temporal milestone, and clearing of logical indices on reset. | Corrected model verified |
| Reset recovery must be recorded on the later first accepted write, not merely on the reset edge. | Unit sequence proves empty reads do not close the recovery cross; both reset origins close on actual later accepted writes. | Verified |
| Finite prefixes will leave holes; increasing reset frequency may change closure time and must be measured. | Same seed/configuration: 1/500 closes at 1031; 1/200 at 400; both reach 108/108. | Improvement measured for this seed only |

## 3. Unexpected distribution problem and every completion fix

A newly instrumented run closed coverage while failing to generate the intended per-rule bias. Fill-phase writes measured 61.07% rather than 90%, and drain-phase reads measured 62.10% rather than 90%. This was not predicted in the before-run note. The prior constraints, full prior CRV source, output and source manifest are preserved in [`pre_distribution_fix/`](evidence/history/pre_distribution_fix/).

The completion changes were:

1. Replaced the guarded per-branch enable distributions with one unconditional distribution per enable, using nonrandom weights selected from live queue occupancy and phase before each solve. Added measured per-rule rate assertions, so passing functional checks cannot conceal the same bias error.
2. Made data-pattern selection explicit (zero, all-one, two alternating patterns, other) so the wider 16-bit regression can reach the promised data bins. Checked generated category frequencies as well as accepted-write coverage.
3. Added the missing C05/C06/C09/C12 and X03-X05 model elements, completed C10 with a reachable temporal definition, sampled initial reset/recovery and the final drain, and based flag coverage on actual checked observations.
4. Removed the silent optional-coverage import path. Normal runs now fail on coverage holes. The only closure-disabled modes are explicitly labeled convergence/mutation diagnostics.
5. Added a reproducible runner with fresh build/results directories, XML pass/fail parsing, exact source hashes, tool versions, same-seed comparison and measured parameter elaborations. Unit checks reject missing/empty XML and detect assertion, error and skip records.
6. Added the intentionally weakened boundary-request constraint mode only for the controlled two-survivor experiment. The ordinary suite keeps all specified request combinations enabled.
7. Turned unresolved required signal values into clear monitor assertions, retained unspecified empty-data handling, and replaced outdated planning/status documents with current measured findings and honest contributions.

All these changes and the preserved initial record are disclosed; no synthetic score or unexecuted measurement is presented as a run.

## 4. After-run evidence

The final regression passes the five-test baseline, three 5,000-cycle CRV seeds, exact replay, two supplemental WIDTH/DEPTH configurations and three focused unit checks. Every final normal coverage report reaches 108/108, before deterministic final draining. See [`regression/summary.json`](evidence/current/regression/summary.json).

Final seed-4701 request rates are:

| Rule | Samples | Target write | Observed write | Target read | Observed read |
|---|---:|---:|---:|---:|---:|
| near_empty | 1401 | 70% | 69.88% | 60% | 59.74% |
| near_full | 1283 | 60% | 59.94% | 70% | 69.60% |
| fill | 1192 | 90% | 89.43% | 30% | 28.02% |
| drain | 1124 | 30% | 30.16% | 90% | 90.30% |

Full counts, data-pattern distribution, reset observations, hole timelines and limitations are in [`coverage/README.md`](coverage/README.md). Current mutation evidence and both survivor analyses are in [`FINDINGS.md`](FINDINGS.md). The shared verification-source hash is `5351bff7374d0b2c614c479b728d1c2e1b5642a7b888c7ed8823ff9b6a2dce42`.

## 5. Takeaway and attribution

Verify a claimed stimulus distribution with counts, and verify a claimed coverage model with reachability and sampling checks. Passing the clean design or achieving 100% of an incomplete model is insufficient. Full-write and empty-read requests are essential specified cases; excluding them creates demonstrable reachability gaps.

The assistant wrote the completion changes and executed the saved automated checks at William's request. The original team contributions remain attributed through git history. This log does not attest that teammates independently reran or reviewed the completion results during this session. The report PDF and demo remain outside this completion task.
