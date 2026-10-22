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

## 3. Let the release workflow push

The release workflow pushes a release commit and tags straight to `main`, so it needs to bypass the ruleset. Which actor can bypass depends on who owns the repository:

```bash
gh api repos/OWNER/REPO -q .owner.type    # User or Organization
```

| Owner          | Release bypass actor                                     |
|----------------|----------------------------------------------------------|
| `User`         | A deploy key                                             |
| `Organization` | GitHub Actions, or a deploy key to trigger tag workflows |

On a personal account, GitHub rejects GitHub Actions as a bypass actor as soon as the ruleset is created ("must be part of the ruleset source or owner organization"). The whole request fails, so no ruleset and no bypass is saved.

### Deploy key

Create a key with write access and store its private half as the `RELEASE_DEPLOY_KEY` secret. The release workflow uses it when the secret exists:

```bash
ssh-keygen -t ed25519 -N "" -C "release workflow" -f release_key
gh repo deploy-key add release_key.pub --repo OWNER/REPO --allow-write --title "release workflow"
gh secret set RELEASE_DEPLOY_KEY --repo OWNER/REPO < release_key
rm release_key release_key.pub
```

Pushes made with a deploy key trigger other workflows, unlike pushes made with the workflow's `GITHUB_TOKEN`.

## 4. Ruleset for main

Once `sdd verify` has run at least once, protect `main`. Add the project's test check next to `sdd verify`.

```bash
gh api -X POST repos/OWNER/REPO/rulesets --input - <<'EOF'
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"},
    {"actor_type": "DeployKey", "bypass_mode": "always"}
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

- **Repository admins** (`RepositoryRole` 5) in `pull_request` mode: they can merge a pull request whose checks fail, but cannot push to `main` directly.
- **The deploy key**, so the release workflow can push its commit and tags.

In an organization without a deploy key, replace the deploy key with GitHub Actions: `{"actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always"}`.

## 5. Check the first release

After the first slice is merged:

- the `release` run succeeds;
- `main` gains a `chore(release): vX.Y.Z` commit;
- the tag exists: `git ls-remote --tags origin`.

If the push is rejected with `GH013: Repository rule violations`, the release actor is not in the ruleset's bypass list.

## 6. Deployment

- **With the deploy key**, the pushed tags trigger other workflows, so a separate workflow on `push: tags: ["v*"]` can deploy.
- **With GitHub Actions as the bypass actor**, the tags are pushed with `GITHUB_TOKEN` and trigger no other workflow. Deploy from the `deploy` job in `release.yml` instead. It receives the new tags, and can run the deployment itself or call a reusable workflow (`on: workflow_call`).
