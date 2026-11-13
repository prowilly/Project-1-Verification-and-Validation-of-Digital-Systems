# Project 1 contributions

**Course:** EEE 4701 — Verification and Validation of Digital Systems\
**Team:** William Garland, Banmeet Singh, Daniel Jo\
**Updated:** November 13, 2026

This record is grounded in the repository's existing commit history and the explicitly disclosed completion work below. It does not estimate hours or contribution percentages from commit counts.

| Member | Recorded contribution | Repository evidence |
|---|---|---|
| William Garland | Established the repository and verification plan; brought in the FIFO/specification/reference model and HW4 baseline; split the driver, monitor, scoreboard and environment into reusable modules; added directed reset/idle/transition checks and standalone build paths | `6df778e` (`vplan.md`), `fac4570` (baseline/mutant definitions), `65892f0` (layered modules), `be3d156` (directed tests), `ebb49f8` (Eustis author `wi323300`, Makefile paths); `tb/`, `dut/`, `lib/` |
| Banmeet Singh | Added and integrated pyvsc constrained-random stimulus; implemented the initial functional-coverage model and CRV Makefile; committed the original measured 70-bin report | `d6938c9`, `db9b73d` (`crv/`), `05a331f` (`coverage/fifo_coverage.py`), `030309a` (removed duplicate coverage location), `5826bbd` (coverage report) |
| Daniel Jo | Added the Check the Machine AI prompt, prior predictions, mutation output and correction discussion; introduced the initial contributions template | `2aff308` (`ai_log.md`, original preserved in `evidence/history/ai_log_initial.md`), `a39a54d` (initial template) |

## Completion and AI assistance

At William's explicit request on November 13, ChatGPT/Codex assisted with the repository-wide completion commit: filling the coverage-model gaps, strengthening reporting/failure detection, adding reproducible regressions and controlled mutation experiments, correcting documentation, assembling the evidence, and updating the front-page README. This work extends the team's files above; it is not presented as independently hand-written work by any teammate.

The assistant executed the simulations and focused unit checks recorded in `evidence/current/`, against the source hashes in each manifest. The model and checks were compared with `dut/specs/fifo.md`. The AI predictions, original historical record, observed outcomes and changes are documented in `ai_log.md`.

William requested and authorized this integration and publication. The repository does not claim that William, Banmeet or Daniel personally reran or reviewed the new automated completion results during this session. The report PDF and recorded demo remain the team's separate deliverables.
