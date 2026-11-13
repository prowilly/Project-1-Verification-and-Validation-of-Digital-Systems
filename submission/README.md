# Project 1 submission

Upload **[Project1_Submission.zip](Project1_Submission.zip)** to the assignment. Do not upload GitHub's whole-repository ZIP or the historical `HW4.zip`: those include multiple test entry points or older work.

The ZIP has one runnable directory at its root, with exactly one `test_fifo.py` and one `Makefile`. Its test is the unchanged CRV test from `crv/test_fifo.py`. Required helper modules, reference model, coverage model, supplied DUT/specification, released mutant pool, evidence and deliverables are included. The baseline's separate `tb/test_fifo.py` and the repository's runner unit tests are intentionally excluded from the upload; they remain in GitHub.

Required documents are at the ZIP root: `vplan.md`, `closure.md`, `FINDINGS.md`, `CONTRIBUTIONS.md`, `ai_log.md`, and `REPORT.pdf`. The README contains the existing demo link. The PDF and protected teammate-authored source files are copied without edits.

Rebuild from the repository root:

```bash
python scripts/package_submission.py
```

Extract the ZIP into an empty directory, activate the pinned Python environment with Icarus Verilog available, and run from that directory:

```bash
make SIM=icarus SEED=4701 N_CYCLES=5000
# The grader/mutation harness may override the RTL:
make SIM=icarus DUT=/absolute/path/to/fifo.sv
```

Use a fresh build (`make clean`) between RTL variants if running them manually. The local validation uses a fresh extracted copy for each variant and checks the XML test result rather than make's exit status alone.

`source_manifest.json` maps package files to original repository paths and SHA-256 hashes. Only the package Makefile/README and missing relative Markdown links are adapted for the standalone layout. Banmeet's original `crv/` and `coverage/` and Daniel's `ai_log.md` remain unchanged in the repository.
