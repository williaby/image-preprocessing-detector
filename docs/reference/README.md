---
schema_type: common
title: "Reference Documentation"
description: "Technical reference materials, taxonomies, and operational references for the Image Preprocessing Detector project"
tags: [reference, documentation, taxonomy, coverage]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Index of reference documentation including taxonomies, model references, and operational guides."
---

This folder contains technical reference materials and operational guides for the Image Preprocessing Detector project.

## Contents

### Taxonomies & Classifications

- [**detection-taxonomy.md**](detection-taxonomy.md) - Classification of image quality issues, severity levels, detection methods, and correction strategies

### Model References

- [**MODEL_CARDS.md**](MODEL_CARDS.md) - Model inventory and specifications (ResNet-50 teacher, ResNet-18 student, YOLOv10-doc)
- [**MODEL_STORAGE.md**](MODEL_STORAGE.md) - Model artifact storage locations (GCS + local)
- [**DUAL_STORAGE_STRATEGY.md**](DUAL_STORAGE_STRATEGY.md) - GCS and local storage strategy

### Operational References

- [**MODAL_QUICK_REFERENCE.md**](MODAL_QUICK_REFERENCE.md) - Modal GPU platform quick reference
- [**MIGRATION_GUIDE.md**](MIGRATION_GUIDE.md) - Phase renumbering and migration procedures
- [**CITATIONS.md**](CITATIONS.md) - Academic citations and references
- [**REPOSITORY_STRUCTURE.md**](REPOSITORY_STRUCTURE.md) - Repository directory structure
- [**REVIEW_AND_MERGE_POLICY.md**](REVIEW_AND_MERGE_POLICY.md) - Automated review and branch-merge policy (CodeRabbit advisory, ruleset gates)

### Testing References

- [**TESTING_STRATEGY.md**](TESTING_STRATEGY.md) - Testing strategy and approach

## Related Documentation

- [API Reference](../api/) - Module and function documentation
- [Architecture](../architecture/) - System design and architecture
- [ADRs](../ADRs/) - Architecture decision records
- [Benchmarks](../benchmarks/) - Model benchmark results

---

*Last Updated: 2026-02-09*
