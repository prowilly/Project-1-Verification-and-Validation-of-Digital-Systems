# Coverage-completion predictions recorded before the new runs

Date: 2026-11-13. Author: ChatGPT/Codex, acting on William Garland's request to complete the repository except REPORT.pdf and the demo link.

The verbatim request was: "Complete everything besides the REPORT.pdf and demo link. Push them to the github and update the README on the front page when it's done."

This authoring task includes drafting the missing coverage model and experimental constraints. These are assistant predictions, not retroactively attributed to a teammate.

1. An over-constrained generator that prevents write requests at full and read requests at empty should leave `ignore_full` and `ignore_empty` alive, even if its clean scoreboard checks pass. Predict 6/8 released detections, with exactly those two survivors. The final generator should detect 8/8.
2. Treating both pointers wrapping on the same edge as a reachable bin would create a false coverage hole: accepted operations cannot both occur at occupancy zero or depth. The implemented `both_wrapped` bin will instead require that both logical indices have completed a revolution since reset, possibly on different edges. A focused sampler test will check this interpretation and clearing on reset.
3. A reset-recovery cross sampled only on the resetting edge would miss the first accepted post-reset write. Keep an explicit pending reset origin, sample on the actual later accepted write, and check this with a focused sequence.
4. At a finite prefix, reset/head-event/data bins may still be empty. Compare saved checkpoints using reset weight 1/500 and 1/200, then report the actual changes in closure time. Do not assume the tuning improves every seed or invent a speedup.

Outcomes and fixes will be recorded in ai_log.md and coverage/README.md after execution.
