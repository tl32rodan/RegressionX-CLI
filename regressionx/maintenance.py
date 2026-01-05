from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from .config import Config
from .runner import RegressionRunner


def clean_paths(config: Config) -> None:
    runner = RegressionRunner(config)
    workspace_paths = _case_paths(runner, config, key="workspace_root")
    artifact_paths = _case_paths(runner, config, key="artifacts_root")
    report_paths = _report_paths(config)

    for path in sorted(workspace_paths.union(artifact_paths), key=lambda p: len(p.as_posix()), reverse=True):
        _safe_rmtree(path)

    for path in report_paths:
        if path.exists():
            path.unlink()
            _remove_empty_parents(path.parent)


def _case_paths(runner: RegressionRunner, config: Config, key: str) -> set[Path]:
    paths: set[Path] = set()
    for case in config.cases:
        for version, label in config.versions.items():
            context = runner._context_for(case, version, label)
            paths.add(Path(context[key]))
    return paths


def _report_paths(config: Config) -> set[Path]:
    formats = config.reporting.get("formats", ["json"])
    global_base = Path(config.reporting.get("global_report", "reports/global"))
    case_base_template = config.reporting.get("case_report", "reports/cases/{case_id}")
    paths: set[Path] = {global_base.with_suffix(f".{fmt}") for fmt in formats}
    for case in config.cases:
        base = Path(case_base_template.format(case_id=case.case_id))
        paths.update(base.with_suffix(f".{fmt}") for fmt in formats)
    return paths


def _safe_rmtree(path: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    if resolved == Path(resolved.anchor):
        return
    shutil.rmtree(resolved)
    _remove_empty_parents(resolved.parent)


def _remove_empty_parents(path: Path) -> None:
    current = path
    while True:
        if not current.exists() or any(current.iterdir()):
            break
        current.rmdir()
        if current.parent == current:
            break
        current = current.parent
