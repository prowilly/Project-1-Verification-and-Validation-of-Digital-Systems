"""Scoreboard layer: spec-based reference queue and checked FIFO observations.

Uses the provided FifoModel, which was reviewed against dut/specs/fifo.md.
Do not check unspecified rd_data when empty or use RTL pointers/memory.
"""
from models.fifo_model import FifoModel


class FifoScoreboard:
    def __init__(self, width=8, depth=8):
        self.model = FifoModel(width=width, depth=depth)
        self.cycles = 0
        self.last_acceptance = (False, False)

    def reset(self):
        self.model.reset()
        self.last_acceptance = (False, False)

    def predict(self, tx):
        """Apply requests using PRE-edge queue state; return accepted operations.

        This allows the CRV/coverage owner to distinguish requests from accepts.
        """
        self.last_acceptance = self.model.step(tx.wr_en, tx.wr_data, tx.rd_en)
        return self.last_acceptance

    def check(self, observed, tx=None, label=""):
        self.cycles += 1
        info = (
            f"cycle={self.cycles}, case={label}, tx={tx}, "
            f"expected_queue={list(self.model.q)}, observed={observed}"
        )
        assert 0 <= observed.count <= self.model.depth, "out-of-range count: " + info
        assert observed.count == self.model.count, "count mismatch: " + info
        assert observed.full == int(self.model.full), "full mismatch: " + info
        assert observed.empty == int(self.model.empty), "empty mismatch: " + info
        if not self.model.empty:
            assert observed.rd_data == self.model.head, "FWFT head mismatch: " + info
        if tx is not None:
            assert observed.wr_en == tx.wr_en, "write-enable pin mismatch: " + info
            assert observed.rd_en == tx.rd_en, "read-enable pin mismatch: " + info
            assert observed.wr_data == tx.wr_data, "write-data pin mismatch: " + info
