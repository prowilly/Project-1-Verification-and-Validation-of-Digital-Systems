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
import random
from collections import Counter

import cocotb
import vsc
from cocotb.triggers import Timer

from fifo_bench import FifoBench
from fifo_types import FifoTransaction

try:                                   # functional coverage (coverage/); records only
    from fifo_coverage import FifoCoverage
except ImportError:                    # coverage/ not on the path -> run without it
    FifoCoverage = None

WIDTH = int(os.environ.get("WIDTH", "8"))
DEPTH = int(os.environ.get("DEPTH", "8"))
SEED = int(os.environ.get("SEED", "4701"), 0)
N_CYCLES = int(os.environ.get("N_CYCLES", "5000"))
# STIM=biased (default, graded) | uniform (bias + data constraints OFF; used only
# as the "before" baseline for the coverage convergence argument)
STIM = os.environ.get("STIM", "biased")

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
        self.rst = vsc.rand_bit_t(1)          # rare mid-run reset
        # Non-random state, written by the testbench before each randomize().
        self.count = vsc.uint32_t()
        self.phase = vsc.uint8_t()
        self.depth = vsc.uint32_t(i=depth)
        self._mask = (1 << width) - 1

    @vsc.constraint
    def boundary_bias_c(self):
        with vsc.if_then(self.count <= 1):
            # Near empty: push writes, keep reads common so read-while-empty
            # and r+w-at-empty still happen.
            vsc.dist(self.wr_en, [vsc.weight(1, 7), vsc.weight(0, 3)])
            vsc.dist(self.rd_en, [vsc.weight(1, 6), vsc.weight(0, 4)])
        with vsc.else_if(self.count >= self.depth - 1):
            # Near full: push reads, keep writes common so write-while-full
            # and r+w-at-full still happen.
            vsc.dist(self.wr_en, [vsc.weight(1, 6), vsc.weight(0, 4)])
            vsc.dist(self.rd_en, [vsc.weight(1, 7), vsc.weight(0, 3)])
        with vsc.else_if(self.phase == FILL):
            # Mid-range, sweeping up toward full (r+w still frequent).
            vsc.dist(self.wr_en, [vsc.weight(1, 9), vsc.weight(0, 1)])
            vsc.dist(self.rd_en, [vsc.weight(1, 3), vsc.weight(0, 7)])
        with vsc.else_then:
            # Mid-range, sweeping down toward empty (r+w still frequent).
            vsc.dist(self.wr_en, [vsc.weight(1, 3), vsc.weight(0, 7)])
            vsc.dist(self.rd_en, [vsc.weight(1, 9), vsc.weight(0, 1)])

    @vsc.constraint
    def data_c(self):
        # Corner data values (all-0s / all-1s) so stuck/flipped bits show.
        vsc.dist(self.wr_data, [vsc.weight(0, 1),
                                vsc.weight(self._mask, 1),
                                vsc.weight((1, self._mask - 1), 6)])

    @vsc.constraint
    def reset_c(self):
        # Rare reset, only when the FIFO holds data (so it actually matters).
        with vsc.if_then(self.count == 0):
            self.rst == 0
        with vsc.else_then:
            # 1/200 (tuned from HW5's 1/500): closes the reset coverage bins
            # 2-3x sooner across seeds; see coverage convergence notes.
            vsc.dist(self.rst, [vsc.weight(1, 1), vsc.weight(0, 199)])


# ----------------------------------------------------------------------------
# Stimulus self-checks + seeded regression
# ----------------------------------------------------------------------------


class StimCoverage:
    """Stimulus self-checks: prove the walk actually reached the corners."""

    def __init__(self, depth=DEPTH):
        self.depth = depth
        self.occupancy = Counter()   # model count seen BEFORE each cycle
        self.events = Counter()

    def record(self, count, wr, rd, rst):
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
    fcov = FifoCoverage(depth=DEPTH, width=WIDTH) if FifoCoverage else None

    random.seed(SEED)                          # pyvsc draws from stdlib random
    txn = FifoTxn(width=WIDTH, depth=DEPTH)
    if STIM == "uniform":
        txn.boundary_bias_c.constraint_mode(False)
        txn.data_c.constraint_mode(False)
    phase, fills, drains = FILL, 0, 0

    for i in range(N_CYCLES):
        txn.count = model.count
        txn.phase = phase
        txn.randomize()
        wr, rd = int(txn.wr_en), int(txn.rd_en)
        data, rst = int(txn.wr_data), int(txn.rst)
        cov.record(model.count, wr, rd, rst)
        occ_pre = model.count

        label = f"seed={SEED} crv#{i}"
        if rst:
            # Synchronous reset with the drawn requests held on the pins:
            # the reset+write security/trust corner (spec defines only the
            # reset outputs, which FifoBench.reset() checks).
            await bench.reset(wr_en=wr, rd_en=rd, wr_data=data)
            if fcov:
                fcov.sample_reset(occ_pre, wr)
        else:
            await checked_cycle(bench, FifoTransaction(wr, rd, data), label)
            if fcov:
                acc_wr, acc_rd = bench.scoreboard.last_acceptance
                fcov.sample_cycle(occ_pre, wr, rd, data, acc_wr, acc_rd,
                                  model.count)

        # Sweep direction flips at the boundaries so we fill and drain fully.
        if phase == FILL and model.full:
            phase, fills = DRAIN, fills + 1
        elif phase == DRAIN and model.empty:
            phase, drains = FILL, drains + 1

    # Final drain: every remaining word must come out in order.
    while not model.empty:
        await checked_cycle(bench, FifoTransaction(0, 1, 0), "final drain")

    hist = " ".join(f"{k}:{cov.occupancy[k]}" for k in range(DEPTH + 1))
    dut._log.info(f"CRV seed={SEED} cycles={N_CYCLES} fills={fills} drains={drains}")
    dut._log.info(f"CRV occupancy histogram  {hist}")
    dut._log.info(f"CRV events  {dict(sorted(cov.events.items()))}")
    if fcov:
        fcov.report(dut._log, SEED)            # writes coverage/coverage_report.*
    cov.assert_reached(fills, drains)
