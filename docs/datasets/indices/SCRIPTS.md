# Script-Specific Datasets

> **Purpose**: Datasets grouped by script/language for script detection training
> **Target Model**: Script classifier (Phase 10B)
> **Coverage**: 27+ scripts across 1.3M+ images

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
| egyptian-handwriting | 11,216 | Arabic cursive (89 writers, CC-BY-4.0) | [egyptian-handwriting.md](../source/egyptian-handwriting.md) |
| yarmouk-ocr | 15,062 | Arabic | [yarmouk-ocr.md](../source/yarmouk-ocr.md) |
| pucit-ohul | 7,401 | Urdu | [pucit-ohul.md](../source/pucit-ohul.md) |

**Total**: ~69K images
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

| Dataset | Images | Scripts | License | Link |
|---------|--------|---------|---------|------|
| jssoda | 2,000 | Japanese (Hiragana, Katakana, Kanji) | CC-BY-4.0 | [jssoda.md](../source/jssoda.md) |
| vjroda | ~100 | Japanese vertical (Jpan) — OOD eval only | CC-BY-4.0 | [vjroda.md](../source/vjroda.md) |
| ndl-docl | ~2,290 | Japanese (Jpan) — kuzushiji + modern | PDM 1.0 | [ndl-docl.md](../source/ndl-docl.md) |
| pdmocr-part1 | ~2,713 | Japanese (Jpan) — 1870s-1940s historical | PDM 1.0 | [pdmocr-part1.md](../source/pdmocr-part1.md) |
| pdmocr-part2 | ~3,997 | Japanese (Jpan) — 1870s-1960s, direction GT | PDM 1.0 | [pdmocr-part2.md](../source/pdmocr-part2.md) |
| ndl-minhon | ~32,822 | Japanese (Jpan) — kuzushiji manuscripts | CC-BY-SA 4.0 | [ndl-minhon.md](../source/ndl-minhon.md) |
| thousand-character-classic | 391 | CJK calligraphy (Hant/Hani/Kore/Jpan, 6 script styles) | Mixed (CC0/CC BY/PD) | [thousand-character-classic.md](../source/thousand-character-classic.md) |
| john11-manuscripts | 210-520 | Multi-script manuscripts (Grek/Latn/Ethi/Armn/Syrc/Arab/Cyrs/Copt/Goth/Geor, 11 scripts) | Mixed (CC0/PD/CC-BY) | [john11-manuscripts.md](../source/john11-manuscripts.md) |
| mle2e | 1,816 | Chinese, Korean, Latin, Kannada | Research | [mle2e.md](../source/mle2e.md) |
| cc-ocr | 7,058 | CJK mixed | Research | [cc-ocr.md](../source/cc-ocr.md) |
| casia-hwdb2-line | 52,160 | Chinese Simplified (Hans) — handwritten lines | MIT | [casia-hwdb2-line.md](../source/casia-hwdb2-line.md) |
| casia-hwdb2 | ~1,097 pages | Chinese Simplified (Hans) — full pages 300 DPI | Academic only | [casia-hwdb2.md](../source/casia-hwdb2.md) |
| kuzushiji (K-49) | 270,912 | Japanese Hiragana historical cursive (Jpan) | CC BY-SA 4.0 | [kuzushiji.md](../source/kuzushiji.md) |
| kuzushiji (K-Kanji) | 140,424 | Japanese Kanji historical (Jpan) | CC BY-SA 4.0 | [kuzushiji.md](../source/kuzushiji.md) |
| kuzushiji (K-MNIST) | 70,000 | Japanese Hiragana historical (Jpan, 10 classes) | CC BY-SA 4.0 | [kuzushiji.md](../source/kuzushiji.md) |

**Total**: ~587K images (was ~545K — **+42K with NDL Japanese additions**)
**Scripts**: Chinese Simplified (Hans/HANS), Japanese (Jpan/JPAN), Korean (Hangul — cc-ocr subset)

**HANS gap addressed**: casia-hwdb2-line (52K) + casia-hwdb2 pages (~1K) add 53K handwritten HANS samples.
**JPAN gap addressed**: Kuzushiji adds 481K handwritten JPAN (vs. prior ~10K mostly printed). K-49 train alone adds 232K. NDL datasets add ~42K historical Japanese (kuzushiji + typography) with direction GT.
⚠️ Kuzushiji CC BY-SA 4.0: ShareAlike applies to published derivatives.
⚠️ ndl-minhon CC BY-SA 4.0: ShareAlike applies to published derivatives.
⚠️ CASIA-HWDB2 page-level: Academic license only — no commercial use.
⚠️ vjroda: OOD evaluation only (100 images, too small for training).

---

### Tibetan Script

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| tibhcr | 141,698 | 47 character classes | [tibhcr.md](../source/tibhcr.md) |
| openpecha-ocr-drutsa | 32,364 | Tibetan line-level OCR (CC-BY-4.0) | [openpecha-ocr-drutsa.md](../source/openpecha-ocr-drutsa.md) |
| dzongkha-digits | 1,000 | 10 digit classes | [dzongkha-digits.md](../source/dzongkha-digits.md) |

**Total**: ~175K images

---

### Armenian Script

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| salami | 5 | Historical manuscripts (legibility labels) | [salami.md](../source/salami.md) |

**Total**: 5 images (SALAMI subset)
**Note**: Small sample count; SALAMI's value is legibility calibration, not script volume

---

### Georgian Script

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| salami | 5 | Historical manuscripts (legibility labels) | [salami.md](../source/salami.md) |

**Total**: 5 images (SALAMI subset)
**Note**: Small sample count; SALAMI's value is legibility calibration, not script volume

---

### Gothic Script

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| salami | 5 | Historical manuscripts (legibility labels) | [salami.md](../source/salami.md) |

**Total**: 5 images (SALAMI subset)
**Note**: Only real-image source for Gothic script in corpus

---

### Cyrillic Script

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| salami | 95 | Slavonic manuscripts (legibility labels) | [salami.md](../source/salami.md) |

**Coverage**: Limited - available in MDIW13, MLT19 multi-script datasets + SALAMI Slavonic subset
**Dedicated Dataset**: None currently

---

### Greek Script

| Dataset | Images | Content | Link |
|---------|--------|---------|------|
| salami | 60 | Greek manuscripts (legibility labels) | [salami.md](../source/salami.md) |

**Coverage**: Limited - SALAMI Greek subset + MDIW13
**Dedicated Dataset**: None currently

---

### Hebrew Script

**Coverage**: Limited - available in MDIW13 multi-script dataset
**Dedicated Dataset**: None currently

---

## Synthetic Multi-Script Dataset

| Dataset | Images | Scripts | Status | Link |
|---------|--------|---------|--------|------|
| synth-multiscript-v3 | 350,012 | 27 scripts + 8 IQA dimensions | ⚠️ Complete — Imbalanced | [../training/synth-multiscript-v3.md](../training/synth-multiscript-v3.md) |

**Purpose**: Phase 10B script detection training
**Generation Source**: OpenLID v2 text corpus
**Status**: ✅ Complete on GCS (350,012 images) — ⚠️ Imbalanced distribution (Arab 3.8× target; 17 scripts below target); rebalancing required before training. v2 (250K) DELETED.
**Scripts**: 27 scripts (imbalanced — see training doc for per-script counts)

---

## Training Strategy

### Phase 10B: Script Detection

**Primary Training Data**:

- synth-multiscript-v3 (350,012, 27 scripts on GCS — ⚠️ rebalancing required before training)
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
| **Arabic** | Arabic, Farsi, Urdu | 5 datasets | ~69K |
| **Indic** | Devanagari, Bengali, Telugu, Kannada, Tamil, Malayalam | 3 datasets | ~83K |
| **CJK** | Chinese (Hans), Japanese (Jpan), Korean | 13 datasets | ~587K |
| **Tibetan** | Tibetan, Dzongkha | 3 datasets | ~175K |
| **Cyrillic** | Russian, Bulgarian, etc. | MDIW13 subset | TBD |
| **Hebrew** | Hebrew | MDIW13 subset | TBD |

**Total Coverage**: 27+ scripts across 1.3M+ real images + 350,012 synthetic (v3, GCS-complete)

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
*See [GROUND_TRUTH_SUMMARY.md](../GROUND_TRUTH_SUMMARY.md) for annotation methodology and provenance*
