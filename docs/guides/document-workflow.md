# Document Processing Workflow

This guide explains how the image preprocessing detector processes files, from input to output.

## 1. How the App Knows What File to Review

### CLI Entry Point

The application uses a Click-based CLI defined in `src/image_preprocessing_detector/cli.py`:

```bash
# Single file processing
imgprep process <input_path> --output result.json

# Batch processing
imgprep batch <input_dir> --output-dir <output_dir>
```

### Supported File Formats

| Type | Extensions |
|------|------------|
| **PDFs** | `.pdf` |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.bmp`, `.webp` |

### File Loading Process

- **PDFs**: PyMuPDF extracts each page as an image at 300 DPI
- **Images**: PIL extracts metadata (EXIF DPI), OpenCV loads the pixel data

---

## 2. What the App Does to the File

### Processing Pipeline

Each page goes through the following steps:

| Step | Module | Purpose |
|------|--------|---------|
| **Pre-flight** | `ingestion/pdf_analyzer.py` | DPI detection, auto-upscale if <300 DPI |
| **Text Gate** | `detection/text_gate.py` | Fast (<50ms) ensemble to detect text presence |
| **Classical IQA** | `detection/iqa_classical.py` | Skew (Hough), blur (Laplacian), contrast (histogram) |
| **ML IQA** | `detection/iqa_ml.py` | ResNet-18 student model quality scores (optional) |
| **Layout-Lite** | `detection/layout_lite/` | Coarse attributes: tables, figures, columns (optional) |
| **Corrections** | `correction/corrections.py` | Deskew, CLAHE contrast, sharpening (if not `--dry-run`) |

### Pipeline Flow Diagram

```
Input File
    │
    ▼
┌─────────────────────────────────────────┐
│ File Format Detection                   │
│ PDF vs Image                            │
└─────────────────────────────────────────┘
    │
    ├─────────────────┐
    ▼                 ▼
┌─────────────┐  ┌─────────────────────────┐
│ PDF Branch  │  │ Image Branch            │
├─────────────┤  ├─────────────────────────┤
│ Pre-flight  │  │ PIL/OpenCV loading      │
│ DPI upscale │  │ Metadata extraction     │
│ PyMuPDF     │  │ Single page processing  │
│ Multi-page  │  │                         │
└─────────────┘  └─────────────────────────┘
    │                 │
    └────────┬────────┘
             ▼
    For Each Page:
             │
             ├── Text Gate Detection (ensemble)
             │
             ├── If text detected:
             │   ├── Classical IQA (skew, blur, contrast)
             │   ├── ML IQA optional (student + teacher)
             │   └── Layout-Lite analysis (coarse attributes)
             │
             ├── If corrections enabled:
             │   ├── Deskew (if skew detected + confident)
             │   ├── Contrast enhancement (if low contrast)
             │   └── Sharpening (if blur detected)
             │
             └── Record transform history
             │
             ▼
    ┌─────────────────────────────────────────┐
    │ Aggregate Results                       │
    │ - DQS calculation                       │
    │ - Routing recommendation                │
    │ - Teacher usage tracking                │
    └─────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────┐
    │ Output                                  │
    │ - DocumentMetadata.json                 │
    │ - Corrected images (if applied)         │
    └─────────────────────────────────────────┘
             │
             ▼
    Project B Handoff (OCR Orchestration)
```

### Correction Guardrails

The correction module applies safeguards to avoid damaging images:

- **Skew correction**: Skip if angle <0.5° or >45°, or confidence <0.3
- **All corrections**: Record a transform history audit trail for traceability

---

## 3. What the Output Contains

### Output Files

The application produces two types of output:

1. **`DocumentMetadata.json`** - Structured metadata about the document and processing results
2. **Corrected images** - Modified image files (if corrections were applied)

### JSON Schema Structure

The output schema is defined in `src/image_preprocessing_detector/schema.py`:

```json
{
  "document_id": "doc_001",
  "file_name": "sample.pdf",
  "source_mime": "application/pdf",
  "num_pages": 3,
  "pdf_type": "born_digital",
  "languages": ["en"],
  "pre_ocr_risk": 0.25,
  "dqs": {
    "degradation_score": 0.85,
    "structural_complexity_score": 0.3
  },
  "ocr_routing_recommendation": "ocr_fast",
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 300,
      "dpi_effective": 300,
      "detected_issues": [
        {
          "type": "skew",
          "severity": "medium",
          "confidence": 0.85,
          "metrics": {"angle": 2.5, "method": "hough"}
        }
      ],
      "planned_actions": [
        {
          "action": "deskew",
          "params": {"angle": 2.5},
          "confidence": 0.85,
          "reason": "Detected skew of 2.50°"
        }
      ],
      "transform_history": [
        {
          "action": "deskew",
          "params": {"angle": 2.5, "confidence": 0.85},
          "started_at": "2025-01-15T10:30:00Z",
          "finished_at": "2025-01-15T10:30:00.015Z",
          "status": "success"
        }
      ]
    }
  ]
}
```

### Key Output Fields

| Field | Description |
|-------|-------------|
| `document_id` | Unique identifier for the document |
| `file_name` | Original input filename |
| `num_pages` | Total number of pages processed |
| `pdf_type` | Classification: `image_only`, `born_digital`, or `hybrid` |
| `pre_ocr_risk` | Risk score (0-1) for OCR processing |
| `dqs` | Document Quality Score with degradation and complexity metrics |
| `ocr_routing_recommendation` | Suggested OCR strategy for Project B |
| `pages` | Array of per-page metadata |

### Per-Page Fields

| Field | Description |
|-------|-------------|
| `page_index` | Zero-based page number |
| `width_px` / `height_px` | Page dimensions in pixels |
| `dpi_effective` | Effective DPI after any upscaling |
| `detected_issues` | Array of quality problems found (blur, skew, contrast) |
| `planned_actions` | Corrections that will/would be applied |
| `transform_history` | Audit trail of applied corrections with timestamps |

### Document Quality Score (DQS)

The DQS provides two metrics for downstream decision-making:

| Metric | Range | Description |
|--------|-------|-------------|
| `degradation_score` | 0-1 | Image quality (0 = worst, 1 = pristine) |
| `structural_complexity_score` | 0-1 | Layout complexity (0 = simple, 1 = very complex) |

### OCR Routing Strategies

The `ocr_routing_recommendation` field suggests which strategy Project B should use:

| Strategy | When Used |
|----------|-----------|
| `ocr_fast` | Born-digital documents with high quality and simple layout |
| `ocr_advanced` | High-risk or complex documents |
| `vision_simple` | Image-only documents with simple layout |
| `vision_structured` | Documents containing tables or figures |

---

## Related Documentation

- [Quick Start Guide](quick-start.md) - Getting started with the CLI
- [Configuration Guide](configuration.md) - Environment variables and settings
- [IQA Guide](iqa.md) - Image Quality Assessment details
- [Correction Guide](correction.md) - Image correction algorithms
- [Schema API Reference](../api/schema.md) - Full Pydantic model documentation
