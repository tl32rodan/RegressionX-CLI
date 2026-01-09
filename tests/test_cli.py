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

    def _make_case(self, name):
        return Case(
            name=name,
            baseline_command=f"echo {name}a",
            candidate_command=f"echo {name}b",
            base_path=f"/tmp/{name}/baseline",
            cand_path=f"/tmp/{name}/candidate"
        )

    def _set_compare_ok(self, mock_compare):
        mock_compare.return_value.match = True
        mock_compare.return_value.errors = []
        mock_compare.return_value.diffs = []

    @patch('regressionx.cli.run_case')
    @patch('regressionx.cli.load_config')
    @patch('regressionx.cli.compare_directories')
    def test_run_command_loads_config_and_runs_cases(self, mock_compare, mock_load, mock_run):
        # Arrange
        mock_load.return_value = [
            self._make_case("c1"),
            self._make_case("c2")
        ]
        mock_run.return_value = (
            type('obj', (object,), {'returncode': 0}),
            type('obj', (object,), {'returncode': 0}),
            Path("/tmp/a"), Path("/tmp/b")
        )
        # Mock successful comparison
        self._set_compare_ok(mock_compare)

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

        # Check call args
        args, kwargs = mock_run.call_args
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, "c2")

    @patch('regressionx.cli.run_case')
    @patch('regressionx.cli.load_config')
    @patch('regressionx.cli.compare_directories')
    def test_compare_command_only_compares(self, mock_compare, mock_load, mock_run):
        mock_load.return_value = [
            self._make_case("c1")
        ]
        self._set_compare_ok(mock_compare)

        cli.main(["compare", "--config", "dummy_config.py"])

        self.assertEqual(mock_run.call_count, 0)
        self.assertEqual(mock_compare.call_count, 1)

    @patch('regressionx.cli.run_case')
    @patch('regressionx.cli.load_config')
    @patch('regressionx.cli.compare_directories')
    def test_run_base_command_runs_baseline_only(self, mock_compare, mock_load, mock_run):
        mock_load.return_value = [
            self._make_case("c1")
        ]
        mock_run.return_value = (
            type('obj', (object,), {'returncode': 0}),
            type('obj', (object,), {'returncode': 0}),
            Path("/tmp/a"), Path("/tmp/b")
        )
        self._set_compare_ok(mock_compare)

        cli.main(["run_base", "--config", "dummy_config.py"])

        args, kwargs = mock_run.call_args
        self.assertEqual(kwargs["run_baseline"], True)
        self.assertEqual(kwargs["run_candidate"], False)

    @patch('regressionx.cli.run_case')
    @patch('regressionx.cli.load_config')
    @patch('regressionx.cli.compare_directories')
    def test_run_cand_command_runs_candidate_only(self, mock_compare, mock_load, mock_run):
        mock_load.return_value = [
            self._make_case("c1")
        ]
        mock_run.return_value = (
            type('obj', (object,), {'returncode': 0}),
            type('obj', (object,), {'returncode': 0}),
            Path("/tmp/a"), Path("/tmp/b")
        )
        self._set_compare_ok(mock_compare)

        cli.main(["run_cand", "--config", "dummy_config.py"])

        args, kwargs = mock_run.call_args
        self.assertEqual(kwargs["run_baseline"], False)
        self.assertEqual(kwargs["run_candidate"], True)

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
