# Code Quality & Maintainability Audit — 2026-05-29

Summary: src is 107K LOC across 631 classes / 2452 functions; coverage gate is 60% (docs claim 80%), 815 `Any` usages, 59 type-ignores, 77 TODO/FIXME/XXX markers, 62 ruff errors, longest file 2845 lines.

## Findings

### CQ-01 — Coverage gate set to 60%, not the 80% the docs assert

- Severity: High | Effort: S
- Affected: `pyproject.toml`
- Evidence: `pyproject.toml: "--cov-fail-under=60"`. CLAUDE.md and project docs repeatedly state "80% minimum enforced via `--cov-fail-under=80`" and "All tests pass with 80%+ coverage". The configured gate is 60%. Note: `pytest --collect-only` failed in this env because pytest-cov is not installed (`unrecognized arguments: --cov=...`), so the live coverage figure could not be measured here.
- Recommendation: Reconcile the gate with the documented target. Either raise the gate to 80 or correct the docs to 60.

### CQ-02 — Oversized modules; one file at 2845 lines

- Severity: High | Effort: L
- Affected: `detection/iqa_classical.py` (2845), `synthetic/generator.py` (1735), `detection/iqa_ml.py` (1520), `metrics/dqs_calculator.py` (1507), `schema.py` (1411)
- Evidence: top-20 src files all exceed 800 lines. `iqa_classical.py` holds 67 functions in one file; its largest function `_compute_detailed_metrics` spans 99 lines, `detect` (JPEGBlockiness) 82 lines.
- Recommendation: Split `iqa_classical.py` per detector (one module per detector class). Extract long methods like `_compute_detailed_metrics`.

### CQ-03 — 815 `Any` annotations weaken strict typing on src

- Severity: Medium | Effort: M
- Affected: `logging/__init__.py` (26), `cli.py` (20), `synthetic/validation.py` (18), `synthetic/schema_adapter.py` (16), `logging/errors.py` (16), `labeling/arena/schemas.py` (16), `labeling/domain/openrouter_client.py` (15), `core/exceptions.py` (14)
- Evidence: `grep -rnE ":\s*Any\b|-> Any\b|\bAny\]" src/ | wc -l` = 815. basedpyright is configured strict on src, so each `Any` is an escape hatch around that strictness. Concentrated in logging and labeling/synthetic config layers (external/JSON boundaries).
- Recommendation: Replace boundary `Any` with TypedDict/Pydantic models where the shape is known; keep `Any` only at genuine dynamic edges with a comment.

### CQ-04 — 59 type/pyright-ignores, 14 in one file

- Severity: Medium | Effort: S
- Affected: `monitoring/__init__.py` (14), `logging/errors.py` (3), `annotation/monitoring/metrics.py` (3)
- Evidence: `grep -rn "# type: ignore\|# pyright: ignore" src/ | wc -l` = 59. `monitoring/__init__.py` carries 14 of them (24% of all ignores).
- Recommendation: Audit the 14 ignores in `monitoring/__init__.py`; cluster like that usually means one untyped import that a stub or `cast` would fix once.

### CQ-05 — 62 ruff errors, 60 are str-Enum modernization (UP042)

- Severity: Low | Effort: S
- Affected: `synthetic/config.py` and other enum definitions; `ASYNC240` (1, blocking path method in async fn), `FURB171` (1)
- Evidence: `ruff check --statistics`: `60 UP042 replace-str-enum`, `1 ASYNC240`, `1 FURB171`. 61 of 62 are auto-fixable via `--unsafe-fixes`.
- Recommendation: Migrate `class X(str, Enum)` to `enum.StrEnum` (project targets 3.11+). Investigate the single `ASYNC240` blocking-IO-in-async case by hand.

### CQ-06 — 77 TODO/FIXME/XXX markers; oldest dated 2026-02-22

- Severity: Low | Effort: M
- Affected: 63 TODO, 13 XXX, 1 FIXME across src/tests/scripts
- Evidence: `grep -rnoE "(TODO|FIXME|HACK|XXX)"` counts above. git blame on samples dates the oldest to 2026-02-22 (`annotation/cli.py:91`, `ingestion/document_processor.py:88`, `detection/layout_lite/doclayout_integration.py:607` and others), ~3 months old. No HACK markers.
- Recommendation: Triage the 13 XXX markers first (usually flag broken/risky code); convert actionable TODOs to tracked issues.

### CQ-07 — `torch.cuda.is_available()` called in 10 files despite a central device_probe util

- Severity: Medium | Effort: M
- Affected: `utils/device_probe.py` (canonical) vs direct callers `annotation/enrichment/providers/{yolo,docling_layout,siglip}.py`, `labeling/arena/inference/{regression,local,huggingface}.py`, `labeling/arena/runner.py`, `detection/{doclayout_yolo,siglip2_multitask}.py`
- Evidence: `grep -rlE "torch.cuda.is_available\(\)" src/` = 10 files; a `utils/device_probe.py` exists meant to centralize this. Device-selection logic is duplicated rather than routed through the probe.
- Recommendation: Route all device selection through `device_probe.py` so priority policy (Local GPU -> Modal -> CPU) is enforced in one place.

### CQ-08 — 58 hand-written `to_dict` / inline 0-1 clamping suggest missing shared helpers

- Severity: Low | Effort: M
- Affected: 58 `to_dict` defs, 15 `from_dict`, 15 inline `max(0, min(1, ...))` clamps, 10 `normalize` helpers across src
- Evidence: counts from grep above. Pydantic v2 models already provide serialization, so 58 manual `to_dict` methods are likely redundant; clamp-to-[0,1] is reimplemented 15 times inline.
- Recommendation: Add one `clamp01()` util and replace inline clamps. Audit `to_dict` methods on Pydantic models for redundancy with `model_dump()`.

### CQ-09 — Zero-assert test file; 138 runtime skips

- Severity: Medium | Effort: S
- Affected: `tests/security/test_codeql_validation.py` (no assert/raises/mock-assert anywhere); 138 `pytest.skip()` runtime guards
- Evidence: scan of `git ls-files tests/**/test_*.py` for `assert|pytest.raises|.assert_` found exactly one file with zero — `test_codeql_validation.py` (its bodies are `try/except: pass` blocks meant as CodeQL bait, so it validates nothing at runtime). 138 `pytest.skip()` calls; most are fixture-availability guards in `tests/conftest.py` (DocLayNet/TableBank/IQA fixtures "not available"), meaning large test surfaces silently skip when data is absent. Marker skips are low: 10 skip, 5 skipif, 3 xfail.
- Recommendation: Add real assertions to `test_codeql_validation.py` or mark it as a static-analysis fixture (not a pytest test). Audit how many of the 138 fixture-skips fire in CI; silently-skipped tests do not protect coverage.

## Clean areas

No HACK markers; marker-based skip/xfail count is low (18 total); no genuinely empty/`assert True`-only test bodies found (all bare `pass` are legitimate except-block bodies); type-ignore count (59) is low for 107K LOC; a central device_probe util already exists to consolidate CQ-07.
