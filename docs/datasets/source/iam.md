#### IAM Handwriting Database

> **Quick Stats**: 130,212 images | 657 writers | Forms, lines, words | Ground truth text + XML bboxes
>
> **License**: Research | **Commercial Use**: Research Only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | IAM Handwriting Database |
| **Version** | 3.0 |
| **Release Date** | 2002 (updated 2004) |
| **Maintainer** | FKI Research Group, University of Bern (now HEIA-FR) |
| **Website** | [IAM Handwriting Database](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database) |
| **Paper** | [The IAM-database: an English sentence database for offline handwriting recognition (IJDAR 2002)](https://link.springer.com/article/10.1007/s100320200071) |
| **License** | Research Use Only (registration required) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/iam_handwriting/` |
| **Documentation Status** | Partial (missing parser implementation, split files) |

##### Source Data Inventory

**Official Counts** [Official]:

- Forms: 1,539 pages
- Text Lines: 13,353
- Words: 115,320
- Sentences: 5,685 unique
- Writers: 657

**Empirically Derived** [Empirically Derived]:

- Total PNG files: 130,212 (1,539 forms + 13,353 lines + 115,320 words)
- XML annotations: 1,539 files (one per form)
- TXT annotations: 4 files (forms, lines, sentences, words)

**Split Information** [Official]:

Standard evaluation protocol: "Large Writer Independent Text Line Recognition Task"

| Split | Text Lines | Writers | Notes |
|-------|-----------|---------|-------|
| Training | 6,161 | 283 | Writer-independent |
| Validation 1 | 900 | 46 | Writer-independent |
| Validation 2 | 940 | 43 | Writer-independent |
| Test | 1,861 | 128 | Writer-independent |
| **Total Used** | 9,862 | 500 | Mutually exclusive writers |
| Unused | 3,491 | 157 | Remaining data |

**Split Pattern**: `by_file_list` (expected - split files not present in download)

**Split Status**: [NEEDS_VERIFICATION] Split definition files need to be located or generated from writer IDs

##### Dataset Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Total Images** | 130,212 | [Empirically Derived] |
| **Forms (Full Pages)** | 1,539 | [Official] |
| **Lines** | 13,353 | [Official] |
| **Words** | 115,320 | [Official] |
| **Writers** | 657 | [Official] |
| **Sentences** | 5,685 unique | [Official] |
| **Format** | PNG (grayscale, 300 DPI) | [Official] |
| **Total Size** | 6.4 GB | [Empirically Derived] |

##### Content Composition

**Data Hierarchy**:

| Level | Count | Description |
|-------|-------|-------------|
| **Forms** | 1,539 | Full handwritten pages (aXX-YYY format) |
| **Lines** | 13,353 | Individual text lines with bounding boxes |
| **Words** | 115,320 | Segmented words with transcriptions |
| **Components** | ~1M+ | Stroke-level components (in XML) |

**Text Content**: Lancaster-Oslo/Bergen (LOB) corpus

- 5,685 unique English sentences
- Writers copied sentences from printed prompts
- Forms contain both machine-printed prompts and handwritten text

##### Annotation Format

| Annotation Type | Format | Content |
|-----------------|--------|---------|
| **Text Labels** | TXT (`ascii/`) | Transcriptions for forms, lines, sentences, words |
| **Bounding Boxes** | XML (`xml/`) | Per-page word/line coordinates |
| **Line Format** | `lines.txt` | `id ok graylevel components x,y,w,h transcription` |

**Sample lines.txt entry**:

```text
a01-000u-00 ok 154 19 408 746 1663 91 A|MOVE|to|stop|Mr.|Gaitskell|from
```

##### IQA Profile

| Characteristic | Rating | Notes |
|----------------|--------|-------|
| **Blur Sensitivity** | Medium | Handwriting clarity varies by writer |
| **Contrast Sensitivity** | High | Grayscale scans, ink density varies |
| **Noise Tolerance** | Medium | Some scan artifacts present |
| **Primary Degradation** | Writer variability | Different handwriting styles |
| **DPI** | 300 | Consistent across all forms |

##### Project Usage

**Training Purpose**:

- Handwriting recognition and text detection
- Writer identification and style analysis
- Segmentation quality assessment

**Project Phases**:

- Phase 3: Handwriting detection training
- Phase 10A: Writer identification, handwriting style analysis

**Parser Status**: ❌ Not Implemented (see Parser & Metadata Integration section)

##### Parser & Metadata Integration

**Parser Status**: ❌ Not Implemented

**Expected Location**: `src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py`

**Required Capabilities**:

1. XML parsing for word-level bounding boxes and hierarchical structure
2. TXT parsing for line-level bounding boxes and transcriptions
3. Writer ID extraction and mapping to splits
4. Multi-level annotation aggregation (form → line → word → component)
5. POS tag extraction from XML

**Schema-Derived Comparison Matrix**:

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| XML word bboxes (XYWH) | layout_detections.bbox | ❌ No | High | Component-level in XML |
| TXT line bboxes (XYWH) | layout_detections.bbox | ❌ No | High | Ready in ascii/lines.txt |
| Word transcriptions | text_content.full_text | ❌ No | High | Available in XML + TXT |
| Text source type | text_content.source_type | ❌ No | High | Should be "ground_truth" |
| Writer ID | provenance.writer_id | ❌ No | Medium | Available in forms.txt |
| Segmentation status | quality.segmentation_ok | ❌ No | Medium | ok/err flag in TXT files |
| POS tags | entities.pos_tags | ❌ No | Low | Available in XML |
| Split assignment | provenance.split | ❌ No | High | Requires split file generation |

**Gap Analysis**: Parser implementation required for Layer 2 integration. All source data available but not currently extracted.

##### Data Locations

| Data Type | Path |
|-----------|------|
| **Local Path** | `01_base_data/handwriting/iam_handwriting/` |
| **Images** | Root + `a01/`, `a02/`, etc. subdirectories (77 writer directories) |
| **ASCII Labels** | `ascii/forms.txt`, `ascii/lines.txt`, `ascii/words.txt`, `ascii/sentences.txt` |
| **XML Annotations** | `xml/*.xml` (1,539 files, one per form) |
| **GCS Backup** | `gs://image_detection_b/image-preprocessing-detector/datasets/iam_handwriting/` |

##### Known Issues

**Segmentation Quality** [Official]:

- Some lines have segmentation errors (marked as `err` status in `lines.txt`)
- Forms marked with `prt` (partial) vs `all` (complete) segmentation flags
- Example: Form `a01-000u` has 7 lines total, only 5 correctly segmented

**Missing Data**:

- Writer directory gaps (e.g., c05, d02 missing) suggest excluded or lost data
- Split definition files not included in standard download (requires separate acquisition or generation)

**Writer Variability**:

- Handwriting quality varies significantly across 657 writers
- Some writers have very few samples, others have extensive contributions
- Variable ink density and writing styles affect IQA consistency

##### Dataset-Specific Notes

**Annotation Hierarchy**:

The IAM dataset provides multi-level annotations with component-level granularity:

- **Forms**: Full page scans with machine-printed prompts + handwritten text
- **Lines**: Text line segmentation with bounding boxes
- **Words**: Individual word segmentation with POS tags
- **Components**: Stroke-level components (unique to IAM, most datasets stop at word level)

**XML Component Structure Example**:

```xml
<word id="a01-000u-00-01" tag="NN" text="MOVE">
  <cmp x="507" y="768" width="63" height="46" />
  <cmp x="568" y="770" width="56" height="41" />
  <cmp x="631" y="768" width="38" height="41" />
  <cmp x="676" y="772" width="31" height="36" />
  <cmp x="691" y="766" width="29" height="12" />
</word>
```

Each word can have multiple `<cmp>` (component) elements representing individual strokes.

**POS Tagging**:

XML annotations include part-of-speech tags for each word (AT, NN, TO, VB, NPT, NP, IN, etc.) which could be useful for linguistic analysis.

**Binarization Metadata**:

The `lines.txt` file includes optimal binarization thresholds (gray level) for each line, useful for preprocessing experiments.

**Usage Recommendations**:

- Use line-level annotations for standard handwriting recognition benchmarks (9,862 lines in official split)
- Use word-level for detailed segmentation studies (115,320 words)
- Use component-level for stroke analysis research (unique capability)
- Respect writer-independent splits to ensure fair evaluation

---
