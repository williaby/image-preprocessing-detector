# Natural Scan Stratification Plan for Skew Training Dataset

> **Status**: Draft
> **Purpose**: Define stratification strategy for the natural scan subset of the 100K skew training dataset
> **Target**: 20K natural scans (expanded from original 15K for better coverage)
> **Key Requirement**: Hold back at least one language/script per text direction category for testing

---

## Design Principles

1. **Script-held-back testing**: Reserve at least one full script per text direction (LTR, RTL, vertical) that appears ONLY in test, never in training
2. **Stratify across**: orientation (portrait/landscape), text direction, layout type, domain, handwriting presence, capture method
3. **Maximize coverage** from existing datasets rather than under-utilizing available data

---

## Text Direction Categories & Held-Back Scripts

### Category 1: Left-to-Right (LTR)

| Role | Scripts | Rationale |
|------|---------|-----------|
| **Training** | Latin, Cyrillic, Devanagari, Thai, Bengali, Tibetan | Broad LTR coverage |
| **Held-back for Test** | **Georgian (Geor)** | Well-represented in MDIW13, never seen during training |

### Category 2: Right-to-Left (RTL)

| Role | Scripts | Rationale |
|------|---------|-----------|
| **Training** | Arabic (Arab), Hebrew (Hebr) | Two major RTL families |
| **Held-back for Test** | **Urdu/Nastaliq (Arab variant)** | Distinct visual structure from standard Arabic, available via MDIW13 Urdu subset |

> **Note**: Urdu uses Nastaliq style of Arabic script which is visually distinct enough to test generalization. If the model handles Arabic Naskh in training, Nastaliq tests whether it generalizes to RTL scripts with different visual characteristics.

### Category 3: Vertical (Top-to-Bottom)

| Role | Scripts | Rationale |
|------|---------|-----------|
| **Training** | Chinese Simplified (Hans), Chinese Traditional (Hant), Japanese (Jpan) | Major vertical text families |
| **Held-back for Test** | **Korean (Hang)** | Can be written vertically, visually distinct from CJK |

### Script/Language Inventory by Dataset

| Dataset | Scripts Available | Text Directions | Usable for |
|---------|-----------------|-----------------|------------|
| RVL-CDIP (16K) | Latin | LTR | Training LTR |
| Tobacco-800 (1.3K) | Latin | LTR | Training LTR |
| MDIW13 (290K) | 13 scripts: Arabic, Latin, Chinese, Devanagari, Cyrillic, Thai, Khmer, Bengali, Georgian, Japanese, Tibetan, Korean, Urdu | LTR, RTL, Vertical | All categories |
| MLT19 (20K) | 10 languages including Arabic, Chinese, Japanese, Korean, Devanagari | LTR, RTL, Vertical | All categories |
| OHR-Bench (8.5K) | Mixed (OpenLID detected) | LTR dominant | Training LTR |
| Arabic-Docs (10K) | Arabic | RTL | Training RTL |
| Yarmouk (15K) | Arabic | RTL | Training RTL |
| Muharaf (25.7K) | Arabic | RTL | Training RTL |
| PUCIT-OHUL (7.4K) | Urdu | RTL (Nastaliq) | **Test-only RTL** |
| Nepali-Handwritten (958) | Devanagari | LTR | Training LTR |
| CVSI (10.7K) | Multiple Indic | LTR | Training LTR |
| NIST-SD6 (5.6K) | Latin | LTR | Training LTR |
| SROIE (973) | Latin + Mixed | LTR | Training LTR |
| MIDV-500 (3.6K) | Mixed (50 countries) | Mixed | Training Mixed |
| Bhutan-AFS (135) | Dzongkha | LTR | Training LTR |

---

## Stratification Matrix

### Dimension 1: Page Orientation (Portrait vs Landscape)

| Orientation | Target Count | Source Strategy |
|-------------|-------------|-----------------|
| **Portrait** | 12,000 (60%) | Most documents are portrait (letters, forms, reports) |
| **Landscape** | 5,000 (25%) | Spreadsheets, presentations, wide tables, ID documents |
| **Square/Mixed** | 3,000 (15%) | Receipts, cropped images, mobile captures |

**Selection method**: Use image dimensions (width > height = landscape). For datasets with known orientation metadata, use that directly.

### Dimension 2: Text Direction

| Direction | Target Count | Training Scripts | Test-Only Scripts |
|-----------|-------------|-----------------|-------------------|
| **LTR** | 12,000 (60%) | Latin, Cyrillic, Devanagari, Thai, Bengali, Tibetan | Georgian |
| **RTL** | 4,000 (20%) | Arabic (Naskh), Hebrew | Urdu (Nastaliq) |
| **Vertical** | 2,500 (12.5%) | Hans, Hant, Japanese | Korean |
| **Mixed/Bidi** | 1,500 (7.5%) | Multi-script documents, IDs | - |

### Dimension 3: Document Layout Types

| Layout | Target | Primary Sources |
|--------|--------|-----------------|
| **Single-column text** | 5,000 (25%) | RVL-CDIP (letters, memos), Arabic-Docs |
| **Multi-column** | 3,000 (15%) | RVL-CDIP (scientific), OHR-Bench |
| **Tables/Structured** | 4,000 (20%) | RVL-CDIP (invoices, budgets), NIST-SD6 |
| **Forms** | 2,500 (12.5%) | NIST-SD6, RVL-CDIP (forms), FUNSD |
| **Dense math/scientific** | 1,000 (5%) | RVL-CDIP (scientific_publication) |
| **Sparse/image-heavy** | 1,500 (7.5%) | RVL-CDIP (advertisements, presentations) |
| **Handwriting-dominant** | 2,000 (10%) | MDIW13, RVL-CDIP (handwritten class), PUCIT-OHUL (test) |
| **Mixed/other** | 1,000 (5%) | MIDV-500, SROIE, mixed |

### Dimension 4: Domains

| Domain | Target | Primary Sources |
|--------|--------|-----------------|
| **Administrative (ADM)** | 4,000 (20%) | RVL-CDIP, Tobacco-800 |
| **Financial (FIN)** | 3,000 (15%) | NIST-SD6, SROIE, RVL-CDIP (invoices) |
| **Scientific (SCI)** | 3,000 (15%) | RVL-CDIP (scientific), OHR-Bench |
| **Educational (EDU)** | 2,500 (12.5%) | OHR-Bench, MDIW13 |
| **Government/Legal** | 2,500 (12.5%) | Tobacco-800, NIST-SD2, Arabic-Docs |
| **Technical (TEC)** | 2,000 (10%) | RVL-CDIP (specifications) |
| **Identity/Travel** | 1,000 (5%) | MIDV-500 |
| **Commercial** | 1,000 (5%) | RVL-CDIP (advertisements), SROIE |
| **Mixed/Other** | 1,000 (5%) | Various |

### Dimension 5: Handwriting Presence

| Category | Target | Sources |
|----------|--------|---------|
| **No handwriting** | 14,000 (70%) | Most printed datasets |
| **Mixed (print + handwriting)** | 3,000 (15%) | NIST-SD6, forms with annotations |
| **Handwriting-dominant** | 3,000 (15%) | RVL-CDIP handwritten, MDIW13, Nepali-Handwritten |

### Dimension 6: Capture Method

| Method | Target | Sources |
|--------|--------|---------|
| **Scanner (flatbed/ADF)** | 10,000 (50%) | RVL-CDIP, Tobacco-800, NIST-SD6 |
| **Camera/Mobile** | 6,000 (30%) | MDIW13, MIDV-500, SROIE, SmartDoc-QA |
| **Born-digital** | 2,000 (10%) | Clean PDFs with synthetic rotation applied |
| **Mixed/Unknown** | 2,000 (10%) | OHR-Bench, other mixed sources |

---

## Dataset Allocation Table

### Training Split (16,000 images)

| Dataset | Count | Role | Scripts | Directions | Layout Types |
|---------|-------|------|---------|------------|--------------|
| **RVL-CDIP** | 6,000 | Core LTR, diverse layouts | Latin | LTR | All 16 classes (375 each) |
| **MDIW13** | 3,000 | Multilingual diversity | 10 scripts (excl. Georgian, Korean, Urdu) | LTR, RTL, Vertical | Mixed wild |
| **Arabic-Docs** | 1,200 | RTL coverage | Arabic | RTL | Mixed |
| **Yarmouk** | 800 | RTL + OCR diversity | Arabic | RTL | Mixed |
| **Muharaf** | 500 | RTL handwriting | Arabic | RTL | Handwriting |
| **OHR-Bench** | 1,500 | Quality diversity | Mixed | LTR dominant | Mixed |
| **Tobacco-800** | 800 | Archival degradation | Latin | LTR | Administrative |
| **NIST-SD6** | 500 | Forms + handwriting | Latin | LTR | Forms |
| **MLT19** | 500 | Scene text (excl. Korean) | 9 languages | LTR, RTL, Vertical | Scene |
| **MIDV-500** | 400 | ID documents | Mixed | Mixed | Identity |
| **SROIE** | 300 | Receipts | Mixed | LTR | Structured |
| **CVSI** | 200 | Indic scripts | Multiple Indic | LTR | Video captions |
| **Nepali-Handwritten** | 200 | Devanagari handwriting | Devanagari | LTR | Handwriting |
| **Bhutan-AFS** | 100 | Dzongkha rare script | Tibetan/Dzongkha | LTR | Forms |
| **TOTAL** | **16,000** | | | | |

### Validation Split (2,000 images)

Same distribution as training at ~12.5% ratio, sampled from same datasets (different images).

### Test Split (2,000 images) -- INCLUDES HELD-BACK SCRIPTS

| Dataset | Count | Purpose | Scripts |
|---------|-------|---------|---------|
| **MDIW13 - Georgian** | 400 | Held-back LTR script | Georgian |
| **MDIW13 - Korean** | 400 | Held-back vertical script | Korean (Hangul) |
| **PUCIT-OHUL** | 400 | Held-back RTL script (Nastaliq) | Urdu |
| **RVL-CDIP holdout** | 300 | In-distribution LTR test | Latin |
| **Arabic-Docs holdout** | 200 | In-distribution RTL test | Arabic |
| **MDIW13 - CJK holdout** | 200 | In-distribution vertical test | Hans/Hant/Jpan |
| **MIDV-500 holdout** | 100 | ID document test | Mixed |
| **TOTAL** | **2,000** | | |

> **Key**: 1,200 of 2,000 test images (60%) use **scripts never seen in training**. This provides strong generalization testing for each text direction.

---

## Skew Angle Labeling Strategy

Natural scans don't have ground-truth skew angles. Strategy:

1. **High-confidence classical ensemble** (conf >= 0.7): Run existing `SkewDetector` (Hough + Projection Profile) and keep only images where both methods agree within 1 degree
2. **Manual review of 1,000 samples**: Random sample across all datasets, manually verify classical labels
3. **Cross-validation**: For images with OCR text, verify that text lines confirm the detected skew direction
4. **Discard ambiguous**: Remove images where classical methods disagree by > 2 degrees or confidence < 0.5

### Angle Distribution Targets (for natural scans)

Natural scans will NOT match the synthetic distribution (which is uniform). Expected distribution:

| Range | Expected % | Count | Notes |
|-------|-----------|-------|-------|
| |angle| < 0.5 | 30% | 6,000 | Many well-scanned documents |
| 0.5 <= |angle| < 2 | 35% | 7,000 | Common mild skew |
| 2 <= |angle| < 5 | 20% | 4,000 | Moderate skew |
| 5 <= |angle| < 15 | 10% | 2,000 | Large skew (ADF errors) |
| |angle| >= 15 | 5% | 1,000 | Extreme (camera captures) |

If the natural distribution is too concentrated near zero, we can:

- Over-sample skewed images from camera datasets (MDIW13, MIDV-500)
- Apply synthetic rotation to a subset of natural images (keeping the natural degradation but adding known skew)

---

## Dataset Size Justification

Expanding from 15K to 20K provides:

1. **Better script coverage**: 10+ scripts with meaningful sample counts (200+ each)
2. **Adequate held-back test sets**: 400 images per held-back script is statistically meaningful
3. **Domain diversity**: 9 domains with 200+ images each
4. **Layout type coverage**: 8 layout categories with meaningful representation
5. **Leverage available data**: We have 400K+ images across eligible datasets; 20K is only 5%

Combined with the 80K synthetic images (already planned), the total training set becomes 100K (80K synthetic + 20K natural), maintaining the overall dataset size from the original plan.

---

## Selection Script Specifications

Script: `scripts/select_natural_scan_skew_subset.py`

**Inputs**:

- Layer 2 metadata from `/mnt/e/image_detection/metadata_registry/json/{dataset}/`
- Classical IQA skew detection results
- Stratification targets (this document)

**Algorithm**:

1. Load all candidate images with Layer 2 metadata
2. Compute stratification bins (orientation, direction, layout, domain, handwriting, capture)
3. Greedy allocation: fill each bin to target, prioritizing under-represented dimensions
4. Enforce held-back constraint: Georgian, Korean, Urdu images go ONLY to test split
5. Apply 80/10/10 split (train/val/test) with stratification preserved across splits
6. Run classical skew detection on selected images, filter by confidence >= 0.7
7. Output: `metadata_registry/json/skew_natural_scan/` with per-image records

**Output schema** (per image):

```json
{
  "filename": "rvl-cdip_00001.jpg",
  "source_dataset": "rvl-cdip",
  "split": "train",
  "classical_skew_angle": 1.23,
  "classical_skew_confidence": 0.85,
  "classical_skew_method": "ensemble",
  "orientation": "portrait",
  "text_direction": "ltr",
  "script": "Latn",
  "language": "en",
  "layout_type": "single_column",
  "domain": "ADM",
  "has_handwriting": false,
  "capture_method": "scanner"
}
```

---

## Verification Checklist

- [ ] Every training script appears in at least 200 images
- [ ] Georgian, Korean, Urdu appear ONLY in test split
- [ ] Portrait/Landscape ratio approximately 60/25/15
- [ ] RTL represents at least 20% of total
- [ ] Vertical text represents at least 12.5% of total
- [ ] Handwriting present in at least 15% of total
- [ ] All 9 domains represented with at least 200 images
- [ ] Classical skew labels have confidence >= 0.7
- [ ] 1,000 manual label verifications completed
- [ ] Train/val/test splits have consistent stratification distributions
