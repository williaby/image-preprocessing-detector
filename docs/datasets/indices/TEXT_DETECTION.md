# Text Detection & Script Classification Datasets

> **Purpose**: Datasets for text presence detection and script/language identification
> **Target Model**: Text Gate (ensemble heuristics) + Script Classifier
> **Label Type**: Word-level bounding boxes + script/language labels

---

## Primary Text Detection Datasets

| Dataset | Images | Scripts/Languages | Restrictions | Link |
|---------|--------|-------------------|--------------|------|
| mdiw13 | 290,213 | 13 scripts (doc/line/word) | ⚠️ Train OK (232,170), test reserved | [mdiw13.md](../source/mdiw13.md) |
| cocotext | 63,686 | Scene text (incidental) | ⚠️ Train OK (43,686), val/test reserved | [cocotext.md](../source/cocotext.md) |
| mlt19 | 20,000 | 10 languages (word boxes) | ⚠️ Train OK (10,000), val/test reserved | [mlt19.md](../source/mlt19.md) |
| hiertext | 11,639 | Scene text (mixed) | ⚠️ Train OK (8,281), test reserved | [hiertext.md](../source/hiertext.md) |
| cvsi | 10,715 | 10 scripts (video frames) | ✅ Unrestricted | [cvsi.md](../source/cvsi.md) |
| siw13 | 16,291 | 13 scripts | ✅ Unrestricted | [siw13.md](../source/siw13.md) |
| cc-ocr | 7,058 | CJK mixed | 🔒 Test only (benchmark) | [cc-ocr.md](../source/cc-ocr.md) |

**Total Available for Training**: ~734K images

---

## Script-Specific Datasets

### Arabic Scripts

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| arabic-docs-ocr | 10,045 | Arabic (word + page) | [arabic-docs-ocr.md](../source/arabic-docs-ocr.md) |
| muharaf | 24,952 | Arabic cursive (historical) | [muharaf.md](../source/muharaf.md) |
| yarmouk-ocr | 15,062 | Arabic documents | [yarmouk-ocr.md](../source/yarmouk-ocr.md) |

### South Asian Scripts

| Dataset | Images | Script | Link |
|---------|--------|--------|------|
| hindi-ocr-synthetic | 80,009 | Hindi/Devanagari | [hindi-ocr-synthetic.md](../source/hindi-ocr-synthetic.md) |
| nepali-handwritten | 958 | Devanagari handwriting | [nepali-handwritten.md](../source/nepali-handwritten.md) |
| pucit-ohul | 7,401 | Urdu handwriting | [pucit-ohul.md](../source/pucit-ohul.md) |

### East Asian Scripts

| Dataset | Images | Script | Link |
|---------|--------|--------|------|
| jssoda | 2,000 | Japanese (vertical + horizontal) | [jssoda.md](../source/jssoda.md) |
| mle2e | 1,816 | Latin, Chinese, Korean, Kannada | [mle2e.md](../source/mle2e.md) |

### Tibetan Scripts

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| tibhcr | 141,698 | Tibetan (47 classes) | [tibhcr.md](../source/tibhcr.md) |
| dzongkha-digits | 1,000 | Tibetan digits (10 classes) | [dzongkha-digits.md](../source/dzongkha-digits.md) |

---

## Synthetic Training Dataset

| Dataset | Images | Scripts | Status | Link |
|---------|--------|---------|--------|------|
| synth-multiscript-v3 | 350,012 | 27 scripts + 8 IQA dimensions | ⚠️ Complete — Imbalanced | [../training/synth-multiscript-v3.md](../training/synth-multiscript-v3.md) |

**Purpose**: Phase 10B script detection training
**Generation**: From OpenLID v2 corpus
**Status**: ✅ Complete on GCS (350,012 images) — ⚠️ Imbalanced distribution; rebalancing required. v2 (250K) DELETED.

---

## Training Strategy

### Text Detection Gate (Binary Classification)

**Model**: Ensemble heuristics (stroke density, connected components, edge density)
**Purpose**: Route documents to text vs no-text processing branches
**Training Data**:

- Positive examples: mdiw13, cocotext, mlt19 (any dataset with word-level boxes)
- Negative examples: Pure image datasets without text annotations

### Script Classification (Multi-class)

**Model**: CNN or SigLIP-based classifier
**Classes**: 27+ scripts (Latin, Arabic, Chinese, Devanagari, Cyrillic, etc.)
**Training Data**:

- Primary: synth-multiscript-v3 (350,012, 27 scripts on GCS — ⚠️ rebalancing required before training)
- Augmentation: mdiw13 (13 scripts, real-world), mlt19 (10 languages)
- Script-specific: Use domain datasets for fine-tuning

---

## Scripts Covered

**Latin-based**: English, French, German, Spanish, Italian, Portuguese, Dutch, Swedish, Danish, Norwegian, Polish, Czech, Romanian, Turkish
**Arabic-based**: Arabic, Farsi/Persian, Urdu
**Asian Scripts**: Chinese (Simplified/Traditional), Japanese (Hiragana/Katakana/Kanji), Korean (Hangul), Thai
**Indic Scripts**: Hindi/Devanagari, Bengali, Telugu, Kannada, Tamil, Malayalam, Nepali
**Other**: Cyrillic (Russian), Hebrew, Tibetan, Greek

**Total**: 27+ scripts across 779K+ images

---

## Benchmark Protection

**MDIW13**: Competition test split RESERVED (58,043 images)
**MLT19**: Val/test splits RESERVED (10,000 images)
**COCO-Text**: Val/test splits RESERVED (20,000 images)
**CC-OCR**: Test-only benchmark (7,058 images) - no training allowed
**HierText**: Test split RESERVED (3,358 images)

---

*See [SCRIPTS.md](SCRIPTS.md) for script-specific dataset details*
*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
*See [GROUND_TRUTH_SUMMARY.md](../GROUND_TRUTH_SUMMARY.md) for annotation methodology and provenance*
