# Project 1 AI Log

**Group Members:** Daniel Jo\
**Section:** EEE 4701\
**Week:** Project 1 — Constrained Random Stimulus\
**Autonomy tier:** self-directed\
**Assistant used:** a general-purpose frontier
assistant, web interface, November 2026

---

## 1. Task

The machine was asked to generate a pyvsc transaction class with a block of constraints for a synchronous FIFO (width 8, depth 8) to test specific corner cases without generating illegal transactions.

**Prompt (verbatim):**

```text
Write a `pyvsc` transaction class for a synchronous FIFO (width=8, depth=8). Include constraints that ensure every transaction is legal (no writing when full, no reading when empty). Add constraints to specifically stress the near-full and near-empty occupancy corners, empty reads and over writes, and simultaneous read and write operations. The constraints should induce a distribution that hits these corners frequently over a 3000-cycle test.
```

---

## 2. Before


**Prediction 1 —** The AI will generate illegal transactions because the pyvsc class won't have access to the live FIFO state, like the full or empty flags.
*Evidence that would show it:* A pyvsc.RandomizationError in the console or a gtkwave waveform showing a write occurring while the FIFO is already full.

**Prediction 2 —** The AI will fail to generate stimulus that reaches the complex corner case of simultaneous reads and writes exactly at the full boundary.
*Evidence that would show it:* The cocotb-coverage report will show a 0% hit rate for the cross coverage of the full flag with simultaneous rd_en and wr_en.

**Review criteria I am checking against:**

1. Constraints keep every transaction legal according to the synchronous FIFO specification.
2. Constraints successfully stress near-full, near-empty, and simultaneous read/write corners.
3. The generated code uses correct pyvsc syntax and integrates cleanly into a layered cocotb environment.


---

## 3. After


**What I ran:**

```bash
just test fifo icarus
just mutate fifo
```

**Raw output:**

```text
python -m craft_mutate.mutate --tb tb/fifo --pool tb/fifo/mutants_released.yaml --sim icarus
[baseline] running clean fifo.sv through fifo ...
  clean RTL: 1 tests passed.

  [found   ] full_offbyone        (test-failed)  -- full asserts one entry too early (cnt == DEPTH-1)
  [found   ] empty_offbyone       (test-failed)  -- empty asserts one entry too early (cnt == 1)
  [SURVIVED] ignore_full          (passed)       -- writes are accepted even when full (overflow)
  [SURVIVED] ignore_empty         (passed)       -- reads are accepted even when empty (underflow)
  [found   ] count_wr_dec         (test-failed)  -- a write-only cycle decrements the count
  [found   ] rd_data_wrptr        (test-failed)  -- rd_data reads from the write pointer instead of the read pointer
  [found   ] mem_corrupt          (test-failed)  -- stored data is corrupted (+1) on write
  [found   ] wrptr_wrap_early     (test-failed)  -- write pointer wraps one slot early

==== found/total = 6/8 = 75.0% (threshold 90%) ====
surviving mutants: ignore_full, ignore_empty
```

**The number:** 6/8, 75% mutation score

**Against each prediction:**

| # | Predicted | Observed | Verdict |
|---|-----------|----------|---------|
| 1 | The AI will generate illegal transactions or fail randomization because the transaction class lacks live FIFO state synchronization. |The AI incorrectly randomized occupancy and caused solver contradictions at boundaries, prevented testing overflow/underflow, leaving 2 mutants surviving. | confirmed |
| 2 | The AI will fail to generate stimulus that reaches complex boundary corner cases (simultaneous read/write at the full boundary). | The distribution successfully caught the off-by-one and pointer-wrap mutants. However, it explicitly blocked simultaneous read/writes at the full boundary to maintain strict legality. | partly |

**Anything I did not predict:** \
1. SystemVerilog-to-Python API Hallucinations: The AI struggled with the specific Python verification library API, mixing it up with SystemVerilog concepts. It imported the wrong module name, treated constrained random fields like standard variables, improperly formatted the distribution weights, and incorrectly nested the distribution function.
2. Every fix made to the AI's output:

     -Corrected the library import statement.

     -Changed the FIFO occupancy tracker from a randomized variable to a state attribute that syncs with the testbench scoreboard before each cycle.

     -Replaced standard Python conditional statements with the library's required conditional constraint blocks.

     -Restructured the weighted distribution block to use the correct API format for the constraint solver.

     -Cast the randomized transaction fields to standard integers before passing them to the physical simulation driver.

---

## 4. Takeaway


**The class of failure (or of success):** Library API hallucination (mixing up hardware verification languages) combined with contradictory prompt requirements that caused solver contradictions.

**Where it connects:** Constrained-Random Verification (CRV) solver satisfiability and Mutation Analysis. Over-constraining the stimulus to generate only "strictly legal" transactions creates observability blind spots, preventing the test from evaluating the FIFO's overflow and underflow protection.

**What I would change in how I framed the request:** Instead of simultaneously asking the AI to keep all transactions strictly legal while also asking it to test illegal over-writes and empty reads, I would explicitly ask for a parameterized constraint mode that allows a small, controlled percentage of illegal boundary transactions.

---

## Disclosure

- [x] Every prompt above is verbatim and complete.
- [x] I have marked every edit I made to the generated output.
- [x] The tool is described by class, not by product name.
- [x] Section 2 was written before the prompt was sent.
