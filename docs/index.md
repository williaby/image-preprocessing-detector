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
- **Classical IQA**: 8 detectors (skew, blur, contrast, noise, illumination, JPEG blockiness, binarization, bleed-through)
- **ML IQA**: Teacher-student ResNet architecture (ResNet-50 teacher, ResNet-18 student)
- **Layout-Lite**: Coarse page attribute classification (11 DocLayNet classes via YOLOv10-doc)
- **DPI Upscaling**: Automatic resolution detection and upscaling for low-resolution inputs
- **Correction Pipeline**: OpenCV-based corrections with guardrails and audit trail
- **DQS & Routing**: Document Quality Score calculation with OCR routing recommendations
- **JSON Output**: COCO-aligned metadata for downstream OCR processors

## Quick Start

Install and run:

```bash
uv sync --extra dev
uv run imgprep process input.pdf --output result.json
```

## Architecture Overview

The system uses a multi-stage pipeline with text detection gate and DPI upscaling:

```text
PDF/Image Input → DPI Detection & Upscaling → Ingestion (300 DPI)
                                                    ↓
                                              Text Gate
                                           ↓            ↓
                                      [NO TEXT]     [TEXT]
                                           ↓            ↓
                                    Classical IQA  Layout-Lite
                                           ↓            ↓
                                      ML IQA (Student + selective Teacher)
                                           ↓
                                    Correction Pipeline
                                           ↓
                                    DQS & Routing → JSON Output
```

## Navigation

- **[Guides](guides/deployment.md)**: Deployment and operational guides
- **[API Reference](api/index.md)**: Complete API documentation
- **[Architecture](architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md)**: System architecture (4-level hierarchy)
- **[Planning](planning/PROJECT_PLAN.md)**: Project plan and active planning documents
- **[Development](development/index.md)**: Contributing guidelines and dev setup
- **[Datasets](datasets/DATASET_QUICK_REFERENCE.md)**: Dataset inventory (51 source datasets)
- **[ADRs](ADRs/README.md)**: Architecture decision records
- **[Model Cards](model-cards/REGISTRY.md)**: ML model documentation

## Project Status

- **Phase 0** (Complete): Foundation & Scaffolding
- **Phase 1** (Complete): MVP with Classical Methods + DPI Upscaling + Enhanced IQA
- **Phase 2** (Complete): Layout-Lite, DQS, Routing, PDF Classification
- **Phase 3** (Complete): Teacher-Student ML IQA (ResNet-50/18)
- **Phase 4** (98%): Device Priority & Production Hardening
- **Phase 5** (40%): Testing, Documentation & Deployment
- **Phase 6** (95%): Monitoring & Drift Detection

See [Project Plan](planning/PROJECT_PLAN.md) for detailed roadmap.

## License

This project is licensed under CC-BY-SA-4.0. See the [License](project/license.md) page for details.
