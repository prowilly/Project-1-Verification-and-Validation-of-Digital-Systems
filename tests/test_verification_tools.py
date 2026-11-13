"""Failure-detection tests: a zero shell status must never mask bad JUnit."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('runner', Path(__file__).parents[1] / 'scripts/run_verification.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ResultChecks(unittest.TestCase):
    def check_xml(self, body):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'results.xml'
            path.write_text('<testsuites><testsuite>' + body + '</testsuite></testsuites>')
            return runner.read_results(path)

    def test_assertions_errors_and_skips_are_not_passes(self):
        result = self.check_xml('<testcase/><testcase><failure/></testcase>'
                                '<testcase><error/></testcase><testcase><skipped/></testcase>')
        self.assertEqual(result, {'tests': 4, 'failed': 2, 'skipped': 1})

    def test_missing_and_empty_results_are_errors(self):
        with self.assertRaises(RuntimeError):
            runner.read_results('/nonexistent/project1-results.xml')
        with self.assertRaises(RuntimeError):
            self.check_xml('')

    def test_expected_count_is_enforced(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'results.xml'
            path.write_text('<testsuites><testsuite><testcase/></testsuite></testsuites>')
            with self.assertRaises(RuntimeError):
                runner.read_results(path, expected=5)

    def test_trace_excludes_initial_reset_and_final_drain(self):
        reset = dict(rst_n=0, count=0, wr_en=0, rd_en=0, wr_data=0)
        first = dict(rst_n=1, count=1, wr_en=1, rd_en=0, wr_data=85)
        second = dict(rst_n=1, count=1, wr_en=1, rd_en=1, wr_data=170)
        drain = dict(rst_n=1, count=0, wr_en=0, rd_en=1, wr_data=0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'trace.jsonl'
            path.write_text(''.join(json.dumps(row)+'\n' for row in [reset]*3+[first,second,drain]))
            measured = runner.summarize_trace(path, cycles=2, depth=8)
            self.assertEqual(measured['groups']['near_empty'],
                             dict(draws=2, writes=2, reads=1, resets=0))
            self.assertEqual(measured['occupancy']['0'], 1)
            self.assertEqual(measured['occupancy']['1'], 1)
            self.assertEqual(sum(measured['occupancy'].values()), 2)
            with self.assertRaises(RuntimeError):
                runner.summarize_trace(path, cycles=20, depth=8)
