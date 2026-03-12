# IQA Training Datasets

> **Purpose**: Datasets for training ML-based Image Quality Assessment (IQA) detectors
> **Target Model**: ResNet-18 Student (Phase 3)
> **Label Type**: Quality scores (0-100 or 1-5 MOS)

---

## Primary IQA Datasets

| Dataset | Images | Restrictions | Capture | Domain | Link |
|---------|--------|--------------|---------|--------|------|
| ohr-bench | 8,561 | 🔒 Test reserved (1,712) | Unknown | UNK | [ohr-bench.md](../source/ohr-bench.md) |
| diqa-5000 | 5,500 | ⚠️ Train OK (4,400), test reserved | Unknown | UNK | [diqa-5000.md](../source/diqa-5000.md) |
| realdae | 1,200 | ✅ Unrestricted (600 pairs) | 📱 Camera 100% | UNK | [realdae.md](../source/realdae.md) |
| ocr-quality | 1,000 | ✅ Unrestricted | Unknown | UNK | [ocr-quality.md](../source/ocr-quality.md) |
| q-doc | 4,260 | 🔒 Benchmark-only (test-only) | Unknown | UNK | [q-doc.md](../source/q-doc.md) |

**Total Available for Training**: ~11,000 images (q-doc is benchmark-only)

**Restriction Legend**:

- 🔒 **Test reserved**: Benchmark only, cannot train on any split
- ⚠️ **Train OK, test reserved**: Can train on train/val splits, protect test split
- ✅ **Unrestricted**: Full training allowed on all splits

---

## Training Strategy

**Model**: ResNet-18 Student (knowledge distillation from ResNet-50 Teacher)
**Loss**: MSE/MAE for quality score regression
**Labels**: Float quality scores normalized to 0-1 range

**Recommended Splits**:

1. **Base training**: ohr-bench train (6,849) + diqa-5000 train (4,400)
2. **Augmentation**: realdae (600 pairs with before/after) + ocr-quality (1,000)
3. **Validation**: ohr-bench val + diqa-5000 val
4. **Testing**: ohr-bench test + diqa-5000 test (NEVER use for training)

---

## Additional Datasets with IQA Potential

These datasets don't have explicit quality scores but contain degradation/quality annotations:

| Dataset | Images | IQA Signals | Link |
|---------|--------|-------------|------|
| tobacco800 | 1,290 | Real archival degradation | [tobacco800.md](../source/tobacco800.md) |
| dibco (all variants) | 343 | Binarization ground truth | [dibco.md](../source/dibco.md) |
| smartdoc-qa | 4,280 | Mobile capture quality | [smartdoc-qa.md](../source/smartdoc-qa.md) |
| doc3d | 100,000 | Dewarping quality | [doc3d.md](../source/doc3d.md) |
| john11-manuscripts | 210-520 | Historical manuscript degradation (foxing, ink fading, bleed-through, parchment aging) | [john11-manuscripts.md](../source/john11-manuscripts.md) |

**Usage**: Can be used for binary classification (degraded vs clean) or pseudo-labeled via teacher model

---

## Key Considerations

**Benchmark Protection**:

- ohr-bench test split (1,712 images): NEVER use for training
- diqa-5000 test split (~1,100 images): NEVER use for training
- q-doc (4,260 images): NEVER use for training (benchmark-only, test-only dataset)
- Used for SigLIP v2 training (just avoid test splits)

**Label Quality**:

- ohr-bench: Expert quality scores (0-100)
- diqa-5000: Human MOS ratings (1-5 scale)
- realdae: Before/after pairs with degradation scores
- ocr-quality: Human quality assessments

**Training Phase**: Phase 3 (Teacher-Student ML IQA) - ✅ COMPLETE

---

*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
*See [GROUND_TRUTH_SUMMARY.md](../GROUND_TRUTH_SUMMARY.md) for annotation methodology and provenance*
