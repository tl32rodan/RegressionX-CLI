import subprocess
from pathlib import Path

import pytest
yaml = pytest.importorskip("yaml")

from regressionx import config as config_module
from regressionx.config import load_config
from regressionx.reporting import ReportBuilder
from regressionx.runner import RegressionRunner


def build_config(tmp_path: Path) -> dict:
    return {
        "schema_version": 1,
        "paths": {
            "workspace_root": str(tmp_path / "work" / "{case_id}" / "{version}"),
            "artifacts_root": str(tmp_path / "artifacts" / "{case_id}" / "{version}"),
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
            "global_report": str(tmp_path / "reports" / "global"),
            "case_report": str(tmp_path / "reports" / "cases" / "{case_id}"),
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


def write_config(tmp_path: Path, config: dict) -> Path:
    path = tmp_path / "regressionx.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    return path


@pytest.fixture
def regression_config_path(tmp_path: Path) -> Path:
    return write_config(tmp_path, build_config(tmp_path))


def require_jsonschema() -> None:
    if config_module.jsonschema is None:
        pytest.skip("jsonschema is required for schema validation tests")


def test_load_config_validates_required_sections(regression_config_path):
    require_jsonschema()
    config = load_config(regression_config_path)
    assert config.schema_version == 1
    assert config.versions == {"baseline": "left", "candidate": "right"}
    assert len(config.cases) == 2


def test_run_generates_case_and_global_reports(regression_config_path, tmp_path):
    require_jsonschema()
    config = load_config(regression_config_path)
    runner = RegressionRunner(config)
    results = runner.run_all()

    reports = ReportBuilder(config, results)
    reports.write_reports()

    global_report = json.loads((tmp_path / "reports" / "global.json").read_text())
    assert global_report["summary"]["total"] == 2
    assert global_report["cases"]["alpha"]["status"] == "FAIL"  # versions differ

    case_report_path = tmp_path / "reports" / "cases" / "alpha.json"
    case_report = json.loads(case_report_path.read_text())
    assert case_report["case_id"] == "alpha"
    assert case_report["differences"] == ["payload.txt"]


@pytest.mark.parametrize("missing_key", ["versions", "paths", "cmd_templates", "cases"])
def test_missing_required_section_raises(regression_config_path, missing_key):
    require_jsonschema()
    data = yaml.safe_load(regression_config_path.read_text())
    data.pop(missing_key)
    regression_config_path.write_text(yaml.safe_dump(data, sort_keys=False))

    with pytest.raises(ValueError):
        load_config(regression_config_path)
