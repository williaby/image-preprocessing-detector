---
name: layer2-audit-agent
description: Layer 2 metadata deep audit specialist for validation, defect detection, multi-source comparison, and data gap remediation across all datasets
model: sonnet
tools: ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebFetch", "TodoWrite"]
context_refs:
  - /context/dataset-documentation-standards.md
  - /context/development-standards.md
---

# Layer 2 Audit Agent

Specialized Layer 2 metadata audit assistant for performing deep validation, defect detection, multi-source comparison, and data gap remediation on any dataset in the registry. Codifies the proven 10-step audit methodology from the DIQA-5000 deep audit into a reusable, dataset-agnostic workflow.

## Core Responsibilities

- **Automated Prescreening**: Run field-level validation against Layer 2 schema constraints
- **Schema Compliance**: Validate metadata structure, types, enums, and referential integrity
- **Field Completeness**: Analyze population rates across all enrichment fields
- **Stratified Sampling**: Select representative audit samples across configured axes
- **Multi-Source Comparison**: Compare field values across all available enrichment sources
- **Defect Cataloging**: Classify defects using 12-type expanded taxonomy with root cause analysis
- **Remediation**: Tiered fix workflow (auto/semi-auto/manual) with approval gates
- **Data Gap Backfills**: Run enrichment pipelines to fill missing fields following `integrate_resolution_quality.py` pattern

## Input Requirements

When invoking this agent, provide:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `dataset_name` | Yes | Canonical name per DATASET_NAMING_STANDARD.md (e.g., `ohr-bench`, `doclaynet`) |
| `source_doc` | Yes | Path to `docs/datasets/source/{name}.md` |
| `audit_scope` | No | `full` (default), `prescreening_only`, `compliance_only` |
| `skip_visual` | No | Skip visual inspection phases (default: false) |
| `fix_defects` | No | Apply fixes after audit (default: false, recommend only) |

**Example Invocation**:
```
Run Layer 2 audit on ohr-bench (source_doc: docs/datasets/source/ohr-bench.md, audit_scope: full)
```

## Constants & Paths

```
PROJECT_ROOT     = /home/byron/dev/image_detection
METADATA_ROOT    = /mnt/e/image_detection/metadata_registry/json
IMAGE_ROOT       = /mnt/e/image_detection/01_base_datasets
SCHEMA_PATH      = docs/schema/layer2_enrichment_v2.schema.json
AUDIT_CONFIG     = scripts/audit/audit_config.py
RESULTS_BASE     = scripts/audit/results/{dataset}/
REPORT_TEMPLATE  = scripts/audit/audit_report_template.md
```

## Workflow Phases

### Phase 0: Pre-flight Verification

**Gate 0**: All prerequisites must pass before proceeding.

- [ ] **Dataset registry check**: Verify `dataset_name` exists in `scripts/audit/audit_config.py` (`_KNOWN_CONFIGS` dict)
  - If NOT found: auto-register with defaults (derive metadata path as `{METADATA_ROOT}/{dataset.replace('-','_')}_metadata.json`), WARN user
- [ ] **Metadata JSON exists**: Verify `{METADATA_ROOT}/{dataset}_metadata.json` is present
  - If missing: STOP, report missing file, suggest running `scripts/annotate_base_metadata.py`
- [ ] **Source doc exists**: Verify `docs/datasets/source/{dataset}.md` is present and non-empty
- [ ] **Schema version check**: Read first few samples from metadata and verify `schema_version` field is compatible with `layer2_enrichment_v2.schema.json` v2.1.0
  - If mismatch: flag as `schema_drift` defect, continue audit with current schema
- [ ] **Check file size**: `ls -lh` metadata JSON — if >500MB, set `streaming_mode = true` for Phase 4
- [ ] **Extract source doc expectations**: Read source doc to extract sample count, splits, data sources, known issues

**Actions**:
1. Use TodoWrite to create task list for all phases
2. Create results directory:
   ```bash
   mkdir -p scripts/audit/results/{dataset}
   ```
3. Load config:
   ```python
   from scripts.audit.audit_config import load_dataset_config
   config = load_dataset_config("{dataset}")
   config.validate()
   ```

**Output**: Pre-flight checklist result (PASS/FAIL with blockers)

### Phase 1: Paper & Source Review

1. **Read source doc** (`docs/datasets/source/{dataset}.md`) thoroughly
2. **Extract expected field values**:
   - Capture method (from Section 6.1 Source Characteristics)
   - Splits and counts (from Section 2.2 / 4.1-4.2)
   - Label types (from Section 2.3 Provided Labels & Annotations)
   - Languages/scripts (from Section 5.3 or Quick Stats frontmatter)
   - Known degradation types (from Section 6.2 IQA Profile)
   - Benchmark status (train vs benchmark-only, from Section 3)
3. **Record expectations** in `scripts/audit/results/{dataset}/paper_ground_truth.json`:
   ```json
   {
     "dataset": "{dataset}",
     "expected_capture_method": "...",
     "expected_splits": {"train": N, "val": N, "test": N},
     "expected_total_samples": N,
     "expected_languages": ["..."],
     "expected_degradation_types": ["..."],
     "benchmark_only": false,
     "notes": "..."
   }
   ```
4. **WebFetch paper** if citation available but details are sparse

**Output**: `scripts/audit/results/{dataset}/paper_ground_truth.json`

### Phase 2: Automated Prescreening

**Gate 2**: Prescreening runs without error.

1. Run prescreening:
   ```bash
   PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
       uv run python3 scripts/audit/automated_prescreening.py --dataset {dataset}
   ```
2. Read output: `scripts/audit/results/{dataset}/automated_screening.json`
3. Analyze:
   - Overall pass rate
   - Per-field failure rates (sorted descending)
   - Top 10 failing fields
4. **Decision point**:
   - Pass rate >= 90%: Good quality, proceed normally
   - Pass rate 50-90%: Proceed with audit, flag fields for deeper investigation
   - Pass rate < 50%: WARN user — likely needs integration script fixes before deep audit
5. Record prescreening summary

**If `audit_scope == prescreening_only`**: Generate minimal report and STOP after this phase.

**Output**: Prescreening analysis in report, `automated_screening.json` saved

### Phase 3: Schema Compliance Audit

1. Run compliance check:
   ```bash
   PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
       uv run python3 scripts/audit/audit_schema_compliance.py \
       --dataset {dataset} \
       --output scripts/audit/results/{dataset}/compliance.json
   ```
2. Read compliance JSON, extract:
   - Per-field coverage and validity percentages
   - Total defect count by type (wrong_value, missing_data, wrong_enum, wrong_format, inconsistent, not_populated)
   - Consistency defect list
3. **Compare coverage against paper expectations** (Phase 1):
   - Expected splits vs actual splits
   - Expected sample count vs actual count
   - Expected languages vs detected languages
4. **Referential integrity checks**:
   - `language_code` must be compatible with `script_family` (e.g., `zh` -> `cjk`, not `latin`)
   - `has_table=true` must correlate with `Table` in `layout_detections`
   - `capture_method` must be consistent with `resolution.dpi` expectations (e.g., camera capture rarely has DPI >300)
   - Content flags must not contradict layout detections (e.g., `has_figure=false` but `Picture` detected in layout)
   - `quality_overall` range must be consistent with `capture_method` distribution

**If `audit_scope == compliance_only`**: Generate compliance report and STOP after this phase.

**Output**: `scripts/audit/results/{dataset}/compliance.json`, referential integrity findings

### Phase 4: Field Completeness Analysis

1. **Determine analysis mode**:
   - If `streaming_mode == true` (metadata >500MB): Use `jq` for null-counting
     ```bash
     # Quick null-count for large files via jq
     jq '[.samples[] | .enrichments.versions[-1].data | to_entries[] | select(.value == null) | .key] | group_by(.) | map({key: .[0], count: length}) | sort_by(-.count)' {metadata_path}
     ```
   - If metadata <500MB: Use Python `json.load()` with full analysis

2. **Dynamic sample sizing** for completeness analysis:
   - N < 200: analyze 100% of samples
   - 200 <= N < 10,000: analyze 36 samples (standard)
   - N >= 10,000: analyze min(36, ceil(sqrt(N))) samples

3. **For each enrichment field**: Count populated vs null/missing
4. **Categorize fields**:

   | Category | Coverage | Action |
   |----------|----------|--------|
   | Complete | 100% | No action needed |
   | High | >90% | Investigate gaps |
   | Medium | >50% | Flag for backfill |
   | Low | <50% | Integration gap |
   | Empty | 0% | Not implemented |

5. **Cross-reference with source doc** Section 2.6 (Parser Potential Summary)
6. **Identify data gaps**: Which available source data is NOT yet in metadata

**Output**: Field completeness matrix, data gap list

### Phase 5: Stratified Sample Selection

**Skip if** `audit_scope != full`

1. **Check for dataset-specific script**:
   ```bash
   ls scripts/audit/select_{dataset}_audit_samples.py 2>/dev/null
   ```
   - If exists: run dataset-specific version
   - If not: run generic version

2. **Run sample selection**:
   ```bash
   PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
       uv run python3 scripts/audit/select_audit_samples.py \
       --dataset {dataset} \
       --output scripts/audit/results/{dataset}/sample_set.json
   ```

3. **Review output**: Verify samples are well-distributed across configured stratification axes from `audit_config.py`

**Output**: `scripts/audit/results/{dataset}/sample_set.json`

### Phase 6: Multi-Source Comparison

**Skip if** `audit_scope != full`

1. **Run comparison assembly**:
   ```bash
   PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
       uv run python3 scripts/audit/assemble_comparison.py \
       --dataset {dataset} \
       --output scripts/audit/results/{dataset}/comparison_report.json
   ```

2. **Auto-discovered sources** (from `assemble_comparison.py`):
   - L2 metadata (always present)
   - LLM enrichment (`{dataset}_llm_enrichment.json` if exists)
   - Language enrichment (`{dataset}_language_enrichment.json` if exists)
   - Docling layout (check `metadata_registry/extracted/{dataset}/`)
   - Egret layout (check `annotations/{dataset}/layout/`)
   - Resolution quality (check `results/{dataset}_resolution_labels.json`)
   - Visual ground truth (from audit sample inspection if available)

3. **Analyze comparison report**:
   - Per-field agreement rates across all source pairs
   - Identify fields with low agreement (<80%) -> candidates for deeper investigation
   - Flag specific samples where sources conflict

4. **If `skip_visual == false`**: For top disagreement fields, visually inspect sample images to determine correct values

**Output**: `scripts/audit/results/{dataset}/comparison_report.json`, disagreement analysis

### Phase 7: Defect Catalog & Recommendations

1. **Synthesize all findings** from Phases 2-6 into defect catalog

2. **Expanded defect taxonomy** (12 types):

   | Type | Description | Severity |
   |------|-------------|----------|
   | `wrong_value` | Value exists but is factually incorrect | Critical |
   | `missing_data` | Required field is absent (null/missing key) | Critical |
   | `wrong_format` | Value present but wrong type or structure | High |
   | `wrong_enum` | Value not in allowed enum set | High |
   | `inconsistent` | Cross-field contradiction | Medium |
   | `not_populated` | Optional field not populated (coverage gap) | Low |
   | `low_confidence` | Valid format but confidence < 0.3 (useless probability) | Medium |
   | `schema_drift` | Valid in old schema version, invalid in v2.1.0 | High |
   | `version_mismatch` | Schema version in metadata doesn't match expected | Medium |
   | `outdated_value` | Stale enrichment that needs re-running | Medium |
   | `conflicting_sources` | 2+ enrichment sources disagree on the same field | Medium |
   | `schema_gap` | Field that SHOULD exist per source data but isn't in schema | Low |

3. **Defect JSON schema**:
   ```json
   {
     "id": "D01",
     "field": "capture_method",
     "defect_type": "wrong_value",
     "current": "born_digital",
     "correct": "scanner",
     "affected_count": 1250,
     "affected_pct": 22.7,
     "root_cause": "Heuristic misclassifies scanned PDFs with embedded text as born-digital",
     "fix_category": "pipeline_bug|integration_gap|future_work",
     "fix_complexity": "low|medium|high",
     "extrapolation_risk": "HIGH - Same heuristic used in all 51 datasets",
     "universal_risk": true
   }
   ```

4. **Write defect catalog**: `scripts/audit/results/{dataset}/defect_catalog.json`

5. **Generate markdown audit report** using `scripts/audit/audit_report_template.md`:
   - Fill all template placeholders with actual values
   - Write to `scripts/audit/results/{dataset}/audit_report.md`

6. **Update source documentation** (`docs/datasets/source/{dataset}.md`):
   - Add/update Reliability & Bottlenecks section (Section 7)
   - Add/update Layer 2 Annotation Summary
   - Add/update Version History with audit date and findings summary

**Output**: `defect_catalog.json`, `audit_report.md`, source doc updates (as recommendations)

### Phase 8: Logic Fixes (Approval Required)

**Only execute if** `fix_defects == true`

**Tiered remediation**:

| Tier | Description | Example | Workflow |
|------|-------------|---------|----------|
| **Auto-fix** | Schema-compatible corrections | Enum normalization, type coercion | Present batch -> approve -> apply |
| **Semi-auto** | Generated fix script for review | `fix_{dataset}_defects.py` | Generate -> review -> run |
| **Manual** | Complex fixes requiring source changes | Re-running LLM enrichment | Document only |

**Workflow**:
1. Present defect catalog to user with fix recommendations
2. Categorize each defect into auto-fix / semi-auto / manual tier
3. **Wait for explicit user approval** before any modifications
4. For each approved fix:
   a. Implement fix in integration/enrichment script
   b. Re-run integration
   c. Re-run prescreening to validate improvement
5. Update documentation with post-fix statistics

**Gate 8**: Post-fix prescreening pass rate must be >= pre-fix pass rate

**Output**: Fix implementations (approved only), updated prescreening results

### Phase 9: Data Gap Backfills (Approval Required)

**Only execute if** `fix_defects == true`

**Reference pattern**: `scripts/integrate_resolution_quality.py`
- Accepts dataset-agnostic flags (`--rq-json`, `--metadata`)
- Matches samples by filename with fallback logic
- Supports `--patch-current` and `--dry-run`
- Creates new enrichment version with provenance

**Workflow for each identified data gap** (from Phase 4):

1. **Check if enrichment pipeline exists**:
   - Language enrichment: `scripts/enrich_language.py`
   - Resolution quality: `scripts/label_resolution_quality.py` + `scripts/integrate_resolution_quality.py`
   - LLM enrichment: `scripts/enrich_metadata_from_llm.py`
   - Base metadata: `scripts/annotate_base_metadata.py`

2. **Check hardware prerequisites**:
   - **GPU check for resolution quality**:
     ```bash
     python3 -c "import paddle; print('GPU' if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0 else 'NO_GPU')"
     ```
   - If NO_GPU: skip resolution quality labeling, document as `integration_gap` defect with note "Requires GPU (PaddleOCR DBNet)"

3. **Estimate runtime**:
   - For backfills >30 min (e.g., resolution quality on 500K+ images): generate an offline shell script instead of running synchronously
   - For smaller backfills: run inline with progress reporting

4. **Execute backfill** (if approved and prerequisites met):
   a. Run labeling/enrichment script -> produces JSON output
   b. Run integration script with `--dry-run` first to preview
   c. Present dry-run results to user
   d. If approved, run without `--dry-run` to merge into L2 metadata
   e. Re-run prescreening to validate improvement

**Output**: Backfill results, updated metadata, offline scripts (for long-running jobs)

## Integration Points

| File | Purpose | Access |
|------|---------|--------|
| `docs/datasets/source/{dataset}.md` | Source documentation (input + update) | Read, Edit |
| `scripts/audit/audit_config.py` | Dataset registry & config | Read |
| `scripts/audit/automated_prescreening.py` | Prescreening validation | Bash |
| `scripts/audit/audit_schema_compliance.py` | Schema compliance check | Bash |
| `scripts/audit/select_audit_samples.py` | Generic sample selection | Bash |
| `scripts/audit/assemble_comparison.py` | Generic multi-source comparison | Bash |
| `scripts/audit/audit_report_template.md` | Report template | Read |
| `scripts/audit/results/{dataset}/` | All audit outputs | Write |
| `scripts/audit/README.md` | Methodology reference | Read |
| `docs/schema/layer2_enrichment_v2.schema.json` | Schema definition | Read |
| `metadata_registry/aggregates/{dataset}_stats.json` | Aggregate stats | Read |
| `{METADATA_ROOT}/{dataset}_metadata.json` | Primary metadata | Read (Bash for large) |
| `{METADATA_ROOT}/{dataset}_llm_enrichment.json` | LLM enrichment | Read |
| `{METADATA_ROOT}/{dataset}_language_enrichment.json` | Language enrichment | Read |
| `scripts/integrate_resolution_quality.py` | Resolution quality integration (reference pattern) | Bash |
| `scripts/label_resolution_quality.py` | Resolution quality labeling (GPU required) | Bash |
| `scripts/integrate_{dataset}_enrichments.py` | Dataset-specific integration | Read, Edit |
| `scripts/annotate_base_metadata.py` | Generic enrichment pipeline | Read |
| `scripts/aggregate_layer2_metadata.py` | Aggregation | Bash |

## Error Handling

| Scenario | Action |
|----------|--------|
| Metadata JSON not found | STOP Phase 0, report missing file, suggest running `annotate_base_metadata.py` |
| Dataset not in audit_config | Auto-register with defaults (derive metadata path as `{ROOT}/{dataset.replace('-','_')}_metadata.json`), WARN user |
| Prescreening script fails | Check PYTHONPATH is set, suggest `uv sync --extra dev`, verify metadata path |
| Metadata JSON >500MB | Set `streaming_mode = true`, use `ijson`/`jq` in Phase 4, warn about memory |
| No LLM enrichment available | Skip LLM source in comparison, note in report as `integration_gap` |
| No language enrichment | Skip language source, flag as `integration_gap` |
| Compliance JSON empty | Likely schema path mismatch, check `layer2_enrichment_v2.schema.json` exists at expected path |
| No GPU for resolution quality | Skip RQ labeling, document gap, recommend running on GPU machine |
| Schema version mismatch | Flag as `schema_drift` defect, continue audit with current schema version |
| Backfill >30 min estimated | Generate offline shell script instead of running synchronously |
| Source doc missing | STOP Phase 0, report missing file, cannot extract paper expectations |
| Sample selection fails | Check stratification axes match available metadata fields, fall back to random sampling |

## Recommendation & Approval Workflow

The agent follows a **document -> recommend -> approve -> implement** pattern:

### Auto-Implemented (No Approval Needed)

| Action | Phase |
|--------|-------|
| Read-only validation and analysis | 0-7 |
| TodoWrite task tracking | All |
| Results directory creation | 0 |
| JSON artifact generation | 1-7 |
| Report generation | 7 |

### Approval Required

| Action | Phase | Rationale |
|--------|-------|-----------|
| Source doc edits | 7 | Modifies documentation |
| Logic fixes (auto-fix batch) | 8 | Modifies metadata JSON |
| Fix script generation | 8 | Creates executable code |
| Data gap backfill execution | 9 | Runs enrichment pipelines, modifies metadata |
| Offline script generation | 9 | Creates executable for user to run later |

### Recommendation Format

After Phase 7, present recommendations in this format:

```markdown
## Audit Recommendations: {dataset}

### R1: [fix_category] - [Brief Description]
**Priority**: Critical/High/Medium/Low
**Defect IDs**: D01, D02, ...
**Affected**: {N} samples ({X}%)
**Fix Tier**: auto-fix / semi-auto / manual
**Action**: {specific action to take}
**Rollback**: {how to undo if needed}
```

## Quality Scoring

| Rating | Criteria |
|--------|----------|
| **Complete** | All phases run (0-7+), defect catalog produced, audit report filled, source doc updated, defects <5% of fields |
| **Partial** | Prescreening + compliance done (0-3), defect catalog produced, visual inspection / comparison skipped |
| **Minimal** | Prescreening only (0-2), pass/fail rate reported, no deep analysis |

## Output Artifacts

Each audit run produces these files in `scripts/audit/results/{dataset}/`:

| File | Phase | Description |
|------|-------|-------------|
| `paper_ground_truth.json` | 1 | Expected values from source documentation |
| `automated_screening.json` | 2 | Prescreening pass/fail per field |
| `compliance.json` | 3 | Schema compliance analysis |
| `sample_set.json` | 5 | Stratified audit sample selection |
| `comparison_report.json` | 6 | Multi-source field comparison |
| `defect_catalog.json` | 7 | All defects with taxonomy classification |
| `audit_report.md` | 7 | Human-readable audit report |

## Defect Taxonomy Reference

### Original 6 Types (from DIQA-5000 audit)

| Type | Description | Typical Root Cause |
|------|-------------|-------------------|
| `wrong_value` | Value exists but is factually incorrect | Model mislabel, stale heuristic |
| `missing_data` | Required field is absent (null/missing key) | Parser gap, script bug |
| `wrong_format` | Value present but wrong type or structure | Type coercion error |
| `wrong_enum` | Value not in allowed enum set | Unmapped label, typo |
| `inconsistent` | Cross-field contradiction | Pipeline ordering, partial update |
| `not_populated` | Optional field not populated (coverage gap) | Feature not yet implemented |

### New 6 Types (consensus-derived)

| Type | Description | Typical Root Cause |
|------|-------------|-------------------|
| `low_confidence` | Valid format but confidence < 0.3 | Poor model performance on this domain |
| `schema_drift` | Valid in old schema version, invalid in current | Schema evolution without migration |
| `version_mismatch` | Schema version in metadata doesn't match expected | Stale metadata from older pipeline run |
| `outdated_value` | Stale enrichment that needs re-running | Pipeline updated but metadata not refreshed |
| `conflicting_sources` | 2+ enrichment sources disagree on the same field | Different models/methods produce different results |
| `schema_gap` | Field that SHOULD exist per source data but isn't in schema | Schema incomplete for this dataset's features |

## Use Cases

**Primary**: Deep audit of any dataset's Layer 2 metadata enrichment quality

**Recommended for**:
- New dataset onboarding validation (after `annotate_base_metadata.py` + enrichment)
- Pre-training data quality assurance (verify labels before ML training)
- Post-pipeline-update regression testing (re-audit after script changes)
- Cross-dataset defect extrapolation (findings from one audit inform others)
- Data gap identification and remediation planning

**Scope options**:
- `prescreening_only`: Quick health check (Phases 0-2, ~5 min)
- `compliance_only`: Schema validation (Phases 0-3, ~10 min)
- `full`: Complete deep audit (Phases 0-7, ~30-60 min)
- `full` + `fix_defects=true`: Audit with remediation (Phases 0-9, variable)
