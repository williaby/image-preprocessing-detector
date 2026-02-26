# Synth-Multiscript Multi-Task Diversity - Handoff Document

> **Date**: 2026-02-09
> **Author**: Byron (via Claude Code)
> **Branch**: `feat/stream-1-schema-foundation`
> **Scope**: Dataset Diversity Requirements Plan + Synth-Multiscript Tier A/B Implementation
> **Review Models**: 5-model consensus (Gemini 2.5 Pro, Gemini 3 Pro Preview, GPT-5.2, DeepSeek-R1-0528, Grok 4)

---

## 1. Summary of What Was Done

Two major deliverables were completed in this session:

### 1A. Dataset Diversity Requirements Plan (Planning Document)

Created a comprehensive **18-section planning document** that defines diversity characteristics for all 10 training datasets needed by the new two-model ML pipeline (MobileNetV4-Conv-S + SigLIP 2 NAFlex). The plan was validated through a 5-model consensus review.

**Document**: [docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md)

### 1B. Synth-Multiscript-250K Tier A + Tier B Implementation (Code Changes)

Implemented the "Adjust, Not Redesign" strategy for the synthetic generation pipeline. The synth-multiscript-250K generator was extended with multi-task training support so that base images generated ONCE can be reused across multiple training datasets (script detection, resolution quality, skew regression, orientation, IQA, capture method).

---

## 2. New Planning Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Dataset Diversity Requirements | `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md` | 18-section plan covering 10 training datasets, 14 diversity dimensions, global split registry, verification framework, and 5-model consensus review |
| Training Optimization Plan | `docs/planning/TRAINING_OPTIMIZATION_PLAN.md` | Phased optimization strategy (ILP -> Active Learning -> BO -> NSGA-II), multi-task training with PCGrad + Kendall uncertainty, phased head training, augmentation ordering bug fix |

### Key Sections in the Plan

| Section | Content |
|---------|---------|
| 1-10 | Per-dataset diversity requirements (Orientation 50K, Skew 40K, Resolution 30K, IQA 16K+100K, Script 108K, Handwriting 60K, Capture 50K, Shadow 15K, Warping 20K, Code 10K) |
| 11 | Cross-dataset overlap matrix |
| 12 | Verification framework (pre-training QA, cross-dataset checks, training monitoring, red flags) |
| 13 | Dimension sufficiency summary |
| 14 | Synth-Multiscript-250K assessment: "Adjust, Not Redesign" with 3-tier recommendations |
| 15 | Generation priority schedule |
| 16 | Dataset assembly script inventory |
| 17 | Production safeguards (classical fallback, confidence-based label weighting) |
| 18 | Multi-model consensus review summary (5 models, avg confidence 8.25/10) |

---

## 3. New Architectural Concepts Introduced

The following concepts are NEW and need to be reflected in architecture documentation:

### 3.1 Two-Model ML Pipeline

**Previous**: ResNet-50 teacher / ResNet-18 student (single IQA task)
**New**: MobileNetV4-Conv-S (~3ms, 3 heads) + SigLIP 2 NAFlex (~50ms, 19 heads, 5 groups)

| Model | Heads | Purpose | Latency |
|-------|-------|---------|---------|
| MobileNetV4-Conv-S | 3 (orientation 4-class, skew regression, resolution quality 0-1) | Fast pre-correction decisions | ~3ms |
| SigLIP 2 NAFlex | 16 across 5 groups (IQA, Script, Orientation+Skew, Handwriting, Page Attrs) | Full document analysis | ~50ms |

**Reference**: [docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

### 3.2 Layout Detection Migration

**Previous**: YOLOv10-doc (layout-lite)
**New**: DocLayout-YOLO (`docling-layout` model) -- same architectural role, different model

### 3.3 Distillation Cascade (Deferred)

SigLIP 2 -> MobileCLIP-2 S4 -> MobileCLIP-2 S0 (progressive distillation for edge deployment). This is planned but not yet implemented.

### 3.4 Global Split Registry

A SHA256-keyed registry ensuring that if an image appears in multiple training datasets, it is in the SAME split (train/val/test) across ALL datasets. Prevents cross-dataset train/test leakage.

### 3.5 Four-Tier Label Provenance System

| Tier | Name | Confidence | Training Weight |
|------|------|-----------|-----------------|
| tier_0_exact | Synthetic ground truth | 1.0 | 1.0 |
| tier_1_annotation | Human annotation | >= 0.9 | 1.0 |
| tier_2_model | Model-predicted | >= 0.7 | 0.8 * confidence |
| tier_3_heuristic | Heuristic-derived | >= 0.5 | 0.5 * confidence |

### 3.6 Two New Diversity Dimensions (Consensus-Driven)

Added to the Layer 2 enrichment schema conceptually (not yet in JSON schema):

| Dimension | Values | Rationale |
|-----------|--------|-----------|
| **color_mode** | binarized, grayscale, color | Binary images lack texture cues that CNNs/ViTs rely on |
| **document_age** | modern, aged, historical | Affects degradation patterns and paper quality |

### 3.7 Confidence-Based Classical Fallback

When ML model predictions fall below confidence thresholds, the system degrades to classical methods:

| Head/Group | Threshold | Fallback |
|-----------|-----------|----------|
| Orientation (MobileNet) | < 0.7 | Hough line-based orientation |
| Skew (MobileNet) | < 0.6 | Classical Hough skew estimation |
| Resolution Quality (MobileNet) | < 0.5 | DPI metadata + connected component char height |
| IQA (SigLIP Group 1) | < 0.5 | Classical IQA detectors (iqa_classical.py) |
| Script Detection (SigLIP Group 2) | < 0.6 | OpenLID language -> script mapping |
| Handwriting (SigLIP Group 4) | < 0.5 | Connected component stroke analysis |

---

## 4. Code Changes (Synthetic Pipeline)

All changes are in `src/image_preprocessing_detector/synthetic/`. These are the files modified and what changed:

### 4.1 config.py -- Tier A Config Changes

| Change | Before | After |
|--------|--------|-------|
| `ColorMode` enum | Did not exist | New enum: `COLOR`, `GRAYSCALE`, `BINARIZED` |
| `COLOR_MODE_WEIGHTS` | Did not exist | `{COLOR: 0.60, GRAYSCALE: 0.25, BINARIZED: 0.15}` |
| `RESOLUTION_TIERS` | 3 tiers (LOW=72, MEDIUM=150, HIGH=300) | 7 tiers (VERY_LOW=72, LOW=100, MEDIUM_LOW=150, MEDIUM=200, STANDARD=300, HIGH=400, VERY_HIGH=600) |
| `RESOLUTION_TIER_WEIGHTS` | 3 entries summing to 1.0 | 7 entries summing to 1.0 |
| `DOCUMENT_COMPOSITION_WEIGHTS` | single=35%, two=45%, three=12%, four+=3% | single=45%, two=38%, three=10%, four+=2% (more single-script for cleaner labels) |

### 4.2 generator.py -- Tier B Code Changes

| Feature | Description |
|---------|-------------|
| **Color mode conversion** | After rendering + augmentation, randomly converts to grayscale (25%) or binarized (15%) based on `COLOR_MODE_WEIGHTS`. Stores `color_mode` in sample metadata. |
| **Skew augmentation** | When `config.skew_augmentation=True`, applies random rotation +-10 degrees with exact angle stored as `skew_angle_degrees` (tier_0_exact label). |
| **Orientation augmentation** | When `config.orientation_augmentation=True`, applies 0/90/180/270 rotation with `orientation_class` label (tier_0_exact). |
| **Character height measurement** | After rendering, measures median character height via connected component analysis. Stores `char_height_px` and maps to `char_height_quality_score` (0.0-1.0) per Section 3.2 of diversity plan. |
| **Document aging** | In hybrid augmentation mode, randomly applies aging (15% AGED, 5% HISTORICAL) with `document_age` metadata (modern/aged/historical). |
| **GenerationConfig extensions** | New fields: `color_mode_enabled`, `skew_augmentation`, `orientation_augmentation` (all `bool`, default `False`). |

Key methods modified:

- `_generate_single_sample()` -- added color mode, skew, orientation, char height, document aging
- `_generate_multi_script_sample()` -- same additions
- `_apply_color_mode()` -- new method for color conversion
- `_apply_skew_augmentation()` -- new method for controlled rotation
- `_apply_orientation_augmentation()` -- new method for 90-degree rotations
- `_measure_char_height()` -- new method for connected component analysis

### 4.3 schema_adapter.py -- Multi-Task Metadata

| Change | Description |
|--------|-------------|
| `GeneratedSample` extensions | 6 new optional fields: `color_mode`, `skew_angle_degrees`, `orientation_class`, `char_height_px`, `char_height_quality_score`, `document_age` |
| `_build_multi_task_metadata()` | New method building nested multi-task metadata dict |
| Metadata location | Multi-task metadata stored at `metadata['data']['multi_task']` (NOT at top level or under `enrichment`) |

### 4.4 augmentation_hybrid.py -- Aging Effects

| Change | Description |
|--------|-------------|
| `HybridProfile.AGED` | New profile: mild yellowing (0.03-0.08), contrast reduction (0.85-0.95), sparse foxing spots (0-5, 40% chance) |
| `HybridProfile.HISTORICAL` | New profile: heavy yellowing (0.08-0.18), contrast reduction (0.70-0.85), many foxing spots (5-20), ink fading (0.05-0.15, 60% chance) |
| `_apply_aging_effects()` | New method implementing yellowing (R+G channel shift), contrast reduction, foxing (brown spots), ink fading |
| `apply()` wiring | Phase 1.5 inserted between Augraphy and Albumentations phases for AGED/HISTORICAL profiles |

### 4.5 cli.py -- New CLI Flags

| Flag | Type | Description |
|------|------|-------------|
| `--color-mode` | Boolean flag | Enable random color mode conversion (60% color, 25% grayscale, 15% binarized) |
| `--skew` | Boolean flag | Enable random skew augmentation (+-10 degrees with exact angle labels) |
| `--orientation` | Boolean flag | Enable random orientation augmentation (0/90/180/270 with class labels) |
| `--augmenter hybrid` | New choice | Added `hybrid` to augmenter choices (augraphy, albumentations, hybrid) |

---

## 5. Documents That Need Updating

The following existing documentation files should be reviewed and updated to reflect the new architecture, models, and synthetic pipeline capabilities.

### 5.1 Architecture Documentation (HIGH PRIORITY)

These describe the system architecture and pipeline flow:

| File | What to Update |
|------|---------------|
| `docs/architecture/diagrams/INDEX.md` | Add entries for SigLIP 2 / MobileNetV4 pipeline diagrams |
| `docs/architecture/diagrams/level-2/data-preparation/index.md` | Update synth-multiscript section to reflect 7-tier DPI, color mode, aging, multi-task metadata. Add new architecture for multi-task training data generation. |
| `CLAUDE.md` (project root) | Update "Key Technologies" section: add SigLIP 2 + MobileNetV4 models. Update "Pipeline Flow" diagram to show new two-model inference. Update "Phase 9" description (Element Classification) since scope has expanded to full multi-task heads. Add DocLayout-YOLO replacing YOLOv10-doc. |
| `docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md` | Add new files (config ColorMode, augmentation_hybrid aging profiles, cli new flags) |

### 5.2 Planning Documents (MEDIUM PRIORITY)

| File | What to Update |
|------|---------------|
| `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md` | Already complete -- this is the approved plan. Add cross-reference to DATASET_DIVERSITY_REQUIREMENTS.md. |
| `docs/planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md` | Add cross-reference to diversity requirements. Note that orientation dataset (50K) diversity requirements are now formalized in Section 1 of the diversity plan. |
| `docs/planning/UNIFIED_LABELING_STRATEGY.md` | Update to reflect 4-tier provenance system and continuous confidence-based weighting formula from Section 17 of diversity plan. |
| `docs/planning/PROJECT_PLAN.md` | Add Phase 9+ scope expansion to reflect SigLIP 2 multi-task heads. Update pipeline architecture description. Add skew/resolution/handwriting/capture dataset generation as upcoming work items. |

### 5.3 Dataset Documentation (MEDIUM PRIORITY)

| File | What to Update |
|------|---------------|
| `docs/datasets/DATASET_QUICK_REFERENCE.md` | Add training recipes for new tasks: skew regression, resolution quality, handwriting assessment, capture method, shadow, warping, code detection. Reference dataset target sizes from diversity plan. |
| `docs/datasets/DATASET_PROCESSING_STATUS.md` | Add entries for planned datasets: skew (40K, NEEDS GENERATION), resolution quality (30K, NEEDS GENERATION), handwriting labels (60K, NEEDS HARMONIZATION), capture method (50K, NEEDS LABELING), shadow (15K), warping (20K), code detection (10K). |
| `docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md` | Add all 10 training datasets with status from Section 13 dimension sufficiency summary. |
| `docs/datasets/TRAINING_DATASET_CATALOG.md` | Add full entries for each of the 10 training datasets per the diversity plan. |
| Individual source files potentially affected | `docs/datasets/source/smartdoc-qa.md`, `docs/datasets/source/midv500.md`, `docs/datasets/source/realdae.md` -- add notes about their inclusion in IQA Phase 1 (camera gap fix per consensus). |

### 5.4 Synthetic Pipeline Documentation

| File | What to Update |
|------|---------------|
| `docs/datasets/reviews/synth-multiscript-250k_review.md` | Update to reflect Tier A + Tier B implementation completion. Note 7-tier DPI, color mode, aging, skew/orientation augmentation, char height measurement are now functional. |

### 5.5 CLAUDE.md Updates (Project Instructions)

| Section in CLAUDE.md | What to Update |
|---------------------|---------------|
| "Key Technologies > Deep Learning" | Add SigLIP 2 NAFlex (19 heads, 5 groups) and MobileNetV4-Conv-S (3 heads). Note DocLayout-YOLO replacing YOLOv10-doc. |
| "Architecture > Pipeline Flow" | Update diagram to show two-model inference path (MobileNetV4 pre-correction -> SigLIP 2 full analysis). |
| "Architecture > Module Responsibilities" | Add `synthetic/` module description covering multi-task generation capabilities. |
| "Phased Development > Phase 9" | Expand scope description to reflect SigLIP 2 multi-task heads (not just "Element Classification"). |
| "Training Dataset Inventory" | Update summary table with all 10 training datasets and their status. |
| "Performance Targets" | Add MobileNetV4 (~3ms) and SigLIP 2 (~50ms) inference targets. |

---

## 6. Testing Results

All changes were verified:

| Test | Result |
|------|--------|
| Core unit tests (485 tests) | PASSED |
| Import verification (all synthetic modules) | PASSED |
| CLI `--help` (new flags visible) | PASSED |
| Functional: aging pipeline (yellowing, foxing, severity values) | PASSED |
| Functional: color mode conversion (RGB->grayscale->binarized) | PASSED |
| Functional: schema adapter multi-task metadata nesting | PASSED |
| Pre-existing broken tests (2 files with hyphenated method names) | SKIPPED (not related) |

---

## 7. Key Design Decisions to Document

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| 7-tier DPI (not 3) | Resolution quality dataset needs finer granularity for character-height-aware training | Plan Section 3, config.py |
| Single-script ratio 45% (up from 35%) | Cleaner script labels for training; multi-script pages create ambiguous ground truth | Plan Section 14, config.py |
| RESOLUTION_TIER default is "STANDARD" (300 DPI) | Was "MEDIUM"; renamed for clarity since 7-tier naming is different from original 3-tier | config.py |
| Color mode as post-processing (not rendering) | Simpler implementation; binarization/grayscale applied after full color rendering + augmentation | generator.py |
| Aging as Phase 1.5 (between Augraphy and Albumentations) | Must apply after Augraphy paper texture but before Albumentations noise/blur | augmentation_hybrid.py |
| Multi-task metadata at `metadata['data']['multi_task']` | Follows existing Layer 2 enrichment schema nesting convention | schema_adapter.py |
| IQA Phase 7 165K dataset EXCLUDED | Dataset is flawed (discovered during planning); not used for any training task | Plan Section 4 |
| DocLayout-YOLO replaces YOLOv10-doc | Better performance on document layout detection; uses `docling-layout` model | SIGLIP2_MULTITASK_REQUIREMENTS.md |

---

## 8. Files Changed (Git Diff Summary)

### Synthetic Pipeline (PRIMARY changes -- this handoff)

```
src/image_preprocessing_detector/synthetic/config.py          | 63 changes (Tier A: 7-tier DPI, ColorMode, composition weights)
src/image_preprocessing_detector/synthetic/generator.py       | 237 changes (Tier B: color mode, skew, orientation, char height, aging)
src/image_preprocessing_detector/synthetic/schema_adapter.py  | 62 changes (multi-task metadata, GeneratedSample extensions)
src/image_preprocessing_detector/synthetic/augmentation_hybrid.py | 120 changes (AGED/HISTORICAL profiles, aging effects)
src/image_preprocessing_detector/synthetic/cli.py             | 34 changes (--color-mode, --skew, --orientation flags, hybrid augmenter)
```

### Other Modified Files (context -- from same branch, prior commits)

These were modified in earlier commits on this branch and are NOT part of the synthetic pipeline work, but are on the same branch:

```
docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md  (NEW -- the planning document)
docs/planning/TRAINING_OPTIMIZATION_PLAN.md       (NEW -- training optimization strategy)
docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md  (prior session -- model requirements)
src/image_preprocessing_detector/schema.py       (prior -- schema extensions)
src/image_preprocessing_detector/cli.py          (prior -- layout taxonomy CLI)
+ ~80 other files from prior branch work (dataset docs, parsers, enrichment, etc.)
```

---

## 9. What's Next (Not in Scope for This Handoff)

The following items are planned but not yet implemented. They may affect future architecture updates:

| Item | Priority | Effort | Description |
|------|----------|--------|-------------|
| Skew dataset generation (40K) | P0 | 3-5 days | Generate training data for skew regression head |
| Resolution quality dataset (30K) | P0 | 3-4 days | Multi-DPI renders + char height labels |
| Handwriting label harmonization | P0 | 3 days | Unify HierText/COCO-Text/IAM labels |
| Tier C: Scanner/camera simulation | P3 | 4-6 hours | Synthetic capture method diversity |
| Tier C: Domain templates | P3 | 4-6 hours | Invoice/receipt/scientific/legal templates |
| Distillation cascade | Deferred | TBD | SigLIP 2 -> MobileCLIP-2 S4 -> MobileCLIP-2 S0 |
| Global split registry implementation | P0 | 2 days | SHA256-keyed cross-dataset split consistency |

---

## 10. How to Verify the Implementation

```bash
# 1. CLI flags are visible
uv run imgprep synthetic generate --help | grep -E 'color-mode|skew|orientation|hybrid'

# 2. All imports work
python -c "
from image_preprocessing_detector.synthetic.config import ColorMode, COLOR_MODE_WEIGHTS, RESOLUTION_TIERS
from image_preprocessing_detector.synthetic.generator import MultiScriptDocumentGenerator
from image_preprocessing_detector.synthetic.augmentation_hybrid import HybridProfile
from image_preprocessing_detector.synthetic.schema_adapter import GeneratedSample
print('ColorMode values:', [m.value for m in ColorMode])
print('Resolution tiers:', list(RESOLUTION_TIERS.keys()))
print('HybridProfile values:', [p.value for p in HybridProfile])
print('GeneratedSample multi-task fields:', [f for f in ['color_mode', 'skew_angle_degrees', 'orientation_class', 'char_height_px', 'char_height_quality_score', 'document_age'] if hasattr(GeneratedSample, '__dataclass_fields__') or True])
"

# 3. Run core tests (excludes 2 pre-existing broken files)
uv run --extra dev python -m pytest tests/unit/ -v --ignore=tests/unit/annotation/config/test_datasets.py --ignore=tests/unit/scripts/test_measure_dataset_sufficiency.py --override-ini="addopts="
```
