---
name: sdd-next
description: Moves a slice forward to its next lifecycle phase by activating the matching sdd skill, stopping at human checkpoints. Use when the user says next, continue or advance on a slice, or wants to move spec-driven work forward without naming the phase.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py and the other sdd-* skills.
metadata:
  author: spec-harness
  version: "0.1.0"
---

# sdd-next

Dispatcher over the slice lifecycle. Invoking it after a checkpoint counts as the user's approval of that checkpoint.

## Harness

- Workspace: `.agents/` with `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing).

## Steps

1. **Pick the slice**: the ID the user gave; otherwise the only open slice in `sdd.py status`; otherwise ask which one.
2. **Read its status** with `sdd.py status <ID>` and act:

| Status | Action                                          | Then                                   |
|--------|-------------------------------------------------|----------------------------------------|
| draft  | Activate `sdd-spec`                             | Stop at its checkpoint (spec review)   |
| ready  | Activate `sdd-red`                              | Stop at its checkpoint (test review)   |
| red    | Activate `sdd-green`                            | Continue with `sdd-close` on success   |
| green  | Activate `sdd-close`                            | Stop at its checkpoint (release)       |
| done   | Nothing to advance                              | Propose the top candidate from `sdd-status` |

3. If there is no open slice, propose promoting the top idea candidate with `sdd-spec`, or capturing a new idea with `sdd-idea`.

## Rules

- Never skip a checkpoint: spec review (ready), test review (red) and release confirmation (close).
- If a phase fails its gate and cannot be fixed within that phase's rules, stop and report; do not jump phases.
