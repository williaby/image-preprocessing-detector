---
schema_type: common
title: "Architecture Decision Records (ADRs)"
description: "Index of all architecture decision records for the Image Preprocessing Detector"
tags: [adr, architecture, decisions, documentation]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Track and document all significant architectural decisions with rationale and context."
---


This directory contains Architecture Decision Records (ADRs) for the Image Preprocessing Detector project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences. ADRs help us:

- Understand why decisions were made
- Track the evolution of the architecture
- Onboard new team members
- Avoid repeating past discussions
- Learn from both good and bad decisions

## ADR Format

Each ADR follows this structure:

```markdown
# ADR-NNN: [Title]

**Status**: [Proposed | Accepted | Deprecated | Superseded]
**Date**: YYYY-MM-DD
**Deciders**: [Names]
**Related**: [Links to related ADRs, issues, PRs]

## Context

What is the issue we're facing? What factors led to this decision?

## Decision

What did we decide to do?

## Consequences

### Positive

What are the benefits of this decision?

### Negative

What are the drawbacks or costs?

### Neutral

What are the neutral implications?

## Alternatives Considered

What other options did we evaluate and why were they rejected?

## References

Links to relevant documentation, discussions, or external resources.
```

## Index of ADRs

### Development Tooling & Infrastructure

- [ADR-001: Consolidate Python Linting with Ruff](0001-consolidate-linting-with-ruff.md) - **Accepted** (2025-01-08)
- [ADR-002: Separate Mutation Testing from Main CI](0002-separate-mutation-testing-workflow.md) - **Accepted** (2025-01-08)
- [ADR-003: Adopt Property-Based Testing with Hypothesis](0003-adopt-property-based-testing.md) - **Accepted** (2025-01-08)
- [ADR-004: GitHub Actions Security Hardening](0004-github-actions-security-hardening.md) - **Accepted** (2025-01-08)
- [ADR-005: MkDocs Documentation System with Front Matter Validation](0005-mkdocs-documentation-system.md) - **Accepted** (2025-11-08)

### Validation & Quality Assurance

- [ADR-006: Synthetic Validation Dataset Strategy](0006-synthetic-validation-dataset-strategy.md) - **Accepted** (2025-11-05)
- [ADR-011: Hybrid Validation Strategy for Threshold Calibration](0011-hybrid-validation-strategy.md) - **Accepted** (2025-11-05)
- [ADR-013: Real Testing Over Mocking Strategy](0013-real-testing-over-mocking.md) - **Accepted** (2025-11-05)

### System Architecture

- [ADR-007: Hybrid IQA Approach for Embedded Images](0007-hybrid-iqa-approach.md) - **Accepted** (2025-01-15)
- [ADR-008: Multi-Stage Pipeline with Text Detection Fork](0008-multi-stage-pipeline-architecture.md) - **Accepted** (2025-01-15)
- [ADR-009: COCO Bounding Box Format Standardization](0009-coco-bounding-box-format.md) - **Accepted** (2025-01-15)
- [ADR-010: 300 DPI Normalization Strategy](0010-300-dpi-normalization.md) - **Accepted** (2025-01-15)
- [ADR-014: Classical CV + ML Hybrid for IQA](0014-classical-ml-hybrid-iqa.md) - **Accepted** (2025-01-15)
- [ADR-015: YOLOv8 for Layout Detection](0015-yolov8-layout-detection.md) - **Accepted** (2025-01-15)
- [ADR-016: Defer Superscript/Footnote to Post-OCR](0016-defer-superscript-footnote-detection.md) - **Accepted** (2025-01-15)
- [ADR-029: Project A Scope Boundaries in RAG Pipeline](0029-project-a-scope-boundaries.md) - **Accepted** (2025-11-15)

### Technology Stack

- [ADR-017: Pydantic v2 for JSON Schema Validation](0017-pydantic-v2-json-schema.md) - **Accepted** (2025-01-15)
- [ADR-018: Poetry for Dependency Management](0018-poetry-dependency-management.md) - **Accepted** (2025-01-08)
- [ADR-019: Structured Logging with structlog + rich](0019-structured-logging.md) - **Accepted** (2025-01-08)

### Phase Planning & Deployment

- [ADR-012: Defer Handwriting Detection to Phase 2](0012-defer-handwriting-detection.md) - **Accepted** (2025-11-05)
- [ADR-020: CPU-First Deployment Strategy for Phase 1](0020-cpu-first-deployment-strategy.md) - **Accepted** (2025-11-04)
- [ADR-021: Do-No-Harm Guardrails for Image Corrections](0021-do-no-harm-guardrails.md) - **Accepted** (2025-11-04)

### Data & ML Models

- [ADR-022: Synthetic Data Generation with Albumentations](0022-synthetic-data-generation.md) - **Accepted** (2025-01-15)
- [ADR-023: Weak Supervision with BRISQUE/NIQE for IQA Labeling](0023-weak-supervision-brisque-niqe.md) - **Accepted** (2025-01-15)
- [ADR-024: Active Learning for Annotation Efficiency](0024-active-learning-annotation.md) - **Accepted** (2025-01-15)
- [ADR-025: MobileNetV3 vs EfficientNet for IQA Model Selection](0025-mobilenetv3-vs-efficientnet.md) - **Accepted** (2025-01-15)
- [ADR-026: Transfer Learning from ImageNet/COCO](0026-transfer-learning-imagenet-coco.md) - **Accepted** (2025-01-15)
- [ADR-027: INT8 Quantization via ONNX/TensorRT](0027-int8-quantization-onnx.md) - **Accepted** (2025-01-15)
- [ADR-028: ResNet Teacher-Student Architecture for ML IQA](0028-resnet-teacher-student-architecture.md) - **Accepted** (2025-11-15)
- [ADR-030: Document Quality Score (DQS) Design](0030-document-quality-score-design.md) - **Accepted** (2025-11-15)

## How to Create a New ADR

1. Copy the template above to a new file: `docs/adr/NNNN-short-title.md`
2. Use sequential numbering (check existing ADRs for the next number)
3. Fill in all sections with relevant information
4. Submit via pull request for team review
5. Update this index with the new ADR
6. Link to the ADR in related documentation

## ADR Lifecycle

- **Proposed**: Under discussion, not yet adopted
- **Accepted**: Decision has been made and is in effect
- **Deprecated**: No longer recommended, but still in use
- **Superseded**: Replaced by a newer ADR (link to replacement)

## Relationship to Other Documentation

- **DECISION_MATRIX.md**: High-level decision tracking (what needs deciding)
- **ADRs**: Detailed decision documentation (what was decided and why)
- **ARCHITECTURE_SUMMARY.md**: Current system architecture (result of decisions)
- **docs/development/architecture.md**: Architectural overview and design patterns
