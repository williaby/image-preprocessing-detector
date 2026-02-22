#### Nepali Handwritten Dataset

> **Quick Stats**: 958 images | Handwritten Devanagari | Text detection annotations
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes (with attribution)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Nepali Handwritten Images for Text Detection |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Kaggle** | [sweekardahal/nepali-handwritten-images-for-text-detection](https://www.kaggle.com/datasets/sweekardahal/nepali-handwritten-images-for-text-detection) |
| **License** | CC-BY-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nepali_handwritten/` |
| **Documentation Status** | Complete |

##### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Handwritten Nepali text images |
| **Annotations** | XML | PASCAL VOC format bounding boxes |

###### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/*.jpg` | `train/*.xml` | ~766 | ✅ Available |
| **Test** | `test/*.jpg` | `test/*.xml` | ~192 | ✅ Available |

**Split Organization Pattern**: `by_folder` (train/test directories)

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Bounding Boxes** | PASCAL VOC XML | Word/Character | Text detection boxes (no transcriptions) |

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Image-level** | XML `<filename>`, `<size>` | Image dimensions, filename |
| **Object-level** | XML `<object>` elements | Bounding boxes, category labels |

###### 2.5 Annotation Schema Details

> **Format**: PASCAL VOC XML

```xml
<annotation>
  <filename>image_001.jpg</filename>
  <size>
    <width>1280</width>
    <height>960</height>
  </size>
  <object>
    <name>text</name>
    <bndbox>
      <xmin>100</xmin>
      <ymin>200</ymin>
      <xmax>400</xmax>
      <ymax>250</ymax>
    </bndbox>
  </object>
</annotation>
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `filename` | str | Yes | Links to image file |
| `bndbox` | element | Yes | Contains xmin/ymin/xmax/ymax |
| `name` | str | Varies | Object category (typically "text") |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Bounding boxes | `layout_annotations` | High | PASCAL VOC format, convert to COCO |
| ✅ Image dimensions | `image_metadata` | Medium | From XML size element |
| ❌ Text transcriptions | - | N/A | Not provided (detection only) |
| ❌ Reading order | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

###### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | Handwriting contributors |
| **Quality Assurance** | Character class collection |
| **GT Label Coverage** | 100% |

##### 3. Integration Status

###### 3a. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 10B (Script Detection) |
| **Purpose** | Devanagari script class training (handwritten variety) |
| **Local Path** | `01_base_data/language/nepali_handwritten/` |
| **Subset Used** | Full dataset (train + test) |
| **Preprocessing** | GCS extraction required if not local |
| **Note** | Complements synthetic Hindi data with real handwriting |

###### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`NepaliHandwrittenParser`](../../src/image_preprocessing_detector/annotation/parsers/multilingual/nepali_handwritten.py) |
| **Parser Status** | ✅ Complete - Metadata + PASCAL VOC bounding box extraction |
| **Layer 1 Fields** | `language_code="ne"`, `iso15924_script_code="Deva"`, `script_name="Devanagari"`, `split` |
| **Bounding Box Format** | PASCAL VOC XML → COCO format `[x, y, width, height]` |
| **Layer 2 Auto-Derived** | `has_handwriting=True`, `script_family=Indic`, `domain=EDUCATIONAL` |

> **Parser Implementation**: Extracts bounding boxes from PASCAL VOC XML files and converts to COCO format for Layer 2 compatibility.

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/nepali_handwritten/` | ✅ Available | 958 PNG files |
| **Text/GT** | Native annotations | ⚠️ Partial | Labels: Character/digit class labels |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/nepali-handwritten/` | ✅ Available | Docling GPU: 5 layout batches, 958 images |

**Location Status Legend**:

- ✅ Available | ❌ None/Not extracted | ⚠️ GCS only

##### 4. Dataset Statistics

###### 4.1 Split Coverage

> **CRITICAL**: Layer 2 metadata coverage tracking for training/validation.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~766 | ~766 | 100% | ✅ Complete |
| **Test** | ~192 | ~192 | 100% | ✅ Complete |
| **Total** | 958 | 958 | 100% | ✅ Complete |

**Split Status Legend**:

- ✅ Complete - All samples in Layer 2 | ⚠️ Partial | ❌ Missing | ℹ️ N/A

> **Note**: Layer 2 base metadata generated via `scripts/annotate_base_metadata.py --dataset nepali_handwritten` (2026-02-09). Includes 958 images (.jpg, .jpeg, .png).

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 958 |
| **XML Annotations** | 958 (bounding boxes) |
| **Train Set** | ~766 images (80%) |
| **Test Set** | ~192 images (20%) |
| **Total Size** | 1.3-1.5 GB |
| **File Format** | JPEG/JPG |

###### 4.3 Dataset Structure

| Split | Images | Annotations |
|-------|--------|-------------|
| **train/** | ~766 | XML (PASCAL VOC format) |
| **test/** | ~192 | XML (PASCAL VOC format) |

##### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Educational (handwriting practice/samples) |
| **Document Types** | Handwritten text images |
| **Language(s)** | Nepali (100%) |
| **Temporal Range** | 2023 collection |
| **Acquisition Method** | Camera/smartphone capture of handwritten samples |

###### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Devanagari (Nepali) | Deva / ne | 958 | 100% | Handwritten variant |

**Script Families Present**: Indic (Devanagari)

**Text Direction**: Left-to-right (LTR) - standard for Devanagari script

> **Note**: Monolingual dataset. Complements synthetic Hindi data (printed Devanagari) with real handwriting.

##### 6. IQA Profile

###### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Real handwritten documents (camera capture) |
| **Capture Device** | Camera/smartphone (inferred from resolution) |
| **Original Quality** | High - modern capture equipment |
| **Compression** | JPEG quality ~85-95 |
| **Known Artifacts** | Minor compression artifacts, variable lighting |

###### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Handwriting strokes sensitive to motion blur |
| **Noise** | MEDIUM | Stroke edges degrade with noise |
| **Skew** | MEDIUM | Handwritten text naturally rotated, some tolerance |
| **Contrast** | MEDIUM | Variable pen pressure requires good contrast |
| **Compression** | MEDIUM | Stroke edges sensitive to JPEG artifacts |

###### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Handwriting Variability** | High | Multiple writers, varying styles |
| **Stroke Thickness** | Variable | Pen pressure variations affect quality |
| **Line Spacing** | Variable | Affects text detection accuracy |
| **Background Uniformity** | Good | Clean paper backgrounds |
| **Script Complexity** | Medium | Devanagari character complexity |

###### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Real handwritten Devanagari samples |
| **Unique Characteristics** | Handwritten Devanagari (vs synthetic printed) |
| **Complementary Datasets** | hindi_ocr_synthetic (printed), cvsi (scene text) |
| **Benchmark Suitability** | MEDIUM - Small dataset (958 images) |

##### 7. Known Issues & Limitations

- **Small Dataset Size**: Only 958 images limits training data volume
- **No Transcriptions**: Bounding boxes only - no ground truth text for OCR training
- **Single Script**: Only Devanagari - no script diversity within dataset
- **Local Availability**: Dataset on GCS only, requires extraction for local use
- **Train/Test Split**: No validation split provided (only train/test)
- **Annotation Granularity**: Uncertain if word-level or character-level boxes (requires inspection)
- **Writer Diversity**: Unknown number of handwriters, may have style bias
- **License Clarity**: Multiple sources cite CC-BY-4.0, requires verification (see Section 9.5)

###### Layer 2 Audit Findings (2026-02-12)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| NH-D001 | layout_detections | MEDIUM | DEFERRED | No Docling layout extractions available; content flags rely on VLM + dataset documentation |
| NH-D002 | text_content | LOW | DEFERRED | No OCR text content; language relies on parser GT and dataset docs |
| NH-D003 | capture_method | LOW | RESOLVED | v1 had `scanner_flatbed`, corrected to `camera_smartphone` |
| NH-D004 | has_figure | MEDIUM | OPEN | 344 Docling Picture disagreements; VLM sample shows ~8% true positive rate |
| NH-D005 | quality_overall | LOW | DEFERRED | No IQA quality scores available |

> **Cross-Dataset Issues Applied**: KI-001 (layout casing), KI-008 (script_family `ltr` -> `indic`)

##### 8. Layer 2 Annotation Summary

> **Purpose**: Documents the enrichment sources, field coverage, and known issue mitigations applied during Layer 2 metadata integration.

###### 8.1 Enrichment Sources

| Source | Available | Integration Status | Notes |
|--------|-----------|-------------------|-------|
| **Base metadata** | Yes | Integrated | 958 samples, v1 (2026-02-09) |
| **Language enrichment** | Yes | Integrated | Dataset-level (ne, Deva, 1.0) |
| **LLM enrichment** | No | N/A | Not available for this dataset |
| **Docling layout** | No | N/A | Planned but not extracted |
| **Docling OCR** | No | N/A | Planned but not extracted |
| **Classical IQA** | No | N/A | Not yet run |
| **Resolution quality** | No | N/A | Not yet run |
| **Skew/orientation** | No | N/A | Not yet run |
| **VLM corrections** | Yes | Integrated | 12 Track C samples, 96.2% accuracy |

###### 8.2 Field Coverage (Prescreening)

| Field | Pass Rate | Notes |
|-------|----------:|-------|
| split | 100% | train/test from parser GT |
| capture_method | 100% | Corrected to camera_smartphone (NH-D003) |
| domain_level1 | 100% | EDU from dataset documentation |
| iso639_language | 100% | ne from parser GT |
| script_family | 100% | indic (KI-008 fix applied) |
| layout_detections | 0% | No Docling layout available (NH-D001) |
| layout_bbox_valid | 100% | Vacuously passes (no detections) |
| content_flags_boolean | 100% | has_handwriting=True, VLM-corrected content flags |
| text_has_content | 0% | No OCR text content (NH-D002) |
| orientation_class | 100% | Default UP (not independently verified) |
| image_properties_color_mode | 100% | From base metadata |
| handwriting_present | 100% | True for all samples (GT override) |
| text_direction | 100% | ltr (v2.3.0 field) |
| text_directions_present | 100% | ["ltr"] (v2.3.0 field) |
| quality_overall_mos | 100% | Vacuously passes (not populated) |

**Overall**: 13/15 fields at 100% pass rate. Failures due to missing Docling extractions (deferred).

###### 8.3 Known Issue Mitigations

| KI ID | Description | Applied | Method |
|-------|-------------|---------|--------|
| KI-001 | Docling layout label casing | N/A | No Docling layout available |
| KI-005 | LLM capture method detection | Yes | Override to `camera_smartphone` from dataset docs |
| KI-008 | script_family `ltr` -> `indic` | Yes | `get_script_family("Deva")` returns `indic` |

###### 8.4 Schema Version

- **Schema Version**: 2.3.0
- **v2.3.0 Fields**: `text_direction="ltr"`, `text_directions_present=["ltr"]`, `character_height_rendered_px=null`, `output_size_px=null`
- **Enrichment Version**: v3 (`integrated_v2_vlm_corrected`)
- **Integration Script**: `scripts/integrate_nepali_handwritten_enrichments.py` v1.1.0

##### 9. Dataset-Specific Notes

###### 9.1 Annotation Caveats

- **PASCAL VOC Format**: Standard format but requires conversion to COCO for Prepare-Doc pipeline
- **Bounding Box Granularity**: Dataset documentation unclear on word vs character level
- **XML Validation**: Unknown if all XML files are well-formed (requires testing)
- **Difficult Flag**: PASCAL VOC `<difficult>` flag may be present but usage unclear

###### 9.2 Implementation Notes

- **XML Parsing**: Uses `xml.etree.ElementTree` for bounding box extraction
- **COCO Conversion**: PASCAL VOC `[xmin, ymin, xmax, ymax]` → COCO `[x, y, width, height]`
- **Parser Priority**: Bounding box extraction implemented in NepaliHandwrittenParser
- **Error Handling**: Parser handles malformed XML gracefully with debug logging

###### 9.3 External Resources

- **Kaggle Dataset**: Requires Kaggle API authentication for download
- **GCS Storage**: `gs://image_detection_b/image-preprocessing-detector/datasets/nepali_handwritten/`
- **Related Dataset**: hindi_ocr_synthetic provides printed Devanagari for comparison

###### 9.4 Training Context

- **Phase 10B Usage**: Part of 10-class script detection training
- **Complementary Role**: Real handwriting vs synthetic printed text (hindi_ocr_synthetic)
- **Devanagari Confusers**: Use with CVSI dataset (Bengali, Gujarati, Gurmukhi) for robust training

###### 9.5 License Clarification

**Issue**: Three sources provide conflicting license information:

| Source | License Stated | Notes |
|--------|----------------|-------|
| Kaggle Page | CC-BY-4.0 | Dataset description |
| DATASET_CATALOG.md (current) | CC-BY-4.0 | Quick Stats line |
| GCS Metadata | Unknown | Not yet inspected |

**Status**: ⚠️ **NEEDS VERIFICATION**

**Action Required**:

1. Check Kaggle dataset "About" section for official license
2. Inspect actual dataset files for LICENSE.txt or similar
3. Contact dataset author (Sweekar Dahal) if ambiguity remains

**Assumption for Now**: CC-BY-4.0 (most commonly cited), **commercial use with attribution**

> **CRITICAL**: Do not use commercially without confirming license. If license is more restrictive (e.g., CC-BY-NC), update Quick Stats and all documentation.

##### 10. References

###### Primary Citation

```bibtex
@misc{dahal2023nepali,
  title={Nepali Handwritten Images for Text Detection},
  author={Dahal, Sweekar},
  year={2023},
  publisher={Kaggle},
  howpublished={\url{https://www.kaggle.com/datasets/sweekardahal/nepali-handwritten-images-for-text-detection}},
  note={Licensed under CC-BY-4.0 (to be verified)}
}
```

###### Related Works

- [hindi_ocr_synthetic](hindi_ocr_synthetic.md) - Printed Devanagari (synthetic)
- [CVSI](cvsi.md) - Indic script scene text (includes Devanagari confusers)

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (88.6/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.4 | 15% |  |
| Field Validity | 100.0 | 15% |  |
| Doc Completeness | 72.7 | 5% |  |
| Defect Rate | 96.2 | 10% |  |
| Cross-Source Agreement | 52.5 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **88.6** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 5 defects (1 resolved, 3 deferred, 1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| NH-D001 | layout_detections | MEDIUM | DEFERRED | No layout detections available. Docling layout extraction was planned (5 batches |
| NH-D002 | text_content | LOW | DEFERRED | No OCR text content available. Docling OCR extraction was planned but not execut |
| NH-D003 | capture_method | LOW | RESOLVED | v1 metadata had capture_method='scanner_flatbed' (from dataset_config defaults). |
| NH-D004 | has_figure | MEDIUM | OPEN | Comparison report shows 344 disagreements for has_figure between Docling layout  |
| NH-D005 | quality_overall_score | LOW | DEFERRED | No IQA quality scores available (no LLM enrichment, no classical IQA pipeline).  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 96.2%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/nepali-handwritten/](../../scripts/audit/results/nepali-handwritten/)

##### 12. Reliability & Bottlenecks

> **Computed**: 2026-02-12 | **Samples**: 958 | **Avg Min Confidence**: 0.000
>
> **Note**: All samples show as "unreliable" because `text_quality` has 0.000 confidence
> (no IQA pipeline has been run, NH-D005). This is the sole bottleneck field; all other
> enrichment fields were populated by the v3 integration script with confidence 0.80-0.90.
> See Layer 2 Audit Summary (Section 11) above for post-integration quality assessment.

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 958 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 958 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 958 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
