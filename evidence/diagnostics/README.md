# Short-run diagnostic

The exploratory 1,000-cycle CRV run passed the observed FIFO behavior checks but failed the existing stimulus-quality assertion: only three fills occurred, below the required five. It also reached only 69/70 coverage bins, missing `fifo.reset:reset_no_request`. This is an actual failed experiment, not a passing regression or a mutant detection.

`short-run/run.log` and `short-run/results.xml` preserve the result. `initial-convergence-summary.json` records the source hashes and commands for that exploratory group; its uniform comparison is now in `../current/convergence/uniform-5000/`. `runner_before_length_adjustment.py` preserves the exact runner version named in that manifest. The only subsequent runner change was increasing the scheduled short biased run from 1,000 to 3,000 cycles. No teammate-owned source was changed.

The final check set uses a passing 3,000-cycle comparison and 5,000-cycle required regressions. The late reset bin demonstrates why the run length matters. Reproduce the short diagnostic, expecting a nonzero result, from the repository root after setup:

```bash
python -c "from scripts.run_verification import Runs; Runs('evidence/generated/diagnostic').run('short-run', cycles=1000, closure=False)"
```
