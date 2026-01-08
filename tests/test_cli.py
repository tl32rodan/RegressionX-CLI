import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from regressionx import cli
except ImportError:
    cli = None

from regressionx.domain import Case

class TestCLI(unittest.TestCase):
    def setUp(self):
        if cli is None:
            self.fail("Implementation Missing: regressionx.cli module not found")

    @patch('regressionx.cli.run_case')
    @patch('regressionx.cli.load_config')
    @patch('regressionx.cli.compare_directories')
    def test_run_command_loads_config_and_runs_cases(self, mock_compare, mock_load, mock_run):
        # Arrange
        mock_load.return_value = [
            Case(name="c1", baseline_command="echo 1a", candidate_command="echo 1b"),
            Case(name="c2", baseline_command="echo 2a", candidate_command="echo 2b")
        ]
        mock_run.return_value = (
            type('obj', (object,), {'returncode': 0}),
            type('obj', (object,), {'returncode': 0}),
            Path("/tmp/a"), Path("/tmp/b")
        )
        # Mock successful comparison
        mock_compare.return_value.match = True
        mock_compare.return_value.errors = []
        mock_compare.return_value.diffs = []

        # Act
        original_argv = sys.argv
        sys.argv = ["regressionx", "run", "--config", "dummy_config.py"]
        try:
            cli.main()
        finally:
            sys.argv = original_argv

        # Assert
        self.assertEqual(mock_load.call_count, 1)
        self.assertEqual(mock_run.call_count, 2)

        # Check that work_root was passed
        args, kwargs = mock_run.call_args
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0].name, "c2")
        self.assertTrue(isinstance(args[1], str)) # work_root

    @patch('sys.stderr', new_callable=MagicMock)
    def test_missing_config_arg_prints_usage(self, mock_stderr):
        # Arrange
        # Act
        with self.assertRaises(SystemExit) as cm:
             cli.main(["run"]) # Missing --config

        # Assert
        self.assertNotEqual(cm.exception.code, 0)

if __name__ == "__main__":
    unittest.main()
