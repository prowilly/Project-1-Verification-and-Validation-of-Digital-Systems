# Layered FIFO environment

- `fifo_driver.py`: validates and drives public input transactions at falling edges.
- `fifo_monitor.py`: observes settled public pins and reports unresolved required values.
- `fifo_scoreboard.py`: checks the independent reference queue, count, flags and valid FWFT head.
- `fifo_bench.py`: coordinates clock, synchronous reset and transactions.
- `test_fifo.py`: five directed/seeded baseline tests at WIDTH=8, DEPTH=8.
- `mutants_released.yaml`: eight supplied practice mutations, applied individually by the root runner.

From the repository root:

```bash
make -C tb SIM=icarus
python scripts/run_verification.py --suite regression
```

Use the Python runner for a reliable pass/fail exit status and saved evidence. The baseline's 1,200-cycle Python-random test uses seed `0x4701` (18177 decimal); the separate pyvsc suite defaults to decimal seed 4701. Current results and survivor analysis are in [`../FINDINGS.md`](../FINDINGS.md). Historical HW4 results are preserved separately.
