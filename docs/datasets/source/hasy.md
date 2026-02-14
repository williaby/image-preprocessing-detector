#### hasy (HASYv2 - Math Symbols Handwriting)

> **Quick Stats**: 168,233 symbols | 369 classes | Mathematical symbols | Crowdsourced
>
> **License**: ODC ODbL v1.0 | **Commercial Use**: Yes (with attribution required)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | HASY v2: Handwritten Symbol Database |
| **Version** | 2.0 |
| **Release Date** | 2017-01-24 |
| **Last Updated** | 2020-01-24 (dataset), 2026-02-01 (documentation) |
| **Maintainer** | Martin Thoma |
| **Paper** | [The HASYv2 dataset](https://arxiv.org/abs/1701.08380) |
| **Repository** | [Zenodo: HASYv2](https://zenodo.org/records/259444) |
| **DOI** | [10.5281/zenodo.259444](https://doi.org/10.5281/zenodo.259444) |
| **License** | ODC ODbL v1.0 ([Open Database License](https://opendatacommons.org/licenses/odbl/1-0/)) |
| **Commercial Use** | Yes (with attribution required) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/hasyv2/` |
| **GCS (Legacy)** | `gs://image_detection_b/image-preprocessing-detector/datasets/maths_handwriting/` |
| **Documentation Status** | Complete |

> **Attribution Required**: Must credit Martin Thoma and cite paper (arXiv:1701.08380) when using this dataset.

##### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | 168,233 handwritten symbol images (32×32 pixels) |
| **Annotations** | CSV | 20 CSV files (10 folds × 2 splits) with labels |
| **Metadata** | Implicit | User IDs in CSV for crowdsource tracking |
| **Supplementary** | Unknown | README/documentation (if present in archive) |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Fold 1 Train** | `hasy-data/` (shared) | `classification-task/fold-1/train.csv` | ~15,141 | ✅ |
| **Fold 1 Test** | `hasy-data/` (shared) | `classification-task/fold-1/test.csv` | ~1,682 | ✅ |
| **Fold 2 Train** | `hasy-data/` (shared) | `classification-task/fold-2/train.csv` | ~15,141 | ✅ |
| **Fold 2 Test** | `hasy-data/` (shared) | `classification-task/fold-2/test.csv` | ~1,682 | ✅ |
| **...** | *(Folds 3-10 follow same pattern)* | | | |
| **Total Train** | `hasy-data/` | All fold-*/train.csv | 151,410 | ✅ |
| **Total Test** | `hasy-data/` | All fold-*/test.csv | 16,823 | ✅ **RESERVED** |

**Split Organization Pattern**: `by_file_list` (CSV manifests reference shared image directory)

> **Notes**:
>
> - All 168,233 images stored in single `hasy-data/` directory
> - CSV files use relative paths: `../../hasy-data/v2-XXXXX.png`
> - Test split (16,823 samples) is **RESERVED** for benchmark comparisons
> - 10-fold cross-validation structure enables robust model evaluation

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Symbol Class ID** | CSV | Image-level | Numeric class ID (1-369) |
| **LaTeX Representation** | CSV | Image-level | Semantic symbol label (e.g., `\alpha`, `\sum`) |
| **User ID** | CSV | Image-level | Crowdsource contributor ID for quality control |
| **Fold Membership** | CSV location | Image-level | Which cross-validation fold (1-10) |
| **Split Assignment** | CSV location | Image-level | Train or test within fold |

> **Note**: No bounding boxes or polygons (each 32×32 image contains exactly one symbol)

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Zenodo page | Version, license, DOI, citation |
| **Image-level** | Filename | Unique identifier (v2-XXXXX.png) |
| **Annotation-level** | CSV columns | Symbol ID, LaTeX, user ID |
| **Quality Control** | CSV user_id | Crowdsource contributor tracking |

###### 2.5 Annotation Schema Details

> **Format**: CSV with 4 columns per image

```text
# CSV Format (classification-task/fold-N/train.csv or test.csv)
path,symbol_id,latex,user_id
../../hasy-data/v2-00016.png,31,A,8071
../../hasy-data/v2-00017.png,145,\alpha,8071
../../hasy-data/v2-00018.png,267,\sum,8072
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `path` | str | Yes | Relative path from CSV location to image |
| `symbol_id` | int | Yes | Numeric class ID (1-369) |
| `latex` | str | Yes | LaTeX representation of symbol |
| `user_id` | int | Yes | Crowdsource contributor ID |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Symbol class IDs | `symbol_id` | High | Direct integer mapping |
| ✅ LaTeX labels | `latex` (text GT) | High | Semantic ground truth |
| ✅ User IDs | `user_id` | Medium | Quality control metadata |
| ✅ Fold structure | `fold`, `split` | High | Cross-validation tracking |
| ❌ Bounding boxes | - | N/A | Not applicable (isolated symbols) |
| ❌ Segmentation | - | N/A | Not applicable (32×32 isolated) |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

###### 2.7 Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Crowdsourced |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | ~100K contributors via write-math.com |
| **Inter-Annotator Agreement** | Crowd consensus (multiple contributors per symbol class) |
| **Quality Assurance** | Crowdsource verification with contributor agreement filtering |
| **GT Label Coverage** | 100% (all 168K symbol images with class labels) |

##### Dataset Statistics

###### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Fold 1 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 1 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 2 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 2 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 3 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 3 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 4 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 4 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 5 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 5 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 6 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 6 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 7 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 7 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 8 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 8 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 9 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 9 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Fold 10 Train** | ~15,141 | TBD | TBD | ⚠️ Verify |
| **Fold 10 Test** | ~1,682 | TBD | TBD | ⚠️ Verify |
| **Total Train** | 151,410 | TBD | TBD | ⚠️ Verify |
| **Total Test** | 16,823 | TBD | TBD | ⚠️ Verify **RESERVED** |
| **Grand Total** | 168,233 | TBD | TBD | ⚠️ Verify |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Verify - Counts need verification from CSV parsing or Layer 2 metadata
- ❌ Missing - Split not included in Layer 2 metadata
- 🔴 RESERVED - Test split must not be used for training

> **Note**: Per-fold counts are estimates assuming balanced folds (~15,141 train / ~1,682 test per fold).
> Actual counts should be verified by parsing CSV files or querying Layer 2 metadata.
>
> **Training Constraint**: The 16,823 test samples across all folds are RESERVED for benchmark
> comparisons and must never be used for training or validation.

> **Cross-Validation Usage**: When training with 10-fold CV, ensure each fold's test split is
> held out during training on that fold. Do not mix train/test samples within folds.

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Samples** | 168,233 |
| **Symbol Classes** | 369 |
| **Image Size** | 32×32 pixels |
| **File Format** | PNG |
| **Color** | Binary (B&W) |

##### 5. Content Composition

###### 5.2 Class/Category Definitions

> **Purpose**: Define the taxonomy of 369 mathematical symbol classes.
> **Source**: Extracted from CSV label files (symbol_id → latex mappings)

**Symbol Categories** (369 total classes):

| Category | Symbol Count | Examples |
|----------|--------------|----------|
| **Latin Uppercase** | 26 | A, B, C, ..., Z |
| **Latin Lowercase** | 26 | a, b, c, ..., z |
| **Greek Uppercase** | ~24 | Α, Β, Γ, ..., Ω |
| **Greek Lowercase** | ~24 | α, β, γ, ..., ω |
| **Digits** | 10 | 0, 1, 2, ..., 9 |
| **Operators** | ~50 | +, -, ×, ÷, =, ≠, ≈, ∝, etc. |
| **Relations** | ~30 | <, >, ≤, ≥, ∈, ∉, ⊂, ⊃, etc. |
| **Symbols** | ~60 | ∑, ∏, ∫, ∂, ∇, √, ∞, π, etc. |
| **Arrows** | ~20 | →, ←, ↔, ⇒, ⇐, ⇔, etc. |
| **Brackets** | ~12 | (, ), [, ], {, }, ⟨, ⟩, etc. |
| **Other** | ~97 | Miscellaneous mathematical symbols |

**Sample Symbol Mappings**:

| Symbol ID | LaTeX | Description | Category |
|-----------|-------|-------------|----------|
| 31 | `A` | Latin uppercase A | Latin Uppercase |
| 145 | `\alpha` | Greek lowercase alpha | Greek Lowercase |
| 267 | `\sum` | Summation operator | Symbols |

> **Note**: Complete 369-class taxonomy available by parsing all CSV files. The above table
> shows category-level groupings and representative examples. Full symbol-by-symbol mapping
> can be extracted using parser code or CSV inspection.

**Class Distribution Analysis**: [NEEDS_PROFILING]

- Most frequent symbols: TBD (requires CSV parsing)
- Least frequent symbols: TBD (requires CSV parsing)
- Class imbalance ratio: TBD (requires analysis)

###### 5.3 Language & Script Coverage

> **Purpose**: Document script classification for mathematical symbols.
> **Applicability**: OCR routing, script detection model training.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Common (Math) | Zyyy | 168,233 | 100% | Mathematical symbols, script-agnostic |

**Script Families Present**: Common (mathematical notation)

> **Notes**:
>
> - Mathematical symbols use ISO 15924 code "Zyyy" (Common/Undetermined script)
> - This is the correct classification per Unicode standards for math notation
> - Symbols are language-agnostic (used across all written languages)
> - Some Latin and Greek letters may also be present (369 classes include A-Z, α-ω)
>
> **OCR Routing**: This dataset is suitable for training symbol recognizers that operate
> independently of language or script context (e.g., equation parsing, STEM document OCR).

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Crowdsourced handwritten symbols |
| **Baseline Quality** | Variable (crowdsourced) |
| **Blur Sensitivity** | **EXTREME** - Small 32×32 images |
| **Stroke Quality** | Highly variable |
| **Symbol Clarity** | Critical for recognition |
| **Key Challenge** | Symbol clarity under degradation |

##### Benchmark Performance

| Model | Accuracy | Notes |
|-------|----------|-------|
| MLP | 91.5% | Baseline |
| CNN (optimized) | **97.3%** | Convolutional layers |
| HMS-VGGNet | State-of-the-art | BatchNorm + GAP |
| MCDNN | Higher | Multi-column DNN |

*10-fold cross-validation challenge + verification challenge included*

##### 6. Training Value

###### 6.5 Training Value Assessment

> **NEW in Template v1.2.0**: Structured assessment of training suitability

**Strengths**:

- ✅ **Large Scale**: 168,233 samples sufficient for deep learning
- ✅ **Diverse Classes**: 369 symbol classes covers broad mathematical symbol space
- ✅ **Open License**: ODC ODbL v1.0 allows commercial use with attribution
- ✅ **10-Fold CV**: Built-in robust evaluation methodology
- ✅ **LaTeX Ground Truth**: Semantic labels alongside numeric class IDs
- ✅ **Quality Control**: User IDs enable filtering by contributor reliability
- ✅ **Benchmark Pedigree**: Related to CROHME competition (handwriting recognition standard)

**Weaknesses**:

- ❌ **Small Image Size**: 32×32 pixels limits spatial resolution
- ❌ **Crowdsourced Variability**: Quality varies by contributor (user_id filtering recommended)
- ❌ **No Context**: Isolated symbols, not in-document context
- ❌ **Binary Only**: No grayscale or color information
- ❌ **Class Imbalance**: Likely present but not quantified (needs analysis)
- ❌ **Resolution Mismatch**: May not generalize well to higher-resolution inputs

**Unique Characteristics**:

- **10-Fold Structure**: Enables robust cross-validation (must respect fold boundaries)
- **LaTeX Labels**: Semantic meaning alongside numeric class enables multi-task learning
- **Crowdsource Metadata**: User IDs for quality-based filtering or quality prediction tasks
- **Symbol Focus**: Pure symbol recognition, no layout or reading order complexity

**Recommended Use Cases**:

1. **Primary**: Symbol recognition model training
2. **Secondary**: Handwriting quality assessment (variable quality useful for IQA)
3. **Research**: Class imbalance handling, crowdsourced data quality analysis
4. **Transfer Learning**: Pre-train for other handwriting or symbol recognition tasks
5. **Data Augmentation**: Small size makes augmentation experiments computationally cheap

**Not Recommended For**:

- ❌ Layout detection training (no spatial context)
- ❌ Reading order prediction (isolated symbols)
- ❌ In-context symbol recognition (no surrounding text)
- ❌ High-resolution document analysis (32×32 size mismatch)

**Training Cautions**:

- ⚠️ **Test Split RESERVED**: 16,823 samples must not be used for training
- ⚠️ **Respect Fold Boundaries**: Do not mix train/test within folds during CV
- ⚠️ **User ID Filtering**: Consider filtering low-quality contributors
- ⚠️ **Resolution Generalization**: Models may not generalize to higher resolutions
- ⚠️ **License Compliance**: Must provide attribution (ODC ODbL v1.0)

**Expected Performance** (from paper):

- Baseline MLP: 91.5% accuracy
- Optimized CNN: 97.3% accuracy (10-fold CV)
- State-of-the-art: >97.3% (various architectures)

##### 3. Project Usage

###### 3a. Project Integration

- **Path (Legacy)**: `01_base_data/handwriting/maths_handwriting/` (15K images, labels unavailable)
- **Path (Full)**: `01_base_data/handwriting/hasyv2_original/hasy-data/` (168K images, labels available)
- **Purpose**: Mathematical symbol IQA, stroke quality metrics

###### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`HASYv2Parser`](../../src/image_preprocessing_detector/annotation/parsers/handwriting/hasyv2.py) |
| **Parser Status** | ✅ Complete - All available labels extracted |
| **Parser Registry** | ✅ Registered as `hasyv2`, `hasy-v2`, `hasy_v2`, `hasyv2_original` |
| **Layer 1 Fields** | `symbol_id`, `latex`, `user_id`, `fold`, `split`, `content_type` |
| **Layer 2 Auto-Derived** | `content_flags.has_handwriting=True`, `content_flags.has_formula=True`, `domain.level1="EDU"`, `capture_method.method="scanner"`, `text_content.full_text=latex`, `text_content.source_type="ground_truth"` |
| **Config Entry** | `DATASET_CONFIGS["hasyv2"]` (if present in annotate_base_metadata.py) |

**Parser Features**:

- ✅ Efficient caching mechanism for CSV data (builds label cache once)
- ✅ 10-fold cross-validation support (tracks fold membership)
- ✅ All available labels extracted (symbol_id, latex, user_id, fold, split)
- ✅ Comprehensive error handling (gracefully handles missing CSV files)
- ✅ Full type hints and documentation

**Label Extraction Mapping**:

| Source Label | Parser Field | Layer 2 Field | Notes |
|--------------|--------------|---------------|-------|
| CSV `symbol_id` | `raw_labels["symbol_id"]` | `original_labels.raw_labels.symbol_id` | Numeric class (1-369) |
| CSV `latex` | `raw_labels["latex"]` | `original_labels.raw_labels.latex` + `text_content.full_text` | Ground truth text |
| CSV `user_id` | `raw_labels["user_id"]` | `original_labels.raw_labels.user_id` | Quality control |
| CSV directory | `raw_labels["fold"]` | `original_labels.raw_labels.fold` | Fold number (1-10) |
| CSV directory | `raw_labels["split"]` | `original_labels.raw_labels.split` | "train" or "test" |
| Hardcoded | `raw_labels["content_type"]` | `original_labels.raw_labels.content_type` | "mathematical_symbol" |

> **Parser Reference**: See [hasyv2_review.md](../datasets/reviews/hasyv2_review.md) for detailed parser analysis (if available).

**Text Content Integration**:

- ✅ LaTeX labels serve as ground truth text
- ✅ Parser extracts `latex` field to `text_content.full_text`
- ✅ `text_content.source_type` set to `"ground_truth"`
- ⚠️ `text_statistics` should be computed from LaTeX strings (needs verification)

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/hasy/` | ✅ Available | 168,233 PNG files |
| **Text/GT** | Native annotations | ⚠️ Partial | CSV: LaTeX symbol labels (`latex` field, e.g., `A`, `\alpha`, `\sum`) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ⚠️ Partial - Some data available, incomplete
- ℹ️ N/A - Not applicable for this dataset
- ❌ None/Not extracted - Data not available or not yet processed

**Recommendation**: Use `hasyv2_original` for all training and evaluation (full 168K with labels).
Legacy `maths_handwriting` subset (15K) has lost labels and should not be used.

##### Dataset Variants

| Variant | Path | Images | Labels | Notes |
|---------|------|--------|--------|-------|
| **Legacy Subset** | `maths_handwriting/` | 15,000 | ❌ Lost | Upscaled, renamed |
| **Original HASYv2** | `hasyv2_original/hasy-data/` | 168,233 | ✅ CSV | Full dataset from Zenodo |

**Recommendation**: Use `hasyv2_original` for training/evaluation with labels.

##### Label Structure (hasyv2_original)

Labels are extracted from CSV files in `classification-task/fold-{1-10}/`:

| Field | Description | Example |
|-------|-------------|---------|
| `symbol_id` | Numeric class ID (1-369) | `31` |
| `latex` | LaTeX representation | `A`, `\alpha`, `\sum` |
| `user_id` | Crowdsource contributor | `8071` |
| `fold` | Cross-validation fold (1-10) | `1` |
| `split` | Train or test split | `train` |

##### Layer 2 Annotation Summary (Legacy Subset)

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 15,000 (subset) |
| **File Format** | PNG (100%) |
| **Dimensions** | 232 × 231 px (fixed) |
| **Avg File Size** | 10 KB |
| **Color Space** | RGBA |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | EDU (Educational/Math) |
| **Content Flags** | Formulas: ✅, Handwriting: ✅ |

---
