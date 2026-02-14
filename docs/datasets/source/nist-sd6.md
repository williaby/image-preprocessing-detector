#### NIST Special Database 6 (SD-6)

> **Quick Stats**: 5,595 pages | Synthesized census forms | Binary B&W | Handprint samples
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NIST Special Database 6: Structured Forms Reference Set II (SFRS2) |
| **Version** | Final |
| **Release Date** | 1992 |
| **Maintainer** | NIST |
| **Website** | [NIST SRD 6](https://www.nist.gov/srd/nist-special-database-6) |
| **License** | Public Domain |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nist_sd6/` |
| **Documentation Status** | Complete |

##### Source Data Inventory

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Binary (1-bit) scanned form images, 2560×3300 px |
| **Annotations** | .fmt (TXT) | Field-level transcriptions with field IDs |
| **Supplementary** | .txt (field tables) | Field definition tables per form type |

###### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **All (no splits)** | `sd06/data/sfrs2_*/` | Same directory (.fmt files) | 5,595 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest`

> **Notes**:
>
> - Dataset does not provide official train/val/test splits
> - Forms organized by form type (sfrs2_0 through sfrs2_19, 20 types total)
> - Each form type contains submissions from 900 simulated respondents
> - Typical usage: Use entire dataset for training (not a benchmark)

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | .fmt (TXT) | Field-level | Ground truth field values (handwritten content) |
| **Form Metadata** | .fmt (TXT) | Page-level | Form type ID (line 1 of .fmt file) |

> **Note**: Dataset does NOT provide bounding boxes, polygons, or layout annotations. Only field-level text transcriptions.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Image-level** | Filename | Form type (sfrs2_X), submission ID (rXXXX), page number |
| **Document-level** | .fmt file (line 1) | Form type identifier (e.g., "1040_1") |

###### 2.5 Annotation Schema Details

> **Format**: Custom text format (field_id + space + transcription)

```text
# .fmt file structure:
1040_1                                    # Line 1: Form type ID
1040_1_L_H1_V1 July                      # Lines 2+: field_id value
1040_1_L_H2_V1 July
1040_1_L_H3_V1 88
1040_1_L_H1_V2 Brainerd A. & Erskine W. Mitchell
... (variable number of fields per form)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `form_type_id` | str | Yes | Line 1 of .fmt file (e.g., "1040_1") |
| `field_id` | str | Yes | First token of each line (e.g., "1040_1_L_H1_V1") |
| `field_value` | str | Varies | Transcription after space, may be empty or "_ICON_" |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Field text | `text_content.full_text` | **HIGH** | Ground truth transcriptions |
| ✅ Form type ID | `provenance.source_file` | Medium | Useful for stratification |
| ✅ Field IDs | `text_content.segments[].id` | Medium | Enables field-level tracking |
| ⚠️ Handwriting flag | `content_flags.has_handwriting` | Medium | Inferred from non-empty fields |
| ❌ Bounding boxes | - | Low | Not provided |
| ❌ Layout structure | - | Low | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

###### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Mixed |
| **Provenance Tier** | Tier 0/Tier 1 |
| **Annotator Details** | NIST (synthesized forms + real handprint overlays) |
| **Quality Assurance** | Standardized NIST collection protocol |
| **GT Label Coverage** | 100% |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 5,595 pages |
| **Simulated Submissions** | 900 |
| **Form Faces** | 20 unique |
| **Resolution** | 300 DPI |
| **File Format** | Binary (B&W) |
| **Supplementary Files** | 5,595 text files, 20 field tables |

##### Split Coverage

> **CRITICAL**: Dataset does not provide official train/val/test splits.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **All (no split)** | 5,595 | 5,595 | 100% | ✅ Complete |

**Split Status Legend:**

- ✅ Complete - All samples included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: NIST SD-6 is distributed as a single collection without splits. Typical usage
> is to use the entire dataset for training. For research experiments, recommend stratified
> splitting by form type (20 types: sfrs2_0 through sfrs2_19) to ensure all form types
> represented in train/val/test.

##### Text Statistics

> **Source**: Computed from ground truth text labels via `calculate_text_statistics.py`
> **Availability**: ⚠️ NOT YET COMPUTED - Requires R1 implementation first

**Status**: ❌ BLOCKED - Text content not yet integrated into Layer 2 (see R1)

**Text Source**: `dataset_provided` (ground truth field transcriptions from .fmt files)

> **Note**: Text statistics will be populated after implementing R1 (text_content integration).
> Expected statistics include character count, word count, field count, and handwriting prevalence.

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthesized with handprint |
| **Content** | 1988 Census forms with handwritten entries |
| **Skew Sensitivity** | HIGH - Form grid alignment |
| **Handwriting Quality** | Variable stroke quality |
| **Key Value** | Mixed printed/handwritten form processing |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Document Types** | Tax forms with handwritten fields |
| **Form Types** | 20 unique form faces from 1988 US Census |
| **Content Mix** | Printed form structure + handwritten entries |
| **Field Types** | Names, addresses, dates, numeric values, checkboxes |

##### Language & Script Coverage

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Latin | Latn | 5,595 | 100% | English only |
| English | en | 5,595 | 100% | US Census forms (1988 version) |

**Script Families Present**: Latin only

> **Notes**:
>
> - Monolingual dataset (English only)
> - All text content is English handwriting or printed English labels
> - Script: Latin alphabet (A-Z, 0-9, punctuation)
> - No multilingual or multi-script content

##### Project Usage

- **Path**: `01_base_data/forms/nist_sd6/`
- **Purpose**: Handwritten field detection, form grid IQA
- **Parser**: ✅ `parse_nist_sd6_labels` (extracts form_id, field_count, sample_fields from .fmt files)

##### Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`parse_nist_sd6_labels`](../../scripts/annotate_base_metadata.py#L3103) |
| **Parser Status** | ⚠️ Partial - Extracts to raw_labels, needs text_content integration |
| **Layer 1 Fields** | `raw_labels.form_id`, `raw_labels.field_count`, `raw_labels.sample_fields`, `raw_labels.has_handwritten_content` |
| **Layer 2 Auto-Derived** | `language.language_code="en"`, `language.script_name="Latin"`, `domain.domain_code="TAX"`, `capture_method.method="scanner_flatbed"` |
| **Config Entry** | [`DATASET_CONFIGS["nist-sd6"]`](../../scripts/annotate_base_metadata.py) |
| **Text Content Status** | ❌ NOT INTEGRATED - Requires R1 implementation |

**Parser Field Mappings** (current):

| Source Field (.fmt) | Layer 1 Destination | Layer 2 Destination | Status |
|---------------------|---------------------|---------------------|--------|
| Line 1 (form_id) | `raw_labels.form_id` | - | ⚠️ Should map to provenance |
| Field values | `raw_labels.sample_fields` | ❌ NOT MAPPED | ⚠️ Should map to text_content |
| Field count | `raw_labels.field_count` | - | ✅ OK (metadata) |
| Non-empty fields | `raw_labels.has_handwriting` | ❌ NOT MAPPED | ⚠️ Should map to content_flags |

> **Action Required**: Implement R1 to integrate text_content properly.

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/forms/nist_sd6/` | ✅ Available | 5,595 PNG files |
| **Text/GT** | Native annotations | ✅ Available | TXT (.fmt): Form field values (field_id value pairs in `.fmt` files) |
| **Text/OCR Extracted** | `annotations/nist-sd6/ocr/ocr_batch_*.jsonl` | ✅ Available | 5,595 records (100%), Docling OCR |
| **Layout Extracted** | `annotations/nist-sd6/layout/layout_batch_*.json` | ✅ Available | 5,593 records (100%), DocLayout-YOLO |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Empty - Data not available or not extracted
- ⚠️ Partial - Some data available, incomplete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 5,595 |
| **File Format** | PNG (100%) |
| **Dimensions** | 2560 × 3300 px (fixed) |
| **Avg File Size** | 169 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | TAX (Tax Forms w/ Handprint) |

#### Known Issues & Limitations

- **Synthesized Content**: Forms are synthesized (900 simulated respondents), not real census data
- **Limited Form Types**: Only 20 form types from 1988 Census forms
- **No Bounding Boxes**: Dataset does not provide field-level bounding boxes or layout annotations
- **Field Granularity Only**: Text available at field level, not word or character level
- **Historical Context**: 1988 Census forms may not reflect modern form design patterns
- **Handwriting Variety**: Limited to 900 simulated respondents (may lack diversity)
- **Binary Images**: 1-bit binary format limits preprocessing options (no grayscale information)
- **No Form Structure**: Field structure and layout must be inferred from form type tables
- **Incomplete Field Coverage**: Some fields empty or marked "_ICON_" (not transcribed)

#### Representative Samples

> **Note**: Representative samples to be added. Sample images available at:
> `/mnt/e/image_detection/01_base_data/forms/nist_sd6/sd06/data/sfrs2_0/r0000/r0000_00.png`

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| [Pending] | Typical census form | Binary image, grid structure, handwritten fields |
| [Pending] | Form with dense fields | Multiple handwritten entries |
| [Pending] | Sparse form | Empty fields, checkboxes |

> **TODO**: Extract 3 representative samples, create thumbnails, add to `docs/assets/datasets/`

#### References

##### Primary Citation

```bibtex
@techreport{nist_sd6_1992,
  title={NIST Special Database 6: Structured Forms Reference Set II (SFRS2)},
  author={NIST},
  institution={National Institute of Standards and Technology},
  year={1992},
  url={https://www.nist.gov/srd/nist-special-database-6}
}
```

##### Related Works

- [NIST SD-2](#nist-sd2) - Tax forms without handwriting (predecessor)
- [NIST SD-19](#nist-sd19) - Pure handwriting dataset (digits + letters)
- [FUNSD](#funsd) - Modern form understanding dataset

##### External Resources

- [NIST Official Page](https://www.nist.gov/srd/nist-special-database-6)
- [NIST Special Database Series](https://www.nist.gov/srd/nist-special-database-series)

#### Dataset-Specific Notes

##### 10.1 Annotation Caveats

- Field IDs follow NIST convention: `{form_type}_L_{location_code}_V{variant}`
- Some fields contain "_ICON_" placeholder (checkbox or icon, not transcribed)
- Empty fields represented by blank lines (field_id present but no value)
- Field count varies by form type (typically 40-60 fields per form)

##### 10.2 Implementation Notes

- .fmt files use UTF-8 encoding but may contain legacy encoding artifacts
- Parser uses `errors="ignore"` when reading .fmt files to handle encoding issues
- Form type mapping available in `sd06/tables/` directory (20 .txt files)
- Image filenames format: `{submission_id}_{page_number}.png` (e.g., "r0000_00.png")

##### 10.3 Form Type Distribution

| Form Type Range | Count | Notes |
|-----------------|-------|-------|
| sfrs2_0 to sfrs2_19 | ~280 each | 20 form types, approximately balanced |

**Total**: 5,595 forms across 20 types (avg 279.75 per type)

##### 10.4 Custom Metrics

- **Field Completion Rate**: Percentage of non-empty fields per form (varies by form type)
- **Handwriting Density**: Estimated by counting non-empty field values
- **Form Type Stratification**: Recommend splitting by form type for train/val/test to ensure coverage

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 5,595 | **Avg Min Confidence**: 0.572

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 399 | 7.1% |
| active_learning | 4,352 | 77.8% |
| unreliable | 844 | 15.1% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `layout_detections` | 99.5% | 0.572 |
| 2 | `text_quality` | 0.5% | 0.800 |
| 3 | `has_table` | 0.0% | 0.800 |
