# GitHub setup

How to configure a GitHub repository for the harness. Apply the steps in this order: a check can only be required after it has run.

Replace `OWNER/REPO` with the repository. The commands use the GitHub CLI (`gh`).

## How releases work

The release workflow never writes to `main`. After each merge it creates one annotated tag per affected release unit on the merged commit. Each tag message carries the release notes, and the workflow publishes a GitHub Release from it. The workflow's own `GITHUB_TOKEN` is enough, on personal accounts and organizations alike.

`CHANGELOG.md` is not committed. When a package needs one, generate it from the tags at build time with `sdd.py changelog`.

## 1. Add the workflows

Open one pull request that adds:

- `.github/workflows/check.yml`, from [the check workflow](../assets/check.yml): runs `sdd.py verify` on every pull request;
- `.github/workflows/release.yml`, from [the release workflow](../assets/release.yml): tags and publishes merged slices on every push to `main`;
- the project's own test workflow, if it has none.

Merge it before requiring any check: until `check.yml` exists on `main` and has run once, requiring `sdd verify` blocks every pull request.

## 2. Merge settings

Squash merge only, with the pull request title as the subject and its description as the body, so the Conventional Commit subject and the `Slice:` trailer reach `main` unchanged:

```bash
gh api -X PATCH repos/OWNER/REPO \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY \
  -F delete_branch_on_merge=true
```

The defaults are wrong for the harness:

- `COMMIT_OR_PR_TITLE` takes the commit title when the branch has a single commit.
- `COMMIT_MESSAGES` replaces the description with the branch's commit messages.

## 3. Ruleset for main

Once `sdd verify` has run at least once, protect `main`. Add the project's test check next to `sdd verify`.

```bash
gh api -X POST repos/OWNER/REPO/rulesets --input - <<'EOF'
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}
  ],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 0,
      "dismiss_stale_reviews_on_push": false,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false,
      "allowed_merge_methods": ["squash"]
    }},
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": false,
      "required_status_checks": [{"context": "sdd verify", "integration_id": 15368}]
    }}
  ]
}
EOF
```

Repository admins (`RepositoryRole` 5) bypass in `pull_request` mode: they can merge a pull request whose checks fail, but cannot push to `main` directly.

If you add a ruleset that protects tags, it must still let GitHub Actions create `v*` and `<unit>/v*` tags.

## 4. Check the first release

After the first slice is merged:

- the `release` run succeeds;
- the tag exists (`git ls-remote --tags origin`), and so does its GitHub Release;
- `main` has no new commit.

## 5. Deployment

Tags and releases created with the workflow's `GITHUB_TOKEN` trigger no other workflow, so a separate `on: push: tags` workflow never runs. Deploy from the `deploy` job in `release.yml`: it receives the new tags, and can run the deployment itself or call a reusable workflow (`on: workflow_call`).
