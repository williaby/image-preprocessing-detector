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

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 19,657 | **Avg Min Confidence**: 0.260

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 19,657 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `domain` | 79.6% | 0.300 |
| 2 | `layout_detections` | 20.4% | 0.411 |
| 3 | `language` | 0.1% | 0.950 |
