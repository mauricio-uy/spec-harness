# spec-harness

A minimalist harness for AI coding agents that combines spec-driven development (SDD) and test-driven development (TDD). It takes small vertical slices from idea to release, with gates checked by a script instead of by ceremony.

## Principles

- **Vertical slices.** One user-observable behavior per slice, 1–6 acceptance criteria, explicit boundaries and an explicit out of scope.
- **Specs are the contract, tests are the proof.** Each acceptance criterion becomes a test before any implementation exists, and those tests are frozen.
- **Gates, not approvals.** A stdlib-only Python CLI verifies every transition. People step in at three checkpoints only: the spec, the acceptance tests and the release.
- **Living spec.** Closed slices merge into a spec of how the system behaves today, traceable to its tests.
- **Continuous deployment.** Every closed slice is a release, with a Semantic Versioning bump, a Keep a Changelog entry, a Conventional Commit and a tag.

## Lifecycle

```
sdd-idea ──► sdd-spec ──► sdd-red ──► sdd-green ──► sdd-close
(optional)    draft→ready   ready→red    red→green     green→done + release
                   ✋            ✋                          ✋
```

✋ marks a checkpoint: the skill stops and waits for approval.

## Skills

The skills follow the [Agent Skills](https://agentskills.io/specification) standard and live in `.agents/skills/`.

| Skill        | Purpose                                                                                 |
|--------------|-----------------------------------------------------------------------------------------|
| `sdd-init`   | Set up a project: overview, glossary, test and release configuration, `AGENTS.md` block |
| `sdd-idea`   | Decompose an idea into candidate slices                                                 |
| `sdd-spec`   | Write a slice spec and take it to `ready`, or amend it                                  |
| `sdd-adr`    | Record a cross-cutting decision, or replace an outdated one                             |
| `sdd-red`    | Write the failing acceptance tests and freeze them                                      |
| `sdd-green`  | Implement with TDD until the frozen tests and the full suite pass                       |
| `sdd-close`  | Close the slice, merge it into the living spec and release it                           |
| `sdd-next`   | Run the next phase of a slice, stopping at checkpoints                                  |
| `sdd-status` | Report work in progress and what comes next                                             |

## CLI

`.agents/bin/sdd.py` owns every status change. Run it with `python3`, or `python` on Windows.

| Command                    | What it does                                                              |
|----------------------------|---------------------------------------------------------------------------|
| `init`                     | Add the managed block to `AGENTS.md` and generate the docs index          |
| `index [--check]`          | Regenerate the index, or verify it and `AGENTS.md` are current            |
| `status [SLICE]`           | List open slices, or show one slice and its next gate                     |
| `check SLICE`              | Verify the gate to the next status, running tests when needed             |
| `advance SLICE`            | Check the gate and move the slice to the next status                      |
| `reopen SLICE`             | Send a slice back to draft and unfreeze its acceptance tests              |
| `accept ADR`               | Accept a proposed ADR and supersede the one it replaces                   |
| `lint`                     | Check links, ID references, criterion-to-test traceability and vocabulary |
| `next-id {idea,slice,adr}` | Print the next free ID                                                    |
| `release SLICE [--apply]`  | Plan or apply the changelog entry, release commit and tags                |

## Installation

Requirements: git and Python 3.11 or later, on Linux, macOS or Windows. There are no dependencies to install.

1. Copy the `.agents/` folder of this repository into the root of your project. It includes its `LICENSE`; keep it with the copy.
2. Point your agent client at `.agents/skills/`. Client-specific adapters are not provided yet.
3. Run the `sdd-init` skill.

In your project, the harness creates its documents under `.agents/docs/`:

```
.agents/
  bin/sdd.py        CLI
  skills/           sdd-* skills
  config.toml       tests and release units
  docs/
    index.md        generated map
    overview.md     what the system is
    glossary.md     the system's vocabulary
    ideas/  changes/  archive/  specs/  adr/  runbooks/
```

## Configuration

`.agents/config.toml` is optional:

```toml
[tests]
paths = ["tests"]          # where acceptance tests live
slice = "pytest {files}"   # runs the slice's acceptance test files
full = "pytest"            # runs the full suite

[[units]]                  # release units; omit for a single unit tagged vX.Y.Z
name = "api"
paths = ["services/api"]   # tagged api/vX.Y.Z, changelog in services/api/CHANGELOG.md
```

## Development

This repository contains the harness itself. `.agents/` is the product; `tests/` and `.github/` support its development and are not copied into projects.

```bash
python3 -m unittest discover -s tests
```

The CI runs the suite on Linux, macOS and Windows with Python 3.11 and 3.14.

## License

[MIT](LICENSE)
