---
schema_type: common
title: "Level 2: Data Preparation"
description: "Detailed data preparation workflow diagrams for Project A"
tags: [architecture, diagrams, plantuml, level-2, data-preparation]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the data preparation pipeline including dataset ingestion and automated labeling."
---

# Level 2: Data Preparation

This level provides detailed diagrams for the Data Preparation workstream - ingesting and normalizing training data.

---

## Training Data Ingestion

Pipeline for collecting, normalizing, and splitting training datasets.

![Training Data Ingestion](project-a-training-data-ingestion.svg)

---

## Automated Data Labeling Pipeline

Three-layer pipeline for dataset annotation and label management.

![Automated Data Labeling Pipeline](automated-data-labeling-pipeline.svg)

---

## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| Dataset Collection | `scripts/download_*.py` | Download source datasets |
| Base Metadata | `scripts/annotate_base_metadata.py` | Layer 1: Immutable annotations |
| Training Labels | `scripts/build_training_labels.py` | Layer 2: Training-specific labels |

---

## Datasets

| Dataset | Type | Purpose |
|---------|------|---------|
| OHR-Bench | IQA | Document quality assessment |
| DIQA-5000 | IQA | Additional IQA training data |
| DocLayNet | Layout | 11-class layout detection |
| LIVE/CSIQ | IQA Reference | Classical IQA benchmarks |

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Pseudo-Labeling](../pseudo-labeling/index.md) | Multi-model labeling |
| **Level 2** | [Model Training](../model-training/index.md) | Training pipeline |
