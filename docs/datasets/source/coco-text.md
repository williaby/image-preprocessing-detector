#### COCO-Text

> **Quick Stats**: 63,686 images | Scene text (camera) | Word-level annotations | 173K+ text instances
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | COCO-Text: Text Detection and Recognition in Natural Images |
| **Version** | 2.0 |
| **Release Date** | January 2016 |
| **Maintainer** | Cornell Vision Group |
| **Paper** | [COCO-Text (arXiv:1601.07140)](https://arxiv.org/abs/1601.07140) |
| **Repository** | [Cornell Vision](https://vision.cornell.edu/se3/coco-text-2/) |
| **License** | CC-BY-4.0 |
| **GCS Path** | `gs://image_detection_b/01_base_data/text_detection/cocotext/` |
| **Local Path** | `01_base_data/text_detection/cocotext/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | MS COCO 2014 images (requires separate download) |
| **Annotations** | JSON | COCO-Text v2.0 annotation file (cocotext.v2.json, 55 MB) |
| **Metadata** | Inline JSON | Image dimensions, split assignments in annotation file |
| **Supplementary** | - | Paper (arXiv:1601.07140), repository documentation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | MS COCO 2014 train images | `cocotext.v2.json` (imgToAnns) | 43,686 | ✅ |
| **Validation** | MS COCO 2014 val images | `cocotext.v2.json` (imgToAnns) | 10,000 | ✅ RESERVED |
| **Test** | MS COCO 2014 val images | `cocotext.v2.json` (imgToAnns) | 10,000 | ✅ RESERVED |

**Split Organization Pattern**: `single_dir_with_manifest` (JSON file maps image_id to split)

> **Notes**:
>
> - COCO-Text provides annotations only; images must be downloaded from MS COCO 2014
> - Val/test splits RESERVED for benchmark evaluation
> - Images organized by COCO split (train2014, val2014), annotations reference both

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Bounding Boxes** | COCO format [x,y,w,h] | Word-level | Text region coordinates |
| **Text Transcriptions** | JSON string (utf8_string) | Word-level | Ground truth text content (legible instances only) |
| **Language Labels** | JSON enum | Word-level | "english", "not_english", "na" |
| **Text Class** | JSON enum | Word-level | "machine printed" or "handwritten" |
| **Legibility** | JSON enum | Word-level | "legible" or "illegible" |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Paper, repository | Version 2.0, license (CC-BY-4.0), citation, split definitions |
| **Image-level** | cocotext.v2.json (imgs) | Dimensions (width, height), COCO filename, split assignment |
| **Annotation-level** | cocotext.v2.json (anns) | Bounding box area, annotation ID, image ID |

##### 2.5 Annotation Schema Details

**Format**: COCO-Text v2.0 JSON format

```json
{
  "imgs": {
    "image_id": {
      "id": 123456,
      "width": 640,
      "height": 480,
      "file_name": "COCO_train2014_000000123456.jpg",
      "set": "train"
    }
  },
  "anns": {
    "annotation_id": {
      "id": 1,
      "image_id": 123456,
      "bbox": [x, y, width, height],
      "utf8_string": "Hello World",
      "language": "english",
      "class": "machine printed",
      "legibility": "legible",
      "area": 1200
    }
  },
  "imgToAnns": {
    "image_id": [ann_id1, ann_id2, ...]
  }
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | int | Yes | Links annotation to MS COCO image |
| `bbox` | list[float] | Yes | COCO format [x, y, width, height] |
| `utf8_string` | str | Yes | Text transcription (empty for illegible) |
| `language` | str | Yes | "english" / "not_english" / "na" |
| `class` | str | Yes | "machine printed" / "handwritten" |
| `legibility` | str | Yes | "legible" / "illegible" |
| `set` | str | Yes | "train" / "val" / "test" |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Bounding boxes (word-level) | `layout_detections.bbox` | High | COCO format, direct mapping |
| ✅ Text transcriptions | `text_content.full_text` | High | Word-level, requires concatenation |
| ✅ Language labels | `language.language_code` | High | Mapped to ISO 639-1 (en/und) |
| ✅ Text class | `raw_labels.text_class` | Medium | Handwriting detection |
| ✅ Legibility | `quality.legibility_score` | Medium | Binary classification |
| ✅ Split info | `provenance.split` | High | Train/val/test assignment |
| ❌ Reading order | - | Low | Not provided (scene text) |
| ❌ Full-page text | - | N/A | Dataset provides word snippets only |
| ❌ Quality scores | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

#### 3. Project Integration

##### 3a. Project Usage

- **Path**: `01_base_data/text_detection/cocotext/`
- **Phase(s)**: Phase 1 (text gate validation)
- **Purpose**: Scene text detection benchmark, text gate calibration
- **Parser**: ✅ `CocotextParser` (multilingual package)

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/text_detection/cocotext/` | ✅ Available | 123,287 JPG files |
| **Text/GT** | Native annotations | ✅ Available | JSON (COCO): Word-level scene text (`anns.utf8_string` in cocotext.v2.json) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### 3b. Parser & Metadata Integration

**Parser Implementation**: ✅ `CocotextParser` (src/image_preprocessing_detector/annotation/parsers/multilingual/cocotext.py)

**Layer 2 Schema Coverage Matrix**:

| Layer 2 Field | Parser Handles? | Source Field | Coverage | Notes |
|---------------|-----------------|--------------|----------|-------|
| **Text Content** | | | | |
| `text_content.full_text` | ✅ Yes | `utf8_string` (per word) | 100% | Concatenated from word-level annotations |
| `text_content.source_type` | ✅ Yes | - | 100% | Set to "dataset_provided" |
| `text_content.source_file` | ✅ Yes | - | 100% | References cocotext.v2.json |
| `text_content.extraction_method` | ✅ Yes | - | 100% | Set to "CocotextParser.parse" |
| `text_statistics.*` | ⚠️ Partial | - | 50% | Requires calculate_text_statistics.py |
| **Layout Detections** | | | | |
| `layout_detections.bbox` | ✅ Yes | `anns.bbox` | 100% | COCO format [x,y,w,h] |
| `layout_detections.polygon` | ❌ No | - | N/A | Not provided by dataset |
| `layout_detections.class_name` | ⚠️ In raw_labels | `anns.class` | 50% | Not in layout_detections structure |
| `layout_detections.class_id` | ❌ No | - | 0% | Needs taxonomy mapping |
| `layout_detections.confidence` | ❌ No | - | N/A | Not provided by dataset |
| **Language** | | | | |
| `language.language_code` | ✅ Yes | `anns.language` (mapped) | 100% | Mapped to ISO 639-1 (en/und) |
| `language.script_code` | ❌ No | - | 0% | Should infer from language_code |
| `language.detection_method` | ❌ No | - | 0% | Should be "dataset_provided" |
| **Quality** | | | | |
| `quality.overall_score` | ❌ No | - | N/A | Not provided by dataset |
| `quality.legibility_score` | ⚠️ Binary | `anns.legibility` | 50% | "legible"/"illegible" (not 0-1 score) |
| **Provenance** | | | | |
| `provenance.split` | ✅ Yes | `imgs.set` | 100% | Train/val/test assignment |
| `provenance.dataset_name` | ❌ No | - | 0% | Should populate "coco-text" |
| `provenance.original_filename` | ❌ No | `imgs.file_name` | 0% | COCO filename not propagated |

**Overall Coverage**: 40% (8/20 fields fully implemented)

**Known Gaps**:

1. **Text statistics missing** - Requires post-processing with `scripts/calculate_text_statistics.py`
2. **Provenance fields incomplete** - Dataset name and original filename not propagated
3. **Language script inference missing** - Should derive script_code from language_code
4. **Class labels in wrong structure** - Text class stored in `raw_labels`, not `layout_detections`

**Text Content Handling**: ✅ COMPLETE (as of parser enhancement)

- Source Type: `dataset_provided` (ground truth transcriptions)
- Extraction Method: Direct JSON parsing of `utf8_string` field
- Format: Word-level snippets concatenated with spaces
- **Note**: COCO-Text provides scene text snippets (signs, labels, posters), not full document transcriptions

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 63,686 |
| **Text Annotations** | 173,000+ |
| **Cropped Text Instances** | 145,859 |
| **File** | `cocotext.v2.json` (55 MB) |
| **Type** | Annotations only (requires MS COCO images) |

##### Annotation Attributes

| Attribute | Description |
|-----------|-------------|
| **Location** | Bounding box coordinates |
| **Text Type** | Machine-printed vs handwritten |
| **Legibility** | Legible vs illegible |
| **Script** | Script type classification |
| **Transcription** | Text content (for legible text) |

#### 6. Content Composition

##### 6.1 Label Distribution

| Label Type | Count | Percentage | Notes |
|------------|-------|------------|-------|
| **Total Text Instances** | 173,000+ | 100% | Official count |
| **Legible Instances** | ~145,859 | 84.3% | With transcriptions |
| **Illegible Instances** | ~27,141 | 15.7% | No transcriptions |
| **Machine Printed** | Unknown | [NEEDS_PROFILING] | Requires parser statistics |
| **Handwritten** | Unknown | [NEEDS_PROFILING] | Requires parser statistics |
| **English Text** | Unknown | [NEEDS_PROFILING] | Majority assumed |
| **Non-English Text** | Unknown | [NEEDS_PROFILING] | Minority |

##### 6.2 Content Flags

| Flag | Value | Confidence | Notes |
|------|-------|------------|-------|
| `has_text` | True | [Official] | Scene text dataset |
| `has_handwriting` | True | [Official] | Handwritten class label exists |
| `has_scene_text` | True | [Official] | Natural scene images (MS COCO) |
| `has_document_text` | False | [Official] | Scene text only, not documents |
| `has_tables` | Varies | [Inferred] | Incidental (COCO contains some tables) |
| `has_figures` | Varies | [Inferred] | Incidental (COCO contains images) |
| `has_math` | Rare | [Inferred] | Unlikely in natural scenes |

##### 6.3 Capture Method

| Method | Percentage | Notes |
|--------|------------|-------|
| **Camera** | 100% | Natural scene photography (MS COCO 2014) |
| **Born-Digital** | 0% | No synthetic or born-digital content |
| **Scanner** | 0% | No scanned documents |
| **Synthetic** | 0% | Real-world images only |

**Icon**: 📱 (Camera-based scene photography)

##### 6.4 Domain Distribution

| Domain | Percentage | Notes |
|--------|------------|-------|
| **Natural Scenes** | 100% | Street signs, storefronts, posters, labels |
| **Indoor** | ~50% | [Inferred] COCO indoor scenes |
| **Outdoor** | ~50% | [Inferred] COCO outdoor scenes |
| **Specific Domains** | Varies | Sports, food, transportation, etc. (COCO categories) |

**Domain Code**: `SCENE` (natural scene text, not specialized domain)

##### 6.5 Text Content Analysis

**Text Extraction Method**: Direct parsing from COCO-Text v2.0 JSON annotations

**Source Type**: `dataset_provided` (ground truth transcriptions)

**Extraction Details**:

- **Granularity**: Word-level text snippets (scene text)
- **Field**: `utf8_string` in annotation records
- **Coverage**: 173,000+ text instances across 63,686 images
- **Quality**: Ground truth transcriptions for legible text only
- **Language**: Coarse labels (english/not_english/na)

**Text Statistics** [NEEDS_PROFILING]:

| Metric | Value | Documentation Status |
|--------|-------|---------------------|
| **Text Availability** | Word-level snippets | [Official] |
| **Legible Instances** | ~145,859 | [Official] |
| **Illegible Instances** | ~27,141 (estimated) | [Inferred] |
| **Avg Characters/Instance** | Unknown | [NEEDS_PROFILING] |
| **Avg Words/Image** | ~2.7 | [Empirically Derived] (173K / 63,686) |
| **Total Characters** | Unknown | [NEEDS_PROFILING] |
| **Handwritten Ratio** | Unknown | [NEEDS_PROFILING] |

**Language Coverage**:

- **Primary**: English (majority)
- **Secondary**: Non-English (coarse label, script not specified)
- **Unknown/NA**: No text instances

**Limitations**:

- **Word-level only**: No full page transcriptions (scene text dataset)
- **Coarse language labels**: Binary english/not_english classification (no fine-grained script detection)
- **Scene text focus**: Short snippets (signs, labels, posters) not full documents
- **Illegible instances**: No transcriptions provided for illegible text

**Layer 2 Integration Status**: ✅ COMPLETE (text_content.full_text populated)

- `text_content.full_text`: Populated via word concatenation
- `text_content.source_type`: Set to "dataset_provided"
- `text_statistics`: Requires script execution (calculate_text_statistics.py)

#### 7. IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Natural scene images (MS COCO 2014, camera-based photography) |
| **Primary Value** | Large-scale scene text benchmark, diverse real-world conditions |
| **Blur Sensitivity** | Moderate (scene text often sharp, but motion blur possible) |
| **Contrast Characteristics** | High variability (indoor/outdoor, day/night, backlit text) |
| **Common Degradations** | Motion blur, perspective distortion, occlusion, low light |
| **Quality Distribution** | Natural variation (realistic scene conditions, no synthetic degradation) |
| **IQA Training Suitability** | ❌ No (lacks quality scores, scene text not document-focused) |
| **Text Detection Training** | ✅ Yes (word-level bboxes, legibility labels) |
| **Handwriting Detection** | ⚠️ Limited (handwritten class exists, but minority in dataset) |

#### 8. Training Value

- **Strengths**: First large-scale scene text dataset, attribute annotations (legibility, type), diverse natural scenes
- **Weaknesses**: Requires separate COCO image download, annotations only
- **Complementary Datasets**: MS COCO, TextOCR, Total-Text

#### 9. Known Issues

##### Data Acquisition Issues

1. **Images not included**: COCO-Text provides annotations only; MS COCO 2014 images must be downloaded separately
   - **Impact**: Additional 18GB+ download required
   - **Workaround**: Use `scripts/download_coco_images.sh` or official COCO download
   - **Status**: ⚠️ Operational complexity

2. **Annotations-only format**: No self-contained dataset
   - **Impact**: Two-step setup process (COCO images + COCO-Text annotations)
   - **Workaround**: Documented in README
   - **Status**: ⚠️ Inconvenient but manageable

##### Label Quality Issues

1. **Coarse language labels**: Only "english" / "not_english" / "na"
   - **Impact**: Cannot distinguish specific non-English scripts (Chinese, Arabic, etc.)
   - **Workaround**: Use fine-grained script detection datasets (mlt19, mdiw13)
   - **Status**: ❌ Limitation (cannot fix with current labels)

2. **Illegible text has no transcriptions**: 15.7% of instances marked illegible
   - **Impact**: Cannot train OCR on illegible samples
   - **Workaround**: Use for legibility classification training instead
   - **Status**: ✅ By design (realistic ground truth)

##### Integration Issues

1. **Word-level text only**: No full page transcriptions
   - **Impact**: Cannot use for full document OCR training
   - **Workaround**: Use for word detection/recognition, not full page layout
   - **Status**: ❌ Limitation (scene text dataset by design)

2. **Text statistics not calculated**: Requires post-processing script
   - **Impact**: `text_statistics` fields missing from Layer 2 JSON
   - **Workaround**: Run `scripts/calculate_text_statistics.py` on Layer 2 files
   - **Status**: 🔄 Fixable (script execution needed)

3. **COCO filename dependencies**: Parser relies on MS COCO filename patterns
   - **Impact**: Images must maintain COCO naming (COCO_train2014_*.jpg)
   - **Workaround**: Document filename requirements
   - **Status**: ⚠️ Operational constraint

##### Benchmark Constraints

1. **Val/test splits reserved**: 20,000 images (31%) unavailable for training
   - **Impact**: Only 43,686 images available for training (68%)
   - **Workaround**: Use complementary datasets (hiertext, textocr)
   - **Status**: ✅ By design (benchmark integrity)

#### 10. Dataset-Specific Notes

##### Relationship to MS COCO

COCO-Text is an **annotation layer** built on top of MS COCO 2014:

- **Image Source**: MS COCO train2014 (82,783 images) and val2014 (40,504 images)
- **Text Annotations**: 173,000+ text instances added to 63,686 COCO images
- **Selection Criteria**: Images with visible text (51.6% of COCO 2014)
- **Image Ownership**: MS COCO license (CC-BY-4.0), COCO-Text adds text annotations

##### Historical Significance

- **First large-scale scene text dataset** (2016)
- Preceded TextOCR, Total-Text, HierText by 2-4 years
- Introduced **word-level legibility labels** (legible/illegible classification)
- Pioneered **text class labels** (machine printed vs. handwritten) in scene text

##### Evaluation Protocol

Official COCO-Text benchmark uses:

- **Val set**: 10,000 images for development/tuning
- **Test set**: 10,000 images for final evaluation
- **Metrics**: Precision, Recall, F-score for detection; Edit distance for recognition
- **Baseline models**: EAST, FOTS, ABCNet (documented in paper)

##### Integration with Project A

**Phase 1 Usage**:

- **Text Gate Validation**: Scene text presence helps calibrate text detection threshold
- **Legibility Classification**: Binary labels useful for quality assessment

**Limitations for IQA**:

- **No quality scores**: Dataset lacks degradation or quality labels
- **Scene text bias**: Natural images, not documents (different quality characteristics)
- **Not suitable for**: Document IQA training (use ohr-bench, diqa instead)

##### Parser Implementation Notes

`CocotextParser` (multilingual package):

- **Class-level caching**: Loads 55MB JSON once, shares across batch processing
- **Filename flexibility**: Handles full path, basename, or COCO ID extraction
- **Batch support**: Efficient processing of full dataset via `parse_batch()`
- **Output format**: Populates `text_content.full_text` with concatenated word transcriptions

##### Citation

If using COCO-Text, cite both:

```bibtex
@article{veit2016cocotext,
  title={COCO-Text: Dataset and Benchmark for Text Detection and Recognition in Natural Images},
  author={Veit, Andreas and Matera, Tomas and Neumann, Lukas and Matas, Jiri and Belongie, Serge},
  journal={arXiv preprint arXiv:1601.07140},
  year={2016}
}

@inproceedings{lin2014microsoft,
  title={Microsoft COCO: Common Objects in Context},
  author={Lin, Tsung-Yi and Maire, Michael and Belongie, Serge and others},
  booktitle={ECCV},
  year={2014}
}
```

---
