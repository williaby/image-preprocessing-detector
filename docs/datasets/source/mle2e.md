#### mle2e (Multi-Language End-to-End)

> **Quick Stats**: 1,817 images (1,816 verified) | 4 scripts | Scene text | Korean focus
>
> **License**: Research | **Commercial Use**: Research only

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multi-Language End-to-End Dataset |
| **Canonical Name** | mle2e |
| **Version** | 1.0 |
| **Release Date** | 2016 |
| **Maintainer** | Lluis Gomez et al. |
| **Paper** | [A fine-grained approach to scene text script identification (arXiv:1602.07475)](https://arxiv.org/abs/1602.07475) |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **Commercial Use** | Research only (no commercial license) |
| **Documentation Status** | Partial (Sections 2-5 complete, IQA profiling pending) |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Scene text images (4 scripts), pre-segmented text line crops |
| **Annotations** | TXT | Per-image annotation files (.txt) for full scene images |
| **Metadata** | TXT (README) | Dataset README with structure documentation |
| **Supplementary** | None | See paper for detailed documentation |

##### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `mle2e/Training/{script}/*.jpg` | N/A (pre-segmented by script) | 1,174 | ✅ [Official] |
| **Test** | `mle2e/Testing/{script}/*.jpg` | N/A (pre-segmented by script) | 642 | ✅ [Official] |
| **Total** | - | - | 1,816 | ✅ All splits |

**Split Organization Pattern**: `by_folder` (Training/ and Testing/ directories, subdivided by script)

> **Notes**:
>
> - Dataset provides **pre-segmented text line crops** organized by script class
> - Each split has 4 subdirectories: `chinese/`, `kannada/`, `korean/`, `latin/`
> - Full scene images with bounding box annotations exist separately (not in current local copy)
> - Current local dataset: **cropped text lines only** (1,816 images total)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Script Labels** | Directory structure | Word/Region | Implicit from folder name (chinese, kannada, korean, latin) |
| **Text Transcriptions** | TXT (separate) | Word/Region | Ground truth text (available for test set only) |
| **Bounding Boxes** | TXT (x1,y1,x2,y2) | Word/Region | **NOT in current local copy** (full scene images only) |

> **Note**: Current local dataset contains **pre-segmented crops** without bounding boxes. Full scene images with bbox annotations exist in original dataset but not extracted locally.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README.txt, Paper (arXiv:1602.07475) | Dataset description, splits, annotation format |
| **Image-level** | Filename | Implicit script class from directory structure |
| **Annotation-level** | N/A (pre-segmented) | Script class determined by folder location |

##### 2.5 Annotation Schema Details

**Format**: Pre-segmented text line images organized by script class

```text
# Directory structure:
mle2e/
  Training/
    chinese/     # Chinese text line crops
    kannada/     # Kannada text line crops
    korean/      # Korean (Hangul) text line crops
    latin/       # Latin text line crops
  Testing/
    chinese/
    kannada/
    korean/
    latin/
  README.txt     # Dataset documentation
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `directory_path` | str | Yes | Determines script class (chinese, kannada, korean, latin) |
| `filename` | str | Yes | Image identifier (e.g., box_1193.jpg) |
| `split` | str | Yes | Extracted from path (Training → train, Testing → test) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Script labels | ✅ `language.script_code` | High | ISO 15924 mapping implemented |
| ✅ Text transcriptions | ⚠️ `text_content.full_text` | High | Available for test set only (separate file) |
| ❌ Bounding boxes | ❌ `layout_detections.bbox` | N/A | Pre-segmented crops (no bbox needed) |
| ✅ Split info | ✅ `provenance.split` | Medium | From directory structure (Training/Testing) |
| ⚠️ ISO 639 codes | ✅ `language.language_code` | High | Inferred mapping (latin→en, chinese→zh, etc.) |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Scene text annotation with 4 scripts |
| **GT Label Coverage** | 100% |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 10B (Script Detection) |
| **Purpose** | Korean script isolation from CJK Mixed, 4-script classification training |
| **Local Path** | `01_base_data/language/mle2e/` |
| **Subset Used** | Full dataset (all 1,816 pre-segmented text line crops) |
| **Training Approach** | Pre-segmented text line classification (no detection required) |

##### 3a. Parser & Metadata Integration

| Component | Status | Details |
|-----------|--------|---------|
| **Parser** | ✅ Implemented | `Mle2eParser` in `parsers/multilingual/mle2e.py` |
| **Registry** | ✅ Registered | Handles dataset name: `mle2e` |
| **Layer 2 Schema** | ⚠️ Partial | Language/script extraction complete, bbox extraction N/A (pre-segmented) |
| **Text Extraction** | ⚠️ Partial | Test set only (separate transcription file not yet integrated) |

**Parser Capabilities**:

- ✅ Script class extraction (from directory structure)
- ✅ ISO 15924 script code mapping (Latn, Hans, Knda, Hang)
- ✅ ISO 639 language code inference (en, zh, kn, ko)
- ✅ Split detection (train/test from path)
- ⚠️ Text transcription extraction (test set only, requires separate file processing)
- ❌ Bounding box extraction (N/A for pre-segmented crops)

##### 3b. Parser Coverage Matrix

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| Directory name (script) | language.script_code | ✅ Yes | High | ISO 15924 codes (Latn, Hans, Knda, Hang) |
| Directory name (script) | language.language_code | ✅ Yes | High | Inferred ISO 639 codes (en, zh, kn, ko) |
| Directory structure | provenance.split | ✅ Yes | Medium | Training → train, Testing → test |
| Text transcriptions | text_content.full_text | ⚠️ Partial | Medium | Test set only (not yet integrated) |
| Image dimensions | image_metadata.width/height | ✅ Yes | Low | Extracted from image file |
| Bounding boxes | layout_detections.bbox | ❌ N/A | N/A | Pre-segmented crops (no bbox needed) |

**Gaps**:

1. **Text transcription integration**: Test set transcriptions exist in separate file (not yet integrated into parser)
2. **Full scene image annotations**: Original dataset has bbox annotations for full scene images, but only pre-segmented crops are available locally

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/mle2e/` | ✅ Available | 1,816 JPG files |
| **Text/GT** | Native annotations | ✅ Available | TXT/JSON: Word-level text in detection annotations |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/mle2e/` | ✅ Available | Docling GPU: 10 layout batches, 1,816 images |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ⚠️ Partial - Data partially available or pending integration
- ❌ Not available locally - Data not available in current local setup
- 🔄 In progress - Currently being processed

---

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Layer 2 metadata exists in parquet format. This section populated from empirical data.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 1,174 | TBD | - | ⚠️ Pending aggregation |
| **Test** | 642 | TBD | - | ⚠️ Pending aggregation |
| **Total** | 1,816 | TBD | - | ⚠️ Pending aggregation |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Pending - Layer 2 metadata aggregation not yet run
- ❌ Missing - Split not included in Layer 2 metadata

> **Action Required**: Run aggregation script to populate Layer 2 counts:
>
> ```bash
> uv run python scripts/aggregate_layer2_metadata.py --dataset mle2e
> ```

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 1,816 (1,174 train + 642 test) |
| **Training Split** | 1,174 (64.6%) |
| **Testing Split** | 642 (35.4%) |
| **Image Dimensions** | [NEEDS_PROFILING] Variable (pre-segmented text line crops, scene text) |
| **Resolution (DPI)** | N/A (scene text crops, no DPI metadata) |
| **File Format(s)** | JPG |
| **Color Space** | RGB |
| **Total Size on Disk** | 19 MB [Official] |
| **Annotation Format** | Directory structure (implicit script labels) |

**Script Distribution** (empirical counts from filesystem):

| Script | Training | Testing | Total | Percentage |
|--------|----------|---------|-------|------------|
| **Chinese** | 301 | TBD | 301+ | 16.6%+ |
| **Kannada** | 152 | TBD | 152+ | 8.4%+ |
| **Korean** | 225 | TBD | 225+ | 12.4%+ |
| **Latin** | 496 | TBD | 496+ | 27.3%+ |
| **Total** | 1,174 | 642 | 1,816 | 100% |

> **Note**: Test set script distribution pending verification. Training set shows Latin-heavy distribution.

##### 4.3 Text Statistics (from ground truth transcriptions)

> **Source**: Ground truth text labels (available for test set only)
> **Availability**: ⚠️ Partial (test set only, not yet integrated into parser)
> **Status**: [NEEDS_PROFILING] - Statistics will be computed after transcription integration

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Character Count** | TBD | TBD | TBD | TBD / TBD / TBD |
| **Word Count** | TBD | TBD | TBD | TBD / TBD / TBD |
| **Sentence Count** | N/A | N/A | N/A | N/A (word/phrase-level only) |

**Text Source**: `ground_truth` (dataset_provided, test set only)

> **Note**: Text statistics will be computed after transcription file integration using:
>
> ```bash
> uv run python scripts/calculate_text_statistics.py --input metadata_registry/json/mle2e_layer2.json
> ```

---

#### 5. Content Composition

##### 5.1 Content Type Distribution

| Content Type | Presence | Notes |
|--------------|----------|-------|
| **Scene Text** | 100% | All images are scene text (signs, storefronts, natural scenes) |
| **Multi-Script** | Common | Some images contain multiple scripts |
| **Handwriting** | 0% | Printed text only |
| **Tables** | 0% | Scene text only |
| **Figures** | 0% | Text regions only |

##### 5.2 Script Class Definitions

> **Purpose**: Define the 4 script classes used in mle2e annotations.
> **Taxonomy**: Flat (no hierarchy), single label per image (pre-segmented crops).

| Script Class | ISO 15924 Code | Language Examples | Description |
|--------------|----------------|-------------------|-------------|
| **Latin** | Latn | English, Spanish, French | Western alphabet (A-Z) |
| **Chinese** | Hans | Chinese (Simplified) | Han logograms (CJK) |
| **Kannada** | Knda | Kannada | South Indian Dravidian script |
| **Korean** | Hang | Korean | Hangul blocks (syllabic alphabet) |

**Script Family Mapping**:

- Latin → `latin` family
- Chinese → `cjk` family
- Kannada → `indic` family
- Korean → `cjk` family (Hangul is distinct but grouped for OCR routing)

**Notes**:

- mle2e is designed to test script confusability, especially Korean vs Chinese
- Scene text images may contain multiple scripts (in full scene images)
- Each pre-segmented text line crop is labeled with ONE primary script

##### 5.3 Language & Script Coverage

> **Purpose**: Document script distribution across 1,816 scene text images.
> **Status**: [NEEDS_PROFILING] - Full distribution will be computed from Layer 2 metadata.

| Script | ISO 15924 | Language | ISO 639 | Instances | Coverage | Notes |
|--------|-----------|----------|---------|-----------|----------|-------|
| **Latin** | Latn | English | en | 496+ | 27.3%+ | Primary script (training set) |
| **Chinese** | Hans | Chinese (Simplified) | zh | 301+ | 16.6%+ | Han logograms |
| **Korean** | Hang | Korean | ko | 225+ | 12.4%+ | Hangul blocks |
| **Kannada** | Knda | Kannada | kn | 152+ | 8.4%+ | South Indian script |

**Script Families Present**: Latin, CJK, Indic

**Key Characteristics**:

- **Korean Focus**: Dataset emphasizes distinguishing Hangul from Han logograms
- **Multi-Script Images**: Some full scene images contain multiple scripts
- **Scene Text**: Natural scene images (signs, storefronts, etc.)
- **Script Confusability**: Designed to test script identification accuracy
- **Pre-segmented Crops**: Current local dataset has isolated text lines (one script per crop)

> **Note**: Script distribution counts are from training set only. Test set distribution will be computed after Layer 2 metadata aggregation using:
>
> ```bash
> uv run python scripts/enrich_language.py --dataset mle2e
> uv run python scripts/aggregate_layer2_metadata.py --dataset mle2e --stats script
> ```

---

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Scene text images (camera-captured, natural scenes) |
| **Capture Device** | Various (smartphone, camera) [Inferred] |
| **Original Quality** | Variable (outdoor scenes, varied lighting conditions) |
| **Compression** | JPEG (quality varies) |
| **Known Artifacts** | Perspective distortion, motion blur, lighting variations, low resolution |

##### 6.2 Degradation Sensitivity

> **Status**: [NEEDS_PROFILING] - IQA sensitivity to be determined from profiling runs.

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | [NEEDS_PROFILING] | Scene text may already have motion/focus blur |
| **Noise** | [NEEDS_PROFILING] | Variable based on capture conditions |
| **Skew** | HIGH | Perspective distortion common in scene text |
| **Contrast** | [NEEDS_PROFILING] | Variable lighting conditions |
| **Compression** | [NEEDS_PROFILING] | JPEG artifacts present |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Small text in distant signs, larger text in close-up shots |
| **Font Diversity** | High | Natural scene fonts (signage, storefronts) |
| **Background Complexity** | High | Storefronts, signs, natural scenes, busy backgrounds |
| **Script Mixing** | Common | Multiple scripts per full scene image |
| **Perspective Distortion** | Common | Camera angle effects, non-frontal captures |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Korean/Hangul differentiation from CJK |
| **Unique Characteristics** | 4-script coverage with Korean focus, scene text variability |
| **Complementary Datasets** | Combine with MLT19, CVSI, SIW13 for broader script coverage |
| **Benchmark Suitability** | HIGH - Standard script identification benchmark |
| **Known Limitations** | Only 4 scripts (limited compared to MLT19's 10 languages), small dataset (1,816 samples) |

##### 6.5 Benchmark Results

> **Purpose**: Document published model performance on mle2e.
> **Status**: [NEEDS_RESEARCH] - Check paper and citations for benchmark results.

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| TBD | Script Identification | F1 | TBD | [Paper arXiv:1602.07475](https://arxiv.org/abs/1602.07475) |

**Competition Results**: N/A (research dataset, not competition)

> **Action Required**: Review paper for baseline model performance metrics.

---

#### 7. Known Issues

> **Status**: [NEEDS_INVESTIGATION] - Known issues documented below.

| Issue | Severity | Impact | Workaround |
|-------|----------|--------|------------|
| **Local dataset missing full scene images** | Medium | Cannot extract bounding box annotations | Use pre-segmented crops for classification tasks only |
| **Test set transcriptions not integrated** | Low | Text statistics incomplete | Integrate separate transcription file into parser |
| **Small dataset size** | Low | Limited training diversity | Combine with MLT19, CVSI for broader coverage |
| **Latin-heavy distribution** | Low | Class imbalance in training set | Apply weighted sampling or augmentation |

> **Note**: Update this section after dataset processing and profiling.

---

#### 8. Citation

```bibtex
@article{gomez2016fine,
  title={A fine-grained approach to scene text script identification},
  author={Gomez, Lluis and Karatzas, Dimosthenis},
  journal={arXiv preprint arXiv:1602.07475},
  year={2016}
}
```

**Paper**: [A fine-grained approach to scene text script identification (arXiv:1602.07475)](https://arxiv.org/abs/1602.07475)

---

#### 9. Related Datasets

| Dataset | Relationship | Notes |
|---------|--------------|-------|
| **CVSI** | Similar task (10 scripts) | Video scene text, broader script coverage |
| **SIW13** | Similar task (13 scripts) | Scene word-level script identification |
| **MLT19** | Broader coverage (10 languages) | ICDAR 2019 multi-lingual text detection |
| **COCO-Text** | Scene text | Monolingual (English) but similar capture method |
| **MSRA-TD500** | Source dataset | Chinese and Latin text detection (source for mle2e) |
| **Chars74K** | Source dataset | Character recognition (source for mle2e) |

**Use Case**: Combine mle2e with CVSI and SIW13 for comprehensive script identification training.

---

#### 10. Dataset-Specific Notes

**Korean/Hangul Focus**:

- mle2e's primary contribution is Korean script (Hangul) representation
- Critical for CJK script disambiguation (Korean uses alphabet, not logograms)
- 4-class internal model benefits from Hangul vs Han distinction

**Scene Text Characteristics**:

- Natural variability in lighting, perspective, scale
- Multi-script images common in full scene images (bilingual signs)
- Ground truth transcriptions are OPTIONAL (test set only)

**Processing Notes**:

- **Current local dataset**: Pre-segmented text line crops only (no bounding boxes)
- **Full scene images**: Original dataset has bbox annotations, but not in current local copy
- Parser currently extracts language/script codes from directory structure
- Text transcriptions for test set exist but not yet integrated into parser

**Training Integration**:

- Phase 10B: Script Detection (4-class CJK internal model)
- Combine with other script datasets for balanced training
- 1,816 samples is relatively small - augmentation recommended
- Pre-segmented format ideal for text line classification (no detection stage needed)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 1,816 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 1,816 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `has_table` | 100.0% | 0.000 |
