# Layer 2 Metadata Enrichment Audit Prompt

> **Version**: 2.0.0
> **Last Updated**: 2026-02-12
> **Usage**: Copy this prompt into a new Claude session, replacing all `{PLACEHOLDERS}` with dataset-specific values.
> **Prerequisite**: The dataset must already have Layer 2 metadata JSON at the standard registry path.

---

## BEGIN PROMPT

You are conducting a comprehensive Layer 2 metadata enrichment audit for the **{DATASET_NAME}** dataset ({TOTAL_SAMPLES} samples). Your goal is to validate every enrichment field for coverage, validity, and accuracy, then fix all defects and produce a complete audit trail.

### Project Context

This is Prepare-Doc of a four-project RAG document pipeline. Prepare-Doc handles preprocessing, IQA, and coarse layout detection. Layer 2 metadata enrichment adds derived annotations (domain classification, content flags, layout detections, language/script, capture method, quality scores, etc.) to each document image. These annotations drive downstream training pipelines and routing decisions.

The metadata follows a three-layer architecture:

- **Layer 0**: Raw file properties (path, dimensions, format) - produced by parsers
- **Layer 1**: Dataset-level annotations (from original dataset labels) - produced by parsers
- **Layer 2**: Derived enrichment annotations (from models, LLMs, heuristics) - produced by enrichment scripts

Each sample's Layer 2 data lives under `enrichments.versions[]` in the metadata JSON, with `enrichments.current_version` pointing to the active version.

### File Locations

| Resource | Path |
|----------|------|
| Metadata JSON | `/mnt/e/image_detection/metadata_registry/json/{DATASET_NAME}_metadata.json` |
| Images | `{IMAGE_BASE_PATH}` |
| Dataset documentation | `docs/datasets/source/{DATASET_NAME}.md` |
| Audit results output | `scripts/audit/results/{DATASET_NAME}/` |
| Known issues registry | `docs/known_issues/` |
| Cross-dataset advisory | `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json` |
| Layout taxonomy config | `config/layout_taxonomy.yaml` |
| Enrichment schema | `src/image_preprocessing_detector/annotation/schemas/enrichment.py` |

### Available Enrichment Sources

Check which of these exist for this dataset (paths under `/mnt/e/image_detection/metadata_registry/`):

| Source | Typical Path | Content |
|--------|-------------|---------|
| Base metadata | `json/{DATASET_NAME}_metadata.json` | Layer 0+1 fields |
| LLM enrichment | `enrichments/{DATASET_NAME}_llm_enrichment.json` | domain, content_type, orientation, content_flags |
| Language enrichment | `enrichments/{DATASET_NAME}_language_enrichment.json` | iso639, iso15924, script_family |
| Docling layout | `enrichments/{DATASET_NAME}_docling_layout.json` | layout_detections with bboxes |
| Docling OCR | `enrichments/{DATASET_NAME}_docling_ocr.json` | text_content, text_statistics |
| Classical IQA | `enrichments/{DATASET_NAME}_classical_iqa.json` | 8 detector scores |
| Resolution quality | `results/{DATASET_NAME}_resolution_labels.json` | char_height, resolution_quality_score |
| Parser/manifest | Dataset-specific | split, source annotations |
| VLM contact sheet | `scripts/audit/results/{DATASET_NAME}/vlm_test_enrichments.json` | language, script (visual batch ID) |
| Train GT enrichment | `scripts/audit/results/{DATASET_NAME}/train_gt_enrichments.json` | language, script from GT files |

---

## Audit Methodology (8 Phases)

### Phase 0: Paper Review

1. Read `docs/datasets/source/{DATASET_NAME}.md` thoroughly. Extract:
   - Dataset origin, purpose, and composition
   - Known languages, scripts, and document types
   - Whether images are synthetic, scanned, born-digital, or camera-captured
   - Available ground truth labels (splits, classes, bounding boxes)
   - Any existing parser at `src/image_preprocessing_detector/annotation/parsers/`

2. Read the cross-dataset known issues advisory: `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json`
   - Check which known issues (KI-001 through KI-008) apply to this dataset

3. Document expected field values based on documentation (these become your ground truth for validation):
   - `capture_method`: What capture method does the documentation describe?
   - `iso639_language`: What language(s) does the dataset contain?
   - `iso15924_script`: What script(s)?
   - `split`: Are splits documented? How are they structured?
   - Is the dataset synthetic? (Critical for KI-004, KI-005)

### Phase 1: Automated Prescreening

Run the prescreening script against ALL samples:

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --dataset {DATASET_NAME}
```

This checks 13 field-level validators:

| # | Field | Rule | Valid Values |
|---|-------|------|-------------|
| 1 | `split` | Must not be "unknown" | train, val, test, dev |
| 2 | `capture_method` | Must be in enum | camera_smartphone, synthetic, scanner, born_digital, screen_capture, unknown |
| 3 | `domain_level1` | Must not be "UNK" | ADM, EDU, SCI, FIN, MED, TEC, LEG, PER, TAX |
| 4 | `iso639_language` | Must not be "und" or null | ISO 639-1/3 codes (en, ja, zh, ar, etc.) |
| 5 | `script_family` | Must be in enum | latin, cjk, arabic, indic, cyrillic, greek, hebrew, ethiopic, georgian, armenian, other |
| 6 | `layout_detections` | Must be list with >=1 element | Array of detection objects |
| 7 | `layout_bbox_valid` | All bboxes: [x,y,w,h] with w>0, h>0 | 4 valid floats |
| 8 | `content_flags_boolean` | has_table/formula/handwriting/figure/code must be boolean | true/false |
| 9 | `text_has_content` | text_statistics.has_content must be true | true |
| 10 | `orientation_class` | Must be in enum | 0, 90, 180, 270 |
| 11 | `image_properties_color_mode` | Must be non-empty string | color, grayscale, binarized |
| 12 | `handwriting_present` | Must be boolean | true/false |
| 13 | `quality_overall_mos` | Must be numeric (context-dependent) | 1.0-5.0 |

**Output**: `scripts/audit/results/{DATASET_NAME}/automated_screening.json`

Record the per-field pass/fail rates. Fields at 0% pass rate indicate missing enrichment sources.

### Phase 2: Schema Compliance

Run the full schema compliance check:

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/audit_schema_compliance.py \
    --dataset {DATASET_NAME} \
    --output scripts/audit/results/{DATASET_NAME}/compliance.json
```

This validates 27+ fields across categories:

- **Type correctness**: string, float, int, list, bool
- **Enum membership**: domain codes, capture methods, script families
- **Range validation**: confidences 0-1, MOS 1-5
- **Structural validity**: bbox format, detection object shape
- **Cross-field consistency**: layout detections vs content flags (e.g., Table detection -> has_table=true)

**Defect taxonomy** (6 types):

| Type | Definition |
|------|-----------|
| `wrong_value` | Value exists but factually incorrect |
| `missing_value` | Required field absent |
| `wrong_format` | Wrong type or structure |
| `wrong_enum` | Not in allowed enumeration |
| `inconsistent` | Cross-field contradiction |
| `not_populated` | Optional field not populated |

### Phase 3: Multi-Source Comparison

If multiple enrichment sources exist, compare field values across sources:

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/assemble_comparison.py \
    --dataset {DATASET_NAME}
```

For each field, identify:

- **Agreement**: All sources give the same value (high confidence)
- **Disagreement**: Sources conflict (investigate which is correct)
- **Single source**: Only one source populates the field (no cross-validation possible)

### Phase 4: Defect Cataloging

Based on Phases 1-3, create a defect catalog at `scripts/audit/results/{DATASET_NAME}/defect_catalog.json`.

For each defect, document:

```json
{
  "id": "D01",
  "field": "layout_detections[*].class_name",
  "defect_type": "wrong_enum",
  "status": "OPEN",
  "current": "Current values in metadata",
  "correct": "Expected correct values",
  "affected_count": 0,
  "affected_pct": 0.0,
  "root_cause": "Why this defect exists",
  "fix_category": "enrichment_fix|backfill|parser_fix|deferred",
  "fix_complexity": "low|medium|high",
  "fix_location": "Script or module where fix should be applied",
  "extrapolation_risk": "CRITICAL|HIGH|MEDIUM|LOW - Does this affect other datasets?",
  "universal_risk": true
}
```

**Assign defect IDs** as D01, D02, ... in order of severity (critical first).

### Phase 4.5: Scale Assessment & Strategy Selection (CRITICAL)

Before writing any integration script or starting VLM inspection, classify each defect by the **number of affected samples** and select the appropriate resolution strategy. This prevents context exhaustion from attempting individual image inspection on thousands of samples.

#### Strategy Tiers

| Affected Samples | Strategy | Context Cost | Example |
|------------------|----------|-------------|---------|
| **< 50** | **Individual VLM inspection**: Read each image directly with the Read tool | Low (~1-2 images/turn) | Content flag FP verification |
| **50 - 500** | **Programmatic enrichment**: Exploit GT files, parsers, or heuristic rules | Minimal (code execution) | Train GT file parsing for language labels |
| **500 - 2,000** | **Stratified sampling + extrapolation**: Inspect 30-50 representative samples, extrapolate pattern | Medium (~15-25 turns) | Domain classification verification |
| **> 2,000** | **Contact sheet batch VLM**: Generate thumbnail grids, classify in bulk | High but manageable (~1 sheet/turn) | Script identification for 9,735 test images |

#### Contact Sheet Methodology (for > 2,000 samples)

When a defect affects thousands of samples and requires visual classification (e.g., script/language identification, orientation detection, capture method verification):

1. **Generate contact sheets** using a script that creates thumbnail grid images:
   - Grid: 10 columns x 5 rows = 50 thumbnails per sheet
   - Thumbnail size: ~150x150px (enough to identify scripts/orientation, not fine text)
   - Sheet size: ~1500x750px, JPEG quality 90
   - Number each thumbnail position 1-50 for reference
   - Save as `tmp_cleanup/{DATASET_NAME}_contact_sheets/contact_sheet_NNN.jpg`
   - Generate a manifest JSON mapping each thumbnail position to its image filename/stem

2. **Process sheets in batches of 5** (250 images per turn):
   - Read 5 contact sheet images in parallel using the Read tool
   - For each sheet, output a compact code string (e.g., `la la hi ko la zh ...` for script IDs)
   - Use short codes to minimize output tokens (e.g., `la`=latin, `hi`=devanagari, `ko`=hangul, `zh`=chinese, `ja`=japanese, `ar`=arabic, `bn`=bengali, `un`=unclear)

3. **Save incrementally every 5 sheets** (CRITICAL for crash recovery):
   - After each batch of 5 sheets, run Python to map codes to enrichment records
   - Append to the output JSON file immediately
   - Track `completed` count and `sheets_processed` in the JSON header
   - If the session crashes, the next session can resume from the last saved sheet

4. **Enrichment record format** per sample:

   ```json
   {
     "script_family": "latin",
     "iso639_language": "en",
     "iso15924_script": "Latn",
     "domain_level1": "UNK",
     "domain_confidence": 0.7,
     "language_confidence": 0.75,
     "method": "vlm_contact_sheet"
   }
   ```

#### GT File Exploitation (for train splits with annotations)

Before any VLM work, check whether ground truth annotation files can resolve the defect programmatically:

1. Read a sample GT file to understand the annotation format
2. If GT files contain the needed field (e.g., language labels in MLT19's `TrainGT/*.txt`), write a script to extract and map them
3. This is **orders of magnitude cheaper** than VLM inspection and more accurate

#### Scale Assessment Output

Document the strategy for each defect in the defect catalog:

```json
{
  "id": "D07",
  "resolution_strategy": "contact_sheet_batch_vlm",
  "affected_count": 9735,
  "estimated_sheets": 195,
  "estimated_turns": 40,
  "estimated_sessions": 3,
  "incremental_save_path": "scripts/audit/results/{DATASET_NAME}/vlm_test_enrichments.json"
}
```

**IMPORTANT**: If the total estimated turns for all VLM work exceeds 50, plan for a **multi-session workflow**. Create a progress tracking file at `scripts/audit/results/{DATASET_NAME}/audit_progress.json` with:

- Current phase
- Sheets completed / total
- Samples enriched / total
- Last saved sheet number (for crash recovery)

### Phase 5: Integration Script

Create `scripts/integrate_{DATASET_NAME}_enrichments.py` following the established pattern. The script must:

1. **Load** the metadata JSON and all available enrichment sources
2. **Merge** per-sample enrichments into a new enrichment version
3. **Apply known issue mitigations** (see Known Issues Checklist below)
4. **Derive** content flags from standardized layout detections
5. **Compute** reliability summary for each sample
6. **Support** `--dry-run` mode for testing without writes

**IMPORTANT - Iterative Integration**: The integration script will likely be updated multiple times as new enrichment sources become available (e.g., VLM contact sheet results from Phase 6). Design the script with modular loader functions so new sources can be added without rewriting:

```python
# Each enrichment source gets its own loader + CLI argument:
def load_vlm_test_enrichment(path: Path) -> dict[str, dict]:
    """Load VLM contact sheet enrichments, indexed by image stem."""
    ...

# resolve_language() uses a priority chain that's easy to extend:
def resolve_language(sample, llm, lang_enrichment, vlm=None, train_gt=None):
    # 1. Parser GT (0.95) -> 2. Train GT (0.9) -> 3. VLM (0.75) -> 4. LLM (0.7) -> ...
    ...
```

Bump the enrichment version tag each time the script is updated with new sources (e.g., `integrated_v2` -> `integrated_v3`).

**Field population priority** (use this decision tree for each field):

| Field | Priority Source | Fallback | Notes |
|-------|----------------|----------|-------|
| `capture_method` | Dataset documentation | LLM enrichment | Never trust LLM for synthetic datasets (KI-005) |
| `domain_level1` | LLM enrichment | "UNK" acceptable | Accept UNK, don't force reclassification (KI-007) |
| `iso639_language` | Parser/documentation | Language enrichment | Use highest-confidence source |
| `iso15924_script` | Parser/documentation | Language enrichment | |
| `script_family` | Derived from iso15924_script | `_get_script_family()` | Automatic derivation |
| `layout_detections` | Docling/Egret layout | Parser annotations | Must run standardize_layout_labels.py first (KI-001) |
| `content_flags.*` | `derive_content_flags()` from layout + LLM merge | LLM-only | VLM-verify all True flags (KI-002,003,004,006) |
| `split` | Parser/manifest | Dataset documentation | |
| `text_scope` | LLM content_type field | "printed" default | |
| `orientation_class` | LLM enrichment | 0 (upright) default | |
| `quality_overall` | VLM IQA / Classical IQA | Deferred if unavailable | |
| `resolution_quality_score` | PaddleOCR pipeline | Deferred if no GPU | |

**Content flag derivation** from layout detections:

```python
def derive_content_flags(layout_detections: list[dict]) -> dict:
    """Derive boolean content flags from standardized layout detections."""
    classes = {d.get("class_name", "").upper() for d in layout_detections}
    return {
        "has_table": bool(classes & {"TABLE"}),
        "has_formula": bool(classes & {"FORMULA"}),
        "has_figure": bool(classes & {"PICTURE"}),
        "has_code": bool(classes & {"CODE"}),
    }
```

After integration, run prescreening again to measure improvement:

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --dataset {DATASET_NAME}
```

### Phase 6: VLM Visual Inspection

This is the most critical phase. You will visually inspect actual document images to validate metadata accuracy. **Use the strategy tier from Phase 4.5** to determine the approach for each defect.

**CONTEXT MANAGEMENT IS CRITICAL**: Each image read consumes significant context tokens. A naive approach of reading 9,000+ individual images will crash the session. Always use the appropriate strategy tier.

#### Track A: Small-Scale Inspection (< 50 failing samples per field)

For content flag verification, capture method checks, and other fields where only a small number of samples are flagged:

1. Parse the prescreening results to identify failing samples and their failing fields
2. For each failing sample, read the image using the Read tool (it supports PNG/JPG)
3. For each image, assess:

| Field | What to Look For |
|-------|-----------------|
| `capture_method` | Scan lines? Camera distortion? Clean digital rendering? Synthetic artifacts? |
| `domain_level1` | What type of document? (administrative, educational, scientific, financial, medical, technical, legal, personal, tax) |
| `iso639_language` | What language is the text in? Multiple languages? |
| `has_table` | Is there an actual table with rows/columns/grid structure? (NOT multi-column text) |
| `has_formula` | Is there a **rendered** mathematical expression? (NOT just text discussing math) |
| `has_figure` | Is there a chart, diagram, photo, or illustration? |
| `has_handwriting` | Is there actual handwritten text? (NOT printed/typed text) |
| `has_code` | Is there source code, command-line output, or code snippets? |
| `orientation_class` | Is the text upright (0), rotated 90/180/270 degrees? |
| `text_scope_content_type` | What kind of document? (letter, memo, report, form, invoice, etc.) |

1. Record corrections in `scripts/audit/results/{DATASET_NAME}/vlm_corrections.json`:

```json
{
  "dataset": "{DATASET_NAME}",
  "audited_at": "YYYY-MM-DD",
  "auditor": "claude-opus-4-6-vlm",
  "methodology": "Visual inspection of N images",
  "content_flag_corrections": {
    "has_table": {
      "original_true_count": 0,
      "corrected_true_count": 0,
      "false_positive_rate": 0.0,
      "root_cause": "Description",
      "action": "override_all_to_false|per_sample_override|no_action",
      "universal_risk": "HIGH|MEDIUM|LOW",
      "samples_inspected": [
        {"filename": "example.png", "original": true, "corrected": false, "reason": "Explanation"}
      ]
    }
  }
}
```

#### Track B: Large-Scale Contact Sheet Classification (> 2,000 samples)

For defects affecting thousands of samples (e.g., script/language identification for an entire test split), use the contact sheet methodology from Phase 4.5:

1. **Generate contact sheets** with a Python script (see Phase 4.5 for specs)
2. **Process in batches of 5 sheets** (250 images per turn), reading sheets in parallel
3. **Use compact codes** to minimize output tokens per sheet:
   - Script ID: `la hi bn ko zh ja ar un` (8 codes for common script families)
   - Orientation: `0 90 180 270`
   - Capture: `sc bd cm sy` (scanner, born-digital, camera, synthetic)
4. **Save incrementally** after every 5 sheets to guard against session crashes
5. **Resume from last save** if a new session is needed - check `sheets_processed` in the output JSON

**Contact sheet generation script template**:

```python
"""Generate contact sheets for VLM batch classification.

Usage:
    python scripts/generate_{DATASET_NAME}_contact_sheets.py \
        --image-dir {IMAGE_BASE_PATH} \
        --output-dir tmp_cleanup/{DATASET_NAME}_contact_sheets \
        --samples-json scripts/audit/results/{DATASET_NAME}/samples_to_classify.json
"""
# Key parameters:
COLS, ROWS = 10, 5          # 50 thumbnails per sheet
THUMB_SIZE = (150, 150)      # Enough for script/orientation ID
QUALITY = 90                 # JPEG quality
```

**Incremental save pattern** (run after every 5 sheets):

```python
import json
with open(enrichment_path, "r") as f:
    data = json.load(f)
# ... append new sample records ...
data["completed"] = len(data["samples"])
data["sheets_processed"] = current_sheet_number
with open(enrichment_path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

#### Track C: Validate Passing Samples (10-15 stratified samples)

1. Select 10-15 passing samples stratified across orientations, domains, and content types
2. For each, read the image and verify ALL populated fields match what you see
3. Compute accuracy rate per field
4. Record in `scripts/audit/results/{DATASET_NAME}/vlm_validation_passing.json`

**Target**: 95%+ accuracy on all fields for passing samples. If accuracy < 90% for any field, flag for systematic review.

#### Context Budget Planning

Before starting VLM work, estimate the total context cost:

| Approach | Context per Turn | Turns Needed | Risk |
|----------|-----------------|-------------|------|
| Individual images (1-2/turn) | ~50-100K tokens/image | N_samples / 2 | **HIGH** - crashes on > 100 samples |
| Contact sheets (5 sheets/turn) | ~25-50K tokens/5 sheets | N_sheets / 5 | **MEDIUM** - manageable for 200 sheets |
| Programmatic (GT files) | ~1K tokens | 1-2 | **LOW** - always prefer this |

**Rule of thumb**: A single session can handle ~40-60 contact sheet processing turns before context pressure. For datasets needing > 60 turns of VLM work, plan for continuation sessions and ensure incremental saves.

### Phase 7: Apply Corrections (Iterative)

This phase may run multiple times as new enrichment sources become available:

1. Update the integration script with VLM-determined corrections and new data sources
2. Bump the enrichment version tag (e.g., `integrated_v2` -> `integrated_v3`)
3. Run integration with `--dry-run` first, then actual write
4. Re-run prescreening to confirm improvement (`uv run python3 scripts/audit/automated_prescreening.py --dataset {DATASET_NAME}`)
5. Update the defect catalog with resolution status
6. If new defects are discovered or existing defects partially resolved, loop back to Phase 6

**Typical iteration pattern**:

- **v2 integration**: Phase 0-5 sources (parser GT, LLM, OpenLID, layout, documentation)
- **v3 integration**: + Phase 6 sources (VLM contact sheet, train GT enrichment)
- **v4 integration**: + any additional sources (resolution quality, IQA, etc.)

### Phase 8: Documentation

Update `docs/datasets/source/{DATASET_NAME}.md` with:

1. **Layer 2 Annotation Summary** section:
   - Enrichment version, data sources used
   - Field-by-field coverage percentages
   - Known issues and mitigations applied
   - VLM validation results

2. **Reliability & Bottlenecks** section:
   - Prescreening pass rates (before/after)
   - Remaining failure fields with explanations
   - Deferred items and their requirements
   - Version history

If any new cross-dataset patterns are discovered, add them to:

- `docs/known_issues/KI-{NNN}-{slug}.md` (human-readable)
- `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json` (machine-readable)

---

## Known Issues Checklist

Apply these mitigations during integration. Each has been validated across multiple datasets.

### KI-001: Layout Label Casing (CRITICAL, AUTOMATED)

**Applies to**: All datasets with Docling layout extraction
**Symptom**: `class_name` uses lowercase/snake_case instead of DocLayNet PascalCase
**Fix**: Run `standardize_layout_labels.py --dataset {DATASET_NAME}` BEFORE integration

Mapping:

| Docling Output | DocLayNet Standard |
|---------------|-------------------|
| text | Text |
| list_item | List-Item |
| section_header | Section-Header |
| page_header | Page-Header |
| page_footer | Page-Footer |
| table | Table |
| picture | Picture |
| formula | Formula |
| caption | Caption |
| footnote | Footnote |
| title | Title |

### KI-002: Table Detection on Multi-Column Text (HIGH, MANUAL)

**Applies to**: Synthetic and multi-column documents
**Symptom**: Docling flags multi-column text as `Table` (100% FP rate on JSSODa)
**Fix**: VLM-inspect all `has_table=True` samples. Override to `False` if the image shows multi-column text without actual table structure (rows, columns, grid lines, headers).
**Universal risk**: HIGH - affects all Docling-extracted multi-column documents

### KI-003: Picture Detection on Dense Text (MEDIUM, MANUAL)

**Applies to**: Synthetic datasets, documents with dark backgrounds or dense text
**Symptom**: Docling flags dense text blocks or dark-rendered text as `Picture`
**Fix**: VLM-inspect all `has_figure=True` samples. Override to `False` if no actual chart/diagram/photo/illustration is visible.

### KI-004: LLM Handwriting on Synthetic (HIGH, PATTERN)

**Applies to**: All synthetic datasets
**Symptom**: LLM flags typed/rendered text as `has_handwriting=True` (100% FP on JSSODa)
**Fix**: For **known synthetic** datasets, override `has_handwriting=False` for ALL samples.
For mixed datasets, VLM-inspect each `has_handwriting=True` sample.

```python
# KI-004: Override for synthetic datasets
if is_synthetic_dataset:
    data["has_handwriting"] = False
    data["handwriting_present"] = False
```

### KI-005: LLM Cannot Detect Synthetic Capture Method (HIGH, PATTERN)

**Applies to**: All synthetic datasets
**Symptom**: LLM classifies synthetic images as `born_digital` or `scanner_flatbed` (0% accuracy)
**Fix**: For **known synthetic** datasets, hardcode `capture_method="synthetic"` with confidence 1.0 from dataset documentation. Do NOT use LLM value.

```python
# KI-005: Override for synthetic datasets
if is_synthetic_dataset:
    data["capture_method"] = "synthetic"
    data["capture_method_confidence"] = 1.0
    data["capture_method_source"] = "dataset_documentation"
```

**Known synthetic datasets**: jssoda, synth-multiscript-250k, docsynth300k

### KI-006: LLM Formula Semantic Confusion (MEDIUM, MANUAL)

**Applies to**: All datasets with LLM enrichment, especially scientific/educational content
**Symptom**: LLM flags text that *discusses* chemistry/math as `has_formula=True` even without rendered expressions (67% FP on JSSODa)
**Fix**: VLM-inspect all `has_formula=True` samples. A true positive requires a **visually rendered** mathematical expression (equations, subscripts, superscripts, mathematical notation), not just text mentioning formulas.

```python
# KI-006: VLM-verified formula true positives
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset({
    # "sample_id",  # description of visible formula
})
data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
```

### KI-007: LLM Domain UNK on Generic Content (LOW, ACCEPTED)

**Applies to**: Datasets with generic, narrative, literary, or creative text
**Symptom**: High `domain_level1=UNK` rate (34.7% on JSSODa)
**Fix**: Accept UNK as valid. The domain taxonomy (ADM, EDU, SCI, FIN, MED, TEC, LEG, PER, TAX) does not cover literary/narrative content. Do NOT force reclassification.

### KI-008: Docling Multi-Column Text Extraction (HIGH, OPEN)

**Applies to**: All multi-column documents processed through Docling OCR
**Symptom**: When Docling misclassifies multi-column text as `Table`, the downstream text extraction produces garbled output (wrong reading order). This is a Unify (OCR) concern documented here because the root cause is in layout detection.
**Fix**: No automated fix yet. Document as a known limitation. Proposed fixes are tracked in `docs/known_issues/KI-008-docling-multicolumn-text-extraction.md`.

---

## Layer 2 Enrichment Fields Reference

The complete field inventory for each sample's enrichment data:

### Capture & Resolution

| Field | Type | Values | Source |
|-------|------|--------|--------|
| `capture_method` | string | camera_smartphone, synthetic, scanner, born_digital, screen_capture | LLM or documentation |
| `capture_confidence` | float | 0.0-1.0 | Enrichment source |
| `resolution_dpi` | int | 72-600 | Image analysis |
| `resolution_category` | string | low, medium, standard, high | Derived from DPI |
| `resolution_pixels` | tuple | (width, height) | Image dimensions |
| `resolution_quality_score` | float | 0.0-1.0 | PaddleOCR char-height pipeline |
| `character_height_px` | float | Pixels | PaddleOCR detection |

### Domain & Language

| Field | Type | Values | Source |
|-------|------|--------|--------|
| `domain_level1` | string | ADM, EDU, SCI, FIN, MED, TEC, LEG, PER, TAX, UNK | LLM enrichment |
| `domain_confidence` | float | 0.0-1.0 | LLM enrichment |
| `iso639_language` | string | ISO 639-1/3 code | Parser/language enrichment |
| `iso15924_script` | string | ISO 15924 code (Latn, Jpan, Arab, etc.) | Parser/language enrichment |
| `script_family` | string | latin, cjk, arabic, indic, cyrillic, etc. | Derived from script |

### Content Flags (with confidence companions)

| Field | Type | Values | Source |
|-------|------|--------|--------|
| `has_table` | bool | true/false | Layout detections + VLM verification |
| `has_formula` | bool | true/false | Layout detections + VLM verification |
| `has_handwriting` | bool | true/false | LLM + VLM verification |
| `has_signature` | bool | true/false | LLM |
| `has_figure` | bool | true/false | Layout detections + VLM verification |
| `has_code` | bool | true/false | LLM or layout |
| `content_flags_tier` | string | tier_2_model | Enrichment tier |
| `content_flags_source` | string | docling_gpu+llm_vision | Pipeline used |

### Layout Detections

| Field | Type | Values | Source |
|-------|------|--------|--------|
| `layout_detections[].class_name` | string | DocLayNet 11-class PascalCase | Docling/Egret |
| `layout_detections[].bbox` | list[float] | [x, y, width, height] COCO format | Detection model |
| `layout_detections[].confidence` | float | 0.0-1.0 | Detection model |
| `layout_detections[].source` | string | Model identifier | |
| `layout_detections[].canonical_class` | string | UPPERCASE canonical | Taxonomy mapping |
| `layout_detections[].source_schema` | string | doclaynet, docling, etc. | Taxonomy mapping |
| `layout_detections[].source_label` | string | Original label before conversion | Taxonomy mapping |

DocLayNet 11 classes: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title

### Geometric & Quality

| Field | Type | Values | Source |
|-------|------|--------|--------|
| `orientation_class` | int | 0, 90, 180, 270 | LLM or detection model |
| `skew_angle_degrees` | float | -180 to 180 | Detection model |
| `quality_overall` | float | 0.0-1.0 | IQA pipeline |
| `ml_iqa_blur` | float | 0.0-1.0 | ML IQA model |
| `ml_iqa_noise` | float | 0.0-1.0 | ML IQA model |
| `color_mode` | string | color, grayscale, binarized | Image analysis |
| `document_age` | string | modern, aged, historical | Augmentation or detection |

### Text & Document

| Field | Type | Values | Source |
|-------|------|--------|--------|
| `text_scope` | string | printed, handwritten, mixed | Detection |
| `text_scope_content_type` | string | letter, memo, report, form, etc. | LLM enrichment |
| `split` | string | train, val, test | Parser/manifest |
| `dataset_short_code` | string | Dataset identifier | Configuration |

---

## Output Artifacts Checklist

A complete audit produces these artifacts:

| File | Purpose | When Created |
|------|---------|-------------|
| `scripts/audit/results/{DATASET_NAME}/automated_screening.json` | Per-field pass/fail counts | Phase 1 |
| `scripts/audit/results/{DATASET_NAME}/compliance.json` | Schema validation per field | Phase 2 |
| `scripts/audit/results/{DATASET_NAME}/comparison_report.json` | Multi-source field comparison | Phase 3 |
| `scripts/audit/results/{DATASET_NAME}/defect_catalog.json` | Categorized defects with status | Phase 4 |
| `scripts/integrate_{DATASET_NAME}_enrichments.py` | Integration script | Phase 5 |
| `scripts/audit/results/{DATASET_NAME}/vlm_corrections.json` | VLM visual inspection corrections | Phase 6 |
| `scripts/audit/results/{DATASET_NAME}/vlm_validation_passing.json` | Passing sample accuracy check | Phase 6 |
| `docs/datasets/source/{DATASET_NAME}.md` (UPDATED) | Documentation with L2 summary | Phase 8 |

### Defect Catalog JSON Schema

```json
{
  "dataset": "{DATASET_NAME}",
  "audited_at": "YYYY-MM-DD",
  "schema_version": "layer2_enrichment_v2 (v2.1.0)",
  "total_samples": 0,
  "prescreening_pass_rate_pct": 0.0,
  "post_fix_prescreening": {
    "fields_passing_100_pct": 0,
    "fields_total": 13,
    "remaining_failures": {}
  },
  "vlm_validation": {
    "total_images_inspected": 0,
    "failing_samples_inspected": 0,
    "passing_samples_inspected": 0,
    "passing_sample_accuracy": 0.0,
    "content_flag_corrections": 0
  },
  "total_defects": 0,
  "defects": [],
  "summary": {
    "total_defects": 0,
    "resolved": 0,
    "partially_resolved": 0,
    "deferred": 0,
    "resolution_breakdown": {},
    "prescreening_improvement": {
      "before": "0/13 fields at 100%",
      "after": "0/13 fields at 100%",
      "remaining_failures": []
    },
    "cross_dataset_findings": []
  }
}
```

---

## Success Criteria

| Metric | Target | Minimum Acceptable |
|--------|--------|-------------------|
| Prescreening pass rate | 95%+ | 85% |
| Fields at 100% coverage | 10+/13 | 8/13 |
| VLM passing sample accuracy | 95%+ | 90% |
| Defects resolved | 80%+ | 60% |
| Content flag false positive rate | <5% | <15% |
| Cross-dataset findings documented | All | All critical/high |

---

## Working Notes

### Data & Integration

- **Layout standardization MUST run before integration** (KI-001). Run `standardize_layout_labels.py --dataset {DATASET_NAME}` first.
- **ID matching**: LLM enrichment typically uses `image_id` (no extension), metadata uses `original_filename` (with extension). Match via `Path(original_filename).stem`.
- **Enrichment versions**: Always create a NEW version (don't overwrite). Set `enrichments.current_version` to the new version number.
- **Dry-run first**: Always run integration with `--dry-run` before writing.
- **Deferred items**: It is acceptable to defer quality_overall and resolution_quality if the required pipelines (VLM IQA, PaddleOCR GPU) are not available in the current session.

### Context Management (CRITICAL)

- **Never read individual images at scale**: Reading even 100 full-resolution images will consume most of a session's context. Use contact sheets for any visual classification task involving > 50 images.
- **Contact sheet batch size**: Process 5 sheets per turn (250 thumbnails). This balances throughput against context pressure. Reading more than 5 sheets per turn risks output truncation.
- **Incremental saves every 5 sheets**: The single most important crash recovery mechanism. If the session dies at sheet 150/195, the next session resumes from sheet 150 instead of starting over.
- **Compact output codes**: Use 2-letter codes (`la`, `hi`, `ko`, `zh`, `ja`, `ar`, `bn`, `un`) instead of full script names. For 50 thumbnails per sheet, this reduces output from ~500 tokens to ~100 tokens per sheet.
- **Manifest file**: Always generate a manifest JSON mapping sheet numbers to image filenames. This enables automated mapping from VLM codes back to sample records without re-reading sheets.
- **Multi-session planning**: For datasets with > 5,000 samples needing VLM work, plan for 2-4 sessions. Document progress in `audit_progress.json` and the enrichment output file's header fields (`completed`, `sheets_processed`).

### GT File Exploitation (Check Before VLM)

- **Always check for ground truth annotation files first**. Many datasets have annotation files (`.txt`, `.xml`, `.json`) that contain the exact fields needed (language, script, bounding boxes). Parsing these programmatically is 100x cheaper than VLM inspection.
- **Example**: MLT19's `TrainGT/*.txt` files contain per-word language labels. Reading one file reveals the format; a 10-line script resolves 134 samples instantly.
- **Even partial GT coverage helps**: If GT covers the train split but not test, resolve train programmatically and reserve VLM effort for the test split only.

## END PROMPT
