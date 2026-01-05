# RegressionX CLI

RegressionX CLI is a regression-comparison platform aimed at running the same regression case against two code versions and producing consistent, template-driven reports. The platform is built around the principle that **cases are data, not processes**: all process logic lives in shared templates, while cases only provide the minimum parameters needed to differentiate runs.

## Getting started (MVP)

The initial CLI implementation focuses on running two versions of each case, producing case-level and global reports, and keeping per-case configuration minimal.

### Installation

RegressionX requires Python 3.11+ and PyYAML. `pytest` is used for tests, and `jsonschema` is optional for schema validation.
Commands below assume you are in the project root.

### Running regressions

Use `make run` to execute the CLI. Pass additional arguments via `ARGS`:

```bash
make run ARGS="run --config examples/config.example.yaml"
```

Reports are written to the locations defined in your config (`demo/reports` in the demo file). To run a specific case:

```bash
make run ARGS="run --config examples/config.example.yaml --case adder_case"
```

### Demo run

The demo config uses inline Python commands to produce output files under `demo/artifacts`. Run the demo and clean it up with:

```bash
make demo
make clean
```

### Validation

Check configuration validity without executing cases:

```bash
make run ARGS="validate --config examples/config.example.yaml"
```

### Testing (TDD workflow)

The repository includes unit tests that drive the implementation. Run them with:

```bash
make test
```

### Documentation

* `docs/architecture.md` – core architecture, lifecycle, configuration layers, and reporting design.
* `examples/config.example.yaml` – runnable demo showcasing the CLI with generated artifacts and reports.
