#!/bin/sh
# semgrep, trufflehog, radarlint, and osv-scanner are excluded: they scan the full
# codebase and take 45-120 minutes per push. All run in CI (security-analysis.yml).
qlty check \
	--trigger pre-push \
	--upstream-from-pre-push \
	--no-formatters \
	--skip-errored-plugins \
	--filter actionlint,bandit,hadolint,markdownlint,ruff,shellcheck,yamllint
