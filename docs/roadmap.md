# easyreg Roadmap — Agent Integration & scld-code-reviewer Synergy

Living document. Updated each development session. See git log for history.

---

## Vision

easyreg is a **computational feedback sensor** in the harness engineering model
(Fowler, 2026). It pairs with an **inferential feedback sensor** (`scld-code-reviewer`)
to form a complete quality harness around AI coding agents:

```
Coding agent changes code
        ↓
easyreg run           ← computational: did observable behavior change?
        ↓
scld-code-reviewer    ← inferential: does the code follow design rules?
        ↓
/checkin gate         ← reads both; neither alone is sufficient
```

Neither tool is sufficient alone:
- easyreg catches behavioral regressions that code review would miss
- code review catches design violations and optionality erosion that golden
  files cannot detect (see Beck "Genie Tarpit", 2026)

---

## Current State (Phase 1 — Complete)

**All items complete as of 2026-05-18.**

| Feature | Status |
|---|---|
| CLI: run / compare / promote / golden-status / show-config | ✅ |
| JSON suite config with diff_rules | ✅ |
| Parallel execution (`--parallel N`) | ✅ |
| Markdown + JSON report formats | ✅ |
| MCP server (`mcp_server.py`) via FastMCP | ✅ |
| SKILL.md agent usage guide | ✅ |
| docs/agent-integration.md (harness model, TOP, patterns) | ✅ |
| scld-code-reviewer `/regress` personality consumes easyreg via MCP | ✅ |
| `/checkin` gate reads both review.md and regression.md | ✅ |

**Design constraints (non-negotiable):**
- Golden files are the specification; agents MUST NOT auto-promote
- Zero external dependencies for core CLI (Python stdlib only)
- FastMCP required only for MCP server

---

## Phase 2 — Enhanced Reporting & Tighter Review Integration

**Status: Planned. Not yet started.**

Goal: make the easyreg ↔ scld-code-reviewer integration more seamless and
the regression verdict more informative for human reviewers.

### 2a. Structured regression verdict in regression.md

Currently `/regress` in scld-code-reviewer emits a `regression.md` file.
The format follows review.md conventions (Executive Summary table), but the
diff detail is limited.

Improvement: when cases FAIL, include a structured per-case breakdown in
`regression.md` showing:
- Which golden files differ
- The first N lines of the diff (configurable)
- A one-line "likely cause" inference from the diff shape

This makes `regression.md` a richer document for the human reviewer to
diagnose without running the tool again.

**Where this work lives:** primarily in the easyreg reporter module
(`easyreg/reporter/`) + the `/regress` skill in scld-code-reviewer.

### 2b. PR-comment mode for CI

Add a `--pr-comment` flag or a separate `pr_comment_format` reporter that
produces GitHub-flavoured markdown suitable for posting as a PR comment.

Format:
```
## Regression Check
| Case | Verdict | Changed files |
|------|---------|---------------|
| hello | ✅ PASS | — |
| world | ❌ FAIL | output.txt |

<details><summary>Diff for 'world/output.txt'</summary>
...
</details>
```

**Benefit:** closes the gap between easyreg and the Braintrust/LangSmith-style
CI feedback that 2026 community consensus considers standard. No new dependency
needed — reporter just formats existing diff data differently.

### 2c. easyreg as a named MCP server in All-Might

Currently easyreg's MCP server is configured manually by the user. Proposal:
ship a standard MCP config snippet in `docs/agent-integration.md` that
All-Might-managed projects can drop into their `CLAUDE.md` or
`opencode.json` without bespoke setup.

Template:
```json
{
  "mcpServers": {
    "regressionx": {
      "command": "python",
      "args": ["<path-to-easyreg>/mcp_server.py"]
    }
  }
}
```

Companion: add a "quick-start for scld-code-reviewer users" section to
`SKILL.md` pointing to the ADR-002 integration design.

---

## Phase 3 — Targeted Test Selection (TDAD-Inspired)

**Status: Aspirational. Do not implement until Phase 2 is complete
and suite size justifies it.**

### Background: TDAD paper (arxiv:2603.17973, March 2026)

Test-Driven Agentic Development (TDAD) performs pre-change impact analysis
using an AST-based code-test dependency graph. Before the agent commits a
patch, it identifies which tests are most affected and verifies only those
first — reducing test-level regressions by 70% while keeping the fast-path
tight.

TDAD operates at the unit-test level. easyreg operates at the system-output
level. They are complementary (see `scld-code-reviewer/docs/research/2026-05-expert-insights.md`
Academic Research section for the comparison table).

### The easyreg Phase 3 analog

For easyreg, the TDAD-inspired enhancement would be:
1. Add a lightweight **change-to-case mapping file** (e.g., `suite.json` gains
   an optional `case_triggers` field: `{"case_name": ["glob_patterns_of_files_that_affect_this_case"]}`).
2. A `--affected-by <changed_files>` flag that, given a list of changed files,
   returns only the cases whose triggers match.
3. Agents can then run `easyreg run --affected-by $(git diff --name-only)` for
   fast pre-commit feedback, and `easyreg run` (full suite) as the CI gate.

**When to implement:**
- Suite has 50+ cases AND full-suite run time exceeds ~2 minutes
- OR a concrete agent workflow shows agents waiting on full-suite runs before
  proceeding with next steps

**Simplicity principle:** the existing `--case` flag already handles targeted
runs for known cases. Phase 3 only adds value when the mapping from "changed
files" to "affected cases" is non-obvious and the agent should not have to
know it. Do not add this complexity before that need is demonstrated.

### Design sketch (for future implementation)

`suite.json` extension (fully backward-compatible; `case_triggers` is optional):
```json
{
  "suite": "main",
  "golden_dir": "regression/golden/{case}",
  "output_dir": "regression/runs/{case}",
  "cases": [
    {
      "name": "hello",
      "command": "...",
      "case_triggers": ["src/hello.py", "src/greeting/**"]
    }
  ]
}
```

New CLI flag:
```bash
easyreg run --config suite.json --affected-by src/hello.py src/world.py
# → runs only cases whose case_triggers match one of the listed files
# → if no case_triggers defined anywhere, falls back to running all cases
```

MCP tool extension: add `affected_files` optional parameter to
`regressionx_run`.

---

## Design Principles (Non-Negotiable)

These apply to all phases:

1. **Agents NEVER auto-promote.** Golden files are the specification (TOP paradigm,
   Beck/arxiv:2604.08102). Human approval is always required for golden promotion.
2. **Zero external dependencies for core CLI.** FastMCP is optional (MCP server
   only). Any new reporter or analysis layer must be opt-in.
3. **Backward compatibility.** New suite.json fields are always optional.
   Existing suites run without change after any easyreg version upgrade.
4. **Simplicity gate.** Every feature must pass: "does this justify the complexity
   it adds?" Reference: if the existing `--case` flag covers the need, the
   new feature is premature.
5. **Outcome-orientation** (Beck, "Nobody Wants Agents", Apr 2026): the goal is
   correct, stable system behavior — not sophisticated tooling. Tooling serves
   the outcome; it is not an end in itself.

---

## Session Log

| Date | Topics | Changes |
|---|---|---|
| 2026-05-26 | Phase 2 + Phase 3 design; TDAD complementarity; scld-code-reviewer synergy vision | This document created |
