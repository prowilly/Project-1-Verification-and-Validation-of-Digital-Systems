"""Independent corner sequences for temporal reset/wrap coverage semantics."""
import sys
import os
import tempfile
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'coverage'))
from fifo_coverage import FifoCoverage, coverage_db


class CoverageChecks(unittest.TestCase):
    def test_temporal_events_and_boundary_acceptance(self):
        c = FifoCoverage()
        count = 0

        def step(wr, rd, data=0x55):
            nonlocal count
            pre = count
            aw, ar = bool(wr and pre < 8), bool(rd and pre > 0)
            count += int(aw) - int(ar)
            observation = SimpleNamespace(count=count, full=int(count == 8), empty=int(count == 0))
            c.sample_cycle(pre, wr, rd, data, aw, ar, observation)

        c.sample_reset(0, 0, initial=True)
        step(0, 1)  # defined empty read; must not count as recovery
        self.assertEqual(coverage_db['fifo.reset_x_first_accept'].coverage, 0)
        step(1, 1)  # empty boundary accepts write only
        self.assertEqual(coverage_db['fifo.reset_x_first_accept'].coverage, 1)
        step(1, 1)  # one-entry replacement
        hits = coverage_db['fifo.occ_x_head'].detailed_coverage
        self.assertGreater(hits[('empty', 'first_write_from_empty')], 0)
        self.assertGreater(hits[('one', 'simultaneous_replaces_one_entry')], 0)
        # Repeated accepted overlap at occupancy one advances both logical
        # indices; they wrap on adjacent edges, never on the same edge.
        for _ in range(16):
            step(1, 1)
        wraps = coverage_db['fifo.pointer_wrap'].detailed_coverage
        self.assertGreater(wraps['write_wrap'], 0)
        self.assertGreater(wraps['read_wrap'], 0)
        self.assertEqual(wraps['both_wrapped'], 1)
        c.sample_reset(count, 1)
        count = 0
        self.assertEqual((c.wr_total, c.rd_total, c.both_wrapped), (0, 0, False))
        step(0, 0)
        self.assertEqual(coverage_db['fifo.reset_x_first_accept'].coverage, 1)
        step(1, 0)
        self.assertEqual(coverage_db['fifo.reset_x_first_accept'].coverage, 2)
        self.assertEqual(coverage_db['fifo.reset_scenario'].coverage, 3)
        # Reject an impossible acceptance rather than awarding coverage credit.
        with self.assertRaises(AssertionError):
            c.sample_cycle(0, 0, 1, 0, False, True, SimpleNamespace(count=0, full=0, empty=1))
        self.assertTrue(c.snapshot()['holes'])  # the short sequence is not closure
        with tempfile.TemporaryDirectory() as output, patch.dict(os.environ, {"COVERAGE_DIR": output}):
            with self.assertRaisesRegex(AssertionError, "coverage target not reached"):
                c.report(SimpleNamespace(info=lambda message: None), 4701, {}, require_complete=True)
