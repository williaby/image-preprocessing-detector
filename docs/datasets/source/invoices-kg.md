### invoices-kg

> **Quick Stats**: 1,414 images (989 train, 425 val) | Scanned invoices | Financial domain | Key-value extraction
>
> **License**: ODbL-1.0 | **Commercial Use**: Yes (with attribution + ShareAlike)

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Kaggle High-Quality Invoice Images for OCR |
| **Version** | 1.0 |
| **Release Date** | 2022 (estimated) |
| **Maintainer** | Osama Hosam Abdellatif (Kaggle) |
| **Source** | [Kaggle Dataset](https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr) |
| **License** | [ODbL-1.0](https://opendatacommons.org/licenses/odbl/1-0/) |
| **Commercial Use** | Yes (with attribution + ShareAlike) |
| **Documentation Status** | Empirically Derived |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Invoice scans/photos |
| **Annotations** | JSON | Manifest with structured invoice data + OCR text |
| **Metadata** | JSON | Dataset preparation metadata |

##### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `invoices_kaggle/train/images/` | `invoices_kaggle/train/annotations.json` | 989 | ✅ |
| **Validation** | `invoices_kaggle/val/images/` | `invoices_kaggle/val/annotations.json` | 425 | ✅ |
| **Total** | - | - | 1,414 | ✅ |

**Split Organization Pattern**: `by_folder` (train/val directories with annotations.json manifest)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Invoice Fields** | JSON (structured) | Document | client_name, seller_name, invoice_number, date, totals |
| **Line Items** | JSON (array) | Item-level | description, quantity, total_price |
| **OCR Text** | TXT (in JSON) | Page-level | Full invoice text transcription |

**Annotation Example**:

```json
{
  "invoice": {
    "client_name": "Davis, Li and Coleman",
    "seller_name": "Carpenter, Robinson and Jackson",
    "invoice_number": "41389063",
    "invoice_date": "03/17/2021",
    ...
  },
  "items": [
    {"description": "...", "quantity": "3.00", "total_price": "16.14"}
  ],
  "subtotal": {"tax": "1.47", "total": "16.14"}
}
```

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | `dataset_metadata.json` | Source, license, split info |
| **Image-level** | `annotations.json` | Original filename, CSV source path |
| **Annotation-level** | Embedded in JSON | Invoice fields, OCR text |

##### 2.5 Annotation Schema Details

**Format**: JSON manifest (one file per split)

Each manifest contains an array of annotation objects:

```json
[
  {
    "filename": "train_00000.jpg",
    "original_filename": "batch1-0965.jpg",
    "original_path": "data/downloads/...",
    "csv_source": "data/downloads/.../batch1_2.csv",
    "json_data": "{...structured invoice data...}",
    "ocred_text": "Invoice no: 41389063 Date of issue: ..."
  }
]
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `filename` | str | Yes | Links annotation to image |
| `json_data` | str (JSON) | Yes | Structured invoice fields |
| `ocred_text` | str | Yes | Full OCR transcription |
| `original_filename` | str | Yes | Provenance tracking |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Invoice fields | `raw_labels.{field}` | High | client, seller, invoice_number, date |
| ✅ Line items | `raw_labels.items` | High | Structured array of items |
| ✅ Totals | `raw_labels.{tax,total}` | High | Financial calculations |
| ✅ OCR text | `text_content.full_text` | High | Complete page transcription |
| ✅ Split info | `raw_labels.split` | Medium | train/val |

**Parser Implementation**: ✅ **Complete** - [`InvoicesKgParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py)

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Mixed |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | Not disclosed |
| **Quality Assurance** | Invoice key-value extraction annotation |
| **GT Label Coverage** | 100% of annotated invoice images (note: Layer 2 Doc Completeness is 45.5% due to missing optional metadata fields) |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Not currently used in training |
| **Purpose** | Key-value extraction, invoice IQA, OCR validation |
| **Local Path** | `01_base_data/forms/invoices_kaggle/` |
| **Subset Used** | Full dataset (1,414 images) |
| **Preprocessing** | `scripts/prepare_invoice_dataset.py` (flattens batch structure) |
| **Parser** | [`InvoicesKgParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py) |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`InvoicesKgParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `invoice_data`, `line_items`, `text_content` |
| **Layer 2 Auto-Derived** | `capture_method=scanned`, `domain.level1=FIN`, `domain.level2=INVOICE` |
| **Config Entry** | `DATASET_CONFIGS["invoices-kg"]` |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/forms/invoices_kaggle/` | ✅ Available | 1,414 JPG/PNG files |
| **Text/GT** | Native annotations | ✅ Available | JSON: Invoice fields + line items + full OCR text (`ocred_text`, `json_data`) |
| **Text/OCR Extracted** | `annotations/invoices-kg/ocr/ocr_batch_*.jsonl` | ✅ Available | 1,414 records (100%), Docling OCR |
| **Layout Extracted** | `annotations/invoices-kg/layout/layout_batch_*.json` | ✅ Available | 1,414 records (100%), DocLayout-YOLO |

#### 4. Dataset Statistics

##### 4.1 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 1,414 |
| **Training Split** | 989 (70%) |
| **Validation Split** | 425 (30%) |
| **Test Split** | None |
| **File Format** | JPG |
| **Split Method** | Random (seed=42) |

##### 4.2 Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Financial (invoices) |
| **Document Types** | Business invoices (mixed layouts) |
| **Language(s)** | English (Empirically Derived) |
| **Acquisition Method** | Scanned/photographed (mixed quality) |

#### 5. Known Issues & Limitations

- **Small Dataset**: Only 1,414 images (limited training utility)
- **No Bounding Boxes**: Source dataset does not provide spatial layout annotations
- **No Test Split**: Only train/val splits available
- **Quality Variance**: Mixed scan quality (not profiled yet)

#### 6. References

**Source**: [Kaggle Dataset](https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr)

**Preparation Script**: `scripts/prepare_invoice_dataset.py`

**Parser Implementation**: `src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py`

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (88.9/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.7 | 18% |  |
| Field Validity | 100.0 | 18% |  |
| Doc Completeness | 54.5 | 6% | Below threshold |
| Defect Rate | 85.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **88.9** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 2 defects (2 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| IKG-D01 | layout_detections | HIGH | OPEN | Missing or incomplete layout element bounding boxes; blocks downstream layout-aware processing |
| IKG-D02 | text_has_content | MEDIUM | OPEN | Empty or missing OCR text content where text is expected in invoice fields |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 80.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/invoices-kg/](../../scripts/audit/results/invoices-kg/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 1,414 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 1,414 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ✅ Primary | 1,414 | All upright (0°) assumed; born-digital invoices are uniformly oriented | Adds born-digital invoice examples to orientation corpus |
| MNV4-H2 | skew_reg | ❌ Not applicable | 0 | Born-digital; zero physical skew | Digitally rendered invoices have no geometric distortion |
| MNV4-H3 | resolution_quality_reg | 🟡 Secondary | 1,414 | Derivable via resolution quality pipeline | Born-digital at consistent resolution; contributes to high-quality end of scale |
| SIG-G1-1 | blur_score | ➖ Negatives | 1,414 | Clean/unblurred; useful negative examples | Born-digital documents have no blur; reliable low-blur reference samples |
| SIG-G1-2 | noise_score | ➖ Negatives | 1,414 | No noise; useful negative examples | Born-digital with no sensor or compression noise artifacts |
| SIG-G1-3 | contrast_score | 🟡 Secondary | 1,414 | IQA derivable | High-contrast printed text; contributes to high-contrast end of scale |
| SIG-G1-4 | skew_score | ❌ Not applicable | 0 | No skew in born-digital documents | Skew score is not meaningful for digitally rendered content |
| SIG-G1-5 | compression_score | 🟡 Secondary | 1,414 | IQA derivable | JPEG save from born-digital source; minor compression artifacts possible |
| SIG-G1-6 | overall_quality | 🟡 Secondary | 1,414 | IQA derivable (text_quality bottleneck = 0.000 confidence) | High-quality examples at top of scale; text_quality label absent limits utility |
| SIG-G2-1 | script_cls | ✅ Primary | 1,414 | Latn (100% from L2 metadata) | All English invoices; clean Latin signal |
| SIG-G3-1 | orientation_cls (post) | ✅ Primary | 1,414 | All 0° (born-digital, inherently upright) | Reliable post-correction orientation ground truth |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | 0 | No skew; born-digital | No meaningful skew residual after correction |
| SIG-G4-1 | handwriting_presence_cls | ➖ Negatives | 1,414 | False (100%); born-digital invoices have no handwriting | Strong negative examples for handwriting detection |
| SIG-G4-2 | handwriting_legibility_cls | ➖ Negatives | 1,414 | Negative examples (no handwriting present) | Useful for rejection classification |
| SIG-G4-3 | handwriting_content_type_cls | ➖ Negatives | 1,414 | Negative examples only | No handwritten content to type-classify |
| SIG-G4-4 | presence_reg | ➖ Negatives | 1,414 | 0.0 (no handwriting) | Clean zero-end examples for presence regression |
| SIG-G4-5 | legibility_reg | ➖ Negatives | 1,414 | 0.0 (no handwriting) | Clean zero-end examples for legibility regression |
| SIG-G5-1 | capture_method_cls | ✅ Primary | 1,414 | born_digital (100% from L2 metadata) | Clean born-digital signal; all 1,414 confirmed; strong class anchor |
| SIG-G5-2 | shadow_reg | ➖ Negatives | 1,414 | 0.0 (no shadow in born-digital) | Reliable zero-shadow reference samples |
| SIG-G5-3 | warping_reg | ➖ Negatives | 1,414 | 0.0 (no warping in born-digital) | Reliable zero-warping reference samples |
| SIG-G5-4 | code_cls | ❌ Not applicable | 0 | No source code content | Financial invoices contain no programming code |
| SIG-G5-5 | resolution_quality_reg | 🟡 Secondary | 1,414 | Derivable via resolution quality pipeline | Born-digital at consistent resolution; high-quality end of scale anchor |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | Latin only (100%); no multi-script representation |
| 2 | Capture method | ✅ | born_digital (100%); confirmed by L2 metadata; important negative for camera/scanner heads |
| 3 | Document domain | ✅ | FIN invoices (100%); structured business documents, complementary to SROIE receipts |
| 4 | Layout type | ✅ | Structured form/invoice layout; tabular line items, header/footer blocks; consistent single-page |
| 5 | Text density | ✅ | Moderate-to-high density (invoice fields + line items + totals); all page-scope |
| 6 | Degradation types | ❌ | No physical degradation; born-digital with clean rendering; no useful degradation labels |
| 7 | Resolution/DPI range | 🟡 | Born-digital at fixed render resolution; no DPI metadata in L2; narrow range |
| 8 | Document age | ✅ | Modern (2022 estimated release); contemporary invoice layouts and typography |
| 9 | Text scope | ✅ | Page-level scope (100%) |
| 10 | Content flags | ❌ | content_flags empty in L2 aggregates; no has_table/has_figure profiling done |
| 11 | Binarization status | ✅ | Color/RGB born-digital; no binarized images |
| 12 | Artifact types | ❌ | No artifacts; born-digital documents are clean renders |
| 13 | Color mode | ✅ | RGB (inferred from born-digital source); consistent color mode |
| 14 | Font variety | 🟡 | Business invoice fonts (varied templates from multiple companies); moderate variety |

### 13.3 Corpus Role & Constraints

invoices-kg contributes 1,414 born-digital invoice images that serve as clean-reference anchors for capture_method_cls (born_digital class) and as strong negative examples for physical-degradation heads (blur, noise, shadow, warping). Its small size (1,414 images) limits standalone training utility, but it pairs well with SROIE and financebench for financial-document diversity. ODbL-1.0 license permits commercial use with attribution and ShareAlike compliance required.
