# Script-Specific Datasets

> **Purpose**: Datasets grouped by script/language for script detection training
> **Target Model**: Script classifier (Phase 10B)
> **Coverage**: 27+ scripts across 779K+ images

---

## Scripts by Language Family

### Latin Script (15 languages)

| Dataset | Images | Languages | Link |
|---------|--------|-----------|------|
| rvl-cdip | 400,000 | English | [rvl-cdip.md](../source/rvl-cdip.md) |
| funsd | 199 | English | [funsd.md](../source/funsd.md) |
| iam-handwriting | 13,353 | English | [iam-handwriting.md](../source/iam-handwriting.md) |
| bentham-handwritten | 14,000 | English (historical) | [bentham-handwritten.md](../source/bentham-handwritten.md) |
| mlt19 | 20,000 | 10 languages (Latin + others) | [mlt19.md](../source/mlt19.md) |
| mdiw13 | 290,213 | 13 scripts (Latin + others) | [mdiw13.md](../source/mdiw13.md) |

**Total**: ~738K images

---

### Arabic Script (3 variants)

| Dataset | Images | Variant | Link |
|---------|--------|---------|------|
| arabic-docs-ocr | 10,045 | Arabic | [arabic-docs-ocr.md](../source/arabic-docs-ocr.md) |
| muharaf | 24,952 | Arabic cursive (historical) | [muharaf.md](../source/muharaf.md) |
| yarmouk-ocr | 15,062 | Arabic | [yarmouk-ocr.md](../source/yarmouk-ocr.md) |
| pucit-ohul | 7,401 | Urdu | [pucit-ohul.md](../source/pucit-ohul.md) |

**Total**: ~57K images
**Scripts**: Arabic, Farsi, Urdu

---

### Indic Scripts (7 scripts)

| Dataset | Images | Script | Link |
|---------|--------|--------|------|
| hindi-ocr-synthetic | 80,009 | Hindi/Devanagari | [hindi-ocr-synthetic.md](../source/hindi-ocr-synthetic.md) |
| nepali-handwritten | 958 | Devanagari | [nepali-handwritten.md](../source/nepali-handwritten.md) |
| mle2e | 1,816 | Kannada + others | [mle2e.md](../source/mle2e.md) |

**Total**: ~83K images
**Scripts**: Devanagari (Hindi/Nepali), Bengali, Telugu, Kannada, Tamil, Malayalam

---

### East Asian Scripts (CJK)

| Dataset | Images | Scripts | Link |
|---------|--------|---------|------|
| jssoda | 2,000 | Japanese (Hiragana, Katakana, Kanji) | [jssoda.md](../source/jssoda.md) |
| mle2e | 1,816 | Chinese, Korean, Latin, Kannada | [mle2e.md](../source/mle2e.md) |
| cc-ocr | 7,058 | CJK mixed | [cc-ocr.md](../source/cc-ocr.md) |

**Total**: ~11K images
**Scripts**: Chinese (Simplified/Traditional), Japanese, Korean (Hangul)

---

### Tibetan Script

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| tibhcr | 141,698 | 47 character classes | [tibhcr.md](../source/tibhcr.md) |
| dzongkha-digits | 1,000 | 10 digit classes | [dzongkha-digits.md](../source/dzongkha-digits.md) |

**Total**: ~143K images

---

### Cyrillic Script

**Coverage**: Limited - available in MDIW13 and MLT19 multi-script datasets
**Dedicated Dataset**: None currently

---

### Hebrew Script

**Coverage**: Limited - available in MDIW13 multi-script dataset
**Dedicated Dataset**: None currently

---

## Synthetic Multi-Script Dataset

| Dataset | Images | Scripts | Status | Link |
|---------|--------|---------|--------|------|
| synth-multiscript-250k | 250,000 | 27 scripts + 8 IQA dimensions | 🔄 In Progress | [../training/synth-multiscript-250k.md](../training/synth-multiscript-250k.md) |

**Purpose**: Phase 10B script detection training
**Generation Source**: OpenLID v2 text corpus
**Status**: ~27,000 partial, 250,000 target
**Scripts**: Balanced coverage across all 27 scripts

---

## Training Strategy

### Phase 10B: Script Detection

**Primary Training Data**:

- synth-multiscript-250k (250K, balanced across 27 scripts)
- mdiw13 train split (232,170, 13 scripts, real-world)
- mlt19 train split (10,000, 10 languages)

**Augmentation**:

- Script-specific datasets for fine-tuning (Arabic, Indic, Tibetan, CJK)

**Validation**:

- mdiw13 val split
- mlt19 val split

**Testing** (PROTECTED):

- mdiw13 test split (58,043) - RESERVED
- mlt19 test split (10,000) - RESERVED
- cc-ocr (7,058) - RESERVED

---

## Script Coverage Summary

| Script Family | Scripts | Datasets | Total Images |
|---------------|---------|----------|--------------|
| **Latin** | 15 languages | 6 datasets | ~738K |
| **Arabic** | Arabic, Farsi, Urdu | 4 datasets | ~57K |
| **Indic** | Devanagari, Bengali, Telugu, Kannada, Tamil, Malayalam | 3 datasets | ~83K |
| **CJK** | Chinese, Japanese, Korean | 3 datasets | ~11K |
| **Tibetan** | Tibetan, Dzongkha | 2 datasets | ~143K |
| **Cyrillic** | Russian, Bulgarian, etc. | MDIW13 subset | TBD |
| **Hebrew** | Hebrew | MDIW13 subset | TBD |

**Total Coverage**: 27+ scripts across 779K+ real images + 250K synthetic target

---

## Benchmark Protection Rules

1. **NEVER train on benchmark test splits**:
   - ohr-bench test (1,712)
   - diqa-5000 test (~1,100)
   - doclaynet test (6,480)
   - pubtabnet test (9,138)
   - mdiw13 test (58,043)
   - mlt19 val/test (10,000)
   - cocotext val/test (20,000)
   - hiertext test (3,358)
   - hasyv2 test (16,823)
   - funsd test (50)
   - smartdoc-qa test (856)

2. **Benchmark-only datasets** (no training allowed):
   - cc-ocr (7,058)
   - omnidocbench (metadata only)

3. **Document training data usage** in model cards and training scripts

4. **Use official split files** from `splits/{dataset}/` directory

---

*See [TEXT_DETECTION.md](TEXT_DETECTION.md) for text detection training datasets*
*See [HANDWRITING.md](HANDWRITING.md) for handwriting-specific datasets*
*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
