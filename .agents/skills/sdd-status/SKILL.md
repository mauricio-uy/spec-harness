---
name: sdd-status
description: Reports the state of spec-driven work, including open slices, their lifecycle status, failing gates, pending idea candidates and the next action. Use when the user asks what is in progress, what comes next, or why a slice cannot advance.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  source: github.com/mauricio-uy/spec-harness
  version: "0.1.0"
---

# sdd-status

Read-only overview of the work. Never edit files from this skill.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary: read them first), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Set the harness up once per project with `sdd-init`.
- Reference harness documents by ID (`S-012`, `S-012/AC-1`, `ADR-003`), never by path.

## Steps

1. Run `sdd.py status` to list open slices with their status and next skill. It also warns about slices that follow a superseded ADR and about a stale index.
2. For a specific slice, run `sdd.py status <ID>`: it shows its criteria and the static checks of its next gate. Tests are not run; `sdd.py check <ID>` runs them when the user wants a full verdict.
3. Read `.agents/docs/index.md` for open ideas, proposed decisions and pending candidates.
4. When the user asks about consistency, run `sdd.py lint`: broken links, unknown IDs, criteria without tests, tests without criteria and glossary aliases.
5. Answer briefly:
   - slices in progress, one line each, with what blocks them;
   - the recommended next action: the slice closest to done first, then the top candidate.

| Status | Next skill  | Waiting for                           |
|--------|-------------|---------------------------------------|
| draft  | `sdd-spec`  | spec completion, open questions       |
| ready  | `sdd-red`   | user approval of the spec             |
| red    | `sdd-green` | user approval of the acceptance tests |
| green  | `sdd-close` | close and release                     |
