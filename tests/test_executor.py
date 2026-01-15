import unittest
import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from regressionx.domain import Case

try:
    from regressionx.executor import run_case
except ImportError:
    run_case = None

class TestJobExecutor(unittest.TestCase):
    def _make_case_with_dirs(self, name, base_cmd, cand_cmd):
        from pathlib import Path
        import tempfile

        work_dir = tempfile.mkdtemp()
        base_dir = Path(work_dir) / "baseline"
        cand_dir = Path(work_dir) / "candidate"
        case = Case(
            name=name,
            baseline_command=base_cmd,
            candidate_command=cand_cmd,
            base_path=str(base_dir),
            cand_path=str(cand_dir)
        )
        return work_dir, base_dir, cand_dir, case

    def test_run_sandbox_creation_and_execution(self):
        # Arrange
        # We use simple commands that verify CWD or creating a file
        if os.name == 'nt':
            # Windows: 'cd' prints CWD.
            # We want to create a file to prove we are in different dirs?
            # echo "A" > output.txt
            base_cmd = "echo A > output.txt"
            cand_cmd = "echo B > output.txt"
        else:
            base_cmd = "echo A > output.txt"
            cand_cmd = "echo B > output.txt"

        import shutil

        work_dir, base_dir, cand_dir, case = self._make_case_with_dirs(
            "sandbox_test",
            base_cmd,
            cand_cmd
        )
        
        if run_case is None:
             self.fail("Implementation Missing: run_case not found")

        try:
            # Act
            run_case(case)
            
            # Assert
            # 1. Check directories exist
            self.assertTrue(base_dir.exists())
            self.assertTrue(cand_dir.exists())
            
            # 2. Check files created in those directories
            self.assertTrue((base_dir / "output.txt").exists())
            self.assertTrue((cand_dir / "output.txt").exists())
            
            # 3. Check content
            self.assertEqual((base_dir / "output.txt").read_text().strip(), "A")
            self.assertEqual((cand_dir / "output.txt").read_text().strip(), "B")
            
        finally:
            shutil.rmtree(work_dir)

    def test_run_case_baseline_only(self):
        if run_case is None:
             self.fail("Implementation Missing: run_case not found")

        import shutil
        work_dir, base_dir, cand_dir, case = self._make_case_with_dirs(
            "baseline_only",
            "echo BASE > output.txt",
            "echo CAND > output.txt"
        )

        try:
            base_res, cand_res, base_path, cand_path = run_case(
                case,
                run_baseline=True,
                run_candidate=False
            )

            self.assertEqual(base_res.returncode, 0)
            self.assertEqual(cand_res.returncode, 0)
            self.assertTrue((base_dir / "output.txt").exists())
            self.assertFalse((cand_dir / "output.txt").exists())
        finally:
            shutil.rmtree(work_dir)
        
if __name__ == "__main__":
    unittest.main()
