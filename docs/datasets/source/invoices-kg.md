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
