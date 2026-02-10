---
schema_type: common
title: Priority 2 Layout Edge Cases - Options and Recommendations
tags: [testing, layout, research]
status: published
owner: "core-maintainer"
purpose: "Research findings and implementation options for Priority 2 layout edge case test fixtures."
---

**Created**: 2025-11-24
**Status**: Research complete, awaiting decision
**Context**: Need 4 edge case samples for layout detection testing

---

## Current Status

**✅ Already Available** (from existing fixtures):

- Multi-column layout (can reuse `multi_column_3.pdf` for three-column requirement)
- Tables and figures
- Simple text
- Skewed documents
- Low contrast

**❌ Still Needed** (4 edge cases):

1. Watermarked document
2. Colorful/gradient background document
3. Dense math equations (scientific paper)
4. Handwriting mixed with printed text

---

## Option A: Generate Synthetic Samples (RECOMMENDED)

**Pros**:

- ✅ Full control over sample characteristics
- ✅ No licensing concerns
- ✅ Can be integrated into test suite as generators
- ✅ Fast to implement

**Cons**:

- ❌ Not "real-world" samples
- ❌ Requires implementation effort

### Implementation Approach

**1. Watermarked Document**

```python
# In tests/conftest.py or test helpers
def add_watermark(pdf_path: Path, output_path: Path, watermark_text: str = "SAMPLE"):
    """Add semi-transparent text watermark to existing PDF."""
    # Use PyMuPDF to overlay watermark on existing clean document
    # Example: Take multi_column_3.pdf, add "CONFIDENTIAL" watermark
```

**2. Colorful Background**

```python
def add_gradient_background(image_path: Path, output_path: Path):
    """Add colorful gradient background to document image."""
    # Use PIL/OpenCV to create gradient overlay
    # Example: Take clean_text_page.jpg, add blue-to-purple gradient
```

**3. Dense Math Equations**

- **Option 3a**: Download from arXiv with CC-BY/CC0 license (see Option B below)
- **Option 3b**: Use LaTeX to generate synthetic math-heavy page:

```python
def generate_math_heavy_doc():
    """Generate LaTeX document with dense equations."""
    # Use pylatex to create document with matrices, integrals, summations
```

**4. Handwriting Mixed**

- **Option 4a**: Take existing IAM handwriting sample + overlay on printed doc
- **Option 4b**: Use PIL to draw handwritten annotations over clean document

```python
def add_handwriting_annotations(doc_path: Path, output_path: Path):
    """Add simulated handwriting over printed text."""
    # Composite IAM sample onto document margins/whitespace
```

### Estimated Effort

- **Watermark**: 30 minutes
- **Colorful background**: 20 minutes
- **Dense math**: 1-2 hours (if generating with LaTeX) or 10 minutes (if using arXiv)
- **Handwriting mixed**: 45 minutes
- **Total**: ~3-4 hours

---

## Option B: Source from Online Datasets/Repositories

Research findings from web search:

### 1. Dense Math Equations (Scientific Papers)

**Best Option: arXiv Papers with CC-BY/CC0 License**

**Sources**:

- [arXiv License Options](https://info.arxiv.org/help/license/index.html)
- [arXiv CC0 Blog Post](https://blog.arxiv.org/2020/11/09/arxiv-authors-now-have-a-new-license-option/)
- [arXiv Permissions and Reuse](https://info.arxiv.org/help/license/reuse.html)

**Example Paper**:

- [Dense cell-by-cell systems of PDEs (Sept 2024)](https://arxiv.org/html/2409.13432)
- Contains extensive PDEs, ODEs, matrices
- **License**: Check individual paper's license on abstract page

**Process**:

1. Browse [arXiv Mathematics 2024](https://arxiv.org/list/math/2024) archives
2. Look for papers with CC BY or CC0 license (displayed on abstract page)
3. Download PDF (typically <1 MB per paper)
4. Extract page with dense equations

**Licensing Note**:

- MIT license not typical for research papers (it's a software license)
- Look for CC BY, CC BY-SA, or CC0 for permissive reuse
- arXiv supports CC0 (public domain dedication)

### 2. Watermarked Documents

**Research Findings**:

- [MarkPDF (GitHub)](https://github.com/ajaxray/markpdf) - MIT license tool for adding watermarks
- No readily available pre-watermarked sample documents with permissive licenses found

**Recommendation**: Use MarkPDF (Option A) to generate watermarked sample from existing fixture

### 3. Handwriting Mixed with Printed Text

**Best Option: Wiedergutmachung Dataset** ⚠️ License unclear

**Sources**:

- [Wiedergutmachung GitHub](https://github.com/ISE-FIZKarlsruhe/Wiedergutmachung)
- [Research Paper (PDF)](https://www.fiz-karlsruhe.de/sites/default/files/FIZ/Dokumente/Forschung/ISE/Publications/Conferences-Workshops/ARCHIVING-2022-4-Mahsa-Vafaie.pdf)

**Description**: Artificial dataset for "pixel-wise separation of machine-printed and handwritten text in historical archival documents"

**Licensing**: ⚠️ Not explicitly stated in search results - requires verification on GitHub

**Alternative Datasets** (NOT suitable due to licensing):

- [IAM Handwriting Database](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database) - Academic use only
- [FUNSD (Form Understanding)](https://guillaumejaume.github.io/FUNSD/) - Non-commercial/research only
- [FUNSD GitHub](https://github.com/crcresearch/FUNSD)
- [FUNSD+ (Konfuzio)](https://konfuzio.com/en/funsd-plus/)

**Recommendation**:

1. Check Wiedergutmachung license on GitHub
2. If compatible → use sample from dataset
3. If not → use Option A (composite IAM sample over printed doc)

### 4. Colorful/Gradient Background Documents

**Research Findings**:

- [Prince Sample Documents](https://www.princexml.com/samples/) - Colorful invoices available
- [Color Print Test PDF](https://supertool.org/color-print-test-page-pdf/) - Printer test pages

**Licensing**: ⚠️ Not explicitly CC0 or MIT - requires verification

**Recommendation**: Use Option A (add gradient to existing fixture) to avoid licensing ambiguity

---

## Final Recommendations

### For Dense Math (Scientific Papers)

**✅ Recommended: Option B (arXiv with CC-BY/CC0)**

**Action Steps**:

1. Browse recent arXiv math papers: <https://arxiv.org/list/math/2024>
2. Find paper with dense equations AND CC BY/CC0 license
3. Download PDF (e.g., <https://arxiv.org/pdf/2409.13432>)
4. Extract single page with heaviest math content
5. Save as `data/test_fixtures/layout_samples/dense_math_scientific.pdf`

**Estimated time**: 15-20 minutes

### For Other 3 Edge Cases

**✅ Recommended: Option A (Synthetic Generation)**

**Rationale**:

- No licensing ambiguity
- Full control over characteristics
- Can be templated for test suite
- Faster than researching/verifying licenses

**Action Steps**:

1. **Watermark**: Use MarkPDF or PyMuPDF to add watermark to existing fixture
2. **Colorful background**: Use PIL/OpenCV gradient overlay on clean document
3. **Handwriting mixed**: Composite IAM sample (you already have this) over printed doc

**Estimated time**: 2-3 hours total

---

## Implementation Plan (Recommended)

### Phase 1: arXiv Dense Math (15 minutes)

```bash
# Manual download from arXiv
# Select paper with CC-BY/CC0 license
# Extract page with dense equations
# Save to data/test_fixtures/layout_samples/dense_math_scientific.pdf
```

### Phase 2: Synthetic Edge Cases (2-3 hours)

```python
# Create: tests/fixtures/generators/layout_edge_cases.py

def generate_watermarked_sample():
    """Add watermark to multi_column_3.pdf"""
    # Implementation using PyMuPDF

def generate_colorful_background_sample():
    """Add gradient to clean_text_page.jpg"""
    # Implementation using PIL

def generate_handwriting_mixed_sample():
    """Composite IAM handwriting over printed doc"""
    # Implementation using PIL

# Save outputs to data/test_fixtures/layout_samples/
```

### Phase 3: Documentation

- Update `layout_samples/manifest.json`
- Document generation process in README
- Add fixture paths to `tests/conftest.py`

---

## Size Estimate

Adding 4 layout edge case samples:

- Dense math PDF (arXiv): ~500 KB
- Watermarked PDF: ~450 KB (similar to multi_column_3.pdf)
- Colorful background JPG: ~400 KB
- Handwriting mixed JPG: ~350 KB
- **Total addition**: ~1.7 MB

**New total for test_fixtures**: ~7.3 MB (still well under 50 MB limit)

---

## Alternative: Defer Layout Edge Cases

**If time is limited**, consider deferring Priority 2 entirely:

**Rationale**:

- Existing fixtures cover most layout needs (multi-column, tables, figures)
- Layout-lite (Phase 6) is coarse-grained, not full semantic layout
- Edge cases (watermark, colorful bg) are less critical for Phase 2-4 development
- Can add synthetics later when layout-lite implementation begins

**Impact**: Minimal - current fixtures sufficient for IQA and basic layout testing

---

## Decision Matrix

| Approach | Effort | Licensing Risk | Realism | Recommended? |
|----------|--------|----------------|---------|--------------|
| Option A (All Synthetic) | High | None | Low | ⭐ Good |
| Option B (All Online) | Medium | High | High | ❌ Risky |
| **Hybrid (arXiv + Synthetic)** | **Medium** | **Low** | **Medium** | **✅ BEST** |
| Defer Entirely | None | N/A | N/A | ⭐ Also Good |

---

## Sources

**arXiv Papers**:

- [arXiv License Options](https://info.arxiv.org/help/license/index.html)
- [arXiv CC0 Option](https://blog.arxiv.org/2020/11/09/arxiv-authors-now-have-a-new-license-option/)
- [Dense PDEs Paper (Sept 2024)](https://arxiv.org/html/2409.13432)

**Watermarking Tools**:

- [MarkPDF GitHub (MIT)](https://github.com/ajaxray/markpdf)
- [Open Source PDF Watermarking](https://products.fileformat.com/pdf/go/markpdf/)

**Handwriting Datasets**:

- [Wiedergutmachung Mixed Text](https://github.com/ISE-FIZKarlsruhe/Wiedergutmachung)
- [IAM Database (Academic Only)](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database)
- [FUNSD Forms (Non-commercial)](https://guillaumejaume.github.io/FUNSD/)

**Test Documents**:

- [Prince Sample Documents](https://www.princexml.com/samples/)
- [Color Print Test PDF](https://supertool.org/color-print-test-page-pdf/)

---

**Next Step**: Choose between Hybrid approach (arXiv + synthetic) or defer Priority 2 entirely.
