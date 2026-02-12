# KI-008: Docling Multi-Column Text Extraction Failure

> **Severity**: HIGH | **Status**: OPEN | **Discovered**: 2026-02-11

## Summary

When Docling's layout model misclassifies multi-column text as `Table` (see [KI-002](KI-002-docling-table-multicolumn.md)), the downstream text extraction pipeline produces garbled output. This is not just a metadata issue - it corrupts the actual extracted text by destroying reading order. Tables are extracted row-by-row across cells; multi-column text must be read column-by-column top-to-bottom. Misclassification causes the wrong extraction strategy.

## Scope

All multi-column documents processed through Docling's full text extraction pipeline (OCR). Affects both synthetic and real-world documents. This is a **Project B** (OCR Orchestration) concern but is documented here because the root cause is in the layout detection stage (Project A scope).

## Docling Text Extraction Pipeline

Docling processes documents through five sequential stages. The Table misclassification causes damage at three of them:

```
1. Layout Model (Egret/DocLayout-YOLO)
   |  Multi-column text labeled "Table" here  <-- ROOT CAUSE
   v
2. LayoutPostprocessor
   |  Table clusters get special postprocessing  <-- DAMAGE STAGE 1
   |  Text cells assigned to table grid structure
   v
3. PageAssemble
   |  Table clusters become Table elements (not TextElement)
   v
4. ReadingOrderModel (rule-based)
   |  Single Table element = one reading unit  <-- DAMAGE STAGE 2
   |  Column-first ordering never triggers
   v
5. DoclingDocument.export_to_markdown()
      Table rendered as markdown table or  <-- DAMAGE STAGE 3
      1x1 rich cell with wrong text order
```

### Stage 1: LayoutPostprocessor (cluster assignment)

File: `.venv/.../docling/utils/layout_postprocessor.py`

The postprocessor treats `TABLE` as a special cluster type (line 167). Special clusters get different handling than regular text clusters:

- Children are assigned to the table cluster
- Text cells are grouped for table structure rather than reading-order flow
- The `UnionFind` merge logic and `SpatialClusterIndex` operate differently for special vs regular clusters

When multi-column text is labeled `TABLE`, its text cells are assigned to a table grid structure instead of being treated as independent text blocks.

### Stage 2: ReadingOrderModel (ordering)

File: `.venv/.../docling/models/stages/reading_order/readingorder_model.py`

The reading order predictor uses `ReadingOrderPredictor` from `docling-ibm-models`. This is a **rule-based** system (not ML) that determines reading order via spatial relationships.

The critical comparison in `PageElement.__lt__()` (line 36-43):

```python
def __lt__(self, other):
    if self.page_no == other.page_no:
        if self.overlaps_horizontally(other):
            return self.b > other.b  # top-to-bottom within same column
        else:
            return self.l < other.l  # left-to-right across columns
```

This correctly handles multi-column reading order **when columns are separate Text elements**. Each column becomes its own `TextElement`, and the `overlaps_horizontally` check identifies elements in the same column for top-to-bottom reading.

But when multiple columns are merged into one `Table` element, this comparison never fires between columns. The reading order model sees one large element instead of two or three separate column elements.

The `_init_ud_maps()` method (line 318) builds up/down navigation maps using R-tree spatial queries. It checks `is_strictly_above()` and `overlaps_horizontally()` between elements. A single Table cluster that spans the full page width has no other element to compare against, so it gets a trivial ordering.

### Stage 3: Document assembly (output)

File: `.venv/.../docling/models/stages/reading_order/readingorder_model.py`

In `_readingorder_elements_to_docling_doc()` (line 122), Table elements are assembled at line 215-282:

- If the table structure model found rows/cols: text is arranged into `TableData` cells. Multi-column text has no real cell structure, so the table structure model either fails or produces garbage cell assignments.
- If the table structure model found 0 rows/0 cols: the content is wrapped in a 1x1 `RichTableCell`. All child text elements get dumped into a single cell, and `export_to_markdown()` outputs them in whatever order they were added - typically left-to-right across columns rather than column-first.

Either path produces garbled text output.

## Proposed Fixes

### Fix 1: Table Structure Gatekeeper (Recommended first step)

**Effort**: Medium (1-2 days) | **Impact**: High | **Location**: Post-`LayoutPostprocessor`

The table structure model is the strongest discriminator. Real tables have internal cell structure (rows, columns, grid lines). Multi-column text does not. After the table structure model runs:

- If `num_rows == 0 and num_cols == 0` and the cluster has text children, **reclassify the cluster from `TABLE` to `TEXT`** before reading order runs.
- This allows the reading order model to split it into separate text elements and apply column-first ordering.

This fix should be applied at the boundary between `LayoutPostprocessor` output and `ReadingOrderModel` input. In Docling's pipeline, this is the `PageAssemble` stage.

### Fix 2: Per-Class Confidence Threshold (Quick win)

**Effort**: Low (1 hour) | **Impact**: Partial | **Location**: `DoclingLayoutProvider`

The Egret model uses a global `base_threshold=0.3`. Docling's internal `LayoutPostprocessor` has a `TABLE` confidence threshold of 0.5 (line 181). However, our `DoclingLayoutProvider` uses 0.3 for all classes.

Actions:

- Verify whether false-positive Table detections on JSSODa have confidence below 0.5
- If yes, raising the threshold in `DoclingLayoutProvider` to 0.5 for Table class would filter them
- If no (high-confidence false positives), this fix alone is insufficient

```python
# In DoclingLayoutProvider._convert_predictions():
if raw_label == "Table" and confidence < 0.5:
    continue  # Skip low-confidence table detections
```

### Fix 3: Post-Detection Geometric Heuristic

**Effort**: Medium (1-2 days) | **Impact**: Good for known patterns | **Location**: `derive_content_flags()` or new post-processor

Add a heuristic that distinguishes tables from multi-column text based on detection geometry:

| Signal | Real Table | Multi-Column Text |
|--------|-----------|-------------------|
| Internal structure | Many small cells in a grid | Few large text blocks |
| Aspect ratio | Variable, often tall | Wide, spanning multiple columns |
| Adjacent Text detections | Few (table is self-contained) | Many (text blocks flanking the "table") |
| Caption/Footnote nearby | Often | Rarely |
| Horizontal/vertical rules | Often | Never |

Implementation: ~50-line function checking overlap between Table and Text detections, aspect ratio, and presence of nearby structural elements.

### Fix 4: Column Detection Pre-Pass

**Effort**: Medium (2-3 days) | **Impact**: High | **Location**: Before layout prediction

Our `HybridLayoutAnalyzer.determine_layout_type()` already performs x-position clustering to detect multi-column layout. This signal could be used to:

1. Run column detection before or alongside layout prediction
2. If `layout_type == MULTI_COLUMN`, flag any Table detection that spans a full column width as suspicious
3. Pass column boundary information to the reading order model to constrain text flow

This leverages existing infrastructure in `doclayout_integration.py` (line 258-319).

### Long-Term: SigLIP 2 Pipeline

The SigLIP 2 multi-task pipeline (`docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`) will provide learned layout understanding via dedicated heads. However, SigLIP 2 handles **content flags and page attributes** - it does not replace Docling for text extraction. The text extraction pipeline will always need Docling or an alternative (Surya, Nougat, TrOCR) for actual text/reading order.

The right long-term fix for text extraction is contributing Fix 1 (table structure gatekeeper) upstream to the Docling project.

## Recommendation

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| 1 | Fix 2: Per-class confidence threshold | 1 hour | Filters weak FPs |
| 2 | Fix 1: Table structure gatekeeper | 1-2 days | Fixes root cause |
| 3 | Fix 3: Geometric heuristic | 1-2 days | Catches remaining cases |
| 4 | Fix 4: Column detection pre-pass | 2-3 days | Complementary |

Start with Fix 2 as a quick win, then implement Fix 1 as the primary solution.

## Related Issues

- [KI-002](KI-002-docling-table-multicolumn.md) - The upstream layout misclassification that causes this
- [KI-003](KI-003-docling-picture-dense-text.md) - Similar misclassification for Picture class

## Related Files

- `.venv/.../docling/models/stages/layout/layout_model.py` - Layout prediction
- `.venv/.../docling/utils/layout_postprocessor.py` - Cluster postprocessing
- `.venv/.../docling/models/stages/reading_order/readingorder_model.py` - Reading order assembly
- `.venv/.../docling_ibm_models/reading_order/reading_order_rb.py` - Rule-based reading order predictor
- `src/.../detection/layout_lite/doclayout_integration.py` - Our HybridLayoutAnalyzer with column detection
- `src/.../annotation/enrichment/providers/docling_layout.py` - Our DoclingLayoutProvider wrapper
- `configs/models/doclayout_yolo.yaml` - Model configuration
