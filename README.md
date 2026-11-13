# Project 1 — Constrained-Random Verification of a Synchronous FIFO

**EEE 4701 · Verification & Validation of Digital Systems**\
University of Central Florida · Fall 2026\
**Team:** William Garland · Banmeet Singh · Daniel Jo

## Status

**Code, verification evidence and repository documentation are complete for the measured scope below.** The remaining submission deliverables are **`REPORT.pdf` and the demo link**.

| Check | Verified result |
|---|---|
| Layered cocotb baseline | **5/5 tests passed** |
| pyvsc regression | **5,000 cycles each**, decimal seeds **4701, 17 and 4702** |
| Functional coverage | **108/108 required bins (100%)** in each final normal run |
| Reproducibility | Repeated seed 4701 produces identical coverage JSON and stimulus hash |
| Parameter checks | **8x8, 16x5 and 8x4** WIDTHxDEPTH configurations pass and close coverage |
| Released mutation pool | **8/8 detected** by the baseline and final CRV suites separately |
| Survivor analysis | Two measured survivors in an explicitly weakened experiment; both detected by the final suite |
| Verification-tool checks | **3/3 unit checks passed** |

These results apply to the released pool and recorded configurations. The hidden grading pool is not available. Exact commands, source hashes, versions, logs and reports are under [`evidence/current/`](evidence/current/).

## What the environment verifies

The supplied DUT is a synchronous first-word-fall-through FIFO. A driver applies legal requests, a monitor observes public pins, and an independent reference-queue scoreboard checks occupancy, flags, valid output data and FIFO ordering. Directed tests and state-biased pyvsc traffic cover reset/recovery, idle holds, full/empty boundaries, simultaneous requests, data patterns, bursts and repeated pointer wraps.

Full writes and empty reads are **legal requests with specified dropped/ignored outcomes**. They remain in the normal stimulus. The reset-plus-write control corner is explicitly checked and covered. The supplied interface has no `almost_full` port or configurable non-FWFT mode.

## Run the checks

Prerequisites: **Python 3.12, Icarus Verilog 12.0 and GNU Make**. The Python verification dependencies are pinned in [`requirements.txt`](requirements.txt). On Eustis, use the course environment if its versions match, or an isolated environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/run_verification.py --output evidence/generated
```

The runner executes baseline tests, three CRV seeds, exact replay, two supplemental configurations, unit checks, convergence experiments and released mutation comparisons. It reads cocotb XML results and exits nonzero on failed signoff criteria; a zero `make` status alone is insufficient. Each run uses fresh, separate build/results paths. New local evidence does not overwrite the curated submission evidence.

For individual checks:

```bash
python scripts/run_verification.py --suite regression --output evidence/generated
python scripts/run_verification.py --suite experiments --output evidence/generated
python scripts/run_verification.py --suite mutations --output evidence/generated
```

Direct simulation is also available with `make -C tb SIM=icarus` and `make -C crv SIM=icarus SEED=4701 N_CYCLES=5000`. Direct CRV reports go to `coverage/generated/` unless `COVERAGE_DIR` is set. Use the Python runner for authoritative exit status and preserved evidence.

The baseline's Python-random test uses hexadecimal `0x4701` (18177 decimal). The separate pyvsc regression defaults to decimal `4701`; the seed shown in each command/report is the source of truth.

## Repository guide

| Path | Purpose |
|---|---|
| [`vplan.md`](vplan.md) | Specification requirements, executable test mapping, coverage bins/crosses, constraints and closure criteria |
| [`dut/specs/fifo.md`](dut/specs/fifo.md), [`dut/fifo.sv`](dut/fifo.sv) | Supplied functional contract and RTL |
| [`tb/`](tb/) and [`lib/models/fifo_model.py`](lib/models/fifo_model.py) | Layered environment, five baseline tests and independent queue model |
| [`crv/`](crv/) | pyvsc transactions, constraints, state bias and seeded tests |
| [`coverage/`](coverage/) | Full coverage model, measured distribution and convergence explanation |
| [`scripts/run_verification.py`](scripts/run_verification.py), [`tests/`](tests/) | Reproducible verification runner and focused correctness checks |
| [`FINDINGS.md`](FINDINGS.md) | Current mutation scores, two-survivor analysis and residual risks |
| [`ai_log.md`](ai_log.md) | Check the Machine prompt, prior predictions, observations, corrections and AI disclosure |
| [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md) | Actual contributions grounded in the commit history |
| [`evidence/current/`](evidence/current/) | Current logs, XML, coverage JSON/YAML and source/version manifests |
| [`evidence/history/`](evidence/history/), `HW4.zip` | Preserved earlier work, clearly separated from current results |

## Submission checklist

- [x] Team repository and contribution record
- [x] Specification-based verification plan and test traceability
- [x] Layered driver, monitor and reference-queue scoreboard
- [x] pyvsc constrained-random stimulus with measured distribution
- [x] Complete coverage model, 100% closure and measured convergence argument
- [x] Released mutation results and two observed survivor analyses
- [x] Check the Machine record with predictions, evidence and fixes
- [x] Reproducible regressions and all required local verification checks
- [ ] `REPORT.pdf` — 4-6 page team report
- [ ] Demo link — recorded walkthrough of the environment and evidence

AI-assisted completion work and its executed validation are disclosed in the AI log and contribution record. Only the report PDF and demo link remain outside this repository-completion task.
