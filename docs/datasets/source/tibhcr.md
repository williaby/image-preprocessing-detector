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

> **Audit Date**: 2026-02-14 | **Grade**: B (84.5/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.3 | 33% |  |
| Field Validity | 100.0 | 33% |  |
| Doc Completeness | 45.5 | 20% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 95.0 | 13% |  |
| **Overall** | **84.5** | | **Grade B** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/tibhcr/](../../scripts/audit/results/tibhcr/)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 141,698 | **Avg Min Confidence**: 0.000

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
