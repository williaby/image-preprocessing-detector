---
dataset_id: warpdoc
version: "1.0"
license: Unspecified
commercial_use: false
iqa_profiles:
  - perspective_distortion
  - fold
  - curve
  - rotation
  - lighting_variation
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### WarpDoc (Document Dewarping with 6 Distortion Types)

> **Quick Stats**: 1,020 camera images | 6 distortion types | Dewarping benchmark | CVPR 2022
>
> **License**: Unspecified | **Commercial Use**: Unknown (verify with authors)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | WarpDoc |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | SG-ViLab |
| **Paper** | [Fourier Document Restoration for Robust Document Dewarping and Recognition (CVPR 2022)](https://sg-vilab.github.io/event/warpdoc/) |
| **Site** | [https://sg-vilab.github.io/event/warpdoc/](https://sg-vilab.github.io/event/warpdoc/) |
| **License** | Unspecified (verify with authors) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG / PNG | Camera-captured warped document images |
| **Images** | JPG / PNG | Digital document images (added June 2022) |
| **Supplementary** | Website, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Full Dataset** | `warpdoc/` | Implicit (distortion type folders) | 1,020 camera images | ✅ |
| **Digital Extension** | `warpdoc/digital/` | [NEEDS_VERIFICATION] | [NEEDS_VERIFICATION] | ⚠️ |

**Split Organization Pattern**: `by_folder` (distortion type subfolders)

> **Notes**:
>
> - 1,020 camera-captured images across 6 distortion types
> - Digital document images added in June 2022 update
> - Paired GT may be available (verify with digital document extension)
> - Exact internal split structure to be verified after download

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Distortion Type** | Directory-based | Document | 6 types: Fold, Curved, Incomplete, Random, Rotating, Perspective |
| **Paired Images** | [NEEDS_VERIFICATION] | Document | Digital documents may serve as GT |

> **Note**: Primary annotation is distortion type classification via directory structure.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Project website, Paper | Description, citation, distortion taxonomy |
| **Image-level** | Directory structure | Distortion type classification |

##### 2.5 Annotation Schema Details

> **Format**: Directory-based distortion type classification

```text
WarpDoc/
├── Fold/              # Folded document images
│   └── *.jpg
├── Curved/            # Curved/bent document images
│   └── *.jpg
├── Incomplete/        # Partially visible document images
│   └── *.jpg
├── Random/            # Random deformation patterns
│   └── *.jpg
├── Rotating/          # Rotation-distorted images
│   └── *.jpg
├── Perspective/       # Perspective-distorted images
│   └── *.jpg
└── digital/           # Digital GT documents (added June 2022)
    └── *.jpg

# [NEEDS_VERIFICATION] Exact directory structure after download
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to warped document image |
| `distortion_type` | str | Yes | One of 6 types (from directory name) |
| `is_digital` | bool | No | True for digital GT images |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Distortion type | `distortion_type` | High | 6-class from directory name |
| ✅ Capture method | `capture_method` | Medium | Inferred (camera_smartphone) |
| ⚠️ Paired images | `paired_file` | Medium | Digital GT may enable pairing |
| ❌ Quality scores | - | Low | Not provided |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Paired GT |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Warped/flat document pairs, 6 documented distortion types |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (dewarping/distortion correction) |
| **Purpose** | Dewarping benchmark, distortion classification training |
| **Local Path** | `01_base_data/camera_captured/warpdoc/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Distortion type extraction from directory structure |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Parser Status** | ⚠️ Partial - Parser created but enrichment not yet run |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `distortion_type` from directory |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/warpdoc/` | ✅ Available | JPG/PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/warpdoc_layer2.json` | 🔄 In Progress | Enrichment pending |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

1,020 camera-captured warped document images across 6 distortion types (fold, curve, incomplete, random, rotating, perspective). 170 images per distortion category.

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Full Dataset** | 1,020 camera images | 0 | 0% | ❌ Not started |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 1,020 (camera-captured) + digital extension |
| **Distortion Types** | 6 (Fold, Curved, Incomplete, Random, Rotating, Perspective) |
| **File Format(s)** | JPG / PNG |
| **Color Space** | RGB |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
warpdoc/
├── Fold/              # Folded document images
├── Curved/            # Curved/bent document images
├── Incomplete/        # Partially visible documents
├── Random/            # Random deformation patterns
├── Rotating/          # Rotation-distorted images
├── Perspective/       # Perspective-distorted images
└── digital/           # Digital GT (added June 2022)

# [NEEDS_VERIFICATION] Exact structure and counts per type
```

##### 5.1 Class/Category Distribution

| Distortion Type | Count | Percentage | Description |
|-----------------|-------|------------|-------------|
| **Fold** | ~170 | ~17% | Paper folding deformation |
| **Curved** | ~170 | ~17% | Curved/bent surface |
| **Incomplete** | ~170 | ~17% | Partially visible document |
| **Random** | ~170 | ~17% | Random deformation pattern |
| **Rotating** | ~170 | ~17% | Rotation distortion |
| **Perspective** | ~170 | ~17% | Camera angle perspective |

> **Note**: Exact per-type counts to be verified after download. Assuming roughly equal distribution across 6 types for 1,020 images.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL (scientific papers, magazines, envelopes) |
| **Document Types** | Diverse printed documents with controlled distortions |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone capture with 6 distortion types |

#### 6. IQA Profile

Camera-captured documents with controlled geometric distortions. Primary value for dewarping/correction model training, not IQA benchmarking.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured documents with controlled distortions |
| **Capture Device** | Camera/smartphone |
| **Original Quality** | Variable (controlled distortion types) |
| **Known Artifacts** | 6 distortion types: fold, curve, incomplete, random, rotating, perspective |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Perspective Distortion** | HIGH | Dedicated distortion category |
| **Fold** | HIGH | Dedicated distortion category - paper folding |
| **Curve** | HIGH | Dedicated distortion category - surface bending |
| **Rotation** | HIGH | Dedicated distortion category |
| **Lighting Variation** | MEDIUM | Camera capture introduces lighting artifacts |
| **Blur** | MEDIUM | Some motion/focus blur expected |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Distortion affects text readability |
| **Document Types** | Scientific papers, magazines, envelopes | Diverse content |
| **Color Usage** | Mixed | Both B&W and color documents |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Unique 6-type distortion taxonomy for classification |
| **Unique Characteristics** | 6 distinct, labeled distortion types (only dataset with this granularity) |
| **Complementary Datasets** | Doc3D (synthetic), AnyPhotoDoc6300 (larger scale), DocReal |
| **Benchmark Suitability** | HIGH - CVPR 2022 paper benchmark with distortion classification |
| **Known Limitations** | Small (1,020 images); unspecified license |

#### 7. Known Issues & Limitations

- **License Unspecified**: No explicit license - verify with authors/project site before commercial use
- **Small Dataset**: Only 1,020 camera images - may need augmentation for training
- **No Layout Annotations**: Dataset focused on dewarping, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **Paired GT Uncertain**: Digital extension (June 2022) may provide GT, but pairing is unverified
- **Uneven Type Counts**: Exact distribution across 6 distortion types needs verification

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{xue2022fourier,
  title={Fourier Document Restoration for Robust Document Dewarping and Recognition},
  author={Xue, Chao and others},
  booktitle={CVPR},
  year={2022}
}
```

##### Related Works

- [Doc3D](doc3d.md) - Synthetic 3D warped documents (100K images)
- [AnyPhotoDoc6300](anyphotodoc6300.md) - Larger dewarping benchmark (6.3K images)
- [DocReal](docreal.md) - Small-scale real dewarping benchmark (251 images)

#### 10. Dataset-Specific Notes

##### 10.1 Distortion Taxonomy

WarpDoc defines 6 distinct distortion types, making it unique for distortion classification training:

| Type | Description | Physical Cause |
|------|-------------|----------------|
| **Fold** | Sharp crease deformation | Paper folded along a line |
| **Curved** | Smooth surface bending | Document on curved surface or held by hand |
| **Incomplete** | Partially visible content | Document extends beyond camera field of view |
| **Random** | Irregular deformation | Crumpled or arbitrarily deformed paper |
| **Rotating** | In-plane rotation | Document rotated relative to camera |
| **Perspective** | Keystone distortion | Camera at non-perpendicular angle to document |

##### 10.2 Implementation Notes

- **Parser Note**: Parser should extract distortion_type from directory name
- **Digital Extension**: June 2022 update added digital documents - check if these serve as paired GT
- **Distortion Classification**: Can be used for multi-class distortion type prediction (6 classes)
- **Small Scale**: Consider combining with Doc3D or AnyPhotoDoc6300 for sufficient training volume

##### 10.3 External Resources

- **Project Website**: [https://sg-vilab.github.io/event/warpdoc/](https://sg-vilab.github.io/event/warpdoc/)
- **Fourier Document Restoration Model**: Associated dewarping model from CVPR 2022

#### 10.4 License and Format

| Property | Value |
|----------|-------|
| **License** | Unspecified |
| **Commercial Use** | Unknown (verify with authors) |
| **Image Format** | JPG / PNG |
| **Color Space** | RGB |

#### 10.5 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_warpdoc_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.6 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: C (77.9/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 82.5 | 18% |  |
| Field Validity | 96.3 | 18% |  |
| Doc Completeness | 100.0 | 6% |  |
| Defect Rate | 94.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **77.9** | | **Grade C** |

##### 11.2 Key Defects

> **Total**: 6 defects (3 resolved, 3 accepted)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | low | ACCEPTED |  |
| D02 | domain_level1 | medium | RESOLVED |  |
| D03 | iso639_language | low | RESOLVED |  |
| D04 | layout_detections | low | ACCEPTED |  |
| D05 | text_has_content | low | ACCEPTED |  |
| D06 | text_scope | medium | RESOLVED |  |

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

##### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/warpdoc/](../../scripts/audit/results/warpdoc/)

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Correction/dewarping training (enrichment gaps not blocking).

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 1,020 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 1,020 | 100.0% |

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
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~1,020 | Synthetic rotation | 6 distortion types include rotation; synthetic 90°/180°/270° augmentation viable |
| MNV4-H2 | skew_reg | ❌ Not applicable | - | - | Perspective and rotation are geometric but not OCR-angle skew; no skew angle GT |
| MNV4-H3 | resolution_quality_reg | ❌ Not applicable | - | - | No resolution quality labels; camera capture with no DPI metadata |
| SIG-G1-1 | blur_score | 🟡 Secondary | ~1,020 | Inferred | Camera-captured; some motion/focus blur expected; no explicit blur labels |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~1,020 | Inferred | Camera noise incidental; not primary degradation signal |
| SIG-G1-3 | contrast_score | 🟡 Secondary | ~1,020 | Inferred | Lighting variation present in camera captures; no explicit contrast labels |
| SIG-G1-4 | skew_score | ❌ Not applicable | - | - | skew_score is a quality degradation metric (0-1); no such labels present |
| SIG-G1-5 | compression_score | ❌ Not applicable | - | - | JPG artifacts incidental; no compression quality labels |
| SIG-G1-6 | overall_quality | 🟡 Secondary | ~1,020 | Inferred | Shadow-free images usable as "high quality" reference; warped as "degraded" |
| SIG-G2-1 | script_cls | ➖ Negatives only | ~1,020 | Inferred Latin | 100% Latin (en) per stats; useful as Latin examples but no multi-script signal |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~1,020 | Synthetic rotation | Rotating distortion type maps directly; other types at canonical orientation |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | - | - | No sub-degree skew angle ground truth; Perspective/Fold are not OCR skew |
| SIG-G4-1 | handwriting_presence_cls | ➖ Negatives only | ~1,020 | Inferred | Printed documents only (scientific papers, magazines, envelopes); no handwriting |
| SIG-G4-2 | handwriting_legibility_cls | ❌ Not applicable | - | - | No handwriting present |
| SIG-G4-3 | handwriting_content_type_cls | ❌ Not applicable | - | - | No handwriting present |
| SIG-G4-4 | presence_reg | ➖ Negatives only | ~1,020 | Inferred | Printed documents → 0.0 handwriting presence score |
| SIG-G4-5 | legibility_reg | ❌ Not applicable | - | - | No handwriting present |
| SIG-G5-1 | capture_method_cls | ✅ Primary | 1,020 | Hard label | 100% camera_smartphone per stats; high-confidence label |
| SIG-G5-2 | shadow_reg | ❌ Not applicable | - | - | No shadow degradation; lighting variation is incidental, not annotated shadow |
| SIG-G5-3 | warping_reg | ✅ Primary | ~1,020 | 6-class distortion type | Core warping dataset; Fold, Curved, Perspective, Random, Incomplete, Rotating all map to warping severity; no continuous 0-1 severity GT — needs derivation from distortion class + paired GT pixel difference |
| SIG-G5-4 | code_cls | ❌ Not applicable | - | - | Scientific papers/magazines may contain code but no code annotations |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | ❌ Not applicable | - | - | No resolution quality labels; DPI metadata not available |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ➖ Latin only | 100% Latn (en) per stats; no multi-script coverage |
| 2 | Capture method | ✅ Well-covered | 100% camera_smartphone (1,020 images) |
| 3 | Document domain | 🟡 Partial | 100% GENERAL; diverse types (scientific papers, magazines, envelopes) but no domain breakdown |
| 4 | Layout type | ❌ Not present | No layout annotations; varied real-world layouts but uncharacterized |
| 5 | Text density | ❌ Not present | No text density labels; diverse documents imply variable density |
| 6 | Degradation types | ✅ Well-covered | 6 geometric distortion types: Fold, Curved, Incomplete, Random, Rotating, Perspective; ~170 per type |
| 7 | Resolution/DPI range | ❌ Not present | No DPI metadata; camera-captured at unknown native resolution |
| 8 | Document age | ❌ Not present | No document age annotations; mixed modern documents implied |
| 9 | Text scope | 🟡 Partial | 100% page-level scope per stats; no word/line granularity |
| 10 | Content flags | ❌ Not present | No content flags in L2 metadata (tables, figures, formulas not annotated) |
| 11 | Binarization status | ❌ Not present | RGB color documents; not binarized |
| 12 | Artifact types | ✅ Well-covered | 6 controlled distortion types provide high-quality artifact taxonomy; lighting variation secondary |
| 13 | Color mode | 🟡 Partial | RGB per stats; mixed B&W and color documents per dataset description but not labeled |
| 14 | Font variety | ❌ Not present | No font annotations; scientific papers and magazines imply varied fonts |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

WarpDoc serves as the primary labeled source for the `warping_reg` head (SIG-G5-3) and `capture_method_cls` head (SIG-G5-1), providing 1,020 camera-captured documents with 6 controlled geometric distortion types. Its chief constraint is the absence of continuous warping severity scores — the distortion class labels (Fold/Curved/Perspective/etc.) must be converted to a 0-1 severity proxy, likely via pixel-wise difference between warped input and the digital GT extension, before this dataset can contribute hard labels to `warping_reg` training. License is unspecified; verify with SG-ViLab before using in any commercial pipeline.
