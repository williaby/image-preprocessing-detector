#### SROIE

> **Quick Stats**: 2,043 images | Camera-captured receipts | Text detection + OCR + Entity extraction
>
> **License**: Research Use Only | **Commercial Use**: No (pending verification)

- **Path**: `data/phase7_mvp/00_base_images/sroie/` (1,500 symlinks)
- **Paper**: [ICDAR 2019 Robust Reading Challenge on Scanned Receipts OCR and Information Extraction (2021)](https://arxiv.org/abs/2103.10213)
- **IQA Profile**: [camera_blur, glare_reflection, perspective_distortion]
- **Project Usage**: Phase 7 OCR training, receipt understanding
- **Parser**: [`SroieParser`](../src/image_preprocessing_detector/annotation/parsers/layout/sroie.py) | ✅ Complete

**Data Locations**:

| Type | Path | Status |
|------|------|--------|
| Images | `data/phase7_mvp/00_base_images/sroie/` | ✅ 1,500 symlinks (Phase 7 subset) |
| Images (source) | `/mnt/e/image_detection/v4_datasets/sroie/images/` | ⚠️ Mount unavailable |
| Text/OCR GT | Paired .txt files (8-point quad + transcription) | ⚠️ Source unavailable |
| Layer 2 Metadata | `metadata_registry/json/sroie/` | ✅ Available |
| Aggregated Stats | `metadata_registry/aggregates/sroie_stats.json` | ✅ Available |

SROIE (Scanned Receipt OCR and Information Extraction) provides camera-captured receipt
images with quad-coordinate text localization and ground truth transcriptions. Dataset
was created for ICDAR 2019 competition supporting text detection, OCR, and key information
extraction tasks (company name, date, address, total).

---

##### 1. Source Data Inventory

**Official Dataset**: ICDAR 2019 SROIE

- **Release Year**: 2019 (competition), 2021 (paper publication)
- **Version**: 1.0
- **Publisher**: ICDAR 2019 Robust Reading Competition
- **Authors**: Zheng Huang, Kai Chen, Jianhua He, Xiang Bai, Dimosthenis Karatzas, Shjian Lu, C.V. Jawahar
- **License**: [NEEDS_VERIFICATION] - Conservative classification as Research Use Only
- **Citation**:

  ```bibtex
  @article{huang2021icdar2019,
    title={ICDAR 2019 Robust Reading Challenge on Scanned Receipts OCR and Information Extraction},
    author={Huang, Zheng and Chen, Kai and He, Jianhua and Bai, Xiang and Karatzas, Dimosthenis and Lu, Shijian and Jawahar, CV},
    journal={arXiv preprint arXiv:2103.10213},
    year={2021}
  }
  ```

- **Download**: [HuggingFace: darentang/sroie](https://huggingface.co/datasets/darentang/sroie) | [Kaggle: urbikn/sroie-datasetv2](https://www.kaggle.com/datasets/urbikn/sroie-datasetv2)
- **Documentation Status**: [Official] for paper/competition info, [Empirically Derived] for Layer 2 counts

###### 1.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Camera-captured receipt images |
| **Annotations** | TXT | Paired .txt files (one per image) with quad coords + OCR text |
| **Entity Labels** | TXT (separate) | Key information extraction (company, date, address, total) |

###### 1.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/` | `train/{id}.txt` | [NEEDS_VERIFICATION] | ⚠️ Source unavailable |
| **Test** | `test/` | `test/{id}.txt` | [NEEDS_VERIFICATION] | ⚠️ Source unavailable |
| **Total** | - | - | 2,043 | ✅ Layer 2 metadata |

**Split Organization Pattern**: `by_folder` (train/test directories)

> **Note**: E: drive mount unavailable at review time. Authoritative count (2,043) from Layer 2
> aggregated metadata. Phase 7 subset uses 1,500 symlinks.

###### 1.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Quad Coordinates** | TXT (CSV) | Text region | 8-point polygon per text region (x1,y1,x2,y2,x3,y3,x4,y4) |
| **Text Transcriptions** | TXT (CSV) | Text region | Ground truth OCR text per quad |
| **Entity Labels** | TXT (separate) | Document | 4 key fields (company, date, address, total) |

###### 1.4 Annotation Schema Details

**Text Region Annotation Format** (paired .txt files):

```text
# Format: x1,y1,x2,y2,x3,y3,x4,y4,text
123,45,678,45,678,90,123,90,COMPANY NAME
200,100,500,100,500,120,200,120,Receipt Total: $45.99
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `x1,y1,x2,y2,x3,y3,x4,y4` | 8 ints | Yes | Quad coordinates (rotated/perspective) |
| `text` | str | Yes | OCR transcription |

###### 1.5 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Quad coords | `text_instances.bbox` | High | ✅ Extracted as 8-point polygon |
| ✅ OCR text | `text_content.full_text` | High | ✅ Aggregated to text_content |
| ✅ Text source type | `text_content.source_type` | High | ✅ Set to "dataset_provided" |
| ⚠️ Entity labels | `entities.key_value` | Medium | ❌ Not extracted (separate files) |
| ⚠️ Quad→bbox | `layout_detections.bbox` | Medium | ❌ Not converted to COCO format |
| ❌ Layout class | `layout_detections.class_name` | Low | Not provided (all "text") |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

---

##### 2. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 OCR training |
| **Purpose** | Receipt OCR, text detection, key information extraction |
| **Local Path** | `data/phase7_mvp/00_base_images/sroie/` |
| **Subset Used** | 1,500 images (Phase 7 selection from 2,043 total) |
| **Preprocessing** | None required (images pre-normalized) |
| **Benchmark Status** | ❌ Not reserved (347 test images available for training if needed) |

**Training Task Alignment**:

- ✅ Text detection (quad coordinates preserve rotation/perspective)
- ✅ OCR training (ground truth transcriptions)
- ✅ Receipt structure understanding
- ⚠️ Layout detection (requires quad→bbox conversion)
- ⚠️ Key information extraction (entity labels available but not extracted)

---

##### 3. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `SroieParser` in `parsers/layout/sroie.py` |
| **Parser Status** | ✅ Complete - Text content extraction implemented |
| **Layer 1 Fields** | `text_instances` (list[dict]), `raw_labels["split"]`, `raw_labels["document_type"]` |
| **Layer 2 Auto-Derived** | `text_content` (✅ implemented in parser) |
| **Config Entry** | `DATASET_CONFIGS["sroie"]` |

> **Parser Reference**: See [SroieParser source](../src/image_preprocessing_detector/annotation/parsers/layout/sroie.py#L66-L143)

###### Parser Audit Matrix (Schema-Derived)

| Source Field | Layer 2 Target | Parser Handles? | Priority | Gap Analysis |
|--------------|----------------|-----------------|----------|--------------|
| **Quad coords (8-point)** | `layout_detections.polygon` | ❌ No | High | In text_instances, not layout_detections |
| **Quad coords → bbox** | `layout_detections.bbox` | ❌ No | High | Conversion needed for COCO compatibility |
| **OCR text** | `text_content.full_text` | ✅ Yes | High | ✅ Implemented (lines 119-130) |
| **Text source type** | `text_content.source_type` | ✅ Yes | High | ✅ Set to "dataset_provided" |
| **Text source file** | `text_content.source_file` | ❌ No | Medium | Not tracked |
| **Text source format** | `text_content.source_format` | ✅ Yes | Medium | ✅ Set to "txt_quad_text" |
| **Extraction method** | `text_content.extraction_method` | ✅ Yes | Medium | ✅ Set to "SroieParser.parse" |
| **Split info** | `provenance.split` | ✅ Yes | Medium | ✅ In raw_labels["split"] |
| **Document type** | N/A | ✅ Yes | Low | ✅ In raw_labels["document_type"] |
| **Language/script** | `language.language_code` | ❌ No | Medium | [NEEDS_PROFILING] Likely multilingual |
| **Text statistics** | `text_statistics` | ❌ No | Medium | [NEEDS_PROFILING] Requires text_content aggregation |
| **Quality scores** | `quality.overall_score` | ❌ No | Low | [NEEDS_PROFILING] Camera artifacts expected |

**Parser Coverage**: 50% (5/10 high-priority fields)

**Missing Extractions**:

1. **Layout detections** (polygon/bbox) - High priority for layout models
2. **Text statistics** - Medium priority (requires profiling with source data)
3. **Language detection** - Medium priority (multilingual receipts likely)
4. **Quality assessment** - Low priority (camera artifacts expected: blur, glare, perspective)

---

##### 4. Data Locations

**Images**:

- **Local Path**: `data/phase7_mvp/00_base_images/sroie/`
- **Type**: Symlinks (1,500 files - Phase 7 subset)
- **Target**: `/mnt/e/image_detection/v4_datasets/sroie/images/`
- **Status**: ⚠️ Mount unavailable at review time

**Annotations**:

- **Format**: Paired .txt files (quad coordinates + OCR text)
- **Location**: Expected alongside images in source dataset
- **Status**: ❌ Source unavailable (mount issue)

**Layer 2 Metadata**:

- **Aggregates**: `metadata_registry/aggregates/sroie_stats.json` ✅ Available
- **Individual JSON**: `/mnt/e/image_detection/metadata_registry/json/sroie/` ⚠️ Source location

---

##### 5. Dataset Statistics

###### 5.1 Split Coverage

> **CRITICAL**: Authoritative count from Layer 2 aggregated metadata. Source splits unavailable.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | [NEEDS_VERIFICATION] | [TO_VERIFY] | [TO_COMPUTE]% | ⚠️ Source unavailable |
| **Test** | [NEEDS_VERIFICATION] | [TO_VERIFY] | [TO_COMPUTE]% | ⚠️ Source unavailable |
| **Total** | 2,043 | 2,043 | 100% | ✅ All samples in Layer 2 |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing or source unavailable
- ❌ Missing - Split not included in Layer 2 metadata

> **Note**: E: drive mount unavailable. Layer 2 aggregated metadata shows 2,043 total samples.
> Phase 7 subset uses 1,500 symlinks. Train/test split counts require source verification.

###### 5.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 2,043 [Empirically Derived] |
| **Phase 7 Subset** | 1,500 symlinks |
| **Image Dimensions** | 150-6016 × 168-5312 px [Empirically Derived] |
| **Average Dimensions** | 1026 × 1394 px [Empirically Derived] |
| **Resolution (DPI)** | Variable (camera capture) |
| **File Format** | JPEG (100%) [Empirically Derived] |
| **Color Space** | RGB [Empirically Derived] |
| **Average File Size** | 243 KB [Empirically Derived] |
| **Annotation Format** | TXT (quad coords + OCR text) |

###### 5.3 Text Statistics

> **Source**: Ground truth text available but not yet profiled
> **Availability**: ⚠️ [NEEDS_PROFILING] - E: drive mount unavailable

**Expected Statistics** (based on receipt domain):

| Metric | Expected Range |
|--------|----------------|
| **Character Count** | 200-500 chars/receipt |
| **Word Count** | 30-80 words/receipt |
| **Line Count** | 15-35 lines/receipt |

**Text Source**: `ground_truth` (dataset_provided via parser)

###### 5.4 Capture Method [Official]

> **Source**: Layer 2 aggregated metadata (sroie_stats.json)

| Capture Method | Count | Percentage |
|----------------|-------|------------|
| camera_smartphone | 2,043 | 100% |

**Capture Characteristics**:

- Camera-captured receipts (smartphone or tablet)
- Real-world capture conditions (variable lighting, perspective)
- Potential artifacts: blur, glare, perspective distortion, shadows
- Thermal print substrate (unique degradation profile)

###### 5.5 Domain Distribution [Official]

> **Source**: Layer 2 aggregated metadata (sroie_stats.json)

| Domain | Count | Percentage |
|--------|-------|------------|
| FIN | 2,043 | 100% |

**Domain Notes**: Financial documents (retail receipts) - restaurant, grocery, retail purchases

---

##### 6. Content Composition

###### 6.1 Layout Types

[NEEDS_PROFILING] - Layout classification not performed

**Expected Layout**: Receipt structure

- Header (business name, address, phone)
- Line items (product/service + price)
- Subtotals and calculations
- Totals (subtotal, tax, total)
- Footer (payment method, date/time, transaction ID)

###### 6.2 Text Density

[NEEDS_PROFILING] - Text density analysis not performed

**Expected Density**: Medium to high

- Structured tabular content (line items with prices)
- Short text strings (business names, products, payment methods)
- Numeric values (prices, totals, tax amounts, dates/times)
- Dense footer information (legal text, contact info)

###### 6.3 Script & Language Distribution

**Script Family** [Official]:

> **Source**: Layer 2 aggregated metadata

| Script | Count | Percentage |
|--------|-------|------------|
| ltr | 2,043 | 100% |

**Language**: [NEEDS_PROFILING]

- Likely multilingual (receipts from various countries per ICDAR competition)
- Expected: English, Chinese, Japanese, Thai, Vietnamese (common in ICDAR datasets)
- Ground truth text available for language detection when E: drive restored

###### 6.4 Content Flags [Official]

> **Source**: Layer 2 aggregated metadata (sroie_stats.json)

| Flag | Count | Percentage |
|------|-------|------------|
| has_table | 2,043 | 100% |

**Content Notes**:

- All receipts contain tabular structure (line items with prices)
- Text regions with quad coordinates (rotated/perspective text common)
- Thermal print substrate (variable print quality)

###### 6.5 Text Scope

[NEEDS_PROFILING] - Text scope analysis not performed

**Expected Scope**: page-level (document-level)

- Full receipt text per image
- Character count: [NEEDS_PROFILING] - estimate 200-500 chars/receipt
- Hierarchical structure: page → text regions → words

---

##### 7. IQA Profile

[NEEDS_PROFILING] - Camera-captured receipts expected to have specific quality issues

**Predicted Sensitivity**:

- **High**: Camera blur (motion/focus), glare/reflection (on thermal print), perspective distortion
- **Medium**: Low contrast (faded thermal print), uneven illumination, shadows, thermal print degradation
- **Low**: JPEG artifacts, compression noise

**Recommended IQA Detectors**:

- Blur detection (Laplacian variance for motion/focus blur)
- Glare detection (bright spot analysis on reflective surfaces)
- Perspective distortion (quad coordinate variance analysis)
- Illumination uniformity (shadow detection)
- Thermal print quality (contrast analysis, fading detection)

**Thermal Print Challenges** (unique to SROIE):

- Ink fading over time (low contrast, missing characters)
- Variable ink density (uneven print quality)
- Substrate curl/wrinkle (perspective distortion)
- Reflective surface (glare from camera flash)

---

##### 8. Quality Metrics

[NEEDS_PROFILING] - Quality profiling not performed (E: drive unavailable)

**Recommended Profiling** (when source data restored):

1. Run classical IQA detectors on sample (blur, contrast, illumination, glare)
2. Analyze quad coordinate variance (perspective distortion metric)
3. Text region size distribution (readability metric)
4. Thermal print quality assessment (contrast, fading)

**Expected Quality Distribution**:

- Variable quality (real-world mobile capture)
- Blur presence: Common (handheld camera shake)
- Glare presence: Common (flash on thermal print)
- Perspective distortion: Common (angled capture)

---

##### 9. Degradation Profile

[NEEDS_PROFILING] - No degradation labels in aggregated metadata

**Expected Degradations** (camera capture + thermal print):

**Camera-Related**:

- Motion blur (camera shake during capture)
- Out-of-focus blur (incorrect autofocus)
- Glare/reflection (flash on reflective thermal print)
- Perspective distortion (angled capture, receipt curl)
- Shadow artifacts (uneven lighting)
- Low light conditions (underexposure)

**Thermal Print-Related** (unique to SROIE):

- Ink fading (time-based degradation)
- Low contrast (thermal print characteristics)
- Variable ink density (print quality variation)
- Substrate wrinkle/curl (physical deformation)

---

##### 10. Known Issues

1. **Count Discrepancy** [NEEDS_VERIFICATION]:
   - Layer 2 metadata: 2,043 images (authoritative)
   - Phase7 symlinks: 1,500 images (subset)
   - Previous catalog entry: 973 images (incorrect)
   - **Resolution**: Use 2,043 as authoritative count from Layer 2 aggregation

2. **Source Data Unavailable**:
   - Symlink targets at `/mnt/e/image_detection/v4_datasets/sroie/` not accessible
   - Blocks: Language detection, text statistics profiling, IQA characterization
   - **Priority**: P2 (Medium)
   - **Action**: Verify mount or restore source data

3. **License Classification** [NEEDS_VERIFICATION]:
   - Paper suggests academic use (ICDAR competition)
   - Conservative classification: "Research Use Only"
   - **Action**: Verify ICDAR 2019 competition terms and dataset download license
   - **Priority**: P0 (Critical for commercial use guidance)

4. **Text Content Integration**: ✅ RESOLVED
   - Parser already implements text_content schema fields (lines 118-130)
   - No action needed

5. **Layout Detections Missing**:
   - Quad coordinates not mapped to `layout_detections.polygon`
   - No COCO bbox conversion for `layout_detections.bbox`
   - **Priority**: P3 (Low - optional enhancement for layout training)
   - **Action**: Enhance parser when layout training needed

6. **Entity Labels Not Extracted**:
   - Key information extraction labels (company, date, address, total) available in separate files
   - Not currently extracted by parser
   - **Priority**: P2 (Medium - valuable for structured receipt understanding)
   - **Action**: Enhance parser to extract entity labels

---

##### 11. Dataset-Specific Notes

###### ICDAR 2019 Competition Context

**Competition**: ICDAR 2019 Robust Reading Competition
**Three Tasks**:

1. **Task 1**: Scanned Receipt Text Localisation (quad coordinates)
2. **Task 2**: Scanned Receipt OCR (text transcription)
3. **Task 3**: Key Information Extraction (4 fields: company, date, address, total)

**Test Set**: Likely 347 images reserved for competition
**Training Set**: Remaining images available for model training

**Benchmark Performance** (Key Information Extraction):

| Model | F1 Score | Year | Notes |
|-------|----------|------|-------|
| StrucTexT | High | 2021 | 50M document pre-training |
| GraphDoc | High | 2021 | RVL-CDIP pre-trained |
| LLM-TKIE | **0.839** | 2025 | No fine-tuning, 93.3% accuracy |
| DocAnnot | 0.846 | 2024 | Auto-annotation framework |

###### Quad Coordinates Preservation

**8-Point Polygon Format**: `[x1,y1,x2,y2,x3,y3,x4,y4]`

- Preserves rotation and perspective information
- Essential for rotated/skewed receipt text
- Conversion to axis-aligned bbox may lose skew information
- **Recommendation**: Retain both polygon and bbox representations for layout training

**Example**:

```python
# Quad coordinates (rotated rectangle)
quad = [123,45,678,45,678,90,123,90]

# COCO bbox conversion (axis-aligned)
x_min, x_max = min(quad[::2]), max(quad[::2])
y_min, y_max = min(quad[1::2]), max(quad[1::2])
coco_bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
```

###### Multilingual Receipt Potential

**Expected Languages** (based on ICDAR competition):

- English (Latin script)
- Chinese (Simplified/Traditional Han)
- Japanese (Hiragana, Katakana, Kanji)
- Thai (Thai script)
- Vietnamese (Latin with diacritics)

**Language Detection Recommendation**:

- Run language detection on ground truth text when E: drive restored
- Use ISO 639-1/3 codes for language classification
- Document script-confusable pairs (e.g., Latin O vs CJK 〇)

###### Thermal Print Characteristics

**Unique to SROIE**: Only thermal print dataset in catalog

**Thermal Print Challenges**:

- Ink fading over time (receipts may be aged)
- Low baseline contrast (thermal print lighter than inkjet/laser)
- Variable print quality (thermal printer maintenance-dependent)
- Reflective substrate (glare from camera flash common)

**IQA Training Value**:

- Thermal print degradation patterns different from scanner artifacts
- Mobile capture conditions (blur, perspective, shadows) complement scanner datasets
- Real-world receipt OCR representative samples

###### Entity Extraction Training

**4 Key Fields** (separate label files):

| Entity | Description | Extraction Challenge |
|--------|-------------|---------------------|
| **COMPANY** | Business/merchant name | Variable format, multi-line |
| **DATE** | Transaction date | Format variation (MM/DD/YYYY, DD-MM-YYYY, etc.) |
| **ADDRESS** | Business address | Multi-line, partial addresses |
| **TOTAL** | Final transaction amount | Currency symbols, decimal formats |

**Use Case**: Structured receipt understanding, key-value pair extraction, NER training

---

**References**:

- [ICDAR 2019 SROIE Paper](https://arxiv.org/abs/2103.10213)
- [HuggingFace Dataset](https://huggingface.co/datasets/darentang/sroie)
- [Kaggle Dataset](https://www.kaggle.com/datasets/urbikn/sroie-datasetv2)
- [SroieParser Source Code](../src/image_preprocessing_detector/annotation/parsers/layout/sroie.py)

---

#### receipts_hitl (Human-in-the-Loop Receipts)

> **Quick Stats**: 192 receipts | Supervisely annotations | Text transcriptions | Category labels
>
> **License**: Unknown | **Commercial Use**: Unknown

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Receipts Human-in-the-Loop Dataset |
| **Version** | 1.0 |
| **Source** | Supervisely platform |
| **Local Path** | `01_base_data/forms/receipts_hitl/` |
| **License** | Unknown (check Supervisely terms) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 192 |
| **Annotation Files** | 193 JSON |
| **File Format** | JPEG |
| **Annotation Format** | Supervisely JSON |

##### Entity Types (10 Categories)

| Category | Description |
|----------|-------------|
| **Business name** | Store/merchant name |
| **Business address** | Business location |
| **Business phone** | Contact number |
| **Business other information** | Additional business details |
| **Time and date** | Transaction timestamp |
| **Item information** | Product/service details |
| **Subtotal** | Pre-tax total |
| **Tax** | Tax amount |
| **Total** | Final transaction amount |
| **Other** | Miscellaneous text |

##### Text Labels

receipts_hitl includes OCR transcriptions in Supervisely-format JSON annotation files:

| Attribute | Value |
|-----------|-------|
| **Location** | `ds0/ann/*.json` (193 files) |
| **Format** | Supervisely JSON with `objects` array |
| **Tags** | `Transcription` (text content) + `Category` (field type) |
| **Geometry** | Rectangle bounding boxes |

**Sample structure**:

```json
{
  "objects": [
    {
      "classTitle": "Text",
      "geometryType": "rectangle",
      "points": {"exterior": [[226.0, 54.0], [457.0, 76.0]]},
      "tags": [
        {"name": "Transcription", "value": "Katana Sushi"},
        {"name": "Category", "value": "Business name"}
      ]
    }
  ]
}
```

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mobile camera captures |
| **Baseline Quality** | Variable (real-world conditions) |
| **Blur Sensitivity** | HIGH - Small receipt text |
| **Noise Sensitivity** | HIGH - Mobile camera noise |
| **Key Challenge** | Real-world capture conditions |
| **Annotation Quality** | High (human-in-the-loop verified) |

##### Project Usage

- **Path**: `01_base_data/forms/receipts_hitl/`
- **Phase(s)**: Form understanding, KIE training
- **Purpose**: Receipt OCR and key information extraction
- **Note**: Complements SROIE with additional receipt samples

---
