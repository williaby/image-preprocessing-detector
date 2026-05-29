# Legacy Code Patterns Audit (2026-05-29)

Summary: The codebase is mostly modern. No pkg_resources, no `imp`, no `asyncio.get_event_loop`, pydantic v2 throughout, and a working datetime compat layer. The real findings are idiom drift (`typing.Optional`), a few unreferenced internal "deprecated" shims/aliases, one commented-out parser stub, and one file ignoring the stated pathlib standard.

Scope counted across `src/` (299 .py files). `vulture` is not installed in this environment (`uv run vulture` and `vulture` both unavailable), so dead-code claims below rest on grep heuristics and cross-reference checks, not a dead-code analyzer run.

## Findings

### LEG-01 — `typing.Optional` instead of `X | None` (3.10+ builtin)
- Severity: Low. Effort: M.
- Evidence: 123 occurrences of `Optional` across 56 of 299 src files (19% of files).
- Concentration: `drift/` (6 files), `synthetic/` (5), `detection/` (5), `schema_utils/` (4), `utils/`, `labeling/arena/`, `ingestion/` (3 each).
- `requires-python = ">=3.10,<3.15"` (pyproject.toml:9), so `X | None` is available everywhere. `List[`/`Dict[`/`Tuple[`/`Union[` are already absent (0/0/0/0 hits), so only `Optional` lags.
- Recommendation: Migrate `Optional[X]` to `X | None`; enable Ruff `UP045`/`UP007` to auto-fix and prevent regression. Cosmetic, no behavior change.

### LEG-02 — Unreferenced deprecated datetime shims in compat layer
- Severity: Low. Effort: S.
- Evidence: `utils/datetime_compat.py:305` `utcnow_compat()` and `:317` `utcfromtimestamp_compat()` are defined and self-documented as deprecated ("use utc_now() instead"), but grep across `src/ scripts/ tests/` finds zero call sites outside the defining file.
- The 2 raw `datetime.utcnow()` references in the repo are both inside this file (lines 305, 400) as docstrings/legacy wrappers, not live deprecated calls. Production code correctly imports `utc_now`/`UTC` from the compat layer (e.g. `api/routes/health.py`, `api/routes/batch.py`).
- Recommendation: Delete the two `*_compat()` shims; they are dead deprecated wrappers with no consumers.

### LEG-03 — Unreferenced deprecated alias `ValidationResult`
- Severity: Low. Effort: S.
- Evidence: `annotation/integrity/checkpointing.py:463` `ValidationResult = CheckpointValidationResult` tagged "Backward compatibility alias (deprecated)". No usages of the alias name found elsewhere in `annotation/`.
- Recommendation: Remove the alias; nothing imports it.

### LEG-04 — Deprecated schema field retained
- Severity: Low. Effort: S.
- Evidence: `schema.py:1084` field carries `description="DEPRECATED: Use handwriting_assessment.presence_score instead"`. The deprecated `handwriting_detected` name appears only once in src.
- Recommendation: Confirm no external JSON consumer (Project B handoff contract) depends on it, then drop on the next schema version bump. Low priority because it is a documented compatibility field, not silent cruft.

### LEG-05 — Commented-out parser code block
- Severity: Low. Effort: S.
- Evidence: `annotation/parsers/template.py:244-290` holds a ~12-line commented-out CSV/annotation-reading stub (`# for row in reader:`, `# if ann_path.exists():`, etc.). This file is a template, so the dead block is partly intentional scaffolding. Total commented-out-code hits across src are only 12 lines, and this file accounts for most of them.
- Recommendation: Replace the commented stub with a docstring example or a `raise NotImplementedError`; do not leave executable-looking dead lines in a copied template.

### LEG-06 — `os.path` in one file vs stated pathlib standard
- Severity: Low. Effort: S.
- Evidence: All 5 `os.path.join` calls in src live in a single file, `utils/metadata_generator.py` (lines 133, 170, 281, 315, 347). CONTRIBUTING.md:166/200/252 sets `pathlib.Path` as the standard and specifically calls for `Path.resolve()` for traversal safety.
- Recommendation: Convert this one file to `pathlib.Path`; the rest of the codebase already complies (only 1 of 299 files uses `os.path`).

### LEG-07 — `% ` string formatting outside logging
- Severity: Low. Effort: S.
- Evidence: 218 `%s/%d`-style literals total, but 138 are inside logger calls (`logger.info("...%s", x)`), which is the correct lazy-logging idiom and should stay. Only 2 are manual `%`-built assignment strings outside logging. The 6 `.format(` hits are mostly `result.format()` method calls on validation objects, not `str.format`, except `annotation/schemas/migrations.py:751/782` (`backup_suffix.format(version=...)`).
- Recommendation: Convert the 2 stray manual `%` strings and the 2 `migrations.py` `.format()` calls to f-strings. Leave logging `%` placeholders as-is. Effectively a non-issue.

## Clean areas
No `pkg_resources` / `imp` / `asyncio.get_event_loop`; pydantic v2 only (no `@validator`, `@root_validator`, `parse_obj`, or `class Config:` legacy calls); `List/Dict/Tuple/Union` typing generics already migrated; datetime handled through a real compat layer with no live `utcnow()` calls in production code; `os.path` isolated to one file; commented-out code near zero (12 lines); no resolved-but-stale feature flags found (the `FEATURE_`/`enable_*=True` grep hits were all legitimate config weights and runtime toggles).
