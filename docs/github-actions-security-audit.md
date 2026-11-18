# GitHub Actions security audit

This repository was checked against the Aikido `wfx-loot` GitHub Actions secret-stealer indicators published on 2026-11-12.

## Campaign indicators checked

The audit checks these known indicators:

- Branches named `wfx-docs`, `chore/[a-z0-9]{8}`, or `ci-check-[0-9]{4}`.
- Pull requests titled `docs: dependency audit notes`.
- Commits titled `ci: refresh build cache`, `ci: restore`, `ci: cleanup`, `chore: add ci helper`, or `chore: add dependency audit workflow`.
- Workflow/script content containing `WF_CALLBACK`, `WF_SECRETS`, `wfx-loot`, `WFX-BEGIN`, `194.150.166.244`, or `18.143.168.96`.

## Current findings

- No matching branch, pull request, commit-title, workflow-run, or checked-in workflow payload indicator was found in the local audit performed from the repository.
- GitHub Actions default workflow token permission is already configured as `read` for this repository.
- Workflow files now declare explicit least-privilege permissions instead of relying on repository defaults.
- No workflow uses `pull_request_target`.
- Pull request workflows do not expose repository secrets with `toJSON(secrets)`.
- The only checked-in `contents: write` permission is scoped to the release-publishing job that creates or updates GitHub Releases.
- The Pages workflow uses `id-token: write`, which is expected for GitHub Pages deployment.

## Repository-level follow-ups

These are repository settings, not code changes:

1. Protect `main` if it is not already protected in GitHub settings.
   - Require pull requests before merge.
   - Require status checks from GitHub Actions for normal changes.
   - Do not allow direct pushes by routine collaborators.
2. Keep the repository Actions setting at read-only default `GITHUB_TOKEN` permissions.
3. Consider restricting allowed Actions to GitHub-owned and explicitly approved third-party Actions once the DuckDB extension workflow dependency list is stable.
4. Rotate any release, package, cloud, or Pages credentials if a future audit finds an executed malicious workflow. Absence of `wfx-loot` artifacts or summaries is not proof of safety because the campaign deleted workflow runs.

## Quick repeat audit

Use GitHub CLI from a fresh checkout:

```
git fetch --all --prune
git log --all --since='2026-11-09' --pretty=format:'%h %ad %an %s' --date=iso \
  | grep -Ei 'docs: dependency audit notes|ci: refresh build cache|chore: add ci helper|chore: add dependency audit workflow|ci: restore|ci: cleanup|wfx|loot' || true

git branch -a \
  | grep -E 'wfx-docs|chore/[a-z0-9]{8}|ci-check-[0-9]{4}' || true

gh pr list --state all --limit 100 --json number,title,headRefName,state,url \
  | jq -r '.[] | [.number,.state,.headRefName,.title,.url] | @tsv' \
  | grep -Ei 'docs: dependency audit notes|wfx-docs|chore/[a-z0-9]{8}|ci-check-[0-9]{4}' || true

gh run list --limit 100 --json number,workflowName,event,headBranch,displayTitle,url \
  | jq -r '.[] | [.number,.event,.workflowName,.headBranch,.displayTitle,.url] | @tsv' \
  | grep -Ei 'wfx-docs|chore/[a-z0-9]{8}|ci-check-[0-9]{4}|dependency audit|refresh build cache|ci helper' || true
```

No output from the `grep` commands means no known campaign indicator was found by those checks.
