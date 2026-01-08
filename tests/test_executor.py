import unittest
import subprocess
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

        case = Case(name="sandbox_test", baseline_command=base_cmd, candidate_command=cand_cmd)
        
        if run_case is None:
             self.fail("Implementation Missing: run_case not found")

        # Create a temp workspace
        import tempfile
        import shutil
        from pathlib import Path
        
        work_dir = tempfile.mkdtemp()
        try:
            # Act
            # We expect run_case to take a work_dir argument now
            result = run_case(case, work_root=work_dir)
            
            # Assert
            # 1. Check directories exist
            base_path = Path(work_dir) / case.name / "baseline"
            cand_path = Path(work_dir) / case.name / "candidate"
            
            self.assertTrue(base_path.exists())
            self.assertTrue(cand_path.exists())
            
            # 2. Check files created in those directories
            self.assertTrue((base_path / "output.txt").exists())
            self.assertTrue((cand_path / "output.txt").exists())
            
            # 3. Check content
            self.assertEqual((base_path / "output.txt").read_text().strip(), "A")
            self.assertEqual((cand_path / "output.txt").read_text().strip(), "B")
            
        finally:
            shutil.rmtree(work_dir)
        
if __name__ == "__main__":
    unittest.main()
