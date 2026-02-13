# Layer 2 Metadata Audit System

> **Version**: 1.3.0
> **Last Updated**: 2026-02-12
> **Status**: Active

## Overview

This directory contains the templates, configuration, and tooling for conducting Layer 2 metadata enrichment audits
across all 51 datasets. The audit system uses a 9-phase methodology to validate coverage, accuracy, and consistency
of derived annotations including capture method, domain classification, script family, layout detections, quality
issues, degradation patterns, and content flags.

**The goal of every audit is not just to identify errors and gaps, but to close them so that the dataset is ready
for use in training.** Each phase produces actionable remediation -- integration scripts fix defects, VLM inspection
corrects content flags, and catalog updates ensure documentation reflects the true state of the data. An audit is
not complete until defects are resolved and the dataset meets acceptance criteria for production training.

## Workflow Overview

The audit follows a 9-phase sequential methodology with automated tooling support:

```text
Phase 0: Paper Review
  └─> Document expected values from source paper/README
  └─> Fill paper_review.md template with baseline expectations

Phase 1: Automated Prescreening
  └─> Run automated_prescreening.py → 15-field validation
  └─> Generates automated_screening.json with pass/fail rates

Phase 2: Schema Compliance Check
  └─> Run audit_schema_compliance.py → Validate field types/ranges
  └─> Generates schema_compliance.json with 15 field validations

Phase 3: Multi-Source Comparison
  └─> Run assemble_comparison.py → Compare enrichment sources
  └─> Generates comparison_report.json with cross-source agreement

Phase 4: Defect Catalog
  └─> Manual review of Phase 1-3 artifacts → Identify defect patterns
  └─> Create defect_catalog.json with prioritized issues

Phase 4.5: Defect Sizing
  └─> Run select_audit_samples.py → Stratified random sample
  └─> Generates sample_set.json with 36-100 images for VLM review

Phase 5: Integration Script Development
  └─> Copy integration_script_template.py → Customize per dataset
  └─> Implement mitigation logic for known issues (KI-001 to KI-008)
  └─> Test on sample set, validate outputs

Phase 6: VLM Visual Inspection (Adaptive Sampling)
  └─> Select sampling tier (1/2/3) based on Phase 1-4 quality signals
  └─> Run VLM agent on sample_set.json → Validate 15 fields visually
  └─> Expand inspection for flags with high FP rates
  └─> Generates vlm_validation.json with agreement rates per field

Phase 6.5: VLM Text Labeling (Conditional)
  └─> Trigger: text_has_content pass rate < 50% in Phase 1 prescreening
  └─> Target: max(ceil(1% of dataset), 10) samples at >75% confidence
  └─> Transcribe text via VLM vision → text_content, text_statistics
  └─> Generates vlm_text_labels.json → re-integrate in Phase 7

Phase 7: Corrections & Iteration
  └─> Fix defects identified in Phase 4-6
  └─> Re-integrate with all enrichment sources (including text labels)
  └─> Re-run Phases 1-6 until targets met (90% coverage, <5% defects)

Phase 8: Documentation & Tracking
  └─> Fill AUDIT_REPORT_TEMPLATE.md with final results
  └─> Update docs/datasets/source/{dataset}.md with audit metadata
  └─> Update docs/datasets/AUDIT_TRACKING_INDEX.md with status

Post-Audit: Quality Scorecard
  └─> Run compute_scorecard.py → Generate final grade (A/B/C/D/F)
  └─> Update AUDIT_TRACKING_INDEX.md with scorecard results

Phase 9: Dataset Catalog Update
  └─> Run aggregate_layer2_metadata.py → Regenerate dataset statistics
  └─> Run materialize_reliability_summary.py → Update reliability section
  └─> Update docs/datasets/source/{dataset}.md Section 11 (Audit Summary)
  └─> Run dataset-catalog-agent for gap analysis + cross-file sync

Phase 10: Lessons Learned & Process Improvement
  └─> Review audit for issues with templates, scripts, or methodology
  └─> Document improvements in audit execution checklist
  └─> Propose changes to README, templates, scripts, or Known Issues registry
  └─> Update docs/audit/README.md version and changelog
```

## Directory Structure

```text
docs/audit/
├── README.md                         ← This file
├── AUDIT_EXECUTION_TEMPLATE.md       ← Per-dataset audit checklist (copy per audit)
├── AUDIT_REPORT_TEMPLATE.md          ← Standardized report format (post-audit)
└── audits/                           ← Completed audit execution checklists
    ├── diqa-5000_audit.md
    ├── jssoda_audit.md
    └── mlt19_audit.md

config/
└── audit_scorecard.yaml              ← 6-dimension weighted scoring rubric

scripts/audit/
├── audit_config.py                   ← Dataset registry (14 known datasets)
├── audit_report_template.md          ← Symlink → docs/audit/AUDIT_REPORT_TEMPLATE.md
├── automated_prescreening.py         ← Phase 1: 15-field validation
├── audit_schema_compliance.py        ← Phase 2: Schema compliance (15 fields)
├── assemble_comparison.py            ← Phase 3: Multi-source comparison
├── select_audit_samples.py           ← Phase 4.5: Stratified sample selection
├── compute_scorecard.py              ← Post-audit: Quality scorecard computation
├── integration_script_template.py    ← Phase 5: Integration script skeleton
└── results/                          ← Per-dataset audit artifacts
    ├── CROSS_DATASET_KNOWN_ISSUES.json  ← 8 known issues registry
    ├── diqa-5000/
    │   ├── automated_screening.json
    │   ├── comparison_report.json
    │   ├── sample_set.json
    │   └── scorecard.json
    ├── jssoda/
    │   ├── automated_screening.json
    │   ├── comparison_report.json
    │   ├── sample_set.json
    │   └── scorecard.json
    ├── nepali-handwritten/              ← Full audit example
    │   ├── automated_screening.json
    │   ├── comparison_report.json
    │   ├── defect_catalog.json
    │   ├── sample_set.json
    │   ├── scorecard.json
    │   ├── vlm_corrections.json
    │   └── vlm_validation_passing.json
    └── mlt19/
        ├── automated_screening.json
        ├── comparison_report.json
        └── sample_set.json

docs/datasets/
└── AUDIT_TRACKING_INDEX.md           ← Central progress dashboard (51 datasets)
```

## Templates

### Execution Template

**File**: `AUDIT_EXECUTION_TEMPLATE.md`

**Purpose**: Step-by-step checklist for conducting a dataset audit, with per-phase task lists and artifact generation.

**Usage**:

```bash
# Copy template for new audit
cp docs/audit/AUDIT_EXECUTION_TEMPLATE.md docs/audit/audits/{dataset}_audit.md

# Replace placeholders
sed -i 's/{DATASET_NAME}/my-dataset/g' docs/audit/audits/my-dataset_audit.md
sed -i 's/{DATE}/2026-02-12/g' docs/audit/audits/my-dataset_audit.md
sed -i 's/{AUDITOR}/claude-opus-4-6/g' docs/audit/audits/my-dataset_audit.md

# Follow phases sequentially, check off tasks as completed
```

### Report Template

**File**: `AUDIT_REPORT_TEMPLATE.md`

**Purpose**: Standardized output format for completed audits with scorecard, defect catalog, and recommendations.

**Also Available At**: `scripts/audit/audit_report_template.md` (symlink for script access)

**Usage**:

```bash
# Fill report after audit completion
cp docs/audit/AUDIT_REPORT_TEMPLATE.md docs/audit/audits/{dataset}_report.md

# Include results from Phase 1-8 artifacts
# - automated_screening.json (Phase 1)
# - schema_compliance.json (Phase 2)
# - comparison_report.json (Phase 3)
# - defect_catalog.json (Phase 4)
# - vlm_validation.json (Phase 6)
# - scorecard.json (Post-audit)
```

### Integration Script Template

**File**: `scripts/audit/integration_script_template.py`

**Purpose**: Python skeleton for per-dataset enrichment integration with known issue mitigation toggles.

**Usage**:

```bash
# Copy template for new dataset
cp scripts/audit/integration_script_template.py scripts/integrate_{dataset}_enrichments.py

# Customize:
# 1. Update DATASET_NAME constant
# 2. Implement dataset-specific JSON parsing logic
# 3. Enable/disable KI-001 to KI-008 mitigations as needed
# 4. Add dataset-specific field mappings

# Test on sample set
PYTHONPATH=. uv run python3 scripts/integrate_{dataset}_enrichments.py \
    --sample-ids-file scripts/audit/results/{dataset}/sample_set.json \
    --dry-run

# Run full integration
PYTHONPATH=. uv run python3 scripts/integrate_{dataset}_enrichments.py
```

## Scripts

### Automated Validation Scripts

| Script | Phase | Purpose | Example Usage |
|--------|-------|---------|---------------|
| `automated_prescreening.py` | 1 | Validate 15 prescreening fields (split, capture_method, domain_level1, etc.) | `PYTHONPATH=. uv run python3 scripts/audit/automated_prescreening.py --dataset jssoda` |
| `audit_schema_compliance.py` | 2 | Validate 15 schema fields (types, ranges, COCO bbox format, etc.) | `PYTHONPATH=. uv run python3 scripts/audit/audit_schema_compliance.py --dataset jssoda` |
| `assemble_comparison.py` | 3 | Compare multiple enrichment sources, compute cross-source agreement | `PYTHONPATH=. uv run python3 scripts/audit/assemble_comparison.py --dataset jssoda` |
| `select_audit_samples.py` | 4.5 | Stratified random sampling for VLM inspection (36-100 images) | `PYTHONPATH=. uv run python3 scripts/audit/select_audit_samples.py --dataset jssoda --size 36` |
| `compute_scorecard.py` | Post-Audit | Compute 6-dimension quality grade (A/B/C/D/F) | `PYTHONPATH=. uv run python3 scripts/audit/compute_scorecard.py --dataset jssoda` |

### Dataset Catalog Update Scripts (Phase 9)

These scripts update the dataset source documentation and metadata aggregates after the audit is complete:

| Script | Purpose | Example Usage |
|--------|---------|---------------|
| `aggregate_layer2_metadata.py` | Regenerate dataset statistics from post-integration Layer 2 metadata | `uv run python3 scripts/aggregate_layer2_metadata.py --dataset jssoda --layer2-dir /mnt/e/image_detection/metadata_registry/json --verbose` |
| `materialize_reliability_summary.py` | Compute per-sample reliability and update source doc Reliability section | `uv run python3 scripts/materialize_reliability_summary.py --datasets jssoda --update-docs --force` |
| `compute_scorecard.py` | Compute quality scorecard (also used in Post-Audit phase) | `PYTHONPATH=. uv run python3 scripts/audit/compute_scorecard.py --dataset jssoda` |

**Agent**: `.claude/agents/dataset-catalog-agent.md` - Automated gap analysis against template v1.4.0 and cross-file synchronization.

### Script Output Artifacts

Each script generates JSON artifacts in `scripts/audit/results/{dataset}/`:

| Script | Output File | Fields |
|--------|-------------|--------|
| `automated_prescreening.py` | `automated_screening.json` | 13 field pass rates, failure examples |
| `audit_schema_compliance.py` | `schema_compliance.json` | 15 field validations, type/range errors |
| `assemble_comparison.py` | `comparison_report.json` | Cross-source agreement rates per field |
| `select_audit_samples.py` | `sample_set.json` | 36-100 stratified sample image IDs |
| `compute_scorecard.py` | `scorecard.json` | 6 dimension scores, final grade, recommendations |

### Common Script Options

All audit scripts support these common flags:

```bash
--dataset {dataset}     # Required: dataset canonical name
--verbose               # Enable detailed logging
--output-dir {path}     # Override default results/ directory
--help                  # Show full usage documentation
```

## Configuration

### Audit Scorecard (config/audit_scorecard.yaml)

**6-Dimension Weighted Scoring Rubric:**

| Dimension | Weight | Description | Source Artifact |
|-----------|--------|-------------|-----------------|
| **Field Coverage** | 25% | Percentage of 15 prescreening fields passing validation | `automated_screening.json` |
| **Field Validity** | 25% | Percentage of 15 schema compliance fields passing validation | `schema_compliance.json` |
| **Document Completeness** | 15% | Percentage of samples with all required fields populated | `automated_screening.json` |
| **Defect Rate** | 15% | Inverse of defect rate from VLM validation (1.0 - defect_rate) | `vlm_validation.json` |
| **Cross-Source Agreement** | 10% | Average agreement rate across enrichment sources | `comparison_report.json` |
| **VLM Accuracy** | 10% | VLM validation agreement rate on stratified sample | `vlm_validation.json` |

**Grade Thresholds:**

| Grade | Score Range | Quality Level | Production Readiness |
|-------|-------------|---------------|---------------------|
| **A** | 90-100 | Excellent | Ready for production training |
| **B** | 80-89 | Good | Minor gaps, usable with caveats |
| **C** | 70-79 | Acceptable | Significant gaps needing attention |
| **D** | 60-69 | Below Standard | Major remediation required |
| **F** | 0-59 | Failing | Not suitable for use |

**Missing Dimension Handling**: If a dimension is unavailable (e.g., no VLM validation run), its weight is
redistributed proportionally across remaining dimensions.

### Adaptive VLM Sampling Policy

VLM inspection sample sizes scale with metadata quality signals from Phases 1-4. Datasets with
more gaps or lower confidence require more visual verification to ensure data capture is thorough.

**Tier Selection**: Use the highest tier triggered by any signal.

| Signal | Tier 1 (Standard) | Tier 2 (Enhanced) | Tier 3 (Comprehensive) |
|--------|-------------------|-------------------|------------------------|
| Prescreening pass rate | >= 85% | 50-84% | < 50% |
| Critical/High defects | 0-2 | 3-5 | 6+ |
| Fields at 0% (missing source) | 0-1 | 2-3 | 4+ |
| Cross-source disagreement | < 10% | 10-30% | > 30% |
| KI-009 language mismatch | No | -- | Yes (auto Tier 3) |

**Sample Counts Per Tier:**

All counts use `max(fixed_count, pct_of_dataset)` so larger datasets receive proportionally
more inspection. For datasets > 10K images, use Track B contact sheets for the percentage portion.

| Component | Tier 1 | Tier 2 | Tier 3 |
|-----------|--------|--------|--------|
| Track A (per flag) | max(10, 3%) | max(15, 10%) | max(25, 15%) or all if < 50 |
| Track C (passing) | max(10, 2%) | max(15, 5%) | max(25, 10%) |
| **Minimum total** | **max(15, 5%)** | **max(30, 15%)** | **max(60, 25%)** |
| Target total | max(40, 5%) | max(75, 15%) | max(120, 25%) |

**Adaptive Expansion**: After the initial Track A batch, if any flag's FP rate exceeds the tier
threshold (Tier 2: 20%, Tier 3: 15%), expand to inspect **all TRUE samples** for that flag
before concluding Phase 6. This ensures corrections are applied to every affected sample,
not just a statistical sample.

**Rationale**: The RealDAE audit demonstrated that datasets with significant metadata gaps
(KI-009 language mismatch, 6 critical/high defects) benefit from higher inspection rates.
The 57-image inspection caught 17 corrections across 13 images, with `has_handwriting` at
30% FP and `has_figure` at 50% secondary FP -- patterns only visible with sufficient samples.

### Dataset Registry (scripts/audit/audit_config.py)

**14 Registered Datasets:**

| Dataset | Path | Stratification Axes |
|---------|------|---------------------|
| diqa-5000 | `/mnt/e/image_detection/metadata_registry/json/diqa-5000/` | capture_method, domain_level1 |
| jssoda | `/mnt/e/image_detection/metadata_registry/json/jssoda/` | script_family, degradation_type |
| mlt19 | `/mnt/e/image_detection/metadata_registry/json/mlt19/` | script_family, capture_method |
| tablebank | `/mnt/e/image_detection/metadata_registry/json/tablebank/` | domain_level1, layout_complexity |
| ohr-bench | `/mnt/e/image_detection/metadata_registry/json/ohr-bench/` | degradation_type, quality_score |
| pubtabnet | `/mnt/e/image_detection/metadata_registry/json/pubtabnet/` | layout_complexity, domain_level1 |
| doclaynet | `/mnt/e/image_detection/metadata_registry/json/doclaynet/` | layout_type, capture_method |
| cc-ocr | `/mnt/e/image_detection/metadata_registry/json/cc-ocr/` | capture_method, domain_level1 |
| realdae | `/mnt/e/image_detection/metadata_registry/json/realdae/` | degradation_type, capture_method |
| fintabnet | `/mnt/e/image_detection/metadata_registry/json/fintabnet/` | domain_level1, layout_complexity |
| cocotext | `/mnt/e/image_detection/metadata_registry/json/cocotext/` | capture_method, domain_level1 |
| mdiw13 | `/mnt/e/image_detection/metadata_registry/json/mdiw13/` | script_family, capture_method |
| nepali-handwritten | `/mnt/e/image_detection/metadata_registry/json/nepali_handwritten/` | capture_method, resolution_category, has_handwriting |
| nist-sd2 | `/mnt/e/image_detection/metadata_registry/json/nist_sd2/` | capture_method, domain_level1 |

**Usage**:

```python
from scripts.audit.audit_config import load_dataset_config, list_known_datasets

# List all registered datasets
datasets = list_known_datasets()  # Returns list of 12 dataset names

# Load configuration for specific dataset
config = load_dataset_config("jssoda")
# Returns DatasetAuditConfig with:
#   - name: "jssoda"
#   - metadata_dir: Path to JSON files
#   - stratification_axes: ["script_family", "degradation_type"]
#   - sample_size: 36 (default)
```

**Custom Datasets**: For datasets not in registry, build `DatasetAuditConfig` manually:

```python
from scripts.audit.audit_config import DatasetAuditConfig
from pathlib import Path

config = DatasetAuditConfig(
    name="my-custom-dataset",
    metadata_dir=Path("/path/to/metadata"),
    stratification_axes=["capture_method", "domain_level1"],
    sample_size=50
)
```

## Quick Start

### Prerequisites

```bash
# Ensure Layer 2 metadata exists at expected path
ls -1 /mnt/e/image_detection/metadata_registry/json/{dataset}/*.json | wc -l

# Install dependencies (if needed)
uv sync --extra dev
```

### Step-by-Step Audit Execution

```bash
# 1. Check dataset is registered
python3 -c "from scripts.audit.audit_config import list_known_datasets; print(list_known_datasets())"
# Output: ['diqa-5000', 'jssoda', 'mlt19', ...]

# 2. Copy execution template
cp docs/audit/AUDIT_EXECUTION_TEMPLATE.md docs/audit/audits/{dataset}_audit.md

# 3. Replace placeholders
DATASET="jssoda"
DATE=$(date +%Y-%m-%d)
sed -i "s/{DATASET_NAME}/$DATASET/g" docs/audit/audits/${DATASET}_audit.md
sed -i "s/{DATE}/$DATE/g" docs/audit/audits/${DATASET}_audit.md
sed -i "s/{AUDITOR}/claude-opus-4-6/g" docs/audit/audits/${DATASET}_audit.md

# 4. Phase 0: Complete paper review (manual)
# Read source paper, fill expected values in execution template

# 5. Phase 1: Run automated prescreening
PYTHONPATH=. uv run python3 scripts/audit/automated_prescreening.py --dataset $DATASET --verbose
# Output: scripts/audit/results/${DATASET}/automated_screening.json

# 6. Phase 2: Run schema compliance check
PYTHONPATH=. uv run python3 scripts/audit/audit_schema_compliance.py --dataset $DATASET --verbose
# Output: scripts/audit/results/${DATASET}/schema_compliance.json

# 7. Phase 3: Run multi-source comparison
PYTHONPATH=. uv run python3 scripts/audit/assemble_comparison.py --dataset $DATASET --verbose
# Output: scripts/audit/results/${DATASET}/comparison_report.json

# 8. Phase 4: Create defect catalog (manual)
# Review Phase 1-3 artifacts, identify patterns, create defect_catalog.json

# 9. Phase 4.5: Generate stratified sample for VLM review
PYTHONPATH=. uv run python3 scripts/audit/select_audit_samples.py --dataset $DATASET --size 36 --verbose
# Output: scripts/audit/results/${DATASET}/sample_set.json

# 10. Phase 5: Copy integration script template
cp scripts/audit/integration_script_template.py scripts/integrate_${DATASET}_enrichments.py
# Customize script with dataset-specific logic

# 11. Phase 6: Run VLM visual inspection (manual or agent-assisted)
# Use layer2-audit-agent or manual VLM review on sample_set.json
# Output: scripts/audit/results/${DATASET}/vlm_validation.json

# 12. Phase 7: Iterate corrections until targets met (manual)
# Fix defects, re-run Phases 1-6, repeat until 90% coverage + <5% defects

# 13. Phase 8: Fill audit report
cp docs/audit/AUDIT_REPORT_TEMPLATE.md docs/audit/audits/${DATASET}_report.md
# Fill with Phase 1-8 results

# 14. Post-Audit: Compute quality scorecard
PYTHONPATH=. uv run python3 scripts/audit/compute_scorecard.py --dataset $DATASET --verbose
# Output: scripts/audit/results/${DATASET}/scorecard.json

# 15. Update tracking index
# Add audit completion date and scorecard grade to docs/datasets/AUDIT_TRACKING_INDEX.md

# 16. Phase 6.5: VLM Text Labeling (if text_has_content < 50%)
# Check prescreening text_has_content pass rate:
grep "text_has_content" scripts/audit/results/${DATASET}/automated_screening.json
# If < 50%: scan images, transcribe max(ceil(0.01 * N), 10) samples at >75% confidence
# Output: results/${DATASET_UNDERSCORE}_text_labels.json
# Then re-run integration with --vlm-text-labels flag (see Phase 6.5 policy below)

# 17. Phase 9: Dataset catalog update
# Regenerate aggregate statistics from post-integration metadata
uv run python3 scripts/aggregate_layer2_metadata.py \
    --dataset $DATASET \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --verbose
# Output: metadata_registry/aggregates/${DATASET}_stats.json

# 18. Materialize reliability summary into source doc
uv run python3 scripts/materialize_reliability_summary.py \
    --datasets $DATASET \
    --update-docs \
    --force
# Updates: docs/datasets/source/${DATASET}.md (Reliability & Bottlenecks section)

# 19. Update source doc with audit summary (Section 11 per template v1.4.0)
# Manually or via dataset-catalog-agent:
#   - Add/update Section 11 "Layer 2 Audit Summary" with scorecard, defects, VLM results
#   - Verify Section 12 "Reliability & Bottlenecks" was updated by step 18
#   - Verify language/script section reflects actual LLM-detected distribution
#   - Verify known issues section includes audit-discovered defects

# 20. (Optional) Run dataset-catalog-agent for full gap analysis
# The agent validates all 12 template sections, checks cross-file consistency
# (Quick Reference, Processing Status, Task Indices), and flags missing content.
# Invoke via: /agent dataset-catalog-agent with dataset name

# 21. Phase 10: Lessons Learned & Process Improvement
# Review audit execution for friction points, script bugs, stale docs, new KI patterns.
# Categorize improvements and apply quick fixes to README, templates, scripts.
# Add "Lessons Learned" section to docs/audit/audits/${DATASET}_audit.md.
# See Phase 10 detailed section below for full procedure.
```

### Phase 6.5: VLM Text Labeling Policy

**Trigger**: If Phase 1 prescreening shows `text_has_content` pass rate < 50%, VLM text labeling
is required before proceeding to Phase 7 corrections.

**Sample Count**: `max(ceil(0.01 * total_samples), 10)` samples. For a 958-sample dataset, this
is `max(10, 10) = 10`. For a 5000-sample dataset, this is `max(50, 10) = 50`.

**Sample Selection Criteria**:

1. **Upright images only** - exclude rotated samples (orientation_class != 0)
2. **Confidence > 75%** - VLM must be able to transcribe at >75% estimated accuracy
3. **Diverse document types** - sample across different content categories (essays, forms, lists, etc.)
4. **Both splits represented** - include samples from train and test if available

**Procedure**:

```bash
# 1. Check text_has_content pass rate from prescreening
grep "text_has_content" scripts/audit/results/{dataset}/automated_screening.json

# 2. If pass rate < 50%, scan images for clean samples
#    Read images via VLM vision, classify as HIGH/GOOD/MEDIUM/POOR legibility

# 3. Transcribe high-confidence samples and save to results
#    Output: results/{dataset}_text_labels.json
#    Schema: {"labels": [{"image_id": "train/1", "transcription": "...", "confidence": 0.9, ...}]}

# 4. Add --vlm-text-labels flag to integration script
#    The integration script template includes load_vlm_text_labels() and compute_text_statistics()

# 5. Re-run integration (Phase 7) to populate text_content fields
PYTHONPATH=. uv run python3 scripts/integrate_{dataset}_enrichments.py \
    --vlm-text-labels results/{dataset}_text_labels.json
```

**Integration Fields Set**:

| Field | Source | Description |
|-------|--------|-------------|
| `text_has_content` | Boolean | True if transcription exists for this sample |
| `text_content` | String | Full transcription text |
| `text_content_confidence` | Float | VLM transcription confidence (0.0-1.0) |
| `text_content_source` | Enum | `vlm_manual_transcription`, `docling_gpu_ocr`, or `none` |
| `text_statistics` | Object | `{char_count, word_count, line_count, has_content, avg_line_length, ...}` |

### Expected Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Phase 0: Paper Review | 30-60 min | One-time per dataset |
| Phase 1-3: Automated Analysis | 5-10 min | Fully automated scripts |
| Phase 4: Defect Catalog | 1-2 hours | Manual review of artifacts |
| Phase 4.5: Sample Generation | 1 min | Automated stratified sampling |
| Phase 5: Integration Script | 2-4 hours | Dataset-specific customization |
| Phase 6: VLM Inspection | Variable | Scales with dataset size and tier (see Adaptive Sampling Policy) |
| Phase 7: Corrections | Variable | Depends on defect severity |
| Phase 8: Documentation | 30-60 min | Report writing, index updates |
| Phase 9: Catalog Update | 15-30 min | Scripts + source doc finalization |
| **Total** | **1-2 days** | First audit ~2 days, subsequent ~1 day |

## Known Issues Registry

**Location**: `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json`

**9 Known Issues Tracked:**

| ID | Issue | Severity | Scope | Mitigation |
|----|-------|----------|-------|------------|
| **KI-001** | Docling layout label casing mismatch | CRITICAL | All Docling datasets | Run `standardize_layout_labels.py` before integration |
| **KI-002** | Table detection multi-column FP | HIGH | Synthetic/multi-column | VLM verify all `has_table=True` samples |
| **KI-003** | Picture detection dense text FP | MEDIUM | Synthetic datasets | VLM verify `has_figure=True` samples |
| **KI-004** | LLM handwriting on synthetic | HIGH | Synthetic datasets | Override `has_handwriting=False` for synthetic |
| **KI-005** | LLM cannot detect synthetic capture | HIGH | Synthetic datasets | Hardcode `capture_method=synthetic` from docs |
| **KI-006** | LLM formula semantic confusion | MEDIUM | All LLM-enriched | VLM verify `has_formula=True` samples |
| **KI-007** | LLM domain UNK on generic content | LOW | Generic/narrative | Accept `domain_level1=UNK` as valid |
| **KI-008** | `script_family` contains directionality | HIGH | All base-annotated | Re-derive via `get_script_family(iso15924_script)` |
| **KI-009** | Documentation language claims unreliable | CRITICAL | Docs-only language | Cross-validate with LLM enrichment; prioritize LLM |

**Integration Script Template**: All known issues have toggle flags and mitigation sections
in `integration_script_template.py`:

```python
# Known issue mitigation toggles (integration_script_template.py)
APPLY_KI_001_LAYOUT_CASING = True     # Docling lowercase -> PascalCase
# KI-002: VLM_TABLE_TRUE_POSITIVES frozenset
# KI-003: VLM_FIGURE_TRUE_POSITIVES frozenset
# KI-004: IS_SYNTHETIC_DATASET flag -> has_handwriting=False
# KI-005: KNOWN_CAPTURE_METHOD override
# KI-006: VLM_FORMULA_TRUE_POSITIVES frozenset
# KI-007: Accept domain_level1=UNK (no toggle needed)
# KI-008: Always re-derive script_family via get_script_family()
# KI-009: resolve_language() priority chain favors LLM over docs
```

## Phase 9: Dataset Catalog Update (Detailed)

After the scorecard is computed and the tracking index updated, the dataset's source documentation
(`docs/datasets/source/{dataset}.md`) must be brought into full alignment with the audit findings.
This ensures the catalog entry serves as the single source of truth for downstream consumers
(training recipes, dataset selection, agent gap analysis).

### Why This Phase Exists

Prior to Phase 9, the audit produces JSON artifacts (scorecard, defect catalog, VLM corrections)
but the human-readable source documentation may still contain stale or incomplete information.
Common gaps discovered during audits include:

- Language/script sections reflecting paper claims rather than LLM-detected actuals (e.g., KI-009)
- Missing "Layer 2 Audit Summary" section (Section 11 per template v1.4.0)
- Reliability section not reflecting post-integration bottleneck analysis
- Known issues section missing audit-discovered defects

### Step-by-Step Procedure

**Prerequisites**: Phases 1-8 complete, scorecard computed, integration script has been run.

#### Step 1: Regenerate Aggregate Statistics

```bash
uv run python3 scripts/aggregate_layer2_metadata.py \
    --dataset {dataset} \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --verbose
```

**Output**: `metadata_registry/aggregates/{dataset}_stats.json`

This reads the post-integration Layer 2 metadata and computes:

- Capture method distribution
- Domain distribution
- Language/script distribution
- Quality score statistics
- Degradation type frequencies
- Content flag frequencies

#### Step 2: Materialize Reliability Summary

```bash
uv run python3 scripts/materialize_reliability_summary.py \
    --datasets {dataset} \
    --update-docs \
    --force
```

**Effect**: Rewrites the "Reliability & Bottlenecks" section (Section 12) in
`docs/datasets/source/{dataset}.md` with per-sample confidence analysis. The `--force` flag
recomputes even if a `sample_reliability_summary` already exists in the metadata.

**Important**: This script overwrites the entire section. If you added contextual notes
(e.g., explaining why a bottleneck exists), re-add them after the script runs.

#### Step 3: Update Source Doc Sections

Manually update `docs/datasets/source/{dataset}.md` per template v1.4.0:

| Section | Action | Source |
|---------|--------|--------|
| 5.3 Language & Script | Update with actual LLM-detected distribution | `{dataset}_stats.json` or `comparison_report.json` |
| 7. Known Issues | Add "Layer 2 Audit Findings" subsection with defect IDs | `defect_catalog.json` |
| 8. Layer 2 Annotation Summary | Update enrichment sources, field coverage | Integration script, `automated_screening.json` |
| **11. Layer 2 Audit Summary** (NEW) | Add scorecard, key defects, VLM results | `scorecard.json`, `defect_catalog.json`, `vlm_corrections.json` |
| 12. Reliability & Bottlenecks | Verify materialized by Step 2, add context | `materialize_reliability_summary.py` output |

#### Step 4: Compute Final Scorecard

Re-run the scorecard after doc updates (doc_completeness dimension may change):

```bash
PYTHONPATH=. uv run python3 scripts/audit/compute_scorecard.py --dataset {dataset} --verbose
```

**Output**: `scripts/audit/results/{dataset}/scorecard.json`

#### Step 5: (Optional) Run Dataset Catalog Agent

For thorough gap analysis and cross-file synchronization, invoke the dataset-catalog-agent:

```text
Agent: .claude/agents/dataset-catalog-agent.md
Task: "Validate and update the catalog entry for {dataset} against template v1.4.0.
       Check all 12 sections, flag gaps, and verify cross-file consistency with
       Quick Reference, Processing Status, and Task Indices."
```

The agent validates:

- All 12 template sections are present and populated
- Cross-references with `DATASET_QUICK_REFERENCE.md` are consistent
- Processing status in `DATASET_PROCESSING_STATUS.md` matches current state
- Task index entries (IQA, Layout, etc.) reflect the dataset's capabilities

### Phase 9 Checklist

- [ ] `aggregate_layer2_metadata.py` ran successfully → `{dataset}_stats.json` generated
- [ ] `materialize_reliability_summary.py` updated source doc reliability section
- [ ] Section 11 (Layer 2 Audit Summary) added/updated with scorecard and defects
- [ ] Language/script section reflects actual distribution (not just paper claims)
- [ ] Known issues section includes audit-discovered defects
- [ ] Final scorecard recomputed after doc updates
- [ ] (Optional) Dataset-catalog-agent gap analysis passed

## Phase 10: Lessons Learned & Process Improvement (Detailed)

Every audit surfaces friction points, gaps, or improvements in the audit system itself. Phase 10
captures these insights so the process improves with each dataset audited.

### Why This Phase Exists

Without a structured feedback loop, the same pain points recur across audits. Examples from
past audits:

- **nepali-handwritten**: Discovered `aggregate_layer2_metadata.py` filename mismatch (hyphen vs
  underscore), `materialize_reliability_summary.py` missing `--verbose` flag, prescreening field
  count was stale (13 -> 15 after v2.3.0), and VLM text labeling proved viable as a new enrichment
  source not previously documented.
- **realdae**: KI-009 language mismatch pattern led to creating the Adaptive VLM Sampling Policy
  and expanding from 3 to 8 known issues.

### Step-by-Step Procedure

After the audit scorecard is finalized and the tracking index updated:

#### Step 1: Review Audit Friction Points

Walk through the audit execution checklist and identify:

- **Script failures**: Did any script fail unexpectedly? What was the root cause?
- **Missing enrichment sources**: Were there enrichment types (text labels, skew, resolution) that
  should have been available but weren't?
- **Stale documentation**: Did the README, templates, or Known Issues registry contain outdated
  information?
- **Missing known issues**: Did the audit discover a new cross-dataset pattern not yet in
  `CROSS_DATASET_KNOWN_ISSUES.json`?
- **Workflow gaps**: Were there manual steps that should be automated, or automated steps that
  produced incorrect results?

#### Step 2: Categorize Improvements

| Category | Examples | Target File(s) |
|----------|----------|-----------------|
| **Script bug** | Filename mismatch, missing CLI flags | `scripts/audit/*.py`, `scripts/*.py` |
| **Template gap** | Missing section, stale field count | `docs/audit/README.md`, `AUDIT_EXECUTION_TEMPLATE.md` |
| **New known issue** | Cross-dataset pattern not in registry | `CROSS_DATASET_KNOWN_ISSUES.json` |
| **New enrichment type** | VLM text labels, classical IQA | Integration script template, README |
| **Documentation stale** | Wrong dataset count, old version refs | `docs/audit/README.md`, tracking index |
| **Process change** | New phase, reordered steps | Workflow overview, execution template |

#### Step 3: Implement or Propose Changes

- **Quick fixes** (typos, counts, version refs): Apply directly and increment README version.
- **Script fixes**: Fix in the relevant script, add to troubleshooting table.
- **New known issues**: Add to `CROSS_DATASET_KNOWN_ISSUES.json` with full evidence.
- **Template changes**: Update both the README description and the actual template file.
- **Process changes**: Discuss with team before modifying the workflow sequence.

#### Step 4: Update Audit Execution Checklist

Add a "Lessons Learned" section to the per-dataset audit checklist
(`docs/audit/audits/{dataset}_audit.md`) documenting:

- What worked well
- What caused friction
- Specific changes made or proposed to the audit system

### Phase 10 Checklist

- [ ] Reviewed audit execution for friction points and gaps
- [ ] Categorized improvements by type (script bug, template gap, new KI, etc.)
- [ ] Applied quick fixes (README version, field counts, troubleshooting entries)
- [ ] Proposed or implemented script/template changes
- [ ] Added new known issues to `CROSS_DATASET_KNOWN_ISSUES.json` (if applicable)
- [ ] Updated `docs/audit/README.md` version number and Last Updated date
- [ ] Added "Lessons Learned" note to per-dataset audit checklist

## Related Documentation

### Core Methodology

- [Layer 2 Audit Prompt](../prompts/layer2_audit_prompt.md) - Core 8-phase methodology with prompts (Phase 9 added here)
- [Layer 2 Audit Agent](../../.claude/agents/layer2-audit-agent.md) - Automated agent definition for Phase 6
- [Dataset Catalog Agent](../../.claude/agents/dataset-catalog-agent.md) - Gap analysis and cross-file sync for Phase 9
- [Dataset Template](../datasets/DATASET_TEMPLATE.md) - v1.4.0 with 12 sections including audit summary

### Dataset Documentation

- [Audit Tracking Index](../datasets/AUDIT_TRACKING_INDEX.md) - Central progress dashboard (51 datasets)
- [Dataset Quick Reference](../datasets/DATASET_QUICK_REFERENCE.md) - Dataset overview with metadata coverage
- [Dataset Processing Status](../datasets/DATASET_PROCESSING_STATUS.md) - Conversion/extraction status

### Architecture

- [Level 2 Data Preparation](../architecture/diagrams/level-2/data-preparation/index.md) - Layer 2 enrichment pipeline
- [Architecture Maintenance Guide](../architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md) - Documentation update workflows

### Standards

- [Development Standards](../../CLAUDE.md) - Project-specific development standards
- [Global Standards](~/.claude/CLAUDE.md) - Universal Claude Code development standards

## Support

### Troubleshooting

**Common Issues:**

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: audit_config` | Use `PYTHONPATH=. uv run python3 scripts/audit/script.py` |
| `FileNotFoundError: metadata_registry` | Check dataset is registered in `audit_config.py` |
| `KeyError: field_coverage` | Ensure `automated_screening.json` exists for scorecard computation |
| Empty `comparison_report.json` | Dataset may have only one enrichment source (skip Phase 3) |
| Stratified sampling fails | Reduce `--size` parameter if stratification axes have few unique values |
| `aggregate_layer2_metadata.py` file not found | Metadata filename may use underscores (`foo_bar_metadata.json`) while script constructs with hyphens (`foo-bar_metadata.json`). Create symlink: `ln -sf actual_name.json expected-name.json` |
| `materialize_reliability_summary.py` unknown flag | `--verbose` is NOT supported by this script. Remove the flag. |
| Reliability section overwritten | `materialize_reliability_summary.py --update-docs` replaces the entire Reliability section. Re-add contextual notes (e.g., bottleneck explanations) after the script runs. |

**Debug Mode:**

```bash
# Enable detailed logging
PYTHONPATH=. uv run python3 scripts/audit/automated_prescreening.py \
    --dataset jssoda \
    --verbose \
    --debug
```

### Contact

For audit methodology questions or script issues, see:

- GitHub Issues: [image_detection/issues](https://github.com/ByronWilliamsCPA/image_detection/issues)
- Project Documentation: [docs/](../)
- Layer 2 Enrichment Spec: [schema.py](../../src/image_preprocessing_detector/schema.py)

---

**Last Updated**: 2026-02-12
**Template Version**: 1.2.0
**Audit Methodology Version**: 2.3.0
