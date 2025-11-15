# Training Dataset Concept Document

**Version**: 2.0
**Date**: 2025-11-14 (Updated after comprehensive FR review)
**Purpose**: Define training data requirements derived from functional requirements to meet all ML model objectives

---

## Executive Summary

**Project Goal**: Build ML models that detect preprocessing issues and content types in documents for RAG system optimization.

**Core ML Tasks** (Derived from FRs):
1. **Learned Quality Assessment (FR-2.3)**: 3-dimension regression (Overall Quality, Sharpness, Color Fidelity)
2. **Layout Detection (FR-4.1-4.3)**: 11-class object detection with bounding boxes
3. **Document Quality Score (FR-7.1)**: 2-axis scoring (Degradation + Structural Complexity)
4. **Specialized Detectors (FR-4.4-4.8, FR-5.x)**: Parasitic content, footnotes, figures, handwriting, signatures, stamps, formulas, watermarks, annotations

**Key Principle**: Training data requirements must be derived from **what the FR specifications require**, ensuring all 48 functional requirements are satisfied.

---

## Part 1: Fundamental Data Attributes Framework (Aligned with FRs)

### 1.1 Core Principle: FR-Driven Attribute Coverage

**Every training sample must support one or more FR specifications**. Attributes are organized by the FR they satisfy.

---

### 1.2 Seven Attribute Dimensions (Mapped to FRs)

#### Dimension 1: Learned Quality Attributes (FR-2.3 - 3-Dimension Output)

**FR-2.3 Requirement**: Predict document quality scores across three dimensions using ML model.

| Quality Dimension | Value Range | Distribution Requirement | Training Data Source |
|-------------------|-------------|-------------------------|---------------------|
| **Overall Quality** | 0.0 (poor) → 1.0 (pristine) | Normal distribution (μ=0.7, σ=0.15) - most docs are decent quality | DIQA-5000 ground truth (Phase 3+), BRISQUE/NIQE weak labels (Phase 2) |
| **Sharpness** | 0.0 (blurry) → 1.0 (sharp) | Right-skewed (70% sharp, 20% slight blur, 10% severe) | DIQA-5000 sharpness scores (Phase 3+), Laplacian variance labels (Phase 2) |
| **Color Fidelity** | 0.0 (poor contrast/color) → 1.0 (excellent) | Right-skewed (60% good, 30% moderate, 10% poor) | DIQA-5000 color scores (Phase 3+), histogram analysis labels (Phase 2) |

**Training Data Requirements** (from FR-2.3):
- **Phase 2**: 50,000 synthetic samples (TableBank + Albumentations) with **weak supervision** (BRISQUE/NIQE for Overall, Laplacian for Sharpness, histogram for Color)
- **Phase 3**: DIQA-5000 (5,000 document images with expert-annotated 3-dimension ground truth)
- **Validation**: LIVE/CSIQ/LIVE Challenge (fallback until DIQA-5000 releases Sept 2025)

**Model Architecture**: MobileNetV3-Small or EfficientNet-B0 (multi-output regression)

**Performance Target**: Pearson correlation > 0.80 with DIQA-5000 ground truth

**Sufficiency Metric**:
```python
# For each dimension (Overall, Sharpness, Color Fidelity)
correlation = pearson_correlation(predicted_scores, ground_truth_scores)
if correlation > 0.80:
    print(f"{dimension}: SUFFICIENT (r={correlation:.3f})")
```

---

#### Dimension 2: Document Quality Score Attributes (FR-7.1 - 2-Axis DQS)

**FR-7.1 Requirement**: Calculate Document Quality Score (DQS) with two orthogonal axes for intelligent routing.

**Axis 1: Degradation Score** (0.0 = severe degradation → 1.0 = pristine)

| Degradation Component | Contribution to Score | Measurement Method | Training Data Need |
|-----------------------|----------------------|--------------------|--------------------|
| **Blur** | 25% weight | Laplacian variance (FR-3.1) | Blur severity 0-100% across training set |
| **Noise** | 20% weight | SNR estimation (FR-3.3) | Noise levels (clean → heavy noise) |
| **Contrast** | 20% weight | Histogram analysis (FR-3.7) | Contrast range (low → high) |
| **Skew** | 15% weight | Hough transform (FR-3.2) | Skew angles -15° → +15° |
| **Resolution (DPI)** | 20% weight | DPI detection (FR-3.5) | DPI range 72 → 1200 |

**Distribution Requirement**:
- Degradation Score bins: [0.0-0.2] 10%, [0.2-0.4] 15%, [0.4-0.6] 20%, [0.6-0.8] 30%, [0.8-1.0] 25%
- Realistic distribution: Most documents moderate-to-good quality (60-80% in 0.6-1.0 range)

**Axis 2: Structural Complexity Score** (0.0 = simple → 1.0 = highly complex)

| Complexity Component | Contribution to Score | Measurement Method | Training Data Need |
|----------------------|----------------------|--------------------|--------------------|
| **Multi-column** | 25% weight | Column detection (FR-4.12) | 1-column (70%), 2-column (25%), 3-column (5%) |
| **Tables** | 25% weight | Table count per page | 0 tables (50%), 1-2 tables (35%), 3+ tables (15%) |
| **Formulas** | 15% weight | Formula detection (FR-5.1) | 0 formulas (70%), 1-5 formulas (20%), 6+ formulas (10%) |
| **Figures** | 20% weight | Figure count per page | 0 figures (40%), 1-2 figures (40%), 3+ figures (20%) |
| **Mixed Scripts** | 15% weight | Language detection (FR-5.3) | Monolingual (85%), Mixed scripts (15%) |

**Distribution Requirement**:
- Structural Complexity bins: [0.0-0.2] 30%, [0.2-0.4] 25%, [0.4-0.6] 20%, [0.6-0.8] 15%, [0.8-1.0] 10%
- Realistic distribution: Most documents simple-to-moderate complexity

**Training Data Requirements**:
- 50,000 documents with **both axes labeled**
- Each document characterized by:
  - All 5 degradation components (blur, noise, contrast, skew, DPI)
  - All 5 structural components (columns, tables, formulas, figures, scripts)
- Composite DQS = f(Degradation Score, Structural Complexity Score)

**Routing Matrix Coverage** (FR-7.2):

| Degradation → Complexity ↓ | LOW (0.0-0.4) | MEDIUM (0.4-0.7) | HIGH (0.7-1.0) |
|---------------------------|---------------|------------------|----------------|
| **LOW Structural (0.0-0.4)** | 5,000 samples | 7,500 samples | 7,500 samples |
| **MEDIUM Structural (0.4-0.7)** | 7,500 samples | 10,000 samples | 7,500 samples |
| **HIGH Structural (0.7-1.0)** | 5,000 samples | 5,000 samples | 2,500 samples |

**Total**: 50,000 samples covering all cells of routing matrix

**Sufficiency Metric**:
```python
# Build 2D histogram of (Degradation Score, Structural Complexity Score)
routing_matrix = np.histogram2d(degradation_scores, complexity_scores, bins=3)

# Check each cell has minimum samples
min_cell_count = np.min(routing_matrix)
if min_cell_count >= 2500:  # Minimum for smallest cell
    print("DQS coverage: SUFFICIENT")
else:
    print(f"DQS coverage: INSUFFICIENT - minimum cell has {min_cell_count} samples")
```

---

#### Dimension 3: Layout Element Attributes (FR-4.2 - 11 DocLayNet Classes)

**FR-4.2 Requirement**: Detect all 11 layout element classes with COCO-format bounding boxes.

**11 Layout Classes** (from DocLayNet):

| Class | Per-Class Minimum | Element Size Distribution | Rationale |
|-------|-------------------|--------------------------|-----------|
| **1. Text** | 5,000 samples | Power-law (many small paragraphs, few large blocks) | Most common element |
| **2. Title** | 2,000 samples | Mostly small-medium (5-15% page area) | Document/section titles |
| **3. List-Item** | 3,000 samples | Small (1-3% page area per item) | Bulleted/numbered lists |
| **4. Table** | 3,000 samples | Medium-large (10-40% page area) | Structured data |
| **5. Picture** | 2,500 samples | Medium-large (10-50% page area) | Figures, charts, diagrams |
| **6. Caption** | 2,000 samples | Small (1-3% page area) | Figure/table captions |
| **7. Formula** | 1,500 samples | Small-medium (1-10% page area) | Math equations |
| **8. Footnote** | 1,500 samples | Small (1-5% page area) | Page footnotes |
| **9. Page-Header** | 2,000 samples | Small (1-3% page area) | Repeating headers |
| **10. Page-Footer** | 2,000 samples | Small (1-3% page area) | Repeating footers |
| **11. Section-Header** | 2,000 samples | Small-medium (2-8% page area) | Section titles |

**Total Layout Training Data**: 40,000 pages (DocLayNet provides 42,075 pages)

**Element Co-occurrence Patterns**:
- Title + Text + List-Item (common document structure)
- Title + Text + Table + Caption (academic papers)
- Text + Figure + Caption (reports)
- Text + Formula (scientific documents)
- Page-Header + Page-Footer + Text (formatted documents)

**Training Data Requirements**:
- **Bounding Box Quality**: 100% manual annotation (COCO format `[x, y, width, height]`)
- **Element Size Distribution**: Must match target power-law distribution for each class
- **Element Density**: Normal distribution (mean: 5-7 elements per page)
- **Class Balance**: Each class ≥1,500 samples (class imbalance allowed - reflects real-world)

**Sufficiency Metric**:
```python
# For each of 11 classes
for class_id in range(1, 12):
    count = count_samples(training_data, class_id=class_id)
    if count >= MIN_SAMPLES[class_id]:
        print(f"Class {class_id}: SUFFICIENT ({count} samples)")
    else:
        print(f"Class {class_id}: INSUFFICIENT ({count}/{MIN_SAMPLES[class_id]} samples)")

# YOLOv8 mAP@.50 validation
if mAP_at_50 > 0.82:
    print("Layout detection: SUFFICIENT (mAP={mAP_at_50:.3f})")
```

---

#### Dimension 4: Structural Relationship Attributes (FR-4.4-4.7, 4.12)

**These FRs require spatial/structural relationships, not just element detection:**

##### FR-4.4: Parasitic Content Detection

**Requirement**: Detect headers, footers, page numbers that should be removed from content.

**Training Data Needs**:

| Parasitic Type | Training Samples | Annotation Type | Characteristics |
|----------------|------------------|-----------------|-----------------|
| **Page-Header** (repeating) | 5,000 pages | Bounding box + "parasitic" label | Same header across multiple pages |
| **Page-Footer** (repeating) | 5,000 pages | Bounding box + "parasitic" label | Same footer across multiple pages |
| **Page Numbers** | 5,000 pages | Bounding box + "parasitic" label | Sequential numbering pattern |
| **Watermarks** (non-parasitic) | 1,000 pages | Bounding box + "keep" label | Document watermarks to preserve |

**Sufficiency Metric**: Model correctly identifies 90%+ repeating headers/footers across multi-page documents.

##### FR-4.5: Footnote Linking

**Requirement**: Link footnote markers in text to corresponding footnotes.

**Training Data Needs**:

| Relationship Type | Training Samples | Annotation Type | Example |
|-------------------|------------------|-----------------|---------|
| **Footnote marker → Footnote** | 3,000 pages | Marker bbox + Footnote bbox + Link ID | "See footnote 1" → "1. Citation text" |
| **Superscript detection** | 3,000 samples | Character-level bbox | "text¹" with superscript annotated |

**Annotation Format**: JSON with `{"marker_id": 1, "marker_bbox": [x, y, w, h], "footnote_bbox": [x, y, w, h], "link_confidence": 0.95}`

**Sufficiency Metric**: 85%+ accuracy on footnote-marker matching in held-out test set.

##### FR-4.6: Figure-Caption Linking

**Requirement**: Link figures to their captions based on spatial proximity and references.

**Training Data Needs**:

| Relationship Type | Training Samples | Spatial Pattern | Example |
|-------------------|------------------|-----------------|---------|
| **Figure above, Caption below** | 5,000 pairs | Caption within 50px below figure | Standard academic format |
| **Figure below, Caption above** | 1,000 pairs | Caption within 50px above figure | Less common |
| **Figure left, Caption right** | 500 pairs | Caption adjacent to figure | Technical diagrams |
| **Caption reference** ("Figure 1") | 3,000 pairs | Text reference + figure number | "See Figure 1" → Figure bbox |

**Annotation Format**: JSON with `{"figure_id": 1, "figure_bbox": [x, y, w, h], "caption_bbox": [x, y, w, h], "spatial_relationship": "below", "distance_px": 12}`

**Sufficiency Metric**: 90%+ accuracy on figure-caption pairing in held-out test set.

##### FR-4.7: Vertical Text Orientation Detection

**Requirement**: Detect text at 0°/90°/180°/270° rotations.

**Training Data Needs**:

| Orientation | Training Samples | Use Cases |
|-------------|------------------|-----------|
| **0° (normal)** | 40,000 samples | Standard horizontal text |
| **90° (rotated right)** | 2,000 samples | Vertical text in diagrams, Asian languages |
| **180° (upside down)** | 500 samples | Scanning errors, misaligned pages |
| **270° (rotated left)** | 2,000 samples | Vertical text, Asian languages |

**Annotation Format**: Bounding box + `orientation` field (0, 90, 180, 270 degrees)

**Sufficiency Metric**: 95%+ accuracy on 4-class orientation classification.

##### FR-4.12: Reading Order Prediction

**Requirement**: Predict correct reading order for multi-column, complex layouts.

**Training Data Needs**:

| Layout Complexity | Training Samples | Annotation Type | Reading Order Pattern |
|-------------------|------------------|-----------------|----------------------|
| **Single column** | 20,000 pages | Element IDs with reading order | Top → bottom (simple) |
| **Two column** | 15,000 pages | Element IDs with reading order | Top-left → top-right → bottom-left → bottom-right |
| **Three column** | 3,000 pages | Element IDs with reading order | Left-to-right columns, top-to-bottom |
| **Mixed/Complex** | 2,000 pages | Element IDs with reading order | Sidebars, insets, wrap-around |

**Annotation Format**: JSON with `{"element_id": 1, "element_bbox": [x, y, w, h], "reading_order": 3}` for each element, ordered by reading sequence.

**Sufficiency Metric**: 85%+ accuracy on predicted reading order vs ground truth (Kendall's tau correlation).

---

#### Dimension 5: Specialized Content Attributes (FR-5.x)

##### FR-5.1: Mathematical Content

| Formula Type | Training Samples | Annotation Type | Example |
|--------------|------------------|-----------------|---------|
| **Inline formulas** | 5,000 samples | Bounding box + "inline" label | $E = mc^2$ within text |
| **Display formulas** | 5,000 samples | Bounding box + "display" label | Centered equations |
| **Multi-line formulas** | 2,000 samples | Bounding box + "multi-line" label | Systems of equations |

##### FR-5.2: Handwritten Content

| Handwriting Type | Training Samples | Annotation Type | Mixed vs Pure |
|------------------|------------------|-----------------|---------------|
| **Signatures** | 6,000 samples | Bounding box + "signature" label | Mixed (printed + signature) |
| **Margin annotations** | 3,000 samples | Bounding box + "annotation" label | Mixed (printed + handwritten notes) |
| **Handwritten notes** | 6,000 samples | Bounding box + "handwriting" label | Pure handwritten pages |

##### FR-5.3: Language Detection

**Training Data**: WiLI-2018 (235,000 paragraphs, 235 languages) - SUFFICIENT

##### FR-5.4: Watermark Detection

| Watermark Type | Training Samples | Annotation Type |
|----------------|------------------|-----------------|
| **Text watermarks** | 2,000 samples | Bounding box + transparency | "CONFIDENTIAL", "DRAFT" |
| **Logo watermarks** | 1,500 samples | Bounding box + transparency | Company logos |
| **Pattern watermarks** | 1,000 samples | Bounding box + transparency | Security patterns |

##### FR-5.5: Stamp/Seal Detection

| Stamp Type | Training Samples | Annotation Type |
|------------|------------------|-----------------|
| **Circular seals** | 2,000 samples | Bounding box + "circular" label | Official seals, notary stamps |
| **Rectangular stamps** | 1,500 samples | Bounding box + "rectangular" label | Date stamps, approval stamps |
| **Hole punches** | 500 samples | Bounding box + "hole_punch" label | Binder holes (should remove) |

##### FR-5.6: Signature Detection

**Training Data**: SignaTR6K (6,000 signatures) - SUFFICIENT

##### FR-5.7: Margin Annotation Detection

| Annotation Type | Training Samples | Annotation Type |
|-----------------|------------------|-----------------|
| **Margin notes** | 2,000 samples | Bounding box + "note" label | Handwritten comments |
| **Highlights** | 1,000 samples | Bounding box + "highlight" label | Yellow marker overlays |
| **Strikethroughs** | 500 samples | Bounding box + "strikethrough" label | Crossed-out text |

---

#### Dimension 6: Defect/Feature Attributes (FR-3.x - Classical IQA)

**For Classical IQA detectors (FR-3.1 through FR-3.14):**

| Defect | Value Range | Distribution Requirement | FR Reference |
|--------|-------------|-------------------------|--------------|
| **Blur Severity** | 0% (sharp) → 100% (severe blur) | 70% clean, 20% slight, 8% moderate, 2% severe | FR-3.1 |
| **Skew Angle** | -15° → +15° | 60% perfect (0-1°), 30% slight (1-3°), 8% moderate (3-7°), 2% severe (7-15°) | FR-3.2 |
| **Noise Level** | 0 (clean) → 1.0 (heavy) | 80% clean, 15% slight, 4% moderate, 1% severe | FR-3.3 |
| **DPI** | 72 → 1200 | Bimodal: 72-150 (mobile), 300 (standard), 600+ (professional) | FR-3.4, FR-3.5 |
| **Contrast** | 0.0 (low) → 1.0 (high) | Normal distribution (μ=0.7, σ=0.15) | FR-3.7 |
| **Binarization Quality** | 0 (poor) → 1.0 (excellent) | 75% good, 20% moderate, 5% poor | FR-3.9 (Phase 2) |
| **Illumination Uniformity** | 0 (uneven) → 1.0 (uniform) | 70% uniform, 25% slight gradient, 5% severe | FR-3.10 (Phase 2) |
| **Bleed-Through** | 0 (none) → 1.0 (severe) | 90% none, 8% slight, 2% moderate-severe | FR-3.11 (Phase 3) |
| **Warping/Curvature** | 0 (flat) → 1.0 (severe curve) | 80% flat, 15% slight, 5% moderate-severe | FR-3.12 (Phase 3) |
| **Perspective Distortion** | 0° (frontal) → 45° (severe angle) | 85% frontal, 12% slight, 3% severe | FR-3.13 (Phase 2) |

**Co-occurrence Coverage** (FR-3.14 - Hybrid IQA on Embedded Images):
- **Requirement**: After layout detection identifies embedded images (FR-4.2: Picture class), run IQA on each extracted element
- **Training Data Need**: Pages with embedded images that have varying quality levels
  - Example: Academic paper with high-quality diagram (sharp, good contrast) + low-quality scanned photo (blurry, low resolution)
- **Annotation**: Each Picture element needs IQA labels (blur, noise, contrast scores)

**Sufficiency Metric**:
```python
# All pairwise defect combinations ≥100 samples
cooccurrence_matrix = build_cooccurrence_matrix(training_data)
min_cooccurrence = np.min(cooccurrence_matrix[np.triu_indices(num_defects, k=1)])

if min_cooccurrence >= 100:
    print("Defect co-occurrence: SUFFICIENT")
```

---

#### Dimension 7: Capture Method Variability (Systematic Defect Patterns)

**Each capture method has characteristic defect signatures:**

| Capture Method | Characteristic Defects | Required Samples | Defect Signature |
|----------------|----------------------|------------------|------------------|
| **Flatbed Scanner (Consumer)** | Skew (±2-5°), Low DPI (150-300), Edge shadows | 5,000 samples | Systematic skew + edge artifacts |
| **Flatbed Scanner (Professional)** | High DPI (600+), Minimal defects | 2,000 samples | Clean scans, color accuracy |
| **Sheet-fed Scanner** | Alignment issues, Streaks | 3,000 samples | Vertical streak artifacts |
| **Mobile Camera (Good Lighting)** | Perspective (5-15°), Slight blur, Uneven illumination | 5,000 samples | Geometric distortion dominant |
| **Mobile Camera (Poor Lighting)** | Heavy blur, Low contrast, Noise, Illumination gradient | 3,000 samples | Quality degradation dominant |
| **Photocopier (1st gen)** | Slight noise, Contrast loss (~10%) | 2,000 samples | Subtle degradation |
| **Photocopier (2nd+ gen)** | Heavy noise, Significant contrast loss (~30%) | 1,000 samples | Severe multi-generational loss |
| **Born-digital PDF** | Minimal defects, High DPI, Clean rendering | 10,000 samples | Reference quality |

**Sufficiency Metric**:
```python
for capture_method in capture_methods:
    count = count_samples(training_data, capture_method=capture_method)
    if count >= THRESHOLD[capture_method]:
        print(f"{capture_method}: SUFFICIENT ({count} samples)")
```

---

## Part 2: Statistical Sufficiency Criteria (Updated with FR Targets)

### 2.1 Sufficiency Metrics by FR

#### FR-2.3: Learned Quality Assessment

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Total Samples** | 50,000 | Count training samples |
| **3-Dimension Coverage** | All three scores (Overall, Sharpness, Color) labeled | Check annotation completeness |
| **Score Distribution (KL)** | < 0.1 vs target distribution for each dimension | KL divergence calculation |
| **Pearson Correlation (Validation)** | > 0.80 on DIQA-5000 | Train-validate-test split |
| **Model Calibration (ECE)** | < 0.1 | Expected Calibration Error |

#### FR-4.2: Layout Element Detection (11 Classes)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Total Pages** | 40,000 | Count annotated pages |
| **Per-Class Minimum** | ≥1,500 samples per class | Count samples per class |
| **Bounding Box Quality** | 100% manual annotation (COCO format) | Annotation verification |
| **Element Size Distribution (KL)** | < 0.1 vs target power-law for each class | KL divergence calculation |
| **YOLOv8 mAP@.50** | > 0.82 on validation set | COCO evaluation metrics |

#### FR-7.1: Document Quality Score (DQS)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Routing Matrix Coverage** | All 9 cells ≥2,500 samples | 2D histogram of (Degradation, Complexity) |
| **Degradation Score Distribution (KL)** | < 0.1 vs target | KL divergence calculation |
| **Structural Complexity Distribution (KL)** | < 0.1 vs target | KL divergence calculation |
| **Routing Accuracy** | > 90% correct quadrant assignment | Validation set evaluation |

#### FR-4.4-4.7, 4.12: Structural Relationships

| FR | Metric | Target | Measurement Method |
|----|--------|--------|-------------------|
| **FR-4.4** (Parasitic Content) | Repeating header/footer detection accuracy | > 90% | Multi-page document validation |
| **FR-4.5** (Footnote Linking) | Marker-footnote matching accuracy | > 85% | Held-out test set evaluation |
| **FR-4.6** (Figure-Caption Linking) | Figure-caption pairing accuracy | > 90% | Held-out test set evaluation |
| **FR-4.7** (Vertical Text) | 4-class orientation accuracy | > 95% | Classification accuracy |
| **FR-4.12** (Reading Order) | Kendall's tau correlation | > 0.85 | Reading order sequence correlation |

### 2.2 Validation Performance Plateau (Ultimate Sufficiency Test)

**For each FR with ML model:**

```python
# Train with increasing data fractions: 20%, 40%, 60%, 80%, 100%
for fraction in [0.2, 0.4, 0.6, 0.8, 1.0]:
    subset = sample_training_data(fraction)
    model = train_model(subset)
    val_metric = evaluate(model, validation_set)  # Metric depends on FR

    # FR-2.3: Pearson correlation
    # FR-4.2: mAP@.50
    # FR-7.1: Routing accuracy
    # etc.

# Check for plateau
improvement = val_metric[-1] - val_metric[-2]
if improvement < 0.01:  # <1% improvement from 80% → 100%
    print(f"{FR_ID}: SUFFICIENT - performance plateau reached")
```

---

## Part 3: Training Data Requirements by FR

### 3.1 FR-2.3: Learned Quality Assessment

**Training Data Requirements**:

| Component | Phase 2 (Synthetic) | Phase 3+ (Real-world) |
|-----------|--------------------|-----------------------|
| **Dataset** | TableBank + Albumentations | DIQA-5000 |
| **Samples** | 50,000 | 5,000 (augmented to 50k with synthetic) |
| **Labels** | Weak supervision (BRISQUE, NIQE, Laplacian, histogram) | Expert 3-dimension scores (Overall, Sharpness, Color) |
| **Dimensions** | 3 (Overall Quality, Sharpness, Color Fidelity) | 3 (same) |
| **Ground Truth Quality** | Automated (classical algorithms) | Manual expert annotation |
| **Cost** | ~$0 (compute only) | ~$5,000 (DIQA-5000 dataset license) |

**Sufficiency Criteria**:
- ✅ 50,000 samples with 3-dimension labels
- ✅ Score distributions match target (KL < 0.1)
- ✅ Pearson correlation > 0.80 on DIQA-5000
- ✅ Expected Calibration Error < 0.1
- ✅ Validation plateau reached

---

### 3.2 FR-4.2: Layout Element Detection (11 Classes)

**Training Data Requirements**:

| Component | Specification |
|-----------|--------------|
| **Total Pages** | 40,000 pages |
| **Per-Class Minimum** | Text: 5k, Title: 2k, List-Item: 3k, Table: 3k, Picture: 2.5k, Caption: 2k, Formula: 1.5k, Footnote: 1.5k, Page-Header: 2k, Page-Footer: 2k, Section-Header: 2k |
| **Bounding Box Format** | COCO: `[x, y, width, height]` |
| **Annotation Quality** | 100% manual annotation |
| **Element Size Distribution** | Power-law for each class |
| **Dataset** | DocLayNet (42,075 pages) + DocSynth-300K (300k synthetic) |
| **Cost** | ~$0 (public datasets) |

**Sufficiency Criteria**:
- ✅ All 11 classes ≥1,500 samples
- ✅ Element size distributions match target (KL < 0.1)
- ✅ YOLOv8 mAP@.50 > 0.82 on validation set
- ✅ Validation plateau reached

---

### 3.3 FR-7.1: Document Quality Score (DQS)

**Training Data Requirements**:

| Component | Specification |
|-----------|--------------|
| **Total Samples** | 50,000 documents |
| **Degradation Score Labels** | All 5 components (blur, noise, contrast, skew, DPI) |
| **Structural Complexity Labels** | All 5 components (columns, tables, formulas, figures, scripts) |
| **Routing Matrix Coverage** | All 9 cells (3×3 grid) ≥2,500 samples |
| **Annotation** | Automated (derived from FR-3.x detectors + FR-4.2 layout) |
| **Cost** | ~$0 (computed from existing labels) |

**Routing Matrix Coverage**:

| Degradation → Complexity ↓ | LOW (0.0-0.4) | MEDIUM (0.4-0.7) | HIGH (0.7-1.0) |
|---------------------------|---------------|------------------|----------------|
| **LOW Structural** | 5k samples | 7.5k samples | 7.5k samples |
| **MEDIUM Structural** | 7.5k samples | 10k samples | 7.5k samples |
| **HIGH Structural** | 5k samples | 5k samples | 2.5k samples |

**Sufficiency Criteria**:
- ✅ All routing matrix cells ≥2,500 samples
- ✅ Degradation/Complexity distributions match target (KL < 0.1)
- ✅ Routing accuracy > 90% on validation set
- ✅ Validation plateau reached

---

### 3.4 FR-4.4-4.7, 4.12: Structural Relationships

**Training Data Requirements**:

| FR | Training Samples | Annotation Type | Cost Estimate |
|----|------------------|-----------------|---------------|
| **FR-4.4** (Parasitic Content) | 10,000 pages | Bbox + repeating pattern flag | ~$500 (semi-automated) |
| **FR-4.5** (Footnote Linking) | 6,000 pages | Marker bbox + footnote bbox + link ID | ~$1,500 (manual annotation) |
| **FR-4.6** (Figure-Caption Linking) | 10,000 pairs | Figure bbox + caption bbox + relationship | ~$1,000 (semi-automated) |
| **FR-4.7** (Vertical Text) | 5,000 samples | Bbox + orientation (0/90/180/270°) | ~$500 (semi-automated) |
| **FR-4.12** (Reading Order) | 40,000 pages | Element IDs + reading order sequence | ~$5,000 (manual annotation) |

**Total Cost**: ~$8,500 for structural relationship annotations

**Sufficiency Criteria**:
- ✅ Each FR meets minimum sample requirement
- ✅ Validation accuracy > target for each FR
- ✅ Validation plateau reached

---

### 3.5 FR-5.x: Specialized Content Detection

**Training Data Requirements**:

| FR | Dataset | Samples | Cost |
|----|---------|---------|------|
| **FR-5.1** (Math) | DocLayNet Formula class | 10,000 formulas | ~$0 (included) |
| **FR-5.2** (Handwriting) | SignaTR6K + IAM Database | 15,000 mixed docs | ~$0 (public) |
| **FR-5.3** (Language) | WiLI-2018 | 235,000 paragraphs | ~$0 (public) |
| **FR-5.4** (Watermarks) | Synthetic overlays | 5,000 samples | ~$0 (generated) |
| **FR-5.5** (Stamps) | StaVer + DDI-100 | 6,000 samples | ~$500 (StaVer) |
| **FR-5.6** (Signatures) | SignaTR6K | 6,000 signatures | ~$0 (public) |
| **FR-5.7** (Margin Annotations) | Historical manuscripts | 3,000 samples | ~$1,000 (manual collection) |

**Total Cost**: ~$1,500 for specialized content

**Sufficiency Criteria**: Each FR meets validation accuracy target

---

## Part 4: Comprehensive Data Collection Roadmap

### 4.1 Current Status (Phase 2 - Completed)

| FR | Requirement | Current Coverage | Status |
|----|-------------|------------------|--------|
| **FR-2.3** | 50k samples with 3-dimension labels | ✅ 50k synthetic (weak supervision) | ⚠️ PARTIAL - awaiting DIQA-5000 |
| **FR-4.2** | 40k pages, 11 classes | ✅ DocLayNet 42k pages | ✅ SUFFICIENT |
| **FR-3.x** | Defect detection training | ✅ 50k synthetic variants | ✅ SUFFICIENT |
| **FR-5.3** | Language detection | ✅ WiLI-2018 (235k paragraphs) | ✅ SUFFICIENT |

### 4.2 Phase 3 Priorities (Weeks 3-8) - Critical Gaps

**Priority 1 (Critical FRs)**:

| FR | Gap | Required Dataset | Cost | Priority |
|----|-----|-----------------|------|----------|
| **FR-4.5** | Footnote linking | Annotated academic papers (6k pages) | ~$1,500 | **HIGH** |
| **FR-4.6** | Figure-caption linking | Annotated academic/technical docs (10k pairs) | ~$1,000 | **HIGH** |
| **FR-4.12** | Reading order | Annotated multi-column docs (40k pages) | ~$5,000 | **HIGH** |
| **FR-7.1** | DQS validation | Routing matrix coverage analysis | ~$0 | **MEDIUM** |

**Total Phase 3 Investment**: ~$7,500

**Priority 2 (Important but Deferrable)**:

| FR | Gap | Required Dataset | Cost | Phase |
|----|-----|-----------------|------|-------|
| **FR-4.4** | Parasitic content | Repeating header/footer corpus (10k pages) | ~$500 | Phase 3-4 |
| **FR-4.7** | Vertical text | Rotated text corpus (5k samples) | ~$500 | Phase 3 |
| **FR-5.5** | Stamps/seals | StaVer + government docs | ~$500 | Phase 3 |
| **FR-5.7** | Margin annotations | Historical manuscripts | ~$1,000 | Phase 4 |

**Total Deferred Investment**: ~$2,500

### 4.3 Implementation Checklist

**Week 1-2 (Metrics Implementation)**:
- [ ] Implement sufficiency metrics for all FRs
- [ ] Measure current dataset against all metrics
- [ ] Generate comprehensive sufficiency dashboard
- [ ] Identify critical gaps (FRs with insufficient data)

**Week 3-8 (Critical Gap Filling)**:
- [ ] Acquire/annotate footnote linking dataset (FR-4.5) - $1,500
- [ ] Acquire/annotate figure-caption dataset (FR-4.6) - $1,000
- [ ] Acquire/annotate reading order dataset (FR-4.12) - $5,000
- [ ] Validate DQS routing matrix coverage (FR-7.1) - $0

**Week 9-12 (Validation & Refinement)**:
- [ ] Train all FR-specific models
- [ ] Measure validation performance for each FR
- [ ] Check validation plateau for each FR
- [ ] Fill remaining gaps based on performance analysis

**Week 13-16 (Production Readiness)**:
- [ ] Final validation on held-out test sets
- [ ] Generate FR coverage report
- [ ] Document any remaining gaps with mitigation plans
- [ ] Dataset freeze and versioning

---

## Part 5: Sufficiency Dashboard (FR-Aligned)

### 5.1 FR-2.3: Learned Quality Assessment

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Total Samples** | 50,000 | 50,000 | ✅ SUFFICIENT |
| **3-Dimension Labels** | 100% coverage | 100% (weak supervision) | ⚠️ PARTIAL (awaiting DIQA-5000) |
| **Overall Quality Distribution (KL)** | < 0.1 | TBD | ⏳ PENDING |
| **Sharpness Distribution (KL)** | < 0.1 | TBD | ⏳ PENDING |
| **Color Fidelity Distribution (KL)** | < 0.1 | TBD | ⏳ PENDING |
| **Pearson Correlation (LIVE/CSIQ)** | > 0.75 | TBD | ⏳ PENDING |
| **Validation Plateau** | < 1% improvement | TBD | ⏳ PENDING |

### 5.2 FR-4.2: Layout Element Detection (11 Classes)

| Class | Minimum | Current (DocLayNet) | Status |
|-------|---------|---------------------|--------|
| **Text** | 5,000 | TBD | ⏳ PENDING |
| **Title** | 2,000 | TBD | ⏳ PENDING |
| **List-Item** | 3,000 | TBD | ⏳ PENDING |
| **Table** | 3,000 | TBD | ⏳ PENDING |
| **Picture** | 2,500 | TBD | ⏳ PENDING |
| **Caption** | 2,000 | TBD | ⏳ PENDING |
| **Formula** | 1,500 | TBD | ⏳ PENDING |
| **Footnote** | 1,500 | TBD | ⏳ PENDING |
| **Page-Header** | 2,000 | TBD | ⏳ PENDING |
| **Page-Footer** | 2,000 | TBD | ⏳ PENDING |
| **Section-Header** | 2,000 | TBD | ⏳ PENDING |
| **YOLOv8 mAP@.50** | > 0.82 | TBD | ⏳ PENDING |

### 5.3 FR-7.1: Document Quality Score (DQS)

| Routing Matrix Cell | Minimum | Current | Status |
|--------------------|---------|---------|--------|
| **Low Deg × Low Struct** | 5,000 | TBD | ⏳ PENDING |
| **Low Deg × Med Struct** | 7,500 | TBD | ⏳ PENDING |
| **Low Deg × High Struct** | 7,500 | TBD | ⏳ PENDING |
| **Med Deg × Low Struct** | 7,500 | TBD | ⏳ PENDING |
| **Med Deg × Med Struct** | 10,000 | TBD | ⏳ PENDING |
| **Med Deg × High Struct** | 7,500 | TBD | ⏳ PENDING |
| **High Deg × Low Struct** | 5,000 | TBD | ⏳ PENDING |
| **High Deg × Med Struct** | 5,000 | TBD | ⏳ PENDING |
| **High Deg × High Struct** | 2,500 | TBD | ⏳ PENDING |
| **Routing Accuracy** | > 90% | TBD | ⏳ PENDING |

### 5.4 Structural Relationships (FR-4.4-4.7, 4.12)

| FR | Metric | Target | Current | Status |
|----|--------|--------|---------|--------|
| **FR-4.4** | Parasitic content accuracy | > 90% | 0 samples | ❌ CRITICAL GAP |
| **FR-4.5** | Footnote linking accuracy | > 85% | 0 samples | ❌ CRITICAL GAP |
| **FR-4.6** | Figure-caption accuracy | > 90% | 0 samples | ❌ CRITICAL GAP |
| **FR-4.7** | Vertical text accuracy | > 95% | 0 samples | ❌ CRITICAL GAP |
| **FR-4.12** | Reading order correlation | > 0.85 | 0 samples | ❌ CRITICAL GAP |

---

## Conclusion

**Key Takeaways**:

1. **FR-Driven Coverage**: Every training data attribute maps to specific FR requirements
2. **3-Dimension Quality Assessment** (FR-2.3): Overall, Sharpness, Color Fidelity require separate training
3. **2-Axis DQS** (FR-7.1): Degradation + Structural Complexity require routing matrix coverage
4. **11 Layout Classes** (FR-4.2): All classes need ≥1,500 samples with COCO bounding boxes
5. **Structural Relationships** (FR-4.4-4.7, 4.12): Require specialized annotations (footnote links, figure-caption pairs, reading order sequences)
6. **Statistical Sufficiency**: Validation plateau + all FR-specific metrics met = SUFFICIENT

**Critical Gaps Identified**:
- ❌ **FR-4.5**: No footnote linking annotations (~$1,500 to acquire)
- ❌ **FR-4.6**: No figure-caption linking annotations (~$1,000 to acquire)
- ❌ **FR-4.12**: No reading order annotations (~$5,000 to acquire)
- ⚠️ **FR-2.3**: Weak supervision only, awaiting DIQA-5000 (Sept 2025)

**Total Investment Needed**: ~$7,500 for critical FR gaps

**Next Steps**:
1. Implement sufficiency metrics for all FRs
2. Measure current dataset against all FR requirements
3. Prioritize $7,500 investment in critical gap filling
4. Validate all FRs meet performance targets before production

---

**Created**: 2025-11-14 (v1.0)
**Updated**: 2025-11-14 (v2.0 - comprehensive FR alignment)
**Status**: ✅ Complete - All 48 FRs reviewed and training requirements defined
**Next Review**: After implementing sufficiency metrics and measuring current dataset
