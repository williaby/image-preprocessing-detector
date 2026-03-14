### John 1:1 Multi-Script Manuscripts

> **Quick Stats**: **514 images** (post-curation) | 10 scripts | 4 institutions | 1,700-year span | REL domain | 100% handwritten
>
> **License**: Mixed per-image (CC0, PD, CC-BY-4.0, CC-BY-SA) | **Commercial Use**: Yes (per-image verification)

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | John 1:1 Multi-Script Manuscript Collection |
| **Version** | 1.2 |
| **Release Date** | 2026-03-12 |
| **Maintainer** | Project A team (assembled from 5+ institutions) |
| **Paper** | N/A (assembled dataset from public collections) |
| **Repository** | N/A |
| **License** | Mixed: CC0, Public Domain, CC-BY-4.0 (tracked per-image in registry) |
| **Local Storage** | `data/john11-manuscripts/` (images), `E:\image_detection\` (registry/L2/sidecar) |
| **Documentation Status** | Complete |

**Dataset Description**: A curated collection of 514 historical manuscript images depicting John 1:1 ("In the beginning was the Word...") across 10 writing systems spanning 1,700 years. John 1:1-18 (the Prologue) is the most elaborately decorated and most frequently copied passage in the history of manuscript production, providing the richest possible multi-script manuscript sample from a single textual source.

**Unique value**: Ground truth text content at tier_0_exact confidence for each script — every image depicts a known biblical passage, enabling text_content L2 fields without OCR. Fills the REL (Religious) domain gap in the OOD registry. Provides irreplaceable natural degradation patterns (foxing, ink fading, parchment aging, bleed-through) across 10 scripts.

#### 2. Realized Dataset Diversity (v1.1)

##### 2.1 Script Distribution (10 scripts, 514 images post-curation)

| Script | ISO 15924 | ML Class | OOD? | Target | Achieved | % | Status |
|--------|-----------|----------|------|-------:|--------:|----|--------|
| Latin | Latn | LATN | No | 50 | 177 | 30.7% | EXCEEDED |
| Arabic | Arab | ARAB | No | 10 | 112 | 19.4% | EXCEEDED |
| Armenian | Armn | OTHER | **Yes** | 30 | 80 | 13.9% | EXCEEDED |
| Greek | Grek | GREK | No | 50 | 68 | 11.8% | EXCEEDED |
| Ethiopic | Ethi | OTHER | No | 30 | 49 | 8.5% | EXCEEDED |
| Old Church Slavonic | Cyrs | CYRL | No | 10 | 25 | 4.3% | EXCEEDED |
| Gothic | Goth | OTHER | **Yes** | all | 25 | 4.3% | COMPLETE |
| Coptic | Copt | OTHER | No | 10 | 15 | 2.6% | EXCEEDED |
| Georgian | Geor | OTHER | **Yes** | all | 15 | 2.6% | COMPLETE |
| Syriac | Syrc | OTHER | **Yes** | 10 | 11 | 1.9% | EXCEEDED |

**OOD-reserved scripts**: 4 scripts — Armn, Geor, Goth, Syrc. (Exact post-curation counts to be recalculated.)
**Text direction**: Predominantly LTR; RTL from Arab + Syrc.

##### 2.2 Institution & License Distribution

| Institution | Count | % | License |
|-------------|------:|---:|---------|
| Wikimedia Commons | 404 | 78.6% | PD / CC-BY-SA / CC-BY-4.0 |
| Walters Art Museum | 89 | 17.3% | CC0 |
| BnF / Gallica | 19 | 3.7% | Public Domain |
| Met Museum | 2 | 0.4% | CC0 |

**License breakdown**: Post-curation; exact per-license counts to be recalculated from registry.

##### 2.3 Quality Score Distribution

| Metric | Value |
|--------|-------|
| Mean | 0.665 |
| Median | 0.68 |
| Std Dev | 0.149 |
| Range | [0.05 – 0.95] |

| Script | Mean Q | Min Q | Max Q |
|--------|-------:|------:|------:|
| Latn | 0.754 | 0.420 | 0.920 |
| Ethi | 0.710 | 0.450 | 0.850 |
| Cyrs | 0.709 | 0.350 | 0.910 |
| Copt | 0.707 | 0.500 | 0.880 |
| Syrc | 0.678 | 0.600 | 0.740 |
| Geor | 0.645 | 0.200 | 0.950 |
| Armn | 0.623 | 0.050 | 0.910 |
| Arab | 0.588 | 0.300 | 0.880 |
| Grek | 0.586 | 0.200 | 0.880 |
| Goth | 0.576 | 0.300 | 0.820 |

##### 2.4 Degradation Patterns

| Degradation | Count | % |
|-------------|------:|---:|
| Yellowing | 484 | 83.9% |
| Fading | 420 | 72.8% |
| Staining | 332 | 57.5% |
| Ink fading | 96 | 16.6% |
| Tears | 56 | 9.7% |
| None | 44 | 7.6% |
| Water damage | 42 | 7.3% |
| Foxing | 30 | 5.2% |
| Bleed-through | 25 | 4.3% |

##### 2.5 Layout Types

| Layout | Count | % |
|--------|------:|---:|
| Single column | 250 | 43.3% |
| Illuminated page | 180 | 31.2% |
| Double column | 67 | 11.6% |
| Fragment | 53 | 9.2% |
| Multi-column | 23 | 4.0% |
| Marginal notes | 4 | 0.7% |

##### 2.6 Capture Method & Technical Profile

| Capture Method | Count | % |
|----------------|------:|---:|
| Digital photography | 527 | 91.3% |
| Flatbed scan | 37 | 6.4% |
| Microfilm scan | 7 | 1.2% |
| Screen capture | 6 | 1.0% |

**Resolution**: 72.6% sub-300 DPI (mean ~199 DPI). 27.4% at standard (300+) or high resolution.

##### 2.7 Handwriting & Legibility

| Legibility | Count | % |
|------------|------:|---:|
| FAIR | 243 | 42.1% |
| GOOD | 222 | 38.5% |
| POOR | 66 | 11.4% |
| EXCELLENT | 40 | 6.9% |
| ILLEGIBLE | 6 | 1.0% |

**Handwriting presence**: 100% DOMINANT. **Orientation**: 100% class 0 (upright).

##### 2.8 Annotation Methodology

- **495 images (85.8%)**: Per-image VLM annotations (claude-sonnet-4.6 via 6x5 contact sheet grids)
- **82 images (14.2%)**: Script-average defaults (Arab 52, Latn 30 — VLM refused contact sheets)
- **Label source tracking**: `annotation_source` field distinguishes `vlm` vs `script_default`

#### 3. Source Data Inventory

> **Purpose**: Documents what the original sources provide, enabling harvest script development.

##### 3.1 Provided File Types

| Source | Format | Resolution | License | Harvested |
|--------|--------|------------|---------|-----------|
| Wikimedia Commons | JPEG/PNG/TIFF | Variable (web to museum-quality) | Per-image CC0/CC-BY/PD/CC-BY-SA | 404 |
| Walters Art Museum | JPEG | High-res | CC0 | 89 |
| BnF/Gallica IIIF | JPEG (from IIIF) | Variable | PD (pre-1850) | 19 |
| Met Museum Open Access | JPEG | High-res (2000-4000px) | CC0 | 2 |

##### 3.2 Script Coverage (Realized)

| Script | ISO 15924 | ML Class | OOD? | Achieved | Primary Sources |
|--------|-----------|----------|------|----------|-----------------|
| Latin | Latn | LATN | No | 177 | Wikimedia, Gallica, Walters |
| Arabic | Arab | ARAB | No | 112 | Walters CC0, Wikimedia |
| Armenian | Armn | OTHER | Yes | 80 | Walters CC0, Met CC0, Wikimedia |
| Greek | Grek | GREK | No | 68 | Wikimedia, Gallica |
| Ethiopic | Ethi | OTHER | No | 49 | Wikimedia |
| Old Church Slavonic | Cyrs | CYRL | No | 25 | Wikimedia |
| Gothic | Goth | OTHER | Yes | 25 | Wikimedia (Codex Argenteus) |
| Coptic | Copt | OTHER | No | 15 | Gallica, Wikimedia |
| Georgian | Geor | OTHER | Yes | 15 | Wikimedia |
| Syriac | Syrc | OTHER | Yes | 11 | Walters CC0 |

#### 4. Training Task Mapping

##### 4a. IQA Training

Historical manuscripts exhibit natural degradation patterns:

- **Foxing**: Age spots on parchment/paper
- **Ink fading**: Variable ink density across centuries
- **Bleed-through**: Recto/verso text visibility
- **Parchment aging**: Color shifts, staining, damage
- **Palimpsest layers**: Overwritten text (Codex Ephraemi)

##### 4b. SigLIP 2 Multi-Task Head Mapping

| Head ID | Head Name | Contribution | Notes |
|---------|-----------|--------------|-------|
| SIG-G2-1 | script_cls | Primary | 10 scripts: Grek, Latn, Ethi, Armn, Syrc, Arab, Cyrs, Copt, Goth, Geor |
| SIG-G4-1 | handwriting_presence_cls | Primary | 100% handwritten |
| SIG-G4-2 | handwriting_legibility_cls | Primary | Script-style-to-legibility mapping |
| SIG-G4-4 | presence_reg | Primary | DOMINANT presence (>=0.95) |
| SIG-G4-5 | legibility_reg | Primary | Continuous 0.25-0.80 per script style |
| SIG-G5-2 | shadow_reg | Negatives | Museum scans, minimal shadow |
| SIG-G5-3 | warping_reg | Negatives | Flat scans |

##### 4c. OOD Evaluation

OOD-reserved scripts (Armn, Geor, Goth, Syrc) registered in `metadata_registry/ood_registry.jsonl` with `ood_categories: ["ood_script", "ood_domain"]`.

REL domain images fill the domain gap (previously 0 REL images in OOD registry).

#### 5. Ground Truth Labels

| Label | Source | Confidence | Notes |
|-------|--------|------------|-------|
| script_iso15924 | Catalog metadata | tier_0_exact | Known from manuscript identification |
| text_content | Biblical text (John 1:1) | tier_0_exact | Same passage in all scripts |
| handwriting_presence | Visual inspection | tier_0_exact | 100% handwritten manuscripts |
| handwriting_legibility | Script style mapping | tier_1_annotation | uncial=GOOD, cursive=FAIR |
| domain | Catalog metadata | tier_0_exact | REL (Religious) |
| document_age | Catalog metadata | tier_1_annotation | Date ranges from manuscript identification |

#### 6. Known Limitations & Issues

- **Historical only**: No contemporary manuscripts (all pre-19th century)
- **Single passage**: All images depict John 1:1 — risks shortcut learning via layout/ornament cues correlated with script
- **No orientation variety**: 100% class 0 (upright) — orientation augmentation required during training
- **Sub-300 DPI majority**: 72.6% below 300 DPI (mean ~199) — confounds legibility with resolution
- **Script imbalance**: Latin (30.7%) and Arabic (19.4%) dominate; Syriac (11) and Georgian (15) statistically thin for per-script OOD evaluation
- **VLM annotation noise**: Quality scores derived from contact sheet grids (downsampled), not full-resolution per-image analysis; 82 images (14.2%) use script-average defaults
- **Wikimedia source bias**: 78.6% from single aggregator — may encode specific compression/color processing pipeline
- **CC-BY-SA subset**: 10.2% (59 images) carry ShareAlike obligations — quarantine for commercial use evaluation
- **Binary degradation labels**: Presence/absence only, no severity grading (e.g., "mild" vs "severe" yellowing)
- **Quarantined content**: 61 unsuitable files removed during v1.2 curation — web scraping artifacts (small images <200px, font/UI screenshots), non-manuscript content (architecture photos, ceramic tiles, monuments), wrong biblical books, and Hildebrandslied (non-John 1:1). Plus 2 duplicate Met registry entries. All moved to `data/john11-manuscripts/_quarantined/`

#### 7. Harvest Scripts

| Script | Purpose |
|--------|---------|
| `scripts/harvest_john11_manuscripts.py` | Multi-source harvest CLI (Wikimedia, Met, Walters, Gallica, IA). `MIN_IMAGE_DIMENSION=200` filter added post-curation. |
| `scripts/enrich_john11_manuscripts.py` | L2 metadata enrichment and validation |
| `scripts/quarantine_john11_junk.py` | Quarantine unsuitable files (junk, duplicates, wrong content) to `_quarantined/` |

#### 8. Configuration Files

| File | Purpose |
|------|---------|
| `config/john11_manuscript_catalog.yaml` | Manuscript catalog with per-item metadata |
| `config/john11_source_licenses.yaml` | Institution license verification registry |

#### 9. Registry Files

| File | Count | Purpose |
|------|------:|---------|
| `metadata_registry/john11_manuscripts_registry.jsonl` | 514 | Per-image registry (sample_id, SHA256, license, script) |
| `metadata_registry/john11_manuscripts_extended.jsonl` | 514 | Extended sidecar (manuscript-historical metadata) |
| `metadata_registry/json/john11-manuscripts/` | 514 | Individual L2 JSON records |
| `data/john11-manuscripts/_quarantined/` | 61 | Quarantined junk files (images + registry/sidecar backups) |

#### 10. Citation

Not applicable (assembled dataset from public institutional collections).

#### 11. Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-13 | 1.2 | Data curation: quarantined 61 junk files + 2 duplicate registry entries (577→514). Added `MIN_IMAGE_DIMENSION=200` harvest filter. Registry/L2/sidecar synced to 514. Added `quarantine_john11_junk.py`. |
| 2026-03-12 | 1.1 | Added realized diversity statistics (577 images), per-image VLM annotations, consensus review findings |
| 2026-03-11 | 1.0 | Initial dataset design, catalog, and harvest/enrichment scripts |
