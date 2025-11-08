---
schema_type: common
title: "Image Preprocessing Detector"
description: "Intelligent image preprocessing detection system for RAG applications"
tags: [computer_vision, image_processing, rag, document_analysis]
status: published
owner: "core-maintainer"
review_cycle_days: 90
authors:
  - name: "Byron Williams"
purpose: "Provide comprehensive documentation for the Image Preprocessing Detector system."
---

Welcome to the **Image Preprocessing Detector** documentation. This system intelligently analyzes documents (PDFs, images) and identifies required preprocessing steps before vector database ingestion for RAG applications.

## Key Features

- **Text Detection Gate**: Fast routing to specialized processing paths
- **Classical Computer Vision**: Skew, blur, contrast, and noise detection
- **Deep Learning**: YOLOv8 layout detection and ML-based image quality assessment
- **Hybrid IQA**: Per-element quality assessment for embedded images in documents
- **Correction Pipeline**: OpenCV-based corrections with guardrails
- **JSON Output**: COCO-aligned metadata for downstream processors

## Quick Start

Install the package:

```bash
pip install image-preprocessing-detector
```

Process a document:

```bash
imgprep process input.pdf --output result.json
```

## Architecture Overview

The system uses a multi-stage pipeline with text detection fork:

```
PDF/Image Input → Ingestion (300 DPI) → Text Gate
                                           ↓         ↓
                                      [NO TEXT]  [TEXT]
                                           ↓         ↓
                                   Classical IQA  YOLOv8 Layout
                                           ↓         ↓
                                      Correction Pipeline
                                           ↓
                                      JSON Output
```

## Navigation

- **[Getting Started](guides/installation.md)**: Installation and setup instructions
- **[User Guide](guides/overview.md)**: Comprehensive usage documentation
- **[API Reference](api/index.md)**: Complete API documentation
- **[Tools](tools/index.md)**: Available scripts and utilities
- **[Development](development/contributing.md)**: Contributing guidelines

## Project Status

**Current Phase**: Phase 1 - MVP with Classical Methods

- ✅ Phase 0: Foundation & Scaffolding (Complete)
- 🚧 Phase 1: MVP with Classical Methods (In Progress)
- ⏳ Phase 2: ML for Image Quality
- ⏳ Phase 3: ML for Document Layout
- ⏳ Phase 4: Production Hardening

## License

This project is licensed under the MIT License. See the [License](project/license.md) page for details.
