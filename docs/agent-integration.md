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

### Pattern 5: VibeSec Security Hardening in CI

The VibeSec Reckoning (Fowler/Thoughtworks, 2026) established that AI agents
default to insecure configurations (open CORS, missing auth, over-broad IAM).
Security is a sensor concern, not a prompt concern.

For projects using easyreg in CI, the hardened pipeline is:

```
coding agent produces change
        ↓
automated security checks (static analysis, dependency scan)  ← SEC sensors
        ↓
easyreg run (output behavior preserved?)                      ← external quality sensor
        ↓
code review agent (/review)                                   ← inferential sensor
        ↓
/checkin gate
```

Security checks run *before* easyreg (cheaper; catch a distinct failure class).
A FAIL in either layer blocks the checkin. The SEC protocol category in
`scld-code-reviewer` provides the inferential security review on top.

---

## The Böckeler Sensor Quality Stack (2026)

Source: [Birgitta Böckeler — Maintainability Sensors for Coding Agents](https://martinfowler.com/articles/sensors-for-coding-agents.html)
(Thoughtworks Global Lead for AI-assisted Software Delivery, QCon London 2026)

Böckeler defines three quality dimensions, each requiring a different sensor:

| Quality Dimension | What it verifies | Sensor | easyreg? |
|---|---|---|---|
| **External quality** | Observable behavior at output boundary | Golden-file regression | ✓ **easyreg's lane** |
| Internal quality | Code structure, coupling, complexity | Static analysis, linters | ✗ separate tools |
| **Test quality** | Do tests actually protect anything? | **Mutation testing** | ✗ complementary tool |

**easyreg covers external quality**: deterministic comparison of system outputs
against golden references across code changes. This catches behavioral regressions
at the boundary where the system meets the world.

**Mutation testing** (e.g. `mutmut`, `cosmic-ray`, `stryker`) covers test quality:
it deliberately introduces small bugs into the source code and verifies that the
test suite catches them. Böckeler identifies this as the *strongest* available
sensor — agents can write test suites that are always green but protect nothing,
and only mutation testing exposes this.

**Why both matter**: an agent can satisfy easyreg (output behavior preserved)
while having a hollow test suite that would miss real regressions in a future
change cycle. The layers are independent:

```
Unit tests (TDD/TOP)           ← specification for internal logic
Mutation testing               ← verifies the unit tests are meaningful
easyreg golden-file regression ← specification for observable system behavior
Code review (/review)          ← inferential check across all dimensions
```

**Rippable harness principle** (Böckeler, QCon London 2026): design harness
components to be easy to remove as models improve. Each sensor layer should have
a stated removal or upgrade trigger — not permanent infrastructure. When Claude 5.x
ships, some of the error-recovery logic in the current harness may become dead weight.

**Status for SCLD**: easyreg (external quality) is the current correct first layer.
Mutation testing (test quality) is deferred — requires the SCLD team to adopt a
mutation testing tool. See Proposal 5 in
`scld-code-reviewer/docs/references/ai-era-engineering.md`.

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

Unit tests (TDD/TOP), mutation testing, and easyreg regression tests are not substitutes:

| Level | Tool | What it verifies | In TOP mode |
|---|---|---|---|
| Function / unit | TDD unit tests | Internal logic correctness | Developer-written specification |
| Test suite validity | Mutation testing | Unit tests catch real bugs | Sensor for test quality |
| System / output | easyreg goldens | Observable behavior preservation | Output-level specification |

A complete harness has all three. The specific failure mode Beck warns about — agents
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
`/regress` command (see `docs/architecture/ADR-002-regression-personality-option-a.md`
in the `scld-code-reviewer` repo). Projects using a different path must configure
it explicitly.

---

## Further Reading

- [easyreg SKILL.md](../SKILL.md) — MCP tool reference for agents
- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) — Fowler (2026)
- [Maintainability Sensors for Coding Agents](https://martinfowler.com/articles/sensors-for-coding-agents.html) — Böckeler (2026)
- [Test-Oriented Programming: rethinking coding for the GenAI era](https://arxiv.org/abs/2604.08102) — arxiv:2604.08102 (April 2026)
- [The VibeSec Reckoning](https://martinfowler.com/articles/vibesec-reckoning.html) — Fowler/Thoughtworks (2026)
- `scld-code-reviewer: docs/architecture/ADR-002-regression-personality-option-a.md` — regression personality full design
- `scld-code-reviewer: docs/research/regression-personality-proposal.md` — option analysis and history
- `scld-code-reviewer: docs/research/2026-05-expert-insights.md` — expert insights index (May 2026)
- `scld-code-reviewer: docs/research/2026-06-expert-insights.md` — expert insights index (June 2026)

---

## Session Log

| Date | Topics | Changes made |
|---|---|---|
| 2026-05-18 | Initial agent integration guide created | All patterns 1–3, guidelines, promotion protocol |
| 2026-05-21 | TOP paradigm (arxiv:2604.08102) added | Pattern 4, TOP grounding for MUST NOT rules, updated TDD/TOP comparison table |
| 2026-06-30 | Böckeler sensor stack; VibeSec security hardening; rippable harness | Pattern 5 (VibeSec CI), Böckeler Sensor Quality Stack section, updated TDD/TOP/mutation comparison table, new Further Reading entries |
