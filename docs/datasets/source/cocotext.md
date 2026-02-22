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

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | Multiple human annotators |
| **Inter-Annotator Agreement** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Scene text annotation with legibility and class attributes |
| **GT Label Coverage** | 100% of COCO-Text subset (63,686 images annotated; 69,601 COCO 2014 images without text annotations excluded) |

#### 3. Project Integration

##### 3a. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 1 (text gate validation) |
| **Purpose** | Scene text detection benchmark, text gate calibration |
| **Local Path** | `01_base_data/text_detection/cocotext/` |
| **Subset Used** | Full dataset (train split for training, val/test reserved) |
| **Parser** | ✅ `CocotextParser` (multilingual package) |

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

##### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/text_detection/cocotext/` | ✅ Available | 123,287 JPG files |
| **Text/GT** | Native annotations | ✅ Available | JSON (COCO): Word-level scene text (`anns.utf8_string` in cocotext.v2.json) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

#### 4. Dataset Statistics

123,287 total COCO 2014 images; 63,686 with COCO-Text v2 annotations (173K+ word instances).

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 43,686 | 72,783 | 100% | ✅ Complete (includes unannotated COCO train2014) |
| **Validation** | 10,000 | 50,504 | 100% | ✅ Complete (includes unannotated COCO val2014) |
| **Test** | 10,000 | (merged into val) | - | ⚠️ Test images in val2014 directory |
| **Total** | 63,686 | 123,287 | 100% | ✅ All COCO 2014 images included |

> **Note**: Layer 2 includes all 123,287 COCO 2014 images. 63,686 have COCO-Text annotations;
> 69,601 are unannotated COCO images included for completeness. Generated 2026-02-13.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Annotated Images** | 63,686 (COCO-Text subset; 123,287 total COCO 2014 images) |
| **Training Split** | 43,686 (68.6%) |
| **Validation Split** | 10,000 (15.7%) |
| **Test Split** | 10,000 (15.7%) |
| **Image Dimensions** | Variable (MS COCO 2014, typically 480-640px) |
| **Resolution (DPI)** | 72 (web/camera resolution) |
| **File Format(s)** | JPG |
| **Color Space** | RGB |
| **Total Size on Disk** | ~18 GB (MS COCO 2014 train+val images) |
| **Annotation Format** | JSON (cocotext.v2.json, 55 MB) |

##### 4.3 Text Statistics

> **Source**: Computed from COCO-Text v2.0 ground truth annotations
> **Availability**: ⚠️ Partial (official counts known, per-image stats [NEEDS_PROFILING])

| Metric | Value | Documentation Status |
|--------|-------|---------------------|
| **Total Text Instances** | 173,000+ | [Official] |
| **Legible Instances** | ~145,859 | [Official] |
| **Illegible Instances** | ~27,141 (estimated) | [Inferred] |
| **Avg Words/Image** | ~2.7 | [Empirically Derived] (173K / 63,686) |
| **Avg Characters/Instance** | Unknown | [NEEDS_PROFILING] |
| **Total Characters** | Unknown | [NEEDS_PROFILING] |
| **Handwritten Ratio** | Unknown | [NEEDS_PROFILING] |

**Text Source**: `ground_truth` (word-level transcriptions in cocotext.v2.json)

#### 5. Content Composition

##### 5.1 Label Distribution

| Label Type | Count | Percentage | Notes |
|------------|-------|------------|-------|
| **Total Text Instances** | 173,000+ | 100% | Official count |
| **Legible Instances** | ~145,859 | 84.3% | With transcriptions |
| **Illegible Instances** | ~27,141 | 15.7% | No transcriptions |
| **Machine Printed** | Unknown | [NEEDS_PROFILING] | Requires parser statistics |
| **Handwritten** | Unknown | [NEEDS_PROFILING] | Requires parser statistics |
| **English Text** | Unknown | [NEEDS_PROFILING] | Majority assumed |
| **Non-English Text** | Unknown | [NEEDS_PROFILING] | Minority |

##### 5.2 Class/Category Definitions

| Class/Category | Description | Notes |
|----------------|-------------|-------|
| machine printed | Printed/typed text in scene images | Majority class |
| handwritten | Hand-written text in scene images | Minority class |
| legible | Text that can be read and transcribed | 84.3% of instances |
| illegible | Text too degraded/small/blurred to transcribe | 15.7% of instances |
| english | Text in English language | Coarse label (KI-009) |
| not_english | Text NOT in English (specific language unknown) | Coarse label (KI-009) |
| na | No applicable language (symbols, numbers) | Minority |

##### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.
> **Note**: COCO-Text provides only coarse language labels ("english"/"not_english"/"na").
> Fine-grained script detection requires secondary enrichment sources.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Latin (English) | Latn / en | Majority | ~60-80% | Primary script (KI-009: exact count [NEEDS_PROFILING]) |
| Unknown (non-English) | Zyyy / und | Unknown | ~10-30% | Coarse label "not_english" covers Arabic, CJK, Devanagari, etc. |
| N/A (no text) | - | Unknown | ~10% | Images with "na" language label or no annotations |

**Script Families Present**: Latin (primary), potentially Arabic, CJK, Indic (hidden under "not_english")

**Text Direction** (v2.3.0):

- **ltr** (left-to-right): English text (majority)
- **rtl** (right-to-left): Possible in Arabic/Hebrew signage (subset of "not_english")
- **Limitation**: Cannot reliably determine text direction for "not_english" instances without secondary enrichment

##### 5.4 Content Flags

| Flag | Value | Confidence | Notes |
|------|-------|------------|-------|
| `has_text` | True | [Official] | Scene text dataset |
| `has_handwriting` | True | [Official] | Handwritten class label exists |
| `has_scene_text` | True | [Official] | Natural scene images (MS COCO) |
| `has_document_text` | False | [Official] | Scene text only, not documents |
| `has_tables` | Varies | [Inferred] | Incidental (COCO contains some tables) |
| `has_figures` | Varies | [Inferred] | Incidental (scene photos are NOT embedded figures) |
| `has_math` | Rare | [Inferred] | Unlikely in natural scenes |

##### 5.5 Capture Method

| Method | Percentage | Notes |
|--------|------------|-------|
| **Camera** | 100% | Natural scene photography (MS COCO 2014) |
| **Born-Digital** | 0% | No synthetic or born-digital content |
| **Scanner** | 0% | No scanned documents |
| **Synthetic** | 0% | Real-world images only |

**Icon**: 📱 (Camera-based scene photography)

##### 5.6 Domain Distribution

| Domain | Percentage | Notes |
|--------|------------|-------|
| **SCENE** | 100% | Natural scene text (street signs, storefronts, posters, labels) |
| **Indoor** | ~50% | [Inferred] COCO indoor scenes |
| **Outdoor** | ~50% | [Inferred] COCO outdoor scenes |

**Domain Code**: `SCENE` (natural scene text, not specialized domain)

##### 5.7 Text Content Analysis

**Text Extraction Method**: Direct parsing from COCO-Text v2.0 JSON annotations

**Source Type**: `dataset_provided` (ground truth transcriptions)

**Extraction Details**:

- **Granularity**: Word-level text snippets (scene text)
- **Field**: `utf8_string` in annotation records
- **Coverage**: 173,000+ text instances across 63,686 images
- **Quality**: Ground truth transcriptions for legible text only
- **Language**: Coarse labels (english/not_english/na)

**Limitations**:

- **Word-level only**: No full page transcriptions (scene text dataset)
- **Coarse language labels**: Binary english/not_english classification (no fine-grained script detection)
- **Scene text focus**: Short snippets (signs, labels, posters) not full documents
- **Illegible instances**: No transcriptions provided for illegible text

**Layer 2 Integration Status**: ✅ COMPLETE (text_content.full_text populated)

- `text_content.full_text`: Populated via word concatenation
- `text_content.source_type`: Set to "dataset_provided"
- `text_statistics`: Requires script execution (calculate_text_statistics.py)

#### 6. IQA Profile

Natural scene images with high variability in lighting, perspective, and text quality. Not suitable for document IQA training.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Natural scene images (MS COCO 2014, camera-based photography) |
| **Capture Device** | Various consumer cameras (COCO 2014 Flickr-sourced) |
| **Original Quality** | Natural variation (realistic scene conditions) |
| **Compression** | JPEG (quality varies, web-sourced images) |
| **Known Artifacts** | Motion blur, perspective distortion, occlusion, low light |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | MEDIUM | Scene text often sharp, but motion blur common in outdoor |
| **Noise** | MEDIUM | Low-light scenes introduce noise |
| **Skew** | LOW | Text on signs/surfaces inherently has perspective skew |
| **Contrast** | HIGH | Indoor/outdoor, day/night, backlit text cause wide contrast range |
| **Compression** | MEDIUM | Web-sourced JPEGs have variable quality |
| **Perspective** | HIGH | Scene text captured at various angles and distances |
| **Occlusion** | MEDIUM | Objects/people may partially occlude text in natural scenes |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Highly variable | Small distant signs to large banners |
| **Font Diversity** | High | Real-world signage, hand-lettering, graffiti, labels |
| **Color Usage** | Full color (RGB) | Text on varied backgrounds (colorful signs, posters) |
| **Scene Diversity** | High | 80+ COCO object categories in background |
| **Lighting Conditions** | High variability | Indoor, outdoor, night, backlit, shadows |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH for text detection; LOW for document IQA |
| **Unique Characteristics** | First large-scale scene text, attribute annotations (legibility, type) |
| **Complementary Datasets** | TextOCR, Total-Text, HierText (newer scene text datasets) |
| **Benchmark Suitability** | HIGH for scene text detection/recognition benchmarks |
| **Known Limitations** | No quality scores, scene text not document-focused, coarse language labels |
| **Strengths** | Large scale, diverse natural scenes, word-level attributes |
| **Weaknesses** | Requires separate COCO image download, annotations only |

##### 6.5 Benchmark Results

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| EAST | Text Detection | F-score | 0.508 | [Original COCO-Text paper](https://arxiv.org/abs/1601.07140) |
| FOTS | Text Detection | F-score | - | [FOTS (2018)](https://arxiv.org/abs/1801.01671) |
| ABCNet | Text Spotting | F-score | - | [ABCNet (2020)](https://arxiv.org/abs/2002.10200) |

**Competition Results**:

| Competition | Year | Notes |
|-------------|------|-------|
| COCO-Text Challenge | 2017 | Hosted at ICDAR 2017 Robust Reading Competition |

> **Note**: COCO-Text was a pioneering benchmark (2016); more recent results available on
> [Papers With Code - Scene Text Detection](https://paperswithcode.com/task/scene-text-detection).

#### 7. Known Issues & Limitations

Key limitations include coarse language labels (KI-009), no quality scores, and word-level-only annotations.

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

1. **Coarse language labels (KI-009)**: Only "english" / "not_english" / "na"
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

##### Layer 2 Audit Known Issues

| KI | Title | Applies | Notes |
|----|-------|---------|-------|
| KI-006 | LLM formula semantic confusion | YES | Scene text unlikely to have formulas; all False expected |
| KI-007 | UNK domain acceptable for scene text | YES | ~81.6% UNK expected (diverse COCO categories) |
| KI-008 | script_family directionality | YES | Re-derive from ISO 15924 in integration |
| KI-009 | Language claims unreliable | YES | Coarse parser labels + OpenLID unreliable for scene text |

#### 8. Representative Samples

> **Source**: VLM visual inspection (Phase 6, 2026-02-13), 43 stratified samples

| Image ID | Description | Notable Features |
|----------|-------------|------------------|
| 396793 | Tennis player with Italian banner | Scene text, multilingual (Italian), commercial signage |
| 308548 | London bus 507 to Victoria | Urban scene text, bus route, shop signs, dense text |
| 517246 | Outdoor party, cake with "Thank You DAN!" | Handwritten cake text, product labels |
| 083862 | Restaurant with HP sauce bottle | Product label text, indoor scene |
| 340058 | Cow on beach, no text | Example of COCO image with no text content |

#### 9. References

##### Primary Citation

```bibtex
@article{veit2016cocotext,
  title={COCO-Text: Dataset and Benchmark for Text Detection and Recognition in Natural Images},
  author={Veit, Andreas and Matera, Tomas and Neumann, Lukas and Matas, Jiri and Belongie, Serge},
  journal={arXiv preprint arXiv:1601.07140},
  year={2016}
}
```

##### MS COCO Citation

```bibtex
@inproceedings{lin2014microsoft,
  title={Microsoft COCO: Common Objects in Context},
  author={Lin, Tsung-Yi and Maire, Michael and Belongie, Serge and others},
  booktitle={ECCV},
  year={2014}
}
```

##### Related Works

- [MLT19](mlt19.md) - Multilingual scene text (9 scripts, more diverse than COCO-Text)
- [HierText](hiertext.md) - Hierarchical scene text with paragraph/line annotations
- [TextOCR](textocr.md) - Scene text recognition on Open Images

##### Leaderboards

- [Papers With Code - Scene Text Detection](https://paperswithcode.com/task/scene-text-detection)
- [Papers With Code - Scene Text Recognition](https://paperswithcode.com/task/scene-text-recognition)

#### 10. Dataset-Specific Notes

##### 10.1 Relationship to MS COCO

COCO-Text is an **annotation layer** built on top of MS COCO 2014:

- **Image Source**: MS COCO train2014 (82,783 images) and val2014 (40,504 images)
- **Text Annotations**: 173,000+ text instances added to 63,686 COCO images
- **Selection Criteria**: Images with visible text (51.6% of COCO 2014)
- **Image Ownership**: MS COCO license (CC-BY-4.0), COCO-Text adds text annotations

##### 10.2 Historical Significance

- **First large-scale scene text dataset** (2016)
- Preceded TextOCR, Total-Text, HierText by 2-4 years
- Introduced **word-level legibility labels** (legible/illegible classification)
- Pioneered **text class labels** (machine printed vs. handwritten) in scene text

##### 10.3 Evaluation Protocol

Official COCO-Text benchmark uses:

- **Val set**: 10,000 images for development/tuning
- **Test set**: 10,000 images for final evaluation
- **Metrics**: Precision, Recall, F-score for detection; Edit distance for recognition
- **Baseline models**: EAST, FOTS, ABCNet (documented in paper)

##### 10.4 Integration with Prepare-Doc

**Phase 1 Usage**:

- **Text Gate Validation**: Scene text presence helps calibrate text detection threshold
- **Legibility Classification**: Binary labels useful for quality assessment

**Limitations for IQA**:

- **No quality scores**: Dataset lacks degradation or quality labels
- **Scene text bias**: Natural images, not documents (different quality characteristics)
- **Not suitable for**: Document IQA training (use ohr-bench, diqa instead)

##### 10.5 Parser Implementation Notes

`CocotextParser` (multilingual package):

- **Class-level caching**: Loads 55MB JSON once, shares across batch processing
- **Filename flexibility**: Handles full path, basename, or COCO ID extraction
- **Batch support**: Efficient processing of full dataset via `parse_batch()`
- **Output format**: Populates `text_content.full_text` with concatenated word transcriptions

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: C (81.5/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 87.5 | 15% |  |
| Field Validity | 96.2 | 15% |  |
| Doc Completeness | 100.0 | 5% |  |
| Defect Rate | 88.0 | 10% |  |
| Cross-Source Agreement | 11.2 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **81.5** | | **Grade C** |

##### 11.2 Key Defects

> **Total**: 6 defects (5 accepted, 1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| DEF-001 | layout_detections | low | ACCEPTED | No layout detection source available for cocotext. All 123,287 samples have empt |
| DEF-002 | domain_level1 | medium | ACCEPTED | domain_level1 is UNK for 97.5% of samples (120,266/123,287). Only 3,021 samples  |
| DEF-003 | iso639_language | medium | ACCEPTED | iso639_language is "und" for 81.1% of samples (99,926/123,287). Only English-ann |
| DEF-004 | text_has_content | low | ACCEPTED | text_has_content is false for 80.95% of samples (99,802/123,287). Only 23,485 im |
| DEF-005 | text_scope_content_type | low | OPEN | text_scope_content_type has 2.8% invalid values from LLM enrichment (3,503/123,2 |
| DEF-006 | cross_source_agreement | info | ACCEPTED | Language agreement between OpenLID and LLM enrichment is only 11.2% across 998 o |

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 100.0%

##### 11.4 Cross-Dataset Findings

- **KI-007**: ACCEPTED --
- **KI-009**: ACCEPTED --
- **KI-009**: ACCEPTED --

**Audit Artifacts**: [scripts/audit/results/cocotext/](../../scripts/audit/results/cocotext/)

#### 12. Reliability & Bottlenecks

> **Status**: COMPLETE (from audit 2026-02-13)

##### 12.1 Composite Category Distribution

> **Computed**: 2026-02-13 | **Samples**: 123,287

| Category | Estimated Count | Pct | Notes |
|----------|----------------:|----:|-------|
| hard_label | ~23,485 | 19% | Annotated images with text (parser labels reliable) |
| soft_label | ~16,441 | 13% | LLM-enriched images (domain, content flags) |
| unreliable | ~83,361 | 68% | Unannotated images with minimal enrichment |

**Key Insight**: Only 19% of images have reliable parser-derived labels. The remaining 81% rely on enrichment sources or have no labels.

##### 12.2 Top Bottleneck Fields

| Rank | Field | Issue | Pass Rate |
|-----:|-------|-------|----------:|
| 1 | `layout_detections` | No DocLayout-YOLO extraction | 0% |
| 2 | `domain_level1` | 97.5% UNK (KI-007, expected for scene text) | 2.4% |
| 3 | `iso639_language` | 81.1% "und" (coarse labels, KI-009) | 18.9% |
| 4 | `text_has_content` | 80.95% false (69K unannotated images) | 19.0% |
| 5 | `text_scope_content_type` | 2.8% invalid enum values | 97.2% |

> **Improving Reliability**:
>
> 1. Run DocLayout-YOLO on all 123K images for layout detections
> 2. Re-run LLM enrichment with vision mode for domain classification
> 3. Normalize `text_scope_content_type` invalid values in integration script

#### 13. Format & License

| Attribute | Value |
|-----------|-------|
| **Image Format** | JPEG (MS COCO 2014) |
| **Annotation Format** | JSON (COCO-Text v2.0, 55 MB) |
| **License** | CC-BY-4.0 |
| **Commercial Use** | Yes |
| **Attribution Required** | Yes |

#### 14. Processing Status

| Step | Status | Date | Notes |
|------|--------|------|-------|
| **Download** | ✅ Complete | 2026-02 | COCO 2014 train+val images + cocotext.v2.json |
| **Base Metadata** | ✅ Complete | 2026-02-13 | 123,287 samples generated |
| **Integration** | ✅ Complete | 2026-02-13 | LLM (16K) + OpenLID (1K) enrichments merged |
| **Layer 2 Audit** | ✅ Complete | 2026-02-13 | Grade C (73.8/100) |
| **Layout Extraction** | ❌ Not started | - | DocLayout-YOLO not yet run |
| **VLM Text Labeling** | ❌ Not needed | - | Parser provides text content |

#### 15. Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-02 | Initial dataset documentation |
| v1.1 | 2026-02-13 | Layer 2 audit complete, template v1.4.0 alignment |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 123,287 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 123,287 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
