---
name: sdd-revise
description: Applies review feedback to the open pull request of a closed slice, changing code, closing documents or, after reopening the slice, its spec and acceptance tests, and keeps the pull request title and body in line. Use when a reviewer requests changes on a slice's pull request, or when asked to address its review comments before it is merged.
license: MIT
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py and the other sdd-* skills; updating the pull request uses the GitHub CLI (gh).
metadata:
  source: github.com/mauricio-uy/spec-harness
  version: "0.1.0"
---

# sdd-revise

A slice is finished when its commit reaches `main`, not when it is archived. Until then, review feedback goes into the same branch and pull request, under the same gates.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary: read them first), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Set the harness up once per project with `sdd-init`.
- Reference harness documents by ID (`S-012`, `S-012/AC-1`, `ADR-003`), never by path.
- The CLI owns the `status` field: never edit it by hand.

## Steps

1. Switch to the slice branch and bring it up to date. Read the review comments, e.g. with `gh pr view <number> --comments`.
2. **Classify** each requested change:

   | Kind          | What it touches                                                                    | How                          |
   |---------------|------------------------------------------------------------------------------------|------------------------------|
   | **Code**      | implementation and unit tests, within the spec's criteria and boundaries           | [Code](#code)                |
   | **Documents** | `close.md`, the living spec, runbooks, `overview.md`, `glossary.md`, the idea      | [Documents](#documents)      |
   | **Spec**      | goal, scope, boundaries, acceptance criteria or acceptance tests                   | [Spec](#spec)                |
   | **Out**       | behavior the spec leaves out                                                       | a new candidate, not here    |

   When a comment fits more than one kind, apply each. For **Out**, add a candidate to the slice's idea, or propose `sdd-idea`, and say so in the reply.
3. Apply the changes, then run the steps in [Pull request](#pull-request).

### Code

- Never modify, delete or skip a file listed in the slice's `.frozen.json`. A comment that needs an acceptance test changed is a **Spec** change.
- Grow the change with TDD, as in `sdd-green`, and run the full suite (`tests.full` in `.agents/config.toml`).
- A change that departs from the spec's plan, or adds or pays off debt, is also a **Documents** change: record it in `close.md`.

### Documents

Edit them directly. The slice stays closed: `close.md` still accounts for every criterion, every merge item stays ticked, and the living spec still holds every active criterion with its origin ID.

### Spec

1. Run `sdd.py reopen <ID>`. While the slice is not on `main`, it moves back to `.agents/docs/changes/`, returns to `draft` and its acceptance tests are unfrozen. Once merged, it cannot be reopened: the change is a new slice.
2. If the slice came from an idea, set its candidate back to `specced`.
3. Follow the lifecycle again, with its checkpoints: amend the spec with `sdd-spec` (never renumber criteria), then `sdd-red`, `sdd-green` and the closing steps of `sdd-close`, which update `close.md` and the living spec.

## Pull request

1. Commit the changes on the slice branch with explicit paths. Leave unrelated changes out.
2. Run `sdd.py verify --base origin/main` and fix every error. It checks the slices the branch closes against every gate they passed, so a tampered acceptance test or a criterion missing from the living spec fails here as it will in CI.
3. Run `sdd.py pr <ID>` and compare it with the pull request's current title and body (`gh pr view <number> --json title,body`). Squash merges use them as the commit message, and the release notes come from it.
4. **Checkpoint**: show the user, per comment, its kind and what changed, the new title and body if they differ, and any reply to the reviewer. Wait for confirmation.
5. Push the branch. If the title or body changed, update them: `gh pr edit <number> --title "$(sdd.py pr <ID> --title)" --body "$(sdd.py pr <ID> --body)"`. Post the confirmed replies.
6. Do not merge unless the user asks.
