# CI/CD & Tooling Audit (06-cicd)

Summary: 23 workflows, all actions SHA-pinned on current majors with no deprecated runtimes; main gaps are config drift (basedpyright is the stated type checker but neither CI nor pre-commit runs it; mypy runs instead with divergent args), an unused semgrep ruleset, a non-blocking bandit scan, setup-uv version spread, and duplicate full-pytest runs in sonarcloud and python-compatibility.

## Findings

### CI-01 basedpyright (house type checker) absent from CI and pre-commit; mypy used instead
- Severity: High | Effort: M
- Files: .github/workflows/ci.yml, .pre-commit-config.yaml, pyproject.toml
- Evidence: CLAUDE.md and `pyproject.toml:87` declare `basedpyright>=1.18.0` as the modern type checker ("strict, 3-5x faster than mypy"); `pyproject.toml:86` marks `mypy` as "Legacy ... kept for reference". Yet `ci.yml:316` runs `uv run mypy src --config-file=pyproject.toml` and `.pre-commit-config.yaml:57-66` runs `mirrors-mypy rev: v1.8.0`. `grep -rln basedpyright .github/workflows/ .pre-commit-config.yaml` returns nothing. The enforced gate uses the tool the project calls legacy; basedpyright strict config at `pyproject.toml:589` is never exercised in CI.
- Recommendation: Add `uv run basedpyright src` to the quality-checks job and a basedpyright pre-commit hook, or formally demote basedpyright in docs. Pick one type checker as the gate to avoid two contradicting truth sources.

### CI-02 mypy config drifts between pre-commit and CI
- Severity: Medium | Effort: S
- Files: .pre-commit-config.yaml, .github/workflows/ci.yml
- Evidence: pre-commit (`.pre-commit-config.yaml:66`) runs mypy with `--ignore-missing-imports --python-version=3.12 --no-warn-unused-ignores` and excludes ~9 src files (gcs_uploader, device_probe, recommendation_engine, json_generator, document_processor, augmentation/*, etc.). CI (`ci.yml:316`) runs `mypy src --config-file=pyproject.toml` over all of src with no `--ignore-missing-imports`. Pre-commit pins `v1.8.0`; CI resolves `mypy>=1.4.0` via uv (likely a newer version). A local pre-commit pass can therefore pass while CI fails on the excluded files or stricter import checking.
- Recommendation: Point the pre-commit mypy hook at the same config file and file scope as CI, and align the pinned version with the uv-resolved one.

### CI-03 semgrep ruleset (.semgrep.yaml) is never executed by any workflow
- Severity: Medium | Effort: S
- Files: .semgrep.yaml, .github/workflows/security-analysis.yml, .github/workflows/sonarcloud.yml
- Evidence: `.semgrep.yaml` is a 4 KB custom ruleset. `grep -rln semgrep .github/workflows/` matches only `sonarcloud.yml`, and those are `# nosemgrep:` suppression comments (lines 125, 139), not an invocation. `security-analysis.yml:257-258` states semgrep is delegated to the Semgrep Cloud GitHub App. The local ruleset is not run by any in-repo job, so its rules are unverified in PR checks and drift from the cloud config silently.
- Recommendation: Either add a `semgrep --config .semgrep.yaml` step to security-analysis.yml or document that the cloud app consumes this file; if neither, delete the file to remove dead config.

### CI-04 bandit scan is non-blocking (|| true)
- Severity: Medium | Effort: S
- Files: .github/workflows/security-analysis.yml
- Evidence: `security-analysis.yml:250-255` runs `uv run bandit -r src ... || true` twice, so a HIGH/CRITICAL bandit finding never fails the job. CLAUDE.md states "ALL security findings from scanners (Semgrep, Bandit, Safety, OSV) must be addressed" and "fail on HIGH/CRITICAL by default". The `|| true` contradicts that policy and lets flagged code merge. (Severity here is the gate/policy contradiction; exploit detail is the security agent's scope.)
- Recommendation: Drop `|| true` or gate on severity (`bandit -r src -ll` failing on medium+), keeping the JSON artifact upload under `if: always()`.

### CI-05 setup-uv pinned to 4 different versions across workflows
- Severity: Low | Effort: S
- Files: .github/workflows/*.yml
- Evidence: `grep setup-uv@` shows v5 (12 uses), v5.4.2 (3 uses: security-analysis), v4.2.0 (1 use: codeql.yml:52), v7.6 (1 use: slsa-provenance.yml:59). Four versions of the same action installer cause inconsistent uv/cache behavior and make pin-bump review noisy. codeql.yml on v4.2.0 is the oldest.
- Recommendation: Standardize all workflows on one SHA-pinned setup-uv version (the v7.x line is current); update codeql.yml off v4.2.0.

### CI-06 sonarcloud re-runs the full pytest suite on every PR (duplicates ci.yml test job)
- Severity: Medium | Effort: M
- Files: .github/workflows/sonarcloud.yml, .github/workflows/ci.yml
- Evidence: `sonarcloud.yml:25-26` triggers on every `pull_request`, and `sonarcloud.yml:103` runs `uv run pytest --cov ...` to produce coverage.xml. ci.yml already runs pytest with coverage across a 5-version matrix (`ci.yml:173,236`). Codecov/qlty/coverage correctly reuse ci.yml artifacts via `workflow_run` (codecov.yml:7, qlty.yml:7), but sonarcloud does its own redundant test+coverage run, adding minutes per PR.
- Recommendation: Have sonarcloud consume the coverage artifact from ci.yml via `workflow_run` + download-artifact (same pattern as codecov.yml/qlty.yml) instead of re-running pytest.

### CI-07 python-compatibility re-runs pytest overlapping ci.yml matrix
- Severity: Low | Effort: S
- Files: .github/workflows/python-compatibility.yml, .github/workflows/ci.yml
- Evidence: `python-compatibility.yml:40` tests `["3.10","3.11","3.12","3.13"]` and `:45` runs `pytest tests/ ...`. ci.yml matrix (`ci.yml:173`) already covers `3.10`-`3.14`. The compat workflow triggers on push to main with path filters (`:8-13`), so it is not per-PR, but it duplicates four versions of the ci.yml test surface.
- Recommendation: Narrow python-compatibility to versions ci.yml does not cover, or run an import/smoke check rather than the full suite, to avoid running the same tests twice.

## Healthy areas
All actions SHA-pinned on current majors (checkout v4.3.1, setup-python v6.2.0, upload/download-artifact v7.0.1/v4.3.0, codeql v3.36.0); zero `::set-output`/`save-state`/`set-env` and zero node12/16 runtimes; a real blocking ci-gate (`ci.yml:481` needs all jobs and exits 1 on failure); the 9 `continue-on-error` uses are scoped to non-gating cases (Python 3.14 experimental, optional apt deps, coverage/docs/fuzz reporters); uv caching present in setup-uv and actions/cache; coverage reporters (codecov/qlty/coverage) reuse ci.yml artifacts via workflow_run instead of re-testing; harden-runner on security-sensitive jobs.
