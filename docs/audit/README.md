# Layer 2 Metadata Audit System

> **Version**: 1.2.0
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
  └─> Run automated_prescreening.py → 13-field validation
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
  └─> Run VLM agent on sample_set.json → Validate 13 fields visually
  └─> Expand inspection for flags with high FP rates
  └─> Generates vlm_validation.json with agreement rates per field

Phase 7: Corrections & Iteration
  └─> Fix defects identified in Phase 4-6
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
├── audit_config.py                   ← Dataset registry (12 known datasets)
├── audit_report_template.md          ← Symlink → docs/audit/AUDIT_REPORT_TEMPLATE.md
├── automated_prescreening.py         ← Phase 1: 13-field validation
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
    │   └── sample_set.json
    ├── jssoda/
    │   ├── automated_screening.json
    │   ├── comparison_report.json
    │   └── sample_set.json
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
| `automated_prescreening.py` | 1 | Validate 13 prescreening fields (split, capture_method, domain_level1, etc.) | `PYTHONPATH=. uv run python3 scripts/audit/automated_prescreening.py --dataset jssoda` |
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
| **Field Coverage** | 25% | Percentage of 13 prescreening fields passing validation | `automated_screening.json` |
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
threshold (Tier 2: 20%, Tier 3: 15%), expand inspection for that flag before concluding Phase 6.

**Rationale**: The RealDAE audit demonstrated that datasets with significant metadata gaps
(KI-009 language mismatch, 6 critical/high defects) benefit from higher inspection rates.
The 57-image inspection caught 17 corrections across 13 images, with `has_handwriting` at
30% FP and `has_figure` at 50% secondary FP -- patterns only visible with sufficient samples.

### Dataset Registry (scripts/audit/audit_config.py)

**12 Registered Datasets:**

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

# 16. Phase 9: Dataset catalog update
# Regenerate aggregate statistics from post-integration metadata
uv run python3 scripts/aggregate_layer2_metadata.py \
    --dataset $DATASET \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --verbose
# Output: metadata_registry/aggregates/${DATASET}_stats.json

# 17. Materialize reliability summary into source doc
uv run python3 scripts/materialize_reliability_summary.py \
    --datasets $DATASET \
    --update-docs \
    --force
# Updates: docs/datasets/source/${DATASET}.md (Reliability & Bottlenecks section)

# 18. Update source doc with audit summary (Section 11 per template v1.4.0)
# Manually or via dataset-catalog-agent:
#   - Add/update Section 11 "Layer 2 Audit Summary" with scorecard, defects, VLM results
#   - Verify Section 12 "Reliability & Bottlenecks" was updated by step 17
#   - Verify language/script section reflects actual LLM-detected distribution
#   - Verify known issues section includes audit-discovered defects

# 19. (Optional) Run dataset-catalog-agent for full gap analysis
# The agent validates all 12 template sections, checks cross-file consistency
# (Quick Reference, Processing Status, Task Indices), and flags missing content.
# Invoke via: /agent dataset-catalog-agent with dataset name
```

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

**8 Known Issues Tracked:**

| ID | Issue | Severity | Affected Datasets | Mitigation |
|----|-------|----------|-------------------|------------|
| **KI-001** | Missing `split` field | HIGH | 5 datasets | Default to "train" with deprecation warning |
| **KI-002** | Invalid `capture_method` values | MEDIUM | 3 datasets | Fuzzy matching to canonical values |
| **KI-003** | Script family mismatch with ISO639 | MEDIUM | 4 datasets | ISO639 takes precedence |
| **KI-004** | Layout bbox outside image bounds | HIGH | 2 datasets | Clip to [0, 1] normalized range |
| **KI-005** | Empty `degradation_type` array | LOW | 6 datasets | Accept as valid (pristine documents) |
| **KI-006** | Quality score out of [0, 1] range | HIGH | 1 dataset | Clamp to [0, 1] with warning |
| **KI-007** | Missing `domain_level2` when level1 exists | LOW | 8 datasets | Set to "UNK" |
| **KI-008** | Duplicate layout detections | MEDIUM | 2 datasets | Deduplicate by bbox IoU > 0.95 |

**Integration Script Template**: All known issues have toggle flags in `integration_script_template.py`:

```python
# Known issue mitigation toggles
MITIGATE_KI_001 = True   # Missing split field
MITIGATE_KI_002 = True   # Invalid capture_method
MITIGATE_KI_003 = True   # Script family mismatch
MITIGATE_KI_004 = True   # Layout bbox clipping
MITIGATE_KI_005 = False  # Empty degradation_type (valid)
MITIGATE_KI_006 = True   # Quality score clamping
MITIGATE_KI_007 = True   # Missing domain_level2
MITIGATE_KI_008 = True   # Duplicate layout detections
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
