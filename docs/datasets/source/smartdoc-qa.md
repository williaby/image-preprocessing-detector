---
dataset_id: smartdoc-qa
version: "1.1"
license: Research Only
commercial_use: false
iqa_profiles:
  - camera_smartphone
  - quality_benchmark
baseline_quality: null
training_suitable: false
benchmark_suitable: true
documentation_status: complete
---

### SmartDoc-QA

> **Quick Stats**: 4,280 images | Robotic-arm controlled smartphone capture | Quality assessment benchmark
>
> **License**: Research Only | **Commercial Use**: Not permitted

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | SmartDoc Quality Assessment |
| **Version** | 1.0 (CBDAR@ICDAR 2015) |
| **Release Date** | 2015 |
| **Last Updated** | 2026-02-14 |
| **Maintainer** | L3i Lab, Universite de La Rochelle |
| **Paper** | [Nayef et al. 2015](https://ieeexplore.ieee.org/document/7333960/) |
| **Repository** | [smartdoc.univ-lr.fr](http://smartdoc.univ-lr.fr/smartdoc-qa/) |
| **License** | Research Only |
| **Commercial Use** | No (Research only) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/smartdoc-qa/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPEG | Smartphone-captured document images (3264-4128 x 2448-3096 px) |
| **Q&A Pairs** | JSON | 8,498 question-answer pairs (qas_v2.json) |
| **Annotations** | XML/JSON | Distortion type/amount labels, OCR accuracy scores (3 engines) |
| **Supplementary** | JSON | Structured data variants (GT + distortion levels) |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `02_benchmark_only/smartdoc-qa/` | `splits/smartdoc_qa_splits.json` | 3,424 | ✅ |
| **Validation** | `02_benchmark_only/smartdoc-qa/` | `splits/smartdoc_qa_splits.json` | 428 | ✅ |
| **Test** | `02_benchmark_only/smartdoc-qa/` | `splits/smartdoc_qa_splits.json` | 428 | ✅ |
| **Total** | - | - | 4,280 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (JSON split file)

> **Notes**:
>
> - Split determined by `splits/smartdoc_qa_splits.json` manifest file
> - All images stored in single directory, split membership tracked in manifest
> - Total: 4,280 images (80/10/10 train/val/test split)
> - Original dataset does not define official splits; splits assigned for project use

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Distortion Labels** | XML/JSON | Image | Distortion type and amount per capture |
| **OCR Accuracy** | JSON | Image | OCR accuracy scores from 3 engines (Tesseract, ABBYY, third engine) |
| **Q&A Pairs** | JSON | Document | 8,498 question-answer pairs with evidence |
| **Document Type** | Metadata | Document | 3 categories: modern documents, receipts, old administrative letters |

> **Note**: OCR accuracy serves as proxy quality metric -- higher accuracy correlates with better image quality.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / Paper | Version, license (Research Only), citation, document types |
| **Image-level** | Annotations | Distortion type, distortion amount, OCR accuracy |
| **Document-level** | Annotations | Document type, capture conditions |
| **Q&A-level** | qas_v2.json | Question, answer, evidence source, page number |

##### 2.5 Annotation Schema Details

> **Format**: XML distortion annotations + JSON QA pairs

**Schema Structure**:

```text
Distortion Annotations:
- document_type: Text (modern_document / receipt / old_administrative_letter)
- distortion_type: Text (blur, perspective, lighting, noise, folds, combined)
- distortion_amount: Float (severity level)
- ocr_accuracy_tesseract: Float (0-1 OCR accuracy)
- ocr_accuracy_abbyy: Float (0-1 OCR accuracy)
- ocr_accuracy_third: Float (0-1 OCR accuracy)

QA Pairs (qas_v2.json):
- question: Text (natural language question about document)
- answer: Text (extracted answer)
- evidence: Text (source text from document)
- page_number: Int (page reference)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `distortion_type` | Text | Yes | Type of capture distortion applied |
| `distortion_amount` | Float | Yes | Severity of distortion |
| `ocr_accuracy` | Float | Yes | OCR accuracy as quality proxy (3 engines) |
| `document_type` | Text | Yes | 3 document categories |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ OCR accuracy scores | `quality_metrics.ocr_accuracy` | **HIGH** | 3 engine outputs available |
| ✅ Distortion labels | `quality_metrics.distortion_type` | **HIGH** | Type + amount per image |
| ✅ Document type (3 categories) | `provenance.source_dataset_category` | Medium | Modern docs, receipts, old administrative |
| ✅ Q&A pairs | - | Low | Research evaluation data |
| ⚠️ Capture conditions | - | Low | Robotic arm parameters |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert + Automated (robotic arm controlled capture) |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | L3i Lab researchers; Fanuc LR Mate 200iD robotic arm for controlled capture |
| **Quality Assurance** | Controlled environment ensures reproducible distortions; OCR accuracy computed automatically |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Benchmark evaluation |
| **Purpose** | Mobile capture quality assessment benchmark |
| **Local Path** | `02_benchmark_only/smartdoc-qa/` |
| **Subset Used** | Full dataset |
| **Parser** | [`parse_smartdoc_labels`](../scripts/annotate_base_metadata.py#L1004) ✅ Complete |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`parse_smartdoc_labels`](../../scripts/annotate_base_metadata.py#L1004) |
| **Parser Status** | ✅ Complete |
| **Layer 2 Auto-Derived** | `capture_method`, `script_family`, `iso639_language` |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/smartdoc-qa/` | ✅ Available | 4,280 JPEG files |
| **Text/GT** | Native annotations | ✅ Available | JSON: QA text pairs from document images |
| **Text/OCR Extracted** | `annotations/smartdoc-qa/ocr/ocr_batch_*.jsonl` | ✅ Available | 3,000 records (70%), Docling OCR |
| **Layout Extracted** | `annotations/smartdoc-qa/layout/layout_batch_*.json` | ✅ Available | 2,203 records (51%), DocLayout-YOLO |
| **Docling GPU Extracted** | `metadata_registry/extracted/smartdoc-qa/` | ⚠️ Partial | Docling GPU: 3,000/4,280 OCR (70%) + 2,305/4,280 layout (54%), needs investigation |

#### 4. Dataset Statistics

##### 4.1 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 4,280 |
| **Training Split** | 3,424 (80%) |
| **Validation Split** | 428 (10%) |
| **Test Split** | 428 (10%) |
| **Document Types** | Modern documents, receipts, old administrative letters |
| **Distortion Types** | Single and multiple capture distortions (blur, perspective, lighting, noise, folds) |
| **Capture Setup** | Fanuc LR Mate 200iD robotic arm (controlled environment) |
| **Cameras** | Samsung Galaxy S4, other smartphones |
| **Image Dimensions** | 3264-4128 x 2448-3096 px (avg: 3696 x 2772) |
| **File Format** | JPEG |
| **Color Space** | RGB |
| **Avg File Size** | 3,132 KB |
| **Ground Truth** | Distortion type/amount, OCR outputs (3 engines), OCR accuracy |

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | General documents (modern, administrative, receipts) |
| **Document Types** | 3 categories: modern documents, receipts, old administrative letters |
| **Language(s)** | Predominantly Latin script (French/English) |
| **Acquisition Method** | Robotic arm controlled smartphone capture |

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Mobile camera captures (controlled robotic arm) |
| **Capture Device** | Samsung Galaxy S4 + other smartphones, Fanuc LR Mate 200iD robotic arm |
| **Original Quality** | Variable -- controlled single and multiple distortions applied |
| **Known Artifacts** | Blur, perspective distortion, lighting variation, noise, folds |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Primary distortion type in dataset |
| **Perspective** | HIGH | Controlled perspective distortions |
| **Lighting** | HIGH | Uneven lighting conditions captured |
| **Noise** | MEDIUM | Camera sensor noise present |
| **Folds** | MEDIUM | Physical document folds captured |

##### 6.3 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | NONE -- benchmark only, training prohibited |
| **Unique Characteristics** | Controlled capture environment, multiple distortion types, OCR accuracy ground truth, 3 OCR engine outputs |
| **Benchmark Suitability** | HIGH -- controlled distortions enable isolating specific quality factors |
| **Key Value** | Benchmark for IQA methods via OCR correlation |
| **Known Limitations** | Controlled robotic capture does not represent real-world smartphone usage; limited to 3 document types |

**Benchmark Purpose**: SmartDoc-QA enables benchmarking quality assessment methods using OCR accuracy as an objective measure. The controlled capture environment allows isolating specific distortion effects:

- **Single distortions**: Isolate individual quality factors
- **Multiple distortions**: Simulate real-world capture conditions
- **OCR correlation**: Predict OCR performance from image quality

#### 7. Known Issues & Limitations

- **Benchmark only**: NEVER train on this dataset -- designed exclusively for evaluation/benchmarking
- **Controlled environment**: Robotic arm capture does not represent real-world smartphone usage
- **Limited document types**: Only 3 categories (modern documents, receipts, old administrative letters)
- **Partial OCR/layout coverage**: Docling extracted 70% OCR and 54% layout (failures need investigation)
- **No official splits**: Dataset does not define train/val/test partitions (project-assigned splits used)

#### 8. Processing Status

| Step | Status | Notes |
|------|--------|-------|
| **Image Storage** | ✅ Complete | 4,280 JPEG images |
| **Base Metadata** | ✅ Complete | 4,280 samples annotated |
| **LLM Enrichment** | ✅ Complete | Domain, language, script enrichment |
| **Language Enrichment** | ✅ Complete | OpenLID language detection |
| **Docling OCR** | ⚠️ Partial | 70% coverage (3,000/4,280) |
| **DocLayout-YOLO** | ⚠️ Partial | 54% coverage (2,305/4,280) |
| **VLM Inspection** | ❌ Not started | Content flags unverified |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{nayef2015smartdocqa,
  title={SmartDoc-QA: A Dataset for Quality Assessment of Smartphone Captured
         Document Images - Single and Multiple Distortions},
  author={Nayef, Nibal and Luqman, Muhammad Muzzamil and Prum, Sophea and
          Eskenazi, S{\'e}bastien and Chazalon, Joseph and Ogier, Jean-Marc},
  booktitle={2015 13th International Conference on Document Analysis and
             Recognition (ICDAR) - CBDAR Workshop},
  pages={1231--1235},
  year={2015},
  organization={IEEE},
  doi={10.1109/ICDAR.2015.7333960}
}
```

##### Related Resources

- [Official website](http://smartdoc.univ-lr.fr/smartdoc-qa/)
- [IEEE Xplore](https://ieeexplore.ieee.org/document/7333960/)

#### 10. Dataset-Specific Notes

##### 10.1 Capture Methodology

SmartDoc-QA uses a **Fanuc LR Mate 200iD industrial robotic arm** to control smartphone positioning, enabling precise and reproducible distortion conditions. This differs from typical "mobile-captured" datasets where human hand motion introduces uncontrolled variation. The robotic arm approach allows:

- Exact reproduction of perspective angles
- Controlled blur amounts (via focus/distance)
- Systematic lighting variation
- Repeatable multi-distortion combinations

##### 10.2 OCR-Quality Correlation

The dataset's primary research contribution is using OCR accuracy as an **objective quality proxy**. Three OCR engines provide accuracy measurements, enabling correlation analysis between image quality metrics and OCR performance degradation.

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (88.4/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 92.4 | 15% |  |
| Field Validity | 92.4 | 15% |  |
| Doc Completeness | 100.0 | 5% |  |
| Defect Rate | 84.0 | 10% |  |
| Cross-Source Agreement | 68.5 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **88.4** | | **Grade B** |

##### 11.2 Key Defects

> **Total**: 8 defects (7 accepted, 1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| DEF-001 | split | low | ACCEPTED | Split is 'unknown' for all 4,280 samples. Dataset does not define official train/val/test splits. |
| DEF-002 | domain_level1 | medium | ACCEPTED | domain_level1 is 'UNK' for all 4,280 samples. LLM enrichment domain confidence is 0.3 (unreliable). |
| DEF-003 | script_family | medium | OPEN | script_family uses invalid enum value 'ltr' instead of 'latin' for all 4,280 samples. |
| DEF-004 | layout_detections | low | ACCEPTED | layout_detections empty for 26.7% of samples (1,143/4,280). Partial DocLayout-YOLO coverage. |
| DEF-005 | text_has_content | low | ACCEPTED | text_has_content is false for all 4,280 samples. No OCR extraction integrated. |
| DEF-006 | orientation_class | low | ACCEPTED | orientation_class not populated for all 4,280 samples. |
| DEF-007 | image_properties_color_mode | low | ACCEPTED | image_properties.color_mode not populated for all 4,280 samples. |
| DEF-008 | handwriting_present | low | ACCEPTED | handwriting_present not populated for all 4,280 samples. |

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

##### 11.4 Cross-Dataset Findings

- **KI-007**: ACCEPTED -- LLM domain classification produces high UNK rate on generic content. Domain taxonomy doesn't cover generic/narrative content well. Accept UNK as valid classification.
- **KI-008**: OPEN -- script_family contains directionality value 'ltr' instead of family name 'latin'. Integration script needs to re-derive via `get_script_family(iso15924_script)`.

**Audit Artifacts**: [scripts/audit/results/smartdoc-qa/](../../scripts/audit/results/smartdoc-qa/)

#### 12. Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 4,280 | **Avg Min Confidence**: 0.000

##### 12.1 Composite Category Distribution

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 4,280 | 100.0% |

**Category Thresholds**: hard_label >= 0.9, soft_label >= 0.7, active_learning >= 0.5, unreliable < 0.5

##### 12.2 Top Bottleneck Fields

> The fields most frequently responsible for the lowest per-sample confidence.

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

#### 13. Training Head Coverage

##### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G1-1 | blur_score | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G1-2 | noise_score | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G1-3 | contrast_score | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G1-4 | skew_score | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G1-5 | compression_score | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G1-6 | overall_quality | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G2-1 | script_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G3-1 | orientation_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G3-2 | skew_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G4-1 | handwriting_presence_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G4-4 | presence_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G4-5 | legibility_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G5-1 | capture_method_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G5-2 | shadow_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G5-3 | warping_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |
| SIG-G5-5 | resolution_quality_reg | ❌ | 0 | N/A | BENCHMARK ONLY -- training prohibited |

Contribution legend: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

##### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ✅ | Predominantly LATN (modern documents, receipts, administrative letters) |
| 2 | Capture method | ✅ | camera_smartphone (robotic arm, Samsung Galaxy S4) -- controlled environment |
| 3 | Document domain | 🟡 | 3 document types: modern documents, receipts, old administrative letters |
| 4 | Layout type | 🟡 | Mixed single-column and multi-column |
| 5 | Text density | ✅ | Varied across document types |
| 6 | Degradation types | ✅ | Blur, perspective distortion, lighting variation, noise, folds |
| 7 | Resolution/DPI range | ✅ | Camera-native 3264-4128 x 2448-3096 px |
| 8 | Document age | 🟡 | Modern + old administrative letters |
| 9 | Text scope | ✅ | Document-level (full-page captures) |
| 10 | Content flags | 🟡 | No confirmed tables/figures/formulas/code/handwriting flags |
| 11 | Binarization status | ❌ | All color RGB |
| 12 | Artifact types | ✅ | Perspective, blur, folds, uneven lighting |
| 13 | Color mode | ✅ | Color |
| 14 | Font variety | 🟡 | Limited -- 3 document type categories |

Coverage: ✅ Well-covered | 🟡 Partial | ❌ Not present

##### 13.3 Corpus Role & Constraints

SmartDoc-QA is a **benchmark-only dataset** designed for evaluating IQA methods via OCR accuracy as proxy quality score; training on this dataset is explicitly prohibited (see Section 7). Despite having 4,280 camera-smartphone images with controlled single/multiple distortions, the robotic-arm capture environment and benchmark-design intent make it unsuitable for augmenting training distributions. The dataset resides at `02_benchmark_only/smartdoc-qa/` and should only be used for post-training evaluation of capture method, IQA, and warping head performance on mobile-captured documents.

#### Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-02-10 | Initial Layer 2 metadata documentation |
| v1.1 | 2026-02-13 | Added format, license, limitations, processing, version history sections |
| v1.2 | 2026-03-14 | Fixed ohr-bench copy-paste contamination (sections 2.1-2.6), corrected image count 4,260->4,280, added YAML frontmatter, standardized section numbering per template v1.6.0, added sections 9-10, fixed KI descriptions |
