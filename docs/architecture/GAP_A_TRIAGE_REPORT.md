---
title: GAP_A Triage Report — Git-Tracked Files Absent from Inventory
schema_type: common
status: draft
owner: docs-team
purpose: Triage report classifying git-tracked files absent from FILE_INVENTORY by action required.
---

# GAP_A Triage Report

*Generated: 2026-02-23 07:42*

Files that are git-tracked but absent from FILE_INVENTORY, classified
by whether they need an inventory entry or are intentionally excluded.

## Summary

| Bucket | Count | % | Action |
| ------ | ----- | - | ------ |
| NEEDS_INVENTORY   |   40 |   9% | Add to inventory + assign workstream |
| DATASET_ADAPTER   |  135 |  31% | No action — framework already documented |
| OPERATIONAL_SCRIPT|  238 |  56% | Document in Known Exclusions section |
| NEEDS_TRIAGE      |   10 |   2% | Manual review required |
| **Total**         |  423 |     | |

### By Directory

| Directory | NEEDS_INV | ADAPTER | OPERATIONAL | TRIAGE |
| --------- | --------- | ------- | ----------- | ------ |
| `config/` | 0 | 0 | 13 | 0 |
| `modal/` | 0 | 0 | 3 | 0 |
| `scripts/` | 0 | 52 | 203 | 0 |
| `src/` | 40 | 83 | 9 | 10 |
| `tools/` | 0 | 0 | 10 | 0 |

## NEEDS_INVENTORY

These files are active core modules not yet assigned to a workstream.
**Action**: Add to FILE_INVENTORY, assign workstream, add PUML reference.

### ?

| File | Score | Importers | LOC | Commits | Reason |
| ---- | ----- | --------- | --- | ------- | ------ |
| `src/image_preprocessing_detector/logging/__init__.py` | 578 | 0 | 578 | 4 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/synthetic/__init__.py` | 154 | 0 | 154 | 1 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/utils/__init__.py` | 131 | 0 | 131 | 7 | pkg-init:LOC≥100-or-commits≥3 |

### WS1

| File | Score | Importers | LOC | Commits | Reason |
| ---- | ----- | --------- | --- | ------- | ------ |
| `src/image_preprocessing_detector/pipeline/__init__.py` | 588 | 0 | 588 | 2 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/schema_utils/__init__.py` | 277 | 0 | 277 | 1 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/schema_utils/layout_taxonomy.py` | 55 | 8 | 563 | 2 | score:55 |
| `src/image_preprocessing_detector/schema_utils/openlid_integration.py` | 55 | 5 | 779 | 2 | score:55 |
| `src/image_preprocessing_detector/schema_utils/iso_language_script.py` | 50 | 60 | 595 | 1 | score:50 |
| `src/image_preprocessing_detector/schema_utils/dataset_source.py` | 40 | 2 | 608 | 2 | score:40 |
| `src/image_preprocessing_detector/schema_utils/resolution_quality.py` | 35 | 3 | 657 | 1 | score:35 |
| `src/image_preprocessing_detector/schema_utils/validation.py` | 35 | 2 | 341 | 1 | score:35 |
| `src/image_preprocessing_detector/core/__init__.py` | 34 | 0 | 34 | 3 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/models/__init__.py` | 25 | 0 | 25 | 5 | pkg-init:LOC≥100-or-commits≥3 |

### WS3

| File | Score | Importers | LOC | Commits | Reason |
| ---- | ----- | --------- | --- | ------- | ------ |
| `src/image_preprocessing_detector/annotation/schemas/__init__.py` | 136 | 0 | 136 | 1 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/annotation/workflow/__init__.py` | 124 | 0 | 124 | 1 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/annotation/__init__.py` | 115 | 0 | 115 | 2 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/annotation/config/__init__.py` | 115 | 0 | 115 | 1 | pkg-init:LOC≥100-or-commits≥3 |
| `src/image_preprocessing_detector/annotation/config/datasets.py` | 55 | 18 | 1030 | 3 | score:55 |
| `src/image_preprocessing_detector/annotation/config/settings.py` | 55 | 8 | 301 | 2 | score:55 |
| `src/image_preprocessing_detector/annotation/monitoring/logging.py` | 50 | 256 | 512 | 1 | score:50 |
| `src/image_preprocessing_detector/annotation/monitoring/metrics.py` | 50 | 9 | 646 | 1 | score:50 |
| `src/image_preprocessing_detector/annotation/schemas/enrichment.py` | 50 | 11 | 379 | 1 | score:50 |
| `src/image_preprocessing_detector/labeling/model_spec.py` | 50 | 10 | 479 | 1 | score:50 |
| `src/image_preprocessing_detector/annotation/enrichment/errors.py` | 43 | 7 | 175 | 1 | score:43 |
| `src/image_preprocessing_detector/annotation/schemas/enums.py` | 43 | 7 | 134 | 1 | score:43 |
| `src/image_preprocessing_detector/annotation/schemas/immutable.py` | 43 | 66 | 181 | 1 | score:43 |
| `src/image_preprocessing_detector/annotation/storage/parquet_writer.py` | 40 | 3 | 631 | 2 | score:40 |
| `src/image_preprocessing_detector/annotation/workflow/scanner.py` | 40 | 2 | 622 | 2 | score:40 |
| `src/image_preprocessing_detector/annotation/config/validators.py` | 35 | 3 | 565 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/enrichment/manager.py` | 35 | 3 | 388 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/integrity/checkpointing.py` | 35 | 3 | 726 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/schemas/migrations.py` | 35 | 2 | 838 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/schemas/sample.py` | 35 | 3 | 314 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/schemas/validators.py` | 35 | 3 | 863 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/storage/cache.py` | 35 | 4 | 582 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/workflow/orchestrator.py` | 35 | 3 | 527 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/workflow/pipeline.py` | 35 | 2 | 738 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/workflow/preflight.py` | 35 | 2 | 748 | 1 | score:35 |
| `src/image_preprocessing_detector/annotation/workflow/progress.py` | 35 | 4 | 310 | 1 | score:35 |

### WS6

| File | Score | Importers | LOC | Commits | Reason |
| ---- | ----- | --------- | --- | ------- | ------ |
| `src/image_preprocessing_detector/monitoring/__init__.py` | 838 | 0 | 838 | 4 | pkg-init:LOC≥100-or-commits≥3 |

## DATASET_ADAPTER

These files are per-dataset adapter instances within a documented framework.
**Action**: No change needed — the framework is already in the inventory.

**scripts/** (52 files)

- `integrate_anyphotodoc6300_enrichments.py`
- `integrate_arabic_docs_ocr_enrichments.py`
- `integrate_bhutan_afs_enrichments.py`
- `integrate_cc_ocr_enrichments.py`
- `integrate_cocotext_enrichments.py`
- `integrate_cvsi_enrichments.py`
- `integrate_dibco_enrichments.py`
- `integrate_diqa_enrichments.py`
- `integrate_docalign12k_enrichments.py`
- `integrate_doclaynet_enrichments.py`
- `integrate_docreal_enrichments.py`
- `integrate_dzongkha_digits_enrichments.py`
- `integrate_financebench_enrichments.py`
- `integrate_fintabnet_enrichments.py`
- `integrate_funsd_enrichments.py`
- `integrate_funsd_plus_enrichments.py`
- `integrate_hasy_enrichments.py`
- `integrate_hiertext_enrichments.py`
- `integrate_hindi_synth_enrichments.py`
- `integrate_iam_enrichments.py`
- `integrate_im2latex_enrichments.py`
- `integrate_invoices_kg_enrichments.py`
- `integrate_jssoda_enrichments.py`
- `integrate_mathverse_enrichments.py`
- `integrate_mdiw13_enrichments.py`
- `integrate_midv500_enrichments.py`
- `integrate_mle2e_enrichments.py`
- `integrate_mlt19_enrichments.py`
- `integrate_muharaf_enrichments.py`
- `integrate_multimodal_textbook_enrichments.py`
- `integrate_nepali_handwritten_enrichments.py`
- `integrate_nist_sd19_enrichments.py`
- `integrate_nist_sd2_enrichments.py`
- `integrate_nist_sd6_enrichments.py`
- `integrate_ocr_quality_enrichments.py`
- `integrate_ohr_bench_enrichments.py`
- `integrate_omnidocbench_enrichments.py`
- `integrate_pubtabnet_enrichments.py`
- `integrate_pucit_ohul_enrichments.py`
- `integrate_realdae_enrichments.py`
- `integrate_rvl_cdip_enrichments.py`
- `integrate_sd7k_enrichments.py`
- `integrate_signatr6k_enrichments.py`
- `integrate_siw13_enrichments.py`
- `integrate_smartdoc_qa_enrichments.py`
- `integrate_sroie_enrichments.py`
- `integrate_tablebank_enrichments.py`
- `integrate_tibhcr_enrichments.py`
- `integrate_tobacco800_enrichments.py`
- `integrate_warpdoc_enrichments.py`
- `integrate_wsrd_enrichments.py`
- `integrate_yarmouk_enrichments.py`

**src/image_preprocessing_detector/annotation/enrichment/providers/** (7 files)

- `__init__.py`
- `base.py`
- `docling_layout.py`
- `language_detector.py`
- `siglip.py`
- `simulated.py`
- `yolo.py`

**src/image_preprocessing_detector/annotation/parsers/** (5 files)

- `__init__.py`
- `base.py`
- `generic.py`
- `registry.py`
- `template.py`

**src/image_preprocessing_detector/annotation/parsers/correction/** (9 files)

- `__init__.py`
- `anyphotodoc6300.py`
- `docalign12k.py`
- `docreal.py`
- `drccbi.py`
- `sd7k.py`
- `staindoc.py`
- `warpdoc.py`
- `wsrd.py`

**src/image_preprocessing_detector/annotation/parsers/document/** (11 files)

- `__init__.py`
- `document_haystack.py`
- `financebench.py`
- `markushgrapher.py`
- `midv500.py`
- `multimodal_textbook.py`
- `ohr_bench.py`
- `omnidocbench.py`
- `realdae.py`
- `rvl_cdip.py`
- `tobacco800.py`

**src/image_preprocessing_detector/annotation/parsers/formula/** (2 files)

- `__init__.py`
- `im2latex.py`

**src/image_preprocessing_detector/annotation/parsers/handwriting/** (10 files)

- `__init__.py`
- `hasyv2.py`
- `iam.py`
- `maths_handwriting.py`
- `muharaf.py`
- `nist_db2.py`
- `nist_sd19.py`
- `nist_sd6.py`
- `pucit_ohul.py`
- `signatr.py`

**src/image_preprocessing_detector/annotation/parsers/layout/** (11 files)

- `__init__.py`
- `doclaynet.py`
- `docsynth300k.py`
- `fintabnet.py`
- `funsd.py`
- `funsd_plus.py`
- `indicdlp.py`
- `invoices_kg.py`
- `pubtabnet.py`
- `sroie.py`
- `tablebank.py`

**src/image_preprocessing_detector/annotation/parsers/multilingual/** (17 files)

- `__init__.py`
- `arabic_docs.py`
- `cc_ocr.py`
- `cocotext.py`
- `cvsi.py`
- `hiertext.py`
- `hindi_ocr_synthetic.py`
- `jssoda.py`
- `mdiw13.py`
- `mle2e.py`
- `mlt19.py`
- `multilingual_scripts.py`
- `nepali_handwritten.py`
- `siw13.py`
- `synth_multiscript.py`
- `tibhcr.py`
- `yarmouk.py`

**src/image_preprocessing_detector/annotation/parsers/quality/** (6 files)

- `__init__.py`
- `dibco.py`
- `diqa.py`
- `ocr_quality.py`
- `q_doc.py`
- `smartdoc.py`

**src/image_preprocessing_detector/labeling/domain/** (5 files)

- `__init__.py`
- `classifier.py`
- `config.py`
- `openrouter_client.py`
- `prompts.py`

## OPERATIONAL_SCRIPT

These files are data-ops utilities, audit tools, or one-off scripts
outside the production architecture scope.
**Action**: Document in a "Known Exclusions" section of the inventory.

**modal-support-file** (3 files)

- `modal/app.py`
- `modal/shared/__init__.py`
- `modal/test_gcs.py`

**name-pattern** (38 files)

- `scripts/auth_gcs.sh`
- `scripts/benchmark_classical_skew.py`
- `scripts/benchmark_iqa_models.py`
- `scripts/check_download_progress.sh`
- `scripts/colab_utils.py`
- `scripts/convert_cocotext_parquet.py`
- `scripts/convert_datasets_to_images.py`
- `scripts/convert_doclaynet_to_extracted.py`
- `scripts/convert_fintabnet_to_extracted.py`
- `scripts/convert_funsd_plus_to_extracted.py`
- `scripts/convert_funsd_to_extracted.py`
- `scripts/convert_hiertext_to_extracted.py`
- `scripts/convert_mlt19_to_extracted.py`
- `scripts/convert_parquet_to_images.py`
- `scripts/convert_pubtabnet_to_extracted.py`
- `scripts/convert_sroie_to_extracted.py`
- `scripts/download_doc3d_images.py`
- `scripts/download_docbank.py`
- `scripts/download_docile.sh`
- `scripts/download_fonts.sh`
- `scripts/download_fonts_v2.sh`
- `scripts/download_multilingual_script_datasets.py`
- `scripts/download_multimodal_textbook.py`
- `scripts/download_ocr_quality_images.py`
- `scripts/download_vidore_finance.py`
- `scripts/extract_workstream_loc.sh`
- `scripts/gcs_helpers.sh`
- `scripts/install_fonts.sh`
- `scripts/modal_helpers.sh`
- `scripts/monitor_annotation.sh`
- `scripts/run_complete_dataset_workflow.sh`
- `scripts/run_mutation_tests.sh`
- `scripts/setup_cocotext_symlinks.py`
- `scripts/setup_fonts.sh`
- `scripts/test_annotation.sh`
- `scripts/upload_datasets_to_gcs.sh`
- `scripts/validate-workflows.sh`
- `scripts/validate_architecture_links.sh`

**operational-dir** (64 files)

- `scripts/audit/README.md`
- `scripts/audit/__init__.py`
- `scripts/audit/active_learning_bridge.py`
- `scripts/audit/apply_arabic_docs_domains.py`
- `scripts/audit/apply_cc_ocr_domains.py`
- `scripts/audit/apply_jssoda_domains.py`
- `scripts/audit/apply_mdiw13_domains.py`
- `scripts/audit/apply_muharaf_domains.py`
- `scripts/audit/apply_omnidocbench_domains.py`
- `scripts/audit/apply_omnidocbench_languages.py`
- `scripts/audit/apply_siw13_domains.py`
- `scripts/audit/assemble_comparison.py`
- `scripts/audit/assemble_diqa_comparison.py`
- `scripts/audit/audit_config.py`
- `scripts/audit/audit_report_template.md`
- `scripts/audit/audit_schema_compliance.py`
- `scripts/audit/auto_discover.py`
- `scripts/audit/automated_prescreening.py`
- `scripts/audit/batch_remediation.py`
- `scripts/audit/compute_scorecard.py`
- `scripts/audit/compute_training_criticality.py`
- `scripts/audit/create_contact_sheets.py`
- `scripts/audit/doc_quality_assessment.py`
- `scripts/audit/enrich_content_flag_analysis.py`
- `scripts/audit/enrich_omnidocbench_split_colormode.py`
- `scripts/audit/fix_omnidocbench_language_misclassifications.py`
- `scripts/audit/iaa_gold_standard.py`
- `scripts/audit/integration/__init__.py`
- `scripts/audit/integration/base.py`
- `scripts/audit/integration/config.py`
- `scripts/audit/integration/constants.py`
- `scripts/audit/integration/loaders.py`
- `scripts/audit/integration/mixins/__init__.py`
- `scripts/audit/integration/mixins/confidence_tracking.py`
- `scripts/audit/integration/mixins/content_flags.py`
- `scripts/audit/integration/mixins/ki_mitigation.py`
- `scripts/audit/integration/mixins/reliability_summary.py`
- `scripts/audit/integration/resolvers.py`
- `scripts/audit/integration_script_template.py`
- `scripts/audit/orchestrate_batch.py`
- `scripts/audit/populate_audit_summary.py`
- `scripts/audit/portfolio_analytics.py`
- `scripts/audit/prepare_vlm_images.py`
- `scripts/audit/regression_check.py`
- `scripts/audit/run_egret_full_dataset.py`
- `scripts/audit/run_egret_on_samples.py`
- `scripts/audit/score_history.py`
- `scripts/audit/select_audit_samples.py`
- `scripts/audit/select_diqa_audit_samples.py`
- `scripts/audit/vlm_streaming_service.py`
- `scripts/benchmarks/__init__.py`
- `scripts/benchmarks/bench_descriptive.py`
- `scripts/benchmarks/bench_document_source.py`
- `scripts/benchmarks/bench_handwriting.py`
- `scripts/benchmarks/bench_orientation.py`
- `scripts/benchmarks/bench_script_detection.py`
- `scripts/benchmarks/bench_shadow.py`
- `scripts/benchmarks/bench_warping.py`
- `scripts/benchmarks/benchmark_annotation_cache.py`
- `scripts/benchmarks/benchmark_annotation_scanner.py`
- `scripts/benchmarks/benchmark_classical_detectors.py`
- `scripts/benchmarks/classification_metrics.py`
- `scripts/benchmarks/generate_go_nogo_report.py`
- `scripts/benchmarks/stream3_config.py`

**pkg-init** (9 files)

- `src/image_preprocessing_detector/__init__.py`
- `src/image_preprocessing_detector/annotation/enrichment/__init__.py`
- `src/image_preprocessing_detector/annotation/integrity/__init__.py`
- `src/image_preprocessing_detector/annotation/monitoring/__init__.py`
- `src/image_preprocessing_detector/annotation/storage/__init__.py`
- `src/image_preprocessing_detector/api/__init__.py`
- `src/image_preprocessing_detector/api/routes/__init__.py`
- `src/image_preprocessing_detector/labeling/__init__.py`
- `src/image_preprocessing_detector/orchestration/__init__.py`

**tools-or-config** (23 files)

- `config/agent_orchestration.yaml`
- `config/audit_scorecard.yaml`
- `config/iaa_gold_standard.yaml`
- `config/integration_configs/_schema.yaml`
- `config/integration_configs/doclaynet.yaml`
- `config/integration_configs/funsd.yaml`
- `config/integration_configs/jssoda.yaml`
- `config/integration_configs/mdiw13.yaml`
- `config/integration_configs/realdae.yaml`
- `config/script_ml_classes.yaml`
- `config/script_routing.yaml`
- `config/skew_estimation.yaml`
- `config/training_criticality.yaml`
- `tools/README.md`
- `tools/add_front_matter.py`
- `tools/fix_front_matter_fields.py`
- `tools/frontmatter_contract/__init__.py`
- `tools/frontmatter_contract/models.py`
- `tools/gen_tools_catalog.py`
- `tools/generate_diagram_svgs.py`
- `tools/manual_validation_ui.py`
- `tools/plantuml.jar`
- `tools/validate_front_matter.py`

**unclassified-script** (101 files)

- `scripts/README.md`
- `scripts/__init__.py`
- `scripts/_path_security.py`
- `scripts/aggregate_layer2_metadata.py`
- `scripts/analyze_soft_labels.py`
- `scripts/annotate_base_metadata_incremental.py`
- `scripts/annotate_base_metadata_lite.py`
- `scripts/audit_datasets.py`
- `scripts/audit_layout_labels.py`
- `scripts/backfill_language_confidence.py`
- `scripts/backfill_text_quality_confidence.py`
- `scripts/calculate_text_statistics.py`
- `scripts/check_unresolved_pr_comments.py`
- `scripts/checkpoint_manager.py`
- `scripts/collect_vlm_iqa_labels.py`
- `scripts/compare_quantization_results.py`
- `scripts/consolidate_base_images.py`
- `scripts/create_final_dataset.py`
- `scripts/create_sample_manifest.py`
- `scripts/create_stratified_validation.py`
- `scripts/create_symlinks.py`
- `scripts/disk_manifest.py`
- `scripts/enrich_docalign12k_p0.py`
- `scripts/enrich_docalign12k_p1.py`
- `scripts/enrich_language.py`
- `scripts/enrich_language_from_gt.py`
- `scripts/enrich_metadata_from_llm.py`
- `scripts/enrich_mlt19_language.py`
- `scripts/extract_doclaynet_gt_index.py`
- `scripts/extract_indicdlp_images.py`
- `scripts/extract_markushgrapher_images.py`
- `scripts/extract_test_fixtures.py`
- `scripts/extract_vidore_labels.py`
- `scripts/extract_wili_samples.py`
- `scripts/fetch_sonarcloud_issues.py`
- `scripts/fix_docling_bboxes.py`
- `scripts/gdrive_sync.py`
- `scripts/generate_code_detection_dataset.py`
- `scripts/generate_combined_classification_labels.py`
- `scripts/generate_dataset_parallel.py`
- `scripts/generate_dataset_status.py`
- `scripts/generate_document_classification_labels.py`
- `scripts/generate_dqs_routing_matrix.py`
- `scripts/generate_hiertext_contact_sheets.py`
- `scripts/generate_mlt19_validation_sheets.py`
- `scripts/generate_orientation_dataset.py`
- `scripts/generate_parasitic_content_labels.py`
- `scripts/generate_pubtabnet_contact_sheets.py`
- `scripts/generate_rag_pipeline_visual.py`
- `scripts/generate_skew_dataset.py`
- `scripts/generate_vertical_text_labels.py`
- `scripts/integrate_resolution_quality.py`
- `scripts/integrate_skew_orientation.py`
- `scripts/l2_integration_utils.py`
- `scripts/label_resolution_quality.py`
- `scripts/label_skew_classical.py`
- `scripts/label_skew_orientation.py`
- `scripts/language_escalation.py`
- `scripts/materialize_reliability_summary.py`
- `scripts/mdiw13_groundtruth_mapper.py`
- `scripts/measure_dataset_sufficiency.py`
- `scripts/merge_skew_datasets.py`
- `scripts/metadata_completeness_report.py`
- `scripts/migrate_layer2_schema_to_full.py`
- `scripts/organize_dual_storage.py`
- `scripts/poc_openlid_v2.py`
- `scripts/prepare_invoice_dataset.py`
- `scripts/prepare_orientation_dataset.py`
- `scripts/process_all_datasets.py`
- `scripts/process_local_datasets_docling.py`
- `scripts/promote_to_hf.py`
- `scripts/pubtabnet_text_extractor.py`
- `scripts/resolve_pr_comments.py`
- `scripts/run_language_enrichment.py`
- `scripts/run_new_dataset_orchestrator.py`
- `scripts/sample_ambiguous_cases.py`
- `scripts/select_anyphotodoc_vlm_samples.py`
- `scripts/select_iqa_vlm_images.py`
- `scripts/select_natural_scan_skew_subset.py`
- `scripts/smoke_test_complex_scripts.py`
- `scripts/split_dataset_catalog.py`
- `scripts/standardize_layout_labels.py`
- `scripts/test_arena_local.py`
- `scripts/test_dataset_generation.py`
- `scripts/test_escalation_comprehensive.py`
- `scripts/test_modal_arena.py`
- `scripts/triage_local_analysis.py`
- `scripts/triage_text_analysis.py`
- `scripts/update_data_locations.py`
- `scripts/validate_annotation_output.py`
- `scripts/validate_base_dataset_v3.py`
- `scripts/validate_dqs_correlation.py`
- `scripts/validate_language_detection.py`
- `scripts/validate_layout_lite.py`
- `scripts/validate_openlid_mlt19.py`
- `scripts/validate_pdf_classification.py`
- `scripts/validate_pdf_resolution.py`
- `scripts/validate_routing_accuracy.py`
- `scripts/verify_fintabnet_samples.py`
- `scripts/visualize_risk_distribution.py`
- `scripts/weak_supervision_labeling.py`

## NEEDS_TRIAGE

These files require human judgment. Review each one and assign to
NEEDS_INVENTORY, DATASET_ADAPTER, or OPERATIONAL_SCRIPT as appropriate.

| File | Score | Importers | LOC | Commits | Naming | Reason |
| ---- | ----- | --------- | --- | ------- | ------ | ------ |
| `src/image_preprocessing_detector/annotation/cli.py` | 20 | 1 | 785 | 1 | — | score:20 |
| `src/image_preprocessing_detector/annotation/config/tiers.py` | 13 | 1 | 185 | 1 | — | score:13 |
| `src/image_preprocessing_detector/annotation/integrity/atomic.py` | 28 | 4 | 184 | 1 | — | score:28 |
| `src/image_preprocessing_detector/annotation/integrity/hashing.py` | 28 | 2 | 159 | 1 | — | score:28 |
| `src/image_preprocessing_detector/schema_utils/bbox_utils.py` | 20 | 1 | 409 | 1 | — | score:20 |
| `src/image_preprocessing_detector/schema_utils/degradation_mapping.py` | 20 | 1 | 599 | 1 | — | score:20 |
| `src/image_preprocessing_detector/schema_utils/iso_paper_sizes.py` | 13 | 1 | 260 | 1 | — | score:13 |
| `src/image_preprocessing_detector/schema_utils/script_ml_mapping.py` | 28 | 4 | 286 | 1 | — | score:28 |
| `src/image_preprocessing_detector/schema_utils/split_registry.py` | 28 | 2 | 254 | 1 | — | score:28 |
| `src/image_preprocessing_detector/schema_utils/text_scope.py` | 20 | 1 | 439 | 1 | — | score:20 |

## Next Steps

1. **NEEDS_INVENTORY**: For each file, open FILE_INVENTORY and add a row
   under the suggested workstream. Then reference it in the appropriate PUML
   diagram.
2. **DATASET_ADAPTER**: No action. Each entry documents an instance of a
   framework that is already inventoried at the framework level.
3. **OPERATIONAL_SCRIPT**: Add a *Known Exclusions* section to the FILE_INVENTORY
   listing these scripts with a one-line description of "why excluded".
4. **NEEDS_TRIAGE**: Review manually. If import_count > 0, prefer NEEDS_INVENTORY.
   If it fits a clear dataset/tool pattern, assign the matching category.
