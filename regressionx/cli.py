import argparse
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .reporting import ReportBuilder
from .runner import RegressionRunner
from .maintenance import clean_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="regx", description="RegressionX CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run regression cases")
    run_parser.add_argument("--config", type=Path, default=Path("regressionx.yaml"))
    run_parser.add_argument("--case", action="append", help="Run a specific case by id")

    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    validate_parser.add_argument("--config", type=Path, default=Path("regressionx.yaml"))

    report_parser = subparsers.add_parser("report", help="Regenerate reports from artifacts")
    report_parser.add_argument("--config", type=Path, default=Path("regressionx.yaml"))
    report_parser.add_argument("--case", action="append", help="Report a specific case by id")

    clean_parser = subparsers.add_parser("clean", help="Clean workspaces, artifacts, and reports")
    clean_parser.add_argument("--config", type=Path, default=Path("regressionx.yaml"))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        config = load_config(args.config)
    except (ConfigError, FileNotFoundError) as exc:
        print(f"Configuration error: {exc}")
        return 1

    if args.command == "validate":
        print("Configuration is valid")
        return 0

    selected_cases = config.cases
    if getattr(args, "case", None):
        selected_cases = [case for case in config.cases if case.case_id in args.case]

    if args.command == "report":
        runner = RegressionRunner(config)
        results = runner.report_from_artifacts(selected_cases)
        reports = ReportBuilder(config, results)
        reports.write_reports()
        return 0

    if args.command == "clean":
        clean_paths(config)
        print("Cleaned RegressionX artifacts and reports")
        return 0

    runner = RegressionRunner(config)
    runner.config.cases = selected_cases
    results = runner.run_all()
    reports = ReportBuilder(config, results)
    reports.write_reports()
    return 0


if __name__ == "__main__":
    sys.exit(main())
