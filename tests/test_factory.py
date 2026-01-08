import unittest
import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from regressionx.factory import Template
except ImportError:
    Template = None

class TestTemplateFactory(unittest.TestCase):
    def test_template_generation(self):
        # Arrange
        if Template is None:
            self.fail("Implementation Missing: regressionx.factory.Template not found")
            
        # Define a template for A/B testing
        tmpl = Template(
            baseline_command="old_tool --input {input} --mode {mode}",
            candidate_command="new_tool --input {input} --mode {mode}",
            env={"LOG_LEVEL": "{log_level}"}
        )
        
        data = [
            {"name": "fast_run", "input": "file1.txt", "mode": "fast", "log_level": "INFO"},
            {"name": "slow_run", "input": "file2.txt", "mode": "slow", "log_level": "DEBUG"},
        ]
        
        # Act
        cases = tmpl.generate(data)
        
        # Assert
        self.assertEqual(len(cases), 2)
        
        # Case 1
        self.assertEqual(cases[0].name, "fast_run")
        self.assertEqual(cases[0].baseline_command, "old_tool --input file1.txt --mode fast")
        self.assertEqual(cases[0].candidate_command, "new_tool --input file1.txt --mode fast")
        self.assertEqual(cases[0].env["LOG_LEVEL"], "INFO")
        
        # Case 2
        self.assertEqual(cases[1].name, "slow_run")
        self.assertEqual(cases[1].baseline_command, "old_tool --input file2.txt --mode slow")
        self.assertEqual(cases[1].candidate_command, "new_tool --input file2.txt --mode slow")
        self.assertEqual(cases[1].env["LOG_LEVEL"], "DEBUG")

    def test_missing_keys_raises_error(self):
        # Arrange
        if Template is None:
            self.fail("Implementation Missing")

        tmpl = Template(baseline_command="echo {required}", candidate_command="echo {required}")
        
        # Act & Assert
        with self.assertRaises(KeyError):
            tmpl.generate([{"name": "fail", "other": "value"}])

if __name__ == "__main__":
    unittest.main()
