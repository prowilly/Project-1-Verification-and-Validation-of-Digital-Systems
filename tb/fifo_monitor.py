"""Monitor layer: sample public FIFO pins after rising-edge state updates."""
from cocotb.triggers import RisingEdge, Timer
from fifo_types import FifoObservation


class FifoMonitor:
    def __init__(self, dut):
        self.dut = dut

    def _known(self, name):
        value = getattr(self.dut, name).value
        assert value.is_resolvable, f"Unresolved required FIFO output/input: {name}={value}"
        return int(value)

    def read_pins(self):
        count = self._known("count")
        full = self._known("full")
        empty = self._known("empty")
        # The written specification promises a valid FWFT head only if !empty.
        head = self._known("rd_data") if not empty else None
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
