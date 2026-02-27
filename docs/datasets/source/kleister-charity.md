---
canonical_name: kleister-charity
display_name: Kleister Charity (British Charity Annual Reports)
source_url: https://github.com/applicaai/kleister-charity
license: MIT
total_images: ~20000 (estimated page images from 3,414 PDFs)
format: PDF (git-annex) → rendered PNG page images
status: training-ready
documentation_status: complete
---

# Kleister Charity (British Charity Annual Reports)

## 1. Overview

Kleister Charity contains 3,414 PDF documents of British charity annual reports from
gov.uk, split into 1,729 train / 440 dev / 609 test documents. Reports contain mixed
typed and handwritten content in a financial/administrative context. PDFs are rendered
to individual page images (300 DPI PNG) for use in the IQA/preprocessing pipeline.

Estimated ~20K total page images (average ~6 pages per document).

## 2. Source & Access

| Field | Value |
|-------|-------|
| **Publisher** | Applica.ai (Łukasz Borchmann et al.) |
| **URL** | <https://github.com/applicaai/kleister-charity> |
| **Format** | PDF (git-annex on S3) + TSV label files |
| **License** | MIT (code/labels); data from gov.uk (Open Government Licence) |
| **Download Size** | ~12 GB (all PDFs via git-annex) |
| **Citation** | Borchmann et al., "Kleister: Key Information Extraction Datasets" (ACL 2021) |

## 3. Dataset Composition

| Metric | Value |
|--------|-------|
| **Total Documents** | 3,414 PDFs |
| **Train Documents** | 1,729 |
| **Dev-0 Documents** | 440 |
| **Test-A Documents** | 609 |
| **Est. Page Images** | ~20,000 (rendered at 300 DPI) |
| **Image Type** | Full-page rendered document images |
| **Resolution** | 300 DPI (rendered), varies by source page size |
| **Color Mode** | RGB |

## 4. Label Schema

Per-document labels in `expected.tsv` (space-separated key=value pairs):

- `charity_name`: Organization name (UPPER CASE)
- `charity_number`: Registered charity number
- `address__post_town`: Address post town (UPPER CASE)
- `address__postcode`: Address postcode (UPPER CASE)
- `address__street_line`: Street address
- `income_annually_in_british_pounds`: Annual income (e.g., 103373.00)
- `spending_annually_in_british_pounds`: Annual spending
- `report_date`: Report date (YYYY-MM-DD format)

Labels are document-level (not page-level). Rendered images inherit the parent
document's labels via JSON sidecar files.

## 5. Language & Script Coverage

| Script | ISO 15924 | Count | Notes |
|--------|-----------|-------|-------|
| Latin | Latn | ~20,000 | English financial documents |

## 6. IQA Profile

| Degradation | Prevalence | Notes |
|-------------|-----------|-------|
| Born-digital artifacts | High | Many reports are born-digital PDFs |
| Scanner artifacts | Medium | Some scanned historical reports |
| Mixed quality | Medium | Varies by charity reporting quality |
| Tables/figures | High | Financial tables common |
| Handwriting | Low-Medium | Signatures, annotations, margin notes |

## 7. Training Relevance

| Head | Applicable | Reason |
|------|-----------|--------|
| Handwriting Detection | **Primary** | Mixed typed + handwritten content |
| Script Detection | Secondary | English Latin only |
| IQA | Secondary | Born-digital + scanned mix |
| Layout Detection | **Primary** | Tables, headers, figures common |
| Orientation | No | Standard portrait orientation |

## 8. SigLIP 2 Head Coverage

| SIG ID | Head | Applicable | Count | Tier | Notes |
|--------|------|-----------|-------|------|-------|
| SIG-G4-1 | handwriting_presence_cls | Yes | ~20,000 | tier_2_heuristic | Mixed typed+HW in financial docs |
| SIG-G4-3 | handwriting_content_cls | Yes | ~20,000 | tier_2_heuristic | Signatures, annotations in reports |
| SIG-G4-4 | capture_method | Yes | ~20,000 | tier_0_exact | Born-digital + scanner mix |
| SIG-G2-1 | script_cls | Yes | ~20,000 | tier_0_exact | 100% Latin (English) |

## 9. Known Limitations

- **English only**: British charity documents exclusively
- **Born-digital majority**: Many documents are born-digital PDFs, not scanned
- **Document-level labels**: Key-value labels apply to whole document, not per-page
- **Variable handwriting**: HW content (signatures, notes) is sparse on most pages
- **Large dataset**: ~12 GB of PDFs requires significant disk space and rendering time
- **git-annex dependency**: PDF download requires git-annex + S3 access

## 10. Local Storage

| Item | Path |
|------|------|
| **PDFs** | `/mnt/e/image_detection/01_base_data/documents/kleister-charity/documents/` |
| **Rendered images** | `/mnt/e/image_detection/01_base_data/documents/kleister-charity/rendered_images/` |
| **Train labels** | `/mnt/e/image_detection/01_base_data/documents/kleister-charity/train/expected.tsv` |
| **Dev labels** | `/mnt/e/image_detection/01_base_data/documents/kleister-charity/dev-0/expected.tsv` |
| **Rendering script** | `scripts/render_kleister_charity_pdfs.py` |
