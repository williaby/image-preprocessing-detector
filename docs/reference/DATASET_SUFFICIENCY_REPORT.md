# Dataset Sufficiency Report

**Generated**: measure_dataset_sufficiency.py (Auto-generated from dataset analysis)

**Overall Status**: ✅ SUFFICIENT
**Total Investment Needed**: $500.00

---

## Executive Summary

- **21** FRs have SUFFICIENT data
- **1** FRs have PARTIAL data (50-99% coverage)
- **1** FRs have CRITICAL GAPS (0-49% coverage)

### Data Composition

- **Total Samples**: 3,079,315
  - **Real-World**: 2,689,714 (87.3%)
  - **Synthetic**: 389,601 (12.7%)

### Synthetic Data Analysis

- 🔴 **Synthetic Only**: 3 FRs (100% synthetic, 0% real-world)
- ⚠️ **High Synthetic Ratio**: 1 FRs (>50% synthetic)
- ✅ **Real-World Dominant**: 18 FRs (≥80% real-world)

---

## Two-Part Sufficiency Analysis

> **Goal**: Real-world human-annotated data is our primary target. Synthetic/weak-supervision data helps meet minimum requirements but should be supplemented with real-world data when possible.

### Part 1: Real-World Only Coverage

Coverage using **only real-world, human-annotated datasets** (excludes synthetic, weak supervision, and generated data).

- ✅ **19** FRs have SUFFICIENT real-world data (≥100% of minimum)
- ⚠️ **1** FRs have PARTIAL real-world data (50-99% of minimum)
- ❌ **3** FRs have CRITICAL GAPS in real-world data (<50% of minimum)

### Part 2: Real-World + Synthetic Coverage

Coverage using **combined real-world + synthetic/weak-supervision data**. This represents our achievable coverage with current resources.

- ✅ **21** FRs have SUFFICIENT combined data (≥100% of minimum)
- ⚠️ **1** FRs have PARTIAL combined data (50-99% of minimum)
- ❌ **1** FRs have CRITICAL GAPS in combined data (<50% of minimum)

### Gap Analysis

- **1** Critical gaps in real-world data are filled by synthetic/weak-supervision
- **2** Critical gaps remain even with synthetic data

---

## FR-by-FR Breakdown

| FR ID | Requirement | Min Samples | Real-World | Synthetic | Total | Real-World Status | Combined Status | Notes |
|-------|-------------|-------------|------------|-----------|-------|-------------------|-----------------|-------|
| FR-2.1 | Document Classification Training | 10,000 | 7,909 (79%) | 72,317 | 80,226 (802%) ⚠️ | ⚠️ PARTIAL | ✅ SUFFICIENT | Real-world: 1414 invoices + 713 mobile receipts + 192 HITL receipts + 5590 tax forms (NIST DB2, 20 types) = 7909 total. Weak supervision: 69375 DocLayNet samples (image_only, born_digital, hybrid). VidOre V3 Finance: 2942 financial report samples (banking documents) |
| FR-2.3.1 | Overall Quality Labels | 50,000 | 50,000 (100%) | 0 | 50,000 (100%) | ✅ SUFFICIENT | ✅ SUFFICIENT | Phase 2: 50000 samples with weak supervision (BRISQUE/NIQE). Phase 3: Need DIQA-5000 (5k ground-truth) - PENDING RELEASE Sept 2025 |
| FR-2.3.2 | Sharpness Labels | 50,000 | 50,000 (100%) | 0 | 50,000 (100%) | ✅ SUFFICIENT | ✅ SUFFICIENT | 50000 samples with weak supervision |
| FR-2.3.3 | Color Fidelity Labels | 50,000 | 50,000 (100%) | 0 | 50,000 (100%) | ✅ SUFFICIENT | ✅ SUFFICIENT | 50000 samples with weak supervision |
| FR-4.2 | Layout Element Detection (Overall) | 26,500 | 1,107,470 (4179%) | 300,000 | 1,407,470 (5311%) | ✅ SUFFICIENT | ✅ SUFFICIENT | Real-world: DocLayNet 1,107,470 annotations | Synthetic: DocSynth-300K 300,000 samples |
| FR-4.2-EXTRA | Additional Layout Training (DocSynth-300K) | 300,000 | 300,000 (100%) | 0 | 300,000 (100%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocSynth-300K: 300,000 synthetic layout samples with 71-class taxonomy (pre-training for DocLayNet fine-tuning) |
| FR-4.2.1 | Class 1 Detection | 5,000 | 22,524 (450%) | 0 | 22,524 (450%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 1 samples |
| FR-4.2.10 | Class 10 Detection | 2,000 | 510,377 (25519%) | 0 | 510,377 (25519%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 10 samples |
| FR-4.2.11 | Class 11 Detection | 2,000 | 5,071 (254%) | 0 | 5,071 (254%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 11 samples |
| FR-4.2.2 | Class 2 Detection | 2,000 | 6,318 (316%) | 0 | 6,318 (316%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 2 samples |
| FR-4.2.3 | Class 3 Detection | 3,000 | 25,027 (834%) | 0 | 25,027 (834%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 3 samples |
| FR-4.2.4 | Class 4 Detection | 3,000 | 185,660 (6189%) | 0 | 185,660 (6189%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 4 samples |
| FR-4.2.5 | Class 5 Detection | 2,500 | 70,878 (2835%) | 0 | 70,878 (2835%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 5 samples |
| FR-4.2.6 | Class 6 Detection | 2,000 | 58,022 (2901%) | 0 | 58,022 (2901%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 6 samples |
| FR-4.2.7 | Class 7 Detection | 1,500 | 45,976 (3065%) | 0 | 45,976 (3065%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 7 samples |
| FR-4.2.8 | Class 8 Detection | 1,500 | 142,884 (9526%) | 0 | 142,884 (9526%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 8 samples |
| FR-4.2.9 | Class 9 Detection | 2,000 | 34,733 (1737%) | 0 | 34,733 (1737%) | ✅ SUFFICIENT | ✅ SUFFICIENT | DocLayNet class 9 samples |
| FR-4.4 | Parasitic Content Detection | 10,000 | 0 (0%) | 2,942 | 2,942 (29%) 🔴 | ❌ GAP | ❌ CRITICAL GAP | VidOre V3 Finance: 2,942 annotations (spatial heuristics) |
| FR-4.7 | Vertical Text Detection | 5,000 | 0 (0%) | 5,000 | 5,000 (100%) 🔴 | ❌ GAP | ✅ SUFFICIENT | Synthetic (rotation augmentation): 5,000 samples with orientation annotations (0°, 90°, 180°, 270°) |
| FR-5.1 | Handwriting Detection | 10,000 | 10,373 (104%) | 0 | 10,373 (104%) | ✅ SUFFICIENT | ✅ SUFFICIENT | IAM Handwriting: 10373 text line samples |
| FR-5.2 | Signature Detection | 6,000 | 6,257 (104%) | 0 | 6,257 (104%) | ✅ SUFFICIENT | ✅ SUFFICIENT | SignaTR6K: 6257 signature samples |
| FR-5.3 | Multilingual Text Detection | 235 | 235 (100%) | 0 | 235 (100%) | ✅ SUFFICIENT | ✅ SUFFICIENT | WiLI-2018: 235 languages, 235000 paragraphs |
| FR-7.1 | DQS Routing Matrix (3x3 grid) | 57,500 | 0 (0%) | 9,342 | 9,342 (16%) 🔴 | ❌ GAP | ⚠️ PARTIAL | Weak supervision: 6400 DocLayNet samples with DQS routing labels (Degradation × Structural Complexity). VidOre V3 Finance: 2942 financial document samples (classical CV analysis). Routing matrix coverage: 7/9 bins populated |

---

## Critical Gaps (Priority 1)

| FR ID | Requirement | Missing Samples | Cost Estimate | Notes |
|-------|-------------|-----------------|---------------|-------|
| FR-4.4 | Parasitic Content Detection | 7,058 | $500.00 | VidOre V3 Finance: 2,942 annotations (spatial heuristics) |

**Total Investment for Critical Gaps**: $500.00

---

## FR-4.2: Layout Element Coverage (11 Classes)

| Class ID | Min Required | Current Count | Status |
|----------|--------------|---------------|--------|
| Class 1 | 5,000 | 22,524 | ✅ |
| Class 2 | 2,000 | 6,318 | ✅ |
| Class 3 | 3,000 | 25,027 | ✅ |
| Class 4 | 3,000 | 185,660 | ✅ |
| Class 5 | 2,500 | 70,878 | ✅ |
| Class 6 | 2,000 | 58,022 | ✅ |
| Class 7 | 1,500 | 45,976 | ✅ |
| Class 8 | 1,500 | 142,884 | ✅ |
| Class 9 | 2,000 | 34,733 | ✅ |
| Class 10 | 2,000 | 510,377 | ✅ |
| Class 11 | 2,000 | 5,071 | ✅ |

---

## FR-2.3: Learned Quality Dimensions

| Dimension | Required | Current | Status |
|-----------|----------|---------|--------|
| Overall Quality | 50,000 | 50,000 | ✅ |
| Sharpness | 50,000 | 50,000 | ✅ |
| Color Fidelity | 50,000 | 50,000 | ✅ |

---

## FR-5.3: Multilingual Coverage (235 Languages)

**Top 20 Languages by Sample Count:**

| Language Code | Paragraph Count |
|---------------|----------------|
| est | 1,000 |
| swe | 1,000 |
| mai | 1,000 |
| oci | 1,000 |
| tha | 1,000 |
| orm | 1,000 |
| lim | 1,000 |
| guj | 1,000 |
| pnb | 1,000 |
| zea | 1,000 |
| krc | 1,000 |
| hat | 1,000 |
| pcd | 1,000 |
| tam | 1,000 |
| vie | 1,000 |
| pan | 1,000 |
| szl | 1,000 |
| ckb | 1,000 |
| fur | 1,000 |
| wuu | 1,000 |

**Total**: 235 languages, 235,000 paragraphs

---

## Recommendations

### Priority 0: Real-World Data Acquisition Strategy

> **Philosophy**: While synthetic/weak-supervision data helps meet minimum requirements, **real-world human-annotated data should be prioritized** for production model quality.

**Focus areas for real-world data acquisition:**

- **FR-4.7** (Vertical Text Detection): Need 5,000 real-world samples (currently 0/5,000, filled with 5,000 synthetic)

### Priority 1: Benchmark Dataset Usage Policy

> **IMPORTANT**: Several datasets are located in `/data/benchmarks/` but have train/validation splits that could be used for training. **Test splits must NEVER be used for training.**

**Benchmark datasets with usable train/validation splits:**

- **SignaTR6K**: Train (5,169) + Validation (530) = 5,699 usable for FR-5.2 signature detection
  - ❌ **Test split (558) is RESERVED for peer benchmarking**
- **WiLI-2018**: Train split (117,500) usable for FR-5.3 multilingual detection
  - ❌ **Test split (117,500) is RESERVED for peer benchmarking**
- **DocLayNet**: Used for weak supervision label generation (parasitic content, document classification, DQS routing)
  - ⚠️ **Verify test split is excluded from weak supervision generation**

### Priority 2: Structural Relationship Annotations (~$8,500)

- **FR-4.5**: Footnote linking (6k pages, $1,500)
- **FR-4.12**: Reading order sequences (40k pages, $5,000)
- **FR-4.6**: Figure-caption linking (10k pairs, $1,000)
- **FR-4.4**: Parasitic content flags (10k pages, $500)
- **FR-4.7**: Vertical text orientation (5k samples, $500)

### Priority 3: Weak Supervision Generation (FREE)

- **FR-2.3**: Generate 3-dimension quality labels using BRISQUE, NIQE, Laplacian, histogram analysis
- **FR-7.1**: Generate DQS routing matrix labels (degradation + structural complexity)

### Priority 4: Wait for DIQA-5000 (Sept 2025)

- Replace weak supervision with 5k ground-truth 3-dimension quality labels
- Validate learned quality models against human ratings

---

**Report End**
