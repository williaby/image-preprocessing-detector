#### Muharaf (Arabic Historical Manuscripts)

> **Quick Stats**: 24,952 images (public) | 457 pages + 24,495 lines | Arabic cursive handwriting | Expert transcriptions
>
> **License**: CC BY-NC-SA 4.0 | **Commercial Use**: Research Only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Muharaf: Manuscripts of Handwritten Arabic Dataset |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | Phoenix Center for Lebanese Studies, USEK |
| **Paper** | [Muharaf Dataset (arXiv:2406.09630)](https://arxiv.org/abs/2406.09630) |
| **Zenodo** | [DOI: 10.5281/zenodo.11492215](https://zenodo.org/records/11492215) |
| **License** | CC BY-NC-SA 4.0 (Public portion) |
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
| **Restricted** | Not publicly available | Request from maintainers | 759 | ❌ Restricted access |

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

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **Note**: No official train/test/val splits provided. Dataset is unsplit - all public samples in single directory.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **All (Public)** | 24,952 | 0 | 0% | ❌ Not processed |
| **Restricted** | 759 | 0 | 0% | ❌ Not publicly available |
| **Total** | 25,711 | 0 | 0% | ❌ Pending annotation |

**Split Status Legend:**

- ❌ Not processed - Layer 2 metadata not yet generated
- ❌ Not publicly available - Restricted portion requires contacting maintainers

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

> **Action Required**: Run text profiling after parser implementation:
>
> ```bash
> # Generate Layer 2 metadata with parser
> uv run python scripts/annotate_base_metadata.py --dataset muharaf
>
> # Calculate text statistics from Layer 2 JSON
> uv run python scripts/calculate_text_statistics.py \
>   --input /mnt/e/image_detection/metadata_registry/json/muharaf_layer2.json
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
| **Known Limitations** | Arabic-only, non-commercial license, restricted portion not available |

##### 6.5 Benchmark Results

> **Status**: [NEEDS_RESEARCH] - Check paper for published baselines on OCR accuracy or legibility classification.
>
> **Expected Metrics**:
>
> - Character Error Rate (CER) on line transcriptions
> - Word Error Rate (WER)
> - Legibility classification accuracy

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
- **Parser**: ❌ Pending implementation

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

| Component | Path |
|-----------|------|
| **All Data** | `01_base_data/handwriting/muharaf/public/` |
| **Page Images** | `*.jpg` (457 files) |
| **Line Images** | `*_*.png` (24,495 files) |
| **Transcriptions** | `*_*.txt` (24,495 files) |
| **JSON Annotations** | `*.json` (3,648 files) |
| **XML Metadata** | `*.xml` (1,216 files) |

---
