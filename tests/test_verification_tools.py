"""Failure-detection tests: a zero shell status must never mask bad JUnit."""
import importlib.util
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
