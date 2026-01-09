import unittest
import tempfile
import textwrap
import os
import sys

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from regressionx.domain import Case
# This import is expected to fail initially or the function to be missing
try:
    from regressionx.config import load_config
except ImportError:
    load_config = None

class TestConfigLoader(unittest.TestCase):
    def test_can_load_simple_python_config(self):
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            f.write(textwrap.dedent("""
                from regressionx.domain import Case
                
                cases = [
                    Case(name="test_1", baseline_command="echo 1a", candidate_command="echo 1b", base_path="/tmp/a1", cand_path="/tmp/b1"),
                    Case(name="test_2", baseline_command="echo 2a", candidate_command="echo 2b", base_path="/tmp/a2", cand_path="/tmp/b2"),
                ]
            """))
            config_path = f.name
        
        try:
            # Act
            if load_config is None:
                self.fail("Implementation Missing: load_config could not be imported")
            
            cases = load_config(config_path)
            
            # Assert
            self.assertEqual(len(cases), 2)
            self.assertEqual(cases[0].name, "test_1")
            self.assertEqual(cases[0].baseline_command, "echo 1a")
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)

if __name__ == "__main__":
    unittest.main()
