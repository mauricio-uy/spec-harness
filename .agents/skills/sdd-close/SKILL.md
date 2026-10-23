---
name: sdd-close
description: Closes a green slice by writing close.md, merging its acceptance criteria into the living capability spec, checking runbooks, archiving it, and opening its pull request; the release follows the merge. Use when a slice is green, or when asked to finish, ship or release a slice.
license: MIT
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py.
metadata:
  source: github.com/mauricio-uy/spec-harness
  version: "0.1.0"
---

# sdd-close

Record what was delivered, fold it into the living spec and hand the slice over as one pull request. With continuous deployment, every merged slice is a release.

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
4. **Idea**: if the slice came from one, set its candidate to `done` and add debt or follow-ups under "Debt and follow-ups". A standalone slice records its debt in `close.md` only.
5. **Context**: update `.agents/docs/overview.md` if the slice added a component, a release unit or a stack change. Check that new names in the code match `.agents/docs/glossary.md`, and add missing terms.
6. Tick every merge item in `close.md` (`n/a` where it does not apply) and run `sdd.py advance <ID>`. The slice moves to `.agents/docs/archive/` and the index is regenerated.

## Pull request

1. Run `sdd.py verify --base origin/main` and fix every error. It runs `lint` (broken links, unknown IDs, tests without a criterion, criteria without a test) plus the checks the pull request will face in CI.
2. Commit the remaining changes on the slice branch with explicit paths (code, tests, `.agents/` documents). Leave unrelated changes out.
3. Run `sdd.py pr <ID>`. It prints the pull request title (a Conventional Commit subject built from the spec) and body: goal, acceptance criteria, notes from `close.md`, and the `Slice:` trailer last.
4. **Checkpoint**: show the user the title, the body and the branch's changes, and wait for confirmation.
5. Push the branch and open the pull request with exactly that title and body, e.g. `gh pr create --title "$(sdd.py pr <ID> --title)" --body "$(sdd.py pr <ID> --body)"`. Do not edit the trailers.
6. Do not merge unless the user asks.

## Release

Releases happen after the merge, on `main`, never on the slice branch:

- Merge with **squash**, using the pull request title and body as the commit message, so the `Slice:` trailer reaches `main`. A direct commit to `main` that archives the slice works too.
- The release workflow (proposed by `sdd-init`) runs `sdd.py release --apply` on every push to `main`. Without it, run it locally after `git pull`, then `git push --tags`.
- For the slices merged since the last release, it bumps the version of every release unit whose files changed and creates an annotated tag on the merged commit. The tag message carries the release notes; the workflow publishes them as a GitHub Release. Nothing is committed to `main`.
- `CHANGELOG.md` is generated from the tags when needed: `sdd.py changelog`.

Release units are declared in `.agents/config.toml`. Without units, the whole repository is one unit tagged `vX.Y.Z`.

```toml
[[units]]
name = "api"
paths = ["services/api"]   # tagged api/vX.Y.Z; `sdd.py changelog --unit api` renders its changelog
```
