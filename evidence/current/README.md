# Current Project 1 verification evidence

All three recorded command groups completed successfully on November 13, 2026 using the same verification-source hash. Expected mutant assertion failures are detections and are reported separately from clean-test failures.

| Group | Evidence | Outcome |
|---|---|---|
| Baseline, CRV seeds/replay, parameters and unit checks | [regression/summary.json](regression/summary.json) | Baseline 5/5; six normal CRV runs pass with 108/108 bins; exact replay; unit checks 3/3 |
| Reset-weight convergence comparison | [experiments/summary.json](experiments/summary.json) | Both close 108/108; 1/500 at cycle 1,031, 1/200 at cycle 400 for seed 4701 |
| Released mutation comparisons | [mutations/summary.json](mutations/summary.json) | Final baseline 8/8; final CRV 8/8; intentionally restricted experiment 6/8 with the two predicted survivors |

Each case folder contains the simulator log, XML result and (if the CRV reaches reporting) coverage JSON/YAML. Reports in failing mutant folders can be absent because the first functional mismatch stops the test before coverage export.

See [../../FINDINGS.md](../../FINDINGS.md) for interpretation and [../../coverage/README.md](../../coverage/README.md) for distribution/convergence detail. The summary manifests identify the starting git commit and the actual file-level SHA-256 source snapshot used for these runs. New local runs should use `evidence/generated`, as shown in the root README.
