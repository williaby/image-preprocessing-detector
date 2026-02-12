# Layer 2 Metadata Enrichment Audit Framework

> **Status**: Active
> **Schema**: `layer2_enrichment_v2.schema.json` (v2.3.0)
> **Scope**: All ~51 datasets in the Project A metadata registry

## Purpose

Validate the quality and correctness of Layer 2 metadata enrichment for any
dataset. The framework is dataset-agnostic: it reads the same JSON structure
produced by `annotate_base_metadata.py` and applies a uniform set of checks
against the v2.3.0 schema.

The audit answers three questions:

1. **Coverage** -- What percentage of samples have each field populated?
2. **Validity** -- Are populated values type-correct, within enum sets, and
   structurally sound?
3. **Consistency** -- Do cross-field relationships hold (e.g. layout
   detections agree with content flags)?

## Audit Methodology

### Step 1: Paper Review

Read the dataset source documentation (`docs/datasets/source/{name}.md`) and
the dataset's enrichment provenance to understand expected field values.
Identify fields that should be tier_0_exact vs tier_2_model.

### Step 2: Sample Selection

Use stratified sampling across 2-4 axes (configurable per dataset in
`audit_config.py`). Default sample size is 36, balancing statistical coverage
with manual inspection effort. Axes are chosen from:

- `capture_method` -- born_digital / scanner / camera / synthetic
- `domain_level1` -- TAX / FIN / SCI / EDU / etc.
- `resolution_category` -- low / medium / standard / high
- `quality_overall` -- quality score quartiles
- `layout_type` -- single_column / multi_column / complex / etc.
- `text_density` -- sparse / moderate / dense
- `script_family` -- latin / cjk / arabic / indic / cyrillic
- `has_table` / `has_handwriting` -- boolean content flags

### Step 3: Automated Schema Compliance

Run `audit_schema_compliance.py` against the full dataset:

```bash
# Using a known dataset shortcut:
python scripts/audit/audit_schema_compliance.py \
    --dataset diqa-5000 \
    --output scripts/audit/results/diqa-5000/compliance.json

# Using explicit paths:
python scripts/audit/audit_schema_compliance.py \
    --metadata-path /mnt/e/.../diqa_5000_metadata.json \
    --schema-path docs/schema/layer2_enrichment_v2.schema.json \
    --output scripts/audit/results/diqa-5000/compliance.json
```

This produces per-field coverage, validity percentages, and a per-sample
pass/fail breakdown in structured JSON.

### Step 4: Visual Inspection (Manual)

For each of the 36 stratified samples:

1. Open the source image.
2. Compare every enrichment field against what you see in the image.
3. Record defects using the taxonomy below.

### Step 5: Multi-Source Comparison

If the dataset has multiple enrichment sources (base metadata, LLM
enrichment, language enrichment, Docling layout), compare values across
sources for the audit samples. Record agreements and disagreements in the
Source Comparison Matrix.

### Step 6: Report Generation

Copy `audit_report_template.md` and fill in all placeholder fields. Attach
the JSON compliance report as an appendix.

## Scoring Rubric

### Per-Field Validation

Each field is scored on three dimensions:

| Dimension | Definition | Scoring |
|-----------|-----------|---------|
| **Coverage** | % of samples where the field is populated (non-null, non-missing) | 100% = full, <90% = gap |
| **Validity** | % of populated values that pass type/enum/range checks | 100% = clean, <95% = issue |
| **Accuracy** | % of populated values that match ground truth (manual check on audit sample) | 100% = perfect, <90% = investigate |

### Overall Dataset Score

```
dataset_score = (coverage_weight * avg_coverage
                 + validity_weight * avg_validity
                 + accuracy_weight * sample_accuracy)

Default weights: coverage=0.3, validity=0.3, accuracy=0.4
```

A dataset passes audit if:

- Overall score >= 85%
- No critical defects (wrong_value on required fields) remain unresolved
- All consistency checks pass on >= 95% of samples

## Field-by-Field Checklist

Checked against `layer2_enrichment_v2.schema.json` v2.3.0:

### Root Fields

| Field | Required | Type | Validation |
|-------|----------|------|-----------|
| `sample_id` | Yes | string (UUID) | Format: UUID v4 |
| `enrichment_version` | Yes | integer >= 1 | Must increment |
| `schema_version` | No | const "2.3.0" | Exact match |
| `created_at` | Yes | string (ISO 8601) | Valid datetime |
| `created_by` | Yes | string (minLength 1) | Non-empty |
| `method` | Yes | enum | tier_0_exact, tier_1_annotation, tier_2_model, tier_3_heuristic |

### EnrichmentData Fields

| Field | Type | Key Validations |
|-------|------|----------------|
| `capture_method` | CaptureMethodInfo | `.method` enum: born_digital, scanner_flatbed, scanner_adf, camera_professional, camera_smartphone, fax, synthetic, unknown |
| `resolution` | ResolutionInfo | `.category` enum; `.pixels` = [w,h] positive ints; `.dpi` int >= 1; `.confidence` 0-1; `.character_height_rendered_px` number\|null (v2.3.0); `.output_size_px` int\|null (v2.3.0) |
| `domain` | DomainInfo | `.level1` enum: TAX, LEG, FIN, TEC, SCI, ADM, MED, EDU, PER, UNK |
| `structure` | StructureInfo | `.layout_type` enum; `.text_density` enum; `.text_directions_present` array of ltr/rtl/ttb\|null (v2.3.0) |
| `quality` | QualityInfo | `.overall_score` 0-1; `.degradations[].severity_numeric` 0-1 |
| `language` | LanguageInfo | `.language_code` 2-3 chars; `.script_code` 4 chars ISO 15924; `.text_direction` enum ltr/rtl/ttb\|null (v2.3.0) |
| `languages` | LanguageInfo[] | Same as `language`; one entry has `is_primary=true` |
| `text_scope` | TextScopeInfo | `.scope` enum; `.content_type` enum |
| `paper_size` | PaperSizeInfo | `.detected_size` enum; `.orientation` enum |
| `content_flags` | ContentFlags | Boolean flags + companion `_confidence` floats 0-1 |
| `llm_scores` | LLMScores | `.predicted_mos` 1-5; `.predicted_normalized` 0-1 |
| `layout_detections` | LayoutDetection[] | `.class_name` DocLayNet 11-class; `.bbox` COCO [x,y,w,h]; `.confidence` 0-1 |
| `layout_detections_metadata` | LayoutDetectionMetadata | `.detection_method` string; `.provenance_tier` enum |
| `handwriting_assessment` | HandwritingAssessment | `.presence` enum; `.legibility` enum |
| `text_content` | TextContent | `.full_text` string required; `.source_type` enum |
| `text_statistics` | TextStatistics | `.character_count` int >= 0; `.word_count` int >= 0 |
| `sample_reliability_summary` | SampleReliabilitySummary | `.min_confidence_category` enum; `.assessed_field_count` int >= 0 |
| `geometric` | GeometricInfo | `.orientation_class` enum [0,90,180,270]; `.skew_angle_degrees` -180 to 180 |
| `physical_degradation` | PhysicalDegradationInfo | severity scores 0-1; type enums |
| `ml_image_quality` | MLImageQualityInfo | 6 dimension scores 0-1 |
| `image_properties` | ImagePropertiesInfo | `.color_mode` enum; `.document_age` enum |
| `ocr_impact` | OCRImpactInfo | CER/WER 0-1; `.routing_outcome` enum |

### Label Reliability Mixin (on all Info objects)

| Field | Type | Validation |
|-------|------|-----------|
| `confidence` | number or null | 0-1 float; null = unassessed |
| `provenance_tier` | enum | tier_0_exact, tier_1_annotation, tier_2_model, tier_3_heuristic |
| `is_soft_label` | boolean | true = inferred, false = ground truth |
| `detection_method` | string | Free text describing detection approach |

### COCO Bounding Box Format

All bounding boxes must be COCO format: `[x, y, width, height]` where:

- `(x, y)` is the top-left corner
- All four values are non-negative numbers
- Width and height must be > 0 for valid detections

### Consistency Rules

| Rule | Check | Severity |
|------|-------|----------|
| Layout-flag agreement | If layout_detections has "Table", content_flags.has_table must not be false | Medium |
| Layout-flag agreement | If layout_detections has "Formula", content_flags.has_formula must not be false | Medium |
| Layout-flag agreement | If layout_detections has "Picture", content_flags.has_figure must not be false | Medium |
| Confidence range | All confidence values must be null or in [0, 1] | High |
| Provenance tier match | Field provenance_tier should be consistent with detection_method | Low |

## Defect Classification Taxonomy

| Code | Description | Severity | Example |
|------|-------------|----------|---------|
| `wrong_value` | Value exists but is factually incorrect | Critical | capture_method="born_digital" for a scanned document |
| `missing_value` | Required field is absent (null or missing key) | Critical | layout_detections[0].bbox is null |
| `wrong_format` | Value present but wrong type or structure | High | confidence="0.9" (string instead of float) |
| `wrong_enum` | Value not in the allowed enumeration | High | domain_level1="FINANCE" instead of "FIN" |
| `inconsistent` | Cross-field contradiction | Medium | layout has "Table" detection but has_table=false |
| `not_populated` | Optional field not populated (coverage gap) | Low | llm_scores is null (feature not yet run) |

## Output Formats

### 1. JSON Compliance Report

Produced by `audit_schema_compliance.py`. Structure:

```json
{
  "dataset_name": "diqa-5000",
  "schema_version": "1",
  "total_samples": 5500,
  "valid_samples": 5100,
  "validity_pct": 92.73,
  "audited_at": "2026-02-10T...",
  "field_summary": {
    "capture_method": {
      "field_path": "capture_method",
      "populated_count": 5500,
      "valid_count": 5500,
      "total_samples": 5500,
      "coverage_pct": 100.0,
      "validity_pct": 100.0,
      "defect_count": 0,
      "defect_type_counts": {}
    }
  },
  "consistency_defects": [],
  "sample_results": [
    {
      "sample_id": "abc-123",
      "is_valid": true,
      "defect_count": 0,
      "defects": []
    }
  ]
}
```

### 2. Markdown Audit Report

Human-readable report filled from `audit_report_template.md`. Includes
executive summary, defect catalog, source comparison matrix, per-field
analysis, and fix recommendations.

### 3. Console Summary

Quick terminal output showing field coverage/validity table and defect
counts. Produced by default when running the CLI.

## Directory Structure

```text
scripts/audit/
    __init__.py                       # Package marker
    README.md                         # This file
    audit_config.py                   # Dataset-specific configuration
    audit_schema_compliance.py        # Automated schema compliance checker
    automated_prescreening.py         # Lightweight field validation
    select_audit_samples.py           # Generic stratified sample selection
    assemble_comparison.py            # Generic multi-source field comparison
    audit_report_template.md          # Markdown report template
    select_diqa_audit_samples.py      # DIQA-specific sample selection (reference)
    assemble_diqa_comparison.py       # DIQA-specific comparison (reference)
    results/                          # Per-dataset audit output
        {dataset-name}/
            automated_screening.json  # Prescreening pass/fail
            compliance.json           # Schema compliance JSON
            sample_set.json           # Stratified audit samples
            comparison_report.json    # Multi-source comparison
            defect_catalog.json       # Defect catalog with taxonomy
            audit_report.md           # Filled report
```

## Adding a New Dataset

1. Add an entry to `_KNOWN_CONFIGS` in `audit_config.py` with the dataset's
   metadata path, image path, and stratification axes.
2. Run the automated compliance check:

   ```bash
   python scripts/audit/audit_schema_compliance.py --dataset {name} \
       --output scripts/audit/results/{name}/compliance.json
   ```

3. Copy `audit_report_template.md` to `results/{name}/audit_report.md`.
4. Fill in the template using compliance JSON output and manual inspection.

## Cross-Dataset Defect Tracking

### Defect Catalog (`defect_catalog.json`)

Each dataset audit produces a defect catalog with this schema:

```json
{
  "dataset": "diqa-5000",
  "audit_version": "v4",
  "audited_at": "2026-02-10T...",
  "defects": [
    {
      "id": "DIQA-001",
      "field": "physical_degradation_types",
      "defect_type": "wrong_value",
      "severity": "critical",
      "description": "All 5 types assigned to every ori/ image (should be 1 per image)",
      "affected_samples": 500,
      "affected_pct": 9.1,
      "status": "fixed",
      "fix_version": "integrated_v4",
      "extrapolates_to": []
    }
  ],
  "summary": {
    "total_defects": 5,
    "by_severity": {"critical": 2, "high": 1, "medium": 1, "low": 1},
    "by_status": {"fixed": 4, "accepted": 1}
  }
}
```

### Cross-Dataset Extrapolation Patterns

Defects found during one dataset's audit often indicate systemic issues
affecting other datasets processed through the same pipeline. Track these
with the `extrapolates_to` field.

Known cross-dataset defects from the DIQA-5000 audit:

| Defect | Root Cause | Affected Datasets |
|--------|-----------|-------------------|
| Wrong script_family for Greek, Hebrew, Ethiopic, Georgian, Armenian scripts | Divergent local mappings in `annotate_base_metadata.py` | All ~46 datasets with non-Latin/CJK/Arabic/Indic/Cyrillic text |
| VALID_SCRIPT_FAMILIES too restrictive (6 values) | Prescreening validator not updated for expanded families | All datasets audited before fix |
| Paper size confidence too high for camera captures | `estimate_paper_size()` assumed 300 DPI for all captures | Any dataset with `camera_smartphone` capture method |

### DIQA-Specific Defects (Not Extrapolating)

| Defect | Root Cause | Why DIQA-Only |
|--------|-----------|---------------|
| All 5 distortion types assigned to ori/ | DIQA integration script over-assigned | Custom integration script |
| MOS scores leaked from res/ to ori/ | MOS fallback in `load_mos_scores()` | DIQA-specific MOS handling |

## Automated Prescreening

The `automated_prescreening.py` tool runs lightweight validation checks
on any dataset's Layer 2 metadata. It is faster than full schema compliance
and catches common issues early.

### Single Dataset

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --dataset diqa-5000
```

Output: `scripts/audit/results/diqa-5000/automated_screening.json`

### All Datasets

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --all-datasets
```

Output:

- Per-dataset: `scripts/audit/results/{dataset}/automated_screening.json`
- Summary: `scripts/audit/results/cross_dataset_summary.json`

The cross-dataset summary includes per-dataset pass rates and the most
common failure patterns across all datasets.

## Dataset Audit Priority Order

After completing the DIQA-5000 deep audit, prioritize remaining datasets
based on training importance, sample count, and known risk factors:

### Tier 1: High Priority (Training-Critical)

| Dataset | Samples | Training Purpose | Risk Factors |
|---------|---------|-----------------|--------------|
| ohr-bench | 8,500 | IQA teacher training | Foundation model data |
| doclaynet | 81,000 | Layout detection | Large, high-impact |
| synth-multiscript-250k | 250,000 | Script detection | Synthetic, new pipeline |

### Tier 2: Medium Priority (Validation/Calibration)

| Dataset | Samples | Training Purpose | Risk Factors |
|---------|---------|-----------------|--------------|
| pubtabnet | 568,000 | Table detection | Very large, scientific domain |
| tablebank | 278,000 | Table detection | Multiple sources |
| realdae | 1,200 | IQA benchmark | Camera captures, small |

### Tier 3: Lower Priority (Supplementary)

| Dataset | Samples | Training Purpose | Risk Factors |
|---------|---------|-----------------|--------------|
| mdiw13 | 290,000 | Multi-script | Legacy format |
| mlt19 | 20,000 | Text detection | Multi-language |
| fintabnet | 97,000 | Table detection | Financial domain |

### Audit Workflow for Each Dataset

1. **Run prescreening**: `--dataset {name}` to get quick pass/fail rates
2. **Review paper/docs**: Read `docs/datasets/source/{name}.md` for expected values
3. **Run schema compliance**: Full validation against v2.3.0 schema
4. **Stratified sample**: Select 36 samples across relevant axes
5. **Visual inspection**: Compare metadata against actual images
6. **Multi-source comparison**: If multiple enrichment sources exist
7. **Defect catalog**: Record findings with severity and extrapolation notes
8. **Pipeline fixes**: Apply corrections to integration scripts
9. **Re-run & validate**: Re-integrate, re-aggregate, re-screen

## Generic Stratified Sample Selection

The `select_audit_samples.py` script selects representative audit samples
using stratified sampling across configured axes. It replaces dataset-specific
sample selection scripts with a single dataset-agnostic tool.

### Usage

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/select_audit_samples.py --dataset diqa-5000

# Dry-run mode (preview selection without writing files)
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/select_audit_samples.py \
    --dataset diqa-5000 --dry-run

# Override sample size and seed
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/select_audit_samples.py \
    --dataset ohr-bench --sample-size 48 --seed 12345

# Custom output path
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/select_audit_samples.py \
    --dataset doclaynet --output /tmp/doclaynet_samples.json
```

Output: `scripts/audit/results/{dataset}/sample_set.json`

### Features

- **Dynamic sample sizing**: N<200 audit all, 200-10K use 36, N>=10K use ceil(sqrt(N))
- **Proportional allocation**: Largest-remainder method across strata
- **Config-driven axes**: Reads stratification axes from `audit_config.py`
- **Reproducible**: Fixed random seed for deterministic selection
- **Boolean axis handling**: Converts `has_table`/`has_handwriting` to `true`/`false` strings
- **Quality bucketing**: Maps continuous `quality_overall` scores to low/medium/high tiers

## Generic Multi-Source Comparison

The `assemble_comparison.py` script auto-discovers enrichment sources and
compares field values across all available sources for audit samples. Replaces
dataset-specific comparison scripts.

### Usage

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/assemble_comparison.py --dataset diqa-5000

# Dry-run mode (discover sources but don't write output)
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/assemble_comparison.py \
    --dataset diqa-5000 --dry-run

# Override comparison fields
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/assemble_comparison.py \
    --dataset ohr-bench \
    --fields capture_method domain_level1 resolution_category

# Custom output path
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/assemble_comparison.py \
    --dataset doclaynet --output /tmp/doclaynet_comparison.json
```

Output: `scripts/audit/results/{dataset}/comparison_report.json`

### Auto-Discovered Sources

The script automatically discovers and loads these source types:

| Source | Location | Loaded When |
|--------|----------|-------------|
| L2 metadata | `{METADATA_ROOT}/{dataset}_metadata.json` | Always (required) |
| LLM enrichment | `{METADATA_ROOT}/{dataset}_llm_enrichment.json` | File exists |
| Language enrichment | `{METADATA_ROOT}/{dataset}_language_enrichment.json` | File exists |
| Docling layout | `metadata_registry/extracted/{dataset}/` | Directory exists |
| Egret layout | `annotations/{dataset}/layout/` | Directory exists |
| Resolution quality | `results/{dataset}_resolution_labels.json` | File exists |
| Visual ground truth | `results/{dataset}/sample_set.json` (visual_gt) | File exists |

### Default Comparison Fields

```text
capture_method, capture_confidence, domain_level1, domain_confidence,
resolution_category, iso639_language, iso15924_script, script_family,
has_table, has_handwriting, has_formula, has_figure, quality_overall
```

Override with `--fields field1 field2 ...`.

## Layer 2 Audit Agent

For fully automated deep audits, use the Layer 2 Audit Agent:

**Agent definition**: `.claude/agents/layer2-audit-agent.md`

### Invocation

```text
Run Layer 2 audit on ohr-bench (source_doc: docs/datasets/source/ohr-bench.md)
```

### Scope Options

| Scope | Phases | Duration |
|-------|--------|----------|
| `prescreening_only` | 0-2 | ~5 min |
| `compliance_only` | 0-3 | ~10 min |
| `full` (default) | 0-7 | ~30-60 min |
| `full` + `fix_defects=true` | 0-9 | Variable |

### Agent Workflow Summary

1. **Phase 0**: Pre-flight (registry check, metadata exists, schema version)
2. **Phase 1**: Paper review (extract expected values from source doc)
3. **Phase 2**: Automated prescreening (`automated_prescreening.py`)
4. **Phase 3**: Schema compliance + referential integrity checks
5. **Phase 4**: Field completeness analysis (streaming for >500MB files)
6. **Phase 5**: Stratified sample selection (`select_audit_samples.py`)
7. **Phase 6**: Multi-source comparison (`assemble_comparison.py`)
8. **Phase 7**: Defect catalog with 12-type expanded taxonomy + audit report
9. **Phase 8**: Logic fixes (approval required, tiered remediation)
10. **Phase 9**: Data gap backfills (approval required, follows `integrate_resolution_quality.py` pattern)

See `.claude/agents/layer2-audit-agent.md` for full workflow details, error
handling matrix, and quality scoring rubric.

## Quick Reference: CLI Commands

```bash
# List available datasets
python scripts/audit/audit_schema_compliance.py --list-datasets

# Run compliance audit with console summary
python scripts/audit/audit_schema_compliance.py --dataset diqa-5000

# Run with JSON output
python scripts/audit/audit_schema_compliance.py \
    --dataset diqa-5000 \
    --output scripts/audit/results/diqa-5000/compliance.json

# Run on arbitrary metadata file
python scripts/audit/audit_schema_compliance.py \
    --metadata-path /path/to/metadata.json \
    --output /path/to/report.json

# Run prescreening on single dataset
python scripts/audit/automated_prescreening.py --dataset diqa-5000

# Run prescreening on all datasets
python scripts/audit/automated_prescreening.py --all-datasets

# Run generic sample selection
python scripts/audit/select_audit_samples.py --dataset diqa-5000

# Run generic multi-source comparison
python scripts/audit/assemble_comparison.py --dataset diqa-5000

# Verbose mode for debugging
python scripts/audit/audit_schema_compliance.py \
    --dataset diqa-5000 --verbose
```
