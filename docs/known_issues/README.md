# Known Issues

> **Last Updated**: 2026-02-11 | **Source**: JSSODa Layer 2 audit + Docling pipeline analysis

Cross-cutting issues discovered during Layer 2 metadata audits that affect multiple datasets, enrichment pipelines, or downstream text extraction. Each issue has a severity, scope, root cause analysis, and mitigation strategy.

## Issue Index

| ID | Title | Severity | Scope | Status |
|----|-------|----------|-------|--------|
| [KI-001](KI-001-layout-label-casing.md) | Docling layout label casing mismatch | CRITICAL | All 51 Docling-extracted datasets | AUTOMATED |
| [KI-002](KI-002-docling-table-multicolumn.md) | Docling Table detection on multi-column text | HIGH | Synthetic + multi-column documents | MANUAL |
| [KI-003](KI-003-docling-picture-dense-text.md) | Docling Picture detection on dense text | MEDIUM | Synthetic datasets | MANUAL |
| [KI-004](KI-004-llm-handwriting-synthetic.md) | LLM handwriting detection on synthetic images | HIGH | All synthetic datasets | PATTERN |
| [KI-005](KI-005-llm-capture-method-synthetic.md) | LLM cannot detect synthetic capture method | HIGH | All synthetic datasets | PATTERN |
| [KI-006](KI-006-llm-formula-semantic-confusion.md) | LLM formula detection semantic confusion | MEDIUM | All LLM-enriched datasets | MANUAL |
| [KI-007](KI-007-llm-domain-unk-generic.md) | LLM domain UNK on generic content | LOW | Narrative/creative datasets | ACCEPTED |
| [KI-008](KI-008-docling-multicolumn-text-extraction.md) | Docling multi-column text extraction failure | HIGH | All multi-column documents via Docling OCR | OPEN |

## Severity Definitions

| Level | Meaning |
|-------|---------|
| CRITICAL | Affects all datasets, causes schema violations or data corruption |
| HIGH | Affects multiple datasets, causes incorrect metadata or garbled text |
| MEDIUM | Affects specific dataset types, causes inaccurate but non-breaking metadata |
| LOW | Minor impact, cosmetic or edge-case |

## Status Definitions

| Status | Meaning |
|--------|---------|
| AUTOMATED | Fix exists as a script; run it before integration |
| PATTERN | Fix pattern documented; apply in each integration script |
| MANUAL | Requires per-dataset VLM inspection or manual review |
| ACCEPTED | Not a defect; documented as expected behavior |
| OPEN | No fix available; requires upstream changes or new pipeline |

## Integration Checklist

When writing a new dataset integration script, check every issue in this index. The quick checklist:

**Pre-integration**:

- [ ] Run `standardize_layout_labels.py --dataset <name>` (KI-001)
- [ ] Determine `capture_method` from dataset documentation, not LLM (KI-005)
- [ ] For synthetic datasets: plan `has_handwriting=False` override (KI-004)

**During integration**:

- [ ] Use `derive_content_flags()` from standardized layout as baseline
- [ ] For synthetic datasets: override `has_table`, `has_figure`, `has_handwriting` from VLM or documentation (KI-002, KI-003, KI-004)
- [ ] For `has_formula=True`: require VLM verification (KI-006)
- [ ] Accept `domain_level1=UNK` without forcing reclassification (KI-007)

**Post-integration**:

- [ ] Run prescreening to verify field population
- [ ] VLM-inspect all `content_flag=True` samples (minimum)
- [ ] VLM-inspect 10-15 stratified passing samples for accuracy validation
- [ ] Document all corrections in `vlm_corrections.json`

## Machine-Readable Advisory

A structured JSON version of KI-001 through KI-007 is maintained at:
[`scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json`](../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json)
