---
title: "Script Detection Taxonomy for Phase 10B"
schema_type: planning
status: draft
owner: core-maintainer
purpose: >
  Defines the hierarchical script classification approach with 4-class CJK internal model
  and post-processing logic for external class derivation.
component: "Strategy"
source: "Phase 10B planning session"
tags:
  - planning
  - roadmap
---

## Overview

This document defines the script detection taxonomy for the Phase 10B multilingual document
intelligence pipeline. Based on exhaustive research (see `tmp_cleanup/script-research.md`),
we adopt a **hierarchical approach** that separates internal training classes from external
user-facing classes.

**Key Innovation**: The CJK scripts share Han logograms but differ in phonograms. Training
with 4 internal CJK classes (Han, Hiragana, Katakana, Hangul) enables accurate post-processing
to derive Japanese, Korean, and Chinese classifications.

## External Classes (User-Facing)

The model outputs 10 user-facing script classes:

| Class ID | Class Name | ISO 15924 | Description |
|----------|------------|-----------|-------------|
| 0 | `latin` | Latn | Latin alphabet (English, French, German, etc.) |
| 1 | `japanese` | Jpan | Japanese mixed script (Kanji + Kana) |
| 2 | `devanagari` | Deva | Devanagari (Hindi, Nepali, Sanskrit) |
| 3 | `tibetan` | Tibt | Tibetan script |
| 4 | `arabic` | Arab | Arabic script (Arabic, Urdu, Persian) |
| 5 | `cjk_mixed` | Hani | Han-only or ambiguous CJK context |
| 6 | `korean` | Kore | Korean (Hangul + optional Hanja) |
| 7 | `cyrillic` | Cyrl | Cyrillic (Russian, Ukrainian, Bulgarian) |
| 8 | `thai` | Thai | Thai script |
| 9 | `hebrew` | Hebr | Hebrew script |

## Internal Training Classes (13 Classes)

The model is trained with 13 internal classes for fine-grained discrimination:

### CJK Decomposition (4 Classes)

| Internal ID | Class Name | Purpose |
|-------------|------------|---------|
| 0 | `han` | Shared CJK logograms (Hanzi/Kanji/Hanja) |
| 1 | `hiragana` | Japanese syllabary (curved) |
| 2 | `katakana` | Japanese syllabary (angular) |
| 3 | `hangul` | Korean phonetic blocks |

### Other Scripts (9 Classes)

| Internal ID | Class Name | Notes |
|-------------|------------|-------|
| 4 | `latin` | Direct mapping to external |
| 5 | `devanagari` | Primary Indic script |
| 6 | `tibetan` | Direct mapping to external |
| 7 | `arabic` | RTL cursive script |
| 8 | `cyrillic` | Direct mapping to external |
| 9 | `thai` | Continuous script (no word spacing) |
| 10 | `hebrew` | RTL square script |
| 11 | `bengali` | Indic confuser (similar headline) |
| 12 | `gurmukhi` | Indic confuser (Punjabi script) |

## Post-Processing Logic

### CJK Class Derivation

```python
def derive_cjk_class(predictions: dict) -> str:
    """
    Derive external CJK class from internal predictions.

    Args:
        predictions: Dict with probabilities for han, hiragana, katakana, hangul

    Returns:
        External class: 'japanese', 'korean', or 'cjk_mixed'
    """
    han_prob = predictions.get('han', 0)
    kana_prob = predictions.get('hiragana', 0) + predictions.get('katakana', 0)
    hangul_prob = predictions.get('hangul', 0)

    # Japanese: Han + Kana co-occurrence
    if han_prob > 0.3 and kana_prob > 0.2:
        return 'japanese'

    # Korean: Hangul presence (with or without Hanja)
    if hangul_prob > 0.3:
        return 'korean'

    # Pure Kana (rare but valid Japanese)
    if kana_prob > 0.5:
        return 'japanese'

    # Han-only: Could be Chinese, or Kanji-heavy Japanese
    # Default to cjk_mixed for ambiguous cases
    return 'cjk_mixed'
```

### Indic Script Disambiguation

```python
def derive_indic_class(predictions: dict) -> str:
    """
    Derive Indic script class, handling confusers.

    All Indic scripts with headline (shirorekha) are trained together
    to force the model to learn discriminative features.
    """
    devanagari_prob = predictions.get('devanagari', 0)
    bengali_prob = predictions.get('bengali', 0)
    gurmukhi_prob = predictions.get('gurmukhi', 0)

    # Return highest confidence Indic script
    indic_scores = {
        'devanagari': devanagari_prob,
        'bengali': bengali_prob,
        'gurmukhi': gurmukhi_prob
    }

    winner = max(indic_scores, key=indic_scores.get)

    # Map to external class (bengali/gurmukhi -> devanagari for 10-class output)
    if winner in ('bengali', 'gurmukhi'):
        # Log for analysis but map to devanagari family
        return 'devanagari'

    return winner
```

## Dataset Mapping

### Primary Training Sources

| External Class | Primary Datasets | Sample Count Target |
|----------------|------------------|---------------------|
| `latin` | MLT-19, MDIW-13 | 10,000 (down-sampled) |
| `japanese` | MDIW-13, CC-OCR | 5,000 |
| `devanagari` | Hindi OCR Synthetic, Nepal Handwritten, MDIW-13 | 10,000 |
| `tibetan` | TibHCR (synthetic docs) | 2,000 |
| `arabic` | Arabic Docs OCR, Yarmouk, PUCIT-OHUL, MDIW-13 | 10,000 |
| `cjk_mixed` | CC-OCR, MLT-19 | 5,000 |
| `korean` | MLT-19, MLe2e | 3,000 |
| `cyrillic` | MIDV-500 (RU/UA/BY) | 5,000 |
| `thai` | MDIW-13, SIW-13 | 2,000 |
| `hebrew` | SIW-13 (if available), synthetic | 1,000 |

### Internal CJK Sources

| Internal Class | Primary Datasets |
|----------------|------------------|
| `han` | CC-OCR, MLT-19 (Chinese subset) |
| `hiragana` | CC-OCR (Japanese), MDIW-13 |
| `katakana` | CC-OCR (Japanese), MDIW-13 |
| `hangul` | MLT-19 (Korean), MLe2e |

## Class Balance Strategy

### Down-Sampling High-Resource Scripts

Latin dominates available datasets (~100K+ samples). Apply:

- Random under-sampling to 10K for training balance
- Stratified sampling to preserve document type diversity

### Up-Sampling Low-Resource Scripts

For scripts with <2K samples (Tibetan, Hebrew):

- Synthetic document generation using DocHPLT text corpus
- Font rendering with Noto Sans family
- Paper texture augmentation (aging, noise, bleed-through)

### Augmentation Pipeline

```python
augmentation_pipeline = [
    # Geometric
    RandomRotate(degrees=(-5, 5)),
    RandomPerspective(distortion_scale=0.1),

    # Quality degradation (simulate scans)
    GaussianBlur(kernel_size=(3, 7)),
    JPEGCompression(quality=(50, 95)),

    # Historical document simulation
    PaperTexture(opacity=(0.1, 0.3)),
    BleedThrough(probability=0.2),

    # Binarization (fax/high-contrast simulation)
    AdaptiveBinarization(probability=0.1),
]
```

## Evaluation Metrics

### Per-Class Metrics

| Metric | Target | Priority |
|--------|--------|----------|
| Accuracy (macro) | > 90% | High |
| F1 (weighted) | > 88% | High |
| Confusion (CJK) | < 15% | Critical |
| Confusion (Indic) | < 10% | High |

### Critical Confusion Pairs

Monitor these high-confusion pairs during training:

| Pair | Reason | Mitigation |
|------|--------|------------|
| Japanese ↔ Chinese | Han unification | Kana presence check |
| Devanagari ↔ Bengali | Similar headline | Train with confusers |
| Devanagari ↔ Gurmukhi | Similar headline | Train with confusers |
| Arabic ↔ Urdu | Same script family | Accept as correct |
| Thai ↔ Lao | Visual similarity | Consider Lao confuser |

## Implementation Notes

### Model Architecture

Recommended architecture for hierarchical classification:

```
Input Image (224x224)
    │
    ▼
ResNet-50 / EfficientNet-B0 (feature extractor)
    │
    ▼
┌───────────────┬────────────────┐
│               │                │
▼               ▼                ▼
CJK Head     Indic Head      Main Head
(4 classes)  (3 classes)     (10 classes)
    │               │             │
    ▼               ▼             ▼
Post-process  Post-process   Final Output
    │               │             │
    └───────────────┴─────────────┘
                    │
                    ▼
            Ensemble/Vote
```

### Training Strategy

1. **Phase 1**: Pre-train on full 13-class internal taxonomy
2. **Phase 2**: Fine-tune with weighted loss for low-resource scripts
3. **Phase 3**: Add post-processing logic and validate on held-out set

### File Structure

```
01_base_data/language/
├── mlt19/                    # 30,000 files, 14 GB
├── arabic_docs_ocr/          # 20,091 files, 9.3 GB
├── hindi_ocr_synthetic/      # 80,010 files, 920 MB
├── nepali_handwritten/       # 1,916 files, 1.5 GB
├── pucit_ohul_urdu/          # 7,403 files, 583 MB
├── yarmouk_ocr/              # 16,734 files, 2.8 GB
├── midv500_data/             # 48 GB (Cyrillic ID docs)
├── mdiw13/                   # 226 MB (foundational)
├── huggingface_downloads/
│   ├── TibHCR/               # 4.5 GB (Tibetan characters)
│   └── CC-OCR/               # 2.1 GB (CJK mixed)
└── multilingual_scripts/
    └── nepal_devanagari/     # 717 pages
```

## References

1. MDIW-13: Multi-lingual Database for Script Identification in Document Images
2. SIW-13: Script Identification in the Wild
3. ICDAR 2019 MLT: Robust Reading Challenge on Multi-Lingual Text
4. ISO 15924: Codes for the representation of names of scripts

---

*This taxonomy is designed for Phase 10B script detection training. For implementation
details, see the training scripts in `modal/` directory.*
