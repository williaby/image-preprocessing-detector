# Repository Guidelines

Use this guide to onboard quickly and keep contributions consistent with the project’s practices.

## Project Structure & Module Organization

- `src/image_preprocessing_detector/`: Core package; ingestion, detection (IQA + layout-lite), classification, correction, metrics, routing/output, plus the larger subpackages annotation, labeling, synthetic, drift, api, and utils.
- `tests/`: Unit tests in `tests/unit/`, integration in `tests/integration/`, security and benchmarks under `tests/security/` and `tests/test_benchmarks/`.
- `configs/`: Training/inference configs (Modal/Colab YAMLs).
- `scripts/`: Data prep, training, benchmarking, and validation utilities; prefer `uv run python ...` to execute.
- `docs/`: MkDocs content (guides, ADRs, API reference); `overrides/` for theming.
- `data/`: DVC-tracked training sets (large, not committed) and `data/test_fixtures/` used in CI.

## Build, Test, and Development Commands

- Install: `uv sync --extra dev` (Python 3.10+, CI targets 3.12).
- Lint/format: `uv run ruff format .` then `uv run ruff check .`.
- Type check: `uv run basedpyright src`.
- Tests (fast CI set): `uv run pytest tests/unit -v` and `uv run pytest tests/integration -v -m "not requires_full_dataset"`.
- Full suite: `uv run nox -s tests-3.12 lint type_check` (mirrors CI).
- Docs: `uv run nox -s docs` (strict MkDocs build).

## Coding Style & Naming Conventions

- Ruff formatter (Black-compatible), 88 char line length, spaces for indentation, double quotes preferred.
- Google-style docstrings; type hints required for public functions.
- Prefer pathlib and explicit imports; avoid ad-hoc prints in library code (use structured logging in utils/log_config.py).
- Names: `snake_case` for functions/vars, `PascalCase` for classes, `SCREAMING_SNAKE_CASE` for constants; keep module names descriptive (`pdf_loader.py`, `json_generator.py`).

## Testing Guidelines

- Framework: pytest with property-based checks in targeted modules; coverage target ≥80%.
- Place new unit tests alongside modules in `tests/unit/`; integration scenarios in `tests/integration/`.
- Use markers: skip heavy datasets with `@pytest.mark.requires_full_dataset`; prefer fixtures in `data/test_fixtures/` for reproducibility.
- Include regression cases when fixing bugs; keep assertions specific and avoid broad mocks for pipeline flows.

## Commit & Pull Request Guidelines

- Conventional Commits with scope: `feat(detection): ...`; sign commits (GPG) and keep messages imperative.
- Before pushing: format, lint, type check, tests, and ensure coverage threshold; run `uv run pre-commit run --all-files` if hooks are installed.
- PRs should link issues (`Fixes #123`), describe changes and testing steps, and add screenshots for visual diffs.
- Update docs/CHANGELOG when user-facing behavior shifts; note breaking changes explicitly in the PR body.
