import json
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

from regressionx import config as config_module
from regressionx.config import load_config
from regressionx.maintenance import clean_paths
from regressionx.reporting import ReportBuilder
from regressionx.runner import RegressionRunner


def _dependencies_available() -> bool:
    return yaml is not None and config_module.jsonschema is not None


class RegressionFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        if not _dependencies_available():
            self.skipTest("yaml/jsonschema are required for config validation tests")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_config(self) -> dict:
        return {
            "schema_version": 1,
            "paths": {
                "workspace_root": str(self.tmp_path / "work" / "{case_id}" / "{version}"),
                "artifacts_root": str(self.tmp_path / "artifacts" / "{case_id}" / "{version}"),
            },
            "versions": {"baseline": "left", "candidate": "right"},
            "cmd_templates": {
                "preprocess": (
                    "python -c \"from pathlib import Path; "
                    "root = Path('{workspace_root}'); "
                    "root.mkdir(parents=True, exist_ok=True); "
                    "(root / 'prep.txt').write_text('{case_id}-{version}')\""
                ),
                "run": (
                    "python -c \"from pathlib import Path; "
                    "root = Path('{artifacts_root}'); "
                    "root.mkdir(parents=True, exist_ok=True); "
                    "(root / 'payload.txt').write_text('{params_cell}-{version}')\""
                ),
            },
            "filters": {
                "include": ["**/*"],
                "ignore": ["**/prep.txt"],
                "extra_ignore_allowed": True,
            },
            "reporting": {
                "global_report": str(self.tmp_path / "reports" / "global"),
                "case_report": str(self.tmp_path / "reports" / "cases" / "{case_id}"),
                "formats": ["json"],
            },
            "cases": [
                {
                    "case_id": "alpha",
                    "params": {"cell": "adder"},
                    "metadata": {"owner": "alice"},
                    "extra_ignore": ["**/ignored.bin"],
                },
                {
                    "case_id": "beta",
                    "params": {"cell": "mult"},
                    "metadata": {"owner": "bob"},
                },
            ],
        }

    def _write_config(self, config: dict) -> Path:
        path = self.tmp_path / "regressionx.yaml"
        path.write_text(yaml.safe_dump(config, sort_keys=False))
        return path

    def test_load_config_validates_required_sections(self) -> None:
        # Arrange
        config_path = self._write_config(self._build_config())

        # Act
        config = load_config(config_path)

        # Assert
        self.assertEqual(config.schema_version, 1)
        self.assertEqual(config.versions, {"baseline": "left", "candidate": "right"})
        self.assertEqual(len(config.cases), 2)

    def test_run_generates_case_and_global_reports(self) -> None:
        # Arrange
        config_path = self._write_config(self._build_config())
        config = load_config(config_path)

        # Act
        runner = RegressionRunner(config)
        results = runner.run_all()
        reports = ReportBuilder(config, results)
        reports.write_reports()

        # Assert
        global_report = json.loads((self.tmp_path / "reports" / "global.json").read_text())
        self.assertEqual(global_report["summary"]["total"], 2)
        self.assertEqual(global_report["cases"]["alpha"]["status"], "FAIL")
        self.assertEqual(global_report["summary"]["failure"], 0)

        case_report_path = self.tmp_path / "reports" / "cases" / "alpha.json"
        case_report = json.loads(case_report_path.read_text())
        self.assertEqual(case_report["case_id"], "alpha")
        self.assertEqual(case_report["differences"], ["payload.txt"])
        self.assertEqual(case_report["params"], {"cell": "adder"})
        self.assertEqual(case_report["metadata"], {"owner": "alice"})

    def test_missing_required_section_raises(self) -> None:
        # Arrange
        config = self._build_config()
        config_path = self._write_config(config)
        missing_keys = ["versions", "paths", "cmd_templates", "cases"]

        for missing_key in missing_keys:
            with self.subTest(missing_key=missing_key):
                # Act
                data = yaml.safe_load(config_path.read_text())
                data.pop(missing_key)
                config_path.write_text(yaml.safe_dump(data, sort_keys=False))

                # Assert
                with self.assertRaises(ValueError):
                    load_config(config_path)

                # Arrange
                config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    def test_command_failure_sets_failure_status(self) -> None:
        # Arrange
        config = self._build_config()
        config["cmd_templates"]["run"] = "python -c \"import sys; sys.stderr.write('boom'); sys.exit(1)\""
        config_path = self._write_config(config)
        loaded = load_config(config_path)

        # Act
        runner = RegressionRunner(loaded)
        results = runner.run_all()

        # Assert
        self.assertEqual(results[0].status, "FAILURE")
        self.assertTrue(results[0].commands)
        self.assertEqual(results[0].commands[0].stderr, "boom")
        self.assertTrue(results[0].errors)

    def test_report_from_artifacts_generates_summary(self) -> None:
        # Arrange
        config_path = self._write_config(self._build_config())
        loaded = load_config(config_path)
        for case in loaded.cases:
            for version in loaded.versions.keys():
                artifact_root = self.tmp_path / "artifacts" / case.case_id / version
                artifact_root.mkdir(parents=True, exist_ok=True)
                (artifact_root / "payload.txt").write_text(f"{case.case_id}-{version}")

        # Act
        runner = RegressionRunner(loaded)
        results = runner.report_from_artifacts()
        reports = ReportBuilder(loaded, results)
        reports.write_reports()

        # Assert
        global_report = json.loads((self.tmp_path / "reports" / "global.json").read_text())
        self.assertEqual(global_report["summary"]["total"], 2)
        self.assertEqual(global_report["cases"]["alpha"]["status"], "FAIL")

    def test_clean_paths_removes_outputs(self) -> None:
        # Arrange
        config_path = self._write_config(self._build_config())
        loaded = load_config(config_path)
        runner = RegressionRunner(loaded)
        results = runner.run_all()
        reports = ReportBuilder(loaded, results)
        reports.write_reports()

        # Act
        clean_paths(loaded)

        # Assert
        self.assertFalse((self.tmp_path / "reports").exists())
        self.assertFalse((self.tmp_path / "artifacts").exists())
        self.assertFalse((self.tmp_path / "work").exists())


if __name__ == "__main__":
    unittest.main()
