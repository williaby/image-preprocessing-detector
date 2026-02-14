# Stream 3: Go/No-Go Decision Report

> Generated: 2026-02-14 18:42 UTC
>
> Phase 10 Stream 3 benchmarks heuristic detectors (Stream 2) against
> real labeled datasets to determine if ML upgrades (Stream 4) are needed.

## Executive Summary

| Detector | Metric | Dataset | Score | Target | Status | Decision |
|----------|--------|---------|-------|--------|--------|----------|
| ScriptDetectorHeuristic | accuracy | mlt19 | 15.6% | 80% | FAIL | Train SigLIP2 script head (Stream 4) |
| DocumentSourceClassifier | accuracy | smartdoc-qa | 64.7% | 85% | FAIL | Train ML document source classifier |
| OrientationDetector | accuracy | synth_multiscript_v3 | - | 85% | NOT RUN | - |
| ShadowDetector | f1 | sd7k | 60.1% | 85% | FAIL | Extend ML IQA with shadow head |
| WarpingDetector | f1 | anyphotodoc6300 | 94.7% | 80% | PASS | Ship heuristic |
| HandwritingDetector | f1 | cocotext | 5.3% | 75% | FAIL* | Train handwriting detection head |

**Summary**: 5 benchmarks run, 1 PASS, 4 FAIL
\* Result marked unreliable (insufficient positive samples)

## Detailed Results

### Script Detection (MLT-2019 + IndicDLP)

**Dataset**: mlt19 | **Samples**: 2,000

**Family-Level Metrics**:

- Accuracy: 15.6%
- Macro F1: 0.1223
- Weighted F1: 0.1199
- Cohen's Kappa: 0.0192

**Confusion Matrix**:

```
                     cjk       latin      arabic  devanagari     unknown
------------------------------------------------------------------------
       cjk           223           7          89          33          77
     latin           472          15         244         123         192
    arabic            59           1          34           7          29
devanagari           161           3          80          40         111
   unknown             0           0           0           0           0
```

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| cjk | 0.2437 | 0.5198 | 0.3318 | 429 |
| latin | 0.5769 | 0.0143 | 0.0280 | 1046 |
| arabic | 0.0761 | 0.2615 | 0.1179 | 130 |
| devanagari | 0.1970 | 0.1013 | 0.1338 | 395 |
| unknown | 0.0000 | 0.0000 | 0.0000 | 0 |
**ISO-Level Metrics**:

- Accuracy: 7.5%
- Macro F1: 0.0513
- Weighted F1: 0.0427
- Cohen's Kappa: -0.0042

**Confusion Matrix**:

```
        Arab  Beng  Deva  Hans  Jpan  Kore  Latn
------------------------------------------------
Arab      34     0     7    59     0     0     1
Beng      42     0    23    64     0     0     3
Deva      38     0    17    97     0     0     0
Hans      39     0    16    54     0     0     3
Jpan      18     0    11    67     0     0     2
Kore      32     0     6   102     0     0     2
Latn     244     0   123   472     0     0    15
```

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| Arab | 0.0761 | 0.3366 | 0.1241 | 101 |
| Beng | 0.0000 | 0.0000 | 0.0000 | 132 |
| Deva | 0.0837 | 0.1118 | 0.0958 | 152 |
| Hans | 0.0590 | 0.4821 | 0.1052 | 112 |
| Jpan | 0.0000 | 0.0000 | 0.0000 | 98 |
| Kore | 0.0000 | 0.0000 | 0.0000 | 142 |
| Latn | 0.5769 | 0.0176 | 0.0341 | 854 |

**Supplementary: IndicDLP (12 Indic Languages)**:

> Supplementary evaluation on 12 Indic languages. Does NOT affect Go/No-Go decision.

**Samples**: 5,000

- Family-level accuracy: 7.4%
- Macro F1: 0.0326
- Cohen's Kappa: 0.0066
- ISO-level accuracy: 30.7%

| Script (ISO) | Family Accuracy | Samples |
|--------------|-----------------|---------|
| Beng | 8.0% | 829 |
| Deva | 13.1% | 892 |
| Gujr | 10.8% | 437 |
| Guru | 9.9% | 365 |
| Knda | 1.8% | 458 |
| Latn | 0.6% | 470 |
| Mlym | 1.1% | 469 |
| Orya | 17.7% | 435 |
| Taml | 0.6% | 326 |
| Telu | 3.5% | 319 |

**Latency**: mean=2.5ms, p95=5.5ms

**Go/No-Go**: FAIL (15.6% vs 80% target)
**Recommended Action**: Train SigLIP2 script head (Stream 4)

### Document Source (SmartDoc-QA + Tobacco800 + DocReal)

**Dataset**: smartdoc-qa+tobacco800+docreal | **Samples**: 1,000

**smartdoc-qa+tobacco800+docreal Metrics**:

- Accuracy: 64.7%
- Precision: 1.0000
- Recall: 0.2940
- F1: 0.4544
- ROC-AUC: 0.7772
- TP=147, FP=0, TN=500, FN=353

**Latency**: mean=10.7ms, p95=20.7ms

**Go/No-Go**: FAIL (64.7% vs 85% target)
**Recommended Action**: Train ML document source classifier

### Shadow Detection (SD7K + WSRD)

**Dataset**: sd7k+wsrd | **Samples**: 1,720

**SD7K-test Metrics**:

- Accuracy: 65.4%
- Precision: 0.7097
- Recall: 0.5211
- F1: 0.6009
- ROC-AUC: 0.7311
- TP=396, FP=162, TN=598, FN=364

**Score Distribution**:

- Shadow images: mean=0.1407, std=0.1328
- Clean images: mean=0.0530, std=0.0754

**Validation Dataset**:

- Dataset: WSRD-val
- F1: 0.6316, Accuracy: 54.5%

**Latency**: mean=16.9ms, p95=20.9ms

**Go/No-Go**: FAIL (60.1% vs 85% target)
**Recommended Action**: Extend ML IQA with shadow head

### Warping Detection (AnyPhotoDoc6300 + WarpDoc)

**Dataset**: anyphotodoc6300+warpdoc | **Samples**: 8,459

**Primary Metrics**:

- Accuracy: 90.4%
- Precision: 0.9766
- Recall: 0.9193
- F1: 0.9471
- ROC-AUC: 0.8974
- TP=5797, FP=139, TN=314, FN=509

**WarpDoc Per-Type Results**:

| Type | F1 | Accuracy | Samples |
|------|-----|----------|---------|
| Curved | 0.7601 | 70.3% | 340 |
| Fold | 0.7743 | 72.1% | 340 |
| Incomplete | 0.7696 | 71.5% | 340 |
| Perspective | 0.7654 | 72.1% | 340 |
| Random | 0.7845 | 73.8% | 340 |

**Latency**: mean=15.8ms, p95=27.1ms

**Go/No-Go**: PASS (94.7% vs 80% target)

### Handwriting Detection (COCO-Text)

**Dataset**: cocotext | **Samples**: 205

**cocotext Metrics**:

- Accuracy: 13.2%
- Precision: 0.0273
- Recall: 1.0000
- F1: 0.0532
- ROC-AUC: 0.609
- TP=5, FP=178, TN=22, FN=0

**Latency**: mean=3.3ms, p95=6.3ms

> **Caveat**: COCO-Text is scene text (outdoor signs), not documents. Only 5 positive samples - results have limited statistical significance.

**Go/No-Go**: FAIL (5.3% vs 75% target)
**Recommended Action**: Train handwriting detection head

### Tier 3: Descriptive Statistics (No GT)

#### BlankPageDetector

- Synthetic accuracy: 100.0%
- Real docs false-blank rate: 0.0% (0/200)

#### CodeDetector

- Detection rate: 2.5% (5/200)
- Score distribution: mean=0.3272, p95=0.4343

#### TableComplexityAnalyzer

- Mean complexity: 0.3275
- P95 complexity: 0.6000

## ML Upgrade Recommendations

### ScriptDetectorHeuristic

- **Current**: 15.6% | **Target**: 80% | **Gap**: 64.4%
- **Action**: Train SigLIP2 script head (Stream 4)
- **Dataset**: mlt19

### DocumentSourceClassifier

- **Current**: 64.7% | **Target**: 85% | **Gap**: 20.3%
- **Action**: Train ML document source classifier
- **Dataset**: smartdoc-qa

### ShadowDetector

- **Current**: 60.1% | **Target**: 85% | **Gap**: 24.9%
- **Action**: Extend ML IQA with shadow head
- **Dataset**: sd7k

### HandwritingDetector

- **Current**: 5.3% | **Target**: 75% | **Gap**: 69.7%
- **Action**: Train handwriting detection head
- **Dataset**: cocotext
