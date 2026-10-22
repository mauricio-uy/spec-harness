---
name: sdd-init
description: Sets up spec-driven development in a project by writing the system overview and glossary, configuring tests, release units and the release workflow, adding the harness block to AGENTS.md and generating the docs index. Use when installing the harness in a new or existing project, or when the overview or glossary is missing or outdated.
license: MIT
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  source: github.com/mauricio-uy/spec-harness
  version: "0.1.0"
---

# sdd-init

Give every agent working on the project a shared base: what the system is, the words it uses, and where everything lives.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing).

## Steps

1. If `.agents/docs/overview.md` or `glossary.md` already exists, update it instead of replacing it.
2. **Gather context**:
   - **New project**: ask the user, in one message, for the purpose, users, problem, non-goals, planned architecture and stack.
   - **Existing project**: explore before asking: README, package manifests, entry points, directory layout, domain models, database schema, existing tests. Ask only what the code cannot tell.
3. **Overview**: copy [the overview template](assets/overview.md) to `.agents/docs/overview.md` and fill it. One page at most.
4. **Glossary**: copy [the glossary template](assets/glossary.md) to `.agents/docs/glossary.md`. Add one row per domain term:
   - **In code**: the class, table or module that implements it.
   - **Avoid**: synonyms found in the code, docs or conversation that refer to the same concept.

   When the code uses two names for one concept, ask the user which one wins.
5. **Configuration**: propose `.agents/config.toml` to the user:
   - `[tests]`: the project's test runner, for the slice's acceptance tests (`{files}`) and the full suite.
   - `[[units]]`: one per independently released package or service; omit for a single release unit.
6. **Releases**: each slice is one branch and one squash-merged pull request, released after the merge. On GitHub, propose:
   - copying [the release workflow](assets/release.yml) to `.github/workflows/release.yml`;
   - squash merging with the pull request title and description as the commit message;
   - if `main` is protected, letting GitHub Actions bypass the protection so the workflow can push release commits and tags.

   Without the workflow, releases run locally after each merge: `sdd.py release --apply`, then `git push --follow-tags`.
7. Run `sdd.py init`: it adds the harness block to `AGENTS.md` (between `sdd:begin`/`sdd:end` markers, leaving the rest untouched) and generates the index.
8. Run `sdd.py lint` and fix what it reports.
9. **Checkpoint**: show the user the overview, glossary, configuration and release setup for review.

## Rules

- Do not reverse-engineer specs for existing behavior. The living spec grows as slices touch each area.
- Keep the overview short and free of lists that live elsewhere (capabilities in the index, decisions in ADRs).
