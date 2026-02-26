#### Muharaf (Arabic Historical Manuscripts)

> **Quick Stats**: 24,952 images (public) | 457 pages + 24,495 lines | Arabic cursive handwriting | Expert transcriptions
>
> **License**: CC BY-NC-SA 4.0 (GitHub/arXiv/NeurIPS); ⚠️ Zenodo record shows **2.0** — browser verification needed | **Commercial Use**: No
>
> **⚠️ LICENSE NOTE (2026-02-24)**: GitHub, arXiv, and NeurIPS listing all state CC BY-NC-SA **4.0**. However, the
> Zenodo record 11492215 (the authoritative file deposit) displayed **CC BY-NC-SA 2.0** when fetched by an
> automated agent. This is likely a Zenodo form entry error, but the deposited record governs the files legally.
> Verify directly at zenodo.org/records/11492215. Additionally, the **restricted portion (759 images) is
> proprietary** — it is NOT CC-licensed; it requires contacting the Phoenix Centre for Lebanese Studies (USEK)
> and signing an ethical use statement before access is granted.

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Muharaf: Manuscripts of Handwritten Arabic Dataset |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | Phoenix Center for Lebanese Studies, USEK |
| **Paper** | [Muharaf Dataset (arXiv:2406.09630)](https://arxiv.org/abs/2406.09630) |
| **Zenodo** | [DOI: 10.5281/zenodo.11492215](https://zenodo.org/records/11492215) |
| **License** | CC BY-NC-SA 4.0 (GitHub/arXiv); ⚠️ Zenodo record shows CC BY-NC-SA **2.0** — verify in browser |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/muharaf/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images (Pages)** | JPG | 457 historical manuscript page scans |
| **Images (Lines)** | PNG | 24,495 cropped text line images |
| **Transcriptions** | TXT | 24,495 expert Arabic transcriptions (UTF-8) |
| **Annotations** | JSON | 3,648 annotation files (line assignments, regions) |
| **Metadata** | XML | 1,216 PAGE XML files with full annotations |

##### 2.2 Dataset Split Locations

> **Split Organization**: No official train/test/val splits provided. All samples in `public/` directory.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **All (Public)** | `public/*.jpg + public/*_*.png` | `public/*.txt + public/*.json + public/*.xml` | 24,952 | ✅ Available |
| **Restricted** | Not publicly available | Contact Phoenix Centre, USEK (requires ethical use statement) | 759 | ❌ Proprietary — not CC |

**Split Organization Pattern**: `single_dir_with_manifest` (all files in one directory)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | TXT | Line-level | Expert Arabic transcriptions (24,495 files, UTF-8) |
| **Bounding Boxes** | PAGE XML | Page/Line/Region | Full polygon coordinates in XML TextRegion/TextLine |
| **Reading Order** | PAGE XML | Page-level | ReadingOrder with OrderedGroup and RegionRefIndexed |
| **Line Assignments** | JSON | Page-level | Line-to-region mappings (3,648 files) |
| **Metadata** | PAGE XML | Page-level | Creator, timestamps, QA info, language, reading direction |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Zenodo README | Version, license, citation, public vs. restricted splits |
| **Image-level** | Filename | Page ID and line ID encoded (e.g., `{page_id}_{line_id}.png`) |
| **Document-level** | PAGE XML (1,216 files) | Image dimensions, text regions, reading order, coordinates |

##### 2.5 Annotation Schema Details

**PAGE XML Format** (W3C standard for historical document annotation):

```xml
<PcGts xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">
  <Metadata>
    <Creator>...</Creator>
    <MetadataItem type="other" value="taggingBy:..."/>
    <MetadataItem type="other" value="transcription_QA:..."/>
  </Metadata>
  <Page imageFilename="..." imageWidth="..." imageHeight="...">
    <ReadingOrder>
      <OrderedGroup id="region_order_0">
        <OrderedGroupIndexed caption="record_0" ...>
          <RegionRefIndexed regionRef="region_0" index="0"/>
        </OrderedGroupIndexed>
      </OrderedGroup>
    </ReadingOrder>
    <TextRegion id="region_0" type="floating">
      <Coords points="x1,y1 x2,y2 ... xn,yn"/>
      <TextLine id="line_0" primaryLanguage="Arabic" production="handwritten-cursive"
                readingDirection="right-to-left" index="0">
        <Coords points="x1,y1 x2,y2 ... xn,yn"/>
        <TextEquiv>
          <Unicode>Arabic text transcription</Unicode>
        </TextEquiv>
      </TextLine>
    </TextRegion>
  </Page>
</PcGts>
```

**JSON Format** (line assignment):

```json
{
  "imagedir": "/path/to/public",
  "imagefile": "{page_id}.jpg",
  "json_filename": "{page_id}_tagged.json",
  "line_dict": {
    "line_1": {"assigned": true, "region": "line_1"},
    "line_2": {"assigned": true, "region": "line_2"}
  }
}
```

**Key Fields for Parsing**:

| Field | Type | Location | Required | Notes |
|-------|------|----------|----------|-------|
| `page_id` | str | Filename | Yes | Page identifier (e.g., `2015 5-03 El-Khouri...`) |
| `line_id` | str | Filename | Yes | Line number within page (e.g., `-1`, `-2`) |
| `transcription` | str | TXT files or XML Unicode | Yes | Arabic text content (UTF-8) |
| `bbox` | polygon | XML Coords | Yes | Polygon points for text regions/lines |
| `reading_order` | list | XML ReadingOrder | Yes | Structured reading order with region groups |
| `language` | str | XML TextLine attribute | Yes | `Arabic` |
| `reading_direction` | str | XML TextLine attribute | Yes | `right-to-left` |
| `production` | str | XML TextLine attribute | Yes | `handwritten-cursive` |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Line transcriptions (TXT) | `text_content.full_text` | **High** | 24,495 UTF-8 TXT files, straightforward parsing |
| ✅ Line transcriptions (XML) | `text_content.full_text` | **High** | Alternative source in PAGE XML Unicode elements |
| ✅ Bounding boxes (XML) | `layout_detections.polygon` | **High** | PAGE XML Coords with full polygon support |
| ✅ Reading order (XML) | `layout_detections.reading_order` | **Medium** | Structured OrderedGroup with region references |
| ✅ Language/script (XML) | `language.language_code` | **High** | Arabic (ara), Arab script, RTL direction |
| ✅ Image dimensions (XML) | `image_metadata.width/height` | **Medium** | Page-level dimensions in XML |
| ⚠️ Line assignments (JSON) | `layout_detections.hierarchy` | **Medium** | Line-to-region mappings (format needs parsing) |
| ⚠️ QA metadata (XML) | `provenance.quality_control` | **Low** | Creator and QA annotator names |
| ❌ Quality scores | - | **Low** | Not provided (can derive from legibility assessment) |
| ❌ Classification labels | - | **Low** | Not provided (handwriting only) |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

**Parser Implementation Priority**: **HIGH** - Rich annotations (PAGE XML standard), expert transcriptions, full polygon support

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Historical Arabic manuscript line transcription |
| **GT Label Coverage** | 100% |

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **Note**: No official train/test/val splits provided. Dataset is unsplit - all public samples in single directory.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **All (Public)** | 24,952 | 25,711 | 100% | ✅ Complete |
| **Restricted** | 759 | 0 | 0% | ❌ Proprietary (contact USEK, ethical use statement required) |
| **Total** | 25,711 | 25,711 | 100% | ✅ Complete (public) |

**Split Status Legend:**

- ✅ Complete - Layer 2 base metadata generated (2026-02-09)
- ❌ Proprietary - Restricted portion requires contacting Phoenix Centre for Lebanese Studies (USEK) and signing an ethical use statement; no redistribution permitted

> **Note**: Layer 2 base metadata generated via `scripts/annotate_base_metadata.py --dataset muharaf` (2026-02-09). 25,711 samples (457 page JPGs + 24,495 line PNGs + auxiliary). 24,495 samples include Arabic transcriptions from paired .txt files.
>
> **Recommendation**: Create custom train/test/val splits for training. Suggested split: 70% train, 15% val, 15% test (stratified by quality tier if legibility annotations added).

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 24,952 (public portion) |
| **Page-Level** | 457 images (JPG) |
| **Line-Level** | 24,495 images (PNG) |
| **Annotation Files** | 3,648 JSON + 1,216 XML |
| **Transcriptions** | 24,495 TXT files |
| **Time Period** | 19th-21st century |
| **Document Types** | Letters, diaries, poems, legal records |
| **Full Dataset** | 25,711 images (1,216 pages) - restricted portion |

##### 4.3 Text Statistics

> **Source**: [NEEDS_PROFILING] - Ground truth transcriptions available (24,495 TXT files)
>
> **Availability**: ✅ Available (pending profiling)

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Character Count** | [NEEDS_PROFILING] | - | - | - |
| **Word Count** | [NEEDS_PROFILING] | - | - | - |
| **Line Length** | [NEEDS_PROFILING] | - | - | - |

**Text Source**: `ground_truth` (expert transcriptions)

**Script**: Arabic (cursive, historical variations, RTL direction)

> **Status**: Layer 2 base metadata generated (2026-02-09). Text profiling statistics pending.
>
> ```bash
> # Calculate text statistics from Layer 2 JSON
> uv run python scripts/calculate_text_statistics.py \
>   --input /mnt/e/image_detection/metadata_registry/json/muharaf_metadata.json
> ```

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Historical documents (letters, diaries, poems, legal records) |
| **Document Types** | Manuscripts (19th-21st century) |
| **Language(s)** | Arabic (100%) |
| **Script** | Arabic (cursive, historical) |
| **Temporal Range** | 19th-21st century (3-century span) |
| **Acquisition Method** | Archival scanning (high-resolution) |

##### 5.1 Class/Category Distribution

| Category | Count | Percentage | Notes |
|----------|-------|------------|-------|
| Page-level scans | 457 | 1.8% | Full manuscript pages (JPG) |
| Line-level crops | 24,495 | 98.2% | Pre-segmented text lines (PNG) |

##### 5.2 Document Type Distribution

> **Note**: Distribution estimated from paper description. Exact counts require XML metadata parsing.

| Document Type | Description | Notes |
|---------------|-------------|-------|
| Letters | Personal correspondence | Historical Lebanese diaspora letters |
| Diaries | Personal records | Daily life documentation |
| Poems | Literary works | Arabic poetry |
| Legal records | Official documents | Contracts, agreements |

##### 5.3 Language & Script Coverage

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Arabic | Arab / ara | 24,952 | 100% | Historical cursive handwriting |

**Script Families Present**: Arabic (Semitic)

**Script Characteristics**:

- **Direction**: Right-to-left (RTL)
- **Style**: Cursive (connected letters)
- **Historical Variations**: Multi-century timespan (19th-21st century)
- **Complexity**: High - contextual letter forms, diacritics
- **Legibility**: Variable (clean to illegible)

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Scanned historical manuscripts (archival quality) |
| **Capture Device** | Archival scanner (high-resolution) |
| **Original Quality** | Variable (clean to heavily degraded) |
| **Compression** | Lossless for pages (JPG), PNG for lines |
| **Known Artifacts** | Aging, bleed-through, ink fading, creases, stains |

##### 6.2 Degradation Sensitivity

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned historical manuscripts |
| **Quality Range** | Clean to illegible (varying quality) |
| **Blur Sensitivity** | **HIGH** - Fine Arabic cursive strokes |
| **Degradation Types** | Aging, bleed-through, ink fading, creases |
| **Script** | Arabic (cursive, historical) |
| **Key Challenge** | RTL script, connected letters, historical variations |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable (historical) | Small text sensitive to blur |
| **Cursive Connectivity** | High (Arabic) | Connected strokes sensitive to breaks |
| **Ink Quality** | Variable (fading) | Contrast critical for legibility |
| **Diacritics** | Common | Small marks easily lost to degradation |
| **Historical Variations** | High (3 centuries) | Style inconsistency challenges OCR |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Arabic handwriting with variable quality, expert transcriptions |
| **Unique Characteristics** | Historical Arabic cursive, multi-century timespan, legibility variation |
| **Complementary Datasets** | HierText (graded legibility), yarmouk (modern Arabic OCR) |
| **Benchmark Suitability** | HIGH - Variable quality ideal for legibility assessment |
| **Known Limitations** | Arabic-only, non-commercial license (CC BY-NC-SA; Zenodo shows 2.0 — verify vs 4.0 per GitHub/arXiv), restricted portion is proprietary (not CC — requires USEK contact + ethical use statement) |

##### 6.5 Benchmark Results

> **Status**: [NEEDS_RESEARCH] - Check paper for published baselines on OCR accuracy or legibility classification.
>
> **Expected Metrics**:
>
> - Character Error Rate (CER) on line transcriptions
> - Word Error Rate (WER)
> - Legibility classification accuracy
>
> **Note**: If paper contains no benchmark results, this subsection can be removed.

##### Legibility Assessment

The dataset explicitly includes **variable quality samples**:

- Clean backgrounds with clear text
- Partially degraded (ink bleed, fading)
- Heavily degraded (creases, stains)
- Near-illegible samples

This makes it ideal for **handwriting legibility training**.

##### Training Value

- **Strengths**: Arabic cursive focus, expert transcriptions, quality variation, historical diversity
- **Weaknesses**: Non-commercial license, Arabic-only
- **Use Case**: Arabic handwriting detection, legibility assessment, OCR training
- **Complementary**: HierText (English scene text), COCO-Text (multi-language scene text)

##### Project Usage

- **Path**: `01_base_data/handwriting/muharaf/`
- **Size**: ~3.4 GB (page data) + ~1.3 GB (line images)
- **Phase(s)**: Phase 9 (handwriting), Phase 10 (multilingual)
- **Purpose**: Arabic handwriting quality, legibility grading, script detection
- **Parser**: ✅ `parse_muharaf_labels` (Arabic metadata, transcription from .txt pairs, page/line classification)

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 24,952 (page + line level, public) |
| **File Format** | JPG (pages), PNG (lines) |
| **Capture Method** | Scanner (Archival quality) |
| **Domain** | HIS (Historical Documents) |
| **Script** | Arabic (Arab) |
| **Content Flags** | Handwriting: ✅ 100%, Historical: ✅ |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/muharaf/` | ✅ Available | 25,711 PNG files |
| **Text/GT** | Native annotations | ✅ Available | TXT + XML: Line-level Arabic transcriptions (24,495 `.txt` files + PAGE XML `<Unicode>`) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/muharaf/` | ✅ Available | Docling GPU: 129 layout batches, 25,711 images |
| **Layer 2 Metadata** | `metadata_registry/json/muharaf_metadata.json` | ✅ Complete | 25,711 samples (2026-02-09) |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: D (81.0/100) | **Auditor**: claude-opus-4-6
> **Grade Cap**: B -> D (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 81.0 | 29% |  |
| Field Validity | 90.2 | 29% |  |
| Doc Completeness | 54.5 | 18% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | 84.0 | 12% |  |
| VLM Accuracy | 95.0 | 12% |  |
| **Overall** | **81.0** | | **Grade D** |

**Grade Cap Applied**:
> Grade capped from B to D: Critical fields below 75%: domain_level1=50%. Language, script, and domain are critical training stratification fields. Datasets with <75% coverage on any of these fields cannot reliably support diversity-aware training splits or balanced sampling. A contact sheet VLM review or enrichment pipeline must bring these fields above 75% before the dataset can advance beyond Grade D.

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/muharaf/](../../scripts/audit/results/muharaf/)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 25,711 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 25,711 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `has_table` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ | — | N/A | No orientation labels; scanned pages assumed upright |
| MNV4-H2 | skew_reg | ❌ | — | N/A | No skew labels; line crops have natural skew but not measured |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~24,495 | tier_3_heuristic | Scanner-captured lines; variable archival quality; pending IQA pipeline |
| SIG-G1-1 | blur_score | 🟡 | ~24,495 | tier_3_heuristic | Variable archival quality (ink fading, aging); IQA labeling pending |
| SIG-G1-2 | noise_score | 🟡 | ~24,495 | tier_3_heuristic | Aging artifacts (stains, foxing) provide noise diversity; IQA pending |
| SIG-G1-3 | contrast_score | 🟡 | ~24,495 | tier_3_heuristic | Ink fading and bleed-through vary contrast; IQA labeling pending |
| SIG-G1-4 | skew_score | ❌ | — | N/A | No skew quality labels; line crops are pre-segmented |
| SIG-G1-5 | compression_score | ❌ | — | N/A | PNG lines + JPG pages — compression artifacts not present |
| SIG-G1-6 | overall_quality | 🟡 | ~24,495 | tier_3_heuristic | Clean-to-illegible quality range ideal for overall quality diversity; IQA pending |
| SIG-G2-1 | script_cls | ✅ | ~24,952 | tier_1_annotation | 100% Arab (ISO 15924); PAGE XML confirms Arabic; CC BY-NC-SA permits non-commercial training |
| SIG-G3-1 | orientation_cls (post) | ❌ | — | N/A | No orientation labels; cannot contribute post-correction orientation |
| SIG-G3-2 | skew_reg (post) | ❌ | — | N/A | No skew labels; cannot contribute post-correction skew residual |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~24,952 | tier_1_annotation | 100% handwritten manuscripts; PAGE XML production="handwritten-cursive"; DOMINANT class |
| SIG-G4-2 | handwriting_legibility_cls | ✅ | ~24,952 | tier_1_annotation | Explicit quality variation (clean to illegible); expert QA metadata; ideal legibility range |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | ~24,952 | tier_1_annotation | PAGE XML production="handwritten-cursive" on all lines; CURSIVE class |
| SIG-G4-4 | presence_reg | ✅ | ~24,952 | derived | All manuscript content is handwriting; area ratio = 1.0 |
| SIG-G4-5 | legibility_reg | 🟡 | ~24,952 | tier_3_heuristic | Legibility score derivable from IQA pipeline; clean-to-illegible range provides full 0-1 coverage |
| SIG-G5-1 | capture_method_cls | ✅ | ~24,952 | tier_1_annotation | 100% archival scanner; stats confirm scanner=25,711 (100%); SCANNER class |
| SIG-G5-2 | shadow_reg | ❌ | — | N/A | Controlled archival scanning; no scanner lid shadows or cast shadows |
| SIG-G5-3 | warping_reg | ❌ | — | N/A | Flat archival scans; no page curl or warping artifacts |
| SIG-G5-4 | code_cls | ❌ | — | N/A | Historical Arabic manuscripts (letters, diaries, poetry); no code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~24,952 | tier_3_heuristic | Archival scanner with variable quality; pending IQA labeling pipeline |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | ARAB only (100%); Arabic cursive historical — excellent Arab representative but single-script |
| 2 | Capture method | ✅ | Archival scanner (100%); aggregate stats confirm scanner=25,711 (100%) |
| 3 | Document domain | ✅ | Multi-domain: PER 12.4%, ADM 26.9%, LEG 6.7%, EDU 1.3%, FIN 1.1%, TEC 0.6%, SCI 0.1%, MED 0.5%; 50.3% UNK pending enrichment |
| 4 | Layout type | 🟡 | Mix of full page scans (457) and pre-segmented text line crops (24,495); no tabular or multi-column layouts |
| 5 | Text density | 🟡 | Line crops are single-line (high text density within crop); page scans vary by manuscript |
| 6 | Degradation types | ✅ | Rich: aging, bleed-through, ink fading, creases, stains — three centuries of real degradation |
| 7 | Resolution/DPI range | 🟡 | Archival high-resolution scanner; DPI varies by scan batch (unquantified); generally high quality |
| 8 | Document age | ✅ | Historical — 19th to 21st century; genuine aged documents (AGED/HISTORICAL categories represented) |
| 9 | Text scope | 🟡 | Line-level (24,495 line crops) + page-level (457 pages); no word or character crops |
| 10 | Content flags | ✅ | has_handwriting=100%, has_signature=100% (aggregate stats confirmed) |
| 11 | Binarization status | 🟡 | Color/grayscale JPEG (pages) and PNG (lines); not binarized |
| 12 | Artifact types | ✅ | Aging, bleed-through, ink fading, creases, stains — comprehensive historical degradation set |
| 13 | Color mode | 🟡 | Grayscale/color scans; manuscript ink on aged paper background (not binarized) |
| 14 | Font variety | ❌ | Handwriting only — Arabic cursive (no printed fonts); historical style variation across 3 centuries |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

Muharaf is the primary Arabic cursive handwriting contributor to all G4 handwriting heads, providing
24,952 expert-annotated images with PAGE XML production metadata confirming cursive type and explicit
quality variation from clean to illegible. The CC BY-NC-SA license (4.0 per GitHub/arXiv; ⚠️ Zenodo shows 2.0 — verify)
permits non-commercial research training, but commercial deployment is restricted; all OOD registry entries should be
flagged `license_restriction=cc-by-nc-sa`. The restricted portion (759 images) is **proprietary** — not CC-licensed;
requires contacting USEK + signed ethical use statement. The 50.3% UNK domain share (aggregate stats) should be
resolved via enrichment before using domain-stratified splits.
