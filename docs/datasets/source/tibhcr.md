#### TibHCR (Tibetan Handwritten Character Recognition)

> **Quick Stats**: 141,698 samples | 235 writers | 47 character classes | Handwritten
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Tibetan Handwritten Character Recognition Dataset |
| **Version** | 2025 |
| **HuggingFace** | [qixiaoke/TibHCR](https://huggingface.co/datasets/qixiaoke/TibHCR) |
| **Paper** | [ResearchGate](https://www.researchgate.net/publication/393179332) |
| **License** | Academic |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | 141,698 handwritten character samples |
| **Annotations** | TXT (label.txt) | CSV-like file with Tibetan Unicode characters |
| **Metadata** | None | No additional metadata files |

##### 2.2 Dataset Split Locations

**Split Organization Pattern**: `single_dir_with_category` (NO official splits)

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **All Data** | `TibHCR/{Category}/{Class}/` | `label.txt` | 141,698 | ✅ |
| **Train** | - | - | - | ❌ Not provided |
| **Validation** | - | - | - | ❌ Not provided |
| **Test** | - | - | - | ❌ Not provided |

> **Note**: Dataset has no official splits. Users must create custom train/val/test splits (suggested: 80/10/10 stratified by character class).

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Character Class** | Directory structure | Character-level | 47 classes (30 consonants, 4 vowels, 10 numerals, 3 punctuation) |
| **Tibetan Unicode** | TXT (label.txt) | Character-level | Ground truth Tibetan characters |
| **Writer ID** | Embedded in filename | Sample-level | Writer identifier (not documented) |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace README | Overview, citation, license |
| **Image-level** | Filename | Writer ID, sample number |
| **Annotation-level** | label.txt | Tibetan Unicode character |

##### 2.5 Annotation Schema Details

**Format**: CSV-like text file (label.txt)

```text
{relative_path}, "{tibetan_unicode_character}"

Example:
Consonants/0/0_0001.jpg, "ཀ"
Vowels/1/1_0042.jpg, "◌ི"
Numerals/3/3_0089.jpg, "༣"
```

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Character class | `transcription` | High | From directory structure |
| ✅ Tibetan Unicode | `text_content.full_text` | High | From label.txt (not yet extracted) |
| ✅ Writer ID | `provenance.source_id` | Medium | From filename pattern |
| ✅ Category type | `raw_labels.category` | Medium | Consonants/Vowels/Numerals/Punctuation |
| ❌ Image quality | - | Low | Not provided |

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | 235 Tibetan writers |
| **Quality Assurance** | Character-level collection with writer tracking |
| **GT Label Coverage** | 100% |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 141,698 |
| **Writers** | 235 (from 5 Chinese provinces) |
| **Character Classes** | 47 (30 consonants, 4 vowels, 10 numerals, 3 punctuation) |
| **Total Size** | 1.1 GB |
| **File Format** | JPG |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Handwritten characters (isolated) |
| **Key Value** | **Only large-scale Tibetan source** |
| **Limitation** | Character-level (not document-level) |
| **Usage Strategy** | Synthetic document generation from characters |

##### Project Usage

- **Path**: `01_base_data/language/huggingface_downloads/TibHCR/`
- **Images Path**: `01_base_data/language/huggingface_downloads/TibHCR/TibHCR/` ✅ 141,698 JPG images
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Tibetan script class via synthetic generation
- **Note**: Combine with Bhutan docs (198 real images) + synthetic compositing
- **Parser**: [`parse_tibhcr_labels`](../scripts/annotate_base_metadata.py#L2211) | ✅ Complete
- **Conversion**: ✅ Extracted from `TibHCR.zip` (865 MB) → 141,698 JPG images

---

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/huggingface_downloads/TibHCR/` | ✅ Available | 141,698 PNG files |
| **Text/GT** | Native annotations | ⚠️ Partial | TXT (CSV): Tibetan Unicode character labels (`label.txt`) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/tibhcr/` | ✅ Available | Docling GPU: 284 layout batches, 141,698 images |
| **Layer 2 Metadata** | `metadata_registry/json/tibhcr_metadata.json` | ✅ Complete | 141,698 samples (2026-02-09) |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (91.7/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.0 | 20% |  |
| Field Validity | 100.0 | 20% |  |
| Doc Completeness | 54.5 | 7% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **91.7** | | **Grade B** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 95.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/tibhcr/](../../scripts/audit/results/tibhcr/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 141,698 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 141,698 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~5,000 | Synthetic | Orientation derivable only via synthetic document compositing; character-level images have no meaningful page orientation |
| MNV4-H2 | skew_reg | ❌ Not applicable | 0 | — | Isolated characters; no document baseline for skew measurement |
| MNV4-H3 | resolution_quality_reg | ❌ Not applicable | 0 | — | Character images lack document context required for resolution quality scoring |
| SIG-G1-1 | blur_score | ➖ Negatives only | ~5,000 | Derived | Clean scanner captures provide clean reference examples; no blur variation present |
| SIG-G1-2 | noise_score | ➖ Negatives only | ~5,000 | Derived | Flatbed scans are low-noise; useful as clean-class anchor |
| SIG-G1-3 | contrast_score | ➖ Negatives only | ~5,000 | Derived | High-contrast black-on-white characters; useful as high-contrast anchor |
| SIG-G1-4 | skew_score | ❌ Not applicable | 0 | — | No document layout to assess skew quality against |
| SIG-G1-5 | compression_score | ➖ Negatives only | ~5,000 | Derived | JPG format but flatbed scans at consistent quality; minimal compression artifacts |
| SIG-G1-6 | overall_quality | ❌ Not applicable | 0 | — | Character-level images do not map to document overall quality; SRCC requirement cannot be met |
| SIG-G2-1 | script_cls | ✅ Primary | ~50,000 | Hard label | 141,698 Tibetan (Tibt) character images — primary and sole large-scale Tibt source in training corpus; synthetic document compositing bridges character to document-level |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~5,000 | Synthetic | Same synthetic compositing path as MNV4-H1; post-correction orientation labels derivable |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | 0 | — | No document geometry; residual skew not applicable |
| SIG-G4-1 | handwriting_presence_cls | ✅ Primary | ~50,000 | Hard label | 100% handwritten; all 141,698 images contribute DOMINANT class examples |
| SIG-G4-2 | handwriting_legibility_cls | ✅ Primary | ~50,000 | Hard label | 235 writers, 47 classes; high character variation provides legibility range; labeled via writer-quality proxies |
| SIG-G4-3 | handwriting_content_type_cls | ✅ Primary | ~50,000 | Hard label | 100% PRINTED (block Tibetan characters — isolated consonants, vowels, numerals); no cursive in Tibetan script tradition |
| SIG-G4-4 | presence_reg | ✅ Primary | ~50,000 | Derived | Continuous presence score = 1.0 (DOMINANT); contributes high-end of presence regression range |
| SIG-G4-5 | legibility_reg | ✅ Primary | ~50,000 | Derived | Writer-level legibility variation provides continuous score distribution |
| SIG-G5-1 | capture_method_cls | ✅ Primary | ~50,000 | Hard label | scanner_flatbed (100%); 141,698 samples — significant scanner class contribution |
| SIG-G5-2 | shadow_reg | ❌ Not applicable | 0 | — | No shadow variation in flatbed scans; character-level images not suitable |
| SIG-G5-3 | warping_reg | ❌ Not applicable | 0 | — | No warping in flatbed scanner captures |
| SIG-G5-4 | code_cls | ❌ Not applicable | 0 | — | No code content; Tibetan handwritten characters only |
| SIG-G5-5 | resolution_quality_reg | ❌ Not applicable | 0 | — | Character-level images; no document-level resolution quality context |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ Well-covered | 100% Tibetan (Tibt) / indic family; sole large-scale Tibt source; 47 character classes |
| 2 | Capture method | ✅ Well-covered | 100% scanner_flatbed; contributes dedicated scanner class signal |
| 3 | Document domain | 🟡 Partial | 100% EDU; single domain; no financial, legal, or scientific content |
| 4 | Layout type | ❌ Not present | Isolated character images; no document layout (single character fills canvas) |
| 5 | Text density | ❌ Not present | Single-character images; text density concept not applicable at character level |
| 6 | Degradation types | ❌ Not present | Clean flatbed scans; no degradation variation; quality_scores array is empty |
| 7 | Resolution/DPI range | ❌ Not present | Consistent flatbed scan resolution; no DPI range variation |
| 8 | Document age | ❌ Not present | Contemporary collection (2025); no aged or historical documents |
| 9 | Text scope | 🟡 Partial | 100% character-level scope; no word, line, or document-level coverage |
| 10 | Content flags | 🟡 Partial | has_handwriting=100%; no tables, figures, formulas, or code |
| 11 | Binarization status | ❌ Not present | No binarized variants; JPG color scans only |
| 12 | Artifact types | ❌ Not present | No artifacts documented; clean scanner captures |
| 13 | Color mode | 🟡 Partial | JPG scans (color/grayscale scanner output); no explicit color_mode field populated |
| 14 | Font variety | ✅ Well-covered | 235 writers across 5 Chinese provinces; high natural handwriting variation across 47 character classes |

### 13.3 Corpus Role & Constraints

TibHCR is the **sole large-scale Tibetan (Tibt) script source** in the training corpus, making it indispensable for SIG-G2-1 script classification and G4 handwriting heads despite being character-level rather than document-level. Academic license restricts use to research only, excluding commercial deployment pipelines. Direct use in document-level heads (MNV4-H1, IQA, skew) requires synthetic document compositing — individual characters must be assembled into simulated document pages before contributing orientation or quality training signal.
