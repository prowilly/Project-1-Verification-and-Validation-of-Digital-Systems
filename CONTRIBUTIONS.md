# Project 1 contributions

**Course:** EEE 4701 — Verification and Validation of Digital Systems\
**Team:** William Garland, Banmeet Singh, Daniel Jo\
**Updated:** November 13, 2026\
**Repository:** https://github.com/prowilly/Project-1-Verification-and-Validation-of-Digital-Systems

This record describes contributions supported by the repository history. It does not infer effort percentages or hours from commit counts, and it does not claim that teammates reviewed work they have not reviewed.

| Member | Recorded work | Evidence |
|---|---|---|
| William Garland | Established the repository; imported the supplied FIFO, specification and reference model; integrated the HW4 baseline; organized the driver, monitor, scoreboard and bench; added directed reset/idle/transition tests and standalone simulation paths; authored the verification plan and repository documentation | `2c19829`, `ad098e0`, `be8155b` (supplied design/spec/model); `fac4570`, `65892f0`, `be3d156` (testbench); `6df778e` (plan); `ebb49f8` (build paths, Eustis author `wi323300`) |
| Banmeet Singh | Implemented pyvsc transactions and occupancy-dependent constraints; integrated the seeded CRV regression and Makefile; implemented functional coverage; removed the duplicate coverage module and committed the measured 70-bin report | `d6938c9`, `db9b73d` (`crv/`); `05a331f`, `030309a` (coverage implementation/location); `5826bbd` (`coverage/coverage_report.yml`) |
| Daniel Jo | Documented the Check the Machine prompt, prior predictions, observed 6/8 mutation result, two survivors, API corrections and lessons; introduced the contributions template | `2aff308` (`ai_log.md`); `a39a54d` (initial contributions template) |

## Integration and AI assistance

At William's request, ChatGPT/Codex assisted with the verification plan, README, this contributions record, root findings, a standalone regression/mutation runner, passive pin tracing, explicit unresolved-value diagnostics, and fresh evidence. The supplied reference model's description was aligned with the written specification; its behavior was not changed.

The assistant executed the automated checks in `evidence/current/`. Each summary records the exact source hashes, tool versions, commands and seeds. William authorized this integration and publication. This is AI-assisted work, not a claim that William independently hand-wrote the additions or that any team member personally reran or approved the new results.

Banmeet's entire `crv/` and `coverage/` directories and Daniel's `ai_log.md` are preserved byte-for-byte. Tests run temporary copies so generated reports cannot replace Banmeet's committed report. William explicitly requested completion of this file despite its initial template having been committed by Daniel.

