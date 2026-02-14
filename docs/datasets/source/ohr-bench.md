---
dataset_id: ohr-bench
version: "1.0"
license: CC-BY-4.0
commercial_use: false
iqa_profiles:
  - born_digital
  - high_baseline_quality
baseline_quality: 9.5
training_suitable: false
benchmark_suitable: true
documentation_status: complete
---

### OHR-Bench

> **Quick Stats**: 8,561 PDF pages | 7 domains | 8,498 Q&As | OCR impact on RAG benchmark | ICCV 2025
>
> **License**: CC-BY-4.0 | **Commercial Use**: Research only

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | OHR-Bench: OCR Hinders RAG Benchmark |
| **Version** | 1.0 |
| **Release Date** | 2024-12-02 |
| **Last Updated** | 2026-02-14 |
| **Maintainer** | OpenDataLab |
| **Paper** | [arXiv:2412.02592](https://arxiv.org/abs/2412.02592) (ICCV 2025) |
| **Repository** | [GitHub: opendatalab/OHR-Bench](https://github.com/opendatalab/OHR-Bench) |
| **License** | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Commercial Use** | No (Research only) |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Extracted PDF pages at 300 DPI |
| **Source PDFs** | PDF | 1,261 original unstructured PDFs |
| **Annotations** | Parquet/Arrow | HuggingFace dataset with 17 columns |
| **Q&A Pairs** | JSON | 8,498 question-answer pairs (qas_v2.json) |
| **Supplementary** | JSON | Structured data variants (GT + noise levels) |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **All** | `02_benchmark_only/ohr-bench/extracted_images/` | HF dataset `opendatalab/OHR-Bench` | 8,561 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (no train/val/test splits)

> **Notes**:
>
> - All 8,561 pages are in a single "train" split in the HuggingFace dataset
> - NO official train/validation/test split exists in the source data
> - All images stored in single directory
> - Layer 2 metadata contains 8,303 samples (258 fewer due to missing textbook pages)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Ground Truth Text** | Parquet `gt_text` column | Page | Official structured data extracted from PDFs |
| **Domain Labels** | Parquet `domain` column | Document | 7 domain categories (Textbook, Law, Finance, etc.) |
| **Document Names** | Parquet `doc_name` column | Document | Document identifier (10-168 chars) |
| **Page Index** | Parquet `page_idx` column | Page | Page number (0-381 range) |
| **Q&A Pairs** | JSON | Document | 8,498 question-answer pairs with evidence |
| **OCR Noise Variants** | Parquet (12 columns) | Page | 3 engines × 3 levels + 3 formatting levels |

> **Note**: OCR noise variants are for research evaluation, not training labels.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / Paper | Version, license (CC-BY-4.0), citation, domains |
| **Image-level** | Parquet `page_idx` | Page number, document name |
| **Document-level** | Parquet `doc_name`, `domain` | Document ID, domain category |
| **Q&A-level** | qas_v2.json | Question, answer, evidence source, page number |

##### 2.5 Annotation Schema Details

> **Format**: HuggingFace Parquet with 17 columns

**Schema Structure**:

```text
- domain: Text (7 domain categories)
- doc_name: Text (document identifier, 10-168 chars)
- page_idx: Int32 (page number, 0-381 range)
- gt_text: Text (ground truth structured data, 0-11.7M chars)
- semantic_noise_GOT_mild/moderate/severe: Text (GOT OCR variants)
- semantic_noise_MinerU_mild/moderate/severe: Text (MinerU OCR variants)
- semantic_noise_Qwen2.5-VL_mild/moderate/severe: Text (Qwen2.5-VL variants)
- formatting_noise_mild/moderate/severe: Text (formatting variants)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `domain` | Text | Yes | 7 categories mapped to 5 standardized codes |
| `doc_name` | Text | Yes | Links pages to source document |
| `page_idx` | Int32 | Yes | Page sequence within document |
| `gt_text` | Text | Yes | Ground truth structured data |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Domain labels | `domain_level1` | High | 7 categories map to 5 standard codes |
| ✅ Text GT | `ground_truth_text` | High | Page-level structured data |
| ❌ Layout boxes | - | N/A | Use Docling GPU extraction |
| ❌ IQA scores | - | N/A | Born-digital baseline quality |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Benchmark dataset for IQA and OCR evaluation |
| **Purpose** | RAG pipeline evaluation - measures OCR quality impact on RAG |
| **Local Path** | `/mnt/e/image_detection/02_benchmark_only/ohr-bench/` |
| **GCS Path** | `gs://image_detection_b/image-preprocessing-detector/datasets/ohr_bench/` |
| **Subset Used** | Full dataset (all 8,561 pages) |
| **Preprocessing** | None required (born-digital extraction) |
| **Dataloader** | Not applicable (benchmark dataset) |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | No dedicated parser (uses `annotate_base_metadata.py` for enrichment) |
| **Parser Status** | ✅ Complete (enrichment v2 integrated) |
| **Layer 1 Fields** | `domain`, `doc_name`, `page_idx`, `gt_text` |
| **Layer 2 Auto-Derived** | `capture_method=BORN_DIGITAL`, `script_family`, `iso639_language`, `text_direction` |
| **Config Entry** | DATASET_CONFIGS["ohr-bench"] |

> **Parser Reference**: See integration script `scripts/integrate_ohr_bench_enrichments.py`.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/ohr-bench/` | ✅ Available | 8,303 extracted PNG pages |
| **Text/GT** | HuggingFace parquet `gt_text` | ✅ Available | Ground truth structured data |
| **Docling GPU Layout** | `metadata_registry/extracted/ohr-bench/` | ✅ Available | 7 layout batches (136,555 annotations, 14 categories) |
| **Docling GPU OCR** | `metadata_registry/extracted/ohr-bench/` | ✅ Available | 7 OCR batches (1,261 records) |
| **Language Detection** | OpenLID (1,000/8,259 records) + HF GT analysis (8,561 records) | ✅ Available | English 94.2%, Chinese 1.8%, Undetermined 3.7% |
| **Layer 2 Metadata** | `metadata_registry/json/ohr-bench_metadata.json` | ✅ Available | 8,303 samples, enrichment v2 |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed

#### 4. Dataset Statistics

> **Total**: 8,561 pages (HF) / 8,303 (Layer 2) across 7 domains, single split, 300 DPI PNG.

##### 4.1 Split Coverage

> **CRITICAL**: All samples are in a single split - no train/val/test division exists in source data.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **All** | 8,561 | 8,303 | 96.99% | ✅ Complete |

**Split Status Legend:**

- ✅ Complete - All available samples are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2

> **Note**: 258 samples (3.01%) missing from Layer 2 metadata - textbook pages not in metadata.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 8,561 (HF) / 8,303 (L2) |
| **Training Split** | N/A (no split) |
| **Validation Split** | N/A (no split) |
| **Test Split** | N/A (no split) |
| **Image Dimensions** | Variable (born-digital extraction) |
| **Resolution (DPI)** | 300 (uniform) |
| **File Format(s)** | PNG |
| **Color Space** | RGB |
| **Total Size on Disk** | ~2.2 GB |
| **Annotation Format** | Parquet (HF), JSON (Docling) |

##### 4.3 Text Statistics

> **Source**: Computed from HuggingFace ground truth text labels
> **Availability**: ✅ Available

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Text Content** | 99.9% have text | - | - | 8,292/8,303 pages |

**Text Source**: `ground_truth` (structured data from born-digital PDFs)

> **Note**: Detailed text statistics (word count, sentence count) not computed - focus is on OCR quality impact, not text composition.

##### 4.4 Domain Distribution

> **Source**: Computed from Layer 2 metadata (8,303 samples)

| Domain Code | Count | Percentage |
|-------------|-------|------------|
| **GOV** (administration+law) | 2,528 | 30.4% |
| **FIN** (finance) | 2,133 | 25.7% |
| **TEC** (manual) | 1,724 | 20.8% |
| **EDU** (academic+textbook) | 1,431 | 17.2% |
| **MED** (news) | 487 | 5.9% |

**Domain Mapping**: 7 original categories → 5 standardized codes

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Government, finance, technical manuals, education, news |
| **Document Types** | Born-digital PDFs (administration, law, finance, academic, textbook, manual, news) |
| **Language(s)** | English (94.2%), Chinese (1.8%), Undetermined (3.7%) |
| **Temporal Range** | Not specified |
| **Acquisition Method** | PDF extraction at 300 DPI |

##### 5.1 Domain Categories

> **Original Categories**: 7 (Administration, Law, Finance, Academic, Textbook, Manual, News)
> **Standardized Codes**: 5 (GOV, FIN, TEC, EDU, MED)

| Original Domain | Standardized Code | Count | Percentage |
|-----------------|-------------------|-------|------------|
| Administration | GOV | - | 30.4% (combined) |
| Law | GOV | - | 30.4% (combined) |
| Finance | FIN | 2,133 | 25.7% |
| Manual | TEC | 1,724 | 20.8% |
| Academic | EDU | - | 17.2% (combined) |
| Textbook | EDU | - | 17.2% (combined) |
| News | MED | 487 | 5.9% |

##### 5.2 Content Flags (from Docling Layout)

> **Source**: Docling GPU layout extraction (97.7% coverage)

| Content Type | Pages with Content | Percentage |
|--------------|-------------------|------------|
| **Tables** | 2,092 | 25.2% |
| **Figures** | 2,576 | 31.0% |
| **Formulas** | 107 | 1.3% |
| **Code** | 55 | 0.7% |
| **Handwriting** | 0 | 0% (born-digital) |

**Layout Categories**: 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)

##### 5.3 Language & Script Coverage

> **Source**: OpenLID (1,000 samples) + HF GT character analysis (6,999 samples)

| Language | ISO Code | Samples | Coverage | Detection Method |
|----------|----------|---------|----------|------------------|
| English | en | 7,824 | 94.2% | OpenLID + GT analysis |
| Chinese | zh | 152 | 1.8% | OpenLID + GT analysis |
| Undetermined | - | 304 | 3.7% | Minimal text content |

**Script Families Present**:

| Script | Samples | Coverage | Notes |
|--------|---------|----------|-------|
| Latin | 7,828 | 94.4% | Primarily English |
| CJK (Chinese) | 157 | 1.9% | Simplified + Traditional |
| Other/Undetermined | 307 | 3.7% | Mixed or minimal text |

**Text Direction**:

| Direction | Samples | Coverage |
|-----------|---------|----------|
| LTR (Left-to-Right) | 7,994 | 96.3% |
| Null/Undetermined | 304 | 3.7% |

> **Notes**:
>
> - Language detection truncated: OpenLID file contains only 1,000 of 8,259 detected records
> - Compensated with HF GT character script analysis for remaining samples
> - ISO 639-1 language codes used where applicable

#### 6. IQA Profile

> **Summary**: Born-digital baseline with very high quality. Low IQA training value but high benchmark suitability.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Born-digital (PDF extraction, not scanned) |
| **Capture Device** | N/A (programmatic extraction at 300 DPI) |
| **Original Quality** | Very high baseline quality - clean digital documents |
| **Compression** | PNG format (lossless) |
| **Known Artifacts** | None - no scanning or camera artifacts |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | LOW | Born-digital - no blur present |
| **Noise** | LOW | Born-digital - no noise present |
| **Skew** | LOW | Born-digital - no skew present |
| **Contrast** | LOW | Born-digital - optimal contrast |
| **Compression** | LOW | PNG lossless format |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable (born-digital) | Consistent quality across text sizes |
| **Line/Grid Density** | Moderate (tables 25.2%) | Clean grid lines (no scan artifacts) |
| **Font Diversity** | High (multi-domain) | Consistent OCR behavior expected |
| **Mathematical Notation** | Low (1.3% formulas) | Minimal special character challenges |
| **Color Usage** | RGB (color documents) | Color preservation for figures |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | LOW - Born-digital baseline, not suitable for degradation detection training |
| **Unique Characteristics** | OCR quality impact on RAG, controlled degradation (semantic + formatting noise) |
| **Complementary Datasets** | Combine with scanned datasets (DIQA-5000, RealDAE) for degradation training |
| **Benchmark Suitability** | HIGH - Systematic RAG quality assessment, OCR error propagation analysis |
| **Known Limitations** | No scanned/camera degradation, limited IQA training value |

##### 6.5 Benchmark Results

> **Purpose**: Measures OCR quality impact on RAG retrieval and generation performance.

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| OCR Noise Impact | RAG Retrieval | Accuracy Drop | Variable by noise level | [Paper arXiv:2412.02592](https://arxiv.org/abs/2412.02592) |

**OCR Noise Variants**:

- **3 OCR Engines**: GOT, MinerU, Qwen2.5-VL
- **3 Semantic Noise Levels**: Mild, Moderate, Severe
- **3 Formatting Noise Levels**: Mild, Moderate, Severe
- **Total Variants**: 12 OCR noise columns per page

> **Notes**:
>
> - Benchmark measures how OCR errors propagate through RAG pipelines
> - Controlled degradation enables systematic quality assessment
> - Primary value is in RAG evaluation, NOT IQA detector training

#### 7. Known Issues & Limitations

1. **Split Claim Incorrect**: Previous documentation claimed train/val/test splits exist in HF parquet - they don't. All 8,561 pages are in one split.
2. **258 Missing Pages**: Layer 2 metadata has 8,303 vs HuggingFace's 8,561 (258 textbook pages not in metadata).
3. **Language Enrichment Truncated**: OpenLID enrichment file contains only 1,000 of 8,259 detected records. Compensated with HF GT character script analysis.
4. **Layout Gaps**: 195 pages (2.35%) have no layout annotations from Docling GPU extraction.
5. **Invalid Bboxes**: 71 pages (0.86%) have malformed bounding boxes in layout data.
6. **Born-Digital Limitation**: No scanned/camera degradation - limits IQA training value to benchmark use only.
7. **Domain Imbalance**: GOV+FIN represent 56.1% of dataset - potential domain bias in evaluation.

#### 8. Representative Samples

> **Note**: See VLM inspection results when available for visual quality assessment.

Visual inspection not yet conducted. Dataset consists of born-digital PDF pages at uniform 300 DPI with no visible quality degradation.

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{fan2024ohrbench,
  title={OHR-Bench: Benchmarking the Impact of OCR Quality on RAG Systems},
  author={Fan, Junyuan and others},
  booktitle={ICCV},
  year={2025},
  note={arXiv:2412.02592}
}
```

##### Related Works

- **HuggingFace Dataset**: [opendatalab/OHR-Bench](https://huggingface.co/datasets/opendatalab/OHR-Bench)
- **GitHub Repository**: [opendatalab/OHR-Bench](https://github.com/opendatalab/OHR-Bench)
- **Paper**: [arXiv:2412.02592](https://arxiv.org/abs/2412.02592)

##### Leaderboards

- Not applicable (benchmark dataset, not competition dataset)

#### 10. Dataset-Specific Notes

##### 10.1 OCR Noise Variants

> **Purpose**: Controlled degradation for systematic RAG quality assessment.

The dataset provides 12 OCR noise variants per page:

**Semantic Noise** (3 engines × 3 levels):

- **GOT**: Mild, Moderate, Severe
- **MinerU**: Mild, Moderate, Severe
- **Qwen2.5-VL**: Mild, Moderate, Severe

**Formatting Noise** (3 levels):

- Mild, Moderate, Severe

> **Note**: OCR noise variants are for evaluation, not training. They simulate how OCR errors at different severity levels affect RAG retrieval and generation accuracy.

##### 10.2 Q&A Pairs for RAG Evaluation

> **Purpose**: Measure how OCR quality impacts RAG retrieval and answer accuracy.

- **Total Q&A Pairs**: 8,498 question-answer pairs in `qas_v2.json`
- **Granularity**: Document-level with page number evidence
- **Purpose**: Evaluate RAG systems with controlled OCR degradation
- **Unique Value**: Systematic assessment of OCR error propagation through RAG pipelines

##### 10.3 Benchmark Usage

> **Primary Use Case**: Measuring OCR quality impact on downstream RAG performance.

**Evaluation Workflow**:

1. Extract text using multiple OCR engines at different noise levels
2. Build RAG index with each OCR variant
3. Measure retrieval and generation accuracy using Q&A pairs
4. Quantify quality degradation as noise level increases

**Key Insight**: The dataset enables controlled experiments to determine acceptable OCR quality thresholds for production RAG systems.

---

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Audit Metadata

> **Audit Date**: 2026-02-14 | **Methodology**: v2.3.0 (15-field prescreening) | **Samples**: 8,303

**Audit Scope**:

- **Prescreening Fields**: 15 (split, capture_method, domain_level1, iso639_language, script_family, content_flags, layout_detections, layout_bbox_valid, orientation, color_mode, handwriting, text_has_content, text_direction, text_directions_present, quality_overall_mos)
- **Overall Pass Rate**: 94.7% (7,863/8,303 samples)

##### 11.2 Prescreening Results

| Field | Pass Rate | Failure Rate | Notes |
|-------|----------:|-------------:|-------|
| split | 100% | 0% | All samples "train" |
| capture_method | 100% | 0% | All BORN_DIGITAL |
| domain_level1 | 100% | 0% | 5 standardized codes |
| iso639_language | 96.34% | 3.66% | 304 undetermined (minimal text) |
| script_family | 100% | 0% | Latin/CJK/Other |
| content_flags | 100% | 0% | Docling GPU extraction |
| layout_detections | 97.65% | 2.35% | 195 pages missing layout |
| layout_bbox_valid | 99.14% | 0.86% | 71 pages malformed bboxes |
| orientation | 100% | 0% | All portrait |
| color_mode | 100% | 0% | All RGB |
| handwriting | 100% | 0% | All false (born-digital) |
| text_has_content | 99.87% | 0.13% | 11 pages minimal text |
| text_direction | 100% | 0% | 96.3% LTR, 3.7% null |
| text_directions_present | 100% | 0% | All populated |
| quality_overall_mos | 100% | 0% | Not applicable (no MOS) |

##### 11.3 Fields at 0% Failure

11 of 15 prescreening fields achieved 0% failure:

- split, capture_method, domain_level1, script_family, content_flags
- orientation, color_mode, handwriting, text_direction, text_directions_present, quality_overall_mos

##### 11.4 Integration Details

| Aspect | Details |
|--------|---------|
| **Integration Script** | `scripts/integrate_ohr_bench_enrichments.py` |
| **Enrichment Version** | v2 (integrated_v2) |
| **Known Issues Applied** | KI-001 (layout label casing), KI-005 (capture method), KI-008 (script_family re-derivation) |
| **v2.3.0 Fields** | text_direction populated for 96.3% (ltr), text_directions_present for 100% |

##### 11.5 Key Findings

**Strengths**:

- **11/15 fields at 0% failure**: High-quality automated enrichment
- **Consistent capture method**: All born-digital, no mixed sources
- **Domain coverage**: 5 standardized codes with clean mapping
- **Layout extraction**: 97.65% coverage from Docling GPU

**Remaining Issues**:

1. **iso639_language 3.66% failure**: 304 pages with undetermined language (minimal text content)
2. **layout_detections 2.35% failure**: 195 pages missing Docling layout annotations
3. **layout_bbox_valid 0.86% failure**: 71 pages with malformed bounding boxes
4. **text_has_content 0.13% failure**: 11 pages with minimal text

**Recommended Actions**:

- **iso639_language**: Accept as valid (pages truly have minimal text)
- **layout_detections**: Re-run Docling GPU on 195 failed pages
- **layout_bbox_valid**: Investigate and fix bbox parsing for 71 pages
- **text_has_content**: Manual inspection of 11 edge cases

**Audit Artifacts**: [scripts/audit/results/ohr-bench/](../../scripts/audit/results/ohr-bench/)

---

#### 12. Reliability & Bottlenecks

> **Purpose**: Auto-generated composite reliability summary identifying the weakest enrichment fields per dataset. Populated by `materialize_reliability_summary.py`.
>
> **Methodology**: Each enrichment field is assigned a confidence score (0.0-1.0). Missing/unrun fields get confidence=0.0. The composite min_confidence across all fields determines each sample's overall reliability category.

##### 12.1 Composite Category Distribution

> **Computed**: 2026-02-14 | **Samples**: 8,303 | **Avg Min Confidence**: 0.781

| Category | Count | Pct | Notes |
|----------|------:|----:|-------|
| hard_label | 0 | 0.0% | High confidence (>= 0.9) |
| soft_label | 8,108 | 97.7% | Medium confidence (>= 0.7) |
| active_learning | 0 | 0.0% | Low confidence (>= 0.5) |
| unreliable | 195 | 2.3% | Very low confidence (< 0.5) |

**Category Thresholds**: hard_label >= 0.9, soft_label >= 0.7, active_learning >= 0.5, unreliable < 0.5

> **Note**: 97.7% of samples achieve soft_label reliability (>= 0.7 confidence). The 2.3% unreliable samples correspond to pages missing layout annotations.

##### 12.2 Top Bottleneck Fields

> The fields most frequently responsible for the lowest per-sample confidence.

| Rank | Field | Bottleneck % | Avg Confidence | Notes |
|-----:|-------|-------------:|---------------:|-------|
| 1 | `has_table` | 97.7% | 0.800 | Docling layout confidence |
| 2 | `layout_detections` | 2.3% | 0.830 | 195 pages missing annotations |

> **Improving Reliability**:
>
> - `has_table` -> Inherent from Docling layout detection confidence (0.8 threshold)
> - `layout_detections` -> Re-run Docling GPU extraction on 195 failed pages to reach 100% coverage

---

#### Data Format

> **Primary format**: HuggingFace Parquet with PNG images at 300 DPI.

##### Format Details

| Aspect | Details |
|--------|---------|
| **Source Format** | HuggingFace Parquet (17 columns) |
| **Image Format** | PNG (lossless, 300 DPI) |
| **Annotation Format** | COCO JSON (Docling layout), JSON (Q&A pairs) |
| **Layer 2 Metadata** | JSON (8,303 records, enrichment v2) |
| **Storage** | ~2.2 GB (images), ~500 MB (metadata + annotations) |

#### Processing Status

> **Current state**: Fully processed with Layer 2 enrichment v2 integrated.

| Stage | Status | Notes |
|-------|--------|-------|
| **Image Extraction** | ✅ Complete | 8,303/8,561 pages extracted |
| **Layer 2 Base Metadata** | ✅ Complete | annotate_base_metadata.py |
| **Language Detection** | ✅ Complete | OpenLID + HF GT fallback |
| **Layout Extraction** | ✅ Complete (97.7%) | Docling GPU, 7 batches |
| **OCR Extraction** | ✅ Complete | Docling GPU, 1,261 records |
| **Enrichment Integration** | ✅ Complete | integrate_ohr_bench_enrichments.py (v2) |
| **Layer 2 Audit** | ✅ Complete | 94.7% pass rate, Grade D (no VLM) |

#### License

| Aspect | Details |
|--------|---------|
| **License** | CC-BY-4.0 |
| **License URL** | [Creative Commons BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Commercial Use** | No (Research only per dataset terms) |
| **Redistribution** | Allowed with attribution |
| **Modification** | Allowed with attribution |

#### Version History

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2024-12-02 | Initial release (arXiv:2412.02592) |
| **L2 v1** | 2026-02-09 | Layer 2 base metadata created (8,303 samples) |
| **L2 v2** | 2026-02-14 | Enrichment v2: language, layout, OCR, domain, content flags integrated |
| **Doc v1** | 2026-02-14 | Documentation rewrite: all 12 template sections populated |

---

## Documentation Metadata

**Documentation Status**: ✅ Complete
**Last Updated**: 2026-02-14
**Template Version**: 1.4.0
**Maintainer**: Documentation Team
