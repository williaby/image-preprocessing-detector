---
schema_type: common
title: "Level 1: Project A Architecture"
description: "System architecture and workstream data flow for Project A"
tags: [architecture, diagrams, plantuml, level-1]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Provide system-level view of Project A architecture showing all four workstreams and their interactions."
---

# Level 1: Project A Architecture

This level provides the complete system architecture for Project A (image-detection repository), showing how the four workstreams interact to deliver the preprocessing, IQA, and routing gateway functionality.

---

## Project A Architecture Overview

Project A serves as the "front door" for the RAG document pipeline, responsible for:

- **Document ingestion** and page extraction
- **Image Quality Assessment** (IQA) using classical CV and ML models
- **Layout detection** with DocLayout-YOLO (11 DocLayNet classes)
- **Corrections** (deskew, CLAHE, denoising)
- **Document Quality Score** calculation and routing recommendations

![Project A Architecture Overview](PROJECT_A_ARCHITECTURE_OVERVIEW.svg)

---

## Four Workstreams

Project A is organized into four interconnected workstreams:

### 1. Production Runtime (Green)

The live processing pipeline that handles incoming documents:

| Component | Purpose |
|-----------|---------|
| Ingestion & Pre-flight | DPI detection, PDF upscaling, page extraction |
| Classification & Routing | PDF type classification, text gate |
| Quality Analysis | Classical IQA (7 detectors), ML IQA (student/teacher) |
| Layout Analysis | DocLayout-YOLO (11 classes), reading order, table structure |
| Correction & Scoring | Deskew, CLAHE, denoising, DQS calculation, routing |

### 2. Model Training (Blue)

Training and optimization of production models:

| Model | Architecture | Purpose |
|-------|--------------|---------|
| IQA Teacher | ResNet-50 | High-capacity model for difficult cases |
| IQA Student | ResNet-18 | Production inference (distilled) |
| DocLayout-YOLO | YOLOv10-nano | Layout detection (11 DocLayNet classes) |

### 3. Data Preparation (Orange)

Dataset ingestion and normalization:

- Source dataset collection (OHR-Bench, DIQA-5000, DocLayNet, LIVE/CSIQ)
- 300 DPI normalization
- Train/val/test split creation

### 4. Pseudo-Labeling (Purple)

Multi-model ensemble for label generation:

| Track | Models | Focus |
|-------|--------|-------|
| Track A | MUSIQ, QualiCLIP, DocIQ-Replica | IQA metrics |
| Track B | Qwen3-VL-8B, InternVL3-8B | VLM-based assessment |

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 0** | [RAG Pipeline Overview](../level-0/index.md) | Multi-project pipeline context |
| **Level 1** | [Workflow Hierarchy](workflow-hierarchy.md) | Swimlane data flow |
| **Level 2** | [Production Runtime](../level-2/production-runtime/index.md) | Runtime workflow details |
| **Level 2** | [Model Training](../level-2/model-training/index.md) | Training pipeline |
| **Level 2** | [Data Preparation](../level-2/data-preparation/index.md) | Dataset ingestion |
| **Level 2** | [Pseudo-Labeling](../level-2/pseudo-labeling/index.md) | Ensemble workflow |

---

## Source Files

- **PlantUML**: [`PROJECT_A_ARCHITECTURE_OVERVIEW.puml`](PROJECT_A_ARCHITECTURE_OVERVIEW.puml)
- **Traceability**: [INDEX.md](../INDEX.md)
