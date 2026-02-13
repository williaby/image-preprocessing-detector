# Table Structure Datasets

> **Purpose**: Datasets for table detection and structure extraction
> **Scope**: Table detection (Project A), structure extraction (Project B)
> **Label Type**: COCO boxes + HTML/Cell structure (where available)

---

## Table Detection & Structure Datasets

| Dataset | Images | Structure Labels | Restrictions | Capture | Domain | Link |
|---------|--------|------------------|--------------|---------|--------|------|
| pubtabnet | 519,030 | ✅ HTML + cells | ⚠️ Test reserved (9,138) | 📄 Born-digital | SCI 100% | [pubtabnet.md](../source/pubtabnet.md) |
| tablebank | 278,582 | ❌ Boxes only | ✅ Unrestricted | 📄 Born-digital | SCI 100% | [tablebank.md](../source/tablebank.md) |
| fintabnet | 97,475 | ✅ HTML + cells | ✅ Unrestricted | 📄 Born-digital | FIN 100% | [fintabnet.md](../source/fintabnet.md) |
| financebench | 54,121 | ❌ Boxes only | ✅ Unrestricted | 📄 Born-digital | FIN 100% | [financebench.md](../source/financebench.md) |

**Total Images**: ~949K (structure labels: ~616K)

---

## Label Formats

**Table Detection** (COCO boxes):

- Class: "Table"
- Bounding box: `[x, y, width, height]` (COCO XYWH format)
- Available in: All 4 datasets

**Table Structure** (HTML + Cells):

- HTML tokens: Row/column structure
- Cell annotations: Bboxes + text content + cell properties
- Available in: PubTabNet, FinTabNet only

---

## Training Use Cases

### Project A (Layout-Lite) - THIS REPO

**Task**: Detect table presence for routing decisions
**Model**: YOLOv10-doc (single "Table" class from 11 DocLayNet classes)
**Training Data**: DocLayNet train (69,375) + TableBank train (260,582)
**Purpose**: Set `has_tables: bool` flag for OCR routing

### Project B (Table Structure) - OUT OF SCOPE

**Task**: Extract table structure (rows, columns, cells)
**Model**: TableFormer or similar
**Training Data**: PubTabNet (519K with structure) + FinTabNet (97K with structure)
**Purpose**: Generate HTML table structure from images

---

## Dataset Characteristics

**PubTabNet**:

- **Largest table corpus** (519K images)
- **Scientific domain** (research papers)
- **HTML structure + cell-level annotations**
- **Test split RESERVED** for benchmark evaluation

**TableBank**:

- **Diverse sources** (Word, LaTeX, web tables)
- **Boxes only** (no structure labels)
- **Fully unrestricted** (best for augmentation)

**FinTabNet**:

- **Financial domain** (reports, filings)
- **High-quality structure labels**
- **Smaller but domain-specific** (97K images)

**FinanceBench**:

- **RAG QA context** (not pure table dataset)
- **Boxes only** (no structure)
- **Financial domain diversity**

---

## Benchmark Protection

**PubTabNet**: Test split (9,138) RESERVED - used for PubTables-1M benchmark
**TableBank**: Unrestricted - can use all splits for training
**FinTabNet**: Unrestricted - all images available
**FinanceBench**: Unrestricted - all images available

---

## Related Datasets

**Forms with Tables**:

- [funsd.md](../source/funsd.md) - Forms with table-like structures
- [sroie.md](../source/sroie.md) - Receipts (table-like layouts)
- [nist-sd2.md](../source/nist-sd2.md) - Tax forms (structured fields)

**Scientific Content**:

- [multimodal-textbook.md](../source/multimodal-textbook.md) - Textbook tables + diagrams

---

*See [LAYOUT.md](LAYOUT.md) for general layout detection datasets*
*See [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for complete dataset overview*
