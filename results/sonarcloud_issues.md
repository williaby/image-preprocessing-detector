# SonarCloud Issues Report

**Project**: `williaby_image-preprocessing-detector`
**Fetched**: 2026-02-13T11:05:34.571246+00:00
**Total Issues**: 932 (of 932 reported)
**Total Effort**: 7525 minutes (125.4 hours)

## Issues by Severity

| Severity | Count | Effort (min) |
|----------|-------|-------------|
| BLOCKER | 8 | 25 |
| CRITICAL | 278 | 4652 |
| MAJOR | 492 | 2178 |
| MINOR | 137 | 670 |
| INFO | 17 | 0 |

## Issues by Type

| Type | Count |
|------|-------|
| CODE_SMELL | 751 |
| BUG | 165 |
| VULNERABILITY | 16 |

## Top 30 Rules Triggered

| Rule | Count | Description (from first occurrence) |
|------|-------|-------------------------------------|
| `python:S3776` | 224 | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allo |
| `python:S1244` | 156 | Do not perform equality checks with floating point values. |
| `python:S1481` | 116 | Replace the unused local variable "poly_score" with "_". |
| `shelldre:S7688` | 77 | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and m |
| `shelldre:S7682` | 58 | Add an explicit return statement at the end of the function. |
| `python:S1192` | 50 | Define a constant instead of duplicating this literal "=== Processing complete = |
| `python:S6711` | 49 | Use a "numpy.random.Generator" here instead of this legacy function. |
| `python:S125` | 30 | Remove this commented out code. |
| `python:S1172` | 28 | Remove the unused function parameter "config". |
| `python:S108` | 18 | Either remove or fill this block of code. |
| `python:S1135` | 17 | Complete the task associated to this "TODO" comment. |
| `shelldre:S7679` | 16 | Assign this positional parameter to a local variable. |
| `shelldre:S7677` | 12 | Redirect this error message to stderr (>&2). |
| `githubactions:S8234` | 12 | Replace "read-all" with specific permissions (e.g., "contents: read"). |
| `python:S3358` | 7 | Extract this nested conditional expression into an independent statement. |
| `python:S7494` | 6 | Replace set constructor call with a set comprehension. |
| `pythonbugs:S2259` | 5 | Fix this attribute access on a value that can be 'None'. |
| `python:S1871` | 4 | Either merge this branch with the identical one on line "3687" or change one of  |
| `shelldre:S1192` | 4 | Define a constant instead of using the literal '================================ |
| `python:S8409` | 4 | Remove this redundant "response_model" parameter; it duplicates the return type  |
| `python:S7493` | 3 | Use an asynchronous file API instead of synchronous open() in this async functio |
| `python:S107` | 3 | Function "_train_one_epoch" has 15 parameters, which is greater than the 13 auth |
| `python:S7500` | 3 | Replace this comprehension with passing the iterable to the dict constructor cal |
| `python:S5727` | 3 | Remove this identity check; it will always be False. |
| `python:S1542` | 3 | Rename function "TestOneInput" to match the regular expression ^[a-z_][a-z0-9_]* |
| `python:S6709` | 2 | Provide a seed for this random generator. |
| `python:S5886` | 2 | Remove this yield statement or annotate function "reset_caches" with "typing.Gen |
| `python:S8410` | 2 | Use "Annotated" type hints for FastAPI dependency injection |
| `python:S5713` | 2 | Remove this redundant Exception class; it derives from another which is already  |
| `python:S7504` | 2 | Remove this unnecessary `list()` call on an already iterable object. |

## Issues by Directory

| Directory | Count |
|-----------|-------|
| `tests/unit` | 280 |
| `src/image_preprocessing_detector` | 149 |
| `scripts/annotate_base_metadata.py` | 34 |
| `scripts/extract_workstream_loc.sh` | 31 |
| `scripts/audit` | 28 |
| `tests/integration` | 23 |
| `scripts/gcs_helpers.sh` | 20 |
| `scripts/modal_helpers.sh` | 20 |
| `deployment/scripts` | 18 |
| `scripts/validate_architecture_links.sh` | 18 |
| `.github/workflows` | 14 |
| `scripts/test_arena_local.py` | 13 |
| `scripts/auth_gcs.sh` | 12 |
| `tests/e2e` | 9 |
| `scripts/analyze_soft_labels.py` | 9 |
| `scripts/setup_fonts.sh` | 9 |
| `scripts/enrich_language_from_gt.py` | 8 |
| `scripts/validate_base_dataset_v3.py` | 8 |
| `tests/fixtures` | 8 |
| `deployment/deploy-docling.sh` | 7 |

## Top 50 Files by Issue Count

| File | Count |
|------|-------|
| `scripts/annotate_base_metadata.py` | 34 |
| `scripts/extract_workstream_loc.sh` | 31 |
| `scripts/gcs_helpers.sh` | 20 |
| `scripts/modal_helpers.sh` | 20 |
| `scripts/validate_architecture_links.sh` | 18 |
| `tests/unit/drift/test_distribution.py` | 18 |
| `deployment/scripts/process-dataset-gcs.sh` | 13 |
| `tests/unit/test_resolution_quality.py` | 13 |
| `scripts/test_arena_local.py` | 13 |
| `tests/unit/detection/test_iqa_ml.py` | 13 |
| `tests/unit/scripts/test_validate_dqs_correlation.py` | 12 |
| `scripts/auth_gcs.sh` | 12 |
| `tests/unit/annotation/test_cache.py` | 11 |
| `tests/unit/annotation/test_quality_parsers.py` | 11 |
| `tests/unit/test_deskew_pipeline.py` | 11 |
| `tests/unit/labeling/arena/test_modal_client.py` | 11 |
| `tests/unit/labeling/domain/test_openrouter_client.py` | 10 |
| `tests/unit/labeling/arena/test_schemas.py` | 10 |
| `tests/unit/utils/test_tensor_cache.py` | 10 |
| `tests/unit/scripts/test_create_symlinks.py` | 10 |
| `src/image_preprocessing_detector/drift/performance.py` | 10 |
| `scripts/analyze_soft_labels.py` | 9 |
| `scripts/setup_fonts.sh` | 9 |
| `scripts/enrich_language_from_gt.py` | 8 |
| `scripts/validate_base_dataset_v3.py` | 8 |
| `tests/unit/labeling/arena/test_modal_backend.py` | 8 |
| `deployment/deploy-docling.sh` | 7 |
| `deployment/setup-gcs-processing.sh` | 7 |
| `modal/train_skew_estimator.py` | 7 |
| `scripts/upload_datasets_to_gcs.sh` | 7 |
| `tests/unit/annotation/test_siglip.py` | 7 |
| `tests/unit/annotation/test_validators.py` | 7 |
| `tests/unit/labeling/domain/test_classifier.py` | 7 |
| `tests/unit/orchestration/test_device_orchestrator.py` | 7 |
| `tests/integration/test_device_priority.py` | 7 |
| `scripts/validate-workflows.sh` | 7 |
| `tests/unit/detection/test_code_detector.py` | 6 |
| `scripts/audit/compute_scorecard.py` | 6 |
| `scripts/generate_orientation_dataset.py` | 6 |
| `src/image_preprocessing_detector/synthetic/generator.py` | 6 |
| `tests/unit/test_schema_migration.py` | 6 |
| `tests/integration/logging/test_logging_integration.py` | 6 |
| `modal/train_siglip2_iqa_v2.py` | 5 |
| `scripts/audit/assemble_diqa_comparison.py` | 5 |
| `scripts/audit/audit_schema_compliance.py` | 5 |
| `scripts/convert_datasets_to_images.py` | 5 |
| `scripts/enrich_metadata_from_llm.py` | 5 |
| `src/image_preprocessing_detector/annotation/schemas/validators.py` | 5 |
| `src/image_preprocessing_detector/synthetic/cli.py` | 5 |
| `tests/unit/annotation/test_config.py` | 5 |

## All Issues (Grouped by File)

### `scripts/annotate_base_metadata.py` (34 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 185 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.jpg" 13 times. | 26min |
| 235 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.png" 14 times. | 28min |
| 598 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 610 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 1310 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 40 to the 15 allowed. | 30min |
| 1591 | MINOR | `python:S1481` | Remove the unused local variable "json_path". | 5min |
| 1690 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |
| 1727 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "train.json" 5 times. | 10min |
| 1838 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 2002 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 27 to the 15 allowed. | 17min |
| 2060 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 39 to the 15 allowed. | 29min |
| 2643 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 26 to the 15 allowed. | 16min |
| 2780 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 35 to the 15 allowed. | 25min |
| 3078 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 3139 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |
| 3506 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 44 to the 15 allowed. | 34min |
| 3596 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 25 to the 15 allowed. | 15min |
| 3662 | MINOR | `python:S1481` | Remove the unused local variable "remainder". | 5min |
| 3698 | MAJOR | `python:S1871` | Either merge this branch with the identical one on line "3687" or change one of the implementations. | 10min |
| 3701 | MAJOR | `python:S1871` | Either merge this branch with the identical one on line "3695" or change one of the implementations. | 10min |
| 3729 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |
| 3900 | MAJOR | `python:S1172` | Remove the unused function parameter "config". | 5min |
| 3939 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 45 to the 15 allowed. | 35min |
| 3944 | MAJOR | `python:S1172` | Remove the unused function parameter "git_sha". | 5min |
| 3970 | MINOR | `python:S1481` | Replace the unused local variable "tier_description" with "_". | 5min |
| 4112 | MINOR | `python:S1481` | Remove the unused local variable "has_ground_truth_language". | 5min |
| 4115 | MINOR | `python:S1481` | Remove the unused local variable "has_ground_truth_script". | 5min |
| 4283 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |
| 4416 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 68 to the 15 allowed. | 58min |
| 4627 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |
| 4699 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 32 to the 15 allowed. | 22min |
| 4768 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 50 to the 15 allowed. | 40min |
| 4872 | MAJOR | `python:S3358` | Extract this nested conditional expression into an independent statement. | 5min |
| 4900 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "samples.parquet" 3 times. | 6min |

### `scripts/extract_workstream_loc.sh` (31 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 65 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 69 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 73 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 80 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 84 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 129 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 130 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 147 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 172 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 219 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 231 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 238 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 248 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 265 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 266 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 290 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 293 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 293 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 311 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 320 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 328 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 341 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 341 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 352 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 355 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 369 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 370 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 373 | MINOR | `shelldre:S1192` | Define a constant instead of using the literal '{print $1}' 4 times. | 4min |
| 394 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 397 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 397 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `scripts/gcs_helpers.sh` (20 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 20 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 21 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 24 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 25 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 28 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 29 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 29 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 33 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 45 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 56 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 59 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 83 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 104 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 116 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 129 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 133 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 145 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 151 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 167 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 188 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |

### `scripts/modal_helpers.sh` (20 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 19 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 21 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 28 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 30 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 31 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 38 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 41 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 42 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 47 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 48 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 58 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 59 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 66 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 72 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 83 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 89 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 96 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 103 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 115 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 121 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |

### `scripts/validate_architecture_links.sh` (18 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 32 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 70 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 70 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 70 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 74 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 74 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 85 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 95 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 104 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 106 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 117 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 119 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 131 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 136 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 142 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 149 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 155 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 166 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `tests/unit/drift/test_distribution.py` (18 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 66 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 67 | MINOR | `python:S1481` | Replace the unused local variable "bin_edges" with "_". | 5min |
| 78 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 79 | MINOR | `python:S1481` | Replace the unused local variable "bin_edges" with "_". | 5min |
| 100 | MINOR | `python:S1481` | Replace the unused local variable "histogram" with "_". | 5min |
| 108 | MINOR | `python:S1481` | Replace the unused local variable "bin_edges" with "_". | 5min |
| 116 | MINOR | `python:S1481` | Replace the unused local variable "bin_edges" with "_". | 5min |
| 124 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 236 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 237 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 331 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 332 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 438 | MINOR | `python:S1481` | Replace the unused local variable "bin_edges" with "_". | 5min |
| 971 | MINOR | `python:S1481` | Replace the unused local variable "bin_edges" with "_". | 5min |
| 984 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 985 | MINOR | `python:S1481` | Replace the unused local variable "bin_edges" with "_". | 5min |
| 994 | MINOR | `python:S1481` | Replace the unused loop index "i" with "_". | 5min |
| 995 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `deployment/scripts/process-dataset-gcs.sh` (13 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 58 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 58 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 59 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 59 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 60 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 60 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 63 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 72 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 78 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 95 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 137 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 150 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 159 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |

### `tests/unit/test_resolution_quality.py` (13 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 45 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 46 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 50 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 161 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 233 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 236 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 393 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 394 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 395 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 396 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 474 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 630 | MINOR | `python:S1481` | Replace the unused local variable "heights" with "_". | 5min |
| 638 | MINOR | `python:S1481` | Replace the unused local variable "heights" with "_". | 5min |

### `scripts/test_arena_local.py` (13 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 105 | MINOR | `python:S1481` | Replace the unused loop index "i" with "_". | 5min |
| 110 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 111 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 112 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 124 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 162 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 335 | MINOR | `python:S1481` | Remove the unused local variable "backend". | 5min |
| 367 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 383 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 448 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 459 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 562 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 692 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `tests/unit/detection/test_iqa_ml.py` (13 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 587 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 653 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 654 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 655 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 656 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 657 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 714 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 744 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 774 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 804 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 835 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 836 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 838 | MAJOR | `python:S125` | Remove this commented out code. | 5min |

### `tests/unit/scripts/test_validate_dqs_correlation.py` (12 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 35 | MINOR | `python:S1481` | Replace the unused local variable "p_value" with "_". | 5min |
| 44 | MINOR | `python:S1481` | Replace the unused local variable "p_value" with "_". | 5min |
| 53 | MINOR | `python:S1481` | Replace the unused local variable "p_value" with "_". | 5min |
| 63 | MINOR | `python:S1481` | Replace the unused local variable "correlation" with "_". | 5min |
| 71 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 73 | MINOR | `python:S1481` | Replace the unused local variable "p_value" with "_". | 5min |
| 80 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 82 | MINOR | `python:S1481` | Replace the unused local variable "p_value" with "_". | 5min |
| 124 | MINOR | `python:S1481` | Remove the unused local variable "accuracy_simple". | 5min |
| 125 | MINOR | `python:S1481` | Remove the unused local variable "accuracy_complex". | 5min |
| 142 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 143 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `scripts/auth_gcs.sh` (12 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 26 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 27 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 30 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 31 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 34 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 35 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 35 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 39 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 40 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 47 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 52 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 144 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `tests/unit/annotation/test_cache.py` (11 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 32 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 179 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 191 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 254 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 257 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 262 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 265 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 283 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 284 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 354 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 452 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/annotation/test_quality_parsers.py` (11 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 114 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 115 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 116 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 117 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 125 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 126 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 127 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 128 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 248 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 250 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 251 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/test_deskew_pipeline.py` (11 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 34 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 35 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 36 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 37 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 47 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 48 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 71 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 74 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 278 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 302 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 322 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/labeling/arena/test_modal_client.py` (11 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 29 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 45 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 53 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 62 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 67 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 79 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 96 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 128 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 149 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 303 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 324 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `tests/unit/labeling/domain/test_openrouter_client.py` (10 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 35 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 81 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 103 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 177 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 181 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 185 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 189 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 190 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 194 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 277 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/labeling/arena/test_schemas.py` (10 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 36 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 37 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 38 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 43 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 44 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 65 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 66 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 67 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 69 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 84 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/utils/test_tensor_cache.py` (10 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 31 | MAJOR | `python:S5886` | Remove this yield statement or annotate function "reset_caches" with "typing.Generator" or one of it | 5min |
| 41 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 46 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 51 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 56 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 61 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 66 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 84 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 85 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 86 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/scripts/test_create_symlinks.py` (10 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 105 | MINOR | `python:S1481` | Replace the unused local variable "project_root" with "_". | 5min |
| 105 | MINOR | `python:S1481` | Replace the unused local variable "nfs_root" with "_". | 5min |
| 153 | MINOR | `python:S1481` | Replace the unused local variable "message" with "_". | 5min |
| 175 | MINOR | `python:S1481` | Replace the unused local variable "message" with "_". | 5min |
| 215 | MINOR | `python:S1481` | Replace the unused local variable "message" with "_". | 5min |
| 324 | MINOR | `python:S1481` | Replace the unused local variable "project_root" with "_". | 5min |
| 367 | MINOR | `python:S1481` | Replace the unused local variable "message" with "_". | 5min |
| 377 | MINOR | `python:S1481` | Replace the unused local variable "project_root" with "_". | 5min |
| 383 | MINOR | `python:S1481` | Replace the unused local variable "message" with "_". | 5min |
| 397 | MINOR | `python:S1481` | Replace the unused local variable "message" with "_". | 5min |

### `src/image_preprocessing_detector/drift/performance.py` (10 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 311 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "evaluation_history.json" 3 times. | 6min |
| 329 | MINOR | `python:S5713` | Remove this redundant Exception class; it derives from another which is already caught. | 1min |
| 584 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 585 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 586 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 587 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 588 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 589 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 590 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 949 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `scripts/analyze_soft_labels.py` (9 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 491 | MINOR | `python:S1481` | Remove the unused local variable "hard_count". | 5min |
| 567 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 669 | MINOR | `python:S1481` | Remove the unused local variable "capped_count". | 5min |
| 678 | MINOR | `python:S1481` | Replace the unused loop index "sample_raw" with "_". | 5min |
| 722 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |
| 784 | MAJOR | `python:S3358` | Extract this nested conditional expression into an independent statement. | 5min |
| 807 | MINOR | `python:S1481` | Remove the unused local variable "all_det_confs". | 5min |
| 809 | MINOR | `python:S1481` | Remove the unused local variable "enrichment". | 5min |
| 887 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |

### `scripts/setup_fonts.sh` (9 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 26 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 35 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 64 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 126 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 130 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 144 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 154 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 214 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 224 | MINOR | `shelldre:S1192` | Define a constant instead of using the literal '==============================================' 4 ti | 4min |

### `scripts/enrich_language_from_gt.py` (8 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 492 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "*.json" 3 times. | 6min |
| 607 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 68 to the 15 allowed. | 58min |
| 678 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 709 | MINOR | `python:S1481` | Remove the unused local variable "e". | 5min |
| 716 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 825 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 999 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 52 to the 15 allowed. | 42min |
| 1126 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `scripts/validate_base_dataset_v3.py` (8 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 80 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 98 | MINOR | `python:S7494` | Replace set constructor call with a set comprehension. | 5min |
| 99 | MINOR | `python:S7494` | Replace set constructor call with a set comprehension. | 5min |
| 104 | MINOR | `python:S1481` | Replace the unused loop index "stem" with "_". | 5min |
| 166 | MINOR | `python:S1481` | Remove the unused local variable "quality_counts". | 5min |
| 174 | MINOR | `python:S1481` | Remove the unused local variable "resolution". | 5min |
| 208 | MINOR | `python:S7500` | Replace this comprehension with passing the iterable to the dict constructor call | 5min |
| 278 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `tests/unit/labeling/arena/test_modal_backend.py` (8 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 92 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 100 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 120 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 137 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 188 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 189 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 201 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 202 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `deployment/deploy-docling.sh` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 24 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 24 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 25 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 25 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 26 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 26 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 26 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |

### `deployment/setup-gcs-processing.sh` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 26 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 26 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 27 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 27 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 28 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 28 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 28 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |

### `modal/train_skew_estimator.py` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 167 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "labels.json" 4 times. | 8min |
| 331 | MAJOR | `python:S1172` | Remove the unused function parameter "run_id". | 5min |
| 396 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 37 to the 15 allowed. | 27min |
| 902 | MAJOR | `python:S1172` | Remove the unused function parameter "bin_centers". | 5min |
| 903 | MAJOR | `python:S1172` | Remove the unused function parameter "bin_half_widths". | 5min |
| 907 | MAJOR | `python:S1172` | Remove the unused function parameter "run_id". | 5min |
| 1172 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `scripts/upload_datasets_to_gcs.sh` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 32 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 33 | MAJOR | `shelldre:S7679` | Assign this positional parameter to a local variable. | 5min |
| 71 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 85 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 172 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 253 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 285 | MINOR | `shelldre:S1192` | Define a constant instead of using the literal '==========================================' 10 times | 4min |

### `tests/unit/annotation/test_siglip.py` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 91 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 96 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 155 | MINOR | `python:S1481` | Remove the unused local variable "result". | 5min |
| 271 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 303 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 304 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 605 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/annotation/test_validators.py` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 99 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 104 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 109 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 133 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 245 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 250 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 255 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/labeling/domain/test_classifier.py` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 76 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 105 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 150 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 160 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 177 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 201 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 216 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/orchestration/test_device_orchestrator.py` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 322 | MINOR | `python:S1481` | Replace the unused loop index "i" with "_". | 5min |
| 350 | MINOR | `python:S1481` | Replace the unused loop index "page_idx" with "_". | 5min |
| 430 | MINOR | `python:S1481` | Replace the unused loop index "i" with "_". | 5min |
| 489 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 493 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 511 | MINOR | `python:S1481` | Replace the unused loop index "i" with "_". | 5min |
| 512 | MINOR | `python:S1481` | Remove the unused local variable "choice". | 5min |

### `tests/integration/test_device_priority.py` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 288 | MINOR | `python:S1481` | Remove the unused local variable "original_providers". | 5min |
| 314 | MAJOR | `pythonbugs:S2259` | Fix this attribute access on a value that can be 'None'. | 10min |
| 423 | MINOR | `python:S1481` | Replace the unused local variable "escalation_reason" with "_". | 5min |
| 423 | MINOR | `python:S1481` | Replace the unused local variable "teacher_scores" with "_". | 5min |
| 489 | MAJOR | `pythonbugs:S2259` | Fix this attribute access on a value that can be 'None'. | 10min |
| 509 | MAJOR | `pythonbugs:S2259` | Fix this attribute access on a value that can be 'None'. | 10min |
| 525 | MINOR | `python:S1481` | Remove the unused local variable "max_latency". | 5min |

### `scripts/validate-workflows.sh` (7 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 95 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 154 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 164 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 172 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 172 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 174 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 187 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `tests/unit/detection/test_code_detector.py` (6 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 56 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 58 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 61 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 62 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 64 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 66 | MAJOR | `python:S125` | Remove this commented out code. | 5min |

### `scripts/audit/compute_scorecard.py` (6 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 115 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |
| 171 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 30 to the 15 allowed. | 20min |
| 318 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 42 to the 15 allowed. | 32min |
| 372 | MINOR | `python:S7494` | Replace set constructor call with a set comprehension. | 5min |
| 602 | MINOR | `python:S7500` | Replace this comprehension with passing the iterable to the dict constructor call | 5min |
| 744 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |

### `scripts/generate_orientation_dataset.py` (6 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 62 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "documents/doclaynet" 4 times. | 8min |
| 63 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.png" 10 times. | 20min |
| 87 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.*" 3 times. | 6min |
| 95 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.jpg" 4 times. | 8min |
| 202 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |
| 525 | MINOR | `python:S7500` | Replace this comprehension with passing the iterable to the dict constructor call | 5min |

### `src/image_preprocessing_detector/synthetic/generator.py` (6 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 764 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 28 to the 15 allowed. | 18min |
| 913 | MAJOR | `python:S1871` | Either merge this branch with the identical one on line "841" or change one of the implementations. | 10min |
| 959 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 52 to the 15 allowed. | 42min |
| 973 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "Generator not initialized. Call initialize()  | 6min |
| 1246 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 40 to the 15 allowed. | 30min |
| 1420 | MAJOR | `python:S1871` | Either merge this branch with the identical one on line "1351" or change one of the implementations. | 10min |

### `tests/unit/test_schema_migration.py` (6 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 46 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 57 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 128 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 139 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 149 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 211 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/integration/logging/test_logging_integration.py` (6 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 56 | MAJOR | `python:S5886` | Remove this yield statement or annotate function "temp_log_dir" with "typing.Generator" or one of it | 5min |
| 94 | MINOR | `python:S1481` | Remove the unused local variable "error_logger". | 5min |
| 98 | MINOR | `python:S1481` | Remove the unused local variable "outcome_logger". | 5min |
| 357 | MINOR | `python:S1481` | Remove the unused local variable "error". | 5min |
| 415 | MINOR | `python:S1481` | Remove the unused local variable "outcome". | 5min |
| 619 | MINOR | `python:S1481` | Remove the unused local variable "outcome". | 5min |

### `modal/train_siglip2_iqa_v2.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 793 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |
| 940 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 28 to the 15 allowed. | 18min |
| 1195 | MAJOR | `python:S1172` | Remove the unused function parameter "config". | 5min |
| 1270 | MAJOR | `python:S107` | Function "_train_one_epoch" has 15 parameters, which is greater than the 13 authorized. | 20min |
| 2021 | MAJOR | `python:S107` | Function "main" has 14 parameters, which is greater than the 13 authorized. | 20min |

### `scripts/audit/assemble_diqa_comparison.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 377 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 35 to the 15 allowed. | 25min |
| 392 | MINOR | `python:S1481` | Remove the unused local variable "total_samples". | 5min |
| 457 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |
| 532 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 26 to the 15 allowed. | 16min |
| 658 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |

### `scripts/audit/audit_schema_compliance.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 518 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |
| 720 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "llm_scores.predicted_mos" 4 times. | 8min |
| 777 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |
| 853 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 1042 | MAJOR | `python:S1854` | Remove this assignment to local variable 'schema_path'; the value is never used. | 1min |

### `scripts/convert_datasets_to_images.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 70 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "PyMuPDF (fitz) not installed. Run: pip instal | 6min |
| 76 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "*.pdf" 3 times. | 6min |
| 136 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 32 to the 15 allowed. | 22min |
| 238 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 24 to the 15 allowed. | 14min |
| 354 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 24 to the 15 allowed. | 14min |

### `scripts/enrich_metadata_from_llm.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 215 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 411 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |
| 482 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 800 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |
| 951 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `src/image_preprocessing_detector/annotation/schemas/validators.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 210 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 37 to the 15 allowed. | 27min |
| 314 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 375 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 172 to the 15 allowed. | 2h42min |
| 650 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |
| 734 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 64 to the 15 allowed. | 54min |

### `src/image_preprocessing_detector/synthetic/cli.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 50 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 193 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 28 to the 15 allowed. | 18min |
| 194 | MAJOR | `python:S107` | Function "generate" has 16 parameters, which is greater than the 13 authorized. | 20min |
| 355 | MINOR | `python:S1481` | Remove the unused local variable "generated". | 5min |
| 404 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |

### `tests/unit/annotation/test_config.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 43 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 56 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 105 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 182 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 258 | MINOR | `python:S7492` | Unpack this comprehension expression | 5min |

### `tests/unit/annotation/test_rvl_cdip_parser.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 260 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 261 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 267 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 324 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 326 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/annotation/test_scanner.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 155 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 158 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 161 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 175 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 176 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/annotation/test_schemas.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 131 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 132 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 133 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 169 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 374 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/labeling/domain/test_config.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 31 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 68 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 69 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 95 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 105 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `scripts/run_model_benchmark.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 569 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 30 to the 15 allowed. | 20min |
| 897 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 28 to the 15 allowed. | 18min |
| 1033 | MINOR | `python:S1481` | Remove the unused local variable "cer_np". | 5min |
| 1034 | MINOR | `python:S1481` | Remove the unused local variable "wer_np". | 5min |
| 1095 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `tests/unit/labeling/arena/test_metrics.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 62 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 151 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 152 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 153 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 154 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `.clusterfuzzlite/build.sh` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 18 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 18 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 18 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 19 | MAJOR | `shelldre:S7677` | Redirect this error message to stderr (>&2). | 5min |
| 85 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `tests/fixtures/phase1_validation/validate_detectors.py` (5 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 38 | MAJOR | `python:S5890` | Replace the type hint "list[dict]" with "Optional[list[dict]]" or don't assign "None" to "prediction | 5min |
| 63 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |
| 160 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 234 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 308 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `deployment/scripts/process_datasets.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 243 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |
| 503 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 24 to the 15 allowed. | 14min |
| 606 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "=== Processing complete ===" 4 times. | 8min |
| 614 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 25 to the 15 allowed. | 15min |

### `scripts/audit/integration_script_template.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 460 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 605 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 24 to the 15 allowed. | 14min |
| 761 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 32 to the 15 allowed. | 22min |
| 1045 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 42 to the 15 allowed. | 32min |

### `scripts/audit_datasets.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 248 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 442 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 32 to the 15 allowed. | 22min |
| 450 | MAJOR | `python:S3358` | Extract this nested conditional expression into an independent statement. | 5min |
| 478 | MAJOR | `python:S3358` | Extract this nested conditional expression into an independent statement. | 5min |

### `scripts/generate_skew_dataset.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 231 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 51 to the 15 allowed. | 41min |
| 613 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 28 to the 15 allowed. | 18min |
| 804 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 33 to the 15 allowed. | 23min |
| 959 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/materialize_reliability_summary.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 422 | MINOR | `python:S1481` | Remove the unused local variable "active_count". | 5min |
| 423 | MINOR | `python:S1481` | Remove the unused local variable "unreliable_count". | 5min |
| 501 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 729 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `src/image_preprocessing_detector/annotation/config/datasets.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 194 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.jpg" 14 times. | 28min |
| 250 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.png" 16 times. | 32min |
| 264 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "images/*.jpg" 3 times. | 6min |
| 829 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `tests/plugins/weak_assertion_detector.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 97 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "Checks truthiness only, not specific value" 6 | 12min |
| 245 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |
| 246 | MAJOR | `python:S1172` | Remove the unused function parameter "exitstatus". | 5min |
| 342 | MAJOR | `python:S1172` | Remove the unused function parameter "exitstatus". | 5min |

### `tests/unit/test_skew_estimator.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 32 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 77 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 80 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 219 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `scripts/build_training_labels.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 350 | MAJOR | `python:S1172` | Remove the unused function parameter "record". | 5min |
| 363 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 484 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "training_labels.parquet" 3 times. | 6min |
| 513 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `tests/unit/workers/test_celery_workers.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 127 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 303 | MINOR | `python:S1481` | Replace the unused local variable "confidences" with "_". | 5min |
| 344 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 400 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `src/image_preprocessing_detector/api/routes/process.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 88 | MINOR | `python:S7503` | Use asynchronous features in this function or remove the `async` keyword. | 5min |
| 88 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 24 to the 15 allowed. | 14min |
| 266 | BLOCKER | `python:S8410` | Use "Annotated" type hints for FastAPI dependency injection | 5min |
| 319 | MAJOR | `python:S7493` | Use an asynchronous file API instead of synchronous tempfile.NamedTemporaryFile() in this async func | 5min |

### `tests/e2e/test_device_priority_e2e.py` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 247 | MINOR | `python:S1481` | Remove the unused local variable "builder". | 5min |
| 397 | MINOR | `python:S1481` | Replace the unused local variable "rationale" with "_". | 5min |
| 424 | MINOR | `python:S1481` | Replace the unused local variable "rationale" with "_". | 5min |
| 450 | MINOR | `python:S1481` | Replace the unused local variable "rationale" with "_". | 5min |

### `scripts/download_docile.sh` (4 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 7 | MAJOR | `shelldre:S7682` | Add an explicit return statement at the end of the function. | 2min |
| 36 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 49 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 87 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `scripts/audit/assemble_comparison.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 712 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 82 to the 15 allowed. | 1h12min |
| 884 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 33 to the 15 allowed. | 23min |
| 1028 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `scripts/backfill_text_quality_confidence.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 297 | MAJOR | `python:S1172` | Remove the unused function parameter "dataset_name". | 5min |
| 364 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |
| 365 | MAJOR | `python:S1172` | Remove the unused function parameter "dataset_name". | 5min |

### `scripts/calculate_text_statistics.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 53 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "*.txt" 3 times. | 6min |
| 222 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 447 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |

### `scripts/convert_sroie_to_extracted.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 47 | MINOR | `python:S1481` | Replace the unused local variable "w" with "_". | 5min |
| 47 | MINOR | `python:S1481` | Replace the unused local variable "h" with "_". | 5min |
| 161 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/enrich_language.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 649 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 45 to the 15 allowed. | 35min |
| 1006 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 38 to the 15 allowed. | 28min |
| 1170 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 36 to the 15 allowed. | 26min |

### `scripts/enrich_mlt19_language.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 194 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 360 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 561 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 33 to the 15 allowed. | 23min |

### `scripts/integrate_diqa_enrichments.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 178 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |
| 891 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 108 to the 15 allowed. | 1h38min |
| 1394 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |

### `scripts/language_escalation.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 60 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "google/gemini-2.5-pro" 4 times. | 8min |
| 350 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "image/jpeg" 3 times. | 6min |
| 581 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 40 to the 15 allowed. | 30min |

### `scripts/process_local_datasets_docling.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 120 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 217 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 28 to the 15 allowed. | 18min |
| 321 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `scripts/standardize_layout_labels.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 281 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |
| 646 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 732 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 27 to the 15 allowed. | 17min |

### `scripts/triage_local_analysis.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 280 | MAJOR | `python:S1172` | Remove the unused function parameter "script_counts". | 5min |
| 412 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 539 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `scripts/update_data_locations.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 19 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "JPG/PNG" 4 times. | 8min |
| 676 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 761 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 55 to the 15 allowed. | 45min |

### `scripts/validate_annotation_output.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 156 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 240 | MAJOR | `python:S1172` | Remove the unused function parameter "dataset_name". | 5min |
| 362 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 39 to the 15 allowed. | 29min |

### `scripts/validate_openlid_mlt19.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 171 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 264 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |
| 360 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |

### `src/image_preprocessing_detector/annotation/config/settings.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 73 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "/mnt/e/image_detection" 3 times. | 6min |
| 75 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "/mnt/e/image_detection/metadata_registry" 3 t | 6min |
| 79 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "/mnt/e/image_detection/metadata_registry/.che | 6min |

### `src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 124 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "im2latex_formulas.lst" 4 times. | 8min |
| 152 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |
| 258 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `src/image_preprocessing_detector/synthetic/fonts.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 441 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "Failed to load font %s: %s" 3 times. | 6min |
| 633 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |
| 768 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `src/image_preprocessing_detector/synthetic/validation.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 39 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |
| 381 | MAJOR | `python:S1172` | Remove the unused function parameter "samples". | 5min |
| 384 | MAJOR | `python:S1172` | Remove the unused function parameter "thresh". | 5min |

### `tests/e2e/annotation/test_error_paths_e2e.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 33 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 131 | MINOR | `python:S1481` | Remove the unused local variable "failures". | 5min |
| 240 | MINOR | `python:S1481` | Remove the unused local variable "result". | 5min |

### `tests/unit/annotation/test_checkpointing.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 167 | MINOR | `python:S1481` | Remove the unused local variable "manager". | 5min |
| 252 | MINOR | `python:S1481` | Remove the unused local variable "original_content". | 5min |
| 468 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/annotation/test_pipeline.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 115 | MINOR | `python:S1481` | Remove the unused local variable "manager". | 5min |
| 240 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 407 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/annotation/test_storage.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 139 | MINOR | `python:S1481` | Remove the unused local variable "writer". | 5min |
| 403 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 404 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/test_schema_stream1.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 76 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 189 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 244 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `modal/train_siglip2_iqa.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 173 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 163 to the 15 allowed. | 2h33min |
| 934 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "siglip2_iqa_best.pt" 6 times. | 12min |
| 951 | MAJOR | `python:S6973` | Add the missing hyperparameter lr for this PyTorch optimizer. | 5min |

### `scripts/monitor_annotation.sh` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 19 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 39 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 49 | MINOR | `shelldre:S1192` | Define a constant instead of using the literal '==================================================== | 4min |

### `src/image_preprocessing_detector/labeling/arena/inference/local.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 93 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "model.safetensors" 3 times. | 6min |
| 95 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "model.onnx" 3 times. | 6min |
| 249 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "Model not loaded" 3 times. | 6min |

### `tools/add_front_matter.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 16 | MAJOR | `python:S1172` | Remove the unused function parameter "content". | 5min |
| 16 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 154 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `tools/generate_diagram_svgs.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 48 | CRITICAL | `python:S4423` | Use a stronger protocol, or upgrade to Python 3.10+ which uses secure defaults. | 2min |
| 89 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "*.svg" 3 times. | 6min |
| 160 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |

### `src/image_preprocessing_detector/metrics/calibration.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 326 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 327 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 328 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `tests/unit/scripts/test_download_table_datasets.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 320 | MINOR | `python:S1481` | Remove the unused local variable "mock_download". | 5min |
| 322 | MINOR | `python:S1481` | Remove the unused local variable "result". | 5min |
| 349 | MINOR | `python:S1481` | Remove the unused local variable "result". | 5min |

### `tests/unit/scripts/test_extract_test_fixtures.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 232 | MINOR | `python:S1481` | Replace the unused local variable "sampled" with "_". | 5min |
| 251 | MINOR | `python:S1481` | Replace the unused local variable "total" with "_". | 5min |
| 361 | MINOR | `python:S1481` | Remove the unused local variable "result". | 5min |

### `tests/unit/detection/test_orientation_detector.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 82 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 165 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 326 | MINOR | `python:S1481` | Replace the unused local variable "was_corrected" with "_". | 5min |

### `src/image_preprocessing_detector/api/routes/batch.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 92 | MAJOR | `python:S7493` | Use an asynchronous file API instead of synchronous tempfile.NamedTemporaryFile() in this async func | 5min |
| 171 | BLOCKER | `python:S8410` | Use "Annotated" type hints for FastAPI dependency injection | 5min |
| 291 | BLOCKER | `python:S8409` | Remove this redundant "response_model" parameter; it duplicates the return type annotation. | 2min |

### `src/image_preprocessing_detector/api/routes/health.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 76 | BLOCKER | `python:S8409` | Remove this redundant "response_model" parameter; it duplicates the return type annotation. | 2min |
| 100 | BLOCKER | `python:S8409` | Remove this redundant "response_model" parameter; it duplicates the return type annotation. | 2min |
| 190 | BLOCKER | `python:S8409` | Remove this redundant "response_model" parameter; it duplicates the return type annotation. | 2min |

### `src/image_preprocessing_detector/drift/__init__.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 441 | MAJOR | `python:S6709` | Provide a seed for this random generator. | 5min |
| 614 | MINOR | `python:S5713` | Remove this redundant Exception class; it derives from another which is already caught. | 1min |
| 695 | MINOR | `python:S7504` | Remove this unnecessary `list()` call on an already iterable object. | 5min |

### `tests/unit/logging/test_outcome_logging.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 295 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 410 | MINOR | `python:S1481` | Remove the unused local variable "result". | 5min |
| 411 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |

### `tests/integration/test_classical_ml_integration.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 501 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 637 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 907 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `src/image_preprocessing_detector/ingestion/document_processor.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 88 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 103 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 226 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `benchmarks/tasks/iqa.py` (3 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 139 | MINOR | `python:S1481` | Remove the unused local variable "correction_metadata". | 5min |
| 237 | MINOR | `python:S1481` | Remove the unused local variable "denoise_metadata". | 5min |
| 294 | MINOR | `python:S1481` | Remove the unused local variable "enhance_metadata". | 5min |

### `scripts/aggregate_layer2_metadata.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 218 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 81 to the 15 allowed. | 1h11min |
| 477 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |

### `scripts/audit_layout_labels.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 152 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 25 to the 15 allowed. | 15min |
| 302 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |

### `scripts/convert_cocotext_parquet.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 133 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |
| 177 | MINOR | `python:S1481` | Replace the unused local variable "dataset_name" with "_". | 5min |

### `scripts/convert_hiertext_to_extracted.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 72 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 50 to the 15 allowed. | 40min |
| 191 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `scripts/convert_mlt19_to_extracted.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 186 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |
| 189 | MINOR | `python:S1481` | Remove the unused local variable "img_dir". | 5min |

### `scripts/convert_parquet_to_images.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 95 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 273 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/generate_base_dataset_v3.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 181 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |
| 483 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 30 to the 15 allowed. | 20min |

### `scripts/migrate_layer2_schema_to_full.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 411 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |
| 573 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `scripts/split_dataset_catalog.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 253 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |
| 396 | MINOR | `python:S7494` | Replace set constructor call with a set comprehension. | 5min |

### `scripts/triage_text_analysis.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 252 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |
| 307 | MAJOR | `python:S3358` | Extract this nested conditional expression into an independent statement. | 5min |

### `scripts/validate_language_detection.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 151 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 35 to the 15 allowed. | 25min |
| 217 | MINOR | `python:S1481` | Remove the unused local variable "easyocr_reader". | 5min |

### `src/image_preprocessing_detector/annotation/__init__.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 63 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal ".enrichment" 9 times. | 18min |
| 72 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal ".workflow.orchestrator" 4 times. | 8min |

### `src/image_preprocessing_detector/annotation/cli.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 126 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |
| 385 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `src/image_preprocessing_detector/annotation/enrichment/providers/language_detector.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 140 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 91 to the 15 allowed. | 1h21min |
| 348 | MAJOR | `python:S1172` | Remove the unused function parameter "image_path". | 5min |

### `src/image_preprocessing_detector/annotation/parsers/document/rvl_cdip.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 191 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 25 to the 15 allowed. | 15min |
| 272 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 27 to the 15 allowed. | 17min |

### `src/image_preprocessing_detector/annotation/parsers/generic.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 159 | MAJOR | `python:S1172` | Remove the unused function parameter "image_path". | 5min |
| 160 | MAJOR | `python:S1172` | Remove the unused function parameter "config". | 5min |

### `src/image_preprocessing_detector/annotation/parsers/handwriting/muharaf.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 136 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 26 to the 15 allowed. | 16min |
| 139 | MAJOR | `python:S1172` | Remove the unused function parameter "image_path". | 5min |

### `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_db2.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 66 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 30 to the 15 allowed. | 20min |
| 113 | MINOR | `python:S1481` | Replace the unused local variable "field_id" with "_". | 5min |

### `src/image_preprocessing_detector/annotation/parsers/layout/doclaynet.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 144 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |
| 167 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "train.json" 3 times. | 6min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/cocotext.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 110 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 208 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/hiertext.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 117 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |
| 260 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 36 to the 15 allowed. | 26min |

### `src/image_preprocessing_detector/annotation/parsers/quality/diqa.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 86 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 44 to the 15 allowed. | 34min |
| 138 | MAJOR | `python:S3358` | Extract this nested conditional expression into an independent statement. | 5min |

### `src/image_preprocessing_detector/annotation/workflow/scanner.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 40 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 458 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `src/image_preprocessing_detector/labeling/domain/config.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 100 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "google/gemini-2.0-flash-001" 3 times. | 6min |
| 106 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "google/gemini-2.0-flash-lite-001" 3 times. | 6min |

### `src/image_preprocessing_detector/synthetic/augmentation.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 49 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 314 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 33 to the 15 allowed. | 23min |

### `src/image_preprocessing_detector/synthetic/augmentation_fast.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 31 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 158 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `src/image_preprocessing_detector/synthetic/augmentation_hybrid.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 41 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 231 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `src/image_preprocessing_detector/synthetic/config.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 368 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "NotoSerif-Regular.ttf" 3 times. | 6min |
| 368 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "NotoSans-Regular.ttf" 3 times. | 6min |

### `src/image_preprocessing_detector/synthetic/corpus.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 38 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 530 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 38 to the 15 allowed. | 28min |

### `src/image_preprocessing_detector/synthetic/renderer.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 471 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |
| 730 | MAJOR | `python:S1172` | Remove the unused function parameter "text_density". | 5min |

### `src/image_preprocessing_detector/synthetic/schema_adapter.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 46 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 423 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 39 to the 15 allowed. | 29min |

### `tests/unit/annotation/conftest.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 79 | MAJOR | `python:S125` | Remove this commented out code. | 5min |
| 83 | MAJOR | `python:S125` | Remove this commented out code. | 5min |

### `tests/unit/annotation/test_orchestrator.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 126 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 150 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/test_layout_taxonomy.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 144 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |
| 211 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `scripts/consolidate_base_images.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 71 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "**/*.png" 7 times. | 14min |
| 73 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "*.jpg" 5 times. | 10min |

### `tests/unit/orchestration/test_modal_client.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 499 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |
| 514 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `tests/unit/scripts/test_generate_dataset_status.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 48 | MINOR | `python:S1481` | Replace the unused local variable "bytes_size" with "_". | 5min |
| 59 | MINOR | `python:S1481` | Replace the unused local variable "human_size" with "_". | 5min |

### `src/image_preprocessing_detector/detection/advanced_detectors.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 49 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "Invalid image" 5 times. | 10min |
| 802 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `tests/benchmark/test_throughput_benchmarks.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 104 | MAJOR | `pythonbugs:S2259` | Fix this attribute access on a value that can be 'None'. | 10min |
| 232 | MAJOR | `pythonbugs:S2259` | Fix this attribute access on a value that can be 'None'. | 10min |

### `tests/api/test_app_coverage.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 124 | MINOR | `python:S1481` | Remove the unused local variable "app". | 5min |
| 152 | MINOR | `python:S1481` | Remove the unused local variable "app". | 5min |

### `tests/integration/test_batch_regression.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 79 | MINOR | `python:S1481` | Replace the unused loop index "i" with "_". | 5min |
| 362 | MINOR | `python:S1481` | Replace the unused local variable "rationale" with "_". | 5min |

### `tests/unit/drift/test_active_learning.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 228 | MINOR | `python:S1481` | Replace the unused local variable "notes" with "_". | 5min |
| 283 | MINOR | `python:S1481` | Replace the unused local variable "notes" with "_". | 5min |

### `tests/unit/logging/test_logging_framework.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 232 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |
| 507 | MINOR | `python:S1481` | Remove the unused local variable "config". | 5min |

### `tests/integration/test_pdf_upscaling_integration.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 29 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 248 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `.github/workflows/sonarcloud.yml` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 33 | MAJOR | `githubactions:S8264` | Move this read permission from workflow level to job level. | 5min |
| 34 | MAJOR | `githubactions:S8233` | Move this write permission from workflow level to job level. | 5min |

### `tools/manual_validation_ui.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 150 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |
| 230 | MAJOR | `pythonsecurity:S6549` | Change this code to not construct the path from user-controlled data. | 30min |

### `modal/train_phase6_layout_lite.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 124 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |
| 127 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `scripts/check_download_progress.sh` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 31 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |
| 57 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `scripts/generate_parasitic_content_labels.py` (2 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 438 | MINOR | `python:S7494` | Replace set constructor call with a set comprehension. | 5min |
| 441 | MINOR | `python:S7494` | Replace set constructor call with a set comprehension. | 5min |

### `tests/e2e/test_stream2_detectors.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 355 | MAJOR | `python:S125` | Remove this commented out code. | 5min |

### `tests/unit/detection/test_warping_detector.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 431 | MINOR | `python:S1481` | Replace the unused local variable "poly_score" with "_". | 5min |

### `deployment/scripts/gcs_processor.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 196 | MAJOR | `python:S7493` | Use an asynchronous file API instead of synchronous open() in this async function. | 5min |

### `scripts/audit/audit_config.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 107 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `scripts/audit/automated_prescreening.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 202 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `scripts/audit/run_egret_full_dataset.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 103 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |

### `scripts/audit/run_egret_on_samples.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 319 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 24 to the 15 allowed. | 14min |

### `scripts/audit/select_diqa_audit_samples.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 655 | MAJOR | `python:S1172` | Remove the unused function parameter "selected". | 5min |

### `scripts/backfill_language_confidence.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 246 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 32 to the 15 allowed. | 22min |

### `scripts/benchmarks/benchmark_annotation_scanner.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 271 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/convert_doclaynet_to_extracted.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 189 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 25 to the 15 allowed. | 15min |

### `scripts/convert_fintabnet_to_extracted.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 234 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 38 to the 15 allowed. | 28min |

### `scripts/convert_funsd_plus_to_extracted.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 152 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `scripts/convert_funsd_to_extracted.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 154 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/disk_manifest.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 131 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 27 to the 15 allowed. | 17min |

### `scripts/download_fonts.sh` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 71 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `scripts/generate_dataset_parallel.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 126 | MINOR | `python:S1481` | Replace the unused loop index "sample" with "_". | 5min |

### `scripts/install_fonts.sh` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 12 | MAJOR | `shelldre:S7688` | Use '[[' instead of '[' for conditional tests. The '[[' construct is safer and more feature-rich. | 2min |

### `scripts/integrate_bhutan_afs_enrichments.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 831 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |

### `scripts/integrate_dzongkha_digits_enrichments.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 525 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |

### `scripts/integrate_resolution_quality.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 191 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |

### `scripts/integrate_skew_orientation.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 136 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `scripts/label_skew_orientation.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 115 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/mdiw13_groundtruth_mapper.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 193 | MINOR | `python:S1481` | Remove the unused local variable "lang". | 5min |

### `scripts/merge_skew_datasets.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 67 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 30 to the 15 allowed. | 20min |

### `scripts/metadata_completeness_report.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 257 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `scripts/prepare_orientation_dataset.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 495 | MAJOR | `python:S6709` | Provide a seed for this random generator. | 5min |

### `scripts/run_language_enrichment.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 173 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `scripts/select_natural_scan_skew_subset.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 784 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |

### `scripts/setup_cocotext_symlinks.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 150 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |

### `scripts/verify_fintabnet_samples.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 35 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 32 to the 15 allowed. | 22min |

### `src/image_preprocessing_detector/annotation/enrichment/manager.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 229 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `src/image_preprocessing_detector/annotation/enrichment/providers/siglip.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 158 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `src/image_preprocessing_detector/annotation/enrichment/providers/simulated.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 44 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |

### `src/image_preprocessing_detector/annotation/integrity/checkpointing.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 318 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `src/image_preprocessing_detector/annotation/parsers/base.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 233 | MAJOR | `python:S1172` | Remove the unused function parameter "config". | 5min |

### `src/image_preprocessing_detector/annotation/parsers/document/financebench.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 140 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `src/image_preprocessing_detector/annotation/parsers/document/midv500.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 240 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 27 to the 15 allowed. | 17min |

### `src/image_preprocessing_detector/annotation/parsers/handwriting/hasyv2.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 79 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 301 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 39 to the 15 allowed. | 29min |

### `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd19.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 66 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 20 to the 15 allowed. | 10min |

### `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd6.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 88 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. | 21min |

### `src/image_preprocessing_detector/annotation/parsers/handwriting/pucit_ohul.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 117 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 27 to the 15 allowed. | 17min |

### `src/image_preprocessing_detector/annotation/parsers/layout/docsynth300k.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 99 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 27 to the 15 allowed. | 17min |

### `src/image_preprocessing_detector/annotation/parsers/layout/fintabnet.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 109 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |

### `src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 111 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `src/image_preprocessing_detector/annotation/parsers/layout/pubtabnet.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 114 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 38 to the 15 allowed. | 28min |

### `src/image_preprocessing_detector/annotation/parsers/layout/sroie.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 66 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/arabic_docs.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 86 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 41 to the 15 allowed. | 31min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/cc_ocr.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 145 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/mle2e.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 74 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/mlt19.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 96 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 36 to the 15 allowed. | 26min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/multilingual_scripts.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 94 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 34 to the 15 allowed. | 24min |

### `src/image_preprocessing_detector/annotation/parsers/multilingual/nepali_handwritten.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 67 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 50 to the 15 allowed. | 40min |

### `src/image_preprocessing_detector/annotation/parsers/quality/dibco.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 65 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 29 to the 15 allowed. | 19min |

### `src/image_preprocessing_detector/annotation/parsers/quality/smartdoc.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 74 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 35 to the 15 allowed. | 25min |

### `src/image_preprocessing_detector/annotation/parsers/registry.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 41 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |

### `src/image_preprocessing_detector/annotation/storage/parquet_writer.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 198 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "part-0000.parquet" 3 times. | 6min |

### `src/image_preprocessing_detector/cli_layout.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 123 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "(unmapped)" 3 times. | 6min |

### `src/image_preprocessing_detector/labeling/domain/classifier.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 171 | MAJOR | `python:S1172` | Remove the unused function parameter "text_source". | 5min |

### `src/image_preprocessing_detector/labeling/domain/openrouter_client.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 163 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |

### `src/image_preprocessing_detector/schema_utils/layout_taxonomy.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 374 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |

### `tests/e2e/annotation/test_resume_e2e.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 28 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |

### `tests/unit/annotation/test_atomic.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 92 | CRITICAL | `python:S5727` | Remove this identity check; it will always be False. | 10min |

### `tests/unit/annotation/test_document_parsers.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 21 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |

### `tests/unit/annotation/test_enrichment.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 305 | MAJOR | `python:S1244` | Do not perform equality checks with floating point values. | 5min |

### `tests/unit/annotation/test_parser_registry.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 230 | MINOR | `python:S1481` | Remove the unused local variable "found". | 5min |

### `modal/shared/metrics_utils.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 73 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/create_sample_manifest.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 51 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `scripts/generate_rag_pipeline_visual.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 20 | MINOR | `python:S1481` | Replace the unused local variable "fig" with "_". | 5min |

### `scripts/test_modal_arena.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 109 | MINOR | `python:S117` | Rename this local variable "VLMInference" to match the regular expression ^[*a-z][a-z0-9*]*$. | 2min |

### `src/image_preprocessing_detector/labeling/arena/inference/api.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 204 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "API client not initialized" 3 times. | 6min |

### `src/image_preprocessing_detector/labeling/arena/inference/base.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 173 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `src/image_preprocessing_detector/labeling/arena/leaderboard.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 371 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 16 to the 15 allowed. | 6min |

### `src/image_preprocessing_detector/labeling/arena/metrics.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 65 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "Inputs contain NaN values" 4 times. | 8min |

### `src/image_preprocessing_detector/labeling/arena/modal_client.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 40 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |

### `src/image_preprocessing_detector/orchestration/device_orchestrator.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 253 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. | 9min |

### `tests/api/test_api_comprehensive.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 781 | CRITICAL | `python:S5727` | Remove this identity check; it will always be True. | 10min |

### `tests/unit/scripts/test_create_final_dataset.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 194 | MAJOR | `python:S125` | Remove this commented out code. | 5min |

### `tests/unit/scripts/test_download_docbank.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 36 | MINOR | `python:S1481` | Remove the unused local variable "mock_download". | 5min |

### `tests/unit/scripts/test_download_phase3_datasets.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 179 | MINOR | `python:S1481` | Remove the unused local variable "mock_repo". | 5min |

### `tests/unit/scripts/test_extract_vidore_labels.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 294 | MAJOR | `python:S125` | Remove this commented out code. | 5min |

### `tests/unit/scripts/test_generate_document_classification_labels.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 130 | MINOR | `python:S1481` | Replace the unused local variable "classification" with "_". | 5min |

### `tests/unit/scripts/test_generate_dqs_routing_matrix.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 126 | MAJOR | `python:S6711` | Use a "numpy.random.Generator" here instead of this legacy function. | 5min |

### `tests/unit/scripts/test_prepare_invoice_dataset.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 52 | MAJOR | `python:S3981` | The length of a collection is always ">=0", so update this test to either "==0" or ">0". | 2min |

### `tests/unit/scripts/test_weak_supervision_labeling.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 374 | MINOR | `python:S1481` | Remove the unused local variable "stats". | 5min |

### `.github/workflows/compatibility.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 27 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `src/image_preprocessing_detector/detection/hybrid_iqa.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 211 | MAJOR | `python:S3358` | Extract this nested conditional expression into an independent statement. | 5min |

### `src/image_preprocessing_detector/detection/layout_lite/doclayout_integration.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 610 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `src/image_preprocessing_detector/ingestion/office_processor.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 217 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. | 12min |

### `tests/benchmark/conftest.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 16 | MAJOR | `python:S108` | Either remove or fill this block of code. | 5min |

### `Dockerfile.gpu` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 79 | MINOR | `docker:S7031` | Merge this RUN instruction with the consecutive ones. | 5min |

### `src/image_preprocessing_detector/api/app.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 163 | BLOCKER | `python:S8414` | Add CORSMiddleware last in the middleware chain. | 5min |

### `src/image_preprocessing_detector/drift/alerting.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 993 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. | 8min |

### `src/image_preprocessing_detector/logging/__init__.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 263 | BLOCKER | `python:S3516` | Refactor this method to not always return the same value. | 2min |

### `tests/api/test_health_coverage.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 113 | MINOR | `python:S1481` | Remove the unused local variable "data". | 5min |

### `tests/api/test_middleware_coverage.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 96 | MINOR | `python:S1481` | Remove the unused local variable "mock_logger". | 5min |

### `tests/integration/test_modal_outage_simulation.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 193 | MINOR | `python:S1481` | Remove the unused local variable "consecutive_failures". | 5min |

### `tests/unit/monitoring/conftest.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 36 | MINOR | `python:S7504` | Remove this unnecessary `list()` call on an already iterable object. | 5min |

### `.github/workflows/qlty.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 12 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `tests/integration/test_classical_ml_integration_bleed_through.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 76 | MAJOR | `python:S125` | Remove this commented out code. | 5min |

### `tests/unit/detection/test_layout_lite.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 434 | CRITICAL | `python:S5727` | Remove this identity check; it will always be True. | 10min |

### `tests/unit/output/test_json_snapshots.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 631 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |

### `fuzz/fuzz_text_gate.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 69 | MAJOR | `python:S1542` | Rename function "TestOneInput" to match the regular expression ^[a-z_][a-z0-9_]*$. | 10min |

### `tests/conftest.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 372 | CRITICAL | `python:S1192` | Define a constant instead of duplicating this literal "*.jpg" 4 times. | 8min |

### `tests/integration/test_real_fixtures.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 277 | MINOR | `python:S1481` | Remove the unused local variable "skewed_pages". | 5min |

### `scripts/weak_supervision_labeling.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 172 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `scripts/validate_routing_accuracy.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 149 | INFO | `python:S1135` | Complete the task associated to this "TODO" comment. | 0min |

### `benchmarks/runners/run_benchmark.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 110 | MAJOR | `python:S1172` | Remove the unused function parameter "suite_config". | 5min |

### `scripts/download_docbank.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 26 | MAJOR | `python:S1172` | Remove the unused function parameter "use_cache". | 5min |

### `tests/fixtures/phase1_validation/synthetic_generator.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 38 | MAJOR | `python:S1172` | Remove the unused function parameter "dpi". | 5min |

### `.github/workflows/ci.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 42 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/cifuzzy.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 17 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/codecov.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 12 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/docs.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 21 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/mutation-testing.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 29 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/pr-validation.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 12 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/publish-pypi.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 31 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/reuse.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 13 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `.github/workflows/sbom.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 19 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |

### `tools/validate_front_matter.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 246 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 21 to the 15 allowed. | 11min |

### `fuzz/fuzz_image_loader.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 32 | MAJOR | `python:S1542` | Rename function "TestOneInput" to match the regular expression ^[a-z_][a-z0-9_]*$. | 10min |

### `fuzz/fuzz_pdf_loader.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 30 | MAJOR | `python:S1542` | Rename function "TestOneInput" to match the regular expression ^[a-z_][a-z0-9_]*$. | 10min |

### `tests/fixtures/phase1_validation/analyze_handwriting_samples.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 111 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. | 7min |

### `tests/fixtures/phase1_validation/validate_doclaynet_sample.py` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 25 | CRITICAL | `python:S3776` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. | 13min |

### `.github/workflows/scorecard.yml` (1 issues)

| Line | Severity | Rule | Message | Effort |
|------|----------|------|---------|--------|
| 17 | MAJOR | `githubactions:S8234` | Replace "read-all" with specific permissions (e.g., "contents: read"). | 5min |
