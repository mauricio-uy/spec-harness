---
name: sdd-close
description: Closes a green slice by writing close.md, merging its acceptance criteria into the living capability spec, checking runbooks, archiving it, and creating the changelog entry, release commit and tags. Use when a slice is green, or when asked to finish, ship or release a slice.
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  author: spec-harness
  version: "0.1.0"
---

# sdd-close

Record what was delivered, fold it into the living spec and release it. With continuous deployment, every closed slice is a release.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary: read them first), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Set the harness up once per project with `sdd-init`.
- Reference harness documents by ID (`S-012`, `S-012/AC-1`, `ADR-003`), never by path.
- The CLI owns the `status` field: never edit it by hand.

## Steps

1. **close.md**: copy [the close template](assets/close.md) into the slice folder and fill it:
   - one row per criterion (including struck ones) with its status and test;
   - deviations from spec and plan, debt and learnings, briefly.
2. **Living spec**: merge every active criterion into `.agents/docs/specs/<capability>.md`, creating it from [the capability template](assets/capability.md) if needed.
   - Keep the origin ID: `- **S-012/AC-1:** Given …`.
   - When a criterion replaces an existing behavior, update or remove the old entry; the living spec describes today, not history.
   - Add new contracts and constraints.
3. **Runbooks**: if the slice changed how a release unit is deployed, rolled back, configured or monitored, update `.agents/docs/runbooks/<unit>.md` (`root.md` without units).
4. **Idea**: if the slice came from one, set its candidate to `done` and add debt or follow-ups under "Debt and follow-ups".
5. **Context**: update `.agents/docs/overview.md` if the slice added a component, a release unit or a stack change. Check that new names in the code match `.agents/docs/glossary.md`, and add missing terms.
6. Tick every merge item in `close.md` (`n/a` where it does not apply) and run `sdd.py advance <ID>`. The slice moves to `.agents/docs/archive/` and the index is regenerated.

## Release

1. Run `sdd.py lint` and fix every error: broken links, unknown IDs, tests without a criterion, criteria without a test.
2. Run `sdd.py release <ID>` (dry run). It shows the conventional commit message, the version bump and tag per affected release unit, and the changelog files to update.
3. Stage the slice's changes with explicit paths (code, tests, `.agents/` documents). Check `git status` for unrelated changes and leave them unstaged.
4. **Checkpoint**: show the user the dry run and the staged files, and wait for confirmation.
5. Run `sdd.py release <ID> --apply`, adding `--trailer "<text>"` for each commit trailer the project requires. It writes the changelogs, commits and creates annotated tags.
6. Do not push unless the user asks; pushing the tags is what triggers deployment.

## Release units

Units are declared in `.agents/config.toml`. Without units, the whole repository is one unit tagged `vX.Y.Z`.

```toml
[[units]]
name = "api"
paths = ["services/api"]   # tags api/vX.Y.Z, changelog in services/api/CHANGELOG.md
```

Affected units come from the files changed since the slice became ready.
