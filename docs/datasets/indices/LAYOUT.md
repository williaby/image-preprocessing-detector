# Layout Detection Datasets

> **Purpose**: Datasets for training coarse layout classification (11 DocLayNet classes)
> **Target Model**: YOLOv10-doc (Phase 2)
> **Label Type**: COCO-style bounding boxes `[x, y, width, height]`

---

## Primary Layout Datasets

| Dataset | Images | Classes | Restrictions | Capture | Domain | Link |
|---------|--------|---------|--------------|---------|--------|------|
| doclaynet | 80,863 | 11 DocLayNet | ⚠️ Train OK (69,375), test reserved | 📄 Born-digital | SCI/TEC/UNK | [doclaynet.md](../source/doclaynet.md) |
| docsynth300k | 300,000 | 74 classes | ✅ Unrestricted | 🎨 Synthetic | UNK | [docsynth300k.md](../source/docsynth300k.md) |
| pubtabnet | 519,030 | Tables + layout | ⚠️ Train OK (500,777), test reserved | 📄 Born-digital | SCI 100% | [pubtabnet.md](../source/pubtabnet.md) |
| tablebank | 278,582 | Tables + layout | ✅ Unrestricted (260,582 train) | 📄 Born-digital | SCI 100% | [tablebank.md](../source/tablebank.md) |
| rvl-cdip | 400,000 | 16 doc types | ✅ Unrestricted (320,000 train) | 🖨️ Scanner | UNK | [rvl-cdip.md](../source/rvl-cdip.md) |

**Total Available for Training**: ~1.14M images

---

## DocLayNet Classes (11 total)

**Text Elements**:

- Text, Title, Section-Header, List-Item

**Metadata**:

- Caption, Footnote, Page-Header, Page-Footer

**Special Content**:

- Table, Picture, Formula

---

## Training Strategy

**Model**: YOLOv10-doc (document-optimized YOLO architecture)
**Task**: Multi-class object detection
**Performance Target**: 70-80% mAP, 85+ FPS

**Recommended Training Order**:

1. **Base**: DocLayNet train split (69,375 images, diverse document types)
2. **Table augmentation**: TableBank + PubTabNet train splits
3. **Synthetic augmentation**: DocSynth300K (74 classes, map to 11 DocLayNet)
4. **Document classification**: RVL-CDIP (16 document types)

---

## Layout-Lite vs Full Layout

**Layout-Lite (Project A - THIS REPO)**:

- **Coarse page attributes**: has_tables, has_figures, has_dense_math, has_handwriting
- **Complexity scoring**: Structural complexity for routing decisions
- **11 DocLayNet classes**: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title
- **Fast inference**: < 50ms per page
- **Purpose**: Routing recommendations (ocr_fast/advanced, vision_simple/structured)

**Full Layout (Project B - OUT OF SCOPE)**:

- Semantic layout detection (reading order, hierarchy)
- Table structure extraction (PubTables-1M)
- Reading order prediction (ReadingBank)
- Fine-grained element relationships

---

## Additional Layout-Related Datasets

| Dataset | Images | Focus | Link |
|---------|--------|-------|------|
| funsd | 199 | Forms (entity detection) | [funsd.md](../source/funsd.md) |
| funsd-plus | 1,139 | Forms (extended) | [funsd-plus.md](../source/funsd-plus.md) |
| sroie | 973 | Malaysian receipts (quad + OCR + entities) | [sroie.md](../source/sroie.md) |
| multimodal-textbook | 1,113 | Textbook pages (diagrams, equations) | [multimodal-textbook.md](../source/multimodal-textbook.md) |

---

## Benchmark Considerations

**DocLayNet**:

- Test split (6,480 images): RESERVED for benchmark evaluation
- Can train on train split (69,375)
- Val split can be used if needed

**PubTabNet**:

- Test split (9,138 images): RESERVED
- Train split (500,777): Available for training

**TableBank**:

- Fully unrestricted (train split: 260,582)

---

*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
*See [TABLES.md](TABLES.md) for table-specific training datasets*
