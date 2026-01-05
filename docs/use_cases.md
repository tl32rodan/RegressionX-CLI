# RegressionX Use Cases

## Validate a Configuration Contract
**Goal:** Ensure a regression configuration complies with the formal schema before running any cases.

- Input: `regressionx.yaml`
- Output: Validation success or schema error with actionable feedback.

## Run a Full Regression Suite
**Goal:** Execute all configured cases and produce a global report.

- Input: Full regression configuration with multiple cases.
- Output: Global report plus per-case reports with PASS/FAIL judgements.

## Run a Targeted Case Subset
**Goal:** Execute a subset of cases for quick verification or focused debugging.

- Input: Regression configuration and a list of case IDs.
- Output: Reports limited to the selected cases.

## Produce Machine-Readable Reports
**Goal:** Provide deterministic outputs that can be used by CI, dashboards, or automated gatekeepers.

- Input: Regression configuration with JSON reporting enabled.
- Output: JSON reports containing summary, per-case status, and diff lists.

## Inspect Regression Differences
**Goal:** Identify exactly which artifacts changed between baseline and candidate for a given case.

- Input: Case report and diff list.
- Output: Named list of artifacts that differ.
