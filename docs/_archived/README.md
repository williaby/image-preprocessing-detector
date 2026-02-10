---
schema_type: common
title: Archived Documentation
status: published
owner: core-maintainer
tags:
  - documentation
  - maintenance
purpose: "Preserves superseded and out-of-scope documents for historical reference."
---

> **These documents are NOT part of the active documentation tree.**
> For current docs, start from the [project root README](../../README.md) or these active directories:
>
> - **Planning**: [docs/planning/](../planning/) (19 active planning docs)
> - **Architecture**: [docs/architecture/](../architecture/) (4-level diagram hierarchy)
> - **Datasets**: [docs/datasets/](../datasets/) (5-tier modular system)
> - **Deployment**: [docs/deployment/](../deployment/) (unified runbook)
> - **API**: [docs/api/](../api/) (endpoint reference)
> - **Handoff**: [docs/handoff/](../handoff/) (Project B contract)

**Archived**: 2026-02-09
**Reason**: Docs streamlining to reduce clutter from superseded, abandoned, and out-of-scope content.

These files are preserved for historical reference. Git history is preserved via `git mv`.

## Archive Categories

| Directory | Contents | Why Archived | Replaced By |
|-----------|----------|-------------|-------------|
| `planning/pre-siglip2/` | MUSIQ, DocIQ, old labeling approaches | Replaced by SigLIP 2 multi-task architecture | [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) |
| `planning/diqa-deqa-research/` | DIQA-5000 pseudo-labeling, DeQA replication | Abandoned research (IQA Phase 7 165K dataset confirmed flawed) | [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |
| `planning/phase7-original/` | Phase 7 sprint plans, critiques, deep dives | Written for old ResNet architecture; Phase 7 will use SigLIP 2 | [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) |
| `planning/misc-superseded/` | Phase 2 cleanup, benchmarking arena, fixtures | Various superseded or unexecuted plans | [PROJECT_PLAN.md](../planning/PROJECT_PLAN.md) |
| `planning/workflows-opus/` | Opus workflow analysis and remediation plans | Analysis with unresolved action items from Nov 2025-Jan 2026 | [IMPLEMENTATION_STATUS_MATRIX.md](../planning/IMPLEMENTATION_STATUS_MATRIX.md) |
| `cross-project/` | Project B/C/D planning, schemas, diagrams | Out of scope for Project A repository | N/A (separate repos) |
| `development/` | Old architecture, code-quality, MVP guides | Superseded by architecture hierarchy and CLAUDE.md | [docs/architecture/](../architecture/) |
| `guides/` | Nov 2025 user guides | Predate Phase 3-4 completion and SigLIP 2 planning | [DEPLOYMENT_RUNBOOK.md](../deployment/DEPLOYMENT_RUNBOOK.md) |
| `reference/` | Old taxonomies, sufficiency reports | Superseded by layout taxonomy system and benchmarks | [docs/datasets/](../datasets/), [docs/benchmarks/](../benchmarks/) |

## Finding Content

If you need to reference archived content:

```bash
# List all archived docs
find docs/_archived/ -name "*.md" | sort

# Search within archived docs
grep -r "keyword" docs/_archived/
```
