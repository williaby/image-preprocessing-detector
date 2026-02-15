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
| hasyv2 | 168,233 | Math symbols (handwritten) | ⚠️ Train OK (151,410), test reserved | Symbols | [hasyv2.md](../source/hasyv2.md) |
| iam-handwriting | 13,353 | Line/word text | ✅ Unrestricted | English | [iam-handwriting.md](../source/iam-handwriting.md) |

**Total Available for Training**: ~275K images

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

---

## Character-Level Handwriting Datasets

| Dataset | Images | Content | Scripts | Link |
|---------|--------|---------|---------|------|
| nist-sd19 | 3,669 | Digits + letters | Latin | [nist-sd19.md](../source/nist-sd19.md) |
| nist-sd2 | 5,590 | Tax forms (handprint) | Latin | [nist-sd2.md](../source/nist-sd2.md) |
| nist-sd6 | 5,595 | Tax forms + handprint | Latin | [nist-sd6.md](../source/nist-sd6.md) |
| nepali-handwritten | 958 | Character classes | Devanagari | [nepali-handwritten.md](../source/nepali-handwritten.md) |
| pucit-ohul | 7,401 | Line text | Urdu | [pucit-ohul.md](../source/pucit-ohul.md) |
| tibhcr | 141,698 | 47 character classes | Tibetan | [tibhcr.md](../source/tibhcr.md) |
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
- Secondary: COCO-Text (binary legibility)
- Continuous spectrum: Muharaf (variable quality manuscripts)

**Phase 3: Script Classification**

- Character-level datasets for fine-grained script features
- NIST (Latin), Nepali/PUCIT (Indic), TIBHCR (Tibetan), Muharaf (Arabic)

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
- NIST SD-2/6/19: Tax forms and digits (US government)

**Symbol Handwriting**:

- HASYv2: 168K math symbols (369 classes)

**Multi-Script Handwriting**:

- Nepali: Devanagari script
- PUCIT-OHUL: Urdu script
- TIBHCR: Tibetan characters

---

*See [SCRIPTS.md](SCRIPTS.md) for script-specific training data*
*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
*See [GROUND_TRUTH_SUMMARY.md](../GROUND_TRUTH_SUMMARY.md) for annotation methodology and provenance*
