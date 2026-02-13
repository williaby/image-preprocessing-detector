# Benchmark Datasets & Restrictions

> **Purpose**: Track benchmark-reserved and benchmark-only datasets for training safety
> **Critical**: Protect test splits to prevent benchmark contamination

---

## Restriction Levels

### 🔒 Benchmark-Only (Test Only - NO Training)

These datasets are ONLY for benchmark evaluation:

| Dataset | Images | Purpose | Link |
|---------|--------|---------|------|
| cc-ocr | 7,058 | CJK complex script evaluation | [cc-ocr.md](../source/cc-ocr.md) |
| omnidocbench | Metadata | Multi-task document understanding | [omnidocbench.md](../source/omnidocbench.md) |

**Rules**:

- ❌ NEVER use for training
- ✅ Use for evaluation only
- ⚠️ Test set contamination risk if included in training

---

### ⚠️ Benchmark-Reserved (Train OK, Test Protected)

Train on train/val splits, but PROTECT test splits:

| Dataset | Total | Train Available | Test Reserved | Purpose | Link |
|---------|-------|-----------------|---------------|---------|------|
| ohr-bench | 8,561 | 6,849 | 1,712 | IQA benchmark | [ohr-bench.md](../source/ohr-bench.md) |
| diqa-5000 | 5,500 | 4,400 | 1,100 | IQA benchmark | [diqa-5000.md](../source/diqa-5000.md) |
| pubtabnet | 519,030 | 500,777 | 9,138 | Table structure benchmark (PubTables-1M) | [pubtabnet.md](../source/pubtabnet.md) |
| doclaynet | 80,863 | 69,375 | 6,480 | Layout detection benchmark | [doclaynet.md](../source/doclaynet.md) |
| funsd | 199 | 149 | 50 | Form understanding benchmark | [funsd.md](../source/funsd.md) |
| mdiw13 | 290,213 | 232,170 | 58,043 | Multi-script competition dataset | [mdiw13.md](../source/mdiw13.md) |
| mlt19 | 20,000 | 10,000 | 10,000 | Multi-lingual text detection | [mlt19.md](../source/mlt19.md) |
| cocotext | 63,686 | 43,686 | 20,000 | Scene text detection | [cocotext.md](../source/cocotext.md) |
| hiertext | 11,639 | 8,281 | 3,358 | Scene text + hierarchy | [hiertext.md](../source/hiertext.md) |
| hasyv2 | 168,233 | 151,410 | 16,823 | Math symbol recognition | [hasyv2.md](../source/hasyv2.md) |
| smartdoc-qa | 4,280 | 3,424 | 856 | Document QA benchmark | [smartdoc-qa.md](../source/smartdoc-qa.md) |

**Total Train Available**: ~1,030K images
**Total Test Reserved**: ~128K images

**Rules**:

- ✅ Can train on train/val splits
- ❌ NEVER use test splits for training
- ⚠️ Example: DIQA-5000 used for SigLIP v2 training (just avoid test split)

---

### ✅ Unrestricted (Full Training Allowed)

No benchmark restrictions:

| Dataset | Images | Purpose | Link |
|---------|--------|---------|------|
| tablebank | 278,582 | Table detection | [tablebank.md](../source/tablebank.md) |
| fintabnet | 97,475 | Financial table structure | [fintabnet.md](../source/fintabnet.md) |
| rvl-cdip | 400,000 | Document classification | [rvl-cdip.md](../source/rvl-cdip.md) |
| sroie | 973 | Receipt OCR (ICDAR 2019) | [sroie.md](../source/sroie.md) |
| funsd-plus | 1,139 | Extended forms | [funsd-plus.md](../source/funsd-plus.md) |
| doc3d | 100,000 | 3D document dewarping | [doc3d.md](../source/doc3d.md) |
| realdae | 1,200 | Real degradation pairs | [realdae.md](../source/realdae.md) |
| ... | ... | ... | ... |

**Rules**:

- ✅ Can use all splits for training
- ✅ No benchmark contamination risk
- ℹ️ Still recommended to hold out some data for internal validation

---

## Benchmark Protection Checklist

Before training ANY model:

- [ ] **Verify dataset restrictions** - Check this file for benchmark status
- [ ] **Review splits being used** - Ensure test splits are excluded where required
- [ ] **Document training data** - Record which splits were used in model card
- [ ] **Validate split files** - Check `splits/{dataset}/` for official split assignments

---

## Common Benchmarks

**IQA Benchmarks**:

- OHR-Bench (test: 1,712)
- DIQA-5000 (test: ~1,100)

**Layout Benchmarks**:

- DocLayNet (test: 6,480)
- PubTables-1M uses PubTabNet (test: 9,138)

**Text Detection Benchmarks**:

- COCO-Text (val/test: 20,000)
- MLT19 (val/test: 10,000)
- MDIW13 (competition test: 58,043)
- CC-OCR (test-only: 7,058)

**Form Understanding**:

- FUNSD (test: 50)

**Symbol Recognition**:

- HASYv2 (test: 16,823)

---

## Training Safety Rules

1. **Always check restriction level** before adding dataset to training pipeline
2. **Never mix test splits** into training data (even accidentally)
3. **Document which splits used** in training scripts and model cards
4. **Use official split files** from `splits/{dataset}/` directory
5. **Report benchmark scores separately** from internal validation scores

---

*See [IQA.md](IQA.md), [LAYOUT.md](LAYOUT.md), [TEXT_DETECTION.md](TEXT_DETECTION.md) for task-specific datasets*
*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
