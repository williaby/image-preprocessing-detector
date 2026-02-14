---
dataset_id: docalign12k
version: "2.0"
license: Unspecified
commercial_use: false
iqa_profiles:
  - perspective_distortion
  - alignment
  - warping
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### DocAlign12K (Document Registration/Alignment)

> **Quick Stats**: 30,338 images | Synthetically distorted + flat GT | Paired GT | Document dewarping/alignment
>
> **License**: Unspecified | **Commercial Use**: Unknown (verify with authors)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DocAlign12K |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Last Updated** | 2023 |
| **Maintainer** | Jiaxin Zhang et al. (South China University of Technology) |
| **Paper** | [DocAligner: Annotating Real-World Photographic Document Images (2023)](https://github.com/ZZZHANG-jx/DocAligner) |
| **Repository** | [GitHub: ZZZHANG-jx/DocAligner](https://github.com/ZZZHANG-jx/DocAligner) |
| **License** | Unspecified (verify with authors) |
| **Commercial Use** | Unknown (verify with authors) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Synthetically distorted document images (input) |
| **Images** | JPG | Flat/rectified ground truth images (paired) |
| **Images** | JPG | Shadow overlay images (543) |
| **Split Lists** | TXT | `train_docalign12k.txt` (30,338 lines), `test.txt` (499 lines) |
| **Supplementary** | README, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `distorted_hard/{1-14}/` | `train_docalign12k.txt` (file list) | 30,338 | ✅ |
| **Test** | `distorted_hard/{1-14}/` | `test.txt` (file list) | 499 | ✅ |

**Split Organization Pattern**: `by_file_list` (txt files listing `{group}/{image_id}` paths)

> **Notes**:
>
> - Train list: 30,338 entries; test list: 499 entries (overlap: train file contains all images)
> - No validation split provided
> - Both distorted and flat directories contain same 14 distortion groups with identical filenames
> - Each distorted image has a paired flat GT at the same relative path under `flat/`
> - 543 additional shadow overlay images in `shadows/` directory

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Directory-based | Document | Distorted input paired with flat GT by matching path |
| **Distortion Groups** | Directory structure | Document | 14 numbered groups (1-14) representing distortion severity/type |
| **Shadow Overlays** | Separate directory | Document | 543 shadow images for augmentation |

> **Note**: Primary annotation is through paired image structure. No explicit quality scores, bounding boxes, or displacement maps in our copy. The original dataset includes `forwardmap_hard/` (forward displacement NPY maps) but these are not present on disk.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README, Paper | Description, citation, download instructions |
| **Image-level** | Directory structure | Distortion group, pairing information |
| **Split-level** | `train_docalign12k.txt`, `test.txt` | File lists defining train/test membership |

##### 2.5 Annotation Schema Details

> **Format**: Paired image structure (distorted input + flat GT) in numbered distortion groups

```text
docalign12k/
├── distorted_hard/          # Synthetically distorted document images
│   ├── 1/                   # Distortion group 1 (2,000 images)
│   │   └── *.jpg
│   ├── 2/                   # Distortion group 2 (2,000 images)
│   │   └── *.jpg
│   ├── ...                  # Groups 3-13 (2,000 each)
│   └── 14/                  # Distortion group 14 (4,338 images)
│       └── *.jpg
├── flat/                    # Rectified ground truth (paired)
│   ├── 1/                   # Same structure, same filenames
│   │   └── *.jpg
│   ├── ...
│   └── 14/
│       └── *.jpg
├── shadows/                 # Shadow overlay images (543)
│   └── *.jpg
├── train_docalign12k.txt    # Train split file list (30,338 entries)
└── test.txt                 # Test split file list (499 entries)
```

**Pairing Rule**: `distorted_hard/{N}/{filename}` <-> `flat/{N}/{filename}` (same filename in matching numbered subdirectory)

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to distorted or flat image |
| `image_type` | str | Yes | `input_distorted`, `ground_truth`, or `shadow_overlay` (from directory) |
| `distortion_group` | str | Yes | Group number 1-14 (from directory) |
| `base_filename` | str | Yes | Links paired images across distorted/flat |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `ground_truth_path` | High | Path-based pairing across distorted/flat |
| ✅ Distortion groups | `distortion_group` | High | From numbered subdirectories (1-14) |
| ✅ Image type | `image_type` | High | From top-level directory name |
| ✅ Capture method | `capture_method` | High | `synthetic` (all images are synthetically distorted) |
| ✅ Expected degradations | `expected_degradations` | Medium | `perspective_distortion`, `misalignment`, `warping` |
| ❌ Quality scores | - | Low | Not provided; compute from paired SSIM |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (alignment/registration correction) |
| **Purpose** | Document alignment training, dewarping correction |
| **Local Path** | `01_base_data/correction/docalign12k/` |
| **Subset Used** | `distorted_hard/` images only (flat/ used as GT reference) |
| **Preprocessing** | Pair matching via directory structure |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`Docalign12KParser`](../../../src/image_preprocessing_detector/annotation/parsers/correction/docalign12k.py) |
| **Parser Status** | ✅ Complete - Parser implemented and base metadata generated |
| **Config Entry** | [`DATASET_CONFIGS["docalign12k"]`](../../../src/image_preprocessing_detector/annotation/config/datasets.py) |
| **Layer 1 Fields** | `source`, `capture_method`, `correction_task`, `image_type`, `distortion_group`, `is_degraded`, `has_ground_truth`, `ground_truth_path`, `expected_degradations` |
| **Layer 2 Auto-Derived** | `capture_method=synthetic`, `content_type=printed`, `text_scope=page` |

> **Parser Reference**: Pattern `distorted_hard/**/*.jpg` processes only distorted inputs. Flat/GT images are referenced via `ground_truth_path` label.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/docalign12k/` | ✅ Available | 30,338 distorted + 30,338 flat + 543 shadows |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/docalign12k_metadata.json` | ✅ Base metadata | 30,338 samples, parser-generated (189 MB) |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 30,338 | 30,338 | 100% | ✅ Base metadata |
| **Test** | 499 | 499 | ~100% | ✅ Base metadata |
| **Total** | 30,338 | 30,338 | 100% | ✅ Base metadata |

> **Note**: The 30,338 figure is the total distorted images. The test.txt file lists 499 as the test subset. Train/test overlap needs verification (train list may be superset of all images including test).

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Distorted Images** | 30,338 |
| **Total Flat GT Images** | 30,338 |
| **Shadow Overlay Images** | 543 |
| **Total Images on Disk** | 61,219 (distorted + flat + shadows) |
| **Distortion Groups** | 14 (groups 1-13: 2,000 each; group 14: 4,338) |
| **Test Split** | 499 (per `test.txt`) |
| **File Format(s)** | JPG |
| **Color Space** | RGB |
| **Annotation Format** | Paired image structure (directory-based) |
| **Total Size on Disk** | 18 GB |

##### 4.3 Text Statistics

> **Availability**: ❌ Not Available - No ground truth text provided in source dataset. OCR extraction not yet run.

##### Directory Structure

```text
docalign12k/
├── distorted_hard/          # 30,338 synthetically distorted images
│   ├── 1/                   # 2,000 images
│   ├── 2/                   # 2,000 images
│   ├── ...                  # Groups 3-13: 2,000 each
│   └── 14/                  # 4,338 images
├── flat/                    # 30,338 rectified ground truth images
│   ├── 1/ ... 14/           # Same structure as distorted_hard/
├── shadows/                 # 543 shadow overlay images
├── train_docalign12k.txt    # Train file list (30,338 entries)
└── test.txt                 # Test file list (499 entries)
```

##### Baseline Quality Metrics

> **Source**: [NEEDS_PROFILING] - Empirical profiling not yet run on this dataset.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL (UNK in metadata - needs LLM enrichment) |
| **Document Types** | Mixed printed documents with synthetic geometric distortion |
| **Language(s)** | Unknown (`und` in metadata - needs LLM enrichment) |
| **Acquisition Method** | Synthetic distortion of document images (NOT camera capture) |

##### 5.1 Class/Category Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Distortion Group 1 | 2,000 | 6.6% |
| Distortion Group 2 | 2,000 | 6.6% |
| Distortion Group 3 | 2,000 | 6.6% |
| Distortion Group 4 | 2,000 | 6.6% |
| Distortion Group 5 | 2,000 | 6.6% |
| Distortion Group 6 | 2,000 | 6.6% |
| Distortion Group 7 | 2,000 | 6.6% |
| Distortion Group 8 | 2,000 | 6.6% |
| Distortion Group 9 | 2,000 | 6.6% |
| Distortion Group 10 | 2,000 | 6.6% |
| Distortion Group 11 | 2,000 | 6.6% |
| Distortion Group 12 | 2,000 | 6.6% |
| Distortion Group 13 | 2,000 | 6.6% |
| Distortion Group 14 | 4,338 | 14.3% |
| Shadow Overlays | 543 | 1.8% |

##### 5.3 Language & Script Coverage

> **Status**: Unknown - all samples currently `und`/`Zyyy` in metadata. Needs LLM enrichment to determine actual language and script distribution. Given the synthetic distortion methodology, source documents likely span multiple languages.

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Synthetically distorted documents with flat rectified GT |
| **Capture Device** | N/A (synthetic distortion pipeline) |
| **Original Quality** | Variable (depends on source document quality before distortion) |
| **Known Artifacts** | Perspective distortion, warping, misalignment, shadows (subset) |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Perspective Distortion** | HIGH | Primary degradation - synthetic geometric warping |
| **Warping** | HIGH | Non-rigid document deformation |
| **Alignment** | HIGH | Core focus - document registration errors |
| **Shadows** | MEDIUM | 543 shadow overlay images in dedicated subset |
| **Blur** | LOW | Secondary artifact from resampling during distortion |
| **Noise** | LOW | Not a primary degradation type |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Distortion affects text readability |
| **Line/Grid Density** | Variable | Alignment errors visible on structured content |
| **Color Usage** | Mixed | Color documents in source material |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large paired dataset for alignment/dewarping correction |
| **Unique Characteristics** | 14 distortion groups with paired flat GT, shadow overlays |
| **Complementary Datasets** | [RealDAE](realdae.md) (enhancement), [AnyPhotoDoc6300](anyphotodoc6300.md) (dewarping), [WarpDoc](warpdoc.md) (warping) |
| **Benchmark Suitability** | HIGH - Pre-split train/test, enables quantitative evaluation via SSIM/MS-SSIM |
| **Known Limitations** | Unspecified license; synthetic distortion only (no real camera capture artifacts) |

#### 7. Known Issues & Limitations

- **License Unspecified**: No explicit license provided - contact authors before commercial use
- **No Explicit Quality Scores**: Quality must be computed from paired comparison (SSIM/MS-SSIM)
- **No Layout Annotations**: Dataset focused on alignment, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **No Validation Split**: Test list has only 499 entries; no separate validation set
- **Same Authors as RealDAE**: Jiaxin Zhang et al. - may share similar methodology/biases
- **Synthetic Only**: All distortions are synthetically generated; no real camera-capture artifacts
- **Missing Displacement Maps**: `forwardmap_hard/` NPY files referenced in paper not present on disk

##### Layer 2 Audit Findings

- **D01**: Documentation claimed 12,000 images / camera-captured; actual is 30,338 / synthetic distortion (RESOLVED in doc v2.0)
- **D02**: Directory structure documented incorrectly (`train/input/` vs actual `distorted_hard/{1-14}/`) (RESOLVED in doc v2.0)
- **D03**: Local path documented as `camera_captured/` vs actual `correction/` (RESOLVED in doc v2.0)
- **D04**: 11/13 v2.3.0 prescreening fields missing enrichment (domain, language, script, layout, content flags, orientation, color mode, handwriting, quality MOS) (OPEN - needs enrichment pipeline)

#### 8. Representative Samples

> Placeholder - To be populated during VLM Phase 6 inspection.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{zhang2023docaligner,
  title={DocAligner: Annotating Real-World Photographic Document Images},
  author={Zhang, Jiaxin and others},
  year={2023},
  url={https://github.com/ZZZHANG-jx/DocAligner}
}
```

##### Related Works

- [RealDAE](realdae.md) - Camera document enhancement (same research group)
- [AnyPhotoDoc6300](anyphotodoc6300.md) - Document dewarping benchmark
- [DocReal](docreal.md) - Small-scale real dewarping benchmark
- [WarpDoc](warpdoc.md) - Document warping dataset

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Paired Image Structure**: Distorted and flat images must be processed together for quality comparison
- **Synthetic Distortion**: GT images are flat/rectified versions, distortions are synthetically applied
- **No Distortion Parameters**: Distortion severity per group not explicitly documented; group 14 has more images (4,338 vs 2,000) suggesting different characteristics
- **Shadow Subset**: The 543 shadow images are a separate augmentation set, not paired with flat GT

##### 10.2 Implementation Notes

- **Parser**: [`Docalign12KParser`](../../../src/image_preprocessing_detector/annotation/parsers/correction/docalign12k.py) extracts distortion group, image type, and pairing info from directory structure
- **Capture Method**: Set `synthetic` (NOT `camera_smartphone` as originally documented)
- **Quality Computation**: Use SSIM/MS-SSIM between distorted and paired flat GT for quality scoring
- **Config Pattern**: `distorted_hard/**/*.jpg` processes only distorted inputs; flat/ referenced as GT
- **Same Research Group as RealDAE**: May use similar base document sources

##### 10.3 External Resources

- **DocAligner Model**: Document alignment model available at [GitHub: ZZZHANG-jx/DocAligner](https://github.com/ZZZHANG-jx/DocAligner)

---

#### 11. Layer 2 Audit Summary

> **Status**: Audit in progress. Phase 0 (Paper Review) complete. Phases 1-2 (automated prescreening + schema compliance) pending execution.

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-13 | **Grade**: Pending | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | TBD | 0.25 | Expected low (~15%) due to missing enrichments |
| Field Validity | TBD | 0.25 | Pending Phase 2 execution |
| Doc Completeness | TBD | 0.15 | Improved with doc v2.0 update |
| Defect Rate | TBD | 0.15 | 4 defects cataloged (3 resolved, 1 open) |
| Cross-Source Agreement | N/A | - | Only one enrichment source (parser baseline) |
| VLM Accuracy | TBD | 0.10 | Not yet inspected |
| **Overall** | **TBD** | | **Grade pending** |

##### 11.2 Key Defects

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | documentation | HIGH | RESOLVED | Image count 12K vs actual 30,338 |
| D02 | documentation | HIGH | RESOLVED | Directory structure incorrect in docs |
| D03 | documentation | MEDIUM | RESOLVED | Local path wrong (camera_captured vs correction) |
| D04 | enrichment | CRITICAL | OPEN | 11/13 prescreening fields missing enrichment |

##### 11.3 VLM Inspection Summary

> Not yet performed. VLM inspection required before grade can exceed D.

##### 11.4 Cross-Dataset Findings

- **KI-005 applicable**: Synthetic dataset - LLM cannot detect synthetic capture method. Parser correctly hardcodes `capture_method=synthetic`.
- **KI-004 applicable**: Synthetic dataset - LLM may incorrectly flag handwriting. Integration script should override `has_handwriting=False`.
- **KI-007 applicable**: Domain is `UNK` for all samples - acceptable for generic/mixed content.

**Audit Artifacts**: [scripts/audit/results/docalign12k/](../../../scripts/audit/results/docalign12k/) (pending generation)

---

#### 12. Reliability & Bottlenecks

> **Status**: Base metadata only. Enrichment pipeline not yet run - reliability analysis blocked on missing fields.

##### 12.1 Composite Category Distribution

> **Computed**: Pending | **Samples**: 30,338 | **Avg Min Confidence**: N/A

Expected to show majority `unreliable` category due to 11/13 prescreening fields at 0% coverage.

##### 12.2 Top Bottleneck Fields

| Rank | Field | Status | Remediation |
|-----:|-------|--------|-------------|
| 1 | `domain_level1` | 0% (all UNK) | LLM enrichment |
| 2 | `iso639_language` | 0% (all und) | LLM enrichment |
| 3 | `script_family` | 0% (all other) | LLM enrichment (derived from iso15924) |
| 4 | `layout_detections` | 0% (missing) | DocLayout-YOLO extraction |
| 5 | `content_flags_boolean` | 0% (missing) | LLM or VLM enrichment |
| 6 | `quality_overall_mos` | 0% (missing) | IQA pipeline or VLM scoring |

> **Improving Reliability**: Priority enrichment order documented in audit checklist (see `docs/audit/audits/docalign12k_audit.md`).

---
