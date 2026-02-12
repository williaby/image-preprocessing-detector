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
- **License Clarity**: Multiple sources cite CC-BY-4.0, requires verification (see Section 10.5)

##### 10. Dataset-Specific Notes

###### 10.1 Annotation Caveats

- **PASCAL VOC Format**: Standard format but requires conversion to COCO for Project A pipeline
- **Bounding Box Granularity**: Dataset documentation unclear on word vs character level
- **XML Validation**: Unknown if all XML files are well-formed (requires testing)
- **Difficult Flag**: PASCAL VOC `<difficult>` flag may be present but usage unclear

###### 10.2 Implementation Notes

- **XML Parsing**: Uses `xml.etree.ElementTree` for bounding box extraction
- **COCO Conversion**: PASCAL VOC `[xmin, ymin, xmax, ymax]` → COCO `[x, y, width, height]`
- **Parser Priority**: Bounding box extraction implemented in NepaliHandwrittenParser
- **Error Handling**: Parser handles malformed XML gracefully with debug logging

###### 10.3 External Resources

- **Kaggle Dataset**: Requires Kaggle API authentication for download
- **GCS Storage**: `gs://image_detection_b/image-preprocessing-detector/datasets/nepali_handwritten/`
- **Related Dataset**: hindi_ocr_synthetic provides printed Devanagari for comparison

###### 10.4 Training Context

- **Phase 10B Usage**: Part of 10-class script detection training
- **Complementary Role**: Real handwriting vs synthetic printed text (hindi_ocr_synthetic)
- **Devanagari Confusers**: Use with CVSI dataset (Bengali, Gujarati, Gurmukhi) for robust training

###### 10.5 License Clarification

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

##### 9. References

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

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 958 | **Avg Min Confidence**: 0.000

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
