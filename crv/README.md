# Constrained-random verification

`test_fifo.py` contains the pyvsc transaction, state-aware request weights, data-pattern constraints, reset constraints and the seeded regression. It reuses the driver, monitor, scoreboard and reference queue in `tb/` and `lib/`.

From the repository root, after installing `requirements.txt` and Icarus Verilog:

```bash
make -C crv SIM=icarus SEED=4701 N_CYCLES=5000
make -C crv SIM=icarus SEED=17 N_CYCLES=5000
make -C crv SIM=icarus SEED=4701 WIDTH=16 DEPTH=5
python scripts/run_verification.py --suite regression
```

The Makefile forwards WIDTH/DEPTH to both RTL elaboration and the Python environment, with separate build paths for each configuration. The final verified configurations are 8x8, 16x5 and 8x4. The coverage partitions require WIDTH>=3 and DEPTH>=4.

All four enable combinations, including full writes and empty reads, are legal requests under the supplied specification. The queue checks whether a request is accepted or ignored. Default `STIM=biased` preserves every boundary request. `STIM=restricted REQUIRE_CLOSURE=0` is the deliberately weakened survivor experiment; it is not a signoff mode.

Functional coverage is required. Import failure stops the test; uncovered bins fail normal runs. Reports go to `coverage/generated/` by default; set `COVERAGE_DIR` to preserve an individual run, or use the root runner, which isolates all outputs. The final drain is checked and sampled, and its coverage is separated from the saved random-only snapshot.

See [`../vplan.md`](../vplan.md) for requirement mapping and the intended distribution, [`../coverage/README.md`](../coverage/README.md) for measured convergence, and [`../FINDINGS.md`](../FINDINGS.md) for current mutation results.
