# Handwriting Detection & Legibility Assessment Datasets

> **Purpose**: Datasets for handwriting presence detection and legibility scoring
> **Target Model**: SigLIP v2 NaFlex (multi-task: 3 classification + 2 regression heads)
> **Label Type**: Word-level handwritten + legibility labels, character classes

---

## Primary Handwriting Datasets

| Dataset | Images | Labels | Restrictions | Scripts | Link |
|---------|--------|--------|--------------|---------|------|
| hiertext | 11,639 | `handwritten` + `legible` (word-level) | ⚠️ Train OK (8,281), test reserved | Mixed | [hiertext.md](../source/hiertext.md) |
| cocotext | 63,686 | `class` + `legibility` (word-level) | ⚠️ Train OK (43,686), test reserved | Latin | [cocotext.md](../source/cocotext.md) |
| muharaf | 24,952 | Line transcriptions (variable quality) | ✅ Unrestricted | Arabic cursive | [muharaf.md](../source/muharaf.md) |
| egyptian-handwriting | 11,216 | Word transcriptions (89 writers, ages 6-73) | ✅ CC-BY-4.0 | Arabic cursive | [egyptian-handwriting.md](../source/egyptian-handwriting.md) |
| hasyv2 | 168,233 | Math symbols (handwritten) | ⚠️ Train OK (151,410), test reserved | Symbols | [hasyv2.md](../source/hasyv2.md) |
| iam-handwriting | 13,353 | Line/word text | ✅ Unrestricted | English | [iam-handwriting.md](../source/iam-handwriting.md) |
| gnhk | 687 | Word-level polygons + legibility tags (%SC%/%NA%) | ✅ CC-BY-4.0 | English | [gnhk.md](../source/gnhk.md) |

**Total Available for Training**: ~287K images

---

## Graded Legibility Labels

**HierText** (GOLD STANDARD):

- Word-level `handwritten: bool` (presence detection)
- Word-level `legible: bool` (legibility assessment)
- **Use Case**: Derive handwriting presence ratio + legibility score per page

**COCO-Text**:

- Word-level `class: machine_printed|handwritten` (binary classification)
- Word-level `legibility: legible|illegible` (binary assessment)
- **Use Case**: Train binary handwriting classifier

**Muharaf** (Variable Quality):

- Historical Arabic manuscripts (clean to degraded)
- Line-level transcriptions (quality varies)
- **Use Case**: Train legibility regression on continuous quality spectrum

**SALAMI** (CALIBRATION ANCHOR):

- 250 manuscript images with 20-expert pixel-level legibility assessments
- 5-level rating scale: 0-20%, 20-40%, 40-60%, 60-80%, 80-100% readable
- 4,811 region-level annotations with expert agreement quantification
- Pre-computed mean score maps and uncertainty (std) maps
- 8 scripts: Armenian, Georgian, German, Gothic, Greek, Latin, Ottoman, Slavonic
- **Use Case**: Gold-standard calibration anchor for legibility regression (SIG-G4-2, SIG-G4-5)
- **Source**: [salami.md](../source/salami.md)

**Egyptian Handwriting** (Arabic Cursive):

- 11,216 word-level Arabic cursive images from 89 writers (ages 6-73)
- Variable quality from child to adult handwriting
- Only commercially-viable Arabic handwriting source (CC-BY-4.0)
- **Use Case**: Arabic cursive handwriting presence, script detection, legibility diversity
- **Source**: [egyptian-handwriting.md](../source/egyptian-handwriting.md)

**GNHK** (ILLEGIBLE CLASS SEED):

- 687 full-page handwritten documents (515 train + 172 test) with 42,561 word annotations
- Legibility tags: 571 %SC% (scribble) + 466 %NA% (unreadable) = **1,037 illegible words**
- Mixed content: 39,027 handwritten (H) + 3,534 printed (P) words
- Word-level polygon annotations with line grouping
- **Use Case**: Seed data for ILLEGIBLE class in legibility classification (SIG-G4-2)
- **Source**: [gnhk.md](../source/gnhk.md)

---

## CJK Handwriting Datasets

| Dataset | Images | Content | Scripts | License | Link |
|---------|--------|---------|---------|---------|------|
| casia-hwdb2-line | 52,160 | Chinese handwriting line crops (height=128px) | Hans (HANS) | MIT | [casia-hwdb2-line.md](../source/casia-hwdb2-line.md) |
| casia-hwdb2 | 5,091 pages | Full-page Chinese handwriting (300 DPI, DGRL format) | Hans (HANS) | Academic only | [casia-hwdb2.md](../source/casia-hwdb2.md) |
| ndl-minhon | ~32,822 | Kuzushiji manuscripts — 523K line annotations with isVertical flag | Jpan (JPAN) | CC BY-SA 4.0 | [ndl-minhon.md](../source/ndl-minhon.md) |
| ndl-docl | ~1,219 | Rare books subset (pre-1868) — kuzushiji annotated via layout VOC classes | Jpan (JPAN) | PDM 1.0 | [ndl-docl.md](../source/ndl-docl.md) |
| kuzushiji (K-49) | 270,912 | Pre-modern Japanese Hiragana (28×28 px) | Jpan (JPAN) | CC BY-SA 4.0 | [kuzushiji.md](../source/kuzushiji.md) |
| kuzushiji (K-Kanji) | 140,424 | Pre-modern Japanese Kanji (64×64 px) | Jpan (JPAN) | CC BY-SA 4.0 | [kuzushiji.md](../source/kuzushiji.md) |
| kuzushiji (K-MNIST) | 70,000 | Pre-modern Japanese Hiragana (28×28 px) | Jpan (JPAN) | CC BY-SA 4.0 | [kuzushiji.md](../source/kuzushiji.md) |

**CJK Total**: ~572K images (52K HANS line-level + 5K HANS pages + 515K JPAN historical cursive/kuzushiji)

⚠️ **Resolution Note**: K-MNIST / K-49 images are 28×28 px; K-Kanji 64×64 px — upscale to ≥224 px before SigLIP2.
⚠️ **License Note**: Kuzushiji CC BY-SA 4.0 requires ShareAlike on published derivative datasets/models.
⚠️ **License Note**: ndl-minhon CC BY-SA 4.0 requires ShareAlike on published derivative datasets/models.
⚠️ **Status Note**: ndl-minhon and ndl-docl require download before use (not yet on local storage).

---

## Character-Level Handwriting Datasets

| Dataset | Images | Content | Scripts | Link |
|---------|--------|---------|---------|------|
| nist-sd19 | 3,669 | Digits + letters | Latin | [nist-sd19.md](../source/nist-sd19.md) |
| nist-sd2 | 5,590 | Tax forms (handprint) | Latin | [nist-sd2.md](../source/nist-sd2.md) |
| nist-sd6 | 5,595 | Tax forms + handprint | Latin | [nist-sd6.md](../source/nist-sd6.md) |
| iiit-hw-hindi | 95,430 | Word-level Hindi HW (Devanagari) | Devanagari | [iiit-hw-hindi.md](../source/iiit-hw-hindi.md) |
| nepali-handwritten | 958 | Character classes | Devanagari | [nepali-handwritten.md](../source/nepali-handwritten.md) |
| pucit-ohul | 7,401 | Line text | Urdu | [pucit-ohul.md](../source/pucit-ohul.md) |
| khatt | ~1,633 | Paragraph Arabic HW (1,000 writers, OOD) | Arabic | [khatt.md](../source/khatt.md) |
| tibhcr | 141,698 | 47 character classes | Tibetan | [tibhcr.md](../source/tibhcr.md) |
| openpecha-ocr-drutsa | 32,364 | Tibetan line-level OCR | Tibetan | [openpecha-ocr-drutsa.md](../source/openpecha-ocr-drutsa.md) |
| dzongkha-digits | 1,000 | 10 digit classes | Tibetan | [dzongkha-digits.md](../source/dzongkha-digits.md) |

---

## Training Strategy

### Multi-Task SigLIP v2 NaFlex

**Classification Heads** (3):

1. **Handwriting Presence** (binary): machine_printed vs handwritten
2. **Legibility** (binary): legible vs illegible
3. **Script** (multi-class): When handwritten, which script family?

**Regression Heads** (2):

1. **Handwriting Ratio** (0-1): Percentage of page that is handwritten
2. **Legibility Score** (0-1): Average legibility of handwritten content

### Training Data Allocation

**Phase 1: Presence Detection**

- Primary: HierText train (8,281) + COCO-Text train (43,686)
- Augmentation: Muharaf (24,952, all handwritten)
- Negative examples: Pure machine-printed datasets (TableBank, PubTabNet)

**Phase 2: Legibility Assessment**

- Primary: HierText (word-level legibility labels)
- Calibration: SALAMI (20-expert pixel-level legibility, gold standard)
- Secondary: COCO-Text (binary legibility)
- Continuous spectrum: Muharaf (variable quality manuscripts)

**Phase 3: Script Classification**

- Character-level datasets for fine-grained script features
- NIST (Latin), Nepali/PUCIT (Indic), TIBHCR (Tibetan), Muharaf (Arabic), Egyptian HW (Arabic cursive)

---

## Benchmark Protection

**HierText**: Test split (3,358) RESERVED for scene text benchmark
**COCO-Text**: Val/test splits (20,000) RESERVED
**HASYv2**: Test split (16,823) RESERVED for math symbol benchmark

---

## Key Characteristics

**Real Handwriting**:

- IAM-Handwriting: English cursive (forms, sentences, words)
- Muharaf: Historical Arabic manuscripts
- Egyptian Handwriting: Arabic cursive (89 writers, CC-BY-4.0)
- NIST SD-2/6/19: Tax forms and digits (US government)
- SALAMI: Multi-script legibility calibration (250 images, 20 experts)

**Symbol Handwriting**:

- HASYv2: 168K math symbols (369 classes)

**Multi-Script Handwriting**:

- Nepali: Devanagari script
- IIIT-HW-Hindi: Devanagari (95K word-level, streaming)
- PUCIT-OHUL: Urdu script
- TIBHCR: Tibetan characters
- KHATT: Arabic cursive (1,000 writers, OOD evaluation)
- Egyptian Handwriting: Arabic cursive (CC-BY-4.0, commercial-viable)
- SALAMI: Multi-script legibility (calibration anchor)

---

*See [SCRIPTS.md](SCRIPTS.md) for script-specific training data*
*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
*See [GROUND_TRUTH_SUMMARY.md](../GROUND_TRUTH_SUMMARY.md) for annotation methodology and provenance*
