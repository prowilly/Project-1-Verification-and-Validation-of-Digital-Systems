"""Monitor layer: sample public FIFO pins after rising-edge state updates."""
from cocotb.triggers import RisingEdge, Timer
from fifo_types import FifoObservation


class FifoMonitor:
    def __init__(self, dut):
        self.dut = dut

    def read_pins(self):
        count = int(self.dut.count.value)
        full = int(self.dut.full.value)
        empty = int(self.dut.empty.value)
        # The written specification promises a valid FWFT head only if !empty.
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
        await Timer(1, units="ns")  # Existing HW4/CRAFT sampling convention.
        return self.read_pins()
