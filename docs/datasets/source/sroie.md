#### SROIE (ICDAR 2019)

> **Quick Stats**: 973 images (626 train + 347 test) | Malaysian receipts | Text detection + OCR + Entity extraction
>
> **License**: [NEEDS_VERIFICATION] - Conservative classification as Research Use Only

- **Path**: `01_base_data/forms/sroie_icdar2019/`
- **Paper**: [ICDAR 2019 Robust Reading Challenge on Scanned Receipts OCR and Information Extraction (2021)](https://arxiv.org/abs/2103.10213)
- **HuggingFace**: [rth/sroie-2019-v2](https://huggingface.co/datasets/rth/sroie-2019-v2)
- **IQA Profile**: [camera_blur, glare_reflection, perspective_distortion, thermal_print_fading]
- **Project Usage**: Phase 7 OCR training, receipt understanding
- **Parser**: [`SroieParser`](../src/image_preprocessing_detector/annotation/parsers/layout/sroie.py) | ⚠️ Needs update for new format

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/forms/sroie_icdar2019/` | ✅ Available | 973 JPG files |
| **Text/GT** | Native annotations | ✅ Available | JSON + TXT: Per-region transcriptions + entity labels (company, date, address, total) |
| **Text/GT Converted** | `metadata_registry/extracted/sroie/` | ✅ Converted | GT conversion: 973 receipts, 52,330 annotations, quad→COCO bbox conversion |
| **Layout GT Converted** | `metadata_registry/extracted/sroie/layout_batch_*.json` | ✅ Converted | COCO-style text region layout from GT annotations |

SROIE (Scanned Receipt OCR and Information Extraction) provides camera-captured and
scanner-captured receipt images from Malaysian businesses with quad-coordinate text
localization, ground truth transcriptions, and key information extraction labels.
Created for the ICDAR 2019 Robust Reading Competition.

> **Data Provenance Note (2026-02-06)**: The previous `01_base_data/forms/sroie/` directory
> (2,043 images) was removed after audit revealed it was contaminated: 425 synthetic invoices
> from an invoice generator + 1,618 web-scraped global receipts (45% US, 5% EU, 7% Malaysian).
> Only ~113 images matched the official SROIE dataset. This clean version was downloaded from
> HuggingFace `rth/sroie-2019-v2` and verified against the original paper. The old
> `sroie_voxel51_labeled/` directory (712 train images) remains as an additional reference.
> Derived training datasets (orientation, stage2_diqa_ensemble) still reference the old data
> and will need regeneration.

---

##### 1. Source Data Inventory

**Official Dataset**: ICDAR 2019 SROIE

- **Release Year**: 2019 (competition), 2021 (paper publication)
- **Version**: 1.0
- **Publisher**: ICDAR 2019 Robust Reading Competition
- **Authors**: Zheng Huang, Kai Chen, Jianhua He, Xiang Bai, Dimosthenis Karatzas, Shijian Lu, C.V. Jawahar
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

- **Download**: [HuggingFace: rth/sroie-2019-v2](https://huggingface.co/datasets/rth/sroie-2019-v2) (canonical) | [Voxel51/scanned_receipts](https://huggingface.co/datasets/Voxel51/scanned_receipts) (712 train only)
- **Documentation Status**: [Official] for paper/competition info, [Verified] for image counts

###### 1.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Camera/scanner-captured Malaysian receipt images |
| **Annotations** | JSON | Per-image quad coordinates + OCR text + entity labels |

###### 1.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/images/` | `train/annotations/` | 626 | ✅ Verified |
| **Test** | `test/images/` | `test/annotations/` | 347 | ✅ Verified |
| **Total** | - | - | 973 | ✅ |

**Split Organization Pattern**: `by_folder` (train/test directories)

###### 1.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Quad Coordinates** | JSON (nested lists) | Text region | 8-point polygon per text region |
| **Text Transcriptions** | JSON (string list) | Text region | Ground truth OCR text per quad |
| **Entity Labels** | JSON | Document | 4 key fields (company, date, address, total) |

###### 1.4 Annotation Schema Details

**JSON Annotation Format** (one file per image):

```json
{
  "image_id": "X00000",
  "split": "train",
  "text_regions": [
    {"text": "BOOK TA .K(TAMAN DAYA) SDN BND", "bbox_quad": [[x1,y1], [x2,y2], ...]},
    {"text": "81100 JOHOR BAHRU, JOHOR.", "bbox_quad": [[x1,y1], [x2,y2], ...]}
  ],
  "entities": {
    "company": "BOOK TA .K (TAMAN DAYA) SDN BHD",
    "date": "25/12/2018",
    "address": "NO.53 55,57 & 59, JALAN SAGU 18, TAMAN DAYA, 81100 JOHOR BAHRU, JOHOR.",
    "total": "9.00"
  }
}
```

---

##### 2. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 OCR training |
| **Purpose** | Receipt OCR, text detection, key information extraction |
| **Local Path** | `01_base_data/forms/sroie_icdar2019/` |
| **Preprocessing** | None required (images pre-normalized) |
| **Benchmark Status** | 347 test images (competition held-out set) |

**Training Task Alignment**:

- ✅ Text detection (quad coordinates preserve rotation/perspective)
- ✅ OCR training (ground truth transcriptions)
- ✅ Key information extraction (company, date, address, total)
- ✅ Receipt structure understanding
- ⚠️ Layout detection (requires quad-to-COCO-bbox conversion)

---

##### 3. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `SroieParser` in `parsers/layout/sroie.py` |
| **Parser Status** | ⚠️ Needs update for new JSON annotation format |
| **Config Entry** | `DATASET_CONFIGS["sroie"]` - needs path update |

> **Action Required**: Parser was written for the old TXT quad+text format.
> New annotations are JSON with embedded entity labels. Parser needs update.

---

##### 4. Dataset Statistics

###### 4.1 Split Coverage

| Split | Count | Status |
|-------|-------|--------|
| **Train** | 626 | ✅ Verified |
| **Test** | 347 | ✅ Verified |
| **Total** | 973 | ✅ |

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 973 [Official] |
| **Image Dimensions** | 439-4961 x 605-7016 px |
| **File Format** | JPEG (100%) |
| **Color Space** | RGB |
| **Annotation Format** | JSON (quad coordinates + entities) |
| **Avg Text Regions/Image** | ~30-50 |

###### 4.3 Capture Method

| Capture Method | Description |
|----------------|-------------|
| Mixed | Camera-captured receipts + flatbed scanner captures |

**Capture Characteristics**:

- Malaysian retail receipts (shops, restaurants, service providers)
- Mix of smartphone camera captures and flatbed scanner scans
- Dates: 2015-2018
- Currency: Malaysian Ringgit (RM)
- Thermal print substrate (receipts)

###### 4.4 Domain Distribution

| Domain | Percentage |
|--------|------------|
| FIN (retail receipts) | 100% |

---

##### 5. Language & Script Coverage

| Script/Language | ISO Code | Coverage | Notes |
|-----------------|----------|----------|-------|
| English | en / Latn | ~85-90% | Primary receipt text |
| Chinese | zh / Hant | ~5-10% | Business names, footer text |
| Malay | ms / Latn | ~5% | Some business/address text |

**Geographic Origin**: Malaysia (Johor Bahru, Kuala Lumpur, Selangor, Penang regions)

---

##### 6. IQA Profile

**Predicted Sensitivity**:

- **High**: Camera blur, glare/reflection, perspective distortion
- **Medium**: Low contrast (thermal print), uneven illumination, shadows
- **Low**: JPEG artifacts, compression noise

**Thermal Print Characteristics** (unique to SROIE):

- Ink fading over time
- Low baseline contrast
- Variable print quality
- Reflective substrate (glare from camera flash)

---

##### 7. Known Issues

1. **Parser Needs Update**:
   - Old parser expected TXT quad+text format, new data is JSON
   - **Priority**: P2 (Medium)
   - **Action**: Update SroieParser for new JSON annotation format

2. **Layer 2 Metadata Missing**:
   - Old metadata was deleted (based on contaminated data)
   - **Priority**: P2 (Medium)
   - **Action**: Rebuild Layer 2 metadata from clean dataset

3. **Derived Training Data Contaminated**:
   - `03_training_datasets/orientation/` contains sroie images from old contaminated set
   - `03_training_datasets/stage2_diqa_ensemble/images/sroie/` same issue
   - **Priority**: P3 (Low - regenerate when training phases revisited)

4. **License Classification** [NEEDS_VERIFICATION]:
   - ICDAR competition dataset, conservative classification as Research Use Only
   - **Priority**: P0 (Critical for commercial use guidance)

---

##### 8. Dataset-Specific Notes

###### ICDAR 2019 Competition Context

**Competition**: ICDAR 2019 Robust Reading Competition

**Three Tasks**:

1. **Task 1**: Scanned Receipt Text Localisation (quad coordinates)
2. **Task 2**: Scanned Receipt OCR (text transcription)
3. **Task 3**: Key Information Extraction (4 fields: company, date, address, total)

###### Related Datasets in Catalog

| Dataset | Count | Relationship |
|---------|-------|-------------|
| **sroie_icdar2019** | 973 | Canonical SROIE (this entry) |
| **sroie_voxel51_labeled** | 712 | Voxel51 train-only subset with original X-prefixed filenames |
| **sroie2019_word_347** (CC-OCR) | 347 | CC-OCR test subset |

---

**References**:

- [ICDAR 2019 SROIE Paper](https://arxiv.org/abs/2103.10213)
- [HuggingFace: rth/sroie-2019-v2](https://huggingface.co/datasets/rth/sroie-2019-v2)
- [HuggingFace: Voxel51/scanned_receipts](https://huggingface.co/datasets/Voxel51/scanned_receipts)
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

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 973 | **Avg Min Confidence**: 0.381

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 973 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `language` | 84.9% | 0.389 |
| 2 | `layout_detections` | 15.1% | 0.493 |
