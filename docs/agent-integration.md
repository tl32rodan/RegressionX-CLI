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

**June 2026 constitutive definition** — an agent harness has four necessary and
sufficient elements. easyreg's role in a full harness:

| Harness element | easyreg's contribution |
|---|---|
| Agent loop | Regression run → verdict → fix loop (via `/regress` in scld-code-reviewer) |
| Tool interface | MCP server: `regressionx_run`, `regressionx_compare`, `regressionx_promote`, etc. |
| Context management | `regressionx_show_config` provides suite structure before running |
| Control mechanisms | Human-only golden promotion; NEVER auto-promote golden files |

---

## Background: Test-Oriented Programming (TOP, April 2026)

Source: [arxiv:2604.08102 — Test-Oriented Programming: rethinking coding for the GenAI era](https://arxiv.org/abs/2604.08102)

TOP is an emerging paradigm that extends TDD to its logical conclusion in the AI age:

| Dimension | TDD | **TOP** |
|---|---|---|
| Who writes tests | Developer | Developer |
| Who writes production code | Developer (guided by tests) | **AI** (generated from tests) |
| Primary developer output | Tests + code | **Tests only** |
| Role of tests | Red/green/refactor cycle | **Specification + verification** |

In TOP, tests are the *specification*. Production code is generated and regenerated
by AI as needed. The developer's job is to write complete, correct tests — not to
write implementation.

**How easyreg golden files relate to TOP:**

Golden files are an *output-level* analog of TOP test specs. They define what the
system must produce at the command/system output boundary. Just as a developer's
unit tests are the spec for production logic in TOP, golden files are the spec for
observable system behavior.

Consequence: modifying a golden file to make a regression disappear is the output-level
equivalent of deleting a unit test in TOP. Both actions destroy the specification.
This is why the hard constraint below — **NEVER call `regressionx_promote`** —
exists and is non-negotiable.

Kent Beck's warning (2026): *"Agents delete tests to make them 'pass'."* applies
equally to golden files.

---

## Background: TDAD — Test-Driven Agentic Development (March 2026)

Source: [arxiv:2603.17973](https://arxiv.org/abs/2603.17973) — ACM AIWare 2026
Accessible secondary summary: [thelgtm.dev](https://thelgtm.dev/tdad-test-driven-agentic-development-reducing-code-regressions-by-70/)

TDAD proves two things relevant to easyreg:

1. **Procedural TDD instructions don't reduce regressions.** Telling an agent
   step-by-step how to do TDD in text produces no measurable improvement in
   regression rates (baseline: 6.08% → still ~6%).

2. **Structured graph context does.** An AST-based code-test dependency graph,
   surfaced to the agent before it commits a change, reduces regressions by 70%
   (6.08% → 1.82%) and improves resolution rate from 24% to 32%.

The TDAD insight for easyreg: if the agent knows *which test cases are sensitive
to a given diff* before running the full suite, it can self-correct at the right
moment rather than discovering failures after the fact. This motivates the
`regressionx_impact` proposal in Pattern 5 below.

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

The `scld-code-reviewer` agent uses easyreg MCP tools via its standalone
`/regress` command. The regression personality is separate from `/review` —
both can be required before `/checkin` allows filing, and both run identically
from a developer terminal and from CI.

Full design: `docs/architecture/ADR-002-regression-personality-option-a.md`
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

### Pattern 4: TOP workflow integration

In a Test-Oriented Programming workflow, easyreg golden files serve as the
output-level specification alongside unit tests:

```
Developer writes unit tests (specification for internal logic)
Developer writes / updates golden files (specification for system output)
        ↓
AI generates production code to satisfy unit tests
        ↓
easyreg run — confirm generated code also satisfies output goldens
        ↓
  PASS: both specs satisfied
  FAIL: generated code broke observable behavior — AI must fix code, not goldens
  NEW:  a new output boundary appeared — human reviews before promoting
```

In TOP mode, the invariant is especially strict: **no agent may promote a golden
or modify a golden without explicit human review**, because goldens are specifications,
not incidental artifacts.

### Pattern 5: TDAD-Inspired Diff-Aware Triage (Proposed)

Motivated by the TDAD paper (arxiv:2603.17973, March 2026): surfacing affected
tests *before* a full run reduces regressions by 70% because the agent can
self-correct at the moment it has the diff in context.

**Requires a new MCP tool `regressionx_impact` (not yet implemented):**

```
coding agent has a diff (changed files from git diff --name-only)
        ↓
Step 1: regressionx_impact(config_path, changed_files)
        → affected_cases: ["case_a", "case_c"]
        → all_cases: ["case_a", "case_b", "case_c"]
        Agent sees: "2 of 3 cases may be affected by this diff"
        ↓
Step 2: regressionx_run(config_path, case_name=affected_cases[0]) — run triage
        If any FAIL → agent self-corrects immediately (has diff + failure in context)
        If all PASS → proceed to full suite
        ↓
Step 3: regressionx_run(config_path) — full suite (safety net)
        Reports final verdict in regression.md
```

**Proposed `regressionx_impact` tool signature:**

```python
@mcp.tool()
def regressionx_impact(config_path: str, changed_files: list[str]) -> dict:
    """Given changed files (e.g. from git diff --name-only), return which
    test cases are likely affected by those changes.

    Approximation: a case is flagged if its command string references
    any changed file, or if its golden_dir path shares a directory
    subtree with any changed file.

    Note: impact analysis is best-effort. The full suite remains
    authoritative — indirect dependencies (shared utilities, config)
    may not be captured by path-matching alone.

    Returns:
      affected_cases: list of case names likely sensitive to this diff
      all_cases: full list of case names in the suite
    """
```

**Implementation note**: This requires changes to both easyreg (`mcp_server.py`)
and the `/regress` skill body in `scld-code-reviewer`. Both must be updated
together — they share a behavioral contract. See `scld-code-reviewer:
docs/research/2026-06-expert-insights.md` Proposal 4 for the full plan.

---

## Guidelines for Coding Agents Using easyreg

### What agents MUST NOT do

- **Never call `regressionx_promote` automatically.** Promoting a golden is an
  explicit human decision. Auto-promotion hides regressions rather than surfacing
  them — this is the output-level equivalent of deleting a unit test in TOP mode
  (Kent Beck, 2026; TOP paper arxiv:2604.08102).
- **Never delete or modify files in `golden_dir`.** These are the ground truth
  specification.
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
- (When available) Call `regressionx_impact` with changed files before a full run
  to focus investigation on the most likely failure points.

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

## Relationship to TDD and TOP

Kent Beck (2026): "TDD is a superpower when working with AI agents."

Unit tests (TDD/TOP) and easyreg regression tests are not substitutes:

| Level | Tool | What it verifies | In TOP mode |
|---|---|---|---|
| Function / unit | TDD unit tests | Internal logic correctness | Developer-written specification |
| System / output | easyreg goldens | Observable behavior preservation | Output-level specification |

A complete harness has both. The specific failure mode Beck warns about — agents
deleting unit tests to make them "pass" — applies equally to golden references:
an agent that modifies goldens to hide regressions is the same anti-pattern.

The TDAD finding (2026) adds a third layer: even with TDD/goldens in place,
agents that are *only told about TDD in text* still introduce regressions at the
baseline rate. Structured context (impact graphs, explicit affected-case surfacing)
is what actually reduces regressions. Pattern 5 (regressionx_impact) is easyreg's
contribution to this structured-context layer.

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
`/regress` command (see `docs/architecture/ADR-002-regression-personality-option-a.md`
in the `scld-code-reviewer` repo). Projects using a different path must configure
it explicitly.

---

## Further Reading

- [easyreg SKILL.md](../SKILL.md) — MCP tool reference for agents
- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) — Fowler (Apr 2026)
- [Test-Oriented Programming: rethinking coding for the GenAI era](https://arxiv.org/abs/2604.08102) — arxiv:2604.08102 (Apr 2026)
- [TDAD: Test-Driven Agentic Development](https://arxiv.org/abs/2603.17973) — arxiv:2603.17973 (Mar 2026); [secondary summary](https://thelgtm.dev/tdad-test-driven-agentic-development-reducing-code-regressions-by-70/)
- `scld-code-reviewer: docs/architecture/ADR-002-regression-personality-option-a.md` — regression personality full design
- `scld-code-reviewer: docs/research/regression-personality-proposal.md` — option analysis and history
- `scld-code-reviewer: docs/research/2026-05-expert-insights.md` — full expert insights index (May)
- `scld-code-reviewer: docs/research/2026-06-expert-insights.md` — June 2026 insights (TDAD, Trust Factory, Proposals 4–6)

---

## Session Log

| Date | Topics | Changes made |
|---|---|---|
| 2026-05-18 | Initial agent integration guide created | All patterns 1–3, guidelines, promotion protocol |
| 2026-05-21 | TOP paradigm (arxiv:2604.08102) added | Pattern 4, TOP grounding for MUST NOT rules, updated TDD/TOP comparison table |
| 2026-06-18 | TDAD paper (arxiv:2603.17973); harness constitutive definition | Pattern 5 (diff-aware triage, proposed); TDAD background section; harness element table; TDAD in further reading; updated relationship section |
