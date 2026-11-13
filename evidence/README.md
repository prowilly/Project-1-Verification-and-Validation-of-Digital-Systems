# Verification evidence

Fresh, reproducible Project 1 results are under [`current/`](current/):

- `regression/`: five-test baseline; three CRV seeds; identical-seed replay; two extra width/depth configurations.
- `convergence/`: measured coverage holes and closure using existing CRV settings and different run lengths.
- `mutations/`: clean controls and each of the eight released mutants, run separately against the baseline and CRV suites.

Each group has `summary.json` with tool versions, exact source SHA-256 hashes, protected-file hashes, commands, seeds and outcomes. Per-run folders contain `run.log`, `results.xml`, and, for passing CRV runs, `coverage.yml` and `stimulus.json`. Stimulus summaries describe the random loop only; the initial reset and final drain are excluded. The temporary full trace is hashed and summarized rather than committed.

The manifest's `base_commit` is the checkout from which the work was prepared. The file-level hashes identify the exact tested source, including additions not yet committed at run time. They take precedence over interpreting the base commit as the full tested tree. Temporary filesystem paths in logs identify disposable run copies; the source hashes, mutation definitions, command and environment reproduce them from any clone.

`clean_icarus.log`, `mutation_icarus.log`, and `results.xml` at this directory's root are earlier uploaded Eustis evidence. Their historical context remains in [`tb/FINDINGS.md`](../tb/FINDINGS.md). Daniel's historical Check the Machine result remains in [`ai_log.md`](../ai_log.md). Neither is relabeled as a fresh run.

## Reproduce

```bash
python scripts/run_verification.py --output evidence/generated
```

The runner never runs simulations inside the tracked `crv/` or `coverage/` directories. It copies source files into a fresh temporary workspace for every case, collects generated reports under the requested output, and verifies that the protected originals remain unchanged. `coverage/coverage_report.yml` remains Banmeet's original report; new reports are stored here separately.

See [`FINDINGS.md`](../FINDINGS.md) for results, convergence, survivor analysis and limitations.
