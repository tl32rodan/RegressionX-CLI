import unittest
import tempfile
import os
import shutil
from dataclasses import dataclass
from regressionx.domain import Case

# Define mocks for results if real ones are too complex to import
@dataclass
class MockProcess:
    returncode: int
    stdout: str = ""
    stderr: str = ""

@dataclass
class MockCmpResult:
    match: bool
    errors: list
    diffs: list

try:
    from regressionx.reporter import MarkdownReporter
except ImportError:
    MarkdownReporter = None

class TestMarkdownReporter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.report_path = os.path.join(self.test_dir, "report.md")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_generate_report(self):
        if MarkdownReporter is None:
            self.fail("Implementation Missing")

        reporter = MarkdownReporter(self.report_path)
        
        # Add a passing case
        case1 = Case(name="case_pass", baseline_command="echo a", candidate_command="echo b", base_path="/tmp/a1", cand_path="/tmp/b1")
        reporter.add_result(
            case=case1,
            base_res=MockProcess(0),
            cand_res=MockProcess(0),
            cmp_result=MockCmpResult(True, [], [])
        )
        
        # Add a failing case (Mismatch)
        case2 = Case(name="case_fail", baseline_command="echo a", candidate_command="echo b", base_path="/tmp/a2", cand_path="/tmp/b2")
        reporter.add_result(
            case=case2,
            base_res=MockProcess(0),
            cand_res=MockProcess(0),
            cmp_result=MockCmpResult(False, [], ["Content Mismatch"])
        )
        
        # Generate
        reporter.generate()
        
        # Verify
        self.assertTrue(os.path.exists(self.report_path))
        with open(self.report_path, "r", encoding="utf-8") as report_file:
            content = report_file.read()
        
        # Check for Markdown syntax
        self.assertIn("# RegressionX Report", content)
        self.assertIn("| case_pass | PASSED |", content)
        self.assertIn("| case_fail | FAILED |", content)
        self.assertIn("- [Content] Content Mismatch", content)

if __name__ == "__main__":
    unittest.main()
