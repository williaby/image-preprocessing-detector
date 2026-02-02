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
| **Maintainer** | FKI Research Group, University of Bern |
| **Website** | [IAM Handwriting Database](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database) |
| **Paper** | [The IAM-database: an English sentence database for offline handwriting recognition (IJDAR 2002)](https://link.springer.com/article/10.1007/s100320200071) |
| **License** | Research Use Only |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/iam_handwriting/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 130,212 |
| **Forms (Full Pages)** | 1,539 |
| **Lines** | 13,353 |
| **Words** | 115,320 |
| **Writers** | 657 |
| **Sentences** | 5,685 unique |
| **Format** | PNG (grayscale, 300 DPI) |

##### Data Hierarchy

| Level | Count | Description |
|-------|-------|-------------|
| **Forms** | 1,539 | Full handwritten pages (aXX-YYY format) |
| **Lines** | 13,353 | Individual text lines with bounding boxes |
| **Words** | 115,320 | Segmented words with transcriptions |

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

- **Phase 3**: Handwriting detection training
- **Phase 10A**: Writer identification, handwriting style analysis
- **Parser**: ✅ `parse_iam_labels` (extracts transcriptions, bounding boxes)

##### Data Locations

| Data Type | Path |
|-----------|------|
| **Local Path** | `01_base_data/handwriting/iam_handwriting/` |
| **Images** | Root + `a01/`, `a02/`, etc. subdirectories |
| **ASCII Labels** | `ascii/forms.txt`, `ascii/lines.txt`, `ascii/words.txt`, `ascii/sentences.txt` |
| **XML Annotations** | `xml/*.xml` (per-form bounding boxes) |

---
