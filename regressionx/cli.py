import argparse
import sys
from .config import load_config
from .executor import run_case
from .comparator import compare_directories

def main(args=None):
    if args is None:
        args = sys.argv[1:]
        
    parser = argparse.ArgumentParser(description="RegressionX CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--config", required=True, help="Path to config file")
    run_parser.add_argument("--report", default="regression_report.md", help="Path to generate Markdown report")
    
    parsed_args = parser.parse_args(args)
    
    if parsed_args.command == "run":
        try:
            cases = load_config(parsed_args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)

        import tempfile
        import shutil
    
        # Create a temporary workspace for this run
        # In the future, we might want to allow users to specify this via flags
        work_root = tempfile.mkdtemp(prefix="regressionx_run_")
        print(f"Work Root: {work_root}")
    
        # Initialize Reporter
        from .reporter import MarkdownReporter
        reporter = MarkdownReporter(parsed_args.report)

        # Initialize a failure counter for the new logic
        total_failures = 0

        try:
            # runner = JobExecutor() # Removed: run_case is a function
            
            for case in cases:
                print(f"Running case: {case.name}...", end=" ", flush=True)
                try:
                    # Pass work_root to run_case
                    base_res, cand_res, base_path, cand_path = run_case(case, work_root)
                    
                    # For now, simple check: Did both run successfully?
                    if base_res.returncode == 0 and cand_res.returncode == 0:
                        # Both commands succeeded, now compare output
                        cmp_result = compare_directories(base_path, cand_path)
                        
                        # Add to report
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
                        if base_res.returncode != 0:
                            print(f"  Baseline Failed ({base_res.returncode})")
                            # print(base_res.stderr)
                        if cand_res.returncode != 0:
                            print(f"  Candidate Failed ({cand_res.returncode})")
                            # print(cand_res.stderr)
                        
                        # Add to report (mocking a failed comparison struct for now, or reporter should handle it)
                        # Let's import ComparatorResult for type safety if needed, or just mock it here
                        from .comparator import ComparatorResult
                        # Create a dummy failure result
                        fail_cmp = ComparatorResult(match=False, errors=["Execution Failed"], diffs=[])
                        reporter.add_result(case, base_res, cand_res, fail_cmp)
                        
                        total_failures += 1
                except Exception as e:
                    print(f"ERROR: {e}")
                    total_failures += 1
                    
            # Generate Report
            reporter.generate()
            print(f"Report generated: {parsed_args.report}")
            
        finally:
            # Cleanup? 
            # Ideally we keep it on failure for debug, but for now clean up to be nice.
            # shutil.rmtree(work_root) 
            pass 
        
        if total_failures > 0:
            sys.exit(1)

if __name__ == "__main__":
    main()
