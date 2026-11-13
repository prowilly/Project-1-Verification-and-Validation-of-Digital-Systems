# Verification evidence

`current/` contains the completed Project 1 regression, convergence experiments and mutation runs. Every group has a `summary.json` with exact commands, tool versions and hashes of the tested verification source. Each case preserves `run.log`, JUnit `results.xml`, and (when the CRV reaches reporting) `coverage.json`/`coverage.yml`. Expected mutant failures are detections; they are not clean-regression failures.

`ctm_pre_run.md` records the completion predictions before the new code was executed. `history/ai_log_initial.md` and `history/HW4_FINDINGS.md` preserve the team's earlier records. The older root `clean_icarus.log`, `mutation_icarus.log` and `results.xml` are also historical Eustis baseline evidence, not substitutes for `current/`.

Regenerate without overwriting curated evidence:

```bash
python scripts/run_verification.py --output evidence/generated
```

Build directories and temporary mutated RTL are not submission artifacts. The runner reconstructs them from `dut/fifo.sv` and the released mutation definitions. Logs can contain absolute paths from the machine that executed them; the commands are parameterized by the runner on each machine.
