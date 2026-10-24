---
name: sdd-fix
description: Fixes a bug through a small slice, writing a short spec and the failing tests that reproduce it, and stopping at one checkpoint for both before the fix is implemented, closed and released. Use when existing behavior is wrong and the fix needs at most two acceptance criteria, or when asked to fix a bug, a regression or a vulnerability.
license: MIT
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py and the other sdd-* skills.
metadata:
  source: github.com/mauricio-uy/spec-harness
  version: "0.1.0"
---

# sdd-fix

A bug changes behavior, so it goes through a slice and is released with a note. A fix slice keeps every gate but has a shorter spec and one checkpoint instead of two before the code: the failing test is the best description of the bug.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary: read them first), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Set the harness up once per project with `sdd-init`.
- Reference harness documents by ID (`S-012`, `S-012/AC-1`, `ADR-003`), never by path.
- The CLI owns the `status` field: never edit it by hand.

## When

- **Fix slice**: existing behavior is wrong, and one or two criteria reproduce it.
- **Regular slice** (`sdd-spec`): the fix needs new behavior, more criteria, a design choice worth a plan, or a new ADR.
- **No slice**: the change keeps behavior (refactor, docs, CI, a dependency update). It goes as one pull request with a Conventional Commit title and ships in its unit's next release without a note.

## Spec

1. Get an ID with `sdd.py next-id slice` and create the slice branch from an up-to-date `main`: `git switch -c slice/<ID>-<slug>`.
2. Create `.agents/docs/changes/<ID>-<slug>/` and copy [the fix template](assets/fix.md) into it as `spec.md`.
3. Reproduce the bug before writing it down. Read the living spec of the capability: a criterion the code breaks is the source of **Expected**.
4. Fill the spec:
   - `change`: `fixed`, or `security` for a vulnerability;
   - **Goal**, **Bug** (`Actual` and `Expected`) and **Boundaries**, writing `none` where nothing applies;
   - one or two criteria, `- **AC-n:** Given …, when …, then …`, that fail today and pass once fixed, observable from the boundary;
   - the glossary's terms, never its Avoid aliases.
5. Ask the user every open question in one message and fold the answers back until **Open questions** is empty.
6. Remove every template comment and placeholder, then run `sdd.py advance <ID>`. There is no checkpoint here.

## Failing tests

1. Write the tests in **dedicated files for this slice**, following the project's test conventions and `.agents/config.toml` (its `[tests]` section, including `support` and any name selector). Each test carries the tag `<ID>/AC-n` in its name, a marker or a comment, drives the slice through its **Input** and asserts on its **Output**.
2. Do not fix anything yet.
3. Run `sdd.py check <ID>`: every test must fail on the bug, not on a broken test, import or runner.
4. Run `sdd.py advance <ID>`: the tests are frozen.

## Checkpoint

Show the user the bug (actual and expected), each criterion next to its test, and the failing output, and stop. Their approval covers the spec and the tests.

After approval, continue with `sdd-green`, then `sdd-close`, which stops at the pull request. When closing, the runbook, idea and overview items are usually `n/a`.

## Rules

- The CLI keeps a fix slice small: `change` is `fixed` or `security`, at most 2 criteria, no plan, and only accepted ADRs.
- When the fix outgrows those limits, it becomes a regular slice: run `sdd.py reopen <ID>` if it is past `draft`, remove `track: fix` from the spec and continue with `sdd-spec`, whose checkpoints apply from then on.
- Defects found on the way are separate slices, never part of this one.
