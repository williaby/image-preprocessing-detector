---
dataset_id: anyphotodoc6300
version: "1.0"
license: GPL-3.0
commercial_use: false
iqa_profiles:
  - perspective_distortion
  - warping
  - lighting_variation
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### AnyPhotoDoc6300 (Document Dewarping Benchmark)

> **Quick Stats**: 6,306 images | Camera-captured | Warped + flat GT pairs | Dewarping benchmark
>
> **License**: GPL-3.0 (dataset, per HuggingFace card); AGPL-3.0 (code repo, per GitHub) | **Commercial Use**: No

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | AnyPhotoDoc6300 |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | hanquansanren et al. |
| **Paper** | [DvD: Decoupled Dewarping](https://github.com/hanquansanren/DvD) |
| **Repository** | [GitHub: hanquansanren/DvD](https://github.com/hanquansanren/DvD) |
| **HuggingFace** | [hanquansanren/AnyPhotoDoc6300](https://huggingface.co/datasets/hanquansanren/AnyPhotoDoc6300) |
| **License** | GPL-3.0 (dataset, per HuggingFace card); AGPL-3.0 (code repo, per GitHub) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Camera-captured warped document images |
| **Images** | PNG | Flat/rectified ground truth images |
| **Supplementary** | README, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Full Dataset** | `anyphotodoc6300/` | Implicit (paired structure) | 6,306 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (user-defined or paired folder structure)

> **Notes**:
>
> - Dataset provides camera-captured warped images paired with flat/rectified ground truth
> - Exact internal split structure to be verified after download
> - Total 6,306 images (warped + corresponding GT pairs)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Filename/directory-based | Document | Warped input paired with flat/rectified GT |
| **Dewarping GT** | Implicit | Document | Flat version serves as dewarping target |

> **Note**: Primary annotation is through paired warped/flat image structure. No explicit quality scores or bounding boxes provided.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace page, GitHub README | Description, citation, download instructions |
| **Image-level** | Filename/directory structure | Pairing information, capture conditions |

##### 2.5 Annotation Schema Details

> **Format**: Paired image structure (warped input + flat/rectified GT)

```text
AnyPhotoDoc6300/
├── warped/            # Camera-captured warped document images (PNG)
│   └── *.png
└── flat/              # Flat/rectified ground truth images (PNG)
    └── *.png

# [NEEDS_VERIFICATION] Exact directory structure after download
# Images are paired by filename correspondence
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to warped or flat image |
| `pair_type` | str | Yes | "warped" or "flat" (from directory/filename) |
| `base_name` | str | Yes | Links paired images |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `paired_file` | High | Filename-based pairing |
| ✅ Capture method | `capture_method` | Medium | Inferred (camera_smartphone) |
| ❌ Quality scores | - | Low | Not provided; compute from pairing (SSIM/MS-SSIM) |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Paired GT |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Corrected/distorted document pairs for dewarping |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (dewarping/correction) |
| **Purpose** | Dewarping benchmark, correction model training |
| **Local Path** | `01_base_data/camera_captured/anyphotodoc6300/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Pair matching required |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Parser Status** | ✅ Available - Parser created, enrichment pending |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `has_warping=True` |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/anyphotodoc6300/` | ✅ Available | PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/anyphotodoc6300_layer2.json` | 🔄 In Progress | Enrichment pending |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

Camera-captured document dewarping benchmark with 6,306 distorted images across 8 layout categories, 3 warping patterns, and 3 lighting conditions.

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Full Dataset** | 6,306 | 0 | 0% | ❌ Not started |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 6,306 |
| **File Format(s)** | PNG |
| **Color Space** | RGB |
| **Annotation Format** | Paired image structure |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
anyphotodoc6300/
├── warped/              # Camera-captured warped documents
│   └── *.png
└── flat/                # Flat/rectified ground truth
    └── *.png

# [NEEDS_VERIFICATION] Exact structure after download
```

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL (scientific papers, magazines, mixed documents) |
| **Document Types** | Diverse printed documents with camera-induced warping |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone capture (warped), digital/flatbed (GT) |

#### 6. IQA Profile

Documents exhibit real-world camera capture degradations including perspective distortion, surface warping, and uneven lighting. Primary value is as paired GT for correction model training.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured documents (real-world warping) |
| **Capture Device** | Camera/smartphone |
| **Original Quality** | Variable (real camera capture conditions) |
| **Known Artifacts** | Perspective distortion, warping, lighting variation |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Perspective Distortion** | HIGH | Primary degradation type - camera angle variation |
| **Warping** | HIGH | Document surface deformation from capture |
| **Lighting Variation** | HIGH | Uneven illumination from camera capture |
| **Blur** | MEDIUM | Some motion/focus blur expected |
| **Noise** | MEDIUM | Camera sensor noise |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Warping distorts text proportionally |
| **Line/Grid Density** | Variable | Grid structures sensitive to warping |
| **Color Usage** | Mixed (B&W and color) | Color documents in source material |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large paired dataset for dewarping correction |
| **Unique Characteristics** | Camera-captured warped documents with flat GT |
| **Complementary Datasets** | Doc3D (synthetic warping), WarpDoc, DocReal |
| **Benchmark Suitability** | HIGH - Paired GT enables quantitative evaluation (SSIM/MS-SSIM/LD) |
| **Known Limitations** | GPL-3.0 (dataset) and AGPL-3.0 (code) both restrict commercial use; AGPL-3.0 also requires network-use disclosure |

#### 7. Known Issues & Limitations

- **License Clarified (2026-02-24)**: Dataset is GPL-3.0 (per HuggingFace card); code repo (DvD) is AGPL-3.0 (per GitHub). No separate dataset license file exists. Both restrict commercial use.
- **No Explicit Quality Scores**: Quality must be computed from paired comparison (SSIM, MS-SSIM)
- **No Layout Annotations**: Dataset focused on dewarping, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **Domain Coverage**: [NEEDS_VERIFICATION] - Verify diversity of document types after download

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{dvd2024,
  title={DvD: Decoupled Dewarping},
  author={hanquansanren},
  year={2024},
  url={https://github.com/hanquansanren/DvD}
}
```

##### Related Works

- [Doc3D](doc3d.md) - Synthetic 3D warped documents (100K images)
- [WarpDoc](warpdoc.md) - Document dewarping with 6 distortion types
- [DocReal](docreal.md) - Small-scale real dewarping benchmark

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Paired Image Structure**: Warped and flat images must be processed together for quality comparison
- **GT Quality**: Flat/rectified GT images serve as dewarping targets
- **No Deformation Parameters**: Warping severity not explicitly annotated (compute from image comparison)

##### 10.2 Implementation Notes

- **Parser Note**: Parser should extract pair type from directory/filename structure
- **Quality Computation**: Use SSIM/MS-SSIM/LD between warped and flat images for quality scoring
- **Capture Method**: Set `camera_smartphone` for warped images; GT images are flat/digital

##### 10.3 External Resources

- **DvD Model**: Decoupled dewarping model available at [GitHub: hanquansanren/DvD](https://github.com/hanquansanren/DvD)
- **HuggingFace**: [hanquansanren/AnyPhotoDoc6300](https://huggingface.co/datasets/hanquansanren/AnyPhotoDoc6300)

#### 10.4 License and Format

| Property | Value |
|----------|-------|
| **License** | GPL-3.0 (dataset, per HuggingFace card); AGPL-3.0 (code repo, per GitHub) |
| **Commercial Use** | No |
| **Image Format** | PNG |
| **Color Space** | RGB |

#### 10.5 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_anyphotodoc6300_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.6 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (90.7/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 84.8 | 18% |  |
| Field Validity | 100.0 | 18% |  |
| Doc Completeness | 100.0 | 6% |  |
| Defect Rate | 94.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **90.7** | | **Grade B** |

##### 11.2 Key Defects

> **Total**: 6 defects (2 resolved, 2 accepted, 2 partial)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | low | RESOLVED |  |
| D02 | domain_level1 | low | PARTIALLY_RESOLVED |  |
| D03 | iso639_language | low | PARTIALLY_RESOLVED |  |
| D04 | layout_detections | low | ACCEPTED |  |
| D05 | text_has_content | low | ACCEPTED |  |
| D06 | text_scope | medium | RESOLVED |  |

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 75.0%

##### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/anyphotodoc6300/](../../scripts/audit/results/anyphotodoc6300/)

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Correction/dewarping training (enrichment gaps not blocking).

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 6,306 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 6,306 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `resolution` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ | 0 | N/A | No explicit orientation GT; camera angle varies unpredictably |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | Warping ≠ page skew; no skew GT |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | N/A | No resolution quality labels |
| SIG-G1-1 | blur_score | 🟡 | ~1,500 | tier_3_heuristic | Some motion/focus blur from camera capture; warping is primary degradation |
| SIG-G1-2 | noise_score | 🟡 | ~1,500 | tier_3_heuristic | Camera sensor noise (warped images only; flat GT is clean) |
| SIG-G1-3 | contrast_score | 🟡 | ~3,100 | tier_3_heuristic | 3 lighting conditions including low light; paired GT enables quality comparison |
| SIG-G1-4 | skew_score | ❌ | 0 | N/A | No quality-based skew degradation |
| SIG-G1-5 | compression_score | ❌ | 0 | N/A | PNG format (lossless) — no compression artifacts |
| SIG-G1-6 | overall_quality | 🟡 | ~3,100 | tier_3_heuristic | Wide quality range: degraded camera to pristine flat GT |
| SIG-G2-1 | script_cls | ➖ | ~500 | derived | Domain (scientific papers, magazines) suggests Latn-dominant; no explicit script labels |
| SIG-G3-1 | orientation_cls | ❌ | 0 | N/A | No orientation GT |
| SIG-G3-2 | skew_reg | ❌ | 0 | N/A | No skew GT |
| SIG-G4-1 | handwriting_presence_cls | ➖ | ~3,100 | derived | Printed documents → reliable NONE-class negatives |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | N/A | No handwriting |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | N/A | No handwriting |
| SIG-G4-4 | presence_reg | ➖ | ~3,100 | derived | 0.0 area ratio (all printed) |
| SIG-G4-5 | legibility_reg | ❌ | 0 | N/A | No handwriting |
| SIG-G5-1 | capture_method_cls | ✅ | ~3,100 | tier_1_annotation | 3,153 camera_smartphone images (warped set); inferred from dataset design |
| SIG-G5-2 | shadow_reg | 🟡 | ~500 | tier_3_heuristic | Uneven lighting conditions create cast shadows in subset of warped images |
| SIG-G5-3 | warping_reg | ✅ | ~3,100 | derived | Largest real camera-warped pool; severity computed via SSIM vs flat GT pairs |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | No code content labels |
| SIG-G5-5 | resolution_quality_reg | ❌ | 0 | N/A | No resolution quality labels |

Contribution legend: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | 🟡 | Domain suggests Latn-dominant (scientific papers, magazines); no explicit script labels |
| 2 | Capture method | ✅ | camera_smartphone (warped set ~3,153); flat GT reference images |
| 3 | Document domain | 🟡 | GENERAL — diverse: scientific papers, magazines, mixed documents (8 layout categories) |
| 4 | Layout type | ✅ | Mixed (8 layout categories across 3 warping patterns) |
| 5 | Text density | ✅ | Variable (document type diversity) |
| 6 | Degradation types | ✅ | Perspective distortion, surface warping, uneven lighting, motion blur, noise |
| 7 | Resolution/DPI range | ✅ | Camera-native (PNG, variable DPI) |
| 8 | Document age | ✅ | Modern documents |
| 9 | Text scope | ✅ | Document-level (full-page camera captures) |
| 10 | Content flags | 🟡 | No confirmed has_handwriting/has_code/has_table flags; mixed document types |
| 11 | Binarization status | ❌ | All color RGB PNG |
| 12 | Artifact types | ✅ | Surface warping (primary), perspective distortion, uneven lighting, shadow |
| 13 | Color mode | ✅ | Color |
| 14 | Font variety | ✅ | Varied — diverse document types (scientific papers, magazines, mixed) |

Coverage: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

AnyPhotoDoc6300 is the **primary source for `warping_reg` head training**, providing 3,153+ real camera-captured warped documents with flat GT pairs that enable SSIM-derived severity scoring (warping severity 0–1 must be computed from image pair comparison before training). It is also a significant contributor to `capture_method_cls` (~3.1K camera images) and IQA heads (contrast/blur from 3 lighting conditions × 3 warping patterns × 8 layout categories). Warping severity labels are not provided natively and must be pre-computed via `scripts/label_warping_severity.py`. The GPL-3.0 applies to the associated code repository; the dataset terms should be verified separately before commercial deployment.
