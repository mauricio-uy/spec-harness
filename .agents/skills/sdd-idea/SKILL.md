---
name: sdd-idea
description: Captures a product idea and decomposes it into candidate vertical slices. Use when the user brings a problem, feature request or initiative larger than a single slice, or asks to break work down before specifying it.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  author: spec-harness
  version: "0.1.0"
---

# sdd-idea

Turn a loose idea into an idea document with an ordered list of candidate slices.

## Harness

- Workspace: `.agents/` with `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing).

## Steps

1. Get an ID with `sdd.py next-id idea` and copy [the idea template](assets/idea.md) to `.agents/ideas/<ID>-<slug>.md`. The slug is short kebab-case.
2. Fill **Problem**, **Outcome** and **Non-goals** from what the user said. Ask only for what is missing, all questions in one message.
3. Decompose into candidate slices, labelled `C1`, `C2`… Each candidate:
   - is one user-observable behavior, described in one sentence without "and";
   - can be demoed on its own;
   - is ordered by value first, then by dependency.
4. When a candidate is too big, split it with SPIDR:
   - **Spike**: too much uncertainty, research first.
   - **Paths**: happy path first, alternatives as separate slices.
   - **Interfaces**: one channel first (API), others later (UI).
   - **Data**: one data type or subset first.
   - **Rules**: base rule first, exceptions later.
5. Remove every template comment and placeholder, then show the candidate table to the user.

## Rules

- Do not assign slice IDs here: a candidate gets one when `sdd-spec` promotes it.
- Do not write acceptance criteria or design here; that belongs to the spec.
- Set the idea `status` to `done` when every candidate is `done` or `dropped`.
