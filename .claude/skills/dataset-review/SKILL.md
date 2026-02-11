# Dataset Review Skill

Dataset catalog review and validation workflow using the dataset-catalog-agent. Reviews, validates, and completes dataset catalog entries ensuring template compliance, parser coverage, Layer 2 schema compliance, and cross-file consistency.

## Activation

Auto-activates on keywords: review dataset, audit dataset, check dataset, dataset catalog, validate dataset, dataset entry

## Usage

```
/dataset-review {dataset_name}
/dataset-review {dataset_name} --category {category}
/dataset-review {dataset_name} --priority P0
/dataset-review {dataset_name} --skip-parser-update
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `dataset_name` | Yes | - | Canonical name per DATASET_NAMING_STANDARD.md |
| `--category` | No | auto-detect | forms, tables, handwriting, language, iqa, documents |
| `--priority` | No | P2 | P0 (critical), P1 (high), P2 (medium), P3 (low) |
| `--skip-parser-update` | No | false | Audit only, no parser modifications |

## Examples

```bash
# Review cocotext dataset with default settings
/dataset-review coco-text

# Review with explicit category
/dataset-review nist-sd2 --category forms

# Critical priority review
/dataset-review ohr-bench --priority P0

# Audit only (no changes)
/dataset-review tablebank --skip-parser-update
```

## Workflow Phases

1. **Pre-flight**: Verify dataset exists, validate naming, check prerequisites
2. **Analysis**: Gap analysis against DATASET_TEMPLATE.md
3. **Research**: Paper lookup, repository review, file structure verification
4. **Catalog Update**: Restructure entry to match template
5. **Parser Audit**: Compare source labels to parser extraction
6. **Text Integration**: Verify Layer 2 text_content compliance
7. **Synchronization**: Update Quick Reference and Processing Status
8. **Validation**: Final checklist and completion report

## Outputs

- Updated `docs/datasets/source/{dataset}.md` entry
- Updated `docs/datasets/DATASET_QUICK_REFERENCE.md` row
- Updated `docs/datasets/DATASET_PROCESSING_STATUS.md` status
- Gap analysis: `tmp_cleanup/.tmp-{dataset}-gap-analysis.md`
- Research notes: `tmp_cleanup/.tmp-{dataset}-research.md`
- Completion report with PASS/FAIL per phase

## Agent Reference

This skill invokes the `dataset-catalog-agent` defined in `.claude/agents/dataset-catalog-agent.md`.

## Related Files

- **Template**: docs/datasets/DATASET_TEMPLATE.md
- **Catalog**: docs/datasets/source/ (individual dataset files)
- **Quick Reference**: docs/datasets/DATASET_QUICK_REFERENCE.md
- **Processing Status**: docs/datasets/DATASET_PROCESSING_STATUS.md
- **Naming Standard**: docs/datasets/DATASET_NAMING_STANDARD.md
- **Layer 2 Schema**: docs/schema/layer2_enrichment.schema.json

## Success Criteria

- All template sections populated or appropriately marked
- Parser audit complete with comparison matrix
- Text content handled OR blocker documented
- Cross-file counts and statuses consistent
- Quality rating assigned: Complete, Partial, or Stub
