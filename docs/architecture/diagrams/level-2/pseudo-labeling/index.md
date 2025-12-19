---
schema_type: common
title: "Level 2: Pseudo-Labeling"
description: "Detailed pseudo-labeling workflow diagrams for Project A"
tags: [architecture, diagrams, plantuml, level-2, pseudo-labeling]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the DIQA pseudo-labeling pipeline including multi-model ensemble, checkpoint selection, and training phases."
---

# Level 2: Pseudo-Labeling

This level provides detailed diagrams for the Pseudo-Labeling workstream - generating high-quality labels using multi-model ensembles.

---

## DIQA Pseudo-Labeling Workflow

Complete workflow for generating pseudo-labels using the 5-model ensemble.

![DIQA Pseudo-Labeling Workflow](diqa-pseudo-labeling-workflow.svg)

---

## DIQA Inference Pipeline

Infrastructure architecture for batch inference on Modal.

![DIQA Inference Pipeline](diqa-inference-pipeline.svg)

---

## Checkpoint Selection Algorithm

Weighted SRCC + ECE scoring for selecting optimal model checkpoints.

![Checkpoint Selection](diqa-checkpoint-selection.svg)

---

## Training Phases

Multi-phase training approach for the DIQA ensemble.

![Training Phases](diqa-training-phases.svg)

---

## Key Components

| Component | Description |
|-----------|-------------|
| Track A: IQA Models | MUSIQ (sharpness), QualiCLIP (color), DocIQ-Replica (overall) |
| Track B: VLM Models | Qwen3-VL-8B (generalist), InternVL3-8B (overall) |
| Hierarchical Stacker | Dimension-specific variance-weighted stacking |
| Temperature Scaler | Uncertainty calibration |

---

## Model Specialists

| Model | Specialty | Parameters |
|-------|-----------|------------|
| MUSIQ | Sharpness | 27M |
| QualiCLIP | Color | 150M |
| DocIQ-Replica | Overall | 25M + masks |
| Qwen3-VL-8B | Generalist | 8B |
| InternVL3-8B | Overall | 8B |

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Data Preparation](../data-preparation/index.md) | Dataset ingestion |
| **Level 2** | [Model Training](../model-training/index.md) | Training pipeline |
