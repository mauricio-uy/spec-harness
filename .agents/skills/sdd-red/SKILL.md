---
name: sdd-red
description: Writes the failing acceptance tests of a ready slice, at least one per acceptance criterion, and freezes them. Use when a slice spec is ready and approved, or when asked to write acceptance tests for a slice.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  author: spec-harness
  version: "0.1.0"
---

# sdd-red

Turn each acceptance criterion into an executable test that fails for the right reason, before any implementation exists.

## Harness

- Docs: `.agents/docs/` with `index.md` (generated map: read it first), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Run `sdd.py init` once per project.
- The CLI owns the `status` field: never edit it by hand.

## Setup

The gate runs the tests through `.agents/config.toml`. If `[tests]` is missing, detect the project's test runner and propose it to the user:

```toml
[tests]
paths = ["tests"]          # where acceptance tests live
slice = "pytest {files}"   # {files} expands to the slice's acceptance test files
full = "pytest"            # the whole suite
```

## Steps

1. Read `.agents/docs/changes/<ID>-*/spec.md`: criteria, boundaries and constraints. The user approved the spec, and with it every ADR in its `adrs` field: run `sdd.py accept <ADR>` for each one still `proposed`.
2. Write the tests in **dedicated files for this slice**, following the project's test conventions (for example `tests/acceptance/test_s012_reset_password.py`). The gate freezes whole files, so do not mix them with other tests.
3. One or more tests per active criterion. Each test:
   - carries the tag `<ID>/AC-n` in its name, a marker or a comment next to it;
   - drives the slice through its **Input** boundary and asserts on its **Output**, never on internals;
   - follows the criterion's Given/When/Then literally.
4. Do not write implementation. When the language needs it to compile, add only empty stubs at the boundary (signatures that raise "not implemented").
5. Run `sdd.py check <ID>` and read the test output: every test must fail on a missing behavior (assertion, not-implemented stub, missing endpoint). A syntax error, a bad import of test helpers or a misconfigured runner is a broken test: fix it.
6. Run `sdd.py advance <ID>`: the tests are frozen in `.frozen.json`.

## Checkpoint

Show the user each criterion next to its test and stop. After this point the tests cannot change without `sdd-spec` reopening the slice.
