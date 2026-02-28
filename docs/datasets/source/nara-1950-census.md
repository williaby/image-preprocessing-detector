---
canonical_name: nara-1950-census
display_name: NARA 1950 Census (Enumeration Schedules)
source_url: https://1950census.archives.gov/
license: Public Domain
total_images: 25000 (stratified sample across 55 states; full dataset ~6.5M pages)
format: JPEG (scanned page images)
status: in-progress
documentation_status: complete
---

# NARA 1950 Census

## 1. Overview

Scanned enumeration schedules from the 1950 United States Population Census,
digitized by the National Archives and Records Administration (NARA). Each page
contains a handwritten census form with tabular data: names, addresses, ages,
occupations, and demographic information filled in by census enumerators.

The full dataset contains approximately 6.5 million page images across all U.S.
states and territories, hosted on a public S3 bucket. This project uses a
stratified sample for handwriting detection and mixed typed+handwriting training.

## 2. Access & Download

**S3 Bucket**: `s3://nara-1950-census/` (public, `--no-sign-request`)
**Web Portal**: <https://1950census.archives.gov/>

Sampling script: `scripts/sample_nara_1950_census.py`

```bash
# Build manifest (downloads state metadata JSONs)
PYTHONPATH=. uv run python scripts/sample_nara_1950_census.py manifest

# Sample 1000 images stratified across states
PYTHONPATH=. uv run python scripts/sample_nara_1950_census.py sample --count 1000

# Download sampled images
PYTHONPATH=. uv run python scripts/sample_nara_1950_census.py download

# Full pipeline
PYTHONPATH=. uv run python scripts/sample_nara_1950_census.py all --count 1000
```

## 3. License

**Public Domain** — U.S. Government work, no copyright restrictions.
No attribution required. Unrestricted use for commercial and research purposes.

SPDX: `LicenseRef-PublicDomain-USGov`

## 4. Dataset Statistics

| Metric | Value |
|--------|-------|
| Total pages (full dataset) | ~6.5 million |
| Current sample | 25,000 (stratified, download in progress) |
| States represented | 55 (of 57 with metadata) |
| States/territories | 57 (50 states + DC + territories) |
| Format | JPEG (scanned) |
| Resolution | Variable (high-resolution scans) |
| Time period | 1950 |
| Language | English |
| Script | Latin (Latn) |

## 5. Content Description

Each page is a pre-printed government form (Population Schedule) filled in
by hand by a census enumerator. Content includes:

- **Handwritten entries**: Names, addresses, ages, occupations, birthplaces
- **Pre-printed structure**: Column headers, row lines, form number, state/county
- **Mixed content**: Typed form structure + handwritten data entries
- **Tabular layout**: Consistent grid structure across all pages

This makes it ideal training data for:

- Handwriting presence detection (100% handwritten content)
- Mixed typed+handwritten form recognition
- Historical document processing
- Tabular handwriting extraction

## 6. Directory Structure

```text
nara-1950-census/
    {StateName}/
        {census_id}-{StateName}-{serial}/
            {census_id}-{StateName}-{serial}-{page:04d}.jpg
    metadata/
        {state_code}.json
    manifest.json
    sample.json
```

## 7. Parser

**File**: `src/image_preprocessing_detector/annotation/parsers/document/nara_1950_census.py`

Filename regex: `(?P<census_id>\d+)-(?P<state_name>[A-Za-z_]+)-(?P<serial>\d+)-(?P<page>\d{4})\.jpg`

Labels extracted:

- `census_id`: Census enumeration district identifier
- `state_name`: State name (from filename)
- `serial_number`: Document serial within the district
- `page_num`: Page number within the document
- `document_type`: `census_enumeration_schedule`
- `content_type`: `handwritten_form`

## 8. Integration Status

| Step | Status |
|------|--------|
| Sampling script | Done (`scripts/sample_nara_1950_census.py`) |
| Parser | Done (`parsers/document/nara_1950_census.py`) |
| DatasetConfig | Done (in `annotate_base_metadata.py`) |
| `__init__.py` registration | Done |
| Layer 1 scan | Pending (25K download in progress, ~3K of 25K downloaded) |
| Cross-reference docs | Done |

## 9. IQA Sensitivity

| Detector | Sensitivity | Notes |
|----------|-------------|-------|
| Blur | Medium | Age-related degradation in some scans |
| Noise | Low-Medium | Clean scanning process, some film grain |
| Contrast | Medium | Pencil entries can be low contrast |
| Skew | Low | Well-controlled scanning |
| Binarization | High | Critical for separating handwriting from form lines |
| JPEG artifacts | Low | High-quality originals |

## 10. Training Relevance

| Head | Contribution | Details |
|------|-------------|---------|
| `orientation_class` | Not applicable | Scans are consistently oriented |
| `needs_rotation` | Not applicable | Standard portrait orientation |
| `skew_angle` | Secondary | Well-scanned, minimal skew |
| `blur_score` | Secondary | Some age-related blur |
| `noise_score` | Negatives only | Clean scanning |
| `contrast_score` | Secondary | Pencil handwriting varies |
| `script_class` | Primary | Latin script, handwritten |
| `handwriting_presence` | Primary | 100% handwritten content |
| `legibility` | Secondary | Variable enumerator handwriting quality |
| `content_type` | Primary | Census form classification |
| `has_signature` | Secondary | Enumerator signatures present |
| `capture_method` | Primary | Scanner (flatbed) |
| `domain` | Primary | Administrative/Government |

## 11. Gap Impact

- **SIG-G4-3** (Mixed typed+HW): Strong contributor — pre-printed forms with handwritten entries
- **SIG-G4-1** (Handwriting in structured docs): Strong — tabular handwritten data
- **Administrative domain**: Expands government document coverage

## 12. Citations

```bibtex
@misc{nara1950census,
  title={1950 Census Records},
  author={{National Archives and Records Administration}},
  year={2022},
  howpublished={\url{https://1950census.archives.gov/}},
  note={Public Domain}
}
```

## 13. Head Contribution Table

| Head | Role | Notes |
|------|------|-------|
| `orientation_class` | N/A | Consistently oriented scans |
| `needs_rotation` | N/A | Standard portrait |
| `skew_angle` | Secondary | Minimal, well-scanned |
| `blur_score` | Secondary | Some historical degradation |
| `noise_score` | Negatives | Clean scans |
| `contrast_score` | Secondary | Variable pencil contrast |
| `resolution_quality` | N/A | High-resolution source |
| `binarization_quality` | Secondary | Form line separation |
| `compression_artifacts` | Negatives | High-quality JPEG |
| `script_class` | Primary | Latin handwriting |
| `handwriting_presence` | Primary | 100% handwritten |
| `handwriting_legibility` | Secondary | Variable quality |
| `content_type` | Primary | Census form |
| `has_signature` | Secondary | Enumerator signatures |
| `capture_method` | Primary | Scanner flatbed |
| `domain` | Primary | Administrative |
