"""Interface-only transaction and observation records for Project 1 FIFO DV.

Only public FIFO signals appear here.  No RTL implementation signals are used.
"""
from dataclasses import dataclass
from typing import Optional


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
    rd_data: Optional[int]  # Not specified, and not checked, when empty=1.
    wr_en: int
    rd_en: int
    wr_data: int
