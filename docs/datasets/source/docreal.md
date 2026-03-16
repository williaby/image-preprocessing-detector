---
dataset_id: docreal
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - perspective_distortion
  - warping
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### DocReal (Document Dewarping Benchmark)

> **Quick Stats**: 251 images (201 distorted + 50 scanned GT) | Camera-captured + scanner | MIT license
>
> **Note**: Quick Reference lists 200 (paired distorted images only); full dataset includes 50 additional scanned GT references and 1 extra distorted image.
>
> **License**: MIT | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DocReal |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | irisXcoding et al. |
| **Paper** | [Robust Document Dewarping via Attention-Enhanced Control Point Prediction](https://github.com/irisXcoding/DocReal) |
| **Repository** | [GitHub: irisXcoding/DocReal](https://github.com/irisXcoding/DocReal) |
| **License** | MIT |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Camera-captured distorted document images (201 images) |
| **Images** | PNG | Flatbed-scanned ground truth images (50 images) |
| **Supplementary** | README, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Distorted** | `DocReal/distorted/` | Implicit (filename-based pairing) | 201 | ✅ |
| **Scanned (GT)** | `DocReal/scanned/` | Implicit (filename-based pairing) | 50 | ✅ |

**Split Organization Pattern**: `by_folder` (distorted vs scanned subfolders)

> **Notes**:
>
> - 201 distorted images (camera-captured with various warping)
> - 50 scanned images serving as ground truth
> - Multiple distorted variants per scanned document (doc_id maps distorted to scanned)
> - No explicit train/val/test split provided (user-defined)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Filename-based | Document | Distorted images paired with scanned GT via doc_id |
| **Capture Method** | Directory-based | Document | "distorted" = camera, "scanned" = flatbed scanner |

> **Note**: Primary annotation is through paired image structure. Scanned images serve as dewarping ground truth.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README, Paper | Description, citation, methodology |
| **Image-level** | Filename pattern | Document ID linking distorted to scanned GT |

##### 2.5 Annotation Schema Details

> **Format**: Filename-based pairing structure

```text
DocReal/
├── distorted/
│   ├── {doc_id}_{variant}.png    # Camera-captured distorted images
│   ├── 001_01.png                # Document 001, variant 01
│   ├── 001_02.png                # Document 001, variant 02
│   └── ...
└── scanned/
    ├── {doc_id}.png              # Flatbed-scanned ground truth
    ├── 001.png                   # Document 001 GT
    └── ...

# Multiple distorted variants per scanned document
# doc_id links distorted to scanned GT
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to distorted or scanned image |
| `doc_id` | str | Yes | Document identifier linking distorted to GT |
| `variant` | str | No | Distortion variant index (distorted images only) |
| `capture_type` | str | Yes | "distorted" (camera) or "scanned" (flatbed) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `paired_file` | High | doc_id-based pairing |
| ✅ Capture method | `capture_method` | High | camera_smartphone (distorted) / scanner_flatbed (scanned) |
| ✅ Document ID | `doc_id` | High | From filename pattern |
| ❌ Quality scores | - | Low | Not provided; compute from pairing |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Paired GT |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Camera-captured distorted images paired with flatbed-scanned GT |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (dewarping correction) |
| **Purpose** | Dewarping benchmark, correction model evaluation |
| **Local Path** | `01_base_data/camera_captured/docreal/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | doc_id-based pair matching required |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Parser Status** | ⚠️ Partial - Parser created but enrichment not yet run |
| **Layer 2 Auto-Derived** | `capture_method` (camera_smartphone or scanner_flatbed), `has_warping=True` |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/docreal/` | ✅ Available | PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `/mnt/e/image_detection/metadata_registry/json/docreal/` | ✅ Complete | Schema v2.3.0 compliant (per Processing Status section) |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

DocReal contains 251 images: 201 camera-captured distorted and 50 flatbed-scanned ground truth.

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Distorted** | 201 | 201 | 100% | ✅ Complete |
| **Scanned (GT)** | 50 | 50 | 100% | ✅ Complete |
| **Total** | 251 | 251 | 100% | ✅ Complete |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 251 |
| **Distorted Images** | 201 (camera-captured) |
| **Scanned GT Images** | 50 (flatbed scanner) |
| **Variants per Document** | ~4 distorted per scanned (~201/50) |
| **File Format(s)** | PNG |
| **Color Space** | RGB |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
docreal/
├── distorted/           # 201 camera-captured distorted images
│   ├── {doc_id}_{variant}.png
│   └── ...
└── scanned/             # 50 flatbed-scanned ground truth images
    ├── {doc_id}.png
    └── ...
```

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL |
| **Document Types** | Mixed printed documents |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone (distorted), flatbed scanner (GT) |

#### 6. IQA Profile

Camera-captured documents with perspective distortion and warping, paired with flatbed-scanned GT.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured distorted + flatbed-scanned GT |
| **Capture Device** | Camera/smartphone (distorted), flatbed scanner (GT) |
| **Original Quality** | Variable distortion (camera), clean (scanner) |
| **Known Artifacts** | Perspective distortion, warping, lighting variation |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Perspective Distortion** | HIGH | Primary degradation from camera capture |
| **Warping** | HIGH | Document surface deformation |
| **Lighting Variation** | MEDIUM | Camera capture introduces lighting artifacts |
| **Blur** | MEDIUM | Some motion/focus blur expected |
| **Noise** | LOW | Secondary artifact |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Warping distorts text readability |
| **Color Usage** | Mixed | Both B&W and color documents |
| **Multi-Variant** | Yes | Multiple distortion variants per document enable controlled comparison |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | MEDIUM - Small but real-world paired data with MIT license |
| **Unique Characteristics** | Multiple distorted variants per GT; clean MIT license |
| **Complementary Datasets** | AnyPhotoDoc6300 (larger), WarpDoc (distortion types), Doc3D (synthetic) |
| **Benchmark Suitability** | HIGH - Real paired data with scanner GT enables rigorous evaluation |
| **Known Limitations** | Very small (251 images); limited document diversity |

#### 7. Known Issues & Limitations

- **Very Small Dataset**: Only 251 images total (201 distorted + 50 GT) - insufficient for standalone training
- **Limited Document Diversity**: Only 50 unique documents with multiple distorted variants
- **No Explicit Splits**: No train/val/test split provided - user must define
- **No Layout Annotations**: Dataset focused on dewarping, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **Variant Imbalance**: Number of distorted variants per document may be uneven

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{docreal2024,
  title={Robust Document Dewarping via Attention-Enhanced Control Point Prediction},
  author={irisXcoding},
  year={2024},
  url={https://github.com/irisXcoding/DocReal}
}
```

##### Related Works

- [AnyPhotoDoc6300](anyphotodoc6300.md) - Larger dewarping benchmark (6.3K images)
- [WarpDoc](warpdoc.md) - 6 distortion types (1K images)
- [Doc3D](doc3d.md) - Synthetic 3D warped documents (100K images)
- [RealDAE](realdae.md) - Camera document enhancement (same capture paradigm)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Multi-Variant Pairing**: Each scanned GT document has multiple distorted variants (avg ~4)
- **Scanned as GT**: Flatbed-scanned images serve as dewarping ground truth (not digital originals)
- **No Distortion Labels**: Unlike WarpDoc, distortion types are not explicitly categorized

##### 10.2 Implementation Notes

- **Parser Note**: Extract doc_id from filename pattern `{doc_id}_{variant}.png` (distorted) and `{doc_id}.png` (scanned)
- **Quality Computation**: Use SSIM/MS-SSIM/LD between distorted and scanned images for quality scoring
- **Capture Method**: Set `camera_smartphone` for distorted, `scanner_flatbed` for scanned
- **Small Scale**: Best used as evaluation benchmark; combine with larger datasets for training
- **MIT License**: One of the few dewarping datasets with a permissive open-source license

##### 10.3 External Resources

- **DocReal Repository**: [GitHub: irisXcoding/DocReal](https://github.com/irisXcoding/DocReal)
- **Attention-Enhanced Control Point Model**: Associated dewarping model in the repository

#### 10.4 License and Format

| Property | Value |
|----------|-------|
| **License** | MIT |
| **Commercial Use** | Yes |
| **Image Format** | PNG |
| **Color Space** | RGB |

#### 10.5 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_docreal_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.6 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: C (85.3/100) | **Auditor**: claude-opus-4-6
> **Grade Cap**: B -> C (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 82.5 | 18% |  |
| Field Validity | 96.3 | 18% |  |
| Doc Completeness | 100.0 | 6% |  |
| Defect Rate | 90.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **85.3** | | **Grade C** |

**Grade Cap Applied**:
> Grade capped from B to C: label_accuracy=58.3% (min 70%). Per-field label accuracy below 70% means labels are unreliable for training. Must improve enrichment quality before use.

##### 11.2 Key Defects

> **Total**: 6 defects (1 resolved, 5 accepted)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | low | ACCEPTED |  |
| D02 | domain_level1 | medium | ACCEPTED |  |
| D03 | iso639_language | low | ACCEPTED |  |
| D04 | layout_detections | low | ACCEPTED |  |
| D05 | text_has_content | low | ACCEPTED |  |
| D06 | text_scope | medium | RESOLVED |  |

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

##### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/docreal/](../../scripts/audit/results/docreal/)

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Correction/dewarping training (enrichment gaps not blocking).

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 200 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 200 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `resolution` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ Not applicable | - | - | No orientation labels; distorted images lack rotation ground truth |
| MNV4-H2 | skew_reg | ❌ Not applicable | - | - | No geometric skew angle labels provided |
| MNV4-H3 | resolution_quality_reg | 🟡 Secondary | ~201 | Inferred | Camera-captured images have variable resolution; no explicit DPI label |
| SIG-G1-1 | blur_score | 🟡 Secondary | ~201 | Inferred | Some motion/focus blur expected in camera-captured distorted images |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~201 | Inferred | Low noise per IQA profile; camera sensor noise present but secondary |
| SIG-G1-3 | contrast_score | 🟡 Secondary | ~201 | Inferred | Lighting variation from camera capture; no explicit contrast label |
| SIG-G1-4 | skew_score | ❌ Not applicable | - | - | Skew degradation quality score not relevant; dataset is dewarping-focused |
| SIG-G1-5 | compression_score | ❌ Not applicable | - | - | PNG format; no JPEG compression artifacts |
| SIG-G1-6 | overall_quality | 🟡 Secondary | ~201 | Inferred from SSIM vs GT | No direct MOS labels; overall quality inferrable by comparing distorted to scanned GT via SSIM |
| SIG-G2-1 | script_cls | 🟡 Secondary | ~201 | Inferred CJK | Aggregate stats show 100% Hani/zh (Chinese); confirms CJK script presence (note: language detection may be noisy at 200-sample audit) |
| SIG-G3-1 | orientation_cls (post) | ❌ Not applicable | - | - | No orientation labels |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | - | - | No geometric skew labels |
| SIG-G4-1 | handwriting_presence_cls | ➖ Negatives only | ~201 | Implicit NONE class | Printed documents; no handwriting; useful as negative examples |
| SIG-G4-2 | handwriting_legibility_cls | ❌ Not applicable | - | - | No handwriting content |
| SIG-G4-3 | handwriting_content_type_cls | ❌ Not applicable | - | - | No handwriting content |
| SIG-G4-4 | presence_reg | ➖ Negatives only | ~201 | Implicit 0.0 | Printed docs provide zero-handwriting anchor for regression |
| SIG-G4-5 | legibility_reg | ❌ Not applicable | - | - | No handwriting content |
| SIG-G5-1 | capture_method_cls | ✅ Primary | ~201 | camera_smartphone (distorted); scanner_flatbed (50 GT) | Clean capture-method labels from directory structure; both camera and scanner classes represented |
| SIG-G5-2 | shadow_reg | 🟡 Secondary | ~201 | Inferred | Lighting variation from camera capture may include shadow effects; no explicit severity label |
| SIG-G5-3 | warping_reg | ✅ Primary | ~201 | Paired GT (high warping) | Distorted images have perspective distortion and warping; scanned GT provides implicit low-warping anchor; warping severity derivable via SSIM |
| SIG-G5-4 | code_cls | ➖ Negatives only | ~201 | Implicit NONE class | General printed documents; no code-containing pages expected |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | 🟡 Secondary | ~201 | Inferred | Variable camera resolution; same inference path as MNV4-H3 |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | 🟡 Partial | Aggregate stats: 100% CJK (Hani/zh); language detection may be unreliable due to no OCR run; likely Chinese-language documents |
| 2 | Capture method | ✅ Well-covered | Both camera_smartphone (201 distorted) and scanner_flatbed (50 GT) represented |
| 3 | Document domain | 🟡 Partial | GENERAL domain; ~50 unique documents; limited subject diversity |
| 4 | Layout type | ❌ Not present | No layout annotations; DocLayout-YOLO not yet run |
| 5 | Text density | ❌ Not present | Not annotated; no OCR run |
| 6 | Degradation types | ✅ Well-covered | Perspective distortion and warping primary; lighting variation secondary; blur present |
| 7 | Resolution/DPI range | 🟡 Partial | Variable camera resolution; bottleneck field (100% low confidence); no DPI metadata available |
| 8 | Document age | ❌ Not present | All recent captures; no aged or historical material |
| 9 | Text scope | 🟡 Partial | Aggregate stats show 100% page-level text scope |
| 10 | Content flags | ❌ Not present | No content flags; content_flags empty in aggregate stats |
| 11 | Binarization status | ❌ Not present | Not annotated; PNG format (likely full-color RGB) |
| 12 | Artifact types | ✅ Well-covered | Perspective distortion, warping, lighting variation, mild blur and noise all present |
| 13 | Color mode | 🟡 Partial | Mixed B&W and color documents noted; not explicitly labelled per image |
| 14 | Font variety | ❌ Not present | No font metadata; CJK printed documents inferred |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

DocReal is a small (251-image) dewarping benchmark with MIT license whose primary training contribution is to the warping_reg and capture_method_cls heads, providing real paired camera-distorted and flatbed-scanned examples of perspective distortion and warping. At only 201 distorted images the dataset is too small to serve as a standalone training source and is best used as a held-out evaluation benchmark or combined with larger dewarping datasets such as AnyPhotoDoc6300 or Doc3D. The Layer 2 audit grade of C (label_accuracy 58.3%) and 100% unreliable composite category indicate enrichment gaps in domain, language, layout, and resolution fields that must be addressed before using metadata-derived labels for training.
