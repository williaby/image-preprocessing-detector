---
schema_type: common
title: "Review and Merge Policy"
tags:
  - ci_cd
  - compliance
  - reference
status: published
owner: docs-team
purpose: Documents the automated review and branch-merge policy for the default branch.
---

**Version**: 1.0
**Last Updated**: 2026-05-28

## Summary

Automated reviewers (CodeRabbit and GitHub Copilot) **run on every pull
request but do not block merges**. No review approval is required to merge to
`main`. Merges remain gated only by automated quality checks (signed commits,
linear history, and required status checks), not by a human or bot approval.

This mirrors the `ByronWilliamsCPA/.claude` and `ByronWilliamsCPA/.github`
reference repositories, where the default-branch baseline ruleset sets
`require_code_owner_review: false`.

## Why

This is a solo-maintained repository. Requiring a code-owner review on every PR
(via `require_code_owner_review: true` combined with a blanket
[.github/CODEOWNERS](../../.github/CODEOWNERS) entry of `* @williaby`) forced a
self-approval on every change with no quality benefit. The automated reviewers
provide the contextual feedback; the CI status checks provide the hard gate.

## Layers

### 1. CodeRabbit (advisory)

Configured in [.coderabbit.yaml](../../.coderabbit.yaml):

- `reviews.auto_review.enabled: true` keeps CodeRabbit reviewing every PR.
- `reviews.request_changes_workflow: false` keeps it in **advisory** mode, so
  its review posts as a comment rather than a blocking "Request changes".

### 2. GitHub Copilot review (advisory)

The default-branch ruleset includes the `copilot_code_review` rule, which
**auto-requests** a Copilot review on each PR. Copilot's review is informational
and does not gate merge.

### 3. Branch ruleset (the merge gate)

The `williaby-default-branch-baseline` repository ruleset enforces the actual
merge requirements. Relevant `pull_request` parameters:

| Parameter | Value | Effect |
| --- | --- | --- |
| `required_approving_review_count` | `0` | No approvals required |
| `require_code_owner_review` | `false` | Code-owner approval not required |

Still enforced by the same ruleset (unchanged by this policy):

- `required_signatures` (signed commits)
- `required_linear_history`
- `required_status_checks`: Security Gate Validation, Dependency & Standards
  Validation, Check REUSE Compliance, CI Gate

## Changing this policy

Rulesets are repository settings, not files in this repo, so they are changed
via the GitHub API rather than a pull request. To re-enable a required
code-owner review:

```bash
# Fetch the current ruleset, edit require_code_owner_review, then PUT it back.
gh api repos/williaby/image-preprocessing-detector/rulesets/16201087 > ruleset.json
# (edit the pull_request rule's require_code_owner_review to true)
gh api -X PUT repos/williaby/image-preprocessing-detector/rulesets/16201087 \
  --input ruleset.json
```

Keep this document in sync with any ruleset change.
