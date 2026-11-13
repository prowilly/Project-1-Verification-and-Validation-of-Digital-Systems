# Project 1 — Constrained-Random Verification of a Synchronous FIFO

**EEE 4701 · Verification and Validation of Digital Systems**\
University of Central Florida · Fall 2026\
**Team:** William Garland · Banmeet Singh · Daniel Jo

A layered cocotb verification environment for the supplied synchronous first-word-fall-through (FWFT) FIFO. It combines an independent reference queue, directed tests, pyvsc stimulus, functional coverage and released-mutation testing.

## Project status

The repository includes the verification plan, layered environment, constrained-random tests, coverage model/report, findings, Check the Machine record and completed contributions record. **`REPORT.pdf` and the demo link remain pending.** Measured results and limitations are documented below; hidden-pool performance and team approval are not assumed.

Banmeet's `crv/` and `coverage/` and Daniel's `ai_log.md` remain unchanged. Fresh verification evidence is stored separately in `evidence/current/`.

## Results

| Check | Measured result | Evidence |
|---|---|---|
| Layered baseline | **5/5 tests passed** | [Baseline log](evidence/current/regression/baseline/run.log) |
| CRV seeds 4701, 17, 4702 | **70/70 bins (100%)** each, 5,000 cycles per seed | [Regression summary](evidence/current/regression/summary.json) |
| Seed 4701 replay | **Identical stimulus and coverage** | [Replay evidence](evidence/current/regression/seed-4701-repeat/) |
| WIDTH=16 DEPTH=5; WIDTH=8 DEPTH=4 | Functional checks pass; coverage **69/70** and **70/70**, respectively | [Parameter results](evidence/current/regression/) |
| Released mutants, baseline | **8/8 detected** | [Mutation summary](evidence/current/mutations/summary.json) |
| Released mutants, CRV | **8/8 detected** | [Mutation summary](evidence/current/mutations/summary.json) |


The coverage total refers to Banmeet's existing 70-bin model. Flags, valid-head data, ordering and reset recovery are also checked by assertions. Measured CRV probabilities differ from the declared state-dependent weights; see [the distribution review in FINDINGS.md](FINDINGS.md#stimulus-distribution-review). This discrepancy is disclosed without rewriting the team's constraint implementation.

The current released suite has no surviving mutants. [FINDINGS.md](FINDINGS.md) analyzes `ignore_full` and `ignore_empty` from Daniel's documented earlier 6/8 run, separately from the new results. The hidden grading pool has not been run.

## Run the project

Use Python 3.12, Icarus Verilog 12.0 and the pinned Python packages. On Eustis, activate the course environment if it provides those versions. For a separate local environment:

```bash
git clone https://github.com/prowilly/Project-1-Verification-and-Validation-of-Digital-Systems.git
cd Project-1-Verification-and-Validation-of-Digital-Systems
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
iverilog -V
python scripts/run_verification.py --output evidence/generated
```

Icarus Verilog is a system prerequisite; `pip` installs the Python dependencies only. The full command runs unit checks, the baseline, three CRV seeds and replay, extra configurations, coverage-convergence measurements, and both released-mutation campaigns.

For individual groups:

```bash
python scripts/run_verification.py --suite regression
python scripts/run_verification.py --suite convergence
python scripts/run_verification.py --suite mutations
```

The runner uses a fresh temporary source copy for each simulation. It records commands, tool versions, source hashes, seeds, test XML, stimulus measurements and coverage. It checks XML outcomes rather than relying only on `make`'s exit status, enforces closure in the required regressions, and checks that teammate-owned files remain unchanged. Generated local evidence goes to the ignored `evidence/generated/` directory by default.

The baseline alone also runs with `make -C tb SIM=icarus`. For CRV, the root runner is recommended because a direct `make -C crv` writes generated coverage into `coverage/` using the existing team's Makefile/model.

## Repository guide

| Path | Purpose |
|---|---|
| [`dut/`](dut/) | Supplied RTL and authoritative FIFO specification |
| [`lib/models/fifo_model.py`](lib/models/fifo_model.py) | Independent reference queue |
| [`tb/`](tb/) | Driver, monitor, scoreboard, bench, five baseline tests and released mutant definitions |
| [`crv/`](crv/) | Banmeet's pyvsc transaction class, constraints and seeded regression |
| [`coverage/`](coverage/) | Banmeet's 70-bin model and original committed coverage report |
| [`scripts/run_verification.py`](scripts/run_verification.py) | Isolated regression, convergence and mutation runner |
| [`tests/`](tests/) | Checks for reliable simulation-result handling |
| [`evidence/current/`](evidence/current/) | Fresh logs, XML, coverage and reproducibility manifests |
| [`vplan.md`](vplan.md) | Requirements, coverage model, test matrix, risks and closure criteria |
| [`FINDINGS.md`](FINDINGS.md) | Results, convergence, two historical survivors and remaining limitations |
| [`ai_log.md`](ai_log.md) | Daniel's original Check the Machine record |
| [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md) | Evidence-backed team contributions and integration disclosure |
| `HW4.zip`, [`tb/FINDINGS.md`](tb/FINDINGS.md) | Earlier HW4 material, retained as historical context |

## Ownership and submission

William leads the layered environment, integration and verification documentation. Banmeet contributed the CRV and coverage implementation. Daniel contributed the Check the Machine analysis. See [CONTRIBUTIONS.md](CONTRIBUTIONS.md) for commit references and AI-assistance disclosure. Coordinate changes to another member's work with that author.

- [x] Verification plan and requirement-to-test mapping
- [x] Layered driver, monitor and reference-queue scoreboard
- [x] pyvsc constraints and seeded regression
- [x] Existing functional-coverage model and measured closure evidence
- [x] Current released-mutation results and two historical survivor analyses
- [x] Check the Machine record and team contributions
- [ ] Final 4–6 page `REPORT.pdf`
- [ ] Recorded demo link

The supplied FIFO has fixed FWFT behavior and no `almost_full` signal. Tests follow its actual written specification. Automated results do not constitute teammate review or final course grading.
