---
name: sdd-red
description: Writes the failing acceptance tests of a ready slice, at least one per acceptance criterion, and freezes them. Use when a slice spec is ready and approved, or when asked to write acceptance tests for a slice.
license: MIT
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  source: github.com/mauricio-uy/spec-harness
  version: "0.1.0"
---

# sdd-red

Turn each acceptance criterion into an executable test that fails for the right reason, before any implementation exists.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary: read them first), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Set the harness up once per project with `sdd-init`.
- Reference harness documents by ID (`S-012`, `S-012/AC-1`, `ADR-003`), never by path.
- The CLI owns the `status` field: never edit it by hand.

## Setup

The gate runs the tests through `.agents/config.toml`. If `[tests]` is missing, detect the project's test runner and propose it to the user:

```toml
[tests]
paths = ["tests"]          # where acceptance tests live
slice = "pytest {files}"   # runs only the slice's acceptance tests
full = "pytest"            # the whole suite
support = ["tests/acceptance/conftest.py", "tests/acceptance/helpers"]   # optional, frozen with the tests
red_exit = [1]             # optional: pytest exits 1 when tests fail, 2 on collection errors, 5 with no tests
```

- `slice`: a string, or a list of arguments when a pattern needs quoting. Placeholders:
  - `{files}`: one argument per acceptance test file of the slice;
  - `{dirs}`: one argument per folder holding them, as `./path` (Go packages);
  - `{id}` and `{ident}`: replaced inside any argument by `S-012` and `S012`. Use `{ident}` to select tests by name.

  | Runner       | `paths`        | `slice`                                                        | `full`             |
  |--------------|----------------|----------------------------------------------------------------|--------------------|
  | pytest       | `["tests"]`    | `"pytest {files}"`                                             | `"pytest"`         |
  | Jest, Vitest | `["tests"]`    | `"npx jest {files}"`                                           | `"npx jest"`       |
  | Go           | `["."]`        | `["go", "test", "-run", "{ident}", "{dirs}"]`                  | `"go test ./..."`  |
  | Gradle       | `["src/test"]` | `["./gradlew", "test", "--tests", "*{ident}*"]`                | `"./gradlew test"` |
  | Maven        | `["src/test"]` | `["mvn", "test", "-Dtest=*{ident}*"]`                          | `"mvn test"`       |
  | .NET         | `["tests"]`    | `["dotnet", "test", "--filter", "FullyQualifiedName~{ident}"]` | `"dotnet test"`    |

  Selecting by name runs the tests whose name contains `{ident}`, so every acceptance test of the slice must carry it (step 3), and no other test may.
- `support`: the fixtures and helpers that acceptance tests rely on, as globs or folders. They are frozen with the slice's tests, so a test cannot be made to pass by changing what surrounds it. Fixtures for unit tests go elsewhere.
- `red_exit`: the runner's exit codes for tests that ran and failed. Set it when the runner tells failures apart from broken tests (pytest, jest: `[1]`); leave it out when it does not (unittest).

## Steps

1. Read `.agents/docs/changes/<ID>-*/spec.md`: criteria, boundaries and constraints. The user approved the spec, and with it every ADR in its `adrs` field: run `sdd.py accept <ADR>` for each one still `proposed`.
2. Write the tests in **dedicated files for this slice**, following the project's test conventions (for example `tests/acceptance/test_s012_reset_password.py`). The gate freezes whole files, so do not mix them with other tests. Put the fixtures and helpers they need under `tests.support`.
3. One or more tests per active criterion. Each test:
   - carries the tag `<ID>/AC-n` in its name, a marker or a comment next to it;
   - when `tests.slice` selects by name, also has the compact ID in its name or its class name, e.g. `TestS012ResetsPassword` or `ResetPasswordS012Test`;
   - drives the slice through its **Input** boundary and asserts on its **Output**, never on internals;
   - follows the criterion's Given/When/Then literally.
4. Do not write implementation. When the language needs it to compile, add only empty stubs at the boundary (signatures that raise "not implemented").
5. Run `sdd.py check <ID>` and read the test output: every test must fail on a missing behavior (assertion, not-implemented stub, missing endpoint). A syntax error, a bad import of test helpers or a misconfigured runner is a broken test: fix it.
6. Run `sdd.py advance <ID>`: the tests, and the files under `tests.support`, are frozen in `.frozen.json`.

## Checkpoint

Show the user each criterion next to its test and stop. After this point the tests cannot change without `sdd-spec` reopening the slice.
