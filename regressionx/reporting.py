import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .config import Config
from .runner import CaseResult


class ReportBuilder:
    def __init__(self, config: Config, results: List[CaseResult]):
        self.config = config
        self.results = results
        self.schema_version = 1

    def write_reports(self) -> None:
        formats = self.config.reporting.get("formats", ["json"])
        global_base = Path(self.config.reporting.get("global_report", "reports/global"))
        case_base_template = self.config.reporting.get("case_report", "reports/cases/{case_id}")

        summary = self._global_summary(formats, case_base_template)
        if "json" in formats:
            self._write_json(global_base.with_suffix(".json"), summary)
        if "md" in formats:
            self._write_md(global_base.with_suffix(".md"), summary, report_type="global")

        for result in self.results:
            case_payload = self._case_report(result)
            case_base = Path(case_base_template.format(case_id=result.case_id))
            if "json" in formats:
                self._write_json(case_base.with_suffix(".json"), case_payload)
            if "md" in formats:
                self._write_md(case_base.with_suffix(".md"), case_payload, report_type="case")

    def _global_summary(self, formats: List[str], case_base_template: str) -> dict:
        totals = {"PASS": 0, "FAIL": 0, "ERROR": 0, "FAILURE": 0}
        for result in self.results:
            totals[result.status] = totals.get(result.status, 0) + 1
        case_reports = {}
        for result in self.results:
            base = Path(case_base_template.format(case_id=result.case_id))
            case_reports[result.case_id] = {
                "status": result.status,
                "differences": result.differences,
                "errors": result.errors,
                "reports": {fmt: str(base.with_suffix(f".{fmt}")) for fmt in formats},
            }
        return {
            "schema_version": self.schema_version,
            "generated_at": self._timestamp(),
            "summary": {
                "total": len(self.results),
                "pass": totals.get("PASS", 0),
                "fail": totals.get("FAIL", 0),
                "failure": totals.get("FAILURE", 0),
                "error": totals.get("ERROR", 0),
            },
            "cases": case_reports,
        }

    def _case_report(self, result: CaseResult) -> dict:
        return {
            "schema_version": self.schema_version,
            "generated_at": self._timestamp(),
            "case_id": result.case_id,
            "status": result.status,
            "differences": result.differences,
            "errors": result.errors,
            "commands": [asdict(cmd) for cmd in result.commands],
            "params": result.params,
            "metadata": result.metadata,
        }

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))

    def _write_md(self, path: Path, payload: dict, report_type: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if report_type == "global":
            lines = self._global_md(payload)
        else:
            lines = self._case_md(payload)
        path.write_text("\n".join(lines))

    def _global_md(self, payload: dict) -> List[str]:
        summary = payload["summary"]
        lines = [
            "# RegressionX Global Report",
            "",
            f"- **Generated at:** {payload['generated_at']}",
            "",
            "## Summary",
            "",
            "| Total | PASS | FAIL | FAILURE | ERROR |",
            "| --- | --- | --- | --- | --- |",
            f"| {summary['total']} | {summary['pass']} | {summary['fail']} | {summary['failure']} | {summary['error']} |",
            "",
            "## Cases",
            "",
            "| Case ID | Status | Differences | Report |",
            "| --- | --- | --- | --- |",
        ]
        for case_id, data in payload["cases"].items():
            report_link = data["reports"].get("md") or next(iter(data["reports"].values()), "")
            diff_count = len(data.get("differences", []))
            lines.append(f"| {case_id} | {data['status']} | {diff_count} | {report_link} |")
        return lines

    def _case_md(self, payload: dict) -> List[str]:
        lines = [
            f"# RegressionX Case Report: {payload['case_id']}",
            "",
            f"- **Status:** {payload['status']}",
            f"- **Generated at:** {payload['generated_at']}",
            "",
            "## Parameters",
            "",
        ]
        if payload.get("params"):
            for key, value in payload["params"].items():
                lines.append(f"- **{key}**: {value}")
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## Metadata",
                "",
            ]
        )
        if payload.get("metadata"):
            for key, value in payload["metadata"].items():
                lines.append(f"- **{key}**: {value}")
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## Differences",
            ]
        )
        if payload["differences"]:
            for diff in payload["differences"]:
                lines.append(f"- {diff}")
        else:
            lines.append("- None")

        if payload.get("errors"):
            lines.extend(["", "## Errors"])
            for err in payload["errors"]:
                lines.append(f"- {err}")

        if payload.get("commands"):
            lines.extend(["", "## Commands", ""])
            lines.append("| Version | Command | Return code | Timed out |")
            lines.append("| --- | --- | --- | --- |")
            for cmd in payload["commands"]:
                lines.append(
                    f"| {cmd['version']} | `{cmd['command']}` | {cmd['returncode']} | {cmd['timed_out']} |"
                )
            lines.extend(["", "### Command Output", ""])
            for cmd in payload["commands"]:
                lines.append(f"#### {cmd['version']}")
                lines.append("")
                lines.append("**Stdout:**")
                lines.append("```")
                lines.append(cmd.get("stdout", "") or "")
                lines.append("```")
                lines.append("**Stderr:**")
                lines.append("```")
                lines.append(cmd.get("stderr", "") or "")
                lines.append("```")
        return lines

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
