# FINDINGS — Homework 4: A Testbench With Parts

> Verification and Validation of Digital Systems (EEE 4701)
> William Garland
> These results come from the actual Eustis/Icarus runs. Detection on the released pool does not establish detection on the hidden pool or prove the FIFO is free from all defects.

## Score

|Pool|found|total|%|
|-|-:|-:|-:|
|released (practice), final suite|**8**|**8**|**100.0%**|
|hidden (reported at grading)|Not available|10|Not available|

The final suite exceeded the released-pool threshold of 90%. The hidden-pool result is not yet known.

**Commands run from `code/` on Eustis:**

```bash
source /opt/course/cocotb-env/bin/activate
just test fifo icarus
just mutate fifo
```

**Verified baseline simulation result:** `TESTS=3 PASS=3 FAIL=0 SKIP=0` under Icarus Verilog 12.0 and cocotb 1.9.2:

* `test\_fifo\_directed\_corners` — PASS
* `test\_fifo\_pointer\_wrap\_and\_reset` — PASS
* `test\_fifo\_seeded\_random\_interleave` — PASS (1,200 transactions; seed `0x4701`)

**Verified released mutation result:**

```text
\[baseline] running clean fifo.sv through fifo ...
  clean RTL: 3 tests passed.

  \[found  ] full\_offbyone        (test-failed)
  \[found  ] empty\_offbyone       (test-failed)
  \[found  ] ignore\_full          (test-failed)
  \[found  ] ignore\_empty         (test-failed)
  \[found  ] count\_wr\_dec         (test-failed)
  \[found  ] rd\_data\_wrptr        (test-failed)
  \[found  ] mem\_corrupt          (test-failed)
  \[found  ] wrptr\_wrap\_early     (test-failed)

==== found/total = 8/8  =  100.0%  (threshold 90%) ====
```

Note: the default `just test fifo` used Verilator and stopped before simulation because it treated an existing RTL width-expansion warning on `cnt == DEPTH` as fatal. The explicitly selected Icarus run above completed successfully; `just mutate fifo` also used Icarus.

## Corner-case checklist

|Corner|Stimulus included|Expected behavior and check|
|-|-|-|
|Full|Eight distinct writes into an empty depth-8 FIFO|`count == 8`, `full == 1`, `empty == 0`, and ordered FWFT head|
|Empty|Drain to zero, then repeat reads|`count == 0`, `empty == 1`, `full == 0`; empty reads do not underflow|
|Write-while-full|Attempt two additional writes at occupancy 8|Both writes are dropped; occupancy and queued data stay correct|
|Read-while-empty|Assert `rd\_en` when occupancy is zero|Read is ignored; flags and count remain correct|
|Simultaneous read+write|Assert both enables at occupancy 1 and 4, and also at 0 and 8|Interior occupancy leaves count unchanged and advances the head; empty accepts only the write and full accepts only the read|
|Pointer wrap|More than four revolutions at occupancy 7 and four complete fill/drain rounds|FIFO contents, occupancy, and head remain correct through wrap-around|
|Synchronous reset (additional check)|Assert active-low reset with five entries queued|FIFO returns to empty state and accepts subsequent transactions correctly|
|Seeded random interleave|1,200 cycles with `random.Random(0x4701)` and varied enable/data patterns|Check count, flags, and valid FWFT head every cycle; drain the remainder|

**Architecture and timing:** `FifoDriver.cycle()` drives transactions on falling edges. `FifoScoreboard` updates the supplied `FifoModel(8, 8)` from pre-rising-edge requests. `FifoMonitor.sample()` reads outputs 1 ns after the rising edge, after sequential updates have settled. The scoreboard checks `count`, `full`, and `empty` on every cycle and `rd\_data` whenever the model is nonempty; it does not assert an unspecified value for `rd\_data` while empty. Driver, monitor, and scoreboard are separate, reusable classes.

## Survivors

**Released pool: none.** All eight mutants were found in the final Eustis run.

|Mutant|What it changes|Result|Detecting stimulus / observable check|
|-|-|-|-|
|`full\_offbyone`|Asserts full at `DEPTH-1`|Found|Reach occupancy 7/8; check `full` and count|
|`empty\_offbyone`|Asserts empty at count 1|Found|Reach occupancy 1/0; check `empty` and valid head|
|`ignore\_full`|Accepts writes despite full|Found|Attempt writes while full; verify count and queued order|
|`ignore\_empty`|Accepts reads despite empty|Found|Attempt reads while empty; verify no underflow|
|`count\_wr\_dec`|Decrements count on write-only cycles|Found|Perform write-only transactions; verify model occupancy|
|`rd\_data\_wrptr`|Reads from write pointer instead of read pointer|Found|Queue distinct values; compare FWFT head with model|
|`mem\_corrupt`|Adds one to a stored byte on write|Found|Read accepted values back through FWFT head checks|
|`wrptr\_wrap\_early`|Wraps write pointer one location early|Found|Repeated wraps and distinct byte patterns; verify FIFO order|

**Last mutant caught:** The last mutant listed as found in the released-pool report is `wrptr\_wrap\_early`. The suite drives write-pointer wrap-around repeatedly and compares the resulting FIFO head and occupancy to the reference queue. An early write-pointer wrap can overwrite or misplace a queued value, making the model-vs-DUT comparison fail. The command output establishes that the mutant was found, but does not identify the precise first failing assertion.

## What I changed, and what it bought

|Change|Score before|Score after|Which survivors it caught|
|-|-:|-:|-|
|Replaced the starter's three-write/count-only smoke test with the layered driver / monitor / `FifoModel` scoreboard, directed corner cases, repeated wraps, reset testing, and 1,200 seeded random transactions|**1/8 (12.5%)**|**8/8 (100.0%)**|The seven starter survivors: `full\_offbyone`, `empty\_offbyone`, `ignore\_full`, `ignore\_empty`, `rd\_data\_wrptr`, `mem\_corrupt`, `wrptr\_wrap\_early`|

The initial Eustis run used the original one-test starter and found only `count\_wr\_dec`. After installing the new testbench, all three baseline tests passed and all eight released mutants were found. Because the improvements were installed together, the run establishes the *combined* improvement, not an independently measured score for each testbench change.

## Residual risk

1. **Reachability gap — alternate parameters.** The suite runs the default width-8, depth-8 FIFO. Faults specific to other supported widths or depths, especially non-power-of-two depths and their rollover behavior, are not exercised. A parameter sweep with an independent model would reduce this risk.
2. **Observability gap — unspecified empty-state data.** The specification makes `rd\_data` meaningful only while `empty` is false. The scoreboard therefore intentionally does not check the data bus in the empty state. Changes visible only on that unspecified output can survive without violating the stated contract.
3. **Observability gap — transient behavior.** The monitor samples after each rising edge plus 1 ns. A short glitch that disappears before the sample would not be seen. Extra timing assertions or intermediate observations would be needed if glitch freedom is a requirement.
4. **Reachability gap — other unmodeled situations.** A finite set of directed and 1,200 pseudo-random cycles may miss rare long-history or unusual reset/enables interleavings, even with 100% detection on this particular released pool.

**If I had another day:** I would add a parameterized depth/width test sweep, particularly a non-power-of-two depth, to exercise rollover logic that the current depth-8 suite cannot reach. I would also use the hidden grading feedback, if supplied later, to identify whether remaining issues require new stimulus (reachability) or additional checks (observability).



\## AI Disclosure



OpenAI's ChatGPT was used to assist in completing Homework 4, including developing the layered cocotb FIFO testbench, implementing the driver, monitor, and scoreboard, generating directed and randomized test cases, and preparing the FINDINGS.md documentation.



ChatGPT also provided guidance for configuring the Eustis environment, executing simulation and mutation tests, and interpreting the results. The testbench was executed on UCF's Eustis server using Icarus Verilog, where all three tests passed and all eight released mutants were successfully detected (8/8, 100%). The findings reported are based on actual simulation results rather than AI-generated estimates.



AI assistance was used for code development, documentation, troubleshooting, and result interpretation. Responsibility for the final submission and its accuracy remains with me.

