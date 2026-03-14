### John 1:1 Printed Editions

> **Quick Stats**: **181 images** (target: 400-500) | 21 scripts | 1 of 4+ institutions harvested | 575-year span | REL domain | 100% printed
>
> **Status**: Phase 1 partial (Internet Archive only) | **License**: Mixed per-image (PD, CC0, CC-BY-4.0) | **Commercial Use**: Yes (per-image verification)

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | John 1:1 Multi-Script Printed Editions Collection |
| **Version** | 0.2 (Phase 1 partial — IA only) |
| **Release Date** | 2026-03-12 (design phase) |
| **Maintainer** | Project A team (assembled from 4+ institutions) |
| **Paper** | N/A (assembled dataset from public digital libraries) |
| **Repository** | N/A |
| **License** | Mixed: Public Domain, CC0, CC-BY-4.0 (tracked per-image in registry) |
| **Local Storage** | `data/john11-printed-editions/` (images by source subfolder) |
| **Registry** | `/mnt/e/image_detection/metadata_registry/john11_printed_editions_registry.jsonl` (181 entries) |
| **Documentation Status** | Phase 1 Partial Harvest (Internet Archive complete, 3 sources remaining) |

**Dataset Description**: A curated collection of printed/typed Bible pages depicting John 1:1 ("In the beginning was the Word...") across 21 writing systems spanning 575 years of print history (Gutenberg ~1455 to present). This is the **printed parallel** to the `john11-manuscripts` dataset (handwritten, 10 scripts, 577 images).

**Unique value**: 100% printed content = handwriting NONE class for training. Covers 21 scripts (vs 10 handwritten), spanning 6 print technologies and 5 time periods. Provides real-world printed typography diversity complementing V4 synthetic font strategy. Same tier_0_exact ground truth text content as manuscripts (known biblical passage).

**Parallel dataset**: `john11-manuscripts` (handwritten, 10 scripts, 577 images) — together they form a handwritten vs. printed corpus for the same passage.

#### 2. Target Dataset Diversity

> **Full diversity framework**: `docs/planning/JOHN11_PRINTED_SAMPLE_PROFILE.md`

##### 2.1 Script Targets (21 scripts, 400-500 images)

###### Group A: Parallel to manuscripts (10 scripts)

| Script | ISO 15924 | ML Class | OOD? | Target |
|--------|-----------|----------|------|-------:|
| Greek | Grek | GREK | No | 40-60 |
| Latin | Latn | LATN | No | 60-80 |
| Ethiopic | Ethi | OTHER | No | 10-20 |
| Armenian | Armn | OTHER | **Yes** | 10-15 |
| Syriac | Syrc | OTHER | **Yes** | 5-10 |
| Arabic | Arab | ARAB | No | 15-25 |
| Cyrillic | Cyrl | CYRL | No | 15-25 |
| Coptic | Copt | OTHER | No | 5-10 |
| Gothic | Goth | OTHER | **Yes** | 3-5 |
| Georgian | Geor | OTHER | **Yes** | 5-10 |

###### Group B: Expanded scripts (11 additional)

| Script | ISO 15924 | ML Class | OOD? | Target |
|--------|-----------|----------|------|-------:|
| Chinese | Hani | CJK | No | 15-25 |
| Japanese | Jpan | CJK | No | 8-12 |
| Korean | Hang | HANG | No | 8-12 |
| Devanagari | Deva | DEVA | No | 8-12 |
| Bengali | Beng | INDIC_OTHER | No | 5-8 |
| Tamil | Taml | TAML | No | 5-8 |
| Gurmukhi | Guru | INDIC_OTHER | No | 3-5 |
| Sinhala | Sinh | INDIC_OTHER | No | 3-5 |
| Thai | Thai | THAI | No | 5-8 |
| Myanmar | Mymr | SE_ASIAN_OTHER | No | 3-5 |
| Tibetan | Tibt | OTHER | No | 3-5 |

**OOD-reserved scripts**: 4 scripts (Armn, Syrc, Goth, Geor) — same as manuscripts.

##### 2.2 Print Technology Targets

| Technology | Target % | Period |
|-----------|-------:|--------|
| Movable type / letterpress | 30% | 1450-1900 |
| Offset | 25% | 1900-present |
| Digital | 15% | 1980-present |
| Lithography | 10% | 1800-1950 |
| Typewriter | 10% | 1870-1990 |
| Woodblock | 5% | 1450-1600 |

##### 2.3 Time Period Targets

| Period | Date Range | Target % |
|--------|-----------|-------:|
| Incunabula | 1450-1500 | 5-10% |
| Early Modern | 1501-1700 | 15-20% |
| Enlightenment | 1701-1850 | 20-25% |
| Industrial | 1851-1950 | 30-35% |
| Modern | 1951-present | 15-20% |

##### 2.4 Typography Targets

| Typography | Target % |
|-----------|-------:|
| Roman serif | 35% |
| Native script | 25% |
| Blackletter | 15% |
| Mixed | 10% |
| Sans serif | 8% |
| Monospace | 5% |
| Italic | 2% |

##### 2.5 Condition Targets

| Condition | Target % |
|----------|-------:|
| Aged/yellowed | 30% |
| Pristine | 20% |
| Foxed | 15% |
| Ink degraded | 15% |
| Poor scan | 10% |
| Microfilm | 10% |

#### 3. Source Data Inventory

##### 3.1 Source Institutions

| Source | License | Phase | Estimated Yield | API Type |
|--------|---------|-------|-----------------|----------|
| Internet Archive | PD (per-item, pre-1929) | 1 | **181 images** (harvested) | IA download API |
| Wikimedia Commons | Per-image CC0/CC-BY/PD | 1 | 20-50 images | MediaWiki API |
| BnF / Gallica | PD (pre-1850) | 1 | 10-20 images | IIIF manifest |
| Library of Congress | PD (no known restrictions) | 1 | 5-15 images | LOC API |
| HathiTrust | Per-item PD (needs verification) | 2 | 20-40 images | HathiTrust API |
| BSB Munich | Mixed (needs verification) | 2 | 5-10 images | IIIF manifest |
| e-rara | Mixed (needs verification) | 2 | 3-5 images | IIIF manifest |

> **Full license details**: `config/john11_printed_editions_licenses.yaml`

##### 3.2 Key Editions in Catalog

| Edition | Date | Script | Institution | Significance |
|---------|------|--------|-------------|-------------|
| Gutenberg Bible | ~1455 | Latn | IA / Wikimedia | First printed Bible |
| Erasmus Novum Instrumentum | 1516 | Grek | IA | First published Greek NT |
| Ostrog Bible | 1581 | Cyrl | IA | First complete Church Slavonic Bible |
| Amsterdam Armenian Bible | 1666 | Armn | IA | First Armenian printed Bible |
| Van Dyck Arabic Bible | 1867 | Arab | IA | Standard Arabic Protestant Bible |
| Morrison Chinese NT | 1813-23 | Hani | IA | First Chinese printed Bible |
| Carey Bengali NT | 1801 | Beng | IA | First Bengali printed Bible |
| Ziegenbalg Tamil NT | 1714 | Taml | IA | First Tamil printed Bible |
| Judson Burmese Bible | 1832 | Mymr | IA | First Burmese printed Bible |

> **Full catalog**: `config/john11_printed_editions_catalog.yaml` (70 entries, 63 harvested)

#### 4. Training Task Mapping

##### 4a. IQA Training

Printed editions exhibit distinct degradation patterns:

- **Ink bleed**: Letterpress impression marks, ink squash
- **Dot gain**: Halftone dot spread in offset/lithographic printing
- **Registration error**: Color plate misalignment
- **Yellowing/foxing**: Paper aging (shared with manuscripts)
- **Binding shadow**: Gutter darkness from flatbed scanning
- **Bleed-through**: Recto/verso text visibility in thin paper

##### 4b. SigLIP 2 Multi-Task Head Mapping

| Head ID | Head Name | Contribution | Notes |
|---------|-----------|--------------|-------|
| SIG-G2-1 | script_cls | **Primary** | 21 scripts (11 more than manuscripts) |
| SIG-G4-1 | handwriting_presence_cls | **Primary (NONE)** | 100% printed = handwriting NONE class |
| SIG-G4-2 | handwriting_legibility_cls | N/A | Not applicable to printed text |
| SIG-G4-4 | presence_reg | **Primary** | 0.0 presence (no handwriting) |
| SIG-G4-5 | legibility_reg | Informative | Typography-to-legibility mapping |
| SIG-G5-2 | shadow_reg | Variable | Binding shadow from book scanning |
| SIG-G5-3 | warping_reg | Variable | Page curvature from book scanning |

##### 4c. OOD Evaluation

OOD-reserved scripts (Armn, Syrc, Goth, Geor) provide printed-typography OOD evaluation paired with handwritten OOD from manuscripts.

REL domain printed editions extend the domain coverage alongside manuscripts.

##### 4d. Relationship to V4 Font Diversity Strategy

| V4 Synthetic | john11-printed-editions |
|-------------|------------------------|
| SYSTEM tier (Noto, 40%) | Modern digital editions (sans/serif, 15%) |
| REGIONAL tier (Google Fonts, 25%) | Native script typography (CJK, Indic, 25%) |
| STYLISTIC tier (display, 15%) | Blackletter/Fraktur incunabula (15%) |
| HANDWRITING tier (brush, 15%) | N/A (handwriting covered by john11-manuscripts) |
| ADVERSARIAL tier (confusable, 5%) | Historical typography at degradation extremes |

#### 5. Ground Truth Labels

| Label | Source | Confidence | Notes |
|-------|--------|------------|-------|
| script_iso15924 | Catalog metadata | tier_0_exact | Known from edition identification |
| text_content | Biblical text (John 1:1) | tier_0_exact | Same passage in all languages (21 translations) |
| handwriting_presence | Catalog metadata | tier_0_exact | 100% printed = NONE |
| print_technology | Catalog metadata | tier_1_annotation | From scholarly publication data |
| typography | Catalog metadata | tier_1_annotation | From visual inspection |
| domain | Catalog metadata | tier_0_exact | REL (Religious) |
| document_age | Catalog metadata | tier_1_annotation | Publication dates from edition identification |

#### 6. Known Limitations & Issues

- **Partial harvest**: Only 1 of 4 Phase 1 sources (Internet Archive) harvested so far; 181 images from 63/70 catalog entries
- **L2 metadata not yet generated**: 0 Layer 2 enrichment records; enrichment pipeline pending
- **Harvest filter**: `MIN_IMAGE_DIMENSION = 200` filter added to harvest script; no junk detected (smallest image 563px wide)
- **Single passage**: All images depict John 1:1 — risks shortcut learning (same as manuscripts)
- **Internet Archive dependency**: Primary source (60-80% of expected images); IA outages block harvest
- **Page identification challenge**: Must locate John 1:1 within multi-hundred-page books
- **No handwriting variety**: 100% printed = useful only for NONE class, not handwriting training
- **Script imbalance anticipated**: Latin/Greek will dominate; Tibetan/Khmer statistically thin
- **CJK vertical text**: Some CJK editions use top-to-bottom text direction (ttb)
- **License verification burden**: HathiTrust, BSB Munich, e-rara require per-item verification before Phase 2 harvest

#### 7. Harvest Scripts

| Script | Purpose |
|--------|---------|
| `scripts/harvest_john11_printed_editions.py` | Multi-source harvest CLI (IA, Wikimedia, Gallica, LOC) |
| `scripts/enrich_john11_printed_editions.py` | L2 metadata enrichment and validation |
| `scripts/apply_vlm_annotations_john11_printed.py` | VLM degradation annotation |
| `scripts/make_contact_sheets_printed.py` | Contact sheet generation (4 grouping modes) |

#### 8. Configuration Files

| File | Purpose |
|------|---------|
| `config/john11_printed_editions_catalog.yaml` | Edition catalog (70 entries with print-specific metadata) |
| `config/john11_printed_editions_licenses.yaml` | Institution license verification registry (9 institutions) |
| `docs/planning/JOHN11_PRINTED_SAMPLE_PROFILE.md` | Target sample profile framework (5 diversity dimensions) |

#### 9. Registry Files

| File | Purpose |
|------|---------|
| `metadata_registry/john11_printed_editions_registry.jsonl` | Per-image registry (sample_id, SHA256, license, script) |
| `metadata_registry/john11_printed_editions_extended.jsonl` | Extended sidecar (print-specific metadata) |
| `metadata_registry/json/john11-printed-editions/` | Individual L2 JSON records |

#### 10. Citation

Not applicable (assembled dataset from public digital library collections).

#### 11. Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-12 | 0.1 | Initial dataset design: target sample profile, catalog (~55 editions), harvest/enrichment/VLM scripts, documentation |
| 2026-03-13 | 0.2 | Phase 1 partial harvest: 181 images from Internet Archive (63/70 catalog entries), registry populated, catalog expanded to 70 entries, MIN_IMAGE_DIMENSION filter added |
