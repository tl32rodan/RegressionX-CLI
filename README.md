# RegressionX-CLI

**The "Standard Library First" A/B Regression Tool.**

RegressionX is a lightweight, zero-dependency Python tool designed to run A/B regression tests. It compares the output of two command versions (Baseline vs Candidate) by executing them in per-case output directories and strictly verifying their output directories.

## Key Features

- **A/B Testing**: Runs two versions of a command side-by-side (`old_tool` vs `new_tool`).
- **Per-Case Output Paths**: Each case declares its own baseline/candidate output directories, making it easy to inspect and archive results.
- **Python-as-Config**: Use the full power of Python to define your test cases and templates.
- **Markdown Reporting**: Generates simple, grep-friendly `.md` reports suitable for LSF logs and Git.
- **Zero Dependencies**: Requires only Python 3. No `pip install` needed.

## Quick Start

1.  **Define your configuration** (e.g., `examples/factory_config.py`):

    ```python
    from regressionx import Template

    # run_logic defines the shape of the command
    run_logic = Template(
        baseline_command="python old_script.py {args}",
        candidate_command="python new_script.py {args}",
        base_path="runs/{name}/baseline",
        cand_path="runs/{name}/candidate"
    )

    # generate creates the list of cases
    cases = run_logic.generate([
        {"name": "test_fast", "args": "--mode fast"},
        {"name": "test_slow", "args": "--mode slow"},
    ])
    ```

2.  **Run the regression**:

    ```bash
    # Linux / Git Bash
    python bin/regressionX run --config examples/factory_config.py

    # Windows (PowerShell)
    python bin/regressionX run --config examples/factory_config.py
    ```

3.  **View the Report**:

    Check `regression_report.md` (generated in CWD by default).

    ```markdown
    # RegressionX Report
    **Total:** 2 | **Passed:** 1 | **Failed:** 1

    ## Failure Details
    ### test_slow
    - [Content] Content mismatch: output.log
    ```

## CLI Options

```bash
usage: regressionX {run,compare,run_base,run_cand} [-h] --config CONFIG [--report REPORT]

options:
  -h, --help       show this help message and exit
  --config CONFIG  Path to config file (required)
  --report REPORT  Path to generate Markdown report (default: regression_report.md)
```

### Modes

- `run`: execute baseline and candidate, then compare outputs
- `compare`: compare `base_path`/`cand_path` without running any commands
- `run_base`: run baseline only, then compare with candidate output
- `run_cand`: run candidate only, then compare with baseline output

## Development

This project uses **Test-Driven Development (TDD)** and provides a `Makefile` for common tasks.

-   **Run Tests**:
    ```bash
    make test
    # or
    python -m unittest discover tests
    ```

-   **Run Demos**:
    ```bash
    make demo          # Run passing demo
    make demo-fail     # Run failing demo
    make demo-nested   # Run nested output demo
    ```

-   **Clean Artifacts**:
    ```bash
    make clean
    ```
