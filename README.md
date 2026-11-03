# Project 1 — Constrained-Random Verification of a Synchronous FIFO

**EEE 4701 / EEE 5703 · Verification & Validation of Digital Systems**  
University of Central Florida · Fall 2026

## Overview

This repository contains our team's verification environment for a parameterized **synchronous first-word-fall-through (FWFT) FIFO**. Using the supplied SystemVerilog RTL and written specification as the design-under-test (DUT) contract, we develop a layered **cocotb** testbench and evaluate correctness through directed tests, seeded randomized stimulus, functional coverage, and mutation testing.

The objective is not just to demonstrate passing tests: it is to provide **traceable requirements, reproducible results, measurable coverage, and an honest assessment of remaining verification gaps**.

## Verification approach

- **Driver:** applies clock-cycle transactions to the FIFO inputs.
- **Monitor:** samples DUT outputs and FIFO status after the relevant clock edge.
- **Reference-queue scoreboard:** independently models FIFO behavior and checks ordering, occupancy, flags, and output data.
- **Constrained-random verification (CRV):** extends the baseline stimulus using `pyvsc` constraints and reproducible seeds. *(In progress.)*
- **Functional coverage:** measures important operations, occupancy boundaries, and crosses; tracks coverage convergence. *(In progress.)*
- **Mutation testing:** evaluates whether the test suite detects intentionally faulty implementations.

### Primary scenarios

Reset and recovery · FIFO data ordering · Empty/full boundaries · Overflow and underflow requests · Simultaneous reads and writes · Pointer wraparound · Idle cycles and flag transitions · FWFT data visibility

## Repository layout

```text
.
├── dut/
│   ├── fifo.sv                  # Supplied FIFO RTL
│   └── specs/fifo.md            # Official FIFO behavior specification
├── lib/models/
│   └── fifo_model.py            # Reference model provided with course materials
├── tb/
│   ├── fifo_types.py            # Transaction definitions
│   ├── fifo_driver.py           # Signal-level stimulus driver
│   ├── fifo_monitor.py          # DUT observation layer
│   ├── fifo_scoreboard.py       # Reference-queue checks
│   ├── fifo_bench.py            # Verification environment integration
│   ├── test_fifo.py             # cocotb test suite
│   ├── Makefile                 # Simulation configuration
│   └── mutants_released.yaml   # Released mutant definitions
├── crv/                         # pyvsc stimulus and seeded regressions (in progress)
├── coverage/                    # Coverage model, results, and closure (in progress)
├── evidence/
│   ├── clean_icarus.log         # Baseline simulation output
│   ├── results.xml              # cocotb test results
│   └── mutation_icarus.log      # Released mutant detection output
├── vplan.md                     # Verification scope, traceability, and closure plan
├── CONTRIBUTIONS.md             # Individual team contributions
└── README.md
```

The final submission will also include `FINDINGS.md`, `ai_log.md`, `REPORT.pdf`, and a demo link as required by the project handout. `HW4.zip` is retained in the repository as an earlier-work archive.

## Running the baseline tests on Eustis

The baseline has been tested on the UCF Eustis environment with **Python 3.12, cocotb 1.9.2, and Icarus Verilog 12.0**.

1. Connect to Eustis from PowerShell (replace `YOUR_NID`):

   ```powershell
   ssh YOUR_NID@eustis.eecs.ucf.edu
   ```

2. On Eustis, clone the repository and activate the course environment:

   ```bash
   git clone https://github.com/prowilly/Project-1-Verification-and-Validation-of-Digital-Systems.git
   cd Project-1-Verification-and-Validation-of-Digital-Systems
   source /opt/course/cocotb-env/bin/activate
   ```

3. Run the FIFO simulation:

   ```bash
   make -C tb SIM=icarus
   ```

The Makefile uses the repository's `dut/fifo.sv` and `lib/` paths. The course-provided Eustis environment is recommended; a local setup requires compatible simulators and Python dependencies.

**Reproducibility:** Preserve the exact command, configuration, seed, and generated test report for each regression. Do not commit generated `sim_build/`, `__pycache__/`, or transient `results.xml` files; curated outputs belong under `evidence/`.

## Baseline results

| Check | Result | Evidence |
|---|---|---|
| Layered cocotb baseline | **5 / 5 passed** | `evidence/clean_icarus.log` and `evidence/results.xml` |
| Seeded randomized interleave | **1,200 transactions passed**, seed `0x4701` | Baseline simulation log |
| Released mutant pool | **8 / 8 detected (100%)** | `evidence/mutation_icarus.log` |
| Independent GitHub-checkout simulation | **5 / 5 passed** on Eustis | Reproduced using `make -C tb SIM=icarus` |

The **8/8 mutation result was obtained using the released pool in the original course environment** (`just mutate fifo`), not yet as a standalone mutation run from this GitHub checkout. These baseline results do **not** imply that Project 1 functional coverage closure, pyvsc integration, or the hidden mutant assessment is complete.

## Current project status

- [x] Team repository, FIFO RTL, specification, and reference model
- [x] Verification plan (`vplan.md`) initial version
- [x] Layered driver, monitor, and reference-queue scoreboard
- [x] Five passing baseline cocotb tests from the GitHub checkout
- [x] Eight of eight released mutants detected in the course environment
- [ ] Integrate `pyvsc` constrained-random transactions and seeded regressions
- [ ] Close functional coverage and document convergence
- [ ] Run the integrated mutation suite and analyze surviving mutants, if present
- [ ] Complete `FINDINGS.md`, `ai_log.md`, final report, and demonstration

## Team workflow

Work is shared on the `main` branch. Team members should pull the latest changes before editing, keep changes focused on their assigned components, and avoid committing generated simulator artifacts.

| Workstream | Primary ownership |
|---|---|
| Testbench architecture, directed tests, and integration | Verification environment lead |
| CRV, functional coverage, and mutation analysis | CRV / coverage lead |
| Check the Machine (`ai_log.md`), report assembly, and demo coordination | AI-evaluation / documentation lead |

All members review the integrated results and record their contributions in `CONTRIBUTIONS.md`.

## Verification documentation

- **[`vplan.md`](vplan.md):** features, requirement-to-test traceability, coverage plan, risks, and closure criteria.
- **[`dut/specs/fifo.md`](dut/specs/fifo.md):** authoritative functional specification; RTL is the implementation under test, not a substitute for the specification.
- **[`evidence/`](evidence/):** reproducible baseline simulation and mutation logs.
- **`FINDINGS.md` / `ai_log.md` (forthcoming):** integrated results, coverage gaps, mutation survivors, and AI-generated proposal versus measured behavior.

---

*Course project for EEE 4701 / EEE 5703. This repository documents educational verification work; coverage closure and final project sign-off remain in progress.*
