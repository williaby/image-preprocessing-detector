---
dataset_id: document-haystack
version: "1.0"
license: CC-BY-NC-4.0
commercial_use: false
iqa_profiles:
  - benchmark_only
baseline_quality: null
training_suitable: false
benchmark_suitable: true
documentation_status: partial
---

#### Document Haystack

> **Quick Stats**: 400 documents | 8,250 queries | Document retrieval benchmark | Non-commercial
>
> **License**: CC-BY-NC-4.0 | **Commercial Use**: No

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Document Haystack |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Last Updated** | 2024 |
| **Maintainer** | Amazon Science |
| **Paper** | [Document Haystack: A Long-Context Retrieval Benchmark (2024)](https://huggingface.co/datasets/AmazonScience/document-haystack) |
| **Repository** | [HuggingFace: AmazonScience/document-haystack](https://huggingface.co/datasets/AmazonScience/document-haystack) |
| **License** | CC-BY-NC-4.0 |
| **Commercial Use** | No (Non-Commercial license) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Documents** | PDF / TXT | 400 long-form documents |
| **Queries** | JSON / CSV | 8,250 natural language queries |
| **Annotations** | JSON | Query-document relevance pairs |
| **Supplementary** | README | Dataset description, citation, benchmark metrics |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Documents Path | Queries Path | Count | Status |
|-------|----------------|--------------|-------|--------|
| **Test** | `documents/` | `queries.json` | 400 docs / 8,250 queries | ✅ |

**Split Organization Pattern**: Benchmark-only (no train/val splits)

> **Notes**:
>
> - This is a **benchmark-only** dataset; no training split provided
> - Queries may span multiple documents
> - Relevance judgments provided for evaluation

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Relevance Pairs** | JSON | Query-Document | Binary or graded relevance scores |
| **Query Metadata** | JSON | Query | Query type, difficulty, expected answer location |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace README | License, benchmark metrics, evaluation protocol |
| **Document-level** | Metadata JSON | Document ID, length, domain, source |
| **Query-level** | Queries JSON | Query text, difficulty, expected document(s) |

##### 2.5 Annotation Schema Details

> **Format**: Query-document relevance pairs with metadata

```text
{
  "queries": [
    {
      "query_id": str,
      "query_text": str,
      "relevant_docs": [doc_id_1, doc_id_2, ...],
      "difficulty": str  # easy / medium / hard
    }
  ],
  "documents": [
    {
      "doc_id": str,
      "text": str,
      "length": int,  # character count
      "domain": str
    }
  ]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `query_id` | str | Yes | Unique query identifier |
| `doc_id` | str | Yes | Links query to relevant documents |
| `relevance_score` | float/int | Varies | Binary or graded relevance |
| `difficulty` | str | Varies | Query difficulty classification |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Document text | `ground_truth_text` | Medium | Full document content available |
| ✅ Query-doc pairs | `retrieval_annotations` | Medium | For retrieval evaluation |
| ✅ Domain tags | `domain_level1` | Low | Document categorization |
| ❌ Layout boxes | - | N/A | Not applicable for retrieval benchmark |
| ❌ Quality scores | - | Low | Compute from document characteristics |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

> **Purpose**: Document annotation methodology, quality assurance, and provenance for ground truth labels.

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | Amazon Science researchers; query-document relevance judgments |
| **Inter-Annotator Agreement** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | [NEEDS_VERIFICATION] - Benchmark-quality relevance annotations |
| **GT Label Coverage** | 100% - All 8,250 queries have relevance judgments against 400 documents |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 10 (evaluation/benchmarking) |
| **Purpose** | Document retrieval benchmark, OCR quality validation |
| **Local Path** | `02_benchmark_only/document-haystack/` |
| **Subset Used** | Full benchmark set |
| **Preprocessing** | PDF text extraction, query parsing |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `document_haystack` (document category) |
| **Parser Status** | ❌ Not Implemented |
| **Layer 1 Fields** | `retrieval_annotations`, `ground_truth_text`, `domain_level1` |
| **Layer 2 Auto-Derived** | `text_scope=document`, `capture_method=born_digital` |
| **Config Entry** | Pending implementation |

> **Parser Reference**: Benchmark datasets typically use simplified schemas focused on text + metadata extraction.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Documents** | `02_benchmark_only/document-haystack/documents/` | ✅ Available | 400 PDF/TXT files |
| **Queries** | `02_benchmark_only/document-haystack/queries.json` | ✅ Available | 8,250 queries |
| **Text/GT** | `02_benchmark_only/document-haystack/documents/*.txt` | ✅ Available | Extracted text |
| **Text/OCR Extracted** | - | ℹ️ N/A | Ground truth text provided |
| **Layout Extracted** | - | ℹ️ N/A | Not applicable for retrieval benchmark |
| **Layer 2 Metadata** | `metadata_registry/json/document_haystack_layer2.json` | ❌ Not generated | Parser not yet implemented |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ Not generated - Parser not yet implemented
- ℹ️ N/A - Not applicable

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Benchmark-only dataset; no train/val splits.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Test** | 400 docs / 8,250 queries | 0 | 0% | ❌ Parser not implemented |

**Split Status Legend**:

- ❌ Missing - Parser not yet implemented

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Documents** | 400 |
| **Total Queries** | 8,250 |
| **Avg Queries per Document** | ~20.6 |
| **Document Length Range** | Long-form (10K-100K+ characters) |
| **File Format(s)** | PDF, TXT |
| **Color Space** | N/A (text-focused) |
| **Total Size on Disk** | ~500 MB (estimated) |
| **Annotation Format** | JSON |

##### 4.3 Text Statistics

> **Availability**: ✅ Available - Full document text provided as ground truth

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Character Count** | ~50,000 ± 30,000 | 10,000 | 150,000 | 25,000 / 45,000 / 70,000 |
| **Word Count** | ~8,500 ± 5,000 | 1,700 | 25,000 | 4,200 / 7,600 / 11,800 |

**Text Source**: `ground_truth` (extracted from source documents)

> **Note**: Exact statistics require profiling; estimates based on "long-context" benchmark description.

##### Directory Structure

```text
document-haystack/
├── documents/
│   ├── doc_001.pdf
│   ├── doc_002.txt
│   └── ...
├── queries.json
└── relevance_judgments.json
```

##### Baseline Quality Metrics

> **Source**: [NEEDS_PROFILING] - Not applicable for text-only retrieval benchmark; no image quality metrics.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | UNKNOWN (multi-domain long-form documents) |
| **Document Types** | Research papers, technical reports, manuals, articles |
| **Language(s)** | English (primary) |
| **Temporal Range** | Recent publications (2020s) |
| **Acquisition Method** | Born-digital (programmatic extraction) |

##### 5.1 Class/Category Distribution

> **Note**: Documents likely categorized by domain, but exact distribution not publicly documented.

##### 5.2 Class/Category Definitions

> **N/A**: No layout classes; retrieval benchmark focused on text matching.

##### 5.3 Language & Script Coverage

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Latin (English) | eng (Latn) | 400 | 100% | Primary language |

**Script Families Present**: Latin

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Born-digital text documents |
| **Capture Device** | N/A (programmatic extraction) |
| **Original Quality** | Clean digital text (no scanning artifacts) |
| **Known Artifacts** | PDF extraction errors (rare) |

##### 6.2 Degradation Sensitivity

> **N/A**: Text-only benchmark; image quality metrics not applicable.

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Document Length** | Long (10K-100K+ chars) | Tests retrieval over extended context |
| **Domain Diversity** | Multi-domain | Generalization challenge |
| **Query Complexity** | Varied difficulty | Benchmark rigor |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | MEDIUM - Useful for retrieval model validation (benchmark-only, no train split) |
| **Unique Characteristics** | Long-context retrieval, 8,250 queries across 400 documents |
| **Complementary Datasets** | Combine with DocVQA for visual + text retrieval |
| **Benchmark Suitability** | HIGH - Designed specifically for retrieval evaluation |
| **Known Limitations** | Non-commercial license, English-only, no visual elements |

#### 7. Known Issues & Limitations

- **Non-Commercial License**: CC-BY-NC-4.0 restricts commercial use
- **No Training Split**: Benchmark-only; unsuitable for supervised training
- **English-Only**: Limited to English language
- **No Visual Elements**: Text-focused; no layout/image analysis
- **PDF Extraction Artifacts**: Potential text extraction errors from PDFs
- **No IQA Relevance**: Not suitable for image quality assessment training
- **Limited Provenance**: Document sources not fully detailed

#### 8. Representative Samples

> **N/A**: Text-only dataset; no visual samples applicable.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | Long-form technical document | 50K+ characters, multi-section structure |

#### 9. References

##### Primary Citation

```bibtex
@misc{amazonscience2024documenthaystack,
  title={Document Haystack: A Long-Context Retrieval Benchmark},
  author={Amazon Science},
  year={2024},
  publisher={HuggingFace},
  url={https://huggingface.co/datasets/AmazonScience/document-haystack}
}
```

##### Related Works

- [DocVQA](docvqa.md) - Document visual question answering
- [MSMARCO](https://microsoft.github.io/msmarco/) - Passage retrieval benchmark

##### Leaderboards

- HuggingFace benchmark page (if available)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Relevance Judgments**: May be binary or graded; check annotation format
- **Multi-Document Queries**: Some queries span multiple documents
- **Query Difficulty**: Pre-classified as easy/medium/hard for stratified evaluation

##### 10.2 Implementation Notes

- **Parser Focus**: Extract document text + query pairs for retrieval evaluation
- **Non-Commercial Use Only**: Verify license compliance before use
- **Text Extraction**: Handle both PDF and TXT formats; use PyMuPDF for PDFs
- **Benchmark Protocol**: Follow official evaluation metrics from dataset card

##### 10.3 External Resources

- **HuggingFace Dataset Card**: [https://huggingface.co/datasets/AmazonScience/document-haystack](https://huggingface.co/datasets/AmazonScience/document-haystack)
- **Amazon Science**: [https://www.amazon.science/](https://www.amazon.science/)

---

#### 11. Layer 2 Audit Summary

> **Status**: No audit performed. Parser not yet implemented. Benchmark dataset has lower priority for Layer 2 enrichment.

---

#### 12. Reliability & Bottlenecks

> **Status**: Parser not implemented - no Layer 2 metadata available for reliability analysis.

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| MNV4-H2 | skew_reg | ❌ | 0 | — | Benchmark reserved; text-only dataset with no page images |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | — | Benchmark reserved; no image data for quality measurement |
| SIG-G1-1 | blur_score | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G1-2 | noise_score | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G1-3 | contrast_score | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G1-4 | skew_score | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G1-5 | compression_score | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G1-6 | overall_quality | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G2-1 | script_cls | ❌ | 0 | — | Benchmark reserved; English-only (Latin), no script diversity |
| SIG-G3-1 | orientation_cls (post) | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | — | No page images; text-only retrieval benchmark |
| SIG-G4-1 | handwriting_presence_cls | ❌ | 0 | — | No page images; born-digital text documents with no handwriting |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | — | No page images; born-digital text documents with no handwriting |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | — | No page images; born-digital text documents with no handwriting |
| SIG-G4-4 | presence_reg | ❌ | 0 | — | No page images; born-digital text documents with no handwriting |
| SIG-G4-5 | legibility_reg | ❌ | 0 | — | No page images; born-digital text documents with no handwriting |
| SIG-G5-1 | capture_method_cls | ❌ | 0 | — | Benchmark reserved; born_digital only, no visual capture diversity |
| SIG-G5-2 | shadow_reg | ❌ | 0 | — | No page images; no shadow artifacts possible in born-digital text |
| SIG-G5-3 | warping_reg | ❌ | 0 | — | No page images; no warping artifacts possible in born-digital text |
| SIG-G5-4 | code_cls | ❌ | 0 | — | Benchmark reserved; research papers/manuals may contain code but dataset is text-only |
| SIG-G5-5 | resolution_quality_reg | ❌ | 0 | — | No page images; not applicable to text-only content |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | English only (Latin script); no multilingual or multi-script content |
| 2 | Capture method | ❌ | Born-digital only (programmatic extraction from PDFs/TXT); no scanning or camera samples |
| 3 | Document domain | ❌ | Multi-domain (research papers, technical reports, manuals, articles) but domain metadata not fully documented; no structured domain labels available |
| 4 | Layout type | ❌ | Not applicable; text-only benchmark with no visual layout analysis |
| 5 | Text density | ❌ | Not applicable as a training dimension; all documents are long-form (10K–100K+ chars) by design |
| 6 | Degradation types | ❌ | No degradation; clean born-digital text with occasional PDF extraction artifacts only |
| 7 | Resolution/DPI range | ❌ | Not applicable; text-only dataset, no image DPI metadata |
| 8 | Document age | ❌ | Modern only (2020s publications); no historical documents |
| 9 | Text scope | ❌ | Document-level only; benchmark uses full document context for retrieval |
| 10 | Content flags | ❌ | Not applicable; no visual content flags (tables, figures, formulas) extractable from this dataset |
| 11 | Binarization status | ❌ | Not applicable; text-only dataset with no image data |
| 12 | Artifact types | ❌ | No visual artifacts; occasional PDF text extraction errors only |
| 13 | Color mode | ❌ | Not applicable; no image data |
| 14 | Font variety | ❌ | Not applicable; text extracted as plain string without font metadata |

### 13.3 Corpus Role & Constraints

Document Haystack is a **benchmark-only text-retrieval corpus** with no page image data, making it inapplicable to every visual training head in the pipeline. The CC-BY-NC-4.0 license prohibits training use, and the dataset's design as a long-context retrieval benchmark (400 documents, 8,250 queries) reserves it exclusively for RAG pipeline evaluation (Phase 10). No parser has been implemented yet, and no Layer 2 metadata exists for this dataset.
