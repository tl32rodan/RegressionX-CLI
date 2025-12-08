# RegressionX CLI Architecture

## Design philosophy

* **Cases are data, not processes.** All executable logic is defined in global templates; cases only inject parameters such as `case_id`, `cell`, `pvt`, or repository paths.
* **Template-driven consistency.** Preprocess, run, layout, and compare steps share unified templates to prevent drift between cases.
* **Global, opinionated defaults.** Include/ignore rules, output conventions, and report formats are centrally defined to keep semantics stable across hundreds or thousands of cases.
* **Parameter-driven extensibility.** Growth is achieved by adding parameters, not duplicating configuration. When exceptions are necessary (e.g., `extra_ignore`), they are explicitly marked as opt-in deviations.

## High-level flow

1. **Case ingestion**
   * Minimal case definition (YAML/JSON): `case_id`, required parameters, optional metadata (owner, tags), and constrained exceptions like `extra_ignore`.
   * Validation layer enforces minimal fields and rejects custom logic to avoid DSL creep.
2. **Preprocess stage**
   * Single `cmd_template` executed once per version inside a templated `workdir`.
   * Owners can register preprocessing scripts, but invocation and layout are dictated by the platform template.
3. **Run stage**
   * Executes templated commands for both code versions (e.g., `baseline` and `candidate`).
   * Output paths derived from the global `output_template`, preventing ad-hoc layouts.
4. **Artifact collection**
   * Normalizes outputs into deterministic directories keyed by `{case_id}/{version}`.
   * Applies global include/ignore rules immediately after run completion to lock in comparison scope.
5. **Comparison stage**
   * Binary-safe recursive diff that treats all files as binary by default.
   * Supports wildcard/regex filters from global config; per-case `extra_ignore` is the exception path.
6. **Reporting**
   * **Global report:** aggregates case outcomes, highlights failures, and links to case summaries.
   * **Case summary:** lists differing files, filtered through ignore rules, and records command/metadata context.
   * Reports written in a stable schema (JSON + human-readable markdown) to support GUI/CI integration.

## Configuration model

```
project_root/
  regressionx.yaml        # Global templates and rules
  cases/
    case1.yaml            # Minimal case parameters
    ...
  scripts/
    preprocess.sh         # Owner-provided scripts referenced by template
```

### Global configuration (`regressionx.yaml`)

* `paths`: `code_root`, `workspace_root`, `artifacts_root` templates.
* `cmd_templates`: `preprocess`, `run`, `compare` commands with placeholders like `{case_id}`, `{version}`, `{param.*}`.
* `reporting`: output locations and formatting options.
* `filters`: global `include`, `ignore`, and optional `extra_ignore_allowed: true/false` gate.
* `versions`: labels and paths for the two code versions (e.g., `baseline`, `candidate`).

### Case definition (example)

```yaml
case_id: rsa_vector_small
params:
  cell: rsa
  pvt: ss_0p8_125c
metadata:
  owner: alice
extra_ignore:
  - "**/timing/**"  # Optional escape hatch; discouraged by default
```

Validation rejects custom commands; only allowed keys are `case_id`, `params`, optional `metadata`, and gated `extra_ignore`.

## Reporting format

* **Global report (`reports/global.json` & `reports/global.md`):**
  * per-case status (`PASS`/`FAIL`/`ERROR`)
  * links to case summary paths
  * timestamp and version metadata
* **Case summary (`reports/cases/{case_id}.json|md`):**
  * command context (templates resolved with parameters)
  * differing files (post-filter)
  * optional preview of binary diffs (size/hash comparison)

## CLI surface

* `regx validate` – validate global and case configs against schema.
* `regx run [CASE_ID|--all] --baseline <path> --candidate <path>` – execute preprocess/run/compare using templates.
* `regx report` – regenerate global report from stored artifacts.
* `regx clean` – remove generated workspaces and reports.

CLI commands share environment variables for injected parameters and expose dry-run mode for auditing resolved commands before execution.

## Extensibility guardrails

* **Schema versioning:** configuration files carry `schema_version`; breaking changes require explicit migration steps.
* **Plugin boundary:** preprocessing scripts live in `scripts/` and are invoked through templates; platform controls working directory, env vars, and allowed arguments.
* **Reproducibility:** outputs are content-addressed where possible (hash-based) to reduce false positives from timestamps.
* **Deterministic filtering:** ignore rules are applied in a fixed order: global `ignore` → global `include` overrides → optional `extra_ignore`.

## Future considerations

* **Dashboard integration:** stable JSON schema enables web dashboards without changing CLI outputs.
* **Historical baselines:** ability to compare against stored artifact sets instead of live code trees.
* **Concurrency controls:** per-case locks and resource quotas to run large suites safely in CI.
* **Secret handling:** sealed env var injection for scripts, with audit logs on usage.
