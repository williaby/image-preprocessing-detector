---
l4_generated: manual
owner: docs-team
tags:
- architecture
- workstream_3
title: 'Level 4: Data Preparation — WS3 Instance Registry'
---

# Level 4: Data Preparation — WS3 Annotation Adapter Registry

This index covers **WS3 (Data Preparation)** per-instance registries. These 135 adapter files are
excluded from Level 2 PUML diagrams by design; this Level 4 tier is their authoritative catalog.

## Registry Documents

| Document | Type | Contents | Coverage |
|----------|------|----------|----------|
| [annotation-parser-registry.md](annotation-parser-registry.md) | AUTO | ~59 parser adapters grouped by task | `parsers/` subdirs |
| [annotation-provider-registry.md](annotation-provider-registry.md) | AUTO | 5 enrichment providers | `enrichment/providers/` |
| [annotation-integrate-registry.md](annotation-integrate-registry.md) | AUTO | ~52 integrate scripts | `scripts/integrate_*_enrichments.py` |

## Adapter Directory Structure

```text
src/image_preprocessing_detector/annotation/
├── parsers/
│   ├── correction/     (8 adapters)   — geometric correction datasets
│   ├── document/       (10 adapters)  — general document understanding datasets
│   ├── formula/        (1 adapter)    — mathematical formula datasets
│   ├── handwriting/    (9 adapters)   — handwriting recognition datasets
│   ├── layout/         (10 adapters)  — layout detection datasets
│   ├── multilingual/   (16 adapters)  — multilingual / multi-script datasets
│   └── quality/        (5 adapters)   — image quality assessment datasets
└── enrichment/
    └── providers/       (5 adapters)   — enrichment computation providers

scripts/
└── integrate_*_enrichments.py  (~52 scripts) — L2 metadata integration
```

## Update Procedure

After adding or removing an adapter file in any of the directories above:

```bash
# Regenerate all three registries
python scripts/generate_level4_registries.py --category all

# Verify 0 warnings
python scripts/generate_level4_registries.py --check
```

The registries (AUTO type) are fully overwritten on each run.

## Cross-References

- **Level 2**: `docs/architecture/diagrams/level-2/data-preparation/` — workflow diagrams
- **Level 3**: `docs/architecture/diagrams/level-3/data-preparation/` — module swimlanes
- **Design spec**: `docs/handoff/LEVEL4_ARCHITECTURE_DESIGN_HANDOFF.md`
