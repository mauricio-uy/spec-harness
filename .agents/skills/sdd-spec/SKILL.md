---
name: sdd-spec
description: Writes or amends the spec of one vertical slice and takes it from draft to ready, covering scope, boundaries, Given/When/Then acceptance criteria and an optional plan. Use when starting a slice from an idea candidate or a small request, or when an in-progress slice's spec or acceptance tests must change.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  author: spec-harness
  version: "0.1.0"
---

# sdd-spec

Produce a spec that states **what** the slice does and how to know it is done, precise enough that acceptance tests follow directly from it.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary: read them first), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Set the harness up once per project with `sdd-init`.
- Reference harness documents by ID (`S-012`, `S-012/AC-1`, `ADR-003`), never by path.
- The CLI owns the `status` and `base` fields: never edit them by hand.

## New slice

1. Get an ID with `sdd.py next-id slice`, create `.agents/docs/changes/<ID>-<slug>/` and copy [the spec template](assets/spec.md) into it as `spec.md`.
2. Fill the front matter:
   - `idea`: the source idea, or remove the line for a standalone request.
   - `capability`: an existing file name in `.agents/docs/specs/` when one fits; otherwise a new short kebab-case name.
   - `change`: `added` | `changed` | `deprecated` | `removed` | `fixed` | `security`.
   - `breaking`: `true` only if an existing contract stops working for its consumers; a list of release units if only some break.
3. If promoted from an idea, write the slice ID in the candidate's row and set its status to `specced`.
4. Run `sdd.py index`.

## Writing the spec

1. **Decisions first**: read `.agents/docs/index.md` and every accepted ADR whose `scope` includes `all`, this capability or a release unit the slice touches. List the ones the slice follows in `adrs` and turn each into a Constraint that cites its ID.
2. **Goal**: one sentence, who can do what and why. If it needs "and", it is two slices.
3. **Explore the code** before filling **Boundaries**: find the entry point (Input), the observable result (Output), the modules it touches and the contracts it relies on. Write `none` where nothing applies.
4. **Out** is never empty: list what a reader could expect but is excluded.
5. **Acceptance criteria**: 1–6, each `- **AC-n:** Given …, when …, then …`, observable from the boundary, never from internals. For a bug (`change: fixed`), one criterion reproduces it.
6. **Vocabulary**: use the glossary's terms, never its Avoid aliases. When the slice introduces a domain term, add it to `.agents/docs/glossary.md`.
7. Collect every doubt in **Open questions**, ask the user all of them in one message, and fold the answers back into the spec until the section is empty.
8. If the slice exceeds 6 criteria or its goal needs "and", split it: keep the first part here and add the rest as candidates to the idea.

## Plan

Add a plan only when the slice is not obvious (several modules, a design choice, or a risk):

- Small: append the sections of [the plan template](assets/plan.md) at the end of `spec.md`.
- Larger: copy it as `plan.md` next to the spec.
- A decision that constrains other slices or contradicts an accepted ADR: activate `sdd-adr`, then add the new ADR to `adrs`.

## Gate

1. Remove every template comment and placeholder.
2. Run `sdd.py advance <ID>`. On failure, fix what it reports and run it again.
3. **Checkpoint**: show the user the goal, scope, boundaries, criteria and any proposed ADR, and stop. Their approval covers the spec and its proposed ADRs, and is the input for `sdd-red`.

## Amending a slice

When the spec must change after `ready` (including when an acceptance test turns out to be wrong):

1. Run `sdd.py reopen <ID>`: status returns to `draft` and acceptance tests are unfrozen.
2. Edit the spec. Never renumber criteria: strike a removed one as `- ~~**AC-n:** …~~` and add new ones with the next number.
3. Tell the user which acceptance tests must be rewritten, then run the gate again.
