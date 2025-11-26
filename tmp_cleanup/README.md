<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: MIT
-->

# tmp_cleanup/

**Purpose**: Temporary reference files to preserve context across conversation compactions (anti-compaction strategy).

## What Goes Here

**✅ Belongs in tmp_cleanup/**:

- Temporary analysis files (`.tmp-*.md`)
- Context preservation markdown files
- Implementation summaries
- Dataset analysis reports
- Planning documents (temporary)
- Session continuation references

**❌ Does NOT belong here** (and where it should go instead):

- **Permanent documentation** → `docs/` (formal documentation)
- **Architecture decisions** → `docs/ADRs/` (architectural decision records)
- **Project plans** → `docs/planning/` (project plans, roadmaps)
- **Code artifacts** → `src/` or `scripts/` (actual code)

## Naming Convention

All files use the `.tmp-` prefix to indicate temporary status:

```text
.tmp-{task-type}-{timestamp}.md
```text

Examples:

- `.tmp-dataset-analysis-20251113.md`
- `.tmp-iqa-implementation-20250205.md`
- `.tmp-phase2-summary-20251113.md`

## Gitignore Policy

Temporary files are gitignored:

```gitignore
# From .gitignore
tmp_cleanup/.tmp-*
```text

## Use Cases

### Context Preservation

When Claude Code conversations risk compaction (memory limits), create temporary reference files to preserve:

- TODO lists with >5 items
- Complex implementation details
- Multi-step workflow progress
- Agent assignments and status

### Implementation Summaries

After completing significant work:

- Capture key decisions made
- Document implementation approach
- List affected files and changes
- Track open questions/risks

### Dataset Analysis

Store temporary analysis of datasets:

- Coverage gaps identified
- Quality issues found
- Integration challenges
- Migration plans

## Lifecycle

1. **Create**: When starting complex multi-turn task
2. **Update**: As task progresses and context accumulates
3. **Archive**: After task completion and findings documented
4. **Delete**: After 30-60 days if no longer needed

## Example File Structure

```markdown
# .tmp-phase2-dataset-prep-20251113.md

## Context
Preparing IQA datasets for Phase 2 training on Google Colab.

## Progress
- [x] Downloaded LIVE dataset
- [x] Downloaded CSIQ dataset
- [ ] Generate synthetic degradations
- [ ] Upload to Google Drive

## Key Decisions
- Using Albumentations for augmentation pipeline
- Target 50k images (10k real + 40k synthetic)
- Weak supervision with BRISQUE/NIQE labels

## Open Questions
- Optimal BRISQUE threshold for clean/degraded split?
- Should we include camera shake degradation?

## Next Steps
1. Run augmentation pipeline
2. Validate synthetic samples
3. Upload to Drive
4. Update PROJECT_PLAN.md with final dataset composition
```text

## Cleanup Policy

Temporary files should be:

- **Reviewed monthly**: Delete files >60 days old
- **Migrated to docs/**: Move important findings to formal documentation
- **Summarized in ADRs**: Extract key decisions into Architecture Decision Records

## Distinction from Other Folders

### vs. docs/

- **tmp_cleanup/**: Temporary, informal, work-in-progress notes
- **docs/**: Permanent, formal, structured documentation

### vs. validation/

- **tmp_cleanup/**: Text-based reference files (.md)
- **validation/**: Code-based validation scripts (.py)

### vs. logs/

- **tmp_cleanup/**: Human-readable context preservation
- **logs/**: Machine-generated application logs

## Best Practices

1. **Descriptive Names**: Include task type and date in filename
2. **Markdown Format**: Use markdown for readability
3. **Regular Cleanup**: Delete obsolete files monthly
4. **Migration Path**: Move important content to formal docs
5. **Not Permanent**: This folder is a temporary workspace

## Tools Integration

The TODO management tool uses tmp_cleanup/ to:

- Preserve TODO lists across compactions
- Store agent assignment history
- Track multi-step workflow progress
- Maintain context for complex tasks
