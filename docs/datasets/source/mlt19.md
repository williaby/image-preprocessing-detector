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

##### Ground Truth Availability

| Split | Images | GT Available | Language Labels |
|-------|--------|--------------|-----------------|
| **TrainImages** | 10,000 | ✅ Yes (`TrainGT/TrainGT/*.txt`) | Per-word language annotation |
| **TestImages** | 10,000 | ❌ No (ICDAR competition holdout) | Requires visual detection |

**Note**: MLT-19 test set ground truth was never publicly released (standard ICDAR competition practice).
Test images require automated language detection for complete coverage. Training images include
per-word language labels: Arabic, Bangla, Chinese, Hindi, Japanese, Korean, Latin, and mixed.

---
