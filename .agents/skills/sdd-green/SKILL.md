---
name: sdd-green
description: Implements a slice whose acceptance tests are red, using test-driven development until they and the full suite pass. Use when a slice is in red status with approved acceptance tests, or when asked to implement a slice.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  author: spec-harness
  version: "0.1.0"
---

# sdd-green

Make the frozen acceptance tests pass with the simplest design that satisfies the spec, growing it through TDD.

## Harness

- Workspace: `.agents/` with `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing).
- The CLI owns the `status` field: never edit it by hand.

## Rules

- **Never modify, delete or skip a file listed in the slice's `.frozen.json`.** If an acceptance test looks wrong, stop and tell the user; the fix goes through `sdd-spec` (reopen).
- Stay inside the spec's **Boundaries**. Touching a module not listed under **Touches** is either a spec amendment or a deviation to record in `close.md`; ask when in doubt.
- Follow `plan.md` (or the plan sections in `spec.md`) when present, ticking tasks as they pass.

## Steps

1. Pick the next failing acceptance test, in criterion order.
2. Inner TDD loop until it passes:
   1. **Red**: write a small unit test for the next piece of behavior and watch it fail.
   2. **Green**: write the minimum code to pass it.
   3. **Refactor**: clean up with all tests green.
3. Repeat for every criterion, then run the full suite and fix regressions.
4. Run `sdd.py advance <ID>`. It verifies the frozen files are untouched and runs the slice and full suites.
5. Report which criteria pass and any deviation or debt worth recording in `close.md`.
