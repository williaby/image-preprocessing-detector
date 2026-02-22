---
dataset_id: markushgrapher
version: "1.0"
license: CC-BY-4.0
commercial_use: true
iqa_profiles:
  - scientific_domain
  - chemical_structures
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: partial
---

#### MarkushGrapher Datasets

> **Quick Stats**: ~235,000 samples | Chemical/Markush structures | Born-digital | Scientific domain
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | MarkushGrapher Datasets |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Last Updated** | 2024 |
| **Maintainer** | DS4SD (Deep Search for Science & Discovery, IBM Research) |
| **Paper** | [MarkushGrapher: Chemical Structure Recognition (2024)](https://huggingface.co/datasets/ds4sd/MarkushGrapher-Datasets) |
| **Repository** | [HuggingFace: ds4sd/MarkushGrapher-Datasets](https://huggingface.co/datasets/ds4sd/MarkushGrapher-Datasets) |
| **License** | CC-BY-4.0 |
| **Commercial Use** | Yes |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG / SVG | Chemical structure diagrams (Markush structures) |
| **Annotations** | JSON / SMILES | Chemical structure annotations (graph representations) |
| **Supplementary** | README | Dataset description, citation, usage instructions |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/` | `train/annotations.json` | ~188,000 | ✅ |
| **Validation** | `val/` | `val/annotations.json` | ~23,500 | ✅ |
| **Test** | `test/` | `test/annotations.json` | ~23,500 | ✅ |
| **Total** | - | - | ~235,000 | ✅ |

**Split Organization Pattern**: `by_folder` with JSON annotations per split

> **Notes**:
>
> - Standard 80/10/10 train/val/test split
> - Annotations include graph representations of chemical structures
> - Sample counts approximate from HuggingFace listing

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Chemical Structures** | JSON / SMILES | Molecule-level | Graph representation of Markush structures |
| **Bounding Boxes** | JSON (optional) | Region | Atom/bond region coordinates (if provided) |
| **Structure Type** | JSON | Image-level | Markush/generic structure classification |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace README | License, citation, usage instructions |
| **Image-level** | Annotations JSON | Structure type, complexity, formula |
| **Annotation-level** | SMILES strings | Chemical graph representation |

##### 2.5 Annotation Schema Details

> **Format**: Chemical structure annotations with graph representations

```text
{
  "images": [
    {
      "image_id": str,
      "file_name": str,
      "structure_type": str,  # Markush, generic, specific
      "complexity": str  # simple, medium, complex
    }
  ],
  "annotations": [
    {
      "image_id": str,
      "smiles": str,  # Chemical structure notation
      "graph": {
        "atoms": [...],
        "bonds": [...]
      },
      "bounding_boxes": [...]  # Optional
    }
  ]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | str | Yes | Unique image identifier |
| `smiles` | str | Yes | Chemical structure notation |
| `graph` | dict | Yes | Atoms and bonds representation |
| `structure_type` | str | Yes | Markush/generic/specific |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Chemical structures | `chemical_annotations` | High | SMILES + graph format |
| ✅ Structure types | `document_type` | Medium | Markush/generic classification |
| ✅ Complexity | `structural_complexity` | Medium | Simple/medium/complex |
| ⚠️ Bounding boxes | `layout_annotations` | Low | If provided; verify schema |
| ❌ Text GT | - | N/A | Not applicable for structure diagrams |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

> **Purpose**: Document annotation methodology, quality assurance, and provenance for ground truth labels.

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Synthetic |
| **Provenance Tier** | Tier 0 (Exact) |
| **Annotator Details** | Programmatically generated chemical structures with SMILES/graph annotations |
| **Inter-Annotator Agreement** | N/A - Synthetic generation (deterministic) |
| **Quality Assurance** | Automated generation pipeline by DS4SD (IBM Research) |
| **GT Label Coverage** | 100% - All ~235,000 images have SMILES + graph structure annotations |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 9 (specialized element detection) |
| **Purpose** | Chemical structure recognition, scientific document analysis |
| **Local Path** | `01_base_data/specialized/markushgrapher/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Chemical structure parsing, graph extraction |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `markushgrapher` (document category - specialized) |
| **Parser Status** | ❌ Not Implemented |
| **Layer 1 Fields** | `chemical_annotations`, `document_type`, `structural_complexity` |
| **Layer 2 Auto-Derived** | `domain_level1=scientific`, `capture_method=born_digital`, `content_type=diagram` |
| **Config Entry** | Pending implementation |

> **Parser Reference**: Specialized domain requiring chemical structure-specific parsing logic.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/specialized/markushgrapher/` | ✅ Available | ~235K chemical structure diagrams |
| **Chemical GT** | `01_base_data/specialized/markushgrapher/{split}/annotations.json` | ✅ Available | SMILES + graph format |
| **Text/OCR GT** | - | ℹ️ N/A | Not applicable for structure diagrams |
| **Text/OCR Extracted** | - | ℹ️ N/A | Chemical structures, not text |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not applicable |
| **Layer 2 Metadata** | `metadata_registry/json/markushgrapher_layer2.json` | ❌ Not generated | Parser not yet implemented |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ Not generated - Parser not yet implemented
- ℹ️ N/A - Not applicable

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~188,000 | 0 | 0% | ❌ Parser not implemented |
| **Validation** | ~23,500 | 0 | 0% | ❌ Parser not implemented |
| **Test** | ~23,500 | 0 | 0% | ❌ Parser not implemented |
| **Total** | ~235,000 | 0 | 0% | ❌ Parser not implemented |

**Split Status Legend**:

- ❌ Missing - Parser not yet implemented

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | ~235,000 |
| **Training Split** | ~188,000 (80%) |
| **Validation Split** | ~23,500 (10%) |
| **Test Split** | ~23,500 (10%) |
| **Image Dimensions** | Variable (chemical structure diagrams) |
| **Resolution (DPI)** | Born-digital (vector graphics) |
| **File Format(s)** | PNG, SVG |
| **Color Space** | Grayscale / Binary (line drawings) |
| **Total Size on Disk** | ~10 GB (estimated) |
| **Annotation Format** | JSON (SMILES + graph) |

##### 4.3 Text Statistics

> **Availability**: ℹ️ N/A - Chemical structures, not text documents.

##### Directory Structure

```text
markushgrapher/
├── train/
│   ├── images/
│   │   └── *.png, *.svg
│   └── annotations.json
├── val/
│   ├── images/
│   └── annotations.json
└── test/
    ├── images/
    └── annotations.json
```

##### Baseline Quality Metrics

> **Source**: [NEEDS_PROFILING] - Chemical structure diagram quality metrics differ from document IQA.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | SCIENTIFIC (chemistry, pharmaceutical) |
| **Document Types** | Chemical structure diagrams (Markush structures) |
| **Language(s)** | N/A (chemical notation) |
| **Temporal Range** | Recent (2020s) |
| **Acquisition Method** | Born-digital (programmatically generated or extracted from patents) |

##### 5.1 Class/Category Distribution

| Category | Count (estimated) | Percentage (estimated) |
|----------|-------------------|------------------------|
| Markush Structures | ~150,000 | ~64% |
| Generic Structures | ~50,000 | ~21% |
| Specific Structures | ~35,000 | ~15% |

> **Note**: Exact distribution not publicly documented; estimates based on typical Markush dataset composition.

##### 5.2 Class/Category Definitions

| Class/Category | ID | Description | Parent |
|----------------|-----|-------------|--------|
| Markush Structure | 1 | Generic chemical structure with variable groups | - |
| Generic Structure | 2 | Chemical structure template | - |
| Specific Structure | 3 | Concrete chemical compound | - |

> **Notes**:
>
> - Markush structures represent families of compounds (common in patents)
> - Generic structures are templates with placeholders
> - Specific structures are concrete molecules

##### 5.3 Language & Script Coverage

> **N/A**: Chemical structures use universal chemical notation (not language-specific).

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Born-digital chemical structure diagrams |
| **Capture Device** | N/A (programmatic generation) |
| **Original Quality** | Clean vector graphics or high-quality raster |
| **Known Artifacts** | Rasterization artifacts (if converted from SVG to PNG) |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Thin lines and small text (atom labels) sensitive to blur |
| **Noise** | LOW | Clean born-digital diagrams |
| **Contrast** | LOW | Binary line drawings (black on white) |
| **Compression** | MEDIUM | JPEG artifacts affect thin lines |
| **Resolution** | HIGH | Small atom/bond labels require high resolution |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Line Thickness** | Thin (1-2px) | Blur detection critical |
| **Text Labels** | Small atom symbols | Character recognition sensitive to resolution |
| **Graph Complexity** | High | Dense structures require high-quality rendering |
| **Vector Graphics** | Common (SVG) | Rasterization quality matters |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | MEDIUM - Specialized domain (chemical structure recognition) |
| **Unique Characteristics** | Large-scale Markush structure dataset |
| **Complementary Datasets** | Domain-specific; limited overlap with general document IQA |
| **Benchmark Suitability** | LOW - Limited to chemical structure recognition; not suitable as general document benchmark |
| **Known Limitations** | Specialized domain, not applicable to general document IQA |

#### 7. Known Issues & Limitations

- **Specialized Domain**: Chemical structure recognition; limited applicability to general document IQA
- **No General Text**: Chemical notation only; not suitable for OCR training
- **Graph Complexity**: Requires specialized parsing beyond standard layout detection
- **Rasterization Quality**: SVG-to-PNG conversion quality may vary
- **No IQA Annotations**: Quality assessment requires domain-specific metrics (bond accuracy, atom recognition)
- **Limited Layout Diversity**: Diagrams only; no full document context

#### 8. Representative Samples

> Placeholder - To be populated during dataset profiling and VLM inspection.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@article{morin2025markushgrapher,
  title={MarkushGrapher: Automatic Generation of Markush Structures
         for IP-Aware Molecular Representation},
  author={Morin, Lucas and Staar, Peter W. J. and others},
  journal={arXiv preprint arXiv:2503.16096},
  year={2025},
  url={https://huggingface.co/datasets/docling-project/MarkushGrapher-Datasets}
}
```

##### Related Works

- [PubChem](https://pubchem.ncbi.nlm.nih.gov/) - Chemical compound database
- [ChemDraw](https://www.perkinelmer.com/category/chemdraw) - Chemical structure drawing software

##### Leaderboards

- None currently available

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **SMILES Notation**: Standard chemical notation; requires chemistry knowledge for interpretation
- **Graph Representation**: Atoms and bonds represented as graph structures
- **Markush Variables**: Generic structures with variable groups (R1, R2, etc.)

##### 10.2 Implementation Notes

- **Parser Priority**: Low - specialized domain, low overlap with general document IQA
- **Domain Tagging**: Set `domain_level1=scientific`, `domain_level2=chemistry`
- **Chemical Parsing**: Requires specialized libraries (RDKit, OpenBabel) for SMILES parsing
- **Capture Method**: Set `born_digital` (programmatically generated diagrams)
- **Content Type**: Set `content_type=diagram` (chemical structures)

##### 10.3 External Resources

- **HuggingFace Dataset Card**: [https://huggingface.co/datasets/ds4sd/MarkushGrapher-Datasets](https://huggingface.co/datasets/ds4sd/MarkushGrapher-Datasets)
- **DS4SD (IBM Research)**: [https://ds4sd.github.io/](https://ds4sd.github.io/)
- **RDKit (Chemical Parsing)**: [https://www.rdkit.org/](https://www.rdkit.org/)

---

#### 11. Layer 2 Audit Summary

> **Status**: No audit performed. Parser not yet implemented. Low priority due to specialized domain.

---

#### 12. Reliability & Bottlenecks

> **Status**: Parser not implemented - no Layer 2 metadata available for reliability analysis.

---
