---
l4_category: training-dataset-template
l4_status: template
---

> **Version**: 2.0.0
> **Last Updated**: 2026-02-23
> **Purpose**: Standardized 11-section template for individual training dataset documentation files
> **Scope**: Assembled training datasets under `docs/datasets/training/{name}.md`
> **What Changed in v2**: Added HAR-sourced sections (source pool, gap registry, OOD cross-reference,
> 14-dimension diversity) to match the Head Adequacy Review methodology

---

## How to Use This Template

1. Copy this file to `docs/datasets/training/{dataset-name}.md`
2. Replace all `{PLACEHOLDER}` values
3. Fill in sections using the referenced HAR file(s) and DDR file as primary sources
4. Update `TRAINING_DATASET_CATALOG.md` summary table row to point to this file
5. Remove this instruction block and the guidance comments before committing

**Primary sources for each section**:

| Section | Primary Source |
|---------|---------------|
| 1. Identity | `SIGLIP2_MULTITASK_REQUIREMENTS.md`, L2 schema |
| 2. Status | `HAR_MASTER_INDEX.md` |
| 3. Source Pool | Individual HAR file(s) § Section 2 |
| 4. Label Schema | HAR § Section 2 + L2 schema |
| 5. Composition | HAR § Section 3 |
| 6. Diversity | HAR § Section 4 + `diversity_reports/{name}_ddr.md` |
| 7. Wild Conditions | HAR § Section 5 |
| 8. OOD | HAR § Section 6 + `OOD_DATASET_CATALOG.md` |
| 9. Assembly Pipeline | `prepare_multitask_datasets.py` or generation scripts |
| 10. Gap Registry | HAR § Section 8 (all gap IDs verbatim) |
| 11. Performance Targets | `SIGLIP2_MULTITASK_REQUIREMENTS.md` |

---

# {Dataset Name}

> **Quick Stats**: {N} images | {task description} | {label type}
>
> **Status**: {✅ Ready / 🔄 In Progress / ❌ Blocked} | **HAR Score**: {XX}/100 | **P0 Gaps**: {N}

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `{name}` |
| **Head(s) Fed** | {e.g., SIG-G5-2 `shadow_reg`} |
| **Model(s)** | {e.g., SigLIP 2 NAFlex} |
| **Task Type** | {e.g., Regression 0–1 continuous severity score} |
| **Primary L2 Field(s)** | `{e.g., physical_degradation.shadow_severity}` |
| **Training Phase** | {e.g., Phase 5 — Page Attributes} |
| **Target Size** | {N} images |
| **Image Size** | {e.g., 384px} |
| **Storage Location** | `E:\image_detection\03_training_datasets\{name}\` |
| **GCS Path** | `gs://image_detection_b/{name}_training/` |
| **Assembly Script** | `scripts/prepare_multitask_datasets.py {subcommand}` |
| **HAR File(s)** | [har/{name}.md](../../planning/har/{name}.md) |
| **DDR File** | [diversity_reports/{name}_ddr.md](../diversity_reports/{name}_ddr.md) |

---

## Section 2 — Status

| Metric | Value |
|--------|-------|
| **Assembly Status** | {e.g., ❌ Blocked / 🔄 In Progress / ✅ Ready} |
| **Current Count** | {N} / {target} assembled |
| **HAR Adequacy Score** | {XX}/100 — {✅ Ready / ⚠️ Needs Work / ❌ Blocked} |
| **P0 Gap Count** | {N} |
| **Primary Blocker** | {e.g., `label_shadow_severity.py` not created — or "None"} |
| **Estimated Unblock Effort** | {e.g., 5–7 days — or "N/A"} |
| **Last HAR Updated** | YYYY-MM-DD |

---

## Section 3 — Source Pool Analysis

> *Derived from HAR § Section 2. Identifies which source datasets contribute to this assembled
> training dataset and how much of each is usable given the required L2 field coverage.*

**Required L2 Field**: `{field.path}` ({type}, {range/enum})
**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)
**Label Provenance**: {preferred provenance tier}

### Candidate Source Datasets

| Source Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Usable |
|----------------|-------------|-----------------|------------|-------------|--------|
| {dataset-1} | {N} | {N} | {%} | {%} | {✅ N / ⚠️ N / ❌ BLOCKED} |
| {dataset-2} | {N} | {N} | {%} | {%} | {✅ N / ⚠️ N / ❌ BLOCKED} |

### Pool Summary

| Metric | Value |
|--------|-------|
| **Total usable (current)** | {N} images |
| **Total usable (post-P0)** | ~{N} images (projected) |
| **Training target** | {N} images |
| **Pool surplus/deficit** | {+N / -N} ({%} of target) |
| **Real vs. synthetic ratio** | {X% real / Y% synthetic} |

---

## Section 4 — Label Schema

> *The exact fields, types, and value conventions that training records must carry.*

**Primary L2 Field**: `{field.path}`
**Type**: {float / int / str / bool}
**Range / Enum**: {e.g., 0.0–1.0 or NONE / SPARSE / MODERATE / SUBSTANTIAL / DOMINANT}
**Provenance Tier**: {tier_0_exact / tier_1_annotation / tier_2_vlm / tier_3_weak}
**Derivation Formula** *(if applicable)*: `{formula or "N/A"}`

### Training Manifest Record Schema

```json
{
  "image_path": "{task}/images/{filename}.jpg",
  "source_dataset": "{source_name}",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0,
  "{primary_label_field}": {example_value},
  "capture_method": "{born_digital|scanner|camera_smartphone|...}"
}
```

### Label Statistics (target / post-assembly)

| Metric | Value |
|--------|-------|
| **Range** | {[min, max]} |
| **Target mean** | {X.XX} |
| **Class/bucket distribution** | {describe — or see Section 5} |

---

## Section 5 — Composition & Splits

> *Target count, class/severity distribution, split ratios, and leakage prevention strategy.*

### Target Distribution

<!-- For regression tasks: use severity/value buckets -->
<!-- For classification tasks: use class names -->

| Class / Bucket | Range | Target % | Target Count |
|----------------|-------|----------|-----------  -|
| {class/bucket 1} | {range} | {%} | {N} |
| {class/bucket 2} | {range} | {%} | {N} |

### Split Strategy

| Split | Images | Percentage |
|-------|-------:|------------|
| Train | {N} | 70% |
| Val | {N} | 15% |
| Test | {N} | 15% |
| **Total** | **{N}** | **100%** |

**Split Method**: {document-level / image-level / stratified-by-class}
**Random Seed**: 42
**Leakage Prevention**: {describe — e.g., source dataset test splits reserved for OOD; global split registry via SHA256}

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audit**: [{name}_ddr.md](../diversity_reports/{name}_ddr.md)
> **HAR Section 4 Reference**: [{har-file}.md § Section 4](../../planning/har/{har-file}.md)
> **Overall Diversity Score**: {XX}/100 (pre-assembly estimate)

*Sorted by relevance to this head. Dimensions not listed have LOW relevance and are not
separately targeted for this dataset.*

| Dimension | L2 Field | Relevance | Target | Current | Status |
|-----------|----------|-----------|--------|---------|--------|
| {dim-1} | `{field}` | CRITICAL | {target} | {current} | {✅ / ⚠️ / ❌} |
| {dim-2} | `{field}` | HIGH | {target} | {current} | {✅ / ⚠️ / ❌} |
| {dim-3} | `{field}` | MEDIUM | {target} | {current} | {✅ / ⚠️ / ❌} |

### Key Diversity Gaps

- {gap description — e.g., "born_digital examples absent; pool is scanner + camera only"}
- {gap description}

---

## Section 7 — Wild Condition Coverage

> **HAR Section 5 Reference**: [{har-file}.md § Section 5](../../planning/har/{har-file}.md)
> **Overall Wild Condition Score**: {XX}/100

*The 3–5 most critical edge cases for this head. A condition is "covered" if the source pool
contains labeled examples and they will be included in the assembled training dataset.*

| Wild Condition | L2 Evidence | Status | Gap |
|----------------|-------------|--------|-----|
| {condition-1} | `{l2_field}` | {✅ Covered / ⚠️ Partial / ❌ Missing} | {gap description or "None"} |
| {condition-2} | `{l2_field}` | {✅ Covered / ⚠️ Partial / ❌ Missing} | {gap description or "None"} |
| {condition-3} | `{l2_field}` | {✅ Covered / ⚠️ Partial / ❌ Missing} | {gap description or "None"} |

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
> **HAR Section 6 Reference**: [{har-file}.md § Section 6](../../planning/har/{har-file}.md)

| Field | Value |
|-------|-------|
| **Primary OOD Category** | {e.g., OOD-Degradation} |
| **OOD Target Images (this head)** | {N} |
| **OOD Acquisition Status** | {⏳ Not started / 🔄 In progress / ✅ Complete} |

| OOD Sub-source | Images | Relevance | Stress Scenario |
|----------------|-------:|-----------|-----------------|
| {sub-source-1} | {N} | {✅ Direct / ⚠️ Indirect / ❌ Not relevant} | {description} |
| {sub-source-2} | {N} | {✅ Direct / ⚠️ Indirect / ❌ Not relevant} | {description} |

**OOD Leakage Risk**: {e.g., training source X must not appear in OOD; doc3d test split reserved}

---

## Section 9 — Assembly Pipeline

**Status**: {❌ Blocked / 🔄 Ready to run / ✅ Complete}

### Assembly Commands

```bash
# Prerequisites (run in order)
# {list any prerequisite steps, e.g., labeling scripts}

# Dry run (validates without writing)
uv run python scripts/prepare_multitask_datasets.py {subcommand} --dry-run

# Full assembly
uv run python scripts/prepare_multitask_datasets.py {subcommand}
```

### Dependencies

| Dependency | Status | Required For |
|------------|--------|-------------|
| `{script_or_field}` | {✅ Ready / ❌ Not created / ⚠️ Partial} | {what it enables} |
| `{dataset}_metadata.json` | {✅ / ⚠️ / ❌} | Source pool labels |

### Generated Outputs

| File | Description |
|------|-------------|
| `train_manifest.json` | Flat JSON list of training records |
| `val_manifest.json` | Flat JSON list of validation records |
| `{name}/images/` | Dataset images (or GCS path) |

---

## Section 10 — Gap Registry

> **Source**: [{har-file}.md § Section 8](../../planning/har/{har-file}.md)
> **HAR Adequacy Score**: {XX}/100 — {✅ Ready / ⚠️ Needs Work / ❌ Blocked}

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
|--------|-------------|------------|-------------|--------|
| {PREFIX}-G01 | {description} | {root cause} | {action} | {N days} |
| {PREFIX}-G02 | {description} | {root cause} | {action} | {N days} |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Remediation | Effort |
|--------|-------------|-------------|--------|
| {PREFIX}-G0N | {description} | {action} | {N days} |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
|--------|-------------|-------------|
| {PREFIX}-G0N | {description} | {action} |

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
> (or [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](../../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) for MNV4 heads)

| Head ID | Head Name | Task | Target Metric | Target Value | Test Set |
|---------|-----------|------|--------------|-------------|----------|
| {SIG-GX-Y} | `{head_name}` | {task type} | {metric} | {value} | {OOD category} |

### Achieved Results

| Head | Val {metric} | Test {metric} | Status |
|------|-------------|--------------|--------|
| `{head_name}` | — | — | ❌ Not trained |

---

## Related Documents

- **HAR File(s)**: [{har-file}.md](../../planning/har/{har-file}.md)
- **DDR**: [{name}_ddr.md](../diversity_reports/{name}_ddr.md)
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **HAR Synthesis**: [HAR_SYNTHESIS.md](../../planning/HAR_SYNTHESIS.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | YYYY-MM-DD | Initial creation |

---

## Template Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-02-23 | Added HAR-sourced sections (source pool, gap registry, OOD, diversity); restructured from 7 to 11 sections |
| 1.0.0 | 2026-02-01 | Initial template |
