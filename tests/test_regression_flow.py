import json
import subprocess
from pathlib import Path

import pytest

from regressionx.config import load_config
from regressionx.runner import RegressionRunner
from regressionx.reporting import ReportBuilder


def write_config(tmp_path: Path) -> Path:
    config = {
        "schema_version": 1,
        "paths": {
            "workspace_root": str(tmp_path / "work" / "{case_id}" / "{version}"),
            "artifacts_root": str(tmp_path / "artifacts" / "{case_id}" / "{version}"),
        },
        "versions": {"baseline": "left", "candidate": "right"},
        "cmd_templates": {
            "preprocess": "python - <<'PY'\nfrom pathlib import Path\nroot = Path('{workspace_root}')\nroot.mkdir(parents=True, exist_ok=True)\n(root / 'prep.txt').write_text('{case_id}-{version}')\nPY",
            "run": "python - <<'PY'\nfrom pathlib import Path\nroot = Path('{artifacts_root}')\nroot.mkdir(parents=True, exist_ok=True)\n(root / 'payload.txt').write_text('{params.cell}-{version}')\nPY",
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
    path = tmp_path / "regressionx.yaml"
    path.write_text(json.dumps(config))
    return path


def test_load_config_validates_required_sections(tmp_path):
    cfg_path = write_config(tmp_path)
    config = load_config(cfg_path)
    assert config.schema_version == 1
    assert config.versions == {"baseline": "left", "candidate": "right"}
    assert len(config.cases) == 2


def test_run_generates_case_and_global_reports(tmp_path):
    cfg_path = write_config(tmp_path)
    config = load_config(cfg_path)
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
def test_missing_required_section_raises(tmp_path, missing_key):
    cfg_path = write_config(tmp_path)
    data = json.loads(cfg_path.read_text())
    data.pop(missing_key)
    cfg_path.write_text(json.dumps(data))

    with pytest.raises(ValueError):
        load_config(cfg_path)
