#### RealDAE (Real-world Document Appearance Enhancement)

> **Quick Stats**: 600 image pairs | Pixel-aligned GT | 3 degradation types | Camera-captured
>
> **License**: Research | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | RealDAE: Real-world Document Image Appearance Enhancement Dataset |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Maintainer** | Jiaxin Zhang et al. (South China University of Technology) |
| **Paper** | [Appearance Enhancement for Camera-Captured Document Images in the Wild (TAI 2023)](https://ieeexplore.ieee.org/document/10268585/) |
| **Repository** | [GitHub: ZZZHANG-jx/GCDRNet](https://github.com/ZZZHANG-jx/GCDRNet) |
| **License** | Research use |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/realdae/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Camera-captured degraded images (_in.jpg) |
| **Images** | JPG | Flatbed-scanned ground truth images (_gt.jpg) |
| **Annotations** | Filename-based | Paired image structure via _in/_gt suffixes |
| **Supplementary** | README, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train (Bleed)** | `task_bleed_train/` | Implicit (filename pairing) | 300 images (150 pairs) | ✅ |
| **Test (Bleed)** | `task_bleed_test/` | Implicit (filename pairing) | 100 images (50 pairs) | ✅ |
| **Train (Color)** | `task_color_train/` | Implicit (filename pairing) | 300 images (150 pairs) | ✅ |
| **Test (Color)** | `task_color_test/` | Implicit (filename pairing) | 100 images (50 pairs) | ✅ |
| **Train (Shadow)** | `task_shadow_train/` | Implicit (filename pairing) | 300 images (150 pairs) | ✅ |
| **Test (Shadow)** | `task_shadow_test/` | Implicit (filename pairing) | 100 images (50 pairs) | ✅ |

**Split Organization Pattern**: `by_folder` (task-specific folders with train/test splits)

> **Notes**:
>
> - Each task has dedicated train/test folders
> - No validation split provided (train/test only)
> - Total: 900 train images (450 pairs), 300 test images (150 pairs)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Filename suffix | Document | _in.jpg (degraded) paired with_gt.jpg (clean) |
| **Task Type** | Directory name | Document | Implicit from folder (bleed/color/shadow) |
| **Degradation Type** | Implicit | Document | Inferred from task type |

> **Note**: No explicit quality scores or bounding boxes provided. Degradation information implicit in task organization.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Paper, README | Version, license, citation, methodology |
| **Image-level** | Filename pattern | Task type, train/test split, pair membership |
| **Document-level** | Implicit | Camera-captured (input), scanner (ground truth) |

##### 2.5 Annotation Schema Details

> **Format**: Filename-based pairing structure

```text
Filename Pattern:
{origin}_{number}_{type}.jpg

Examples:
- origin1000_103_in.jpg  (degraded input image)
- origin1000_103_gt.jpg  (ground truth paired image)

Directory Pattern:
task_{degradation_type}_{split}/

Examples:
- task_bleed_train/  (bleed-through training set)
- task_shadow_test/  (shadow removal test set)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `filename_suffix` | str | Yes | _in or_gt identifies image type |
| `directory_name` | str | Yes | Encodes task type and split |
| `base_name` | str | Yes | Links paired images |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `paired_file` | High | Filename-based detection |
| ✅ Task type | `task_type` | High | From directory name |
| ✅ Split info | `subset` | High | From directory name |
| ✅ Capture method | `capture_method` | Medium | Inferred (camera vs scanner) |
| ❌ Quality scores | - | Low | Not provided, compute from pairing |
| ❌ Layout boxes | - | Low | Not provided |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Image Pairs** | 600 |
| **Training Pairs** | 450 (150 per task) |
| **Test Pairs** | 150 (50 per task) |
| **Image Width Range** | 734-4,976 pixels |
| **Image Height Range** | 864-4,032 pixels |
| **File Format** | JPEG |
| **Annotation Type** | Pixel-aligned input/GT pairs |
| **Total Size** | 2.06 GB |

##### Task-Specific Splits

| Task | Train Pairs | Test Pairs | Total | Description |
|------|-------------|------------|-------|-------------|
| **Bleed-through** | 150 | 50 | 200 | Ink showing through from reverse side |
| **Color Cast** | 150 | 50 | 200 | Uneven color/illumination |
| **Shadow** | 150 | 50 | 200 | Cast shadows from camera capture |

##### Content Organization

```text
realdae/
├── task_bleed_train/     # 150 pairs (300 images)
│   ├── *_in.jpg          # Degraded input images
│   └── *_gt.jpg          # Manually enhanced ground truth
├── task_bleed_test/      # 50 pairs (100 images)
├── task_color_train/     # 150 pairs (300 images)
├── task_color_test/      # 50 pairs (100 images)
├── task_shadow_train/    # 150 pairs (300 images)
└── task_shadow_test/     # 50 pairs (100 images)
```

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | **Real camera-captured documents** |
| **Baseline Quality** | Variable (intentionally degraded) |
| **Bleed-through** | **HIGH** - Dedicated task subset |
| **Illumination Sensitivity** | **HIGH** - Color cast and shadow tasks |
| **Shadow Presence** | **HIGH** - Dedicated task subset |
| **Noise Sensitivity** | MEDIUM - Camera sensor noise present |
| **Blur Sensitivity** | MEDIUM - Some motion/focus blur |
| **Key Value** | **Only pixel-aligned camera document enhancement dataset** |

##### Degradation Types Present

- **Bleed-through**: Ink/print showing through from reverse side of paper
- **Color Cast**: Uneven illumination causing color shifts across document
- **Shadow**: Hard and soft shadows from capture environment
- **Camera Noise**: Sensor noise from mobile/camera capture
- **Perspective Distortion**: Mild warping from non-perpendicular capture angle

##### Training Value

- **Strengths**: Pixel-aligned GT (rare), task-specific splits, real camera capture conditions
- **Weaknesses**: Relatively small (600 pairs), limited to 3 degradation types
- **Unique Features**: Only dataset with manually enhanced ground truth for camera documents
- **Benchmark Suitability**: **HIGH** - Pre-split train/test, enables quantitative evaluation (PSNR/SSIM)
- **Complementary Datasets**: Combine with DocLayNet/RVL-CDIP for content diversity

##### Project Usage

- **Path**: `01_base_data/camera_captured/realdae/`
- **Phase(s)**: Phase 7 training (optional camera enhancement), potential GCDRNet integration
- **Purpose**: Camera-captured document enhancement training, mobile capture preprocessing
- **Priority**: **P2** - Valuable for mobile/camera capture scenarios
- **Parser**: [`parse_realdae_labels`](../scripts/annotate_base_metadata.py#L2979) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/camera_captured/realdae/` | ✅ Available | 1,200 JPG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | `metadata_registry/extracted/realdae/ocr_batch_*.jsonl` | ✅ Extracted | Docling OCR, 6 batch files, 1,200 records (1,198 with text, 99.8%), confidence ~1.0 |
| **Layout Extracted** | `metadata_registry/extracted/realdae/layout_batch_*.json` | ✅ Extracted | Docling layout annotations, 6 batch files, 10 categories |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None - Data not provided by source dataset
- ❌ Not extracted - Data not yet processed/extracted
- ⚠️ Partial - Some data available, incomplete coverage

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 583 |
| **File Format** | JPEG (99%), MPO (1%) |
| **Dimensions** | 398-5344 × 164-4149 px (avg: 2151 × 2611) |
| **Avg File Size** | 1,675 KB |
| **Color Space** | RGB |
| **Capture Method** | Camera (Smartphone) |
| **Domain** | Mixed (EDU 45%, PER 11%, FIN 9%, SCI 8%, UNK 7%, ADM 6%, TAX 5%, other 9%) |
| **Languages** | Chinese 76%, English 19%, other 5% (see [Section 5.3](#53-language--script-coverage)) |

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train (All Tasks)** | 900 images | 437 | ~49% | ⚠️ Partial |
| **Test (All Tasks)** | 300 images | 146 | ~49% | ⚠️ Partial |
| **Total** | 1,200 images | 583 | 49% | ⚠️ Partial coverage |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata

> **Note**: Layer 2 metadata contains 583 samples (only input images, _in.jpg) out of 1,200 total source images.
> The 600 ground truth images (_gt.jpg) are intentionally excluded from Layer 2 metadata as they represent
> reference targets, not source documents requiring analysis. The 17 missing input images (~3%) may have
> failed during initial processing or been filtered for quality issues.

##### Associated Model

**GCDRNet** (Global Context + Detail Restoration Network):

- End-to-end enhancement network trained on RealDAE
- Architecture: GC-Net (global context) + DR-Net (detail restoration)
- Backbone: UNeXt (U-Net variant)
- Pre-trained weights: Available from repository

##### Benchmark Performance (Document Enhancement)

| Model | SSIM ↑ | PSNR ↑ | Year | Notes |
|-------|--------|--------|------|-------|
| **GL-PGENet** | **0.9480** | - | 2025 | State-of-the-art |
| GCDRNet | 0.9312 | 22.87 | 2023 | Baseline (this dataset) |
| DocUNet | 0.8934 | 20.14 | 2018 | Geometric correction only |

*Metrics: SSIM = Structural Similarity Index, PSNR = Peak Signal-to-Noise Ratio*

##### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.
> **Applicability**: **Multilingual dataset** (despite paper claim of English-only).
>
> **CRITICAL (KI-009)**: The RealDAE paper describes "English documents" but LLM vision
> analysis of 583 input images detected **74% Chinese, 22% English**, and 4% other languages.
> The language/script values below are from LLM enrichment (post-audit), NOT source documentation.

| Language | ISO 639 | Samples | Coverage | Notes |
|----------|---------|---------|----------|-------|
| Chinese | zh | 445 | 76.3% | Majority language (paper claimed 0%) |
| English | en | 113 | 19.4% | Paper claimed 100% |
| German | de | 3 | 0.5% | |
| Japanese | ja | 3 | 0.5% | |
| Polish | pl | 3 | 0.5% | |
| Hungarian | hu | 3 | 0.5% | |
| Danish | da | 3 | 0.5% | |
| Other | hi, nl, es, etc. | 10 | 1.7% | |

| Script | ISO 15924 | Samples | Coverage | Notes |
|--------|-----------|---------|----------|-------|
| Simplified Chinese | Hans | 445 | 76.3% | |
| Latin | Latn | 132 | 22.6% | |
| Japanese | Jpan | 3 | 0.5% | |
| Devanagari | Deva | 2 | 0.3% | |
| Malayalam | Mlym | 1 | 0.2% | |

**Script Families Present**: CJK (76.8%), Latin (22.6%), Indic (0.5%)

> **Source**: LLM enrichment (2026-02-12 audit). See KI-009 in
> [CROSS_DATASET_KNOWN_ISSUES.json](../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json)
> for details on documentation unreliability.

#### 7. Known Issues & Limitations

##### Source Dataset Limitations

- **Small Dataset Size**: Only 600 pairs (1,200 images) - Limited diversity compared to other IQA datasets
- **Limited Degradation Types**: Only 3 degradation categories (bleed-through, color cast, shadow) - Missing blur, noise, skew variations
- **No Quality Scores**: No explicit quality scores provided - Must compute from paired comparison (PSNR/SSIM)
- **Camera Type Bias**: Specific camera capture conditions may not generalize to all mobile devices
- **No Layout Annotations**: Dataset focused on enhancement, lacks semantic layout labels
- **Test Set Size**: Only 150 pairs per split (50 per task) - Limited evaluation set
- **GT Images Excluded**: Ground truth images not included in Layer 2 metadata (by design, not an issue)

##### Layer 2 Audit Findings (2026-02-12)

- **KI-009 (CRITICAL): Language documentation is wrong** - Paper claims "English documents" but LLM detection shows 74% Chinese, 22% English. **NEVER trust documentation-only language claims.** See [CROSS_DATASET_KNOWN_ISSUES.json](../../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json) KI-009.
- **KI-008 (HIGH): script_family contained directionality** - Base metadata had `ltr` instead of `cjk`/`latin`/`indic`. Fixed in integration by deriving from `iso15924_script` via `get_script_family()`.
- **KI-005 extended: LLM capture method unreliable for camera images** - LLM misclassified 38.8% of camera-captured images as `scanner_flatbed`. Dataset documentation override required.
- **Content flag FP rates**: `has_handwriting` 30% FP, `has_figure` 50% secondary FP. Both flags are soft labels needing confidence threshold tuning before training use.
- **Layer 2 Coverage**: Only 583 of 1,200 images in Layer 2 metadata (49% coverage, input images only)
- **Document Type Diversity**: Predominantly Chinese educational/financial documents, not the English-only printed text described in the paper

#### 10. Dataset-Specific Notes

> **Purpose**: Capture unique characteristics, caveats, and implementation details specific to this dataset.

##### 10.1 Annotation Caveats

- **Paired Image Structure**: Input (_in.jpg) and ground truth (_gt.jpg) must be processed together for quality comparison
- **Task Organization**: Degradation type is implicit in directory structure, not in image metadata
- **No Validation Split**: Dataset only provides train/test splits, no validation set
- **Manual Enhancement**: GT images are manually enhanced (not original scans), which may introduce subjective quality bias

##### 10.2 Implementation Notes

- **Parser Note**: RealdaeParser extracts task_type from directory name (e.g., "task_bleed_train" → task_type="bleed")
- **Pairing Logic**: Base name (without _in/_gt suffix) links paired images
- **Quality Computation**: Use PSNR/SSIM between paired images to generate quality scores
- **Capture Method**: Parser sets "camera_smartphone" for_in images; GT images should use "scanner_flatbed" but currently not differentiated
- **Layer 2 Processing**: Only input images (_in.jpg) are included in Layer 2 metadata; GT images intentionally excluded

##### 10.3 External Resources

- **GCDRNet Model**: Pre-trained enhancement model available at [GitHub: ZZZHANG-jx/GCDRNet](https://github.com/ZZZHANG-jx/GCDRNet)
- **Paper PDF**: [IEEE Xplore](https://ieeexplore.ieee.org/document/10268585/)
- **GCS Storage**: `gs://image_detection_b/image-preprocessing-detector/datasets/realdae/`

##### 10.4 Custom Metrics

- **Enhancement Quality**: Use SSIM (Structural Similarity Index) as primary metric (higher is better, 0-1 scale)
- **PSNR**: Peak Signal-to-Noise Ratio as secondary metric (higher is better, typically 15-30 dB for document enhancement)
- **Task-Specific Evaluation**: Evaluate bleed-through, color cast, and shadow removal separately

##### References

```bibtex
@article{zhang2023appearance,
  title={Appearance Enhancement for Camera-Captured Document Images in the Wild},
  author={Zhang, Jiaxin and Liang, Lingyu and Ding, Kai and Guo, Fengjun and Jin, Lianwen},
  journal={IEEE Transactions on Artificial Intelligence},
  volume={5},
  number={5},
  year={2024},
  publisher={IEEE},
  doi={10.1109/TAI.2023.3321257}
}
```

---

##### Layer 2 Audit Summary

> **Audit Date**: 2026-02-12 | **Grade**: B (85.9/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 99.0 | 0.278 | 13/13 fields screened |
| Field Validity | 92.6 | 0.278 | 27 fields audited |
| Doc Completeness | 54.6 | 0.167 | 6/11 sections populated |
| Defect Rate | 91.4 | 0.167 | 14 defects (11 resolved, 1 partial, 2 deferred) |
| VLM Accuracy | 75.0 | 0.111 | 57 images inspected (45 Track A + 12 Track C) |
| **Overall** | **85.9** | | **Grade B** |

**Prescreening**: 87.5% pass rate (510/583), 9/13 fields at 100%

**Key Defects Resolved**:

- D03/D04 (CRITICAL): Language/script corrected from English/Latn to per-sample LLM values
- D05 (HIGH): script_family corrected from `ltr` to `cjk`/`latin`/`indic`
- D06 (HIGH): Docling layout integrated (581/583 samples)
- D07 (HIGH): Content flags derived from LLM + Docling layout

**VLM Inspection Results** (57 images):

| Flag | Inspected | FP Rate | Notes |
|------|----------:|--------:|-------|
| has_formula | 15 | 6.7% | 1 FP (medical notes misclassified) |
| has_table | 10 | 0% | Clean; 4 FN found in other inspections |
| has_handwriting | 10 | 30% | 3 FP (printed text misclassified as handwritten) |
| has_figure | 10 | 0% primary | High secondary FP rate across Track A |

**Audit Artifacts**: [scripts/audit/results/realdae/](../../../scripts/audit/results/realdae/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-12 | **Samples**: 583 | **Avg Min Confidence**: 0.000
>
> **Note**: All samples show as "unreliable" because `text_quality` (D13, deferred)
> has 0.000 confidence. This is the sole bottleneck field; all other enrichment fields
> were populated by the integration script. See Layer 2 Audit Summary above for
> post-integration quality assessment.

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 583 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
