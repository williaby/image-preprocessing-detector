---
title: GAP_C Triage Report — Undocumented File Staleness Review
schema_type: common
status: draft
owner: docs-team
purpose: Triage report identifying undocumented files for architecture coverage review.
---

# GAP_C Triage Report

> **Generated**: 2026-02-23 07:18
> **Script**: `scripts/triage_gap_c.py`
> **Source**: GAP_C from `scripts/audit_diagram_file_coverage.py`

Files in git with no PUML architecture diagram reference, scored for staleness.
This report is a **review aid** — no files are deleted automatically.

---

## Summary

| Bucket | Count | Action |
| ------ | ----- | ------ |
| REVIEW_REMOVE (score ≥ 40) | 5 | Review each; delete or archive if confirmed outdated |
| REVIEW_NEEDED (score 25–39) | 38 | Human judgment required |
| PROBABLY_CURRENT (score < 25) | 408 | Likely active; add PUML reference if warranted |

| Directory | Total | REVIEW_REMOVE | REVIEW_NEEDED | PROBABLY_CURRENT |
| --------- | ----- | ------------- | ------------- | ---------------- |
| `config/` | 14 | 0 | 1 | 13 |
| `modal/` | 5 | 1 | 1 | 3 |
| `scripts/` | 254 | 4 | 29 | 221 |
| `src/` | 168 | 0 | 7 | 161 |
| `tools/` | 10 | 0 | 0 | 10 |

---

## REVIEW_REMOVE

Strong staleness signals. Review each file and delete or archive if confirmed outdated.
Check git blame and search for any remaining callers before deleting.

| File | Score | Created | Last Touched | Commits | LOC | Importers | Flags |
| ---- | ----- | ------- | ------------ | ------- | --- | --------- | ----- |
| `scripts/download_phase3_datasets.py` | 48 | 3mo | 3mo | 2 | 290 | n/a | phase_ref, download |
| `modal/train_phase6_layout_lite.py` | 45 | 3mo | 3mo | 1 | 199 | n/a | phase_ref |
| `scripts/download_doc3d_images.py` | 40 | 0mo | 0mo | 1 | 64 | n/a | download |
| `scripts/download_fonts_v2.sh` | 40 | 0mo | 0mo | 1 | 195 | n/a | download |
| `scripts/download_multimodal_textbook.py` | 40 | 1mo | 1mo | 1 | 188 | n/a | download |

---

## REVIEW_NEEDED

Mixed signals. Requires human judgment — check if the file is still
imported, called by a Makefile/CI target, or referenced in docs.

| File | Score | Created | Last Touched | Commits | LOC | Importers | Flags |
| ---- | ----- | ------- | ------------ | ------- | --- | --------- | ----- |
| `scripts/__init__.py` | 35 | 3mo | 3mo | 1 | 0 | n/a | — |
| `scripts/audit/__init__.py` | 35 | 0mo | 0mo | 1 | 3 | n/a | — |
| `scripts/audit/iaa_gold_standard.py` | 35 | 0mo | 0mo | 1 | 558 | n/a | old_legacy |
| `scripts/audit/integration/__init__.py` | 35 | 0mo | 0mo | 1 | 8 | n/a | — |
| `scripts/benchmarks/__init__.py` | 35 | 3mo | 3mo | 1 | 0 | n/a | — |
| `scripts/test_annotation.sh` | 30 | 0mo | 0mo | 1 | 72 | n/a | test_script |
| `src/image_preprocessing_detector/api/routes/__init__.py` | 30 | 3mo | 3mo | 1 | 13 | 0 | — |
| `src/image_preprocessing_detector/labeling/arena/datasets/__init__.py` | 30 | 1mo | 1mo | 1 | 17 | 0 | — |
| `src/image_preprocessing_detector/labeling/arena/inference/__init__.py` | 30 | 1mo | 1mo | 1 | 26 | 0 | — |
| `src/image_preprocessing_detector/labeling/domain/__init__.py` | 30 | 0mo | 0mo | 1 | 29 | 0 | — |
| `scripts/colab_utils.py` | 28 | 3mo | 3mo | 2 | 433 | n/a | colab |
| `config/iaa_gold_standard.yaml` | 25 | 0mo | 0mo | 1 | 40 | n/a | old_legacy |
| `modal/train_phase3_doclayout_yolo.py` | 25 | 3mo | 0mo | 2 | 237 | n/a | phase_ref |
| `scripts/audit/apply_arabic_docs_domains.py` | 25 | 0mo | 0mo | 1 | 192 | n/a | — |
| `scripts/audit/apply_jssoda_domains.py` | 25 | 0mo | 0mo | 1 | 127 | n/a | — |
| `scripts/audit/apply_siw13_domains.py` | 25 | 0mo | 0mo | 1 | 112 | n/a | — |
| `scripts/audit/integration/constants.py` | 25 | 0mo | 0mo | 1 | 103 | n/a | — |
| `scripts/audit/integration/mixins/__init__.py` | 25 | 0mo | 0mo | 1 | 28 | n/a | — |
| `scripts/audit/integration/mixins/confidence_tracking.py` | 25 | 0mo | 0mo | 1 | 166 | n/a | — |
| `scripts/audit/integration/mixins/reliability_summary.py` | 25 | 0mo | 0mo | 1 | 99 | n/a | — |
| `scripts/audit/integration/resolvers.py` | 25 | 0mo | 0mo | 1 | 156 | n/a | — |
| `scripts/audit/prepare_vlm_images.py` | 25 | 0mo | 0mo | 1 | 191 | n/a | — |
| `scripts/benchmarks/stream3_config.py` | 25 | 0mo | 0mo | 1 | 139 | n/a | — |
| `scripts/download_multilingual_script_datasets.py` | 25 | 0mo | 0mo | 1 | 695 | n/a | download |
| `scripts/enrich_docalign12k_p0.py` | 25 | 0mo | 0mo | 1 | 167 | n/a | — |
| `scripts/enrich_docalign12k_p1.py` | 25 | 0mo | 0mo | 1 | 190 | n/a | — |
| `scripts/extract_indicdlp_images.py` | 25 | 0mo | 0mo | 1 | 192 | n/a | — |
| `scripts/fix_docling_bboxes.py` | 25 | 0mo | 0mo | 1 | 132 | n/a | — |
| `scripts/l2_integration_utils.py` | 25 | 0mo | 0mo | 1 | 60 | n/a | — |
| `scripts/poc_openlid_v2.py` | 25 | 0mo | 0mo | 1 | 516 | n/a | poc |
| `scripts/pubtabnet_text_extractor.py` | 25 | 0mo | 0mo | 1 | 158 | n/a | — |
| `scripts/resolve_pr_comments.py` | 25 | 0mo | 0mo | 1 | 167 | n/a | — |
| `scripts/run_mutation_tests.sh` | 25 | 3mo | 3mo | 1 | 137 | n/a | — |
| `scripts/run_new_dataset_orchestrator.py` | 25 | 0mo | 0mo | 1 | 144 | n/a | — |
| `scripts/select_anyphotodoc_vlm_samples.py` | 25 | 0mo | 0mo | 1 | 157 | n/a | — |
| `src/image_preprocessing_detector/annotation/config/tiers.py` | 25 | 0mo | 0mo | 1 | 185 | 1 | — |
| `src/image_preprocessing_detector/detection/hybrid_iqa.py` | 25 | 3mo | 0mo | 2 | 350 | 0 | — |
| `src/image_preprocessing_detector/logging/outcomes.py` | 25 | 3mo | 3mo | 3 | 489 | 0 | — |

---

## PROBABLY_CURRENT

Low staleness score — these files are likely still active and simply
not yet documented in an architecture diagram.
Consider adding a reference to the appropriate PUML diagram.

**`config/`** (13 files)

- `config/agent_orchestration.yaml` — created 0mo ago, 1 commits, 64 LOC
- `config/audit_scorecard.yaml` — created 0mo ago, 3 commits, 311 LOC
- `config/integration_configs/_schema.yaml` — created 0mo ago, 1 commits, 45 LOC
- `config/integration_configs/doclaynet.yaml` — created 0mo ago, 1 commits, 32 LOC
- `config/integration_configs/funsd.yaml` — created 0mo ago, 1 commits, 31 LOC
- `config/integration_configs/jssoda.yaml` — created 0mo ago, 1 commits, 34 LOC
- `config/integration_configs/mdiw13.yaml` — created 0mo ago, 1 commits, 32 LOC
- `config/integration_configs/realdae.yaml` — created 0mo ago, 1 commits, 32 LOC
- `config/script_ml_classes.yaml` — created 0mo ago, 1 commits, 139 LOC
- `config/script_routing.yaml` — created 0mo ago, 3 commits, 215 LOC
- `config/siglip2_multitask.yaml` — created 0mo ago, 1 commits, 175 LOC
- `config/skew_estimation.yaml` — created 0mo ago, 1 commits, 116 LOC
- `config/training_criticality.yaml` — created 0mo ago, 1 commits, 53 LOC
**`modal/`** (3 files)

- `modal/app.py` — created 3mo ago, 2 commits, 71 LOC
- `modal/shared/__init__.py` — created 1mo ago, 1 commits, 63 LOC
- `modal/test_gcs.py` — created 3mo ago, 2 commits, 119 LOC
**`scripts/`** (221 files)

- `scripts/README.md` — created 3mo ago, 2 commits, 252 LOC
- `scripts/_path_security.py` — created 3mo ago, 2 commits, 112 LOC
- `scripts/analyze_soft_labels.py` — created 0mo ago, 2 commits, 993 LOC
- `scripts/annotate_base_metadata_incremental.py` — created 1mo ago, 1 commits, 287 LOC
- `scripts/annotate_base_metadata_lite.py` — created 0mo ago, 1 commits, 583 LOC
- `scripts/audit/README.md` — created 0mo ago, 1 commits, 570 LOC
- `scripts/audit/active_learning_bridge.py` — created 0mo ago, 1 commits, 281 LOC
- `scripts/audit/apply_cc_ocr_domains.py` — created 0mo ago, 1 commits, 206 LOC
- `scripts/audit/apply_mdiw13_domains.py` — created 0mo ago, 1 commits, 255 LOC
- `scripts/audit/apply_muharaf_domains.py` — created 0mo ago, 1 commits, 208 LOC
- `scripts/audit/apply_omnidocbench_domains.py` — created 0mo ago, 1 commits, 246 LOC
- `scripts/audit/apply_omnidocbench_languages.py` — created 0mo ago, 1 commits, 221 LOC
- `scripts/audit/assemble_comparison.py` — created 0mo ago, 2 commits, 1314 LOC
- `scripts/audit/assemble_diqa_comparison.py` — created 0mo ago, 2 commits, 764 LOC
- `scripts/audit/audit_config.py` — created 0mo ago, 3 commits, 1039 LOC
- `scripts/audit/audit_report_template.md` — created 0mo ago, 1 commits, 759 LOC
- `scripts/audit/audit_schema_compliance.py` — created 0mo ago, 3 commits, 1307 LOC
- `scripts/audit/auto_discover.py` — created 0mo ago, 1 commits, 318 LOC
- `scripts/audit/automated_prescreening.py` — created 0mo ago, 3 commits, 1448 LOC
- `scripts/audit/batch_remediation.py` — created 0mo ago, 1 commits, 649 LOC
- `scripts/audit/compute_scorecard.py` — created 0mo ago, 5 commits, 1467 LOC
- `scripts/audit/compute_training_criticality.py` — created 0mo ago, 1 commits, 423 LOC
- `scripts/audit/create_contact_sheets.py` — created 0mo ago, 2 commits, 322 LOC
- `scripts/audit/doc_quality_assessment.py` — created 0mo ago, 1 commits, 339 LOC
- `scripts/audit/enrich_content_flag_analysis.py` — created 0mo ago, 1 commits, 405 LOC
- `scripts/audit/enrich_omnidocbench_split_colormode.py` — created 0mo ago, 1 commits, 231 LOC
- `scripts/audit/fix_omnidocbench_language_misclassifications.py` — created 0mo ago, 1 commits, 287 LOC
- `scripts/audit/integration/base.py` — created 0mo ago, 1 commits, 692 LOC
- `scripts/audit/integration/config.py` — created 0mo ago, 1 commits, 218 LOC
- `scripts/audit/integration/loaders.py` — created 0mo ago, 1 commits, 301 LOC
- `scripts/audit/integration/mixins/content_flags.py` — created 0mo ago, 1 commits, 208 LOC
- `scripts/audit/integration/mixins/ki_mitigation.py` — created 0mo ago, 1 commits, 269 LOC
- `scripts/audit/integration_script_template.py` — created 0mo ago, 3 commits, 1398 LOC
- `scripts/audit/orchestrate_batch.py` — created 0mo ago, 1 commits, 443 LOC
- `scripts/audit/populate_audit_summary.py` — created 0mo ago, 1 commits, 774 LOC
- `scripts/audit/portfolio_analytics.py` — created 0mo ago, 1 commits, 644 LOC
- `scripts/audit/regression_check.py` — created 0mo ago, 1 commits, 673 LOC
- `scripts/audit/run_egret_full_dataset.py` — created 0mo ago, 1 commits, 364 LOC
- `scripts/audit/run_egret_on_samples.py` — created 0mo ago, 2 commits, 490 LOC
- `scripts/audit/score_history.py` — created 0mo ago, 1 commits, 238 LOC
- `scripts/audit/select_audit_samples.py` — created 0mo ago, 3 commits, 1201 LOC
- `scripts/audit/select_diqa_audit_samples.py` — created 0mo ago, 2 commits, 940 LOC
- `scripts/audit/vlm_streaming_service.py` — created 0mo ago, 1 commits, 459 LOC
- `scripts/audit_datasets.py` — created 0mo ago, 2 commits, 708 LOC
- `scripts/audit_font_coverage.py` — created 0mo ago, 1 commits, 287 LOC
- `scripts/audit_layout_labels.py` — created 0mo ago, 3 commits, 610 LOC
- `scripts/audit_v3_per_script_counts.py` — created 0mo ago, 1 commits, 413 LOC
- `scripts/auth_gcs.sh` — created 3mo ago, 5 commits, 154 LOC
- `scripts/backfill_language_confidence.py` — created 0mo ago, 3 commits, 526 LOC
- `scripts/backfill_text_quality_confidence.py` — created 0mo ago, 3 commits, 803 LOC
- `scripts/benchmark_classical_skew.py` — created 0mo ago, 1 commits, 348 LOC
- `scripts/benchmark_iqa_models.py` — created 0mo ago, 2 commits, 911 LOC
- `scripts/benchmarks/bench_descriptive.py` — created 0mo ago, 1 commits, 425 LOC
- `scripts/benchmarks/bench_document_source.py` — created 0mo ago, 1 commits, 271 LOC
- `scripts/benchmarks/bench_handwriting.py` — created 0mo ago, 1 commits, 304 LOC
- `scripts/benchmarks/bench_orientation.py` — created 0mo ago, 1 commits, 424 LOC
- `scripts/benchmarks/bench_script_detection.py` — created 0mo ago, 1 commits, 575 LOC
- `scripts/benchmarks/bench_shadow.py` — created 0mo ago, 2 commits, 296 LOC
- `scripts/benchmarks/bench_warping.py` — created 0mo ago, 1 commits, 330 LOC
- `scripts/benchmarks/benchmark_annotation_cache.py` — created 0mo ago, 1 commits, 603 LOC
- `scripts/benchmarks/benchmark_annotation_scanner.py` — created 0mo ago, 1 commits, 609 LOC
- `scripts/benchmarks/benchmark_classical_detectors.py` — created 3mo ago, 2 commits, 237 LOC
- `scripts/benchmarks/classification_metrics.py` — created 0mo ago, 2 commits, 439 LOC
- `scripts/benchmarks/generate_go_nogo_report.py` — created 0mo ago, 1 commits, 668 LOC
- `scripts/build_orientation_real_component.py` — created 0mo ago, 1 commits, 629 LOC
- `scripts/calculate_text_statistics.py` — created 0mo ago, 2 commits, 711 LOC
- `scripts/check_download_progress.sh` — created 3mo ago, 5 commits, 76 LOC
- `scripts/check_unresolved_pr_comments.py` — created 0mo ago, 1 commits, 554 LOC
- `scripts/checkpoint_manager.py` — created 3mo ago, 3 commits, 437 LOC
- `scripts/collect_vlm_iqa_labels.py` — created 0mo ago, 2 commits, 588 LOC
- `scripts/compare_quantization_results.py` — created 1mo ago, 1 commits, 349 LOC
- `scripts/consolidate_base_images.py` — created 1mo ago, 3 commits, 258 LOC
- `scripts/convert_cocotext_parquet.py` — created 0mo ago, 2 commits, 315 LOC
- `scripts/convert_datasets_to_images.py` — created 0mo ago, 3 commits, 560 LOC
- `scripts/convert_doclaynet_to_extracted.py` — created 0mo ago, 2 commits, 311 LOC
- `scripts/convert_fintabnet_to_extracted.py` — created 0mo ago, 2 commits, 359 LOC
- `scripts/convert_funsd_plus_to_extracted.py` — created 0mo ago, 2 commits, 266 LOC
- `scripts/convert_funsd_to_extracted.py` — created 0mo ago, 1 commits, 217 LOC
- `scripts/convert_hiertext_to_extracted.py` — created 0mo ago, 2 commits, 327 LOC
- `scripts/convert_mlt19_to_extracted.py` — created 0mo ago, 2 commits, 263 LOC
- `scripts/convert_parquet_to_images.py` — created 0mo ago, 3 commits, 440 LOC
- `scripts/convert_pubtabnet_to_extracted.py` — created 0mo ago, 1 commits, 250 LOC
- `scripts/convert_sroie_to_extracted.py` — created 0mo ago, 2 commits, 224 LOC
- `scripts/create_final_dataset.py` — created 3mo ago, 4 commits, 553 LOC
- `scripts/create_sample_manifest.py` — created 1mo ago, 2 commits, 151 LOC
- `scripts/create_stratified_validation.py` — created 1mo ago, 2 commits, 227 LOC
- `scripts/create_symlinks.py` — created 3mo ago, 2 commits, 205 LOC
- `scripts/disk_manifest.py` — created 0mo ago, 2 commits, 255 LOC
- `scripts/download_all_datasets.py` — created 3mo ago, 4 commits, 470 LOC
- `scripts/download_docbank.py` — created 3mo ago, 5 commits, 90 LOC
- `scripts/download_docile.sh` — created 3mo ago, 2 commits, 121 LOC
- `scripts/download_fonts.sh` — created 0mo ago, 2 commits, 114 LOC
- `scripts/download_ocr_quality_images.py` — created 1mo ago, 3 commits, 169 LOC
- `scripts/download_table_datasets.py` — created 3mo ago, 3 commits, 569 LOC
- `scripts/download_vidore_finance.py` — created 3mo ago, 2 commits, 103 LOC
- `scripts/enrich_language.py` — created 0mo ago, 4 commits, 1431 LOC
- `scripts/enrich_language_from_gt.py` — created 0mo ago, 4 commits, 1662 LOC
- `scripts/enrich_mlt19_language.py` — created 0mo ago, 3 commits, 761 LOC
- `scripts/extract_doclaynet_gt_index.py` — created 0mo ago, 1 commits, 387 LOC
- `scripts/extract_markushgrapher_images.py` — created 0mo ago, 1 commits, 213 LOC
- `scripts/extract_test_fixtures.py` — created 3mo ago, 2 commits, 507 LOC
- `scripts/extract_vidore_labels.py` — created 3mo ago, 4 commits, 693 LOC
- `scripts/extract_wili_samples.py` — created 3mo ago, 1 commits, 237 LOC
- `scripts/extract_workstream_loc.sh` — created 1mo ago, 3 commits, 417 LOC
- `scripts/fetch_sonarcloud_issues.py` — created 0mo ago, 1 commits, 354 LOC
- `scripts/gcs_helpers.sh` — created 3mo ago, 5 commits, 248 LOC
- `scripts/gdrive_sync.py` — created 3mo ago, 2 commits, 295 LOC
- `scripts/generate_base_dataset_v3.py` — created 0mo ago, 5 commits, 1090 LOC
- `scripts/generate_code_detection_dataset.py` — created 0mo ago, 1 commits, 1283 LOC
- `scripts/generate_combined_classification_labels.py` — created 3mo ago, 2 commits, 376 LOC
- `scripts/generate_dataset_parallel.py` — created 0mo ago, 2 commits, 374 LOC
- `scripts/generate_dataset_status.py` — created 3mo ago, 2 commits, 200 LOC
- `scripts/generate_document_classification_labels.py` — created 3mo ago, 1 commits, 255 LOC
- `scripts/generate_dqs_routing_matrix.py` — created 3mo ago, 5 commits, 539 LOC
- `scripts/generate_hiertext_contact_sheets.py` — created 0mo ago, 1 commits, 377 LOC
- `scripts/generate_mlt19_validation_sheets.py` — created 0mo ago, 1 commits, 309 LOC
- `scripts/generate_multitask_labels.py` — created 0mo ago, 1 commits, 572 LOC
- `scripts/generate_orientation_dataset.py` — created 0mo ago, 3 commits, 610 LOC
- `scripts/generate_parasitic_content_labels.py` — created 3mo ago, 4 commits, 503 LOC
- `scripts/generate_pubtabnet_contact_sheets.py` — created 0mo ago, 1 commits, 523 LOC
- `scripts/generate_rag_pipeline_visual.py` — created 1mo ago, 2 commits, 315 LOC
- `scripts/generate_vertical_text_labels.py` — created 3mo ago, 2 commits, 421 LOC
- `scripts/install_fonts.sh` — created 0mo ago, 2 commits, 101 LOC
- `scripts/integrate_anyphotodoc6300_enrichments.py` — created 0mo ago, 1 commits, 1681 LOC
- `scripts/integrate_arabic_docs_ocr_enrichments.py` — created 0mo ago, 1 commits, 408 LOC
- `scripts/integrate_bhutan_afs_enrichments.py` — created 0mo ago, 3 commits, 1169 LOC
- `scripts/integrate_cc_ocr_enrichments.py` — created 0mo ago, 1 commits, 421 LOC
- `scripts/integrate_cocotext_enrichments.py` — created 0mo ago, 1 commits, 857 LOC
- `scripts/integrate_cvsi_enrichments.py` — created 0mo ago, 1 commits, 570 LOC
- `scripts/integrate_dibco_enrichments.py` — created 0mo ago, 1 commits, 731 LOC
- `scripts/integrate_diqa_enrichments.py` — created 0mo ago, 2 commits, 1807 LOC
- `scripts/integrate_docalign12k_enrichments.py` — created 0mo ago, 1 commits, 1318 LOC
- `scripts/integrate_doclaynet_enrichments.py` — created 0mo ago, 1 commits, 798 LOC
- `scripts/integrate_docreal_enrichments.py` — created 0mo ago, 1 commits, 988 LOC
- `scripts/integrate_dzongkha_digits_enrichments.py` — created 0mo ago, 1 commits, 761 LOC
- `scripts/integrate_financebench_enrichments.py` — created 0mo ago, 1 commits, 507 LOC
- `scripts/integrate_fintabnet_enrichments.py` — created 0mo ago, 1 commits, 408 LOC
- `scripts/integrate_funsd_enrichments.py` — created 0mo ago, 1 commits, 1280 LOC
- `scripts/integrate_funsd_plus_enrichments.py` — created 0mo ago, 1 commits, 870 LOC
- `scripts/integrate_hasy_enrichments.py` — created 0mo ago, 1 commits, 358 LOC
- `scripts/integrate_hiertext_enrichments.py` — created 0mo ago, 1 commits, 1063 LOC
- `scripts/integrate_hindi_synth_enrichments.py` — created 0mo ago, 1 commits, 449 LOC
- `scripts/integrate_iam_enrichments.py` — created 0mo ago, 1 commits, 426 LOC
- `scripts/integrate_im2latex_enrichments.py` — created 0mo ago, 1 commits, 343 LOC
- `scripts/integrate_invoices_kg_enrichments.py` — created 0mo ago, 1 commits, 562 LOC
- `scripts/integrate_jssoda_enrichments.py` — created 0mo ago, 2 commits, 561 LOC
- `scripts/integrate_mathverse_enrichments.py` — created 0mo ago, 1 commits, 380 LOC
- `scripts/integrate_mdiw13_enrichments.py` — created 0mo ago, 1 commits, 1174 LOC
- `scripts/integrate_midv500_enrichments.py` — created 0mo ago, 1 commits, 714 LOC
- `scripts/integrate_mle2e_enrichments.py` — created 0mo ago, 1 commits, 553 LOC
- `scripts/integrate_mlt19_enrichments.py` — created 0mo ago, 3 commits, 1014 LOC
- `scripts/integrate_muharaf_enrichments.py` — created 0mo ago, 1 commits, 440 LOC
- `scripts/integrate_multimodal_textbook_enrichments.py` — created 0mo ago, 1 commits, 685 LOC
- `scripts/integrate_nepali_handwritten_enrichments.py` — created 0mo ago, 2 commits, 1399 LOC
- `scripts/integrate_nist_sd19_enrichments.py` — created 0mo ago, 1 commits, 450 LOC
- `scripts/integrate_nist_sd2_enrichments.py` — created 0mo ago, 1 commits, 501 LOC
- `scripts/integrate_nist_sd6_enrichments.py` — created 0mo ago, 1 commits, 501 LOC
- `scripts/integrate_ocr_quality_enrichments.py` — created 0mo ago, 1 commits, 742 LOC
- `scripts/integrate_ohr_bench_enrichments.py` — created 0mo ago, 1 commits, 1247 LOC
- `scripts/integrate_omnidocbench_enrichments.py` — created 0mo ago, 1 commits, 463 LOC
- `scripts/integrate_pubtabnet_enrichments.py` — created 0mo ago, 1 commits, 1056 LOC
- `scripts/integrate_pucit_ohul_enrichments.py` — created 0mo ago, 1 commits, 925 LOC
- `scripts/integrate_realdae_enrichments.py` — created 0mo ago, 2 commits, 1079 LOC
- `scripts/integrate_rvl_cdip_enrichments.py` — created 0mo ago, 1 commits, 962 LOC
- `scripts/integrate_sd7k_enrichments.py` — created 0mo ago, 1 commits, 995 LOC
- `scripts/integrate_signatr6k_enrichments.py` — created 0mo ago, 1 commits, 454 LOC
- `scripts/integrate_siw13_enrichments.py` — created 0mo ago, 1 commits, 712 LOC
- `scripts/integrate_smartdoc_qa_enrichments.py` — created 0mo ago, 1 commits, 1059 LOC
- `scripts/integrate_sroie_enrichments.py` — created 0mo ago, 1 commits, 767 LOC
- `scripts/integrate_tablebank_enrichments.py` — created 0mo ago, 1 commits, 404 LOC
- `scripts/integrate_tibhcr_enrichments.py` — created 0mo ago, 1 commits, 508 LOC
- `scripts/integrate_tobacco800_enrichments.py` — created 0mo ago, 1 commits, 1060 LOC
- `scripts/integrate_warpdoc_enrichments.py` — created 0mo ago, 1 commits, 1152 LOC
- `scripts/integrate_wsrd_enrichments.py` — created 0mo ago, 1 commits, 1299 LOC
- `scripts/integrate_yarmouk_enrichments.py` — created 0mo ago, 1 commits, 414 LOC
- `scripts/language_escalation.py` — created 0mo ago, 4 commits, 1104 LOC
- `scripts/mdiw13_groundtruth_mapper.py` — created 0mo ago, 2 commits, 212 LOC
- `scripts/measure_dataset_sufficiency.py` — created 3mo ago, 7 commits, 1832 LOC
- `scripts/merge_skew_datasets.py` — created 0mo ago, 2 commits, 415 LOC
- `scripts/metadata_completeness_report.py` — created 0mo ago, 1 commits, 373 LOC
- `scripts/migrate_layer2_schema_to_full.py` — created 0mo ago, 3 commits, 807 LOC
- `scripts/modal_helpers.sh` — created 3mo ago, 4 commits, 183 LOC
- `scripts/monitor_annotation.sh` — created 1mo ago, 2 commits, 52 LOC
- `scripts/organize_dual_storage.py` — created 3mo ago, 4 commits, 398 LOC
- `scripts/prepare_invoice_dataset.py` — created 3mo ago, 4 commits, 272 LOC
- `scripts/prepare_orientation_dataset.py` — created 0mo ago, 2 commits, 912 LOC
- `scripts/process_all_datasets.py` — created 0mo ago, 3 commits, 543 LOC
- `scripts/process_local_datasets_docling.py` — created 0mo ago, 3 commits, 549 LOC
- `scripts/promote_to_hf.py` — created 3mo ago, 4 commits, 653 LOC
- `scripts/run_complete_dataset_workflow.sh` — created 3mo ago, 3 commits, 160 LOC
- `scripts/run_language_enrichment.py` — created 0mo ago, 1 commits, 268 LOC
- `scripts/sample_ambiguous_cases.py` — created 3mo ago, 3 commits, 372 LOC
- `scripts/select_iqa_vlm_images.py` — created 0mo ago, 3 commits, 381 LOC
- `scripts/select_natural_scan_skew_subset.py` — created 0mo ago, 2 commits, 1036 LOC
- `scripts/setup_cocotext_symlinks.py` — created 0mo ago, 2 commits, 259 LOC
- `scripts/setup_fonts.sh` — created 0mo ago, 2 commits, 243 LOC
- `scripts/smoke_test_complex_scripts.py` — created 0mo ago, 1 commits, 290 LOC
- `scripts/split_dataset_catalog.py` — created 0mo ago, 2 commits, 484 LOC
- `scripts/standardize_layout_labels.py` — created 0mo ago, 3 commits, 888 LOC
- `scripts/test_arena_local.py` — created 1mo ago, 3 commits, 961 LOC
- `scripts/test_dataset_generation.py` — created 3mo ago, 4 commits, 66 LOC
- `scripts/test_escalation_comprehensive.py` — created 0mo ago, 1 commits, 413 LOC
- `scripts/test_modal_arena.py` — created 1mo ago, 2 commits, 212 LOC
- `scripts/triage_local_analysis.py` — created 0mo ago, 2 commits, 666 LOC
- `scripts/triage_text_analysis.py` — created 0mo ago, 2 commits, 593 LOC
- `scripts/update_data_locations.py` — created 0mo ago, 2 commits, 921 LOC
- `scripts/upload_datasets_to_gcs.sh` — created 3mo ago, 6 commits, 298 LOC
- `scripts/validate-workflows.sh` — created 3mo ago, 3 commits, 201 LOC
- `scripts/validate_annotation_output.py` — created 0mo ago, 3 commits, 605 LOC
- `scripts/validate_architecture_links.sh` — created 1mo ago, 2 commits, 187 LOC
- `scripts/validate_base_dataset_v3.py` — created 0mo ago, 2 commits, 632 LOC
- `scripts/validate_datasets.py` — created 3mo ago, 2 commits, 429 LOC
- `scripts/validate_dqs_correlation.py` — created 3mo ago, 3 commits, 406 LOC
- `scripts/validate_language_detection.py` — created 0mo ago, 2 commits, 378 LOC
- `scripts/validate_layout_lite.py` — created 3mo ago, 3 commits, 365 LOC
- `scripts/validate_openlid_mlt19.py` — created 0mo ago, 2 commits, 536 LOC
- `scripts/validate_pdf_classification.py` — created 3mo ago, 3 commits, 291 LOC
- `scripts/validate_pdf_resolution.py` — created 3mo ago, 2 commits, 361 LOC
- `scripts/verify_fintabnet_samples.py` — created 0mo ago, 2 commits, 212 LOC
- `scripts/visualize_risk_distribution.py` — created 3mo ago, 2 commits, 428 LOC
- `scripts/weak_supervision_labeling.py` — created 3mo ago, 2 commits, 380 LOC
**`src/`** (161 files)

- `src/image_preprocessing_detector/__init__.py` — created 4mo ago, 2 commits, 28 LOC
- `src/image_preprocessing_detector/annotation/__init__.py` — created 0mo ago, 2 commits, 115 LOC
- `src/image_preprocessing_detector/annotation/cli.py` — created 0mo ago, 1 commits, 785 LOC
- `src/image_preprocessing_detector/annotation/config/__init__.py` — created 0mo ago, 1 commits, 115 LOC
- `src/image_preprocessing_detector/annotation/config/datasets.py` — created 0mo ago, 3 commits, 1030 LOC
- `src/image_preprocessing_detector/annotation/config/settings.py` — created 0mo ago, 2 commits, 301 LOC
- `src/image_preprocessing_detector/annotation/config/validators.py` — created 0mo ago, 1 commits, 565 LOC
- `src/image_preprocessing_detector/annotation/enrichment/__init__.py` — created 0mo ago, 1 commits, 72 LOC
- `src/image_preprocessing_detector/annotation/enrichment/errors.py` — created 0mo ago, 1 commits, 175 LOC
- `src/image_preprocessing_detector/annotation/enrichment/providers/__init__.py` — created 0mo ago, 1 commits, 56 LOC
- `src/image_preprocessing_detector/annotation/enrichment/providers/base.py` — created 0mo ago, 1 commits, 206 LOC
- `src/image_preprocessing_detector/annotation/enrichment/providers/language_detector.py` — created 0mo ago, 2 commits, 530 LOC
- `src/image_preprocessing_detector/annotation/enrichment/providers/simulated.py` — created 0mo ago, 2 commits, 300 LOC
- `src/image_preprocessing_detector/annotation/enrichment/providers/yolo.py` — created 0mo ago, 1 commits, 331 LOC
- `src/image_preprocessing_detector/annotation/integrity/__init__.py` — created 0mo ago, 1 commits, 87 LOC
- `src/image_preprocessing_detector/annotation/integrity/atomic.py` — created 0mo ago, 1 commits, 184 LOC
- `src/image_preprocessing_detector/annotation/integrity/checkpointing.py` — created 0mo ago, 1 commits, 726 LOC
- `src/image_preprocessing_detector/annotation/integrity/hashing.py` — created 0mo ago, 1 commits, 159 LOC
- `src/image_preprocessing_detector/annotation/monitoring/__init__.py` — created 0mo ago, 1 commits, 86 LOC
- `src/image_preprocessing_detector/annotation/monitoring/logging.py` — created 0mo ago, 1 commits, 512 LOC
- `src/image_preprocessing_detector/annotation/parsers/__init__.py` — created 0mo ago, 1 commits, 73 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/__init__.py` — created 0mo ago, 1 commits, 49 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/anyphotodoc6300.py` — created 0mo ago, 1 commits, 120 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/docalign12k.py` — created 0mo ago, 1 commits, 149 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/docreal.py` — created 0mo ago, 1 commits, 134 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/drccbi.py` — created 0mo ago, 1 commits, 134 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/sd7k.py` — created 0mo ago, 1 commits, 145 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/staindoc.py` — created 0mo ago, 1 commits, 128 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/warpdoc.py` — created 0mo ago, 1 commits, 134 LOC
- `src/image_preprocessing_detector/annotation/parsers/correction/wsrd.py` — created 0mo ago, 1 commits, 154 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/__init__.py` — created 0mo ago, 2 commits, 69 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/document_haystack.py` — created 0mo ago, 1 commits, 124 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/financebench.py` — created 0mo ago, 1 commits, 287 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/markushgrapher.py` — created 0mo ago, 1 commits, 122 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/midv500.py` — created 0mo ago, 1 commits, 322 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/multimodal_textbook.py` — created 0mo ago, 1 commits, 117 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/ohr_bench.py` — created 0mo ago, 2 commits, 449 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/omnidocbench.py` — created 0mo ago, 1 commits, 117 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/realdae.py` — created 0mo ago, 1 commits, 119 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/rvl_cdip.py` — created 0mo ago, 2 commits, 356 LOC
- `src/image_preprocessing_detector/annotation/parsers/document/tobacco800.py` — created 0mo ago, 1 commits, 92 LOC
- `src/image_preprocessing_detector/annotation/parsers/formula/__init__.py` — created 0mo ago, 1 commits, 46 LOC
- `src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py` — created 0mo ago, 2 commits, 401 LOC
- `src/image_preprocessing_detector/annotation/parsers/generic.py` — created 0mo ago, 2 commits, 230 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/__init__.py` — created 0mo ago, 1 commits, 74 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/hasyv2.py` — created 0mo ago, 1 commits, 185 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py` — created 0mo ago, 1 commits, 421 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/maths_handwriting.py` — created 0mo ago, 1 commits, 89 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/muharaf.py` — created 0mo ago, 2 commits, 416 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_db2.py` — created 0mo ago, 2 commits, 142 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd19.py` — created 0mo ago, 1 commits, 126 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd6.py` — created 0mo ago, 1 commits, 195 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/pucit_ohul.py` — created 0mo ago, 1 commits, 185 LOC
- `src/image_preprocessing_detector/annotation/parsers/handwriting/signatr.py` — created 0mo ago, 1 commits, 126 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/__init__.py` — created 0mo ago, 2 commits, 69 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/doclaynet.py` — created 0mo ago, 2 commits, 247 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/docsynth300k.py` — created 0mo ago, 2 commits, 223 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/fintabnet.py` — created 0mo ago, 1 commits, 240 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/funsd.py` — created 0mo ago, 1 commits, 161 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/funsd_plus.py` — created 0mo ago, 1 commits, 119 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/indicdlp.py` — created 0mo ago, 1 commits, 192 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py` — created 0mo ago, 1 commits, 245 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/pubtabnet.py` — created 0mo ago, 1 commits, 262 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/sroie.py` — created 0mo ago, 1 commits, 148 LOC
- `src/image_preprocessing_detector/annotation/parsers/layout/tablebank.py` — created 0mo ago, 1 commits, 295 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/__init__.py` — created 0mo ago, 1 commits, 123 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/arabic_docs.py` — created 0mo ago, 1 commits, 213 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cc_ocr.py` — created 0mo ago, 1 commits, 230 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cocotext.py` — created 0mo ago, 1 commits, 366 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cvsi.py` — created 0mo ago, 1 commits, 116 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/hiertext.py` — created 0mo ago, 1 commits, 449 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/hindi_ocr_synthetic.py` — created 0mo ago, 1 commits, 159 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/jssoda.py` — created 0mo ago, 1 commits, 224 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mdiw13.py` — created 0mo ago, 1 commits, 270 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mle2e.py` — created 0mo ago, 1 commits, 147 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mlt19.py` — created 0mo ago, 1 commits, 271 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/multilingual_scripts.py` — created 0mo ago, 1 commits, 183 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/nepali_handwritten.py` — created 0mo ago, 1 commits, 208 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/siw13.py` — created 0mo ago, 1 commits, 115 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/synth_multiscript.py` — created 0mo ago, 1 commits, 214 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/tibhcr.py` — created 0mo ago, 1 commits, 102 LOC
- `src/image_preprocessing_detector/annotation/parsers/multilingual/yarmouk.py` — created 0mo ago, 1 commits, 97 LOC
- `src/image_preprocessing_detector/annotation/parsers/quality/__init__.py` — created 0mo ago, 2 commits, 54 LOC
- `src/image_preprocessing_detector/annotation/parsers/quality/dibco.py` — created 0mo ago, 1 commits, 146 LOC
- `src/image_preprocessing_detector/annotation/parsers/quality/diqa.py` — created 0mo ago, 2 commits, 194 LOC
- `src/image_preprocessing_detector/annotation/parsers/quality/ocr_quality.py` — created 0mo ago, 1 commits, 126 LOC
- `src/image_preprocessing_detector/annotation/parsers/quality/q_doc.py` — created 0mo ago, 1 commits, 193 LOC
- `src/image_preprocessing_detector/annotation/parsers/quality/smartdoc.py` — created 0mo ago, 1 commits, 209 LOC
- `src/image_preprocessing_detector/annotation/parsers/registry.py` — created 0mo ago, 3 commits, 258 LOC
- `src/image_preprocessing_detector/annotation/parsers/template.py` — created 0mo ago, 1 commits, 573 LOC
- `src/image_preprocessing_detector/annotation/schemas/__init__.py` — created 0mo ago, 1 commits, 136 LOC
- `src/image_preprocessing_detector/annotation/schemas/enums.py` — created 0mo ago, 1 commits, 134 LOC
- `src/image_preprocessing_detector/annotation/schemas/migrations.py` — created 0mo ago, 1 commits, 838 LOC
- `src/image_preprocessing_detector/annotation/schemas/sample.py` — created 0mo ago, 1 commits, 314 LOC
- `src/image_preprocessing_detector/annotation/schemas/validators.py` — created 0mo ago, 1 commits, 863 LOC
- `src/image_preprocessing_detector/annotation/storage/__init__.py` — created 0mo ago, 1 commits, 80 LOC
- `src/image_preprocessing_detector/annotation/storage/cache.py` — created 0mo ago, 1 commits, 582 LOC
- `src/image_preprocessing_detector/annotation/storage/parquet_writer.py` — created 0mo ago, 2 commits, 631 LOC
- `src/image_preprocessing_detector/annotation/workflow/__init__.py` — created 0mo ago, 1 commits, 124 LOC
- `src/image_preprocessing_detector/annotation/workflow/progress.py` — created 0mo ago, 1 commits, 310 LOC
- `src/image_preprocessing_detector/api/__init__.py` — created 3mo ago, 2 commits, 11 LOC
- `src/image_preprocessing_detector/api/models.py` — created 3mo ago, 1 commits, 197 LOC
- `src/image_preprocessing_detector/classification/degradation_classifier.py` — created 0mo ago, 1 commits, 226 LOC
- `src/image_preprocessing_detector/classification/document_source_classifier.py` — created 0mo ago, 1 commits, 557 LOC
- `src/image_preprocessing_detector/classification/text_layer_analyzer.py` — created 0mo ago, 2 commits, 388 LOC
- `src/image_preprocessing_detector/cli_layout.py` — created 0mo ago, 2 commits, 363 LOC
- `src/image_preprocessing_detector/core/__init__.py` — created 3mo ago, 3 commits, 34 LOC
- `src/image_preprocessing_detector/core/config.py` — created 3mo ago, 4 commits, 184 LOC
- `src/image_preprocessing_detector/core/exceptions.py` — created 3mo ago, 1 commits, 552 LOC
- `src/image_preprocessing_detector/detection/blank_page_detector.py` — created 0mo ago, 1 commits, 262 LOC
- `src/image_preprocessing_detector/detection/code_detector.py` — created 0mo ago, 1 commits, 344 LOC
- `src/image_preprocessing_detector/detection/deskew_pipeline.py` — created 0mo ago, 1 commits, 484 LOC
- `src/image_preprocessing_detector/detection/handwriting_detector.py` — created 0mo ago, 2 commits, 561 LOC
- `src/image_preprocessing_detector/detection/script_detector.py` — created 0mo ago, 1 commits, 573 LOC
- `src/image_preprocessing_detector/detection/shadow_detector.py` — created 0mo ago, 2 commits, 391 LOC
- `src/image_preprocessing_detector/detection/table_complexity.py` — created 0mo ago, 1 commits, 478 LOC
- `src/image_preprocessing_detector/detection/warping_detector.py` — created 0mo ago, 1 commits, 520 LOC
- `src/image_preprocessing_detector/labeling/__init__.py` — created 1mo ago, 2 commits, 21 LOC
- `src/image_preprocessing_detector/labeling/arena/__init__.py` — created 1mo ago, 1 commits, 107 LOC
- `src/image_preprocessing_detector/labeling/arena/cli.py` — created 1mo ago, 2 commits, 569 LOC
- `src/image_preprocessing_detector/labeling/arena/datasets/base.py` — created 1mo ago, 2 commits, 344 LOC
- `src/image_preprocessing_detector/labeling/arena/inference/base.py` — created 1mo ago, 4 commits, 253 LOC
- `src/image_preprocessing_detector/labeling/arena/inference/huggingface.py` — created 1mo ago, 2 commits, 466 LOC
- `src/image_preprocessing_detector/labeling/arena/inference/regression.py` — created 1mo ago, 3 commits, 519 LOC
- `src/image_preprocessing_detector/labeling/arena/modal_client.py` — created 1mo ago, 2 commits, 540 LOC
- `src/image_preprocessing_detector/logging/__init__.py` — created 3mo ago, 4 commits, 578 LOC
- `src/image_preprocessing_detector/logging/errors.py` — created 3mo ago, 4 commits, 733 LOC
- `src/image_preprocessing_detector/metrics/calibration.py` — created 1mo ago, 2 commits, 348 LOC
- `src/image_preprocessing_detector/models/__init__.py` — created 3mo ago, 5 commits, 25 LOC
- `src/image_preprocessing_detector/models/onnx_runtime.py` — created 0mo ago, 1 commits, 191 LOC
- `src/image_preprocessing_detector/monitoring/__init__.py` — created 3mo ago, 4 commits, 838 LOC
- `src/image_preprocessing_detector/orchestration/__init__.py` — created 3mo ago, 1 commits, 37 LOC
- `src/image_preprocessing_detector/pipeline/__init__.py` — created 3mo ago, 2 commits, 588 LOC
- `src/image_preprocessing_detector/routing/psm_recommender.py` — created 0mo ago, 1 commits, 223 LOC
- `src/image_preprocessing_detector/routing/script_router.py` — created 0mo ago, 3 commits, 356 LOC
- `src/image_preprocessing_detector/schema_utils/__init__.py` — created 0mo ago, 1 commits, 277 LOC
- `src/image_preprocessing_detector/schema_utils/bbox_utils.py` — created 0mo ago, 1 commits, 409 LOC
- `src/image_preprocessing_detector/schema_utils/dataset_source.py` — created 0mo ago, 2 commits, 608 LOC
- `src/image_preprocessing_detector/schema_utils/degradation_mapping.py` — created 0mo ago, 1 commits, 599 LOC
- `src/image_preprocessing_detector/schema_utils/iso_language_script.py` — created 0mo ago, 1 commits, 595 LOC
- `src/image_preprocessing_detector/schema_utils/iso_paper_sizes.py` — created 0mo ago, 1 commits, 260 LOC
- `src/image_preprocessing_detector/schema_utils/layout_taxonomy.py` — created 0mo ago, 2 commits, 563 LOC
- `src/image_preprocessing_detector/schema_utils/openlid_integration.py` — created 0mo ago, 2 commits, 779 LOC
- `src/image_preprocessing_detector/schema_utils/script_ml_mapping.py` — created 0mo ago, 1 commits, 286 LOC
- `src/image_preprocessing_detector/schema_utils/split_registry.py` — created 0mo ago, 1 commits, 254 LOC
- `src/image_preprocessing_detector/schema_utils/text_scope.py` — created 0mo ago, 1 commits, 439 LOC
- `src/image_preprocessing_detector/schema_utils/validation.py` — created 0mo ago, 1 commits, 341 LOC
- `src/image_preprocessing_detector/synthetic/__init__.py` — created 0mo ago, 1 commits, 154 LOC
- `src/image_preprocessing_detector/synthetic/augmentation.py` — created 0mo ago, 2 commits, 631 LOC
- `src/image_preprocessing_detector/synthetic/augmentation_fast.py` — created 0mo ago, 2 commits, 358 LOC
- `src/image_preprocessing_detector/synthetic/corpus.py` — created 0mo ago, 2 commits, 867 LOC
- `src/image_preprocessing_detector/synthetic/fonts.py` — created 0mo ago, 3 commits, 911 LOC
- `src/image_preprocessing_detector/synthetic/renderer.py` — created 0mo ago, 2 commits, 983 LOC
- `src/image_preprocessing_detector/synthetic/validation.py` — created 0mo ago, 2 commits, 699 LOC
- `src/image_preprocessing_detector/utils/__init__.py` — created 4mo ago, 7 commits, 131 LOC
- `src/image_preprocessing_detector/utils/datetime_compat.py` — created 3mo ago, 6 commits, 404 LOC
- `src/image_preprocessing_detector/utils/log_config.py` — created 3mo ago, 3 commits, 218 LOC
- `src/image_preprocessing_detector/utils/metadata_generator.py` — created 3mo ago, 4 commits, 443 LOC
- `src/image_preprocessing_detector/utils/model_config.py` — created 3mo ago, 2 commits, 133 LOC
- `src/image_preprocessing_detector/utils/path_security.py` — created 3mo ago, 1 commits, 66 LOC
- `src/image_preprocessing_detector/utils/tensor_cache.py` — created 3mo ago, 1 commits, 413 LOC
**`tools/`** (10 files)

- `tools/README.md` — created 3mo ago, 2 commits, 207 LOC
- `tools/add_front_matter.py` — created 1mo ago, 2 commits, 207 LOC
- `tools/fix_front_matter_fields.py` — created 1mo ago, 1 commits, 155 LOC
- `tools/frontmatter_contract/__init__.py` — created 4mo ago, 1 commits, 30 LOC
- `tools/frontmatter_contract/models.py` — created 4mo ago, 3 commits, 203 LOC
- `tools/gen_tools_catalog.py` — created 4mo ago, 3 commits, 123 LOC
- `tools/generate_diagram_svgs.py` — created 1mo ago, 3 commits, 245 LOC
- `tools/manual_validation_ui.py` — created 3mo ago, 2 commits, 340 LOC
- `tools/plantuml.jar` — created 1mo ago, 1 commits, 566748 LOC
- `tools/validate_front_matter.py` — created 4mo ago, 7 commits, 323 LOC

---

## Next Steps

| Action | Bucket | How |
| ------ | ------ | --- |
| Delete outdated file | REVIEW_REMOVE | Confirm no callers, then `git rm <file>` |
| Archive to docs/ | REVIEW_REMOVE | Move to `docs/_archived/` with a dated note |
| Keep and accept | REVIEW_REMOVE/NEEDED | Add to FILE_INVENTORY Intentionally Excluded table |
| Add PUML reference | PROBABLY_CURRENT | In the appropriate diagram note: `- src/.../module.py (N lines)` |

_Re-run `scripts/audit_diagram_file_coverage.py` after changes to verify gap closure._
