---
name: sdd-release
description: Releases slices after they are merged into main, with one Semantic Versioning tag per affected release unit carrying Keep a Changelog notes, and checks, repairs and documents those releases. Use when asked to release, tag or version merged work, when the release workflow fails or a GitHub Release is missing, when a CHANGELOG.md is needed, or when a release unit is declared 1.0.0.
license: MIT
compatibility: Requires git and Python 3.11+. Expects the spec-harness CLI at .agents/bin/sdd.py; publishing GitHub Releases uses the GitHub CLI (gh).
metadata:
  source: github.com/mauricio-uy/spec-harness
  version: "0.1.0"
---

# sdd-release

Turn merged slices into versions. With continuous deployment, every merged slice is a release, cut after the merge, on `main`, never on the slice branch.

## Harness

- Docs: `.agents/docs/` with `overview.md` and `glossary.md` (system context and vocabulary: read them first), `index.md` (generated map), `ideas/`, `changes/` (open slices), `archive/` (closed slices), `specs/` (living spec), `adr/`, `runbooks/`.
- CLI: `python3 .agents/bin/sdd.py <command>` (use `python` on Windows if `python3` is missing). Set the harness up once per project with `sdd-init`.
- Reference harness documents by ID (`S-012`, `S-012/AC-1`, `ADR-003`), never by path.

## How releases work

- **One commit per slice.** A slice reaches `main` squash-merged, with its pull request title and body as the commit message, so the commit carries the `Slice:` trailer. A release attributes to a slice exactly what its commit changed, so a direct commit to `main` works only if it holds the whole slice. When the trailer was edited out, the commit that adds the slice to `.agents/docs/archive/` identifies it.
- **Release units.** Declared in `.agents/config.toml`; without units, the whole repository is one unit tagged `vX.Y.Z`, and a unit named `api` is tagged `api/vX.Y.Z`. Each unit is released on its own: the slices merged since its last tag whose commit touched its files.
- **Versions.** Semantic Versioning from the slices' `change` and `breaking`: `fixed` and `security` bump the patch, other changes the minor, and `breaking` the major. The strongest change wins. While a unit is below `1.0.0`, breaking changes bump the minor instead.
- **Tags.** One annotated tag per unit, on the last of its slices' commits. The tag message carries the release notes, grouped as in Keep a Changelog, and the GitHub Release is published from it. Nothing is committed to `main`.
- **Unnamed work.** Commits without a slice ship in their unit's next version but are not named in its notes. A slice whose commit touches no release unit is never released; `release` says so until the next release.
- **Tags are the record.** Versions, notes and what has been released all come from the tags: never delete or move one. A wrong tag makes the next release compute the wrong version; ask the user before fixing it.

## Release

On GitHub, the release workflow installed by `sdd-init` (`.github/workflows/release.yml`) runs `sdd.py release --apply` on every push to `main`, pushes the new tags and publishes their GitHub Releases. Without it, release locally after each merge:

1. Switch to `main` and bring it up to date: `git switch main && git pull --ff-only`.
2. Run `sdd.py release`. It is a dry run: one line per tag, with its target commit and its slices. Fix what it reports (see [Problems](#problems)).
3. **Checkpoint**: show the user the planned tags and wait for confirmation. Pushed tags are public and should never move.
4. Run `sdd.py release --apply`, then `git push --follow-tags origin main`, which pushes only the new release tags.
5. On GitHub, publish each new tag as a release: `gh release create <tag> --verify-tag --notes-from-tag --title <tag>`.

## Check a release

After a merge:

- the `release` run succeeded;
- each tag exists (`git ls-remote --tags origin`) on the commit of its unit's last slice, and so does its GitHub Release;
- `main` has no new commit.

If a GitHub Release is missing because publishing failed, re-run the workflow: it publishes the release of any recent tag that lacks one. Locally, run the `gh release create` command above for that tag.

## Changelog

`CHANGELOG.md` is not committed. When a package ships one, generate it from the tags at build time:

```bash
python3 .agents/bin/sdd.py changelog --output CHANGELOG.md               # single unit
python3 .agents/bin/sdd.py changelog --unit api --output CHANGELOG.md    # one release unit
```

## Declaring 1.0.0

A unit stays below `1.0.0` until someone declares its API stable: under Semantic Versioning, breaking changes in `0.x` bump the minor, so releases never reach `1.0.0` on their own. Only the user decides it. Declare it once per unit with an annotated tag on `main`:

```bash
git tag -a v1.0.0 -m "Release v1.0.0" origin/main && git push origin v1.0.0        # single unit
git tag -a api/v1.0.0 -m "Release api/v1.0.0" origin/main && git push origin api/v1.0.0
```

`sdd.py release` continues from it: the next `added` slice releases `1.1.0`, and from then on every breaking slice bumps the major (`2.0.0`, `3.0.0`) automatically.

## Problems

| `release` reports                          | Meaning and fix                                                                                                                |
|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `S-012 is merged but not closed`           | Its commit reached `main` before `sdd-close` finished. Close it with `sdd-close` in a new pull request; the release follows it. |
| `lists unknown release units as breaking`  | The slice's `breaking` names a unit missing from `.agents/config.toml`. Fix the unit name in a new pull request.               |
| `S-012 touches no release unit`            | Its commit changed no unit's files, so it is not released. Expected for documentation-only slices; otherwise check the units.  |
| `nothing to release`                       | No slice was merged since each unit's last tag.                                                                                |
