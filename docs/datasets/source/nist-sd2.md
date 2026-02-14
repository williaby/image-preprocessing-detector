#### NIST Special Database 2 (SD-2)

> **Quick Stats**: 5,590 pages | Synthesized tax forms | Binary B&W | Form field annotations
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NIST Special Database 2: Structured Forms Reference Set (SFRS) |
| **Version** | Final |
| **Release Date** | 1992 |
| **Maintainer** | NIST (National Institute of Standards and Technology) |
| **Website** | [NIST SRD 2](https://www.nist.gov/srd/nist-special-database-2) |
| **License** | Public Domain (U.S. Government Work) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nist_db2/` |
| **Documentation Status** | Complete |

##### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | 5,590 page images (2560×3300 px, binary B&W) |
| **Annotations** | .fmt (text) | Field annotation files (one per image) |
| **Metadata** | N/A | No separate metadata files |
| **Supplementary** | PDF / TXT | Dataset documentation, paper |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `splits/nist-sd2/train.json` | Co-located .fmt | 4,472 | ✅ Manifest created |
| **Validation** | `splits/nist-sd2/val.json` | Co-located .fmt | 559 | ✅ Manifest created |
| **Test** | `splits/nist-sd2/test.json` | Co-located .fmt | 559 | ✅ Manifest created |
| **Total** | All images in source directory | Co-located .fmt | 5,590 | ✅ Complete |

**Split Organization Pattern**: `single_dir_with_manifest`

> **Notes**:
>
> - No official splits from NIST - created locally with random seed 42
> - .fmt annotation files co-located with images in source directory
> - All images accessible via symlinks in `data/phase7_mvp/00_base_images/nist_db2/`
> - Original source: `/mnt/e/image_detection/benchmarks/nist_db2/sd02/data/sfrs_*/`

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | .fmt (text) | Form / Field | Ground truth field values |
| **Form Metadata** | .fmt (text) | Form | Form ID, form type (implicit) |
| **Field Count** | .fmt (text) | Form | Number of fields per form |
| **Handwriting Flag** | .fmt (text) | Form | Inferred from field value presence |

> **Note**: No bounding boxes, polygons, segmentation masks, or spatial coordinates provided.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | NIST documentation | Release date (1992), IRS 1040 Package X, 12 form types |
| **Image-level** | Filename | Form type inferred from directory structure (sfrs_0-8) |
| **Annotation-level** | .fmt files | Field ID, field value, special tokens (_ICON_) |
| **Document-level** | .fmt files | Form ID (line 1), field count (line count - 1) |

###### 2.5 Annotation Schema Details

> **Format**: Custom text format (.fmt files)

```text
# .fmt File Structure
Line 1: Form ID (unique identifier, e.g., "1040_001")
Line 2+: field_id value

Example:
1040_001
SSN 123-45-6789
FNAME JOHN
LNAME DOE
WAGES 45000
_ICON_  ← Special token for non-text content (checkboxes, logos)

# Field value parsing
- Split on first space: field_id, value
- Special token "_ICON_" marks non-text content
- Empty values indicate unfilled fields
- No spatial coordinates provided
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `form_id` | str | Yes | Line 1, unique per form |
| `field_id` | str | No | Part of field_id value pairs |
| `value` | str | No | Field transcription or "_ICON_" |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Form ID | `form_id` | High | Direct extraction from .fmt line 1 |
| ✅ Form type | `form_type` | High | Hardcoded "1040" (could infer from dir) |
| ✅ Field values | `sample_fields` | High | Currently extracts first 5, could extract all |
| ✅ Field IDs | - | Medium | Available but not currently extracted |
| ✅ Field count | `field_count` | Medium | Computed from line count |
| ✅ Handwriting flag | `has_handwritten_content` | Medium | Inferred from field value presence |
| ✅ Text GT | `text_content.full_text` | High | Parser populates via .fmt concatenation |
| ❌ Bounding boxes | - | N/A | Not provided in source |
| ❌ Quality scores | - | N/A | Not provided in source |
| ❌ Reading order | - | N/A | Not provided in source |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

###### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Synthetic |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Synthesized IRS 1040 tax forms, exact by construction |
| **GT Label Coverage** | 100% |

##### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training |
| **Purpose** | Form structure IQA, field detection baseline |
| **Local Path** | `01_base_data/forms/nist_db2/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | None required (already normalized) |

##### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `parse_nist_db2_labels` |
| **Parser Status** | ✅ Complete (text_content populated) |
| **Layer 1 Fields** | `form_id`, `field_count`, `sample_fields`, `text_content` |
| **Layer 2 Auto-Derived** | `capture_method`, `domain=FIN`, `resolution` |
| **Config Entry** | `DATASET_CONFIGS["nist_db2"]` |

> **Parser Reference**: Extracts form_id, field_count, sample_fields from .fmt files; populates text_content schema

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/forms/nist-sd2/` | ✅ Available | 5,590 TIF files |
| **Text/GT** | Native annotations | ✅ Available | TXT (.fmt): Form field values (field_id value pairs in `.fmt` files) |
| **Text/OCR Extracted** | `annotations/nist-sd2/ocr/ocr_batch_*.jsonl` | ✅ Available | 5,590 records (100%), Docling OCR |
| **Layout Extracted** | `annotations/nist-sd2/layout/layout_batch_*.json` | ✅ Available | 5,590 records (100%), DocLayout-YOLO |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- ℹ️ N/A - Not applicable for this dataset type

##### 4. Dataset Statistics

###### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 4,472 | 4,472 | 100% | 🔄 Pending re-annotation |
| **Validation** | 559 | 559 | 100% | 🔄 Pending re-annotation |
| **Test** | 559 | 559 | 100% | 🔄 Pending re-annotation |
| **Total** | 5,590 | 5,590 | 100% | ✅ All images annotated |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- 🔄 Pending - Split created, needs Layer 2 re-annotation with split field
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: Splits created locally (not official NIST splits). Layer 2 metadata needs
> re-annotation to populate `provenance.split` field with train/val/test assignments.
> Use split manifests in `splits/nist-sd2/*.json` to map images to splits.

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 5,590 pages |
| **Training Split** | 4,472 (80%) |
| **Validation Split** | 559 (10%) |
| **Test Split** | 559 (10%) |
| **Simulated Submissions** | 900 tax returns |
| **Average Forms/Submission** | 6.2 form faces |
| **Form Types** | 12 IRS forms (20 unique faces) |
| **Resolution** | 300 DPI |
| **File Format** | Binary (B&W) |
| **Supplementary Files** | 5,590 text files (field answers) |

##### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Financial (US Federal Tax Forms) |
| **Document Types** | IRS 1040 Package X (1988 tax year) |
| **Language(s)** | English (100%) |
| **Temporal Range** | 1988 tax year forms |
| **Acquisition Method** | Synthesized (computer-generated) |

###### 5.1 Form Types Included

IRS 1040 Package X (1988 tax year):

- Forms: 1040, 2106, 2441, 4562, 6251
- Schedules: A, B, C, D, E, F, SE

###### 5.2 Class/Category Definitions

> **Purpose**: Define the taxonomy of form types used in the dataset.

| Class/Category | ID | Description | Parent |
|----------------|-----|-------------|--------|
| **Main Forms** | - | Primary IRS tax forms | - |
| Form 1040 | 1 | Individual Income Tax Return | Main Forms |
| Form 2106 | 2 | Employee Business Expenses | Main Forms |
| Form 2441 | 3 | Child and Dependent Care Credit | Main Forms |
| Form 4562 | 4 | Depreciation and Amortization | Main Forms |
| Form 6251 | 5 | Alternative Minimum Tax | Main Forms |
| **Schedules** | - | Income/deduction schedules | - |
| Schedule A | 6 | Itemized Deductions | Schedules |
| Schedule B | 7 | Interest and Dividend Income | Schedules |
| Schedule C | 8 | Profit or Loss from Business | Schedules |
| Schedule D | 9 | Capital Gains and Losses | Schedules |
| Schedule E | 10 | Supplemental Income and Loss | Schedules |
| Schedule F | 11 | Profit or Loss from Farming | Schedules |
| Schedule SE | 12 | Self-Employment Tax | Schedules |

**Total**: 12 form types, 20 unique form faces (some forms are 2-sided)

###### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| English | en / Latn | 5,590 | 100% | US tax forms only |

**Script Families Present**: Latin

##### 6. IQA Profile

###### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Synthesized (computer-generated, not real scans) |
| **Capture Device** | N/A (programmatically generated) |
| **Original Quality** | Clean, no authentic scanning artifacts |
| **Compression** | PNG lossless |
| **Known Artifacts** | None (synthesized data) |

###### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Form field boundaries extremely sensitive |
| **Noise** | MEDIUM | High contrast masks moderate noise |
| **Skew** | **HIGH** | Grid alignment critical for field isolation |
| **Contrast** | LOW | Already high contrast (black on white) |
| **Compression** | LOW | Binary format, no compression artifacts |

###### 6.3 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | MEDIUM - Clean ground truth, but synthesized only |
| **Unique Characteristics** | Form structure, field-level annotations |
| **Complementary Datasets** | Combine with real scanned tax forms (SROIE, FUNSD) |
| **Benchmark Suitability** | LOW - Synthesized data doesn't represent real-world degradation |
| **Known Limitations** | No real scanning artifacts, dated form designs (1988) |

##### 10. Dataset-Specific Notes

> **Purpose**: Capture unique characteristics, caveats, and implementation details specific to this dataset.

###### 10.1 Annotation Caveats

- **.fmt file format is custom**: Not standard JSON/XML - text-based field-value pairs
- **Special token "_ICON_"**: Marks non-text content (checkboxes, logos, signatures)
- **No spatial coordinates**: Field locations not annotated - form-level only
- **Synthesized data**: Computer-generated forms, not real scanned documents
  - **Implication**: No authentic scanning artifacts (blur, skew, degradation)
  - **Use case**: Clean ground truth for form structure, not real-world quality assessment
  - **Complement with**: Real scanned tax forms for degradation training
- **Field ID conventions**: Field IDs are IRS-specific (e.g., SSN, WAGES, FNAME)
- **1988 tax year**: Forms are from 1988 - outdated layouts and field requirements

###### 10.2 Implementation Notes

- **Parser text_content**: Parser successfully populates text_content schema by concatenating .fmt field values
- **Form type hardcoded**: Parser hardcodes form_type="1040"
  - **Alternative**: Could infer from directory structure (sfrs_0-8) or form_id pattern
- **.fmt files co-located**: Annotation files stored alongside images in source directory
  - **Naming**: `{image_stem}.fmt` matches `{image_stem}.png`
- **Capture method metadata**: Marked as "scanner" in Layer 2 but actually synthesized

###### 10.3 External Resources

- **NIST SRD 2 website**: <https://www.nist.gov/srd/nist-special-database-2>
- **Dataset series**: Part of NIST Special Database series
  - SD-2: Tax forms (this dataset)
  - SD-6: Census forms with handprint
  - SD-19: Handwriting characters
- **IRS forms**: 1040 Package X (1988 tax year)
  - **Historical note**: Forms are 35+ years old, layouts have changed significantly
- **Public domain**: U.S. Government work, no license restrictions

###### 10.4 Custom Metrics

N/A - No dataset-specific quality tiers or scoring systems

> **Important**: This is a **synthesized** dataset, not real scanned documents.
> Use for form structure understanding and field detection training, but pair
> with real degraded form datasets for production-ready IQA models.

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthesized (computer-generated) |
| **Baseline Quality** | Clean, no real scanning artifacts |
| **Blur Sensitivity** | HIGH - Form field boundaries sensitive |
| **Skew Sensitivity** | **HIGH** - Grid alignment critical |
| **Key Challenge** | Mixed printed/handwritten content |
| **Annotation Value** | Field-level ground truth available |

##### Training Value

- **Strengths**: Clean ground truth, field annotations, public domain
- **Weaknesses**: Synthesized (not real scans), dated form designs
- **Use Case**: Form structure detection, field isolation training

##### Project Usage

- **Path**: `01_base_data/forms/nist_db2/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Form structure IQA, field detection baseline
- **Parser**: ✅ `parse_nist_db2_labels` (extracts form_id, field_count, sample_fields from .fmt files)

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 5,590 |
| **File Format** | PNG (100%) |
| **Dimensions** | 2560 × 3300 px (fixed) |
| **Avg File Size** | 164 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | FIN (Financial/Tax) |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 5,590 | **Avg Min Confidence**: 0.585

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 512 | 9.2% |
| active_learning | 4,412 | 78.9% |
| unreliable | 666 | 11.9% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `layout_detections` | 98.4% | 0.585 |
| 2 | `has_table` | 1.6% | 0.800 |
