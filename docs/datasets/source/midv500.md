#### MIDV-500 (Cyrillic + Latin ID Documents)

> **Quick Stats**: 50 countries | 500 video clips | Identity documents | Cyrillic coverage
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Mobile Identity Document Video-500 |
| **Paper** | [DOI](https://doi.org/10.18287/2412-6179-2019-43-5-818-824) |
| **GitHub** | [fcakyon/midv500](https://github.com/fcakyon/midv500) |
| **License** | MIT |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/midv500_data/` |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Countries** | 50 |
| **Document Types** | 17 ID cards, 14 passports, 13 driving licences, 6 other |
| **Total Size** | 48 GB |
| **File Format** | JPG (video frames) |

##### Cyrillic Coverage

| Country | Document Types | Script |
|---------|---------------|--------|
| Russia | ID, Passport, Driving Licence | Cyrillic |
| Ukraine | ID, Passport | Cyrillic |
| Belarus | ID, Passport | Cyrillic |
| Bulgaria | ID | Cyrillic |
| Serbia | ID | Cyrillic |
| Kazakhstan | ID | Cyrillic + Latin |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Video frames (mobile-captured) |
| **Key Value** | **Primary Cyrillic source** for script detection |
| **Noise Level** | Motion blur, perspective, lighting variation |
| **Text Density** | Sparse (ID document format) |

##### Project Usage

- **Path**: `01_base_data/language/midv500_data/midv500/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Cyrillic script class training (1,500+ samples needed)
- **Parser**: ✅ `parse_midv500_labels` (extracts country, doc_type, scripts from folder structure)

##### Text Labels

MIDV500 includes per-document-type JSON template files with text field values:

| Attribute | Value |
|-----------|-------|
| **Location** | `*/ground_truth/{doc_type}.json` (50 template files) |
| **Frame Files** | 15,050 JSON files (quad coordinates only) |
| **Format** | JSON with `field##` entries containing `quad` + `value` |
| **Content** | Names, nationalities, dates, document numbers, gender |

**Sample structure** (from `01_alb_id.json`):

```json
{
  "field01": {"quad": [[334, 122], ...], "value": "Sojli"},
  "field02": {"quad": [[334, 179], ...], "value": "Monika"},
  "field05": {"quad": [[334, 353], ...], "value": "01-01-1980"},
  "field08": {"quad": [[693, 236], ...], "value": "200000907"}
}
```

**Note**: Text values are in template files (one per document type). Frame JSONs contain only quad coordinates for document detection.

---
