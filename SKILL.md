# easyreg MCP Skill Guide

> **Audience**: AI agents (especially older models such as qwen3-235B)
> This document describes how to correctly use the tools exposed by the
> easyreg MCP server.

---

## What is RegressionX?

RegressionX is a **regression testing platform** that:

1. Executes test case commands
2. Compares execution outputs against **golden references** (verified expected output)
3. Reports a verdict: `PASS` / `FAIL` / `NEW` / `ERROR`
4. Manages golden reference promotion

---

## Starting the MCP Server

This MCP server is implemented with **FastMCP**.

```json
{
  "mcpServers": {
    "regressionx": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "<absolute path to the RegressionX-CLI root directory>"
    }
  }
}
```

Or via the fastmcp CLI:

```bash
fastmcp run mcp_server.py
```

Install dependency:

```bash
pip install fastmcp
```

---

## Available Tools

| Tool | Purpose | Required params | Optional params |
|---|---|---|---|
| `regressionx_show_config` | Inspect suite config contents | `config_path` | — |
| `regressionx_golden_status` | Check whether golden references exist | `config_path` | — |
| `regressionx_impact` | Identify cases likely affected by changed files | `config_path`, `changed_files` | — |
| `regressionx_run` | Execute cases and compare against golden | `config_path` | `case_name`, `parallel` |
| `regressionx_compare` | Compare only (no re-execution) | `config_path` | `case_name` |
| `regressionx_promote` | Promote output to golden | `config_path` | `case_name` |

---

## ⚠️ Tool Selection and Ordering

### Standard workflow (follow this order strictly)

```
Step 0: regressionx_impact        — (optional) identify affected cases from git diff
Step 1: regressionx_show_config   — inspect the config; confirm config_path is correct
Step 2: regressionx_golden_status — check whether golden references have been created
Step 3: regressionx_run           — execute test cases (targeted or full)
Step 4: regressionx_promote       — (only if verdict=NEW) create golden for the first time
```

Step 0 is optional. Use it when `git diff --name-only` context is available and you
want faster feedback by running only cases affected by the change.

### When to use which tool

| Situation | Use | Do NOT use |
|---|---|---|
| "Changed files known; want targeted run" | `regressionx_impact` then `regressionx_run` per case | — |
| "I want to run regression tests" | `regressionx_run` | ~~regressionx_compare~~ |
| "Outputs already exist; just re-check the diff" | `regressionx_compare` | ~~regressionx_run~~ |
| "Verdict is NEW; I need to create a golden" | `regressionx_promote` | — |
| "I'm not sure what cases are in the config" | `regressionx_show_config` | — |
| "Is golden already set up?" | `regressionx_golden_status` | — |

---

## ⚠️ Parameter Hints (prevent common mistakes)

### config_path

- Must be a **string** pointing to a `.json` file
- Accepts relative or absolute paths
- **Correct**: `"examples/simple_suite.json"`
- **Wrong**: `"examples/simple_suite"` (missing `.json`), `null`, `{}`

```json
// ✅ Correct
{"config_path": "examples/simple_suite.json"}

// ❌ Wrong — do not omit the .json extension
{"config_path": "examples/simple_suite"}

// ❌ Wrong — do not pass null or an object
{"config_path": null}
```

### case_name

- **Optional** — omit it to run/compare/promote **all** cases
- Must **exactly match** a case `name` field in the config (case-sensitive)
- **Always call `regressionx_show_config` first** to get the correct names
- **Correct**: `"hello"`, `"case_a"`
- **Wrong**: `"Hello"` (wrong case), `"all"` (not a real name), `"*"` (not a glob)

```json
// ✅ Correct — run only the case named "hello"
{"config_path": "examples/simple_suite.json", "case_name": "hello"}

// ✅ Correct — run all cases (omit case_name)
{"config_path": "examples/simple_suite.json"}

// ❌ Wrong — do not use "*" or "all"; just omit the parameter
{"config_path": "examples/simple_suite.json", "case_name": "*"}
```

### changed_files (regressionx_impact only)

- **Required** for `regressionx_impact`
- Must be a **list of strings** (file paths from `git diff --name-only`)
- Accepts relative or absolute paths
- **Correct**: `["src/parser.py", "testdata/input.txt"]`
- **Wrong**: `"src/parser.py"` (a string, not a list)

```json
// ✅ Correct
{"config_path": "regression/suite.json", "changed_files": ["src/parser.py"]}

// ❌ Wrong — must be a list, not a string
{"config_path": "regression/suite.json", "changed_files": "src/parser.py"}
```

### parallel

- **Optional**, only used by `regressionx_run`
- Must be a **positive integer**; default is `1`
- Do not pass `0` or a negative value
- Do not pass a string

```json
// ✅ Correct
{"config_path": "examples/simple_suite.json", "parallel": 4}

// ❌ Wrong — do not pass a string
{"config_path": "examples/simple_suite.json", "parallel": "4"}
```

---

## Verdict Reference

| Verdict | Meaning | Next action |
|---|---|---|
| `PASS` | Output matches golden exactly | Nothing needed |
| `FAIL` | Output differs from golden | Inspect the `diffs` field; investigate the cause |
| `NEW` | No golden reference exists yet | Confirm output is correct, then call `regressionx_promote` |
| `ERROR` | Command execution failed | Inspect the `errors` field; fix the command or environment |

---

## Response Structure

### regressionx_run / regressionx_compare

```json
{
  "suite": "suite_name",
  "summary": {"PASS": 1, "FAIL": 0, "NEW": 0, "ERROR": 0},
  "results": [
    {
      "case_name": "hello",
      "verdict": "PASS",
      "diffs": [],
      "errors": []
    }
  ]
}
```

- `diffs`: list of mismatched file paths (non-empty only when verdict is `FAIL`)
- `errors`: list of error messages (non-empty only when verdict is `ERROR`)

### regressionx_impact

```json
{
  "affected_cases": ["parse_hex"],
  "all_cases": ["parse_hex", "parse_oct", "parse_bin"],
  "coverage": 0.333,
  "note": "best-effort; full suite run remains authoritative"
}
```

- `affected_cases`: subset of case names likely impacted by the changed files
- `coverage`: fraction of all cases flagged (0.0 – 1.0)
- If `coverage` is 1.0, run the full suite directly (all cases are affected)

### regressionx_promote

```json
{"promoted": ["hello", "case_a"]}
```

### regressionx_golden_status

```json
{"golden_root": "examples/golden", "cases": {"hello": true}}
```

### regressionx_show_config

Returns the fully parsed suite structure including all cases, diff_rules, env, and versions.

---

## Common Errors and Fixes

| Error message | Cause | Fix |
|---|---|---|
| `Config file not found: xxx` | `config_path` does not exist | Verify the path; check relative path base directory |
| `No case named 'xxx' found` | `case_name` is misspelled or absent | Call `regressionx_show_config` first to get exact case names |
| `Source directory does not exist` | Output directory missing during promote | Run `regressionx_run` first to produce the output |
| `Config missing required field` | Suite JSON is missing a required key | Ensure JSON contains `suite`, `golden_dir`, `output_dir`, `cases` |

---

## Suite JSON Config Quick Reference

Minimal valid suite config:

```json
{
  "suite": "my_test",
  "golden_dir": "golden/{case}",
  "output_dir": "runs/{case}",
  "cases": [
    {
      "name": "example",
      "command": "echo hello > output.txt"
    }
  ]
}
```

### Diff Rule Types

| type | Purpose | `pattern` example | `replace` |
|---|---|---|---|
| `ignore_line` | Drop entire lines matching a regex | `"^#.*timestamp"` | not needed |
| `ignore_regex` | Replace matched text within a line before comparing | `"PID=\\d+"` | `"PID=XXX"` |
| `ignore_file` | Ignore files matching a glob pattern | `"*.log"` | not needed |
| `ignore_folder` | Ignore directories matching a glob pattern | `"tmp/"` | not needed |
| `sort_lines` | Sort lines before comparing (handles unstable output order) | `".*"` (any) | not needed |
| `tolerance` | Numeric tolerance for floating-point values | `".*"` (any) | `"0.001"` (tolerance value) |

---

## Full Worked Examples

### Example 1 — First-time golden setup

```
Agent reasoning: the user wants to set up regression tests for examples/simple_suite.json

1. Call regressionx_show_config(config_path="examples/simple_suite.json")
   → Confirms there is 1 case: "hello"

2. Call regressionx_golden_status(config_path="examples/simple_suite.json")
   → Golden does not exist yet

3. Call regressionx_run(config_path="examples/simple_suite.json")
   → verdict: NEW (no golden to compare against)

4. Confirm the output looks correct, then call:
   regressionx_promote(config_path="examples/simple_suite.json")
   → promoted: ["hello"]

5. Call regressionx_run(config_path="examples/simple_suite.json") again
   → verdict: PASS (golden now exists)
```

### Example 2 — Routine regression check

```
Agent reasoning: the user modified code and wants to check for regressions

1. Call regressionx_run(config_path="examples/simple_suite.json")
   → Check summary: if all PASS, report "no regression detected"
   → If any FAIL, inspect the diffs field and report which files differ
```

### Example 3 — Diff-aware triage (targeted PR review)

```
Agent reasoning: PR modifies src/parser.py; want fast feedback without running
all 20 cases in the suite

1. Collect changed files from the PR diff:
   changed_files = ["src/parser.py", "testdata/inputs/hex_input.txt"]

2. Call regressionx_impact(
       config_path="regression/suite.json",
       changed_files=["src/parser.py", "testdata/inputs/hex_input.txt"]
   )
   → {"affected_cases": ["parse_hex", "parse_oct"], "coverage": 0.1}

3. Call regressionx_run(config_path="regression/suite.json", case_name="parse_hex")
   Call regressionx_run(config_path="regression/suite.json", case_name="parse_oct")
   → Both PASS — no regression in the affected subset

4. Report: "Targeted run (2/20 cases, coverage 10%) — all PASS.
   Full suite recommended before merge."

Note: if coverage is 1.0 (all cases affected), skip step 2 and run the full suite.
```
