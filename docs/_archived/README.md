# Archived Documentation

**Archived**: 2026-02-09
**Reason**: Docs streamlining to reduce clutter from superseded, abandoned, and out-of-scope content.

These files are preserved for historical reference but are no longer part of the active documentation tree. Git history is preserved via `git mv`.

## Archive Categories

| Directory | Contents | Why Archived |
|-----------|----------|-------------|
| `planning/pre-siglip2/` | MUSIQ, DocIQ, old labeling approaches | Replaced by SigLIP 2 multi-task architecture |
| `planning/diqa-deqa-research/` | DIQA-5000 pseudo-labeling, DeQA replication | Abandoned research (IQA Phase 7 165K dataset confirmed flawed) |
| `planning/phase7-original/` | Phase 7 sprint plans, critiques, deep dives | Written for old ResNet architecture; Phase 7 NOT STARTED, will use SigLIP 2 |
| `planning/misc-superseded/` | Phase 2 cleanup, benchmarking arena, fixtures | Various superseded or unexecuted plans |
| `planning/workflows-opus/` | Opus workflow analysis and remediation plans | Analysis with unresolved action items from Nov 2025-Jan 2026 |
| `cross-project/` | Project B/C/D planning, schemas, diagrams | Out of scope for Project A repository |
| `development/` | Old architecture, code-quality, MVP guides | Superseded by docs/architecture/ hierarchy and CLAUDE.md standards |
| `guides/` | Nov 2025 user guides | Predate Phase 3-4 completion and SigLIP 2 planning |
| `reference/` | Old taxonomies, sufficiency reports | Superseded by layout taxonomy system and benchmarks/ directory |

## Finding Content

If you need to reference archived content, the files retain their original names and can be found via:
```bash
find docs/_archived/ -name "*.md" | sort
```
