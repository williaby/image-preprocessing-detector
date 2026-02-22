# DocLayNet - Source Labels Documentation

**Dataset**: doclaynet
**Source**: [DocLayNet on HuggingFace](https://huggingface.co/datasets/ds4sd/DocLayNet)
**Paper**: [DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis](https://arxiv.org/abs/2206.01062)
**License**: CDLA-Permissive-1.0
**Maintainer**: IBM Research, DS4SD (Deep Search for Science Discovery)

---

## Label Files Structure

```
doclaynet/
├── COCO/
│   ├── train.json              # COCO format annotations (train split)
│   ├── val.json                # COCO format annotations (val split)
│   └── test.json               # COCO format annotations (test split)
├── PNG/
│   └── {document_id}_{page_num}.png  # Document page images
└── annotations/                # Alternative location
    ├── train.json
    └── instances_train.json
```

---

## Label Format

**Format Type**: COCO JSON (Microsoft Common Objects in Context)

**Fields Available**:

- ✅ Bounding boxes: Yes (COCO format: `[x, y, width, height]`)
- ✅ Class labels: Yes (11 DocLayNet semantic classes)
- ❌ OCR text: No
- ❌ Quality scores: No
- ❌ Script/Language: No (but likely English/Latin for scientific documents)
- ❌ Degradation types: No (born-digital PDFs)

---

## COCO Structure

### Images

```json
{
  "id": 12345,
  "file_name": "0a0ea75cfa13c6cd3eddfa10e6da9c17d4f87a91_0.png",
  "width": 1654,
  "height": 2339
}
```

### Annotations

```json
{
  "id": 67890,
  "image_id": 12345,
  "category_id": 9,
  "bbox": [245, 156, 1164, 48],
  "area": 55872,
  "iscrowd": 0
}
```

**Bounding Box Format**: `[x, y, width, height]` (COCO standard)

- `x`: Left edge pixel coordinate
- `y`: Top edge pixel coordinate
- `width`: Box width in pixels
- `height`: Box height in pixels

### Categories

**DocLayNet 11 Classes**:

| ID | Name | Description |
|----|------|-------------|
| 1 | Caption | Figure/table captions |
| 2 | Footnote | Page footnotes |
| 3 | Formula | Mathematical formulas |
| 4 | List-Item | Bulleted or numbered list items |
| 5 | Page-Footer | Page footer content |
| 6 | Page-Header | Page header content |
| 7 | Picture | Figures, images, diagrams |
| 8 | Section-Header | Section headings |
| 9 | Table | Table regions |
| 10 | Text | Body text paragraphs |
| 11 | Title | Document/section titles |

```json
{
  "categories": [
    {"id": 1, "name": "Caption"},
    {"id": 2, "name": "Footnote"},
    {"id": 3, "name": "Formula"},
    {"id": 4, "name": "List-Item"},
    {"id": 5, "name": "Page-Footer"},
    {"id": 6, "name": "Page-Header"},
    {"id": 7, "name": "Picture"},
    {"id": 8, "name": "Section-Header"},
    {"id": 9, "name": "Table"},
    {"id": 10, "name": "Text"},
    {"id": 11, "name": "Title"}
  ]
}
```

---

## Example Label

**Full COCO Entry for Single Image**:

```json
{
  "images": [
    {
      "id": 12345,
      "file_name": "0a0ea75cfa13c6cd3eddfa10e6da9c17d4f87a91_0.png",
      "width": 1654,
      "height": 2339
    }
  ],
  "annotations": [
    {
      "id": 67890,
      "image_id": 12345,
      "category_id": 11,
      "bbox": [245, 156, 1164, 48],
      "area": 55872,
      "iscrowd": 0
    },
    {
      "id": 67891,
      "image_id": 12345,
      "category_id": 10,
      "bbox": [245, 220, 1164, 1890],
      "area": 2199960,
      "iscrowd": 0
    },
    {
      "id": 67892,
      "image_id": 12345,
      "category_id": 9,
      "bbox": [300, 550, 1000, 400],
      "area": 400000,
      "iscrowd": 0
    }
  ],
  "categories": [...]
}
```

**Interpretation**:

- Image: `0a0ea75cfa13c6cd3eddfa10e6da9c17d4f87a91_0.png` (1654×2339 pixels)
- Annotation 67890: Title at `[245, 156, 1164, 48]`
- Annotation 67891: Text block at `[245, 220, 1164, 1890]`
- Annotation 67892: Table at `[300, 550, 1000, 400]`

---

## Split Information

- **Train**: ~80,000 images (used for training)
- **Val**: ~6,000 images (RESERVED for validation)
- **Test**: ~6,000 images (RESERVED for evaluation)
- **Total**: 81,471 images

**Note**: Val and test splits are RESERVED for evaluation. Never train on these splits.

---

## Dataset Provenance

**Source Documents**: Scientific and financial PDFs from various sources
**Capture Method**: Born-digital (extracted from PDFs, not scanned)
**Annotation Method**: Human-annotated bounding boxes by trained annotators
**Quality Control**: Multi-stage review process by IBM Research

---

## Usage in Prepare-Doc

**Parser**: `src/image_preprocessing_detector/annotation/parsers/layout/doclaynet.py`

**Extracted Fields** (to `OriginalLabels`):

```python
labels.raw_labels["doclaynet_annotations"] = [
    {
        "id": 67890,
        "image_id": 12345,
        "category_id": 11,
        "category_name": "Title",  # Added by parser
        "bbox": [245, 156, 1164, 48],
        "area": 55872,
        "iscrowd": 0
    },
    # ... more annotations
]
```

**Layer 2 Mapping**:

- `layout_detections[]` ← COCO bounding boxes with category names
- `content_flags.has_table` ← Derived from category_name="Table"
- `content_flags.has_formula` ← Derived from category_name="Formula"
- `content_flags.has_figure` ← Derived from category_name="Picture"

---

## License & Usage Restrictions

- **License**: CDLA-Permissive-1.0 (Community Data License Agreement)
- **Commercial use**: ✅ Yes
- **Research use**: ✅ Yes
- **Attribution required**: ✅ Yes
- **Redistribution**: ✅ Allowed with attribution
- **Modifications**: ✅ Allowed

**Citation**:

```bibtex
@article{doclaynet2022,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis},
  author={Pfitzmann, Birgit and Auer, Christoph and Dolfi, Michele and Nassar, Ahmed S and Staar, Peter},
  journal={arXiv preprint arXiv:2206.01062},
  year={2022}
}
```

---

## Additional Resources

- **HuggingFace Dataset**: <https://huggingface.co/datasets/ds4sd/DocLayNet>
- **GitHub Repository**: <https://github.com/DS4SD/DocLayNet>
- **Paper (arXiv)**: <https://arxiv.org/abs/2206.01062>
- **IBM Research Page**: <https://ds4sd.github.io/DocLayNet/>
