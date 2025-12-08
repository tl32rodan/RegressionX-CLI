import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from .config import Config
from .runner import CaseResult


class ReportBuilder:
    def __init__(self, config: Config, results: List[CaseResult]):
        self.config = config
        self.results = results

    def write_reports(self) -> None:
        formats = self.config.reporting.get("formats", ["json"])
        global_base = Path(self.config.reporting.get("global_report", "reports/global"))
        case_base_template = self.config.reporting.get("case_report", "reports/cases/{case_id}")

        summary = self._global_summary()
        if "json" in formats:
            self._write_json(global_base.with_suffix(".json"), summary)
        if "md" in formats:
            self._write_md(global_base.with_suffix(".md"), summary)

        for result in self.results:
            case_payload = self._case_report(result)
            case_base = Path(case_base_template.format(case_id=result.case_id))
            if "json" in formats:
                self._write_json(case_base.with_suffix(".json"), case_payload)
            if "md" in formats:
                self._write_md(case_base.with_suffix(".md"), case_payload)

    def _global_summary(self) -> dict:
        totals = {"PASS": 0, "FAIL": 0, "ERROR": 0}
        for result in self.results:
            totals[result.status] = totals.get(result.status, 0) + 1
        return {
            "summary": {
                "total": len(self.results),
                "pass": totals.get("PASS", 0),
                "fail": totals.get("FAIL", 0),
                "error": totals.get("ERROR", 0),
            },
            "cases": {
                r.case_id: {
                    "status": r.status,
                    "differences": r.differences,
                    "errors": r.errors,
                }
                for r in self.results
            },
        }

    def _case_report(self, result: CaseResult) -> dict:
        return {
            "case_id": result.case_id,
            "status": result.status,
            "differences": result.differences,
            "errors": result.errors,
            "commands": [asdict(cmd) for cmd in result.commands],
        }

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))

    def _write_md(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Report"]
        for key, value in payload.items():
            lines.append(f"- **{key}**: {value}")
        path.write_text("\n".join(lines))
