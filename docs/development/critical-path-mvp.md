---
schema_type: common
title: "Critical Path to MVP"
description: "Dependencies and critical path analysis for MVP delivery"
tags: [planning, mvp, dependencies, critical-path]
status: published
owner: "docs-team"
purpose: "Identify minimum requirements and dependencies for MVP end-to-end testing"
---

# Critical Path to MVP

This document identifies the critical path to achieve MVP (Minimum Viable Product) that can perform end-to-end document processing with quality assessment and routing recommendations.

## MVP Definition

**MVP Goal**: Process a document (PDF/image), assess quality, and output metadata with routing recommendations for Project B.

**MVP Outputs**:
1. `DocumentMetadata.json` with:
   - Document identification
   - Per-page quality scores (DQS)
   - Overall document quality score
   - OCR routing recommendation
   - Detected issues and corrections applied

## Critical Path Milestones

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CRITICAL PATH TO MVP                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 0 ✅ ──► Phase 4.1 ✅ ──► Phase 4.6 ──► Phase 8.1 ──► Phase 8.4  │
│  Foundation     Blur            Discrepancy     DQS           JSON       │
│                 Detection       Tuning          Weighting     Output     │
│                                                                          │
│         ┌──────────────────────────────────────────┐                    │
│         │ PARALLEL TRACK (Enhancement, not MVP)    │                    │
│         │ Phase 6: Layout-Lite (optional for MVP)  │                    │
│         │ Phase 10: Validation & Documentation     │                    │
│         └──────────────────────────────────────────┘                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Milestone Dependencies

### Phase 0: Foundation ✅ COMPLETE
- **Status**: Complete
- **Dependencies**: None
- **Deliverables**: Project skeleton, logging, configuration

### Phase 2: ML IQA Training ✅ COMPLETE
- **Status**: Complete (teacher trained, student in progress)
- **Dependencies**: Phase 0
- **Deliverables**: ResNet-50 teacher, ResNet-18 student models

### Phase 4: Classical IQA

| Milestone | Status | Dependencies | MVP Critical |
|-----------|--------|--------------|--------------|
| 4.1 Blur Detection | ✅ Complete | Phase 0 | YES |
| 4.2 Noise Estimation | ✅ Complete | Phase 0 | No (enhancement) |
| 4.3 Skew Detection | ✅ Exists | Phase 0 | YES |
| 4.4 Lighting Metrics | ⬜ Pending | Phase 0 | No (enhancement) |
| 4.5 JPEG Blockiness | ⬜ Pending | Phase 0 | No (enhancement) |
| 4.6 Discrepancy Tuning | ⬜ Pending | 4.1, 4.3, Phase 2 | YES |

### Phase 6: Layout-Lite Detection

| Milestone | Status | Dependencies | MVP Critical |
|-----------|--------|--------------|--------------|
| 6.1 YOLOv8-nano | ⬜ Pending | Phase 0 | No |
| 6.2 Handwriting | ⬜ Pending | 6.1 | No |
| 6.3 Complexity | ⬜ Pending | 6.1 | No |
| 6.4 Structural API | ⬜ Pending | 6.1-6.3 | No |

### Phase 8: DQS & Routing ← **MVP CRITICAL**

| Milestone | Status | Dependencies | MVP Critical |
|-----------|--------|--------------|--------------|
| 8.1 DQS Weighting | ⬜ Pending | 4.1, 4.3 (min) | **YES** |
| 8.2 Page/Doc Scoring | ⬜ Pending | 8.1 | **YES** |
| 8.3 Routing Logic | ⬜ Pending | 8.1, 8.2 | **YES** |
| 8.4 JSON Output | ⬜ Pending | 8.1-8.3 | **YES** |

### Phase 10: Validation & Documentation

| Milestone | Status | Dependencies | MVP Critical |
|-----------|--------|--------------|--------------|
| 10.1 Benchmarking | ⬜ Pending | Phase 8 | Post-MVP |
| 10.2 Model Comparison | ⬜ Pending | Phase 2, 8 | Post-MVP |
| 10.3 Stress Tests | ⬜ Pending | Phase 8 | Post-MVP |
| 10.4 Diagrams | ⬜ Pending | All | Post-MVP |
| 10.5 Documentation | ⬜ Pending | All | Post-MVP |

## MVP Critical Path (Minimum Implementation)

### Required for MVP:
1. **Phase 0**: ✅ Complete
2. **Milestone 4.1**: ✅ Blur detection (complete)
3. **Milestone 4.3**: ✅ Skew detection (existing)
4. **Milestone 8.1**: DQS weighting (in progress)
5. **Milestone 8.2**: Page/document scoring
6. **Milestone 8.3**: Routing logic
7. **Milestone 8.4**: JSON schema output

### Optional Enhancements (can defer):
- Milestone 4.2: Noise estimation (complete but optional)
- Milestone 4.4: Lighting metrics
- Milestone 4.5: JPEG blockiness
- Milestone 4.6: Discrepancy tuning (refines accuracy)
- All of Phase 6: Layout-lite detection
- All of Phase 10: Validation (post-MVP)

## Dependency Graph

```
Phase 0 (Foundation)
    │
    ├───► Phase 2 (ML IQA)
    │         │
    │         └───► Milestone 4.6 (Discrepancy Tuning)
    │
    ├───► Milestone 4.1 (Blur) ✅
    │         │
    ├───► Milestone 4.3 (Skew) ✅
    │         │
    │         └───┬───► Milestone 8.1 (DQS Weighting) ◄── CURRENT
    │             │
    │             └───► Milestone 8.2 (Page/Doc Scoring)
    │                       │
    │                       └───► Milestone 8.3 (Routing Logic)
    │                                 │
    │                                 └───► Milestone 8.4 (JSON Output)
    │                                           │
    │                                           └───► MVP COMPLETE
    │
    └───► Phase 6 (Layout-Lite) [OPTIONAL]
              │
              └───► Milestone 8.3 (enhances routing)
```

## MVP Timeline Estimate

| Milestone | Sprints | Est. Days |
|-----------|---------|-----------|
| 8.1 DQS Weighting | 2 | 2 |
| 8.2 Page/Doc Scoring | 2 | 2 |
| 8.3 Routing Logic | 2 | 2 |
| 8.4 JSON Output | 2 | 2 |
| **Total** | **8** | **8 days** |

## First End-to-End Test

**Prerequisites for first E2E test**:
1. ✅ PDF/Image ingestion
2. ✅ Basic IQA (blur, skew, contrast)
3. ✅ Corrections pipeline
4. ⬜ DQS calculation (Milestone 8.1-8.2)
5. ⬜ Routing recommendation (Milestone 8.3)
6. ⬜ JSON output with all fields (Milestone 8.4)

**First benchmark test prerequisites**:
- All of above for E2E
- Benchmark dataset (100+ documents)
- Benchmark framework (Phase 10.1)

## Simplified MVP Implementation Strategy

To achieve MVP fastest:

1. **Implement Milestone 8.1** (DQS weighting):
   - Use existing blur (4.1) and skew (4.3) scores
   - Simple weighted average formula
   - Configurable weights

2. **Implement Milestone 8.2** (Scoring):
   - Aggregate per-page scores
   - Document-level aggregation (mean/min)

3. **Implement Milestone 8.3** (Routing):
   - Simple threshold-based routing
   - 4 routing strategies

4. **Implement Milestone 8.4** (JSON Output):
   - Complete schema population
   - Validation against schema

## Current Status

- **Completed**: Phase 0, Phase 2 (mostly), Milestones 4.1, 4.2
- **In Progress**: Milestone 8.1
- **Remaining for MVP**: Milestones 8.2, 8.3, 8.4

---

*Last updated: 2025-11-23*
