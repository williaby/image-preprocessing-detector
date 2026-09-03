# Remediation Log (2026-05-29)

Follow-up to the audit in this directory. Scope: Medium and Low findings only (High findings left for human review). Every applied change was verified; several findings were reclassified as false positives once their evidence was checked against the code. Read-only constraints no longer apply: this log covers edits made on branch claude/repo-audit-NKadh after the audit commit.

Verification environment: ruff 0.15.8, pytest 9.0.2, Python 3.11, `uv sync --extra dev`. basedpyright not installed locally; type checks deferred to CI.

## Applied

| ID | Change | Files | Verification |
|----|--------|-------|--------------|
| DOC-05, ARCH-07 | CONTRIBUTING.md and AGENTS.md toolchain corrected: Poetry to uv, Black/isort to ruff format, mypy to basedpyright; module map expanded to include annotation, labeling, synthetic, drift, api | CONTRIBUTING.md, AGENTS.md | Manual review; commands match pyproject scripts and CLAUDE.md |
| DOC-06 | Hardcoded `/home/byron/dev/image_detection` replaced with `$(pwd)` in the two CLAUDE.md validation commands | CLAUDE.md:331,1022 | Path now resolves on any checkout |
| DOC-07 | Stale "1,292 files mapped" replaced with a regenerate-via-script pointer | CLAUDE.md:50 | Removed the disputed count |
| DOC-04 (partial) | 3 of 20 broken README links repointed to existing targets: PROJECT_PLAN.md to MASTER_PROJECT_PLAN.md, project-a-project-plan.md to MASTER_PROJECT_PLAN.md, references/CITATIONS.md to reference/CITATIONS.md | README.md:126,347,384,536 | Broken-link scan: 20 down to 17; repoint targets confirmed to exist |
| LEG-06 | os.path.join converted to `str(Path(output_dir) / "...")`; unused `import os` removed | utils/metadata_generator.py:132,169,280,314,346 | ruff clean; 37/37 unit tests pass |
| CI-05 | codeql.yml setup-uv bumped off the outlier v4.2.0 SHA to the majority v5 SHA (already trusted in 14 workflows) | .github/workflows/codeql.yml:52 | Single-token SHA swap; structure unchanged |

## Reclassified as false positive (verified, no change made)

| ID | Original claim | What the code shows |
|----|----------------|---------------------|
| LEG-02 | utcnow_compat / utcfromtimestamp_compat have 0 call sites, delete them | tests/unit/test_datetime_compat.py:336-349 imports and tests both shims for their deprecation warnings. They are intentionally retained tested wrappers. Deleting them breaks 2 tests. |
| LEG-05 | Commented-out parser stub, replace with NotImplementedError | annotation/parsers/template.py is a code generator; lines 236-265 are instructional example patterns inside a template string (closes at :297) emitted into generated parser files. Not dead code. |
| LEG-07 (migrations) | `.format()` is legacy formatting, convert to f-strings | migrations.py:751,782 call `self.backup_suffix.format(version=version)` on a user-configured template string containing `{version}`. `.format()` is correct here; an f-string cannot fill a runtime template. |

## Deferred (Medium/Low not applied, with reason)

| ID | Reason |
|----|--------|
| DOC-04 (remainder) | 17 README links point to docs that exist nowhere in the repo (DATASET_METHODOLOGY, DETECTION_TAXONOMY, ARCHITECTURE_SUMMARY, MODEL_STORAGE, TESTING_STRATEGY, api-reference, and others). Create-vs-remove is a maintainer content decision; not safe to delete a block of the README unilaterally. |
| LEG-01 | Optional to `X \| None` across 56 files. The project ruff config does not enable UP045/UP007, so this is a 123-occurrence change the repo has not opted into; enabling the rule without the bulk fix breaks lint, and the bulk fix is a large noisy diff. Recommend the team enable UP045 and run the autofix in one dedicated commit. |
| LEG-03 | ValidationResult is an exported "backward compatibility alias" in annotation/integrity/__init__.py `__all__`. Removing it changes the package public API; needs a deprecation cycle decision. |
| LEG-04 | handwriting_detected is a documented compatibility schema field; dropping it needs confirmation that no Project B handoff consumer depends on it. |
| DEP-02 | Deduping the divergent requirements copies needs a `uv export` regeneration and a choice of canonical location; lockfile-affecting, better done with the dependency owner. |
| DEP-03, DEP-04 | Python floor raise and dependency pin changes require uv.lock regeneration and resolution checks; lockfile churn should be a standalone reviewed change. |
| CQ-03, CQ-06, CQ-08, ARCH-06 | Large or judgment-heavy (815 Any, 77 TODO triage, shared-helper extraction, annotation package split). Not mechanical. |
| ARCH-04, ARCH-05, ARCH-09 | Code moves and device-routing refactors touch runtime behavior; the model production-vs-retired marking (ARCH-05) overlaps the High DOC-02 narrative decision left for review. |
| SEC-02, SEC-03, SEC-05, SEC-06 | Security-behavior changes (model trust, checkpoint loading, upload streaming, key comparison) need tests and a trust-boundary decision; the audit couldn't run the relevant scanners offline. |
| SEC-04 | Re-dating a Snyk CVE ignore requires actually re-reviewing the ONNX CVE, not extending the expiry blind. |
| CQ-04, CQ-09 | type-ignore cluster and the zero-assert CodeQL fixture need investigation of the underlying untyped import and the CodeQL workflow's expectations before touching. |
| CI-02, CI-03, CI-04, CI-06, CI-07 | CI gate and config changes (mypy alignment, semgrep wiring, making bandit blocking, sonarcloud/compat dedup) can break the build or the security workflow; the bandit change in particular would fail CI on currently-unscanned findings. Each needs a maintainer to confirm the intended gate behavior. |

## Net

6 findings applied and verified, 3 reclassified as false positives, the rest deferred with reasons above. The applied set is documentation drift plus one safe code cleanup and one CI pin; none changes runtime behavior except LEG-06, which is covered by passing tests.
