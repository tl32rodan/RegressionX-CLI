import argparse
import sys
from pathlib import Path
from .config import load_config
from .executor import run_case, skipped_result
from .comparator import compare_directories

COMMAND_MODES = {
    "run": (True, True, False),
    "compare": (False, False, True),
    "run_base": (True, False, False),
    "run_cand": (False, True, False),
}

def main(args=None):
    if args is None:
        args = sys.argv[1:]
        
    parser = argparse.ArgumentParser(description="RegressionX CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    def add_common_args(subparser):
        subparser.add_argument("--config", required=True, help="Path to config file")
        subparser.add_argument("--report", default="regression_report.md", help="Path to generate Markdown report")

    add_common_args(subparsers.add_parser("run"))
    add_common_args(subparsers.add_parser("compare"))
    add_common_args(subparsers.add_parser("run_base"))
    add_common_args(subparsers.add_parser("run_cand"))
    
    parsed_args = parser.parse_args(args)
    
    if parsed_args.command in COMMAND_MODES:
        try:
            cases = load_config(parsed_args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)
    
        # Initialize Reporter
        from .reporter import MarkdownReporter
        reporter = MarkdownReporter(parsed_args.report)

        # Initialize a failure counter for the new logic
        total_failures = 0

        run_baseline, run_candidate, compare_only = COMMAND_MODES[parsed_args.command]

        for case in cases:
            print(f"Running case: {case.name}...", end=" ", flush=True)
            try:
                if compare_only:
                    base_res = skipped_result()
                    cand_res = skipped_result()
                    base_path = Path(case.base_path)
                    cand_path = Path(case.cand_path)
                else:
                    base_res, cand_res, base_path, cand_path = run_case(
                        case,
                        run_baseline=run_baseline,
                        run_candidate=run_candidate
                    )
                
                if compare_only or (
                    (not run_baseline or base_res.returncode == 0) and
                    (not run_candidate or cand_res.returncode == 0)
                ):
                    cmp_result = compare_directories(base_path, cand_path)
                    
                    reporter.add_result(case, base_res, cand_res, cmp_result)
                    
                    if cmp_result.match:
                        print("PASSED")
                    else:
                        print("FAILED (Mismatch)")
                        for err in cmp_result.errors:
                            print(f"  [Structure] {err}")
                        for diff in cmp_result.diffs:
                            print(f"  [Content]   {diff}")
                        total_failures += 1
                else:
                    print("FAILED (Execution Error)")
                    if run_baseline and base_res.returncode != 0:
                        print(f"  Baseline Failed ({base_res.returncode})")
                    if run_candidate and cand_res.returncode != 0:
                        print(f"  Candidate Failed ({cand_res.returncode})")
                    
                    from .comparator import ComparatorResult
                    fail_cmp = ComparatorResult(match=False, errors=["Execution Failed"], diffs=[])
                    reporter.add_result(case, base_res, cand_res, fail_cmp)
                    
                    total_failures += 1
            except Exception as e:
                print(f"ERROR: {e}")
                total_failures += 1
                
        # Generate Report
        reporter.generate()
        print(f"Report generated: {parsed_args.report}")
        
        if total_failures > 0:
            sys.exit(1)

if __name__ == "__main__":
    main()
