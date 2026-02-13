#### MLT-19 (ICDAR 2019 Multilingual Text)

> **Quick Stats**: ~14 GB | 10 languages | Scene text | Script detection
>
> **License**: MIT | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | ICDAR 2019 Multilingual Text Detection Dataset |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Competition** | ICDAR 2019 Robust Reading Competition |
| **Kaggle** | [zubairalibhutto/mlt-19-ocr-dataset](https://www.kaggle.com/datasets/zubairalibhutto/mlt-19-ocr-dataset) |
| **Official** | [rrc.cvc.uab.es](https://rrc.cvc.uab.es/?ch=15) |
| **License** | MIT |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mlt19/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Size** | ~14.3 GB |
| **File Format** | JPG |
| **Annotation Format** | TXT/JSON (bounding boxes + language labels) |

##### Languages Included (10)

| Script Class | Languages |
|--------------|-----------|
| **Arabic** | Arabic |
| **Devanagari** | Bangla (Bengali script) |
| **CJK** | Chinese, Japanese, Korean |
| **Latin** | English, French, German, Italian, Latin |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scene text (natural images) |
| **Text Detection** | Word-level bounding boxes |
| **Language Labels** | Per-text instance |
| **Key Value** | Multi-script scene text for script classification |

##### Download Instructions

```bash
# Requires Kaggle CLI and account
pip install kaggle
kaggle datasets download -d zubairalibhutto/mlt-19-ocr-dataset
unzip mlt-19-ocr-dataset.zip -d /mnt/e/image_detection/01_base_data/language/mlt19/
```

##### Project Usage

- **Path**: `01_base_data/language/mlt19/` ✅ Extracted
- **Phase(s)**: Phase 10A (Script Detection)
- **Purpose**: Multi-script training for 10-class classification
- **Files**: 30,000 files, 14 GB
- **Parser**: [`parse_mlt19_labels`](../scripts/annotate_base_metadata.py#L2457) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/mlt19/` | ✅ Available | 19,993 JPG files |
| **Text/GT** | Native annotations | ✅ Available | TXT: Per-word text with language labels (`TrainGT/*.txt`) |
| **Text/GT Converted** | `metadata_registry/extracted/mlt19/` | ✅ Converted | GT conversion: 10,000 images, 111,996 annotations, 540K chars, 10 script categories |
| **Layout GT Converted** | `metadata_registry/extracted/mlt19/layout_batch_*.json` | ✅ Converted | COCO-style word-level layout with script class labels (Latin/Arabic/Chinese/Japanese/Korean/Bangla/Hindi/Symbols/Mixed/None) |

##### Ground Truth Availability

| Split | Images | GT Available | Language Labels |
|-------|--------|--------------|-----------------|
| **TrainImages** | 10,000 | ✅ Yes (`TrainGT/TrainGT/*.txt`) | Per-word language annotation |
| **TestImages** | 10,000 | ❌ No (ICDAR competition holdout) | Requires visual detection |

**Note**: MLT-19 test set ground truth was never publicly released (standard ICDAR competition practice).
Test images require automated language detection for complete coverage. Training images include
per-word language labels: Arabic, Bangla, Chinese, Hindi, Japanese, Korean, Latin, and mixed.

---

##### Layer 2 Metadata Audit

> **Audit Date**: 2026-02-12 | **Enrichment Version**: integrated_v3 (v2.0.0)
> **Methodology**: 8-phase systematic audit + VLM contact sheet analysis (195 sheets, 9,735 test images)

**Enrichment Sources**:

| Source | Coverage | Used For |
|--------|----------|----------|
| Parser ground truth | 9,922 (50.5%, train only) | language, script (primary) |
| Train GT enrichment | 134 (0.7%, train low-conf) | language, script from GT files |
| VLM contact sheet | 9,706 (49.4%, test only) | language, script (visual identification) |
| LLM enrichment (text-only) | 9,989 (50.8%, train only) | domain, language, script, content_type |
| Language enrichment (OpenLID) | 1,000 (5.1%, train only) | language, script (fallback) |
| DocLayout-YOLO v1 | 17,165 (87.3%) | layout_detections, content flags |

**Prescreening Results** (post v3 integration):

| Field | Pass Rate | Notes |
|-------|-----------|-------|
| split | 100% | Derived from source.split |
| capture_method | 100% | Hardcoded camera_smartphone (confidence 1.0) |
| script_family | 100% | Derived from iso15924_script |
| layout_bbox_valid | 100% | All bboxes valid where present |
| content_flags_boolean | 100% | VLM-corrected (34 images inspected) |
| orientation_class | 100% | Default 0 (upright), confidence 0.5 |
| image_properties_color_mode | 100% | All color (camera-captured) |
| handwriting_present | 100% | VLM-verified (3 true positives found) |
| quality_overall_mos | 100% | Present from v1 base annotation |
| **iso639_language** | **99.85%** | Only 30 unclear samples remain (was 50.5% in v2) |
| **domain_level1** | **19.3%** | 80.7% UNK - expected for scene text (KI-007) |
| **layout_detections** | **87.3%** | 12.7% empty - expected for scene text |
| **text_has_content** | **0%** | DEFERRED - requires Docling OCR |

**Fields at 100%**: 9/13 | **Overall pass (all 13)**: 0% (driven by text_has_content)

**VLM Content Flag Verification**:

| Flag | Flagged by Model | VLM True Positives | FP Rate |
|------|-----------------|-------------------|---------|
| has_table | 14 | 12 | 14.3% |
| has_formula | 6 | 0 | 100% |
| has_figure | 13,009 | 0 | 100% (scene photo ≠ embedded figure) |
| has_handwriting | 0 (model) | 3 (VLM-discovered) | N/A |

**VLM Failing Sample Inspection** (beyond content flags):

| Failure Category | Inspected | Finding |
|-----------------|-----------|---------|
| Domain UNK (train) | 3 | All CORRECT - generic scene text (road/street signs) |
| Domain non-UNK | 3 | 2 correct, 1 questionable (restaurant menu as FIN) |
| Language und (test) | 3 | All KNOWN_GAP - visually identifiable but no source data |
| Empty layout | 3 | All EXPECTED - DocLayout-YOLO not designed for scene text |
| Passing samples | 5 | Domain mostly correct; Latin-script language mapping issue |

**VLM Contact Sheet Script Identification** (v3):

| Script | Count | Pct | ISO 639 |
|--------|------:|----:|---------|
| Latin | 8,046 | 82.7% | en |
| Devanagari | 1,102 | 11.3% | hi |
| Hangul | 193 | 2.0% | ko |
| Han (Chinese) | 164 | 1.7% | zh |
| Bengali | 124 | 1.3% | bn |
| Arabic | 41 | 0.4% | ar |
| Han (Japanese) | 36 | 0.4% | ja |
| Unclear | 29 | 0.3% | und |

**Known Limitations**:

1. **Latin language conflation**: Parser maps all Latin-script European languages (French, German, Italian) to "en" (English). Affects ~2,671 train samples (13.6%). Root cause: MLT19 GT uses "Latin" as a language class, not individual European languages.
2. **Test split language gap (RESOLVED in v3)**: VLM contact sheet analysis resolved 9,706/9,735 test images. Only 29 "unclear" + 1 error remain.
3. **DocLayout-YOLO on scene text**: 12.7% empty detections expected (model trained on documents, not scene signs/banners). "figure" class maps to entire scene photos (100% FP for has_figure).

##### Reliability & Bottlenecks

> **Computed**: 2026-02-12 (post-audit) | **Samples**: 19,657

**Composite Category Distribution** (post v3 integration):

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 19,627 | 99.8% |
| active_learning | 0 | 0.0% |
| unreliable | 30 | 0.2% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `domain` | 80.7% | 0.300 |
| 2 | `layout_detections` | 12.7% | 0.600 |
| 3 | `language` | 0.15% | 0.950 (train) / 0.75 (test VLM) |

**Deferred Items**:

| Item | Prerequisite | Impact |
|------|-------------|--------|
| text_has_content / text_statistics | Docling OCR pipeline | Would enable text density analysis |
| quality_overall (IQA) | VLM IQA or classical IQA run | Would enable quality stratification |
| resolution_quality_score | PaddleOCR GPU session | Character-height-based quality |
