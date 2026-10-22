# GitHub setup

How to configure a GitHub repository for the harness. Apply the steps in this order: a check can only be required after it has run, and the release workflow can only push once `main` lets it.

Replace `OWNER/REPO` with the repository. The commands use the GitHub CLI (`gh`).

## 1. Add the workflows

Open one pull request that adds:

- `.github/workflows/check.yml`, from [the check workflow](../assets/check.yml): runs `sdd.py verify` on every pull request;
- `.github/workflows/release.yml`, from [the release workflow](../assets/release.yml): releases merged slices on every push to `main`;
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
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"},
    {"actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always"}
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

The bypass actors are:

- **Repository admins** (`RepositoryRole` 5), for emergencies.
- **GitHub Actions** (`Integration` 15368), so the release workflow can push its release commit and tags straight to `main`.

## 4. Check the first release

After the first slice is merged:

- the `release` run succeeds;
- `main` gains a `chore(release): vX.Y.Z` commit;
- the tag exists: `git ls-remote --tags origin`.

If the push is rejected, the GitHub Actions bypass is not taking effect. Use a deploy key instead:

1. Create a key pair. Add the public key as a deploy key with write access, and the private key as the `RELEASE_DEPLOY_KEY` secret.
2. In the ruleset, add the bypass actor `{"actor_id": null, "actor_type": "DeployKey", "bypass_mode": "always"}`.
3. In `release.yml`, pass `ssh-key: ${{ secrets.RELEASE_DEPLOY_KEY }}` to `actions/checkout`.

A GitHub App token works the same way.

## 5. Deployment

Tags pushed with the workflow's `GITHUB_TOKEN` do not trigger other workflows, so a separate `on: push: tags` workflow never runs. Deploy from `release.yml` instead: its `deploy` job receives the new tags. It can run the deployment itself, or call a reusable workflow (`on: workflow_call`).

With a deploy key or an App token, pushed tags do trigger other workflows, so a separate tag workflow works too.
