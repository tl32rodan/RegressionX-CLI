# RegressionX CLI

RegressionX CLI is a regression-comparison platform aimed at running the same regression case against two code versions and producing consistent, template-driven reports. The platform is built around the principle that **cases are data, not processes**: all process logic lives in shared templates, while cases only provide the minimum parameters needed to differentiate runs.

## Getting started (MVP)

The initial CLI implementation focuses on running two versions of each case, producing case-level and global reports, and keeping per-case configuration minimal.

### Installation

No external dependencies are required beyond Python 3.11+ and `pytest` for tests. Commands below assume you are in the project root.

### Running regressions

Use `make run` to execute the CLI. Pass additional arguments via `ARGS`:

```bash
make run ARGS="run --config examples/demo_config.yaml"
```

Reports are written to the locations defined in your config (`demo/reports` in the demo file). To run a specific case:

```bash
make run ARGS="run --config examples/demo_config.yaml --case adder_case"
```

### Validation

Check configuration validity without executing cases:

```bash
make run ARGS="validate --config examples/demo_config.yaml"
```

### Testing (TDD workflow)

The repository includes unit tests that drive the implementation. Run them with:

```bash
make test
```

### Documentation

* `docs/architecture.md` – core architecture, lifecycle, configuration layers, and reporting design.
* `examples/config.example.yaml` – sample global configuration illustrating template-driven workflows and reporting options.
* `examples/demo_config.yaml` – runnable demo showcasing the CLI with generated artifacts and reports.
