# Docs & Developer Experience Audit — 2026-05-29

README and CLAUDE.md disagree on the project's architecture, model, and phase status; README has 18 broken links; CONTRIBUTING tells new devs to use Poetry while the project runs on uv.

## Findings

### DOC-01 — README architecture contradicts CLAUDE.md (model + phase) — High — M
**Affected**: `README.md`, `CLAUDE.md`
**Evidence**:
- `README.md:130` "Phase 0: Project Setup (Week 0-1) - COMPLETE"; `README.md:141` "Next: Phase 2 - ResNet Teacher & Student ML IQA"; `README.md:398` "Phase 2: ResNet Teacher & Student ML IQA ... PLANNED"; `README.md:553` "Status: Phase 0 (Foundation) - Week 2-3 of 24-week development timeline".
- `CLAUDE.md:644` "Phases 0-6 COMPLETE | Streams 1-4C COMPLETE"; `CLAUDE.md:511` ResNet student "val_loss=0.14", Phase 3 marked COMPLETE.
- README presents ResNet IQA as not-yet-started; CLAUDE.md presents it as trained and complete. A new dev cannot tell which phase the project is in.
**Recommendation**: Pick one status source (CLAUDE.md is newer, dated 2026-02-21) and rewrite README Project Status + roadmap sections to match, or replace README status block with a link to MASTER_PROJECT_PLAN.md.

### DOC-02 — CLAUDE.md header model (SigLIP/MobileNetV4) contradicts its own body (ResNet) — High — M
**Affected**: `CLAUDE.md`
**Evidence**:
- `CLAUDE.md:146-148` current architecture = "MobileNetV4-Conv-S" gate + "SigLIP 2 NAFlex" multi-task teacher (16 heads) + "docling-layout (replaced YOLOv10-doc)".
- `CLAUDE.md:358` "Model Architecture: ResNet-50 teacher -> ResNet-18 student (NOT MobileNetV3/EfficientNet)"; `:511-512`, `:561`, `:622-624`, `:682-683`, `:764` all describe ResNet-50/18 teacher-student as the implemented model.
- Same file describes two different model families as "current." `:644` then says "SigLIP 2 training PENDING" while ResNet Phase 3 is "COMPLETE" — implying a migration in flight that no section explains.
**Recommendation**: Add a short "current vs target architecture" note: ResNet teacher-student = shipped; SigLIP 2 / MobileNetV4 = target. Tag the SigLIP/MobileNetV4 block as forward-looking.

### DOC-03 — Architecture shift SigLIP<-ResNet and docling<-YOLO not recorded in ADRs — High — M
**Affected**: `docs/ADRs/`
**Evidence**:
- ADR set has `0025-mobilenetv3-vs-efficientnet.md`, `0028-resnet-teacher-student-architecture.md`, `0015-yolov8-layout-detection.md`.
- No ADR mentions SigLIP (`grep -rl SigLIP docs/ADRs/*.md` returns none) despite `CLAUDE.md:147` naming SigLIP 2 NAFlex as the current teacher.
- Layout ADR is `0015-yolov8-layout-detection.md`; `CLAUDE.md:148` says docling-layout "replaced YOLOv10-doc". The YOLO->docling decision and the YOLOv8->YOLOv10 drift are unrecorded.
- Two duplicate ADR numbers: `0028-document-quality-score-design.md` + `0028-resnet-teacher-student-architecture.md`; `0030-document-quality-score-design.md` + `0030-gcs-colab-training-workflow.md`. Missing `0034`.
**Recommendation**: Add ADRs for SigLIP-2 teacher selection and docling-layout adoption; renumber the duplicate 0028/0030 pairs.

### DOC-04 — 18 broken relative links in README — Medium — M
**Affected**: `README.md`
**Evidence** (MISSING targets):
`docs/development/RAG Pipeline/project-a-project-plan.md`, `docs/PHASE2_QUICKSTART.md`, `docs/planning/PROJECT_PLAN.md` (linked twice, `:250`, `:347`), `docs/DATASET_METHODOLOGY.md`, `docs/architecture/ARCHITECTURE_SUMMARY.md`, `docs/architecture/ARCHITECTURE_CORRECTION.md`, `docs/DETECTION_TAXONOMY.md`, `docs/DOCUMENT_TYPE_COVERAGE_MATRIX.md`, `docs/architecture/AUDIT.md`, `docs/ADRs/0029-phase2-dataset-selection-strategy.md`, `docs/MODEL_STORAGE.md`, `docs/PUBLIC_DATASET_COVERAGE.md`, `docs/infrastructure/HF_SPACES_VS_COLAB_PRO.md`, `docs/TESTING_STRATEGY.md`, `docs/WTD-Runbook.md`, `docs/api-reference.md`, `docs/references/CITATIONS.md` (twice), `docs/research/image_reference_sets.md`.
Includes `PROJECT_PLAN.md` referenced as "Complete 114-page implementation plan" (`README.md:347`) — the marquee planning doc link is dead.
**Recommendation**: Repoint to current paths (e.g. `docs/planning/MASTER_PROJECT_PLAN.md`) or remove the dead entries.

### DOC-05 — CONTRIBUTING tells new devs to use Poetry; project uses uv — High — S
**Affected**: `CONTRIBUTING.md`
**Evidence**:
- `CONTRIBUTING.md:36-40` "Install dependencies with Poetry / `poetry install --with dev` / `poetry run pre-commit install`".
- `pyproject.toml:281-282` build-backend = hatchling; no `[tool.poetry]` table; `uv.lock` present (no `poetry.lock`). CLAUDE.md and README both use `uv sync` / `uv run`.
- A fresh clone following CONTRIBUTING runs `poetry install` against a uv project.
**Recommendation**: Replace the Poetry block with `uv sync --extra dev` and `uv run pre-commit install`.

### DOC-06 — Hardcoded foreign path `/home/byron/dev/image_detection` in CLAUDE.md setup commands — Medium — S
**Affected**: `CLAUDE.md`, plus ~949 `/home/byron`+`/mnt/e` hits across `docs/` (most in planning/audit)
**Evidence**:
- `CLAUDE.md:331` and `CLAUDE.md:1022` `PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH uv run python validation/...`. Path does not exist on a fresh checkout (`ls` fails). A new dev copy-pasting the validation command sets a nonexistent PYTHONPATH.
- `grep -rn "/home/byron|/mnt/e" docs/` = 949 hits across planning, audit, known_issues, model-cards.
**Recommendation**: Replace the two CLAUDE.md commands with `PYTHONPATH=$(pwd)` or the repo root. The 949 doc-wide hits are mostly handoff/audit notes (lower priority) but worth a sweep.

### DOC-07 — Stale "1,292 files mapped" count; inventory self-flagged STALE (Jan 2025) — Medium — S
**Affected**: `CLAUDE.md:50`, `docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`
**Evidence**:
- `CLAUDE.md:50` "1,292 files mapped".
- Target file header (lines 13-18) carries its own banner: "STALE — Last accurate: January 2025. WS1/2/3/4/8 file counts are out of date ... not for LOC accuracy."
- Repo now tracks 3,834 git files; `src/` alone has 299 `.py` files, 971 `.py` total. The 1,292 figure is ~16 months stale and the doc disclaims its own accuracy.
**Recommendation**: Drop the count from CLAUDE.md or replace with "see inventory (regenerate via scripts/extract_workstream_loc.sh)".

### DOC-08 — Test-count claims understated vs reality (5,793 actual) — Low — S
**Affected**: `CLAUDE.md:507,529,665,671,679,708`
**Evidence**:
- Claims: "99 tests" (`:671`), "21/21 integration" (`:529,679`), "61 tests" (`:507,665`), "156+ tests" (`:708`).
- Actual: 5,793 `def test_` across 224 test files; 22 integration test files. The per-phase counts are point-in-time snapshots now far below the real suite; harmless but misleading about coverage scale.
**Recommendation**: Replace fixed numbers with "see `uv run pytest --collect-only`" or update to current totals.

### DOC-09 — Broken links in docs index / level-1 architecture index — Low — S
**Affected**: `docs/index.md`, `docs/architecture/diagrams/level-1/index.md`
**Evidence**:
- `docs/index.md` links `planning/PROJECT_PLAN.md` (missing, twice).
- `docs/architecture/diagrams/level-1/index.md` links `../../development/RAG%20Pipeline/prepare-doc-unify-contract.md` (missing).
**Recommendation**: Repoint to MASTER_PROJECT_PLAN.md and the actual contract doc path.

## Healthy / accurate docs
- `pyproject.toml` `[project.scripts]` (`imgprep`, `annotate`) match `src/image_preprocessing_detector/cli.py` and `annotation/cli.py`.
- `docs/ADRs/README.md` index links: all resolve (0 broken).
- `docs/datasets/README.md` links: all resolve (0 broken).
- ADR catalog (0001-0036) is broad and current for most decisions except the SigLIP/docling gaps (DOC-03).
- `mkdocs.yml` and `.readthedocs.yaml` both present.
- CLAUDE.md internal `.md` links: only 1 broken (the RAG Pipeline plan, same dead target as README).
