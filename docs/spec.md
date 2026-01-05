# RegressionX Formal Specification

## Purpose
RegressionX is a regression truth engine that compares two versions of the same case execution to determine whether a change is acceptable. The system produces a legally-defensible judgement with consistent rules and a documented contract.

## Core Definition
A **regression** in RegressionX is the comparison of artifacts produced by running a single case under two versions (baseline and candidate). The comparison yields a judgement for each case and a summary judgement for the run.

## Judgement States
RegressionX emits a judgement per case and per run:

- **PASS**: No differences were detected between baseline and candidate artifacts after applying configured filters.
- **FAIL**: One or more differences were detected between baseline and candidate artifacts after applying configured filters.
- **WARN**: Differences were detected, but the judgement is marked as a warning according to configured rules or policies.

> Note: The current prototype reports PASS/FAIL based on artifact diffs only. WARN is reserved for future rule-based judges and policy layers.

## Regression Boundaries
### Supported
- **File artifact diffs** between baseline and candidate versions.
- **Per-case execution** defined by a regression case configuration.
- **Filtering rules** applied to diff inputs (include/ignore patterns and per-case extra ignore lists).
- **JSON and YAML configuration** with explicit schema versioning.

### Unsupported
- **Non-file artifact comparisons** (e.g., database state, external services) unless represented as artifacts on disk.
- **Cross-case dependencies** or ordering constraints.
- **Real-time streaming or incremental diffing.**
- **Automatic remediation or approval workflows.**

## Out-of-Scope Behaviors
- Any implicit inference of correctness beyond artifact equality.
- Any automatic adjustment of configuration or rules based on previous runs.
- Any change in case execution semantics beyond what the configuration explicitly defines.

## Contractual Guarantees
- Configuration is treated as a contract and must validate against published schemas before execution.
- Regression judgements are derived exclusively from diff results and documented rules.
- Outputs are deterministic given the same inputs, configuration, and runtime environment.
