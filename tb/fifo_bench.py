"""Top-level layered FIFO environment shared with the CRV/coverage workstream.

Stable interface for Teammate 2:
    bench = await FifoBench.start(dut)
    before = bench.scoreboard.model.count  # pre-edge occupancy
    obs = await bench.apply(transaction, label="CRV")
    accepted_write, accepted_read = bench.scoreboard.last_acceptance

The driver validates input legality; the scoreboard predicts pre-edge accepts;
the monitor observes the settled post-edge interface and checks all valid pins.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from fifo_types import FifoTransaction
from fifo_driver import FifoDriver
from fifo_monitor import FifoMonitor
from fifo_scoreboard import FifoScoreboard

CLOCK_NS = 10


class FifoBench:
    def __init__(self, dut, width=8, depth=8):
        self.dut = dut
        self.width = width
        self.depth = depth
        self.driver = FifoDriver(dut, width=width)
        self.monitor = FifoMonitor(dut)
        self.scoreboard = FifoScoreboard(width=width, depth=depth)

    @classmethod
    async def start(cls, dut, width=8, depth=8):
        bench = cls(dut, width=width, depth=depth)
        dut.rst_n.value = 0
        dut.wr_en.value = 0
        dut.rd_en.value = 0
        dut.wr_data.value = 0
        cocotb.start_soon(Clock(dut.clk, CLOCK_NS, units="ns").start())
        for i in range(3):
            obs = await bench.monitor.sample()
            bench.scoreboard.reset()
            bench.scoreboard.check(obs, label=f"initial synchronous reset {i}")
        dut.rst_n.value = 1
        return bench

    async def reset(self, wr_en=0, rd_en=0, wr_data=0):
        """Prove reset is synchronous; optionally coincide reset with requests.

        Before the resetting edge, queue/flags must remain unchanged.  After
        that edge, only the specified reset outputs are checked; no write/read
        acceptance is inferred for the underspecified reset+request overlap.
        """
        tx = self.driver.validate(FifoTransaction(wr_en, rd_en, wr_data))
        await FallingEdge(self.dut.clk)
        self.dut.wr_en.value = tx.wr_en
        self.dut.rd_en.value = tx.rd_en
        self.dut.wr_data.value = tx.wr_data
        self.dut.rst_n.value = 0
        await Timer(1, units="ns")  # Still 4 ns before next rising edge.
        before_edge = self.monitor.read_pins()
        self.scoreboard.check(before_edge, label="reset asserted before rising edge")
        after_edge = await self.monitor.sample()
        self.scoreboard.reset()
        self.scoreboard.check(after_edge, label="synchronous reset edge")
        self.dut.rst_n.value = 1
        return after_edge

    async def apply(self, tx, label=""):
        """Common entry point for the HW4 directed tests and the future pyvsc CRV."""
        tx = await self.driver.drive(tx)
        self.scoreboard.predict(tx)  # MUST precede rising edge.
        observed = await self.monitor.sample()
        self.scoreboard.check(observed, tx=tx, label=label)
        return observed

    async def cycle(self, wr_en=0, rd_en=0, wr_data=0, label=""):
        return await self.apply(FifoTransaction(wr_en, rd_en, wr_data), label)

    async def fill(self, values):
        for value in values:
            await self.cycle(wr_en=1, wr_data=value, label="fill")

    async def drain(self):
        while not self.scoreboard.model.empty:
            await self.cycle(rd_en=1, label="drain / check FIFO order")
