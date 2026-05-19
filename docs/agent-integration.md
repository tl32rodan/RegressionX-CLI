# Agent Integration Guide

easyreg as a **computational feedback sensor** in the harness engineering model.

---

## Background: Harness Engineering (Fowler, 2026)

Martin Fowler coined "harness engineering" (February–April 2026) to describe the
practice of building feedforward guides and feedback sensors around coding agents.

Sources:
- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)
- [Harness Engineering — first thoughts](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering-memo.html)

A harness has two control types:

| Type | Timing | Examples |
|---|---|---|
| **Feedforward guides** | Before the agent runs | CLAUDE.md, specs, ROLE.md, conventions |
| **Feedback sensors** | After the agent runs | Tests, linters, type checkers, regression suites |
| Computational controls | Either | Deterministic — linters, compilers, golden-file regression |
| Inferential controls | Either | LLM-based — code review agents |

**easyreg is a computational feedback sensor.** It runs after code changes and
deterministically compares outputs against golden references. It pairs with
LLM-based code review (an inferential feedback sensor). Neither alone is sufficient.

---

## Integration Patterns

### Pattern 1: Post-change regression gate

The most common pattern. After a coding agent or human makes changes, run easyreg
to confirm existing observable behavior is preserved.

```
coding agent makes changes
        ↓
easyreg run                    ← computational feedback sensor
        ↓
  All PASS? ─yes─> proceed to code review (inferential feedback sensor)
        │
       no
        ↓
  FAIL: agent investigates diff, fixes regression (never touches goldens)
  NEW:  human reviews output and promotes golden (agent reports only)
  ERROR: environment issue → escalate to human
```

### Pattern 2: Code review agent integration

The `scld-code-reviewer` agent (see [scld-code-reviewer repo](https://github.com/tl32rodan/scld-code-reviewer))
uses easyreg MCP tools via its standalone `/regress` command. The regression
personality is separate from `/review` — both can be required before `/checkin`
allows filing, and both run identically from a developer terminal and from CI.

Full design: [ADR-002](https://github.com/tl32rodan/scld-code-reviewer/blob/main/docs/architecture/ADR-002-regression-personality-option-a.md)
in the `scld-code-reviewer` repo (all phases complete as of 2026-05-18).

The `/regress` command:
1. Auto-discovers `regression/suite.json` at repo root
2. Calls `regressionx_run` via MCP
3. Maps results to a verdict using the table below
4. Emits `regression.md` (same Executive Summary conventions as `review.md`)

The `/checkin` command reads both `review.md` and `regression.md` before
allowing a commit to file — neither alone closes the quality loop.

Verdict mapping:

| easyreg summary | `/regress` verdict | `/checkin` impact |
|---|---|---|
| All PASS | `PASS` | Allowed |
| Any NEW (no FAIL) | `BORDERLINE` | Allowed with explicit human ack |
| Any FAIL | `VIOLATED` | Blocked |
| Any ERROR with no other signal | `N/A` (infra) | Allowed with warning |
| Any ERROR with some PASS | `BORDERLINE` (partial) | Allowed with explicit human ack |
| No suite configured | `N/A` (skip) | Allowed (regression.md not produced) |

### Pattern 3: CI/CD gate

easyreg runs in CI on every pull request. Failures block merge. This is the
computational layer of a continuous harness.

```yaml
# Example GitHub Actions step
- name: Regression check
  run: python -m easyreg run --config regression/suite.json --report-format json --report regression_result.json

- name: Fail on regression
  run: |
    python -c "
import json, sys
r = json.load(open('regression_result.json'))
fails = r['summary'].get('FAIL', 0)
if fails:
    print(f'Regression: {fails} case(s) FAILED')
    sys.exit(1)
print('Regression: all cases PASS')
"
```

---

## Guidelines for Coding Agents Using easyreg

### What agents MUST NOT do

- **Never call `regressionx_promote` automatically.** Promoting a golden is an
  explicit human decision. Auto-promotion hides regressions rather than surfacing
  them — the same anti-pattern Kent Beck warns about with agents deleting tests.
- **Never delete or modify files in `golden_dir`.** These are the ground truth.
- **Never modify `diff_rules` to suppress a FAIL.** This defeats the sensor.
- **Never modify `ignore_rules` to make a FAIL into PASS.** Same issue.

### What agents SHOULD do

- Call `regressionx_show_config` first to understand the suite structure.
- Call `regressionx_golden_status` to distinguish NEW (no golden yet) from FAIL
  (golden exists but output differs).
- On FAIL: inspect the `diffs` field, investigate the cause, fix the *code* (not
  the golden).
- On NEW: report to the human that golden promotion is needed with a clear summary
  of what the new output contains.
- On ERROR: report the environment issue; do not treat it as a test failure.

### The golden promotion protocol

```
Agent sees verdict=NEW
        ↓
Agent reports:
  "Case 'X' has no golden reference yet.
   New output is: [summary of output files].
   If this output is correct, promote it with:
     python -m easyreg promote --config suite.json --case X"
        ↓
Human reviews output and decides whether it is correct
        ↓
Human runs: python -m easyreg promote --config suite.json --case X
        ↓
Agent re-runs: regressionx_run → verdict should now be PASS
```

An agent that skips human review and auto-promotes is producing a corrupted
ground truth. The golden is only valid if a human confirmed it.

---

## Relationship to TDD

Kent Beck (2026): "TDD is a superpower when working with AI agents."

Unit tests (TDD) and easyreg regression tests are not substitutes:

| Level | Tool | What it verifies |
|---|---|---|
| Function / unit | TDD unit tests | Internal logic correctness |
| System / output | easyreg goldens | Observable behavior preservation |

A complete harness has both. The specific failure mode Beck warns about — agents
deleting unit tests to make them "pass" — applies equally to golden references:
an agent that modifies goldens to hide regressions is the same anti-pattern.

The `MUST NOT` list above directly addresses this for easyreg.

---

## Recommended Repo Layout for Projects Using Both Tools

```
repo/
├── regression/
│   ├── suite.json          ← suite config (auto-detected by scld-code-reviewer /regress)
│   ├── golden/             ← golden references (committed to git)
│   └── runs/               ← run outputs (add to .gitignore)
```

`.gitignore` addition:
```
regression/runs/
```

Suite config template with timestamp normalization:
```json
{
  "suite": "main",
  "golden_dir": "regression/golden/{case}",
  "output_dir": "regression/runs/{case}",
  "diff_rules": [
    {"type": "ignore_line", "pattern": "^#.*timestamp"},
    {"type": "ignore_regex",
     "pattern": "\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}",
     "replace": "<TIMESTAMP>"}
  ],
  "cases": []
}
```

The `regression/` layout is the convention expected by the `scld-code-reviewer`
`/regress` command (see [ADR-002](https://github.com/tl32rodan/scld-code-reviewer/blob/main/docs/architecture/ADR-002-regression-personality-option-a.md)).
Projects using a different path must configure it explicitly.

---

## Further Reading

- [easyreg SKILL.md](../SKILL.md) — MCP tool reference for agents
- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) — Fowler (2026)
- [scld-code-reviewer: ADR-002](https://github.com/tl32rodan/scld-code-reviewer/blob/main/docs/architecture/ADR-002-regression-personality-option-a.md) — regression personality full design
- [scld-code-reviewer: regression-personality-proposal.md](https://github.com/tl32rodan/scld-code-reviewer/blob/main/docs/research/regression-personality-proposal.md) — option analysis and history
