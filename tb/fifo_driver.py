"""Driver layer: apply one legal request on the FIFO's falling clock edge."""
from cocotb.triggers import FallingEdge
from fifo_types import FifoTransaction


class FifoDriver:
    def __init__(self, dut, width=8):
        self.dut = dut
        self.width = width

    def validate(self, tx):
        """Reject invalid request encodings instead of silently masking them.

        A read request at empty or a write request at full is SPECIFIED behavior;
        both must be permitted.  Only out-of-range signal values are rejected.
        """
        normalized = FifoTransaction(
            wr_en=int(tx.wr_en),
            rd_en=int(tx.rd_en),
            wr_data=int(tx.wr_data),
        )
        if normalized.wr_en not in (0, 1) or normalized.rd_en not in (0, 1):
            raise ValueError(f"enables must be 0 or 1: {normalized}")
        if not 0 <= normalized.wr_data < (1 << self.width):
            raise ValueError(f"wr_data must fit WIDTH={self.width}: {normalized}")
        return normalized

    async def drive(self, tx):
        """Accept a FifoTransaction or CRV object with matching attribute names."""
        tx = self.validate(tx)
        await FallingEdge(self.dut.clk)
        self.dut.wr_en.value = tx.wr_en
        self.dut.rd_en.value = tx.rd_en
        self.dut.wr_data.value = tx.wr_data
        return tx

    async def cycle(self, wr_en=0, rd_en=0, wr_data=0):
        return await self.drive(FifoTransaction(wr_en, rd_en, wr_data))
