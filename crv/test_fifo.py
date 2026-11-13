"""Project 1 seeded constrained-random regression for the FWFT FIFO.

Transaction + constraints (pyvsc) are in this file.  Environment: tb/ (FifoBench -> driver,
monitor, reference-queue scoreboard).  Ported from HW5 onto the team bench.

Every cycle is checked twice against FifoModel:
  * pre-edge  -- 1 ns after inputs are applied, before the rising edge. Nothing
                 has been clocked, so outputs must still equal the model's
                 current state (catches outputs that leak combinationally from
                 wr_en/rd_en/wr_data).
  * post-edge -- 1 ns after the rising edge (FifoBench's monitor convention).

Run (from crv/):   make SEED=4701 N_CYCLES=5000
"""
import os
import hashlib
import json
import math
import random
from collections import Counter

import cocotb
import vsc
from cocotb.triggers import Timer

from fifo_bench import FifoBench
from fifo_types import FifoTransaction

from fifo_coverage import FifoCoverage

WIDTH = int(os.environ.get("WIDTH", "8"))
DEPTH = int(os.environ.get("DEPTH", "8"))
SEED = int(os.environ.get("SEED", "4701"), 0)
N_CYCLES = int(os.environ.get("N_CYCLES", "5000"))
# restricted is a deliberately weakened diagnostic, never submission signoff.
STIM = os.environ.get("STIM", "biased")
RESET_DENOMINATOR = int(os.environ.get("RESET_DENOMINATOR", "200"))
REQUIRE_CLOSURE = os.environ.get("REQUIRE_CLOSURE", "1") == "1"
if STIM not in ("biased", "restricted") or RESET_DENOMINATOR < 2:
    raise ValueError("Invalid stimulus configuration")
if STIM == "restricted" and REQUIRE_CLOSURE:
    raise ValueError("restricted stimulus must explicitly disable closure for the experiment")

FILL, DRAIN = 0, 1


# ----------------------------------------------------------------------------
# Transaction + constraints
# Every wr_en/rd_en combination is legal per dut/specs/fifo.md (write at full
# is dropped, read at empty is ignored). wr_data is a WIDTH-bit field.
# ----------------------------------------------------------------------------


@vsc.randobj
class FifoTxn:
    def __init__(self, width=8, depth=8):
        self.wr_en = vsc.rand_bit_t(1)
        self.rd_en = vsc.rand_bit_t(1)
        self.wr_data = vsc.rand_bit_t(width)
        self.pattern = vsc.rand_uint8_t()
        self.rst = vsc.rand_bit_t(1)          # rare mid-run reset
        # Non-random state, written by the testbench before each randomize().
        self.count = vsc.uint32_t()
        self.phase = vsc.uint8_t()
        self.write_weight = vsc.uint32_t()
        self.read_weight = vsc.uint32_t()
        self.depth = vsc.uint32_t(i=depth)
        self._mask = (1 << width) - 1
        self._alt_a = int("01" * width, 2) & self._mask
        self._alt_b = int("10" * width, 2) & self._mask

    def configure_state(self, count, phase):
        self.count, self.phase = count, phase
        weights = ((7, 6) if count <= 1 else (6, 7) if count >= int(self.depth) - 1
                   else (9, 3) if phase == FILL else (3, 9))
        self.write_weight, self.read_weight = weights

    @vsc.constraint
    def boundary_bias_c(self):
        # One active dist per field. Guarded dist blocks in the earlier model
        # did not produce their advertised per-rule probabilities in our run.
        vsc.dist(self.wr_en, [vsc.weight(1, self.write_weight),
                             vsc.weight(0, 10 - self.write_weight)])
        vsc.dist(self.rd_en, [vsc.weight(1, self.read_weight),
                             vsc.weight(0, 10 - self.read_weight)])

    @vsc.constraint
    def data_c(self):
        # Explicit categories keep alternating patterns reachable at WIDTH=16.
        vsc.dist(self.pattern, [vsc.weight(0, 1), vsc.weight(1, 1),
                               vsc.weight(2, 1), vsc.weight(3, 1), vsc.weight(4, 6)])
        with vsc.if_then(self.pattern == 0):
            self.wr_data == 0
        with vsc.else_if(self.pattern == 1):
            self.wr_data == self._mask
        with vsc.else_if(self.pattern == 2):
            self.wr_data == self._alt_a
        with vsc.else_if(self.pattern == 3):
            self.wr_data == self._alt_b
        with vsc.else_then:
            self.wr_data != 0
            self.wr_data != self._mask
            self.wr_data != self._alt_a
            self.wr_data != self._alt_b

    @vsc.constraint
    def restricted_requests_c(self):
        # Intentional blind spot for the documented survivor experiment only.
        with vsc.if_then(self.count == 0):
            self.rd_en == 0
        with vsc.if_then(self.count == self.depth):
            self.wr_en == 0

    @vsc.constraint
    def reset_c(self):
        # Rare reset, only when the FIFO holds data (so it actually matters).
        with vsc.if_then(self.count == 0):
            self.rst == 0
        with vsc.else_then:
            vsc.dist(self.rst, [vsc.weight(1, 1),
                                vsc.weight(0, RESET_DENOMINATOR - 1)])


# ----------------------------------------------------------------------------
# Stimulus self-checks + seeded regression
# ----------------------------------------------------------------------------


class StimCoverage:
    """Stimulus self-checks: prove the walk actually reached the corners."""

    def __init__(self, depth=DEPTH):
        self.depth = depth
        self.occupancy = Counter()   # model count seen BEFORE each cycle
        self.events = Counter()
        self.groups = {name: Counter() for name in ("near_empty", "near_full", "fill", "drain")}
        self.patterns = Counter()
        self.reset_eligible = 0

    def record(self, count, wr, rd, rst, phase, pattern):
        group = "near_empty" if count <= 1 else "near_full" if count >= self.depth - 1 else "fill" if phase == FILL else "drain"
        self.groups[group].update(samples=1, writes=wr, reads=rd, resets=rst)
        self.patterns[pattern] += 1
        self.reset_eligible += int(count > 0)
        self.occupancy[count] += 1
        if rst:
            self.events["reset_nonempty"] += 1
            if wr:
                self.events["reset_plus_write"] += 1
            return
        full, empty = count == self.depth, count == 0
        if wr and rd:
            self.events["rw"] += 1
            if 0 < count < self.depth:
                self.events["rw_mid"] += 1
            if full:
                self.events["rw_full"] += 1
            if empty:
                self.events["rw_empty"] += 1
        if wr and full:
            self.events["write_while_full"] += 1
        if rd and empty:
            self.events["read_while_empty"] += 1

    def assert_reached(self, fills, drains):
        for occ in range(self.depth + 1):
            assert self.occupancy[occ] > 0, f"never reached occupancy {occ}"
        for ev in ("rw_mid", "rw_full", "rw_empty",
                   "write_while_full", "read_while_empty"):
            assert self.events[ev] > 0, f"stimulus never produced {ev}"
        assert fills >= 5, f"FIFO only filled {fills} times"
        assert drains >= 5, f"FIFO only drained {drains} times"

    def assert_distribution(self):
        targets = {"near_empty": (0.7, 0.6), "near_full": (0.6, 0.7),
                   "fill": (0.9, 0.3), "drain": (0.3, 0.9)}
        for group, (pw, pr) in targets.items():
            n = self.groups[group]["samples"]
            assert n >= 100, f"insufficient distribution samples for {group}: {n}"
            for key, expected in (("writes", pw), ("reads", pr)):
                observed = self.groups[group][key] / n
                tolerance = 6 * math.sqrt(expected * (1 - expected) / n) + 0.02
                assert abs(observed - expected) <= tolerance, (
                    f"distribution mismatch {group}/{key}: {observed:.3f} vs {expected:.3f}")
        n = sum(self.patterns.values())
        for pattern, expected in enumerate((0.1, 0.1, 0.1, 0.1, 0.6)):
            tolerance = 6 * math.sqrt(expected * (1 - expected) / n) + 0.02
            assert abs(self.patterns[pattern] / n - expected) <= tolerance, "data distribution mismatch"


async def checked_cycle(bench, tx, label):
    """One transaction through the bench with pre- AND post-edge checks."""
    tx = await bench.driver.drive(tx)          # falling edge, pins applied
    await Timer(1, units="ns")
    bench.scoreboard.check(bench.monitor.read_pins(), tx=tx,
                           label=f"{label} [pre-edge]")
    bench.scoreboard.predict(tx)               # model uses pre-edge state
    observed = await bench.monitor.sample()    # rising edge + 1 ns
    bench.scoreboard.check(observed, tx=tx, label=label)
    return observed


@cocotb.test()
async def test_crv_seeded_regression(dut):
    bench = await FifoBench.start(dut, width=WIDTH, depth=DEPTH)
    model = bench.scoreboard.model
    cov = StimCoverage(DEPTH)
    assert len(dut.wr_data) == WIDTH, "RTL WIDTH does not match the scoreboard"
    fcov = FifoCoverage(depth=DEPTH, width=WIDTH)
    fcov.sample_reset(0, 0, initial=True)
    trace = hashlib.sha256()

    random.seed(SEED)                          # pyvsc draws from stdlib random
    txn = FifoTxn(width=WIDTH, depth=DEPTH)
    txn.restricted_requests_c.constraint_mode(STIM == "restricted")
    phase, fills, drains = FILL, 0, 0

    for i in range(N_CYCLES):
        txn.configure_state(model.count, phase)
        txn.randomize()
        wr, rd = int(txn.wr_en), int(txn.rd_en)
        data, rst = int(txn.wr_data), int(txn.rst)
        cov.record(model.count, wr, rd, rst, phase, int(txn.pattern))
        trace.update(json.dumps([model.count, wr, rd, data, rst], separators=(",", ":")).encode())
        trace.update(b"\n")
        occ_pre = model.count

        label = f"seed={SEED} crv#{i}"
        if rst:
            # Synchronous reset with the drawn requests held on the pins:
            # the reset+write security/trust corner (spec defines only the
            # reset outputs, which FifoBench.reset() checks).
            await bench.reset(wr_en=wr, rd_en=rd, wr_data=data)
            fcov.sample_reset(occ_pre, wr)
        else:
            observed = await checked_cycle(bench, FifoTransaction(wr, rd, data), label)
            acc_wr, acc_rd = bench.scoreboard.last_acceptance
            fcov.sample_cycle(occ_pre, wr, rd, data, acc_wr, acc_rd, observed)

        # Sweep direction flips at the boundaries so we fill and drain fully.
        if phase == FILL and model.full:
            phase, fills = DRAIN, fills + 1
        elif phase == DRAIN and model.empty:
            phase, drains = FILL, drains + 1

    # Keep the random-only snapshot separate from the deterministic cleanup.
    random_snapshot = fcov.snapshot()
    drain_cycles = 0
    while not model.empty:
        pre = model.count
        observed = await checked_cycle(bench, FifoTransaction(0, 1, 0), "final drain")
        acc_wr, acc_rd = bench.scoreboard.last_acceptance
        fcov.sample_cycle(pre, 0, 1, 0, acc_wr, acc_rd, observed)
        drain_cycles += 1

    dut._log.info(f"CRV seed={SEED} cycles={N_CYCLES} fills={fills} drains={drains}")
    metadata = {
        "stimulus": STIM, "reset_denominator": RESET_DENOMINATOR,
        "random_cycles": N_CYCLES, "drain_cycles": drain_cycles,
        "random_coverage": {k: random_snapshot[k] for k in ("hit", "total", "holes")},
        "stimulus_sha256": trace.hexdigest(), "fills": fills, "drains": drains,
        "occupancy_counts": dict(cov.occupancy), "events": dict(cov.events),
        "distribution_by_rule": {k: dict(v) for k, v in cov.groups.items()},
        "pattern_counts": dict(cov.patterns), "reset_eligible_cycles": cov.reset_eligible,
    }
    fcov.report(dut._log, SEED, metadata, require_complete=REQUIRE_CLOSURE)
    if REQUIRE_CLOSURE:
        cov.assert_reached(fills, drains)
        cov.assert_distribution()
