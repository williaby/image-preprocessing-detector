---
dataset_id: egyptian-handwriting
version: "1.0"
license: CC-BY-4.0
commercial_use: true
iqa_profiles:
  - blur_sensitive
  - contrast_variable
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### Egyptian Handwriting Dataset

> **Quick Stats**: 11,216 word images | Scanner (flatbed) | Arabic cursive | 89 writers (ages 6-73) | CC-BY-4.0
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Egyptian Handwriting Dataset |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | Omar M. Diab |
| **Repository** | [HuggingFace: OmarMDiab/Egyptian-Handwriting-Dataset](https://huggingface.co/datasets/OmarMDiab/Egyptian-Handwriting-Dataset) |
| **License** | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Commercial Use** | Yes |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | Embedded in Parquet (binary blob) | 11,216 word-level handwriting images |
| **Labels** | Parquet column (`label`) | Arabic text transcription for each word |

##### 2.2 Dataset Split Locations

> **Split Organization**: Single parquet file containing all samples. No official train/test/val splits.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **All** | `data/*.parquet` | Inline (label column) | 11,216 | ✅ Available |

**Split Organization Pattern**: `single_file` (all data in one parquet file)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | Parquet column | Word-level | Arabic word labels (ground truth text) |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace card | Writer count (89), age range (6-73), license |
| **Image-level** | Parquet row index | Sequential index (0-11,215) |

##### 2.5 Annotation Schema Details

**Parquet Format** (Apache Arrow):

```text
Schema:
  image: binary (PIL Image serialized)
  label: string (Arabic word transcription)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image` | binary | Yes | PIL-serialized image data |
| `label` | string | Yes | Arabic word transcription (UTF-8) |
| Row index | int | Yes | Implicit (0-based parquet row number) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Word transcriptions | `text_content` | **High** | Label column in parquet, direct extraction |
| ✅ Image data | `image_path` | **High** | Binary blobs, extract to individual files if needed |
| ❌ Writer ID | - | **Low** | Not provided per-image |
| ❌ Quality scores | - | **Low** | Not provided |
| ❌ Bounding boxes | - | **Low** | Word-level crops, no bounding boxes |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | 89 writers (ages 6-73), Egyptian Arabic native speakers |
| **Quality Assurance** | [NEEDS_VERIFICATION] |
| **GT Label Coverage** | 100% (every image has a word label) |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | SigLIP 2 multi-task training (handwriting heads) |
| **Purpose** | Training: Arabic cursive handwriting detection, script detection |
| **Local Path** | `01_base_data/handwriting/egyptian-handwriting/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Parquet extraction to individual images (if needed) |

##### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`EgyptianHandwritingParser`](../../../src/image_preprocessing_detector/annotation/parsers/handwriting/egyptian_handwriting.py) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `text_content`, `language_code`, `script_name`, `iso15924_script_code` |
| **Layer 2 Auto-Derived** | `has_handwriting=True`, `script_family=Arab`, `iso639_language=ar` |
| **Config Entry** | `DATASET_CONFIGS["egyptian-handwriting"]` |

##### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/egyptian-handwriting/` | ✅ Available | Parquet format (11,216 word images) |
| **Text/GT** | Inline (parquet label column) | ✅ Available | Arabic word transcriptions |
| **Layer 2 Metadata** | - | ❌ Not generated | Pending Layer 2 annotation pipeline |

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **Note**: No official train/test/val splits. All samples in single parquet file.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **All** | 11,216 | 0 | 0% | ❌ Pending Layer 2 |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 11,216 |
| **Writers** | 89 (ages 6-73) |
| **File Format(s)** | Parquet (binary image + string label) |
| **Total Size on Disk** | 121 MB (parquet) |
| **Text Scope** | Word-level |
| **Language** | Arabic (Egyptian dialect) |

##### 4.3 Text Statistics

> **Source**: [NEEDS_PROFILING] - Word labels available in parquet
>
> **Availability**: ✅ Available (pending profiling)

| Metric | Mean +/- Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Character Count** | [NEEDS_PROFILING] | - | - | - |
| **Word Count** | 1 (word-level) | 1 | 1 | 1 / 1 / 1 |

**Text Source**: `ground_truth` (human transcriptions)

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Personal / Educational |
| **Document Types** | Individual word images (handwriting samples) |
| **Language(s)** | Arabic (100%) - Egyptian dialect |
| **Script** | Arabic (cursive) |
| **Writer Demographics** | 89 writers, ages 6-73, Egyptian |
| **Acquisition Method** | Flatbed scanning of handwritten word sheets |

##### 5.1 Writer Distribution

| Aspect | Value |
|--------|-------|
| **Total Writers** | 89 |
| **Age Range** | 6-73 years |
| **Nationality** | Egyptian |
| **Writing Style** | Cursive Arabic |

##### 5.3 Language & Script Coverage

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Arabic | Arab / ar | 11,216 | 100% | Egyptian Arabic cursive handwriting |

**Script Families Present**: Arabic (Semitic)

**Script Characteristics**:

- **Direction**: Right-to-left (RTL)
- **Style**: Cursive (connected letters)
- **Complexity**: High - contextual letter forms, diacritics
- **Writer Variation**: Large (89 writers spanning 67-year age range)

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Scanned handwriting sheets |
| **Capture Device** | Flatbed scanner |
| **Original Quality** | Variable (child to adult writing, different pens/pencils) |
| **Compression** | Stored as parquet binary blobs |
| **Known Artifacts** | Pen pressure variation, paper texture, scanning noise |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Fine Arabic cursive strokes sensitive to blur |
| **Noise** | MEDIUM | Scanner noise on paper backgrounds |
| **Contrast** | MEDIUM | Variable ink/pencil darkness across writers |
| **Compression** | LOW | Original quality preserved in parquet |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Only commercial-viable Arabic HW source; large writer diversity |
| **Unique Characteristics** | 89-writer diversity (ages 6-73), word-level crops, Egyptian Arabic |
| **Complementary Datasets** | Muharaf (Arabic historical), Lamtougui (Arabic cursive), KHATT |
| **Benchmark Suitability** | MEDIUM - No official splits, but large enough for custom benchmarks |
| **Known Limitations** | Word-level only (no line/page), no writer ID per image, Egyptian dialect |

#### 7. Known Issues & Limitations

- **Word-Level Only**: Individual word crops, not lines or pages
- **No Writer ID**: Per-image writer identity not provided in parquet
- **No Quality Labels**: No IQA or legibility scores provided
- **Single Language**: Arabic only (Egyptian dialect)
- **Parquet Format**: Images stored as binary blobs require special extraction

#### 9. References

##### Primary Citation

> Dataset published on HuggingFace by OmarMDiab. No associated paper found.

##### Related Works

- [Muharaf](muharaf.md) - Arabic historical handwriting (non-commercial)
- [KHATT](khatt.md) - Arabic handwriting corpus (research-only)

#### 10. Dataset-Specific Notes

##### 10.1 Parquet Extraction

Images are stored as binary blobs in parquet format. The parser extracts labels
from the parquet metadata without rendering images. For training, images can be
extracted to individual files using pyarrow:

```python
import pyarrow.parquet as pq
table = pq.read_table("data/train-00000-of-00001.parquet")
for i in range(len(table)):
    img_bytes = table["image"][i].as_py()["bytes"]
    # Save or process image bytes
```

##### 10.2 Gap Closure

This dataset closes the Arabic cursive handwriting gap (SIG-G4-*):

- **Before**: No commercially-viable Arabic handwriting source
- **After**: 11,216 word images from 89 writers under CC-BY-4.0
- **Heads Served**: SIG-G2-1 (script_cls), SIG-G4-1 through SIG-G4-5 (all handwriting heads)

---

#### 13. Training Head Coverage

##### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ | -- | N/A | Word crops, no orientation labels |
| MNV4-H2 | skew_reg | ❌ | -- | N/A | No skew angle labels |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~11,216 | tier_3_heuristic | Scanner-captured; quality varies by writer |
| SIG-G1-1 | blur_score | 🟡 | ~11,216 | tier_3_heuristic | Variable pen pressure creates blur variation |
| SIG-G1-2 | noise_score | ❌ | -- | N/A | Clean scanner captures, minimal noise variation |
| SIG-G1-3 | contrast_score | 🟡 | ~11,216 | tier_3_heuristic | Ink/pencil darkness varies across writers |
| SIG-G1-4 | skew_score | ❌ | -- | N/A | No skew quality labels |
| SIG-G1-5 | compression_score | ❌ | -- | N/A | Lossless parquet storage |
| SIG-G1-6 | overall_quality | 🟡 | ~11,216 | tier_3_heuristic | Writer quality range (child to adult) |
| SIG-G2-1 | script_cls | ✅ | ~11,216 | tier_1_annotation | 100% Arab (ISO 15924); CC-BY-4.0 allows commercial training |
| SIG-G3-1 | orientation_cls (post) | ❌ | -- | N/A | No orientation labels |
| SIG-G3-2 | skew_reg (post) | ❌ | -- | N/A | No skew labels |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~11,216 | tier_1_annotation | 100% handwritten; word-level cursive Arabic |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~11,216 | tier_3_heuristic | Variable legibility (child vs adult writing); no explicit labels |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | ~11,216 | tier_1_annotation | 100% cursive Arabic handwriting; CURSIVE class |
| SIG-G4-4 | presence_reg | ✅ | ~11,216 | derived | Word crops are 100% handwriting; area ratio = 1.0 |
| SIG-G4-5 | legibility_reg | 🟡 | ~11,216 | tier_3_heuristic | Legibility derivable from writer age/quality range |
| SIG-G5-1 | capture_method_cls | ✅ | ~11,216 | tier_1_annotation | 100% flatbed scanner; SCANNER class |
| SIG-G5-2 | shadow_reg | ❌ | -- | N/A | Flatbed scanner; no shadow artifacts |
| SIG-G5-3 | warping_reg | ❌ | -- | N/A | Flat paper on scanner; no warping |
| SIG-G5-4 | code_cls | ❌ | -- | N/A | Handwriting only; no code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~11,216 | tier_3_heuristic | Scanner quality; pending IQA pipeline |

##### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | ARAB only (100%); excellent Arabic representative |
| 2 | Capture method | ✅ | Flatbed scanner (100%) |
| 3 | Document domain | 🟡 | Personal/educational (handwriting samples) |
| 4 | Layout type | ❌ | Word-level crops only; no page/document layout |
| 5 | Text density | 🟡 | Single word per image; high within-crop density |
| 6 | Degradation types | 🟡 | Pen pressure variation, paper texture; minimal scanner degradation |
| 7 | Resolution/DPI range | 🟡 | Scanner resolution; unquantified |
| 8 | Document age | ❌ | Modern (contemporary writers) |
| 9 | Text scope | 🟡 | Word-level only |
| 10 | Content flags | ✅ | has_handwriting=100% |
| 11 | Binarization status | 🟡 | Color/grayscale (not binarized) |
| 12 | Artifact types | 🟡 | Pen pressure, paper texture; minimal scanner artifacts |
| 13 | Color mode | 🟡 | Color scans |
| 14 | Font variety | ❌ | Handwriting only; 89-writer cursive style variation |

##### 13.3 Corpus Role & Constraints

Egyptian Handwriting is the only commercially-viable Arabic cursive handwriting source (CC-BY-4.0),
providing 11,216 word-level images from 89 writers spanning ages 6-73. It serves as the primary
Arabic contributor to SIG-G2-1 (script detection) and all five SIG-G4 handwriting heads. The wide
writer age range provides natural legibility variation suitable for handwriting quality assessment.
No license restrictions for commercial model training.
