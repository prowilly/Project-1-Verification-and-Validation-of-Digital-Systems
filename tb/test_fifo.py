"""Homework 4: layered, model-based verification of the synchronous FWFT FIFO.

Run from code/:  just test fifo
                  just mutate fifo

The driver drives on falling edges.  The scoreboard advances FifoModel using
pre-rising-edge requests, and the monitor samples settled outputs 1 ns after
the rising edge.  Model checks are independent of DUT implementation signals.
"""

from dataclasses import dataclass
import random
from typing import Optional

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from models.fifo_model import FifoModel


WIDTH = 8
DEPTH = 8
CLOCK_NS = 10
SEED = 0x4701


@dataclass(frozen=True)
class FifoTransaction:
    wr_en: int = 0
    rd_en: int = 0
    wr_data: int = 0


@dataclass(frozen=True)
class FifoObservation:
    count: int
    full: int
    empty: int
    rd_data: Optional[int]
    wr_en: int
    rd_en: int
    wr_data: int


class FifoDriver:
    """Translate a transaction into DUT inputs, driven at a falling edge."""

    def __init__(self, dut):
        self.dut = dut

    async def cycle(self, wr_en=0, rd_en=0, wr_data=0):
        tx = FifoTransaction(int(bool(wr_en)), int(bool(rd_en)), wr_data & ((1 << WIDTH) - 1))
        await FallingEdge(self.dut.clk)
        self.dut.wr_en.value = tx.wr_en
        self.dut.rd_en.value = tx.rd_en
        self.dut.wr_data.value = tx.wr_data
        return tx


class FifoMonitor:
    """Observe interface pins, not the FIFO's internal pointers or memory."""

    def __init__(self, dut):
        self.dut = dut

    def read_pins(self):
        count = int(self.dut.count.value)
        full = int(self.dut.full.value)
        empty = int(self.dut.empty.value)
        # rd_data is not specified when empty and may be X in Icarus.
        head = int(self.dut.rd_data.value) if not empty else None
        return FifoObservation(
            count=count,
            full=full,
            empty=empty,
            rd_data=head,
            wr_en=int(self.dut.wr_en.value),
            rd_en=int(self.dut.rd_en.value),
            wr_data=int(self.dut.wr_data.value),
        )

    async def sample(self):
        await RisingEdge(self.dut.clk)
        await Timer(1, units="ns")  # wait for sequential updates and FWFT settle
        return self.read_pins()


class FifoScoreboard:
    """Advance the course's oracle pre-edge; check *all* valid outputs post-edge."""

    def __init__(self):
        self.model = FifoModel(WIDTH, DEPTH)
        self.cycles = 0

    def reset(self):
        self.model.reset()

    def predict(self, tx):
        # FifoModel gates read/write with pre-edge full and empty states.
        self.model.step(tx.wr_en, tx.wr_data, tx.rd_en)

    def check(self, observed, tx=None, label=""):
        self.cycles += 1
        info = (
            f"cycle={self.cycles}, case={label}, tx={tx}, "
            f"expected_queue={list(self.model.q)}, observed={observed}"
        )
        assert observed.count == self.model.count, "count mismatch: " + info
        assert observed.full == int(self.model.full), "full mismatch: " + info
        assert observed.empty == int(self.model.empty), "empty mismatch: " + info
        if not self.model.empty:
            assert observed.rd_data == self.model.head, "FWFT head mismatch: " + info
        if tx is not None:
            assert observed.wr_en == tx.wr_en, "write-enable pin mismatch: " + info
            assert observed.rd_en == tx.rd_en, "read-enable pin mismatch: " + info
            assert observed.wr_data == tx.wr_data, "write-data pin mismatch: " + info


class FifoBench:
    """Reusable transaction-level glue connecting the three independent parts."""

    def __init__(self, dut):
        self.dut = dut
        self.driver = FifoDriver(dut)
        self.monitor = FifoMonitor(dut)
        self.scoreboard = FifoScoreboard()

    @classmethod
    async def start(cls, dut):
        bench = cls(dut)
        dut.rst_n.value = 0
        dut.wr_en.value = 0
        dut.rd_en.value = 0
        dut.wr_data.value = 0
        cocotb.start_soon(Clock(dut.clk, CLOCK_NS, units="ns").start())
        # Check the reset state after *each* of three rising edges.
        for i in range(3):
            obs = await bench.monitor.sample()
            bench.scoreboard.reset()
            bench.scoreboard.check(obs, label=f"initial reset {i}")
        dut.rst_n.value = 1
        return bench

    async def reset(self):
        """Exercise active-low synchronous reset even when data is queued."""
        await FallingEdge(self.dut.clk)
        self.dut.wr_en.value = 0
        self.dut.rd_en.value = 0
        self.dut.wr_data.value = 0
        self.dut.rst_n.value = 0
        obs = await self.monitor.sample()
        self.scoreboard.reset()
        self.scoreboard.check(obs, label="midstream synchronous reset")
        self.dut.rst_n.value = 1

    async def cycle(self, wr_en=0, rd_en=0, wr_data=0, label=""):
        tx = await self.driver.cycle(wr_en, rd_en, wr_data)
        self.scoreboard.predict(tx)  # must happen BEFORE the rising edge
        obs = await self.monitor.sample()
        self.scoreboard.check(obs, tx=tx, label=label)
        return obs

    async def fill(self, values):
        for value in values:
            await self.cycle(wr_en=1, wr_data=value, label="fill")

    async def drain(self):
        while not self.scoreboard.model.empty:
            await self.cycle(rd_en=1, label="drain / check FIFO order")


@cocotb.test()
async def test_fifo_directed_corners(dut):
    tb = await FifoBench.start(dut)

    # Underflow: read-only at empty is ignored. At empty, simultaneous r+w
    # accepts the write but cannot read the previously empty queue.
    await tb.cycle(rd_en=1, label="read while empty")
    await tb.cycle(rd_en=1, label="repeat empty read")
    await tb.cycle(wr_en=1, rd_en=1, wr_data=0xD3,
                   label="simultaneous at empty: only write is accepted")
    assert tb.scoreboard.model.count == 1
    await tb.cycle(rd_en=1, label="drain only item")
    assert tb.scoreboard.model.empty

    # Filling, overflow rejection, and full-boundary simultaneous operation.
    await tb.fill([0x00, 0x10, 0x55, 0x80, 0xFE, 0x7A, 0x22, 0xFF])
    assert tb.scoreboard.model.full
    await tb.cycle(label="idle while full")
    await tb.cycle(wr_en=1, wr_data=0xAA, label="write while full: dropped")
    await tb.cycle(wr_en=1, wr_data=0xBE, label="second rejected overflow")
    assert tb.scoreboard.model.count == DEPTH
    await tb.cycle(wr_en=1, rd_en=1, wr_data=0xAC,
                   label="simultaneous at full: read only, write dropped")
    assert tb.scoreboard.model.count == DEPTH - 1
    await tb.cycle(wr_en=1, wr_data=0x36, label="refill last slot")
    assert tb.scoreboard.model.full
    await tb.drain()
    assert tb.scoreboard.model.empty
    await tb.cycle(rd_en=1, label="over-read after complete drain")

    # At occupancy one, simultaneous r+w must replace the FWFT head now,
    # without a bubble, and without changing count.
    await tb.cycle(wr_en=1, wr_data=0x35, label="single entry")
    for data in (0xC1, 0x00, 0xFF, 0x72, 0x9B):
        await tb.cycle(wr_en=1, rd_en=1, wr_data=data,
                       label="simultaneous r+w at count one")
        assert tb.scoreboard.model.count == 1
    await tb.drain()

    # Simultaneous traffic in an interior occupancy, with nonidentical data.
    await tb.fill([0x14, 0x28, 0x3C, 0x50])
    for data in (0x64, 0x78, 0x8C, 0xA0, 0xB4):
        await tb.cycle(wr_en=1, rd_en=1, wr_data=data,
                       label="simultaneous r+w in interior")
        assert tb.scoreboard.model.count == 4
    await tb.drain()
    dut._log.info("Directed FIFO boundary tests and ordering checks passed")


@cocotb.test()
async def test_fifo_pointer_wrap_and_reset(dut):
    tb = await FifoBench.start(dut)

    # Maintaining count==DEPTH-1 ensures every simultaneous operation is
    # accepted; >4 complete revolutions of both read and write pointers.
    await tb.fill([0x30 + i for i in range(DEPTH - 1)])
    for i in range(4 * DEPTH + 9):
        await tb.cycle(wr_en=1, rd_en=1, wr_data=(i * 37 + 0x91) & 0xFF,
                       label="pointer wrap under simultaneous traffic")
        assert tb.scoreboard.model.count == DEPTH - 1
    await tb.drain()

    # Repeated full-depth fill/drain rounds wrap pointers even without overlap.
    for round_number in range(4):
        await tb.fill([((round_number << 5) ^ (i * 29)) & 0xFF
                       for i in range(DEPTH)])
        assert tb.scoreboard.model.full
        await tb.drain()
        assert tb.scoreboard.model.empty

    # A nonempty reset must flush state and restart pointers consistently.
    await tb.fill([0xDE, 0xAD, 0xBE, 0xEF, 0x42])
    await tb.reset()
    assert tb.scoreboard.model.empty
    await tb.fill([0x01, 0x02, 0x04, 0x08])
    await tb.drain()
    dut._log.info("Pointer wrap and midstream reset checks passed")


@cocotb.test()
async def test_fifo_seeded_random_interleave(dut):
    tb = await FifoBench.start(dut)
    rng = random.Random(SEED)

    # Bias toward full, then empty, then overlap, followed by mixed traffic.
    # This reliably reaches boundaries while preserving varied data ordering.
    phases = (
        (240, 0.80, 0.25, "write-biased random"),
        (240, 0.25, 0.80, "read-biased random"),
        (320, 0.80, 0.80, "overlap-biased random"),
        (400, 0.50, 0.50, "balanced random"),
    )
    for cycles, write_probability, read_probability, label in phases:
        for _ in range(cycles):
            wr_en = int(rng.random() < write_probability)
            rd_en = int(rng.random() < read_probability)
            wr_data = rng.getrandbits(WIDTH)
            await tb.cycle(wr_en, rd_en, wr_data, label=label)

    # Flush all surviving values: exposes latent data/order corruption.
    await tb.drain()
    await tb.cycle(rd_en=1, label="post-random empty read")
    dut._log.info("1,200 seeded randomized FIFO transactions passed; seed=%#x", SEED)
