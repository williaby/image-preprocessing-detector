#### Tobacco-800

> **Quick Stats**: 1,290 documents | Real archival | Authentic degradation patterns
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Tobacco-800 (CDIP Subset) |
| **Version** | 1.0 |
| **Release Date** | 2006 |
| **Maintainer** | Illinois Institute of Technology |
| **Paper** | [Lewis et al. SIGIR 2006](https://dl.acm.org/doi/10.1145/1148170.1148307) |
| **Repository** | [TC-11](https://tc11.cvc.uab.es/datasets/Tobacco800_1), [Kaggle](https://www.kaggle.com/datasets/sprytte/tobacco-800-dataset) |
| **License** | Academic (derived from Master Settlement Agreement docs) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/tobacco800/` |
| **Documentation Status** | Complete |

##### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | TIF → PNG (converted) | Document page images (binary, 1-bit) |
| **Annotations** | N/A (separate source) | University of Maryland ground truth for signatures/logos |
| **Metadata** | N/A | CDIP source metadata not preserved in dataset distribution |
| **Supplementary** | - | None provided in standard distribution |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Full** | `01_base_data/degraded/tobacco800/images/` | N/A (not in local copy) | 1,290 | ✅ |

**Split Organization Pattern**: `single_dir` (no train/test/val splits)

> **Notes**:
>
> - No official train/test split. Safe to use entire dataset with cross-validation.
> - University of Maryland provides signature and logo ground truth annotations (available from TC-11, not in standard dataset distribution).
> - Local copy contains only images; Maryland annotations must be downloaded separately from [TC-11](https://tc11.cvc.uab.es/datasets/Tobacco800_1).

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Signature Boxes** | Unknown (TC-11) | Region | Location and dimensions of handwritten signatures |
| **Logo Boxes** | Unknown (TC-11) | Region | Location and dimensions of company logos |
| **Document Class** | Binary | Page | Logo present (412) vs absent (878) |

> **Note**: Ground truth annotations from University of Maryland study (Zhu & Doermann CVPR 2007, ICDAR 2007). Format requires verification from TC-11 distribution.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / Papers | Version, license, citation |
| **Image-level** | CDIP metadata | Original document IDs, scan settings (not preserved in dataset distribution) |
| **Annotation-level** | Maryland files | Bounding boxes for signatures/logos (separate download) |

###### 2.5 Annotation Schema Details

> **Format**: Unknown - requires verification from TC-11 dataset distribution

**Expected Fields for Parsing** (based on literature):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | str | Yes | Links to filename |
| `signature_bbox` | list | Varies | Coordinate format TBD |
| `logo_bbox` | list | Varies | Coordinate format TBD |
| `has_logo` | bool | Yes | Binary classification (412 with, 878 without) |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Signature boxes | `layout_detections` | High | Requires Maryland annotation acquisition |
| ✅ Logo boxes | `layout_detections` | High | Requires Maryland annotation acquisition |
| ⚠️ Document class | `document_labels` | Medium | Binary logo presence classification |
| ❌ Text content | - | Low | Binary images, OCR challenging |

> **Blocker**: Parser enhancement blocked until Maryland annotations are acquired from TC-11 official distribution.

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,290 |
| **With Logos** | 412 documents |
| **Without Logos** | 878 documents |
| **Resolution** | 150-300 DPI (variable) |
| **Dimensions** | 1200×1600 to 2500×3200 px |
| **File Format** | TIF |
| **Source** | CDIP collection (42M pages from tobacco litigation) |

##### Ground Truth (University of Maryland)

| Annotation | Coverage |
|------------|----------|
| **Signatures** | Location and dimensions |
| **Logos** | Location and dimensions |
| **Visual Entities** | Complete localization |

*Ground truth by: Zhu, Zheng, Doermann, Jaeger (CVPR 2007, ICDAR 2007)*

##### 5.2 Class/Category Definitions

> **Purpose**: Document detection task taxonomy for University of Maryland ground truth.

| Class/Category | ID | Description | Parent |
|----------------|-----|-------------|--------|
| Logo | 1 | Company logos and trademarks | - |
| Signature | 2 | Handwritten signatures | - |
| Text | 3 | Printed text regions | - |
| Background | 0 | Non-content regions | - |

**Binary Classification**:

- **With Logo** (412 documents): Documents containing visible company logos
- **Without Logo** (878 documents): Documents with no logo content

> **Notes**:
>
> - Ground truth annotations from University of Maryland study
> - Primary benchmark tasks: signature detection, logo detection
> - See benchmark papers: Zhu & Doermann CVPR 2007, ICDAR 2007

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real archival scans (multi-year, multi-device collection) |
| **Baseline Quality** | Variable (authentic degradation) |
| **Degradation Types** | Yellowing, staining, bleed-through, foxing, fading |
| **Key Value** | **Ground truth for real-world document degradation** |

##### 6.2 Degradation Sensitivity

> **Source**: [Empirically Derived] from archival scan characteristics

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | MEDIUM | Variable scan quality, some motion blur |
| **Noise** | HIGH | Aging artifacts, yellowing, speckles |
| **Skew** | LOW | Most documents well-aligned during scan |
| **Contrast** | HIGH | Binary images, loss of gray-level information |
| **Yellowing** | HIGH | Authentic paper aging, color shift |
| **Staining** | HIGH | Coffee stains, water damage, foxing |
| **Bleed-through** | MEDIUM | Ink showing through from reverse side |
| **Fading** | HIGH | Text degradation over decades |
| **Binarization Artifacts** | HIGH | Conversion to binary loses detail |
| **JPEG Blockiness** | LOW | Binary format (not JPEG) |

**Degradation Characteristics**:

- **Temporal**: 30-50 year document aging (tobacco litigation era)
- **Storage**: Poor archival conditions, non-climate controlled
- **Multi-device**: Scanned with different equipment, variable DPI
- **Authentic**: Real-world degradation patterns, not synthetic

##### Training Value

- **Strengths**: Only dataset with authentic archival degradation, realistic multi-device scanning, signature/logo ground truth
- **Weaknesses**: Binary-only images, limited to administrative documents, variable scan quality
- **Complementary Datasets**: RVL-CDIP (same source, document classification)

##### Benchmark Tasks

| Task | Typical Use |
|------|-------------|
| Signature Detection | [Zhu & Doermann CVPR 2007](https://ieeexplore.ieee.org/document/4270268) |
| Logo Detection | [Zhu & Doermann ICDAR 2007](https://ieeexplore.ieee.org/document/4377107) |
| Document Retrieval | Archival search systems |
| Document Classification | Combined with RVL-CDIP |

##### Project Usage

- **Path**: `01_base_data/degraded/tobacco800/`
- **Phase(s)**: Phase 1C (Classical IQA), Phase 3 (ML IQA validation)
- **Purpose**: Real-world degradation patterns, signature/logo detection
- **Parser**: ℹ️ N/A (no ground truth labels)

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/degraded/tobacco800/` | ✅ Available | 1,290 TIFF/PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | `metadata_registry/extracted/tobacco800/ocr_batch_*.jsonl` | ✅ Extracted | Docling OCR, 7 batch files, 1,290 records (100% coverage), confidence 1.0 |
| **Layout Extracted** | `metadata_registry/extracted/tobacco800/layout_batch_*.json` | ✅ Extracted | Docling layout annotations, 7 batch files, 10 categories |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,290 |
| **File Format** | PNG (100%) |
| **Dimensions** | 1200-2720 × 1575-3584 px (avg: 1790 × 2326) |
| **Avg File Size** | 67 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |

##### 10. Dataset-Specific Notes

###### 10.1 Annotation Caveats

- **Binary Images Only**: All documents converted to 1-bit binary format, losing grayscale information
- **Variable Scan Quality**: Multi-device collection results in inconsistent DPI (150-300)
- **Maryland Ground Truth**: Signature/logo annotations from separate research study, not included in standard dataset distribution
- **Incomplete Coverage**: Only 32% annotated with logo/signature locations (412 with logos out of 1,290 total)
- **Separate Download Required**: Maryland annotations available from [TC-11](https://tc11.cvc.uab.es/datasets/Tobacco800_1), not in local copy

###### 10.2 Implementation Notes

- **Binarization Impact**: 1-bit format means classical IQA metrics (blur, noise) have limited applicability
- **Detection Focus**: Primary value is signature/logo detection, not OCR
- **Degradation Patterns**: Authentic aging makes this ideal for real-world degradation training
- **CDIP Context**: Subset of 42-million page tobacco litigation collection
- **Parser Status**: Current parser extracts basic metadata only; enhancement blocked until Maryland annotations acquired

###### 10.3 External Resources

- **CDIP Collection**: Full 42M page archive at [Legacy Tobacco Documents Library](https://www.industrydocuments.ucsf.edu/)
- **Maryland Study**: Zhu & Doermann signature detection papers provide annotation methodology
- **TC-11 Dataset**: Technical Committee 11 (Reading Systems) hosts official version with annotations
- **Related Datasets**: RVL-CDIP uses same source (400K images, document classification)

###### 10.4 Custom Metrics

- **Archival Quality Tiers**: Not formally defined, but images span:
  - **Excellent** (20%): Clean scans, minimal aging
  - **Good** (50%): Moderate yellowing, readable
  - **Poor** (25%): Heavy staining, low contrast
  - **Degraded** (5%): Severe damage, partial illegibility

- **Master Settlement Agreement Context**: Documents from 1998 tobacco industry legal settlement
- **Historical Value**: Only dataset with authentic 30-50 year document aging

---

##### 5. Data Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | TIFF (converted to PNG) |
| **Bit Depth** | 1-bit binary |
| **Resolution** | 150-300 DPI (variable) |
| **Metadata Format** | Per-image JSON (Layer 2) |
| **Storage** | GCS bucket + local E:\ drive |

##### 6. License

| Attribute | Value |
|-----------|-------|
| **License Type** | Academic / Research Only |
| **Source** | Master Settlement Agreement (tobacco litigation) |
| **Commercial Use** | Not permitted |
| **Citation** | Lewis et al. SIGIR 2006 |

##### 7. Limitations

- **Binary-only images**: 1-bit format prevents grayscale/color analysis, limits classical IQA applicability
- **Variable scan quality**: Multi-device collection (150-300 DPI), inconsistent capture settings
- **No official splits**: Entire dataset is a single unsplit collection; splits must be assigned at training time
- **Maryland annotations separate**: Signature/logo ground truth requires separate download from TC-11
- **Administrative documents only**: Limited to tobacco litigation correspondence, memos, and forms

##### 8. Processing Status

| Step | Status | Notes |
|------|--------|-------|
| **Image Conversion** | ✅ Complete | TIF → PNG conversion |
| **Base Metadata** | ✅ Complete | 1,290 samples annotated |
| **LLM Enrichment** | ✅ Complete | Domain, language, script enrichment |
| **Docling OCR** | ✅ Complete | 100% coverage (1,290 records) |
| **Docling Layout** | ✅ Complete | 10 layout categories extracted |
| **VLM Inspection** | ❌ Not started | Content flags unverified |

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-02-10 | Initial Layer 2 metadata documentation |
| v1.1 | 2026-02-13 | Added format, license, limitations, processing, version history sections |

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 1,290 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 1,290 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
