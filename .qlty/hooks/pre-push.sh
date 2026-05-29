#!/bin/sh
# qlty's pre-push trigger runs semgrep and trufflehog across the full tree
# and hangs indefinitely. Fast checks (ruff, yamllint, etc.) already run via
# pre-commit on every commit. Slow security scanners run in CI. Nothing to
# add here that isn't already covered.
exit 0
