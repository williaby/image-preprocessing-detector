---
owner: docs-team
purpose: Ground truth label provenance and annotation methodology summary.
schema_type: common
status: active
tags:
- datasets
- ground_truth
- annotation
- provenance
title: Ground Truth Label Summary
---

> **Version**: 1.0.0
> **Last Updated**: 2026-02-14
> **Purpose**: Centralized summary of ground truth label provenance across all datasets
> **Token Optimized**: ~600 lines, ~6K tokens
> **Usage**: Start here for "How was this dataset annotated?" or "Which datasets have human labels?"

---

## Annotation Method Legend

| Code | Method | Provenance Tier | Description |
|------|--------|----------------|-------------|
| **HUM** | Human Expert | Tier 1 | Trained or expert annotators with quality review |
| **CWD** | Crowdsourced | Tier 1 | Crowd workers with aggregated consensus |
| **SYN** | Synthetic | Tier 0 | Generated programmatically (rendering, LaTeX, simulation) |
| **AUT** | Automatic Extraction | Tier 0/1 | Programmatic extraction from structured source (PDF/XML/HTML) |
| **PAR** | Paired GT | Tier 0 | Clean reference image paired with degraded input |
| **MIX** | Mixed Methods | varies | Combination of above methods |

**Provenance Tier Reference** (from `annotation/schemas/enums.py`):

- **Tier 0 (Exact)**: Dataset IS 100% this content type by construction
- **Tier 1 (Annotation)**: Derived from human COCO/JSON annotations
- **Tier 2 (Model)**: Derived from ML model inference (e.g., DocLayout-YOLO)
- **Tier 3 (Heuristic)**: Dataset-level defaults only

---

## Summary Statistics

| Annotation Method | Datasets | Images | Notes |
|-------------------|---------|--------|-------|
| **HUM** (Human Expert) | 22 | ~880K | Competition, expert, trained annotators |
| **CWD** (Crowdsourced) | 2 | ~169K | hasy (write-math), ocr-quality |
| **SYN** (Synthetic) | 6 | ~631K | Rendering, LaTeX, simulation, chemical structures |
| **AUT** (Automatic) | 8 | ~765K | PDF/XML/HTML extraction |
| **PAR** (Paired GT) | 9 | ~37K+ | Correction/dewarping datasets |
| **MIX** (Mixed) | 6 | ~54K | Combined methods |
| **Unknown/Blocked** | 5 | ~21K+ | GT via Layer 2 only or dataset blocked |
| **Text Corpora** | 2 | N/A | openlid-v2, wili-2018 |

---

## Ground Truth by Training Task

### IQA Training

| Dataset | Images | GT Labels | Method | IAA | Key Details |
|---------|--------|-----------|--------|-----|-------------|
| [ohr-bench](source/ohr-bench.md) | 8,561 | Quality scores (0-100) | AUT | N/A | Born-digital PDF extraction, 7 domain categories |
| [diqa-5000](source/diqa-5000.md) | 5,500 | Quality MOS (1-5, 3-dim) | CWD | 15 subjects | 15-subject consensus: overall, sharpness, color_fidelity |
| [realdae](source/realdae.md) | 1,200 | Paired GT (before/after) | PAR | N/A | 600 camera/flatbed pairs, implicit quality via pairing |
| [ocr-quality](source/ocr-quality.md) | 1,000 | Quality scores | CWD | [NEEDS_VERIFICATION] | Human quality ratings, multilingual |
| [q-doc](source/q-doc.md) | 4,260 | Quality scores | [NEEDS_VERIFICATION] | [NEEDS_VERIFICATION] | Camera-captured, MOS or objective metrics |

### Layout Detection

| Dataset | Images | GT Labels | Method | IAA | Key Details |
|---------|--------|-----------|--------|-----|-------------|
| [doclaynet](source/doclaynet.md) | 81,471 | Layout boxes (11 cls), Text, Domain | HUM | ~90% subset | Expert annotators, double/triple annotated subset, COCO format |
| [pubtabnet](source/pubtabnet.md) | 519,030 | Table structure + cells, Text | AUT | N/A | Automatic PDF/XML matching from PubMed Central |
| [tablebank](source/tablebank.md) | 260,025 | Table detection boxes | AUT | N/A | Automatic extraction from Word/LaTeX source documents |
| [fintabnet](source/fintabnet.md) | 97,475 | Table structure + cells | AUT | N/A | Automatic extraction from financial PDFs |
| [docsynth](source/docsynth.md) | 300,000 | Layout boxes (74 cls) | SYN | N/A | Synthetically generated documents, exact by construction |
| [funsd](source/funsd.md) | 199 | Layout boxes, NER, Entity links | HUM | [NEEDS_VERIFICATION] | Human annotated forms, 4 entity types |
| [funsd-plus](source/funsd-plus.md) | 1,139 | Layout boxes, Text | MIX | [NEEDS_VERIFICATION] | Extended FUNSD with additional annotations |
| [sroie](source/sroie.md) | 973 | Quad boxes, Text, Entities | HUM | N/A | ICDAR 2019 competition, receipt key-value extraction |
| [hiertext](source/hiertext.md) | 11,641 | Word/line/paragraph boxes, Text | HUM | [NEEDS_VERIFICATION] | Google Research, word-level handwritten + legible flags |
| [indicdlp](source/indicdlp.md) | 119,000 | Layout boxes (42 cls), Language tags | HUM | [NEEDS_VERIFICATION] | 12 Indian languages, COCO format |

### Text Detection & Script Classification

| Dataset | Images | GT Labels | Method | IAA | Key Details |
|---------|--------|-----------|--------|-----|-------------|
| [mlt19](source/mlt19.md) | 19,993 | Word boxes, Language (10 cls) | HUM | N/A | ICDAR 2019 competition, per-word language annotation |
| [mdiw13](source/mdiw13.md) | 290,213 | Word/line/doc script (13 cls) | HUM | N/A | Competition dataset, multi-level script identification |
| [siw13](source/siw13.md) | 16,291 | Script classification (13 cls) | HUM | N/A | Script identification in the wild |
| [coco-text](source/coco-text.md) | 123,287 | Word boxes, Legibility, Class | HUM | N/A | Scene text: machine printed vs handwritten + legibility |
| [cvsi](source/cvsi.md) | 10,715 | Script labels (10 cls) | HUM | N/A | Video scene text, frame-level script classification |
| [mle2e](source/mle2e.md) | 1,816 | Word boxes, Script (4 cls) | HUM | N/A | Latin/Chinese/Korean/Kannada pre-segmented crops |
| [cc-ocr](source/cc-ocr.md) | 6,533 | Text, Document-level labels | HUM | N/A | Complex CJK benchmark with multi-task annotation |
| [hindi-synth](source/hindi-synth.md) | 80,009 | Text transcription, Script | SYN | N/A | Programmatic Hindi/Devanagari rendering, exact by construction |
| [arabic-docs](source/arabic-docs.md) | 10,045 | Title text, OCR text | MIX | N/A | Human title annotation + OCR extraction |

### Handwriting Detection

| Dataset | Images | GT Labels | Method | IAA | Key Details |
|---------|--------|-----------|--------|-----|-------------|
| [iam](source/iam.md) | 130,212 | Word/line transcriptions | HUM | N/A | 657 writers, largest English handwriting corpus |
| [hasy](source/hasy.md) | 168,233 | Symbol class (369 cls) | CWD | N/A | Crowdsourced via write-math.com, math symbols |
| [nist-sd19](source/nist-sd19.md) | 3,669 | Character class | HUM | N/A | NIST standard handwriting (digits + letters) |
| [nist-sd6](source/nist-sd6.md) | 5,595 | Form fields + handprint | MIX | N/A | Synthesized tax forms with real handwriting overlays |
| [muharaf](source/muharaf.md) | 25,711 | Line transcriptions | HUM | N/A | Arabic cursive historical manuscripts |
| [pucit-ohul](source/pucit-ohul.md) | 7,401 | Line text | HUM | N/A | Urdu handwriting, line-level transcription |
| [tibhcr](source/tibhcr.md) | 141,698 | Character class (47 cls) | HUM | N/A | Tibetan handwriting, 235 writers |
| [nepali-handwritten](source/nepali-handwritten.md) | 958 | Character class | HUM | N/A | Devanagari handwriting |
| [dzongkha-digits](source/dzongkha-digits.md) | 62 | Digit class (10 cls) | HUM | N/A | Dzongkha handwritten digits, 100 writers |

### Correction / Dewarping / Shadow Removal

| Dataset | Images | GT Labels | Method | IAA | Key Details |
|---------|--------|-----------|--------|-----|-------------|
| [sd7k](source/sd7k.md) | 7,239 | Paired GT (shadow/shadow-free) | PAR | N/A | Shadow removal pairs |
| [wsrd](source/wsrd.md) | 4,500 | Paired GT (shadow/shadow-free) | PAR | N/A | Shadow removal pairs |
| [anyphotodoc6300](source/anyphotodoc6300.md) | 6,306 | Paired GT (corrected/distorted) | PAR | N/A | Dewarping pairs |
| [warpdoc](source/warpdoc.md) | 1,020 | Paired GT (warped/flat) | PAR | N/A | 6 distortion types documented |
| [docreal](source/docreal.md) | 200 | Paired GT (distorted/scanned) | PAR | N/A | Camera + flatbed scanner pairs, MIT license |
| [docalign12k](source/docalign12k.md) | ~12,000 | Paired GT (aligned/unaligned) | PAR | N/A | Alignment pairs, language enrichment pending |
| [drccbi](source/drccbi.md) | Unknown | Paired GT (warped/flat) | PAR | N/A | Camera-captured dewarping pairs |
| [staindoc](source/staindoc.md) | ~5,000 | Paired GT (stained/clean) | PAR | N/A | Stain removal pairs, camera-captured |
| [doc3d](source/doc3d.md) | 102,064 | Depth maps, UV coords, Normals | SYN | N/A | Synthetic 3D warped documents, 7 GT types |

### Specialized

| Dataset | Images | GT Labels | Method | Key Details |
|---------|--------|-----------|--------|-------------|
| [financebench](source/financebench.md) | 54,121 | QA text, Document metadata | AUT | Born-digital financial PDF extraction |
| [multimodal-textbook](source/multimodal-textbook.md) | 1,113 | Text, Diagram labels | AUT | PDF extraction, STEM content |
| [im2latex](source/im2latex.md) | 10,000 | LaTeX source | SYN | Rendered LaTeX formula images |
| [mathverse](source/mathverse.md) | 6,940 | VQA labels, Math problems | MIX | Rendered math + human VQA annotation |
| [midv500](source/midv500.md) | 3,612 | Document type, Text | HUM | 50 countries, identity documents |
| [smartdoc-qa](source/smartdoc-qa.md) | 4,280 | QA pairs, Document text | HUM | Mobile capture, question-answer GT |
| [signatr6k](source/signatr6k.md) | 12,514 | Text segmentation masks | HUM | Signature detection dataset |
| [invoices-kg](source/invoices-kg.md) | 1,414 | Text, Key-value entities | MIX | Invoice extraction, mixed annotation |
| [omnidocbench](source/omnidocbench.md) | 1,358 | Multi-task labels | HUM | Comprehensive benchmark annotation |
| [tobacco800](source/tobacco800.md) | 1,290 | Document classification | HUM | IIT-CDIP archival, 10 document types |
| [rvl-cdip](source/rvl-cdip.md) | 16,000 | Document class (16 cls) | HUM | Scanned document classification |
| [yarmouk](source/yarmouk.md) | 15,062 | OCR text | HUM | Arabic document OCR ground truth |
| [jssoda](source/jssoda.md) | 2,000 | Text, Orientation | SYN | Synthetic Japanese OCR, orientation labels |
| [nist-sd2](source/nist-sd2.md) | 5,590 | Form fields, Text | SYN | Synthesized IRS 1040 tax forms |
| [bhutan-afs](source/bhutan-afs.md) | 135 | None (enrichment only) | -- | Annual reports, GT via Layer 2 only |
| [dibco](source/dibco.md) | 212 | Binarization GT masks | HUM | Competition binarization ground truth |
| [document-haystack](source/document-haystack.md) | 400 | Relevance pairs (8,250 queries) | HUM | Amazon Science retrieval benchmark |
| [markushgrapher](source/markushgrapher.md) | 235,000 | Chemical structures (SMILES + graph) | SYN | Programmatic generation, DS4SD (IBM) |
| [dit700k](source/dit700k.md) | ~700,000 | Unknown | -- | Blocked: not publicly available |
| [u-diads-tl](source/u-diads-tl.md) | Unknown | Unknown | -- | Blocked: competition site offline |

### Text Corpora (Non-Image)

| Dataset | Samples | GT Labels | Method | Key Details |
|---------|---------|-----------|--------|-------------|
| [openlid-v2](source/openlid-v2.md) | 116M+ | Language/script codes | AUT | 201 language varieties, MIT license |
| [wili-2018](source/wili-2018.md) | 235K | Language labels (235 cls) | AUT | Wikipedia extraction, paragraph-level |

---

## Full Dataset Index (Alphabetical)

| Dataset | Method | GT Label Types | Coverage | Tier | Notes |
|---------|--------|----------------|----------|------|-------|
| anyphotodoc6300 | PAR | Paired images (corrected/distorted) | 100% | T0 | Dewarping pairs |
| arabic-docs | MIX | Title text + extracted OCR | 100% | T1/T2 | Human titles, extracted body text |
| bhutan-afs | -- | None (enrichment only) | 0% | T3 | GT via Layer 2 only |
| cc-ocr | HUM | Text, Document labels | 100% | T1 | Benchmark annotation |
| coco-text | HUM | Word boxes, Legibility, Class | 100% | T1 | Machine printed vs handwritten |
| cvsi | HUM | Script labels (10 cls) | 100% | T1 | Video scene text |
| dibco | HUM | Binarization masks | 100% | T1 | Competition GT |
| diqa-5000 | CWD | Quality MOS (3-dim, 1-5) | 100% | T1 | 15-subject consensus |
| dit700k | -- | Unknown | 0% | -- | Blocked: not publicly available |
| doc3d | SYN | Depth, UV, Normals (7 types) | 100% | T0 | Synthetic 3D generation |
| docalign12k | PAR | Paired images (aligned/unaligned) | 100% | T0 | Alignment pairs |
| doclaynet | HUM | Layout (11 cls), Text, Domain | 100% | T1 | Expert, double/triple annotated |
| document-haystack | HUM | Relevance pairs, Document text | 100% | T1 | Amazon Science benchmark |
| docreal | PAR | Paired images (distorted/scanned) | 100% | T0 | Camera + scanner pairs |
| docsynth | SYN | Layout boxes (74 cls) | 100% | T0 | Synthetic generation |
| drccbi | PAR | Paired images (warped/flat) | 100% | T0 | Camera dewarping pairs |
| dzongkha-digits | HUM | Digit class (10 cls) | 100% | T1 | 100 writers |
| financebench | AUT | QA text, Metadata | 100% | T0/T1 | PDF extraction |
| fintabnet | AUT | Table structure + cells | 100% | T0 | PDF extraction |
| funsd | HUM | Layout, NER, Entity links | 100% | T1 | Human annotated forms |
| funsd-plus | MIX | Layout, Text | 100% | T1 | Extended FUNSD |
| hasy | CWD | Symbol class (369 cls) | 100% | T1 | write-math.com crowdsource |
| hiertext | HUM | Word/line/para boxes, Text | 100% | T1 | Google Research annotators |
| hindi-synth | SYN | Text transcription, Script | 100% | T0 | Programmatic rendering |
| iam | HUM | Word/line transcriptions | 100% | T1 | 657 writers |
| im2latex | SYN | LaTeX source | 100% | T0 | Rendered formulas |
| indicdlp | HUM | Layout boxes (42 cls), Language | 100% | T1 | 12 Indian languages, COCO |
| invoices-kg | MIX | Text, Key-value entities | 100% | T1 | Mixed annotation sources |
| jssoda | SYN | Text, Orientation | 100% | T0 | Synthetic Japanese OCR |
| markushgrapher | SYN | Chemical structures (SMILES) | 100% | T0 | Programmatic generation |
| mathverse | MIX | VQA labels, Math problems | 100% | T0/T1 | Rendered + human VQA |
| mdiw13 | HUM | Script labels (13 cls) | 100% | T1 | Competition annotation |
| midv500 | HUM | Document type, Text | 100% | T1 | Identity documents |
| mle2e | HUM | Word boxes, Script (4 cls) | 100% | T1 | Scene text crops |
| mlt19 | HUM | Word boxes, Language (10 cls) | 100% | T1 | ICDAR 2019 competition |
| multimodal-textbook | AUT | Text, Diagram labels | 100% | T0 | PDF extraction |
| muharaf | HUM | Line transcriptions | 100% | T1 | Historical Arabic manuscripts |
| nepali-handwritten | HUM | Character class | 100% | T1 | Handwritten Devanagari |
| nist-sd2 | SYN | Form fields, Text | 100% | T0 | Synthesized IRS forms |
| nist-sd6 | MIX | Form fields + handprint | 100% | T0/T1 | Synth forms + real handwriting |
| nist-sd19 | HUM | Character class | 100% | T1 | NIST standard |
| ocr-quality | CWD | Quality scores | 100% | T1 | Human quality ratings |
| ohr-bench | AUT | Quality scores, Text, Domain | 100% | T0 | Born-digital PDF extraction |
| omnidocbench | HUM | Multi-task labels | 100% | T1 | Benchmark annotation |
| openlid-v2 | AUT | Language/script codes | 100% | T1 | Text corpus, 201 varieties |
| pucit-ohul | HUM | Line text | 100% | T1 | Urdu handwriting |
| pubtabnet | AUT | Table structure + cells, Text | 100% | T0 | PubMed XML extraction |
| q-doc | [VERIFY] | Quality scores | 100% | T1? | Camera-captured IQA benchmark |
| realdae | PAR | Paired images (camera/flatbed) | 100% | T0 | 600 document pairs |
| rvl-cdip | HUM | Document class (16 cls) | 100% | T1 | Scanned classification |
| sd7k | PAR | Paired images (shadow/clean) | 100% | T0 | Shadow removal |
| signatr6k | HUM | Text segmentation masks | 100% | T1 | Signature detection |
| siw13 | HUM | Script labels (13 cls) | 100% | T1 | Script in the wild |
| smartdoc-qa | HUM | QA pairs, Document text | 100% | T1 | Mobile capture QA |
| sroie | HUM | Quad boxes, Text, Entities | 100% | T1 | ICDAR 2019 receipts |
| staindoc | PAR | Paired images (stained/clean) | 100% | T0 | Camera-captured stain removal |
| tablebank | AUT | Table detection boxes | 100% | T0 | Word/LaTeX extraction |
| tibhcr | HUM | Character class (47 cls) | 100% | T1 | 235 Tibetan writers |
| tobacco800 | HUM | Document class (10 cls) | 100% | T1 | Archival documents |
| u-diads-tl | -- | Unknown | 0% | -- | Blocked: site offline |
| warpdoc | PAR | Paired images (warped/flat) | 100% | T0 | 6 distortion types |
| wili-2018 | AUT | Language labels (235 cls) | 100% | T1 | Wikipedia text corpus |
| wsrd | PAR | Paired images (shadow/clean) | 100% | T0 | Shadow removal |
| yarmouk | HUM | OCR text | 100% | T1 | Arabic document OCR |

---

## Annotation Quality Indicators

Datasets with documented inter-annotator agreement (IAA) or annotation quality metrics:

| Dataset | IAA Metric | Value | Annotators | Method | Source |
|---------|-----------|-------|------------|--------|--------|
| doclaynet | Agreement (subset) | ~90% | Expert team | Double/triple annotation | KDD 2022 paper |
| diqa-5000 | MOS consensus | 15 subjects/image | 15 | Crowdsourced rating | DocIQ paper |
| pubtabnet | TEDS | Automatic match | N/A | PDF/XML alignment | Paper validation |
| coco-text | Legibility consensus | [NEEDS_VERIFICATION] | Multiple | Human annotation | COCO-Text v2 |
| hiertext | Annotation review | [NEEDS_VERIFICATION] | Google team | Expert review | Google Research |
| tibhcr | Writer consistency | 235 writers | N/A | Per-writer collection | Dataset paper |
| hasy | Symbol verification | Crowdsource | ~100K contributors | write-math.com | HASYv2 paper |

---

## References

- **Quick Reference**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) -- metadata availability and training recipes
- **Individual Datasets**: [source/](source/) -- per-dataset deep documentation (Section 2.7 for provenance details)
- **Task Indices**: [indices/](indices/) -- curated dataset lists by training task
- **Label Mapping**: [../schema/LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) -- Layer 1 to Layer 2 field mappings
- **Provenance Tiers**: `src/image_preprocessing_detector/annotation/schemas/enums.py` -- `EnrichmentTier` enum
- **Tier Assignments**: `src/image_preprocessing_detector/annotation/config/tiers.py` -- per-dataset tier configuration

---

**Usage Guide**:

1. **"How was dataset X annotated?"** -> Find in Full Dataset Index or task group tables
2. **"Which datasets have human labels?"** -> Filter by HUM/CWD in Full Dataset Index
3. **"Which datasets have synthetic labels?"** -> Filter by SYN in Full Dataset Index
4. **"What annotation quality exists?"** -> Check Annotation Quality Indicators table
5. **"Detailed provenance for dataset X?"** -> Read Section 2.7 in individual dataset file at [source/](source/)
