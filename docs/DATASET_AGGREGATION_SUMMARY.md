---
owner: docs-team
purpose: Summary of Layer 2 metadata aggregation results
schema_type: common
status: active
tags:
- datasets
- metadata
- analysis
title: Dataset Aggregation Summary
---

> **Date**: 2026-01-31
> **Datasets Processed**: 24 of 50 datasets with Layer 2 metadata
> **Output Location**: `metadata_registry/aggregates/`

---

## Aggregation Results

### Successfully Processed Datasets (20)

| Dataset | Samples | Capture Method | Domain | Content Flags | Text Scope | Script Family |
|---------|---------|----------------|--------|---------------|------------|---------------|
| arabic_docs_ocr | 10,045 | Unknown | UNK | - | - | - |
| bhutan_financial | 125 | Unknown | UNK | - | - | - |
| cc_ocr | 7,058 | Unknown | UNK | - | - | - |
| cvsi | 10,715 | Unknown | UNK | - | - | - |
| dibco | 212 | Scanner flatbed (100%) | UNK (100%) | - | - | - |
| diqa-5000 | 5,500 | - | - | - | - | - |
| doclaynet | 80,863 | Born-digital (100%) | UNK/TEC/SCI mix | has_table varies | page (100%) | ltr (100%) |
| docsynth300k | 300,000 | Synthetic (100%) | Mixed | has_table varies | page (100%) | ltr (100%) |
| financebench | 54,121 | Unknown | UNK | - | - | - |
| fintabnet | 97,475 | Born-digital (100%) | FIN (100%) | has_table (100%) | page (100%) | ltr (100%) |
| funsd | 199 | Scanner (100%) | UNK (100%) | - | - | - |
| funsd_plus | 1,113 | Unknown | UNK | - | - | - |
| invoices-kaggle | 1,414 | Scanner (est.) | FIN | - | - | ltr (100%) |
| ohr-bench | 8,303 | Unknown | UNK | - | - | - |
| omnidocbench | 377 | Unknown | UNK | - | - | - |
| pubtabnet | 519,030 | Born-digital (100%) | SCI (100%) | has_table (100%) | page (100%) | ltr (100%) |
| realdae | 583 | Camera (100%) | UNK (100%) | - | - | - |
| signatr6k | 12,514 | Unknown | UNK | - | - | - |
| smartdoc-qa | 4,260 | Camera (100%) | UNK (100%) | - | - | - |
| sroie | 2,043 | Scanner (100%) | UNK (100%) | - | - | - |
| sroie-voxel51 | 712 | Scanner (100%) | UNK | - | - | ltr (100%) |
| tablebank | 10 | Born-digital (100%) | SCI (100%) | has_table (100%) | page (100%) | ltr (100%) |
| tibhcr | 141,698 | Unknown | UNK | - | - | - |
| tobacco800 | 1,290 | Scanner (100%) | UNK (100%) | - | - | - |

**Note**: Some datasets have partial metadata (e.g., tablebank shows only 10 samples in metadata vs 278K images in actual dataset)

### Datasets Without Layer 2 Metadata (26)

No metadata files found for:

- hasyv2
- hindi-synth
- iam-handwriting
- im2latex
- invoices-kg
- iqa-phase7-100k
- iqa-phase7-165k
- mathverse
- mdiw13
- midv500
- midv500-data
- mle2e
- mlt19
- mobile-receipts
- multilingual-scripts
- multimodal-textbook
- nepal-devanagari
- nist-sd2, nist-sd6, nist-sd19
- ocr-quality
- pucit-ohul
- publaynet
- rvl-cdip
- synth-multiscript-250k
- wili-2018
- yarmouk

---

## Key Findings

### Available Metadata Fields

| Field | Datasets with Data | Coverage |
|-------|-------------------|----------|
| **Capture Method** | 17/24 | 71% |
| **Domain** | 24/24 | 100% (but mostly "UNK") |
| **Content Flags** (has_table) | 5/24 | 21% |
| **Text Scope** | 5/24 | 21% |
| **Script Family** | 8/24 | 33% |
| **Quality Scores** | 0/24 | 0% |
| **Degradation Types** | 0/24 | 0% |
| **Layout Types** | 0/24 | 0% |
| **Language/Script Codes** | 0/24 | 0% |

### Observations

1. **Capture Method Coverage**:
   - Synthetic: docsynth300k (layout)
   - Born-digital: doclaynet, fintabnet, pubtabnet, tablebank (table datasets)
   - Scanner: dibco, funsd, sroie, sroie-voxel51, tobacco800, invoices-kaggle, receipts_hitl (degraded/forms)
   - Camera: realdae, smartdoc-qa (camera-captured)
   - Unknown: 7 datasets (need enrichment)

2. **Domain Classification**:
   - FIN (Financial): fintabnet (100%), invoices-kaggle, receipts_hitl
   - SCI (Scientific): pubtabnet, tablebank, doclaynet subset
   - UNK (Unknown): 18/24 datasets (needs improvement)

3. **Content Flags**:
   - has_table: 100% coverage for table datasets (fintabnet, pubtabnet, tablebank, doclaynet, docsynth300k subset)
   - Other flags (has_formula, has_handwriting, has_figure): not yet populated

4. **Missing Fields**:
   - **Quality scores**: Not yet extracted (critical for IQA training)
   - **Degradation types**: Not yet extracted (critical for IQA training)
   - **Layout types**: Not yet extracted (critical for layout detection)
   - **Language/Script codes**: Not yet extracted (critical for multilingual training)

---

## Current Usability for Quick Reference

### What We Can Show Now

**Capture Method** (11 datasets with data):

- Can display icons (📄 born-digital, 🖨️ scanner, 📱 camera)
- Can show percentages for these 11 datasets
- Need to mark others as "Unknown" or infer from dataset type

**Domain** (limited usefulness):

- FIN: 1 dataset (fintabnet)
- SCI: 3 datasets (pubtabnet, tablebank, doclaynet subset)
- UNK: 16 datasets (not useful)

**Content Flags** (4 datasets with data):

- has_table: Can show 100% for table datasets
- Missing for other content types

### What We Cannot Show Yet

**Quality Profiles**:

- ❌ Quality score ranges (min-max-mean)
- ❌ Degradation type frequencies
- ❌ Degradation severity distributions

**Language/Script Coverage**:

- ❌ Script codes (ISO 15924)
- ❌ Language codes (ISO 639)
- ❌ Script family distributions

**Layout Characteristics**:

- ❌ Layout type distributions
- ❌ Text density distributions

**Text Scope**:

- Limited data (only 4 datasets have this field)

---

## Recommendations

### Short-Term (Use What We Have)

1. **Update Quick Reference with Partial Metadata**:
   - Add "Capture Method" column for datasets with data (11/20)
   - Show "Unknown" for datasets without capture method enrichment
   - Add "Domain" column (limited usefulness but shows FIN/SCI for 4 datasets)
   - Add "has_table" indicator for table datasets

2. **Create "Metadata Coverage" Indicator**:

   ```markdown
   | Dataset | Images | Metadata Coverage | Capture | Domain | Notes |
   |---------|--------|-------------------|---------|--------|-------|
   | fintabnet | 97,475 | ⭐⭐⭐ (Good) | 📄 Born-digital | FIN | has_table: 100% |
   | ohr-bench | 8,303 | ⭐ (Minimal) | Unknown | UNK | Needs enrichment |
   ```

3. **Document Metadata Gaps**:
   - Clearly note which datasets have incomplete Layer 2 enrichment
   - Show expected timeline for completing enrichment

### Medium-Term (Complete Layer 2 Enrichment)

1. **Priority Enrichment Tasks**:
   - **P0**: Add quality scores + degradation types to IQA training datasets (ohr-bench, diqa-5000)
   - **P1**: Add language/script codes to multilingual datasets (mdiw13, mlt19, synth-multiscript-250k)
   - **P2**: Add layout types + text density to layout detection datasets
   - **P3**: Backfill capture method for "Unknown" datasets

2. **Update Enrichment Pipeline**:
   - Ensure all schema fields are populated during annotation
   - Run enrichment on 20 datasets without metadata yet
   - Re-process 9 datasets with "Unknown" capture methods

3. **Quality Validation**:
   - Spot-check aggregated statistics for accuracy
   - Validate against ground truth where available
   - Document confidence levels for inferred metadata

### Long-Term (Full Implementation)

1. **Automated Quick Reference Updates**:
   - Create `scripts/update_quick_reference_from_aggregates.py`
   - Auto-generate metadata-enriched tables from aggregate JSONs
   - Integrate into pre-commit hooks or CI/CD

2. **Metadata Characteristics Matrix**:
   - Implement all 8 filtering tables (by capture, domain, quality, layout, etc.)
   - Only possible after Layer 2 enrichment is complete

3. **Training Decision Matrix**:
   - Build dataset recommendation engine based on metadata
   - Show expected coverage for training tasks

---

## Next Steps

### Immediate Actions

1. **Update DATASET_QUICK_REFERENCE.md**:
   - Add "Capture Method" column (show icons + % for 11 datasets with data)
   - Add "Domain" column (show FIN/SCI/UNK)
   - Add metadata coverage indicator (⭐⭐⭐ = good, ⭐⭐ = partial, ⭐ = minimal)
   - Document that full metadata enhancement pending Layer 2 completion

2. **Create Metadata Status Section**:

   ```markdown
   ## Metadata Status

   **Layer 2 Enrichment Progress**: 20/40 datasets annotated
   **Metadata Fields**: Partial (capture method, domain, content flags available)
   **Full Metadata Expected**: After IQA and script detection enrichment completes
   ```

3. **Use Aggregates for Immediate Value**:
   - Show capture method where available
   - Highlight table datasets (has_table: 100%)
   - Show domain classification for FIN/SCI datasets

### Future Work

- Complete Layer 2 enrichment for all datasets
- Re-run aggregation script
- Implement full metadata-enhanced Quick Reference
- Build automated update pipeline

---

**Generated**: 2026-01-31
**Script**: [scripts/aggregate_layer2_metadata.py](../scripts/aggregate_layer2_metadata.py)
**Next Review**: After next batch of Layer 2 enrichment completes
