# Training Dataset Concept Document

**Version**: 1.0
**Date**: 2025-11-14
**Purpose**: Define training data requirements from first principles to meet functional requirements and project goals

---

## Executive Summary

**Project Goal**: Build ML models that detect preprocessing issues and content types in documents for RAG system optimization.

**Core ML Tasks**:
1. **Image Quality Assessment (IQA)**: Multi-label classification of quality defects (blur, skew, noise, contrast, etc.)
2. **Layout Detection**: Object detection for 11 layout element classes (text, table, figure, etc.)
3. **Text Detection Gate**: Binary classification of text presence
4. **Specialized Content Detection**: Handwriting, signatures, stamps, formulas, watermarks

**Key Insight**: Training data requirements should be derived from **what attributes the models need to learn**, not from arbitrary document type categories.

---

## Part 1: Fundamental Data Attributes Framework

### 1.1 Core Principle: Attribute-Based Coverage

**Traditional Approach (Flawed)**:
- Define document types (Academic, Business, Legal, etc.)
- Collect examples of each type
- Hope coverage is sufficient

**Proposed Approach (Attribute-Based)**:
- Identify **attributes that models must discriminate**
- Define **attribute value ranges** and **distributions**
- Measure **coverage of attribute space**
- Determine **statistical sufficiency** for each attribute

---

### 1.2 Five Attribute Dimensions

**Every training sample must be characterized along these five dimensions:**

#### Dimension 1: Defect/Feature Attributes (What we're detecting)

**For IQA Models**:
| Attribute | Value Range | Distribution Requirement |
|-----------|-------------|-------------------------|
| **Blur Severity** | 0% (sharp) → 100% (severe blur) | Uniform across 10% bins (0-10%, 10-20%, ..., 90-100%) |
| **Skew Angle** | -15° → +15° | Uniform across 2° bins, heavy sampling at ±0° (90% of documents) |
| **Noise Level** | 0 (clean) → 1.0 (heavy noise) | Log-normal distribution (most documents clean, tail of noisy) |
| **Contrast** | 0.0 (low) → 1.0 (high) | Normal distribution centered at 0.6-0.8 (typical) |
| **DPI** | 72 → 1200 DPI | Bimodal: 72-150 (mobile/web), 300 (standard scan), 600+ (professional) |

**For Layout Detection**:
| Attribute | Value Range | Distribution Requirement |
|-----------|-------------|-------------------------|
| **Element Type** | 11 classes (Text, Title, Table, Figure, etc.) | Balanced per class (min 1000 samples/class) |
| **Element Size** | Small (< 5% page area) → Large (> 50% page area) | Power-law distribution (many small, few large) |
| **Element Density** | Sparse (1-3 elements/page) → Dense (10+ elements/page) | Normal distribution (mean: 5-7 elements/page) |
| **Element Overlap** | None → Heavy (nested elements) | 80% no overlap, 15% slight, 5% heavy |

**For Specialized Content**:
| Attribute | Value Range | Distribution Requirement |
|-----------|-------------|-------------------------|
| **Handwriting Presence** | 0% → 100% (% of page that's handwritten) | Bimodal: 0% (printed), 5-20% (annotations), 80-100% (handwritten notes) |
| **Signature Presence** | Yes/No | 10% Yes, 90% No (realistic business document ratio) |
| **Stamp/Seal Presence** | Yes/No | 5% Yes, 95% No (realistic ratio) |

---

#### Dimension 2: Co-occurrence Patterns (Realistic defect combinations)

**Key Insight**: Real documents have **multiple simultaneous defects**, not single isolated issues.

**Required Co-occurrence Coverage**:

| Primary Defect | Common Co-occurring Defects | Required Samples |
|----------------|----------------------------|------------------|
| **Blur** | + Low DPI (60%), + Noise (40%), + Low Contrast (30%) | 1000 samples each combination |
| **Skew** | + Blur (50%), + Noise (30%), + Perspective (20%) | 500 samples each combination |
| **Noise** | + Low Contrast (70%), + Blur (40%), + Fading (30%) | 500 samples each combination |
| **Low Contrast** | + Noise (70%), + Fading (50%), + Bleed-through (20%) | 500 samples each combination |

**Combinatorial Coverage Metric**:
- **Pairwise Coverage**: All pairwise defect combinations represented (45 combinations for 10 defects)
- **Triple Coverage**: Top 10 most common triple combinations represented
- **Minimum Samples**: 100 samples per pairwise combination, 500 for high-priority combinations

**How to Measure**:
```python
# Coverage matrix: defect A (rows) × defect B (columns)
coverage_matrix[defect_a][defect_b] = count_samples(has_both(defect_a, defect_b))

# Target: All cells > 100 samples
# High priority cells (common combinations): > 500 samples
```

---

#### Dimension 3: Content Variability (What's ON the document)

**Not "document type categories" but content attributes that affect model behavior:**

| Content Attribute | Value Range | Why It Matters | Distribution Requirement |
|-------------------|-------------|----------------|-------------------------|
| **Text Density** | 0% → 100% of page area | Text Detection Gate, Layout Detection | Uniform across 10% bins |
| **Table Presence** | 0-5 tables per page | Layout Detection (Table class) | Power-law (most pages 0-1, some 2-5) |
| **Figure Presence** | 0-10 figures per page | Layout Detection (Figure class) | Power-law (most pages 0-2, some 3-10) |
| **Formula Presence** | 0-20 formulas per page | Specialized Content Detection | Power-law (most pages 0, scientific docs 5-20) |
| **Column Count** | 1-3 columns | Layout Detection, Reading Order | 70% single, 25% double, 5% triple |
| **Font Diversity** | 1-5 unique fonts | Layout Detection robustness | Normal (mean: 2-3 fonts) |
| **Language** | Monolingual vs Multi-lingual | Language Detection, OCR routing | 85% monolingual, 15% mixed |
| **Content Modality** | Printed-only, Handwritten-only, Mixed | Handwriting Detection | 85% printed, 5% handwritten, 10% mixed |

**Key Principle**: These are **independent attributes**, not document types. A "Business" document can have:
- 40% text density + 2 tables + 1 figure + 2 columns (quarterly report)
- 80% text density + 0 tables + 0 figures + 1 column + handwritten signature (contract)
- 20% text density + 5 tables + 0 figures + 2 columns (financial statement)

**Coverage Metric**:
- For each content attribute, measure distribution across training data
- Compare to target distribution (derived from real-world document corpus analysis)
- **Sufficiency**: KL divergence < 0.1 between training distribution and target distribution

---

#### Dimension 4: Capture Method Variability (How the document was created/digitized)

**Capture methods introduce systematic defect patterns:**

| Capture Method | Characteristic Defects | Required Samples | Example Use Case |
|----------------|----------------------|------------------|------------------|
| **Flatbed Scanner (Consumer)** | Skew (±2-5°), Low DPI (150-300), Edge shadows | 5000 samples | Home/office scanning |
| **Flatbed Scanner (Professional)** | High DPI (600+), Minimal defects, Color accuracy | 2000 samples | Archives, professional digitization |
| **Sheet-fed Scanner** | Alignment issues, Streaks, Consistent DPI (300) | 3000 samples | Bulk office scanning |
| **Mobile Camera (Good Lighting)** | Perspective distortion, Slight blur, Uneven illumination | 5000 samples | Mobile document capture (receipts, forms) |
| **Mobile Camera (Poor Lighting)** | Heavy blur, Low contrast, Noise, Illumination gradient | 3000 samples | Real-world mobile capture |
| **Desktop Camera/Webcam** | Perspective, Warping (books), Shadows | 2000 samples | Desktop document photography |
| **Photocopier (1st generation)** | Slight noise, Contrast loss (~10%) | 2000 samples | Office document workflow |
| **Photocopier (2nd+ generation)** | Heavy noise, Significant contrast loss (~30%), Artifacts | 1000 samples | Degraded copies |
| **Born-digital (PDF from Word/LaTeX)** | Minimal defects, High DPI, Clean rendering | 10000 samples | Modern digital documents |
| **Historical Scan (Old equipment)** | Low DPI (72-150), Noise, Color shift, Fading | 1000 samples | Digitized archives |

**Why This Matters**:
- Flatbed scanners introduce skew + edge shadows
- Mobile cameras introduce perspective + illumination gradients
- Photocopiers introduce noise + contrast loss
- Each capture method has a **characteristic defect signature**

**Coverage Metric**:
- Minimum samples per capture method (listed above)
- For each capture method, measure defect distribution and ensure it matches expected signature
- **Sufficiency**: Each capture method's defect signature is represented with ≥1000 samples

---

#### Dimension 5: Semantic Context (Business domain - determines risk tolerance)

**Different business contexts have different accuracy requirements:**

| Semantic Context | Risk Tolerance | Required Accuracy | Training Data Quality | Sample Requirements |
|------------------|----------------|-------------------|----------------------|-------------------|
| **Legal (Contracts, Court Documents)** | **ZERO** - Errors have legal liability | **>99%** IQA accuracy, **>95%** layout accuracy | Manually verified ground truth | 10000 samples, expert-verified |
| **Financial (Invoices, Statements, Tax Forms)** | **VERY LOW** - Errors affect money | **>98%** IQA accuracy, **>95%** layout accuracy | Manually verified ground truth | 10000 samples, expert-verified |
| **Medical (Patient Records, Prescriptions)** | **VERY LOW** - Errors affect health | **>98%** IQA accuracy, **>95%** layout accuracy | Manually verified ground truth | 5000 samples, expert-verified |
| **Business Operations (Reports, Memos, Presentations)** | **LOW** - Errors cause inefficiency | **>95%** IQA accuracy, **>90%** layout accuracy | Semi-automated with spot-checks | 15000 samples, 10% verified |
| **Academic (Papers, Textbooks, Research)** | **MEDIUM** - Errors acceptable for corpus building | **>90%** IQA accuracy, **>85%** layout accuracy | Automated with weak supervision | 20000 samples, 5% verified |
| **General Knowledge (News, Blogs, General Docs)** | **HIGH** - Errors acceptable | **>85%** IQA accuracy, **>80%** layout accuracy | Automated with weak supervision | 30000 samples, 1% verified |

**Key Principle**: **Risk tolerance determines ground truth quality requirements**, not just sample quantity.

**Coverage Metric**:
- For high-risk contexts (Legal, Financial, Medical): 100% manual verification of ground truth
- For medium-risk (Business Operations): 10-20% manual verification
- For low-risk (Academic, General): 1-5% manual verification
- **Sufficiency**: Validation accuracy on held-out test set meets target accuracy for each context

---

## Part 2: Statistical Sufficiency Criteria

### 2.1 How Do We Know When We Have Enough Data?

**Traditional Approach (Flawed)**:
- Collect X GB of data or Y thousand samples
- Hope it's sufficient

**Proposed Approach (Metric-Driven)**:
- Define **sufficiency metrics** for each attribute dimension
- Measure coverage continuously as data is collected
- **Stop collecting when all sufficiency metrics are met**

---

### 2.2 Sufficiency Metrics by Dimension

#### Metric 1: Per-Class Minimum Threshold

**For Classification Tasks** (IQA, Text Gate, Specialized Content):

| Task | Minimum Samples per Class | Rationale |
|------|--------------------------|-----------|
| **IQA Multi-label** | 1000 samples per defect type | Need balanced representation across all defect types |
| **Layout Detection** | 1000 samples per layout class | YOLOv8 requires minimum samples per class for balanced training |
| **Text Detection Gate** | 5000 no-text, 5000 text | Binary classifier needs balanced classes |
| **Handwriting Detection** | 2000 printed, 2000 handwritten, 2000 mixed | Three-class classifier |

**How to Measure**:
```python
# For each class in task T
min_samples_per_class[T] = min([count_samples(class_c) for class_c in classes[T]])

# Sufficiency check
if min_samples_per_class[T] >= THRESHOLD[T]:
    print(f"Task {T}: SUFFICIENT")
else:
    print(f"Task {T}: INSUFFICIENT - need {THRESHOLD[T] - min_samples_per_class[T]} more samples for class {argmin(count_samples)}")
```

---

#### Metric 2: Severity/Intensity Distribution Matching

**For IQA Tasks**: Ensure defect severity distributions match real-world expectations.

**Target Distributions** (derived from real-world corpus analysis):

| Defect | Target Distribution | Current Distribution | KL Divergence | Status |
|--------|---------------------|---------------------|---------------|--------|
| **Blur** | 70% clean (0-10%), 20% slight (10-30%), 8% moderate (30-60%), 2% severe (60-100%) | TBD | TBD | TBD |
| **Skew** | 60% perfect (0-1°), 30% slight (1-3°), 8% moderate (3-7°), 2% severe (7-15°) | TBD | TBD | TBD |
| **Noise** | 80% clean, 15% slight, 4% moderate, 1% severe | TBD | TBD | TBD |

**How to Measure**:
```python
# Define target distribution (from real-world analysis or domain knowledge)
target_dist[defect] = [0.7, 0.2, 0.08, 0.02]  # bins: [0-10%, 10-30%, 30-60%, 60-100%]

# Measure current distribution in training data
current_dist[defect] = compute_histogram(training_data, defect, bins=[0, 10, 30, 60, 100])

# Compute KL divergence
kl_div[defect] = kl_divergence(current_dist[defect], target_dist[defect])

# Sufficiency check
if kl_div[defect] < 0.1:  # Low divergence threshold
    print(f"{defect}: SUFFICIENT (KL={kl_div[defect]:.3f})")
else:
    print(f"{defect}: INSUFFICIENT (KL={kl_div[defect]:.3f}) - adjust data collection")
```

**Sufficiency Threshold**: KL divergence < 0.1 for all defect types.

---

#### Metric 3: Co-occurrence Coverage

**For Realistic Multi-Defect Scenarios**:

**Target**: All pairwise defect combinations represented with ≥100 samples each.

**How to Measure**:
```python
# Build co-occurrence matrix
cooccurrence_matrix = np.zeros((num_defects, num_defects))

for sample in training_data:
    defects = get_defects(sample)
    for defect_a in defects:
        for defect_b in defects:
            if defect_a != defect_b:
                cooccurrence_matrix[defect_a][defect_b] += 1

# Sufficiency check
min_cooccurrence = np.min(cooccurrence_matrix[np.triu_indices(num_defects, k=1)])

if min_cooccurrence >= 100:
    print("Co-occurrence coverage: SUFFICIENT")
else:
    print(f"Co-occurrence coverage: INSUFFICIENT - minimum cell has {min_cooccurrence} samples")
    print(f"Under-represented combinations: {find_cells_below_threshold(cooccurrence_matrix, 100)}")
```

**Sufficiency Threshold**: All pairwise combinations ≥100 samples, high-priority combinations ≥500 samples.

---

#### Metric 4: Attribute Space Coverage

**For Content Variability Attributes**:

**How to Measure**:
```python
# For each content attribute, measure distribution
attributes = ["text_density", "table_count", "figure_count", "column_count", "font_diversity"]

for attr in attributes:
    # Compute distribution in training data
    current_dist[attr] = compute_histogram(training_data, attr)

    # Compare to target distribution (from real-world corpus)
    kl_div[attr] = kl_divergence(current_dist[attr], target_dist[attr])

    # Sufficiency check
    if kl_div[attr] < 0.1:
        print(f"{attr}: SUFFICIENT (KL={kl_div[attr]:.3f})")
    else:
        print(f"{attr}: INSUFFICIENT (KL={kl_div[attr]:.3f})")
```

**Sufficiency Threshold**: KL divergence < 0.1 for all content attributes.

---

#### Metric 5: Capture Method Representation

**For Each Capture Method**:

| Capture Method | Minimum Samples | Current Count | Status |
|----------------|-----------------|---------------|--------|
| Flatbed Scanner (Consumer) | 5000 | TBD | TBD |
| Mobile Camera (Good Lighting) | 5000 | TBD | TBD |
| Born-digital PDF | 10000 | TBD | TBD |
| ... | ... | ... | ... |

**How to Measure**:
```python
for capture_method in capture_methods:
    count = count_samples(training_data, capture_method=capture_method)

    if count >= THRESHOLD[capture_method]:
        print(f"{capture_method}: SUFFICIENT ({count} samples)")
    else:
        print(f"{capture_method}: INSUFFICIENT ({count}/{THRESHOLD[capture_method]} samples)")
```

**Sufficiency Threshold**: Each capture method meets minimum sample requirement.

---

#### Metric 6: Validation Performance Plateau

**Ultimate Sufficiency Test**: Adding more data doesn't improve validation accuracy.

**How to Measure**:
```python
# Train models with increasing data fractions: 20%, 40%, 60%, 80%, 100%
data_fractions = [0.2, 0.4, 0.6, 0.8, 1.0]
validation_accuracies = []

for fraction in data_fractions:
    subset = sample_training_data(fraction)
    model = train_model(subset)
    val_acc = evaluate(model, validation_set)
    validation_accuracies.append(val_acc)

# Check for plateau (improvement < 1% from 80% → 100%)
improvement = validation_accuracies[-1] - validation_accuracies[-2]

if improvement < 0.01:  # Less than 1% improvement
    print("Validation performance plateau reached: SUFFICIENT")
else:
    print(f"Still improving ({improvement:.2%}) - consider collecting more data")
```

**Sufficiency Threshold**: Validation accuracy improvement < 1% when adding 20% more data.

---

## Part 3: Training Data Requirements by ML Task

### 3.1 Image Quality Assessment (IQA) - Multi-label Classification

**Model Architecture**: EfficientNet-B0 or MobileNetV3 (lightweight, fast inference)

**Training Data Requirements**:

| Requirement | Specification | Rationale |
|-------------|--------------|-----------|
| **Total Samples** | 50,000 samples | Typical for multi-label classification with 10-15 defect classes |
| **Per-Defect Minimum** | 1,000 samples per defect type | Balanced representation across defect types |
| **Severity Distribution** | Match target distribution (70% clean, 20% slight, 8% moderate, 2% severe for blur) | Real-world skew toward clean documents |
| **Co-occurrence Coverage** | All pairwise combinations ≥100 samples | Realistic multi-defect scenarios |
| **Capture Method Diversity** | ≥5 capture methods, each ≥5,000 samples | Generalization across scanner/camera types |
| **File Formats** | 70% PDF, 20% JPG/PNG, 10% TIFF | Match real-world format distribution |
| **Ground Truth Quality** | Automated weak supervision (classical algorithms) + 10% manual verification | Cost-effective while maintaining quality |

**Defect Types to Cover** (from FRs):
1. Blur (FR-3.1)
2. Skew (FR-3.2)
3. Noise (FR-3.3)
4. Low DPI (FR-3.4)
5. Low Contrast (FR-3.7)
6. Poor Binarization (FR-3.8)
7. Illumination Non-uniformity (FR-3.9)
8. Bleed-through (FR-3.10)
9. Warping/Curvature (FR-3.11)
10. Perspective Distortion (FR-3.12)

**Sufficiency Metrics**:
- ✅ Per-defect minimum: All defects ≥1,000 samples
- ✅ Severity distribution: KL divergence < 0.1 for all defects
- ✅ Co-occurrence: All pairs ≥100 samples
- ✅ Capture method: All 5 methods ≥5,000 samples
- ✅ Validation plateau: <1% improvement when adding 20% more data

---

### 3.2 Layout Detection - Object Detection (YOLOv8)

**Model Architecture**: YOLOv8m (medium size, balance speed/accuracy)

**Training Data Requirements**:

| Requirement | Specification | Rationale |
|-------------|--------------|-----------|
| **Total Samples** | 40,000 pages | Typical for 11-class object detection |
| **Per-Class Minimum** | 1,000 samples per layout class | Balanced YOLOv8 training |
| **Element Size Distribution** | Power-law (many small, few large) | Realistic element size distribution |
| **Element Density** | Normal distribution (mean: 5-7 elements/page) | Realistic page complexity |
| **Bounding Box Quality** | 100% manual annotation (COCO format) | High-quality ground truth essential for object detection |
| **File Formats** | 90% PDF, 10% images | PDFs are primary input format |
| **Layout Complexity** | 60% simple (1-3 elements), 30% moderate (4-7), 10% complex (8+) | Graduated complexity |

**Layout Classes to Cover** (from FR-4.2):
1. Text
2. Title
3. List-Item
4. Table
5. Picture
6. Caption
7. Formula
8. Footnote
9. Page-Header
10. Page-Footer
11. Section-Header

**Sufficiency Metrics**:
- ✅ Per-class minimum: All 11 classes ≥1,000 samples
- ✅ Element size distribution: KL divergence < 0.1 vs target power-law
- ✅ Element density distribution: KL divergence < 0.1 vs target normal
- ✅ Validation plateau: mAP@.50 improvement <1% when adding 20% more data

---

### 3.3 Text Detection Gate - Binary Classification

**Model Architecture**: Lightweight CNN or ensemble of heuristics

**Training Data Requirements**:

| Requirement | Specification | Rationale |
|-------------|--------------|-----------|
| **Total Samples** | 10,000 samples | Binary classification (simpler than multi-class) |
| **Class Balance** | 50% no-text, 50% text | Balanced binary classifier |
| **Text Density Range** | Uniform across 0-100% bins | Cover full text density spectrum |
| **File Formats** | 50% PDF, 40% JPG/PNG, 10% TIFF | Diverse format coverage for text detection |
| **Ground Truth Quality** | Automated with spot-checks (text presence is easy to verify) | Cost-effective |

**Text Density Bins**:
- 0-10%: Pure images, minimal text
- 10-30%: Low text (diagrams with labels)
- 30-60%: Moderate text (mixed content)
- 60-100%: High text (text-heavy documents)

**Sufficiency Metrics**:
- ✅ Class balance: 5,000 no-text, 5,000 text samples
- ✅ Text density: Uniform across bins (±10% variance)
- ✅ Validation plateau: <1% accuracy improvement when adding 20% more data

---

### 3.4 Specialized Content Detection

**Model Architectures**: Varies by detector (CNN classifiers, YOLO for stamps/signatures)

**Training Data Requirements**:

| Detector | Total Samples | Per-Class Minimum | Ground Truth Quality | Rationale |
|----------|---------------|-------------------|---------------------|-----------|
| **Handwriting (FR-4.8, FR-5.2)** | 15,000 | 5,000 printed, 5,000 handwritten, 5,000 mixed | Manual verification | Mixed documents are critical |
| **Signatures (FR-5.6)** | 8,000 | 6,000 no-signature, 2,000 signature | Manual verification | Imbalanced (most docs don't have signatures) |
| **Stamps/Seals (FR-5.5)** | 6,000 | 5,000 no-stamp, 1,000 stamp | Manual verification | Rare but important (legal docs) |
| **Formulas (FR-5.1)** | 10,000 | 7,000 no-formula, 3,000 formula | Automated (LaTeX source) | Academic docs heavily represented |
| **Watermarks (FR-5.4)** | 5,000 | 4,000 no-watermark, 1,000 watermark | Automated (synthetic overlays) | Rare in training data |

**Sufficiency Metrics**:
- ✅ Per-detector minimum samples met
- ✅ Class balance matches real-world distribution (not forced 50/50)
- ✅ Validation plateau: <1% F1-score improvement when adding 20% more data

---

## Part 4: Data Collection Strategy

### 4.1 Three-Tier Collection Approach

**Tier 1: Synthetic Data Generation** (Fast, Scalable, Low Cost)
- **Use Case**: IQA defect augmentation, text density variations
- **Methodology**: Albumentations pipeline on clean base documents
- **Volume**: 50,000 samples
- **Cost**: ~$0 (compute only)
- **Limitations**: Synthetic artifacts, limited realism

**Tier 2: Public Dataset Curation** (Moderate Cost, High Quality)
- **Use Case**: Layout detection, academic/research documents
- **Methodology**: Download, clean, annotate public datasets (DocLayNet, PubTables-1M, etc.)
- **Volume**: 40,000 samples
- **Cost**: ~$0 (download only)
- **Limitations**: Limited domain diversity (heavy on academic docs)

**Tier 3: Domain-Specific Acquisition** (High Cost, Critical Coverage)
- **Use Case**: Legal contracts, financial docs, government forms, historical archives
- **Methodology**: Purchase datasets, partner with enterprises, manual collection
- **Volume**: 15,000 samples
- **Cost**: ~$5,000-$10,000 (dataset purchases, annotation labor)
- **Justification**: Required for high-risk semantic contexts (Legal, Financial)

---

### 4.2 Data Collection Roadmap

**Phase 1: Foundation** (Current - 50k IQA samples collected)
- ✅ Synthetic IQA generation (TableBank + Albumentations)
- ✅ DocLayNet layout detection (42k pages)
- ✅ TableBank table detection (417k tables)

**Phase 2: Domain Expansion** (Weeks 3-8)
- 🔲 Acquire Legal contract corpus (5,000 samples, manual annotation, ~$2,000)
- 🔲 Acquire Financial document corpus (5,000 samples, manual annotation, ~$2,000)
- 🔲 Acquire Government forms dataset (3,000 samples, manual annotation, ~$1,000)
- 🔲 Acquire Historical archive scans (2,000 samples, semi-automated, ~$500)

**Phase 3: Edge Case Completion** (Weeks 9-12)
- 🔲 Mobile capture dataset (varied lighting, 5,000 samples, semi-automated)
- 🔲 Photocopier degradation corpus (2,000 samples, automated augmentation)
- 🔲 Multi-lingual document expansion (3,000 samples, automated)

**Phase 4: Validation & Refinement** (Weeks 13-16)
- 🔲 Measure all sufficiency metrics
- 🔲 Identify gaps and collect targeted samples
- 🔲 Validate model performance plateau
- 🔲 Final dataset freeze

---

## Part 5: Sufficiency Dashboard

**Continuous Monitoring**: Track all sufficiency metrics in real-time as data is collected.

### 5.1 IQA Training Data Sufficiency

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Total Samples** | 50,000 | 50,000 | ✅ SUFFICIENT |
| **Blur Samples** | ≥1,000 | 10,000 | ✅ SUFFICIENT |
| **Skew Samples** | ≥1,000 | 10,000 | ✅ SUFFICIENT |
| **Noise Samples** | ≥1,000 | 5,000 | ✅ SUFFICIENT |
| **Contrast Samples** | ≥1,000 | 5,000 | ✅ SUFFICIENT |
| **Blur Severity Distribution (KL)** | <0.1 | TBD | ⏳ PENDING |
| **Skew Severity Distribution (KL)** | <0.1 | TBD | ⏳ PENDING |
| **Co-occurrence Coverage** | All pairs ≥100 | TBD | ⏳ PENDING |
| **Capture Method Diversity** | 5 methods, ≥5k each | TBD | ⏳ PENDING |
| **Validation Plateau** | <1% improvement | TBD | ⏳ PENDING |

### 5.2 Layout Detection Sufficiency

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Total Samples** | 40,000 pages | 42,075 | ✅ SUFFICIENT |
| **Text Class** | ≥1,000 | TBD | ⏳ PENDING |
| **Title Class** | ≥1,000 | TBD | ⏳ PENDING |
| **Table Class** | ≥1,000 | TBD | ⏳ PENDING |
| **Figure Class** | ≥1,000 | TBD | ⏳ PENDING |
| **Element Size Distribution (KL)** | <0.1 | TBD | ⏳ PENDING |
| **Element Density Distribution (KL)** | <0.1 | TBD | ⏳ PENDING |
| **Validation Plateau (mAP@.50)** | <1% improvement | TBD | ⏳ PENDING |

### 5.3 Semantic Context Coverage

| Semantic Context | Required Samples | Current Count | Ground Truth Quality | Status |
|------------------|------------------|---------------|---------------------|--------|
| **Legal** | 10,000 | ~500 (DocLayNet subset) | 100% manual | ❌ CRITICAL GAP |
| **Financial** | 10,000 | ~3,000 (receipts + FinTabNet) | 50% manual | ⚠️ INSUFFICIENT |
| **Business Operations** | 15,000 | ~5,000 (DocLayNet subset) | 10% manual | ⚠️ INSUFFICIENT |
| **Academic** | 20,000 | ~42,000 (DocLayNet) | 5% manual | ✅ SUFFICIENT |

---

## Part 6: Implementation Checklist

### 6.1 Immediate Actions (Week 1-2)

- [ ] **Define target distributions** for all defect severities (from real-world corpus analysis)
- [ ] **Implement sufficiency metrics** (KL divergence, co-occurrence matrix, validation plateau)
- [ ] **Measure current dataset** against all sufficiency metrics
- [ ] **Generate sufficiency dashboard** showing current status

### 6.2 Data Collection Priorities (Week 3-8)

**Priority 1 (Critical Gaps)**:
- [ ] Acquire Legal contract corpus (10,000 samples, ~$2,000)
- [ ] Acquire Financial document corpus (10,000 samples, ~$2,000)
- [ ] Measure co-occurrence coverage and fill gaps

**Priority 2 (Important Gaps)**:
- [ ] Acquire Business document corpus (15,000 samples, ~$3,000)
- [ ] Acquire Government forms dataset (3,000 samples, ~$1,000)
- [ ] Measure capture method diversity and fill gaps

**Priority 3 (Nice-to-Have)**:
- [ ] Expand multi-lingual coverage
- [ ] Acquire historical archive scans
- [ ] Add mobile capture edge cases

### 6.3 Validation & Refinement (Week 9-12)

- [ ] Train models with current dataset
- [ ] Measure validation performance plateau
- [ ] Identify under-performing subgroups
- [ ] Collect targeted samples to address gaps
- [ ] Re-train and validate until plateau reached

---

## Conclusion

**Key Takeaways**:

1. **Attribute-based coverage** > Document type categories
2. **Statistical sufficiency metrics** > Arbitrary sample counts
3. **Co-occurrence patterns** > Single-defect synthetic data
4. **Validation plateau** is the ultimate sufficiency test
5. **Semantic context** determines ground truth quality requirements

**Next Steps**:
1. Define target distributions for all attributes (from real-world analysis)
2. Implement sufficiency metrics and dashboard
3. Measure current dataset against metrics
4. Prioritize data collection to fill critical gaps (Legal, Financial, Business)
5. Iterate until all sufficiency metrics are met and validation plateaus

---

**Created**: 2025-11-14
**Status**: ✅ Complete - Training dataset requirements defined from first principles
**Next Review**: After implementing sufficiency metrics and measuring current dataset
