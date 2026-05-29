# 04 - Architecture & Structure Audit

One-line summary: Subpackage boundaries are mostly clean (no cross-subpackage cycles among the big three), but the package has scattered config with zero detector wiring to the central Settings, duplicated logging/device-probe implementations, a layering inversion in top-level `schema.py`, an `annotation/` god-package (33% of LOC), and docs that describe three contradictory model lineages plus a wrong toolchain.

Method note: pydeps/import-linter not available in this environment. Coupling derived from `grep` over `from/import image_preprocessing_detector.<pkg>` statements across `src/`. Counts are import-statement occurrences, not unique-module edges.

## Coupling overview

Internal import-statement counts by target subpackage (most-depended-on first):

| Target | Import count |
|--------|-------------:|
| utils | 98 |
| labeling | 84 |
| detection | 83 |
| annotation | 60 |
| synthetic | 48 |
| schema_utils | 35 |
| schema | 19 (17 files import top-level `schema.py`) |
| api | 18 |
| ingestion | 15 |
| routing / classification | 11 / 11 |
| models | 10 |
| core | 5 |
| logging | ~2 importers (near-dead, see ARCH-03) |

LOC concentration: package total 106,740 LOC. `annotation/` = 34,787 (33%), `detection/` = 15,517 (15%). Largest single files: `detection/iqa_classical.py` (2,845), `synthetic/generator.py` (1,735), `detection/iqa_ml.py` (1,520), `metrics/dqs_calculator.py` (1,507), `schema.py` (1,411).

## Findings

### ARCH-01 - Scattered thresholds; detectors ignore the central Settings
Severity: High. Effort: L.
Affected: `detection/*.py` (all), `core/config.py`.
Evidence: `core/config.py` defines a hand-rolled `Settings` class (`IMAGE_PREP_` env prefix) but only 4 files import `core.config` (`cli.py`, `synthetic/config.py`, `ingestion/pdf_analyzer.py`, `classification/pdf_type_classifier.py`). Zero files in `detection/` import `core` or `Settings`. 210 hardcoded float literal assignments live in `detection/*.py`, e.g. `blank_page_detector.py:49 _DEFAULT_VARIANCE_THRESHOLD = 100.0`, `code_detector.py:59-63`, `deskew_pipeline.py:46-48`, `discrepancy.py:170 aggregate_threshold = 0.25`, `cross_model_validator.py:103 agreement_threshold = 2.0`.
Recommendation: Route detector thresholds through `core.Settings` (or a per-detector config dataclass loaded from it) so tuning is centralized and testable rather than edited across 20 detector files.

### ARCH-02 - Multiple config systems, no single source of truth
Severity: High. Effort: M.
Affected: `core/config.py`, `api/config.py`, `synthetic/config.py`, `labeling/handwriting/config.py`, `labeling/domain/config.py`, `annotation/config/settings.py`, plus ~15 ad-hoc `*Config` dataclasses.
Evidence: Two different config base mechanisms coexist: hand-rolled env parsing in `core/config.py:14 class Settings` (custom `_get_bool_env`/`_get_int_env` helpers) vs pydantic `BaseSettings` in `api/config.py:17 class APISettings(BaseSettings)`. On top, 8 separate `config.py`/`settings.py` files and ~15 inline `*Config` dataclasses (`AnnotationSettings`, `ScriptConfig`, `DevicePolicyConfig`, `DQSWeightConfig`, `RetrainingConfig`, `AlertConfig`, ...). No unifying config layer.
Recommendation: Standardize on pydantic-settings `BaseSettings` and have `core` own the root config; let subpackage configs be nested models rather than parallel systems.

### ARCH-03 - Two logging setups; the dedicated `logging/` package is near-dead
Severity: High. Effort: M.
Affected: `logging/__init__.py`, `utils/log_config.py`.
Evidence: `setup_logging` and `get_logger` are each defined twice: `logging/__init__.py:297,419` and `utils/log_config.py:33,119`. 57 files import the `utils` logger (`from image_preprocessing_detector.utils import get_logger` / `utils.log_config`), only ~2 import the `logging` package version. Separately, 20+ `annotation/parsers/*` modules call `structlog.configure`/`logging.getLogger` directly instead of either helper. AGENTS.md:27 names `utils/log_config.py` as the canonical logger, leaving the entire `logging/` package's `setup_logging`/`get_logger` as dead parallel infrastructure.
Recommendation: Delete or merge the `logging/` package's duplicate setup into `utils/log_config.py`; keep `logging/` for its `errors.py`/`outcomes.py` domain types only. Stop per-module `structlog.configure`.

### ARCH-04 - Layering inversion: top-level `schema.py` imports a subpackage
Severity: Medium. Effort: M.
Affected: `schema.py`, `annotation/schemas/enums.py`, `schema_utils/`.
Evidence: `schema.py:19 from image_preprocessing_detector.annotation.schemas.enums import CaptureMethod`. `schema.py` is the most foundational data-model module (imported by 17 files) yet depends downward into the large `annotation/` subpackage. No import cycle today (`annotation/` does not import top-level `schema.py`, and `enums.py` has no internal imports), so this is a latent inversion, not a live cycle. `schema.py` also pulls `schema_utils.iso_language_script` (line 20), which is acceptable since `schema_utils` is leaf-level.
Recommendation: Move `CaptureMethod` (and any shared enums) into `schema_utils/` or a new `core/enums.py` so the base schema does not depend on the annotation subpackage.

### ARCH-05 - Doc/code drift: three contradictory model lineages all present in `detection/`
Severity: Medium. Effort: S (docs).
Affected: CLAUDE.md, `detection/`.
Evidence: CLAUDE.md header (two-model pipeline) names MobileNetV4-Conv-S + SigLIP 2 NAFlex + docling-layout and says "replaced YOLOv10-doc"; the same file's module map and Phase 3 sections describe ResNet-50 teacher / ResNet-18 student as production. `detection/` actually contains all lineages simultaneously: `siglip2_multitask.py`, `iqa_ml.py` (ResNet), and `doclayout_yolo.py`. CLAUDE.md status line says "SigLIP 2 training PENDING" while the architecture diagram presents SigLIP/MobileNetV4 as current. Reader cannot tell which is the live path.
Recommendation: Pick the authoritative pipeline in CLAUDE.md, mark the others as legacy/experimental, and note in `detection/__init__.py` which model modules are production vs retired.

### ARCH-06 - `annotation/` god-package
Severity: Medium. Effort: L.
Affected: `annotation/` (130 .py files, 34,787 LOC, 8 sub-subpackages: config, enrichment, integrity, monitoring, parsers, schemas, storage, workflow).
Evidence: 33% of total package LOC in one subpackage; it carries its own CLI (`annotation/cli.py`, wired as the `annotate` entry point), its own logging (`annotation/monitoring/logging.py`), its own config (`annotation/config/settings.py`), and its own metrics. It is effectively a second application inside the package.
Recommendation: Treat `annotation/` as a candidate for extraction into its own top-level package/distribution, or at minimum document it as a distinct application boundary; do not let general-purpose helpers leak into it.

### ARCH-07 - Toolchain/structure drift in CONTRIBUTING.md and AGENTS.md
Severity: Medium. Effort: S.
Affected: CONTRIBUTING.md, AGENTS.md.
Evidence: CONTRIBUTING.md:44-46,105-134 prescribe `poetry run black`, isort, and mypy; pyproject + CLAUDE.md use `uv`, `ruff format`/`ruff check` (isort via ruff rule `I`, pyproject:324) and `basedpyright` (pyproject:87). AGENTS.md:11-19 also says `poetry install` / `poetry run`. AGENTS.md:7 describes the package as only "ingestion, detection (IQA + layout-lite), correction, routing/output, utils" omitting the largest subpackages (`annotation`, `labeling`, `synthetic`, `drift`, `api`, `monitoring`).
Recommendation: Update both docs to `uv` + ruff + basedpyright and expand the module map to list `annotation`, `labeling`, `synthetic`, `drift`.

### ARCH-08 - Orphan CLI module `cli_layout.py`
Severity: Low. Effort: S.
Affected: `cli_layout.py`.
Evidence: pyproject `[project.scripts]` declares only `imgprep = ...cli:cli` (line 264) and `annotate = ...annotation.cli:cli` (line 266). `cli_layout.py` (361 LOC) is referenced by no entry point and by no other module (1 self-referential import only); it is a third, unwired CLI surface parallel to `cli.py` (1,163 LOC).
Recommendation: Either register `cli_layout` as a subcommand group under `imgprep` or remove it; an unreachable 361-LOC CLI invites drift.

### ARCH-09 - Ad-hoc device probing alongside the dedicated `device_probe`/`DeviceOrchestrator`
Severity: Low. Effort: S.
Affected: `utils/device_probe.py`, `orchestration/device_orchestrator.py` vs `annotation/enrichment/providers/{docling_layout,yolo}.py`, `labeling/arena/inference/*`, `labeling/arena/runner.py`.
Evidence: A first-class device layer exists (`utils/device_probe.py:38 DeviceCapabilities`, `orchestration/device_orchestrator.py:149 DeviceOrchestrator` with `select_device_for_student/teacher`), yet at least 6 other sites bypass it with raw `torch.cuda.is_available()` checks (`docling_layout.py:127,161`, `yolo.py:103,142`, `arena/inference/local.py:208,234`, `arena/runner.py:544,557`, `arena/inference/regression.py:93-98,278`).
Recommendation: Have provider/arena code request a device through `DeviceOrchestrator`/`device_probe` so policy (GPU priority, budget) applies uniformly.

## Structurally sound

- No cross-subpackage import cycles among the three largest packages (`annotation`, `labeling`, `detection` are mutually independent; verified by grep).
- `schema_utils/` is a clean leaf layer (no internal upward imports).
- `utils/` internal imports are flat and one-directional (`device_probe`/`tensor_cache`/`budget_enforcement` -> `log_config`/`datetime_compat`); no util imports a high-level pipeline package.
- `core/` depends only downward on `utils` (`core/config.py:9`); no inward dependency from low-level into high-level pipeline code.
- Naming conventions (snake_case modules, PascalCase classes) hold consistently across the sampled subpackages.
