---
name: sdd-adr
description: Records a decision that constrains more than one slice as an architecture decision record, replaces an outdated one, and plans the slices needed to bring existing code in line. Use when a cross-cutting technical or product decision is made or proposed, inside or outside a slice.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  author: spec-harness
  version: "0.1.0"
---

# sdd-adr

Capture why a cross-cutting decision was taken, how far it reaches, and what it takes to apply it.

## Harness

- Docs: `.agents/docs/` with `index.md` (generated map: read it first), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Run `sdd.py init` once per project.
- The CLI owns the `status`, `date` and `superseded_by` fields: never edit them by hand.

## Steps

1. Read the decisions in `.agents/docs/index.md`. If an accepted ADR already covers the topic, either follow it (no new ADR) or replace it (step 3).
2. Get an ID with `sdd.py next-id adr` and copy [the ADR template](assets/adr.md) to `.agents/docs/adr/<ID>-<slug>.md`.
3. Fill it:
   - **Context**: the forces and why now.
   - **Decision**: one or two sentences.
   - **Consequences**: what gets easier, harder or constrained.
   - `scope`: the capabilities and release units it constrains, or `[all]`.
   - `supersedes`: the ADR it replaces, if any.
4. **Follow-up**: if existing code must change to comply, activate `sdd-idea` to create an idea with one candidate per affected capability, and write its ID here. An ADR never changes code itself; each candidate goes through the normal slice lifecycle.
5. Run `sdd.py index`.

## Acceptance

- **Born inside a slice**: list the ADR in the spec's `adrs` field. The user approves it together with the spec, and `sdd-red` accepts it.
- **Standalone**: show the ADR to the user and stop. On approval, run `sdd.py accept <ID>`.

Accepting an ADR that `supersedes` another marks the old one superseded. Open slices that follow a superseded ADR are flagged by `sdd.py status`.

## Rules

- Never edit the Decision of an accepted ADR. Replace it with a new ADR that `supersedes` it.
- A requirement that applies to one capability belongs in its spec's Constraints, not in an ADR.
