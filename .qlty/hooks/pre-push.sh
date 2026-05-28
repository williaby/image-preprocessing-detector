#!/bin/sh
# Scope pre-push to fast linters only. Slow security scanners (semgrep,
# trufflehog, osv-scanner) run in CI where they have no timeout pressure.
qlty check \
	--trigger pre-push \
	--upstream-from-pre-push \
	--no-formatters \
	--skip-errored-plugins \
	--filter ruff \
	--filter markdownlint \
	--filter yamllint \
	--filter actionlint \
	--filter hadolint \
	--filter shellcheck
