---
title: Diagram File Coverage Audit
schema_type: common
status: active
owner: docs-team
purpose: Audit report mapping git-tracked diagram files to workstream inventory entries.
---

# Diagram File Coverage Audit

> **Generated**: 2026-02-23 07:34
> **Script**: `scripts/audit_diagram_file_coverage.py`
> **Inventory**: `docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`

---

## Summary

| Metric | Count |
|--------|-------|
| Git-tracked source files | 579 |
| Files in FILE_INVENTORY | 177 |
| Unique PUML file references (normalized) | 153 |
| PUML diagrams scanned | 37 |

| Gap Category | Count | Meaning |
|-------------|-------|---------|
| **GAP_A**: In git, NOT in inventory | 425 | Newly added; need workstream assignment |
| **GAP_B**: In inventory, NOT in git | 23 | Deleted/renamed; remove from inventory |
| **GAP_C**: In git, NO PUML reference | 453 | No architecture diagram reference |
| **GAP_D**: PUML ref not in git | 27 | Broken diagram reference (non-planned) |

| Coverage | Percentage |
|----------|-----------|
| Files covered by FILE_INVENTORY | 26.6% (154/579) |
| Files referenced in PUML diagrams | 21.8% (126/579) |

---

## GAP_A — In Git, NOT in Inventory

These files are git-tracked but have no entry in `FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`.
Review each to determine: (a) assign to a workstream and add to inventory, or
(b) add to the Intentionally Excluded section if it's tooling/docs/test support.

### `config/` (13 files)

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

### `modal/` (3 files)

- `modal/app.py`
- `modal/shared/__init__.py`
- `modal/test_gcs.py`

### `scripts/` (256 files)

- `scripts/.gitkeep`
- `scripts/README.md`
- `scripts/__init__.py`
- `scripts/_path_security.py`
- `scripts/aggregate_layer2_metadata.py`
- `scripts/analyze_soft_labels.py`
- `scripts/annotate_base_metadata_incremental.py`
- `scripts/annotate_base_metadata_lite.py`
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
- `scripts/audit_datasets.py`
- `scripts/audit_layout_labels.py`
- `scripts/auth_gcs.sh`
- `scripts/backfill_language_confidence.py`
- `scripts/backfill_text_quality_confidence.py`
- `scripts/benchmark_classical_skew.py`
- `scripts/benchmark_iqa_models.py`
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
- `scripts/calculate_text_statistics.py`
- `scripts/check_download_progress.sh`
- `scripts/check_unresolved_pr_comments.py`
- `scripts/checkpoint_manager.py`
- `scripts/colab_utils.py`
- `scripts/collect_vlm_iqa_labels.py`
- `scripts/compare_quantization_results.py`
- `scripts/consolidate_base_images.py`
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
- `scripts/create_final_dataset.py`
- `scripts/create_sample_manifest.py`
- `scripts/create_stratified_validation.py`
- `scripts/create_symlinks.py`
- `scripts/disk_manifest.py`
- `scripts/download_doc3d_images.py`
- `scripts/download_docbank.py`
- `scripts/download_docile.sh`
- `scripts/download_fonts.sh`
- `scripts/download_fonts_v2.sh`
- `scripts/download_multilingual_script_datasets.py`
- `scripts/download_multimodal_textbook.py`
- `scripts/download_ocr_quality_images.py`
- `scripts/download_vidore_finance.py`
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
- `scripts/extract_workstream_loc.sh`
- `scripts/fetch_sonarcloud_issues.py`
- `scripts/fix_docling_bboxes.py`
- `scripts/gcs_helpers.sh`
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
- `scripts/install_fonts.sh`
- `scripts/integrate_anyphotodoc6300_enrichments.py`
- `scripts/integrate_arabic_docs_ocr_enrichments.py`
- `scripts/integrate_bhutan_afs_enrichments.py`
- `scripts/integrate_cc_ocr_enrichments.py`
- `scripts/integrate_cocotext_enrichments.py`
- `scripts/integrate_cvsi_enrichments.py`
- `scripts/integrate_dibco_enrichments.py`
- `scripts/integrate_diqa_enrichments.py`
- `scripts/integrate_docalign12k_enrichments.py`
- `scripts/integrate_doclaynet_enrichments.py`
- `scripts/integrate_docreal_enrichments.py`
- `scripts/integrate_dzongkha_digits_enrichments.py`
- `scripts/integrate_financebench_enrichments.py`
- `scripts/integrate_fintabnet_enrichments.py`
- `scripts/integrate_funsd_enrichments.py`
- `scripts/integrate_funsd_plus_enrichments.py`
- `scripts/integrate_hasy_enrichments.py`
- `scripts/integrate_hiertext_enrichments.py`
- `scripts/integrate_hindi_synth_enrichments.py`
- `scripts/integrate_iam_enrichments.py`
- `scripts/integrate_im2latex_enrichments.py`
- `scripts/integrate_invoices_kg_enrichments.py`
- `scripts/integrate_jssoda_enrichments.py`
- `scripts/integrate_mathverse_enrichments.py`
- `scripts/integrate_mdiw13_enrichments.py`
- `scripts/integrate_midv500_enrichments.py`
- `scripts/integrate_mle2e_enrichments.py`
- `scripts/integrate_mlt19_enrichments.py`
- `scripts/integrate_muharaf_enrichments.py`
- `scripts/integrate_multimodal_textbook_enrichments.py`
- `scripts/integrate_nepali_handwritten_enrichments.py`
- `scripts/integrate_nist_sd19_enrichments.py`
- `scripts/integrate_nist_sd2_enrichments.py`
- `scripts/integrate_nist_sd6_enrichments.py`
- `scripts/integrate_ocr_quality_enrichments.py`
- `scripts/integrate_ohr_bench_enrichments.py`
- `scripts/integrate_omnidocbench_enrichments.py`
- `scripts/integrate_pubtabnet_enrichments.py`
- `scripts/integrate_pucit_ohul_enrichments.py`
- `scripts/integrate_realdae_enrichments.py`
- `scripts/integrate_resolution_quality.py`
- `scripts/integrate_rvl_cdip_enrichments.py`
- `scripts/integrate_sd7k_enrichments.py`
- `scripts/integrate_signatr6k_enrichments.py`
- `scripts/integrate_siw13_enrichments.py`
- `scripts/integrate_skew_orientation.py`
- `scripts/integrate_smartdoc_qa_enrichments.py`
- `scripts/integrate_sroie_enrichments.py`
- `scripts/integrate_tablebank_enrichments.py`
- `scripts/integrate_tibhcr_enrichments.py`
- `scripts/integrate_tobacco800_enrichments.py`
- `scripts/integrate_warpdoc_enrichments.py`
- `scripts/integrate_wsrd_enrichments.py`
- `scripts/integrate_yarmouk_enrichments.py`
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
- `scripts/modal_helpers.sh`
- `scripts/monitor_annotation.sh`
- `scripts/organize_dual_storage.py`
- `scripts/poc_openlid_v2.py`
- `scripts/prepare_invoice_dataset.py`
- `scripts/prepare_orientation_dataset.py`
- `scripts/process_all_datasets.py`
- `scripts/process_local_datasets_docling.py`
- `scripts/promote_to_hf.py`
- `scripts/pubtabnet_text_extractor.py`
- `scripts/resolve_pr_comments.py`
- `scripts/run_complete_dataset_workflow.sh`
- `scripts/run_language_enrichment.py`
- `scripts/run_mutation_tests.sh`
- `scripts/run_new_dataset_orchestrator.py`
- `scripts/sample_ambiguous_cases.py`
- `scripts/select_anyphotodoc_vlm_samples.py`
- `scripts/select_iqa_vlm_images.py`
- `scripts/select_natural_scan_skew_subset.py`
- `scripts/setup_cocotext_symlinks.py`
- `scripts/setup_fonts.sh`
- `scripts/smoke_test_complex_scripts.py`
- `scripts/split_dataset_catalog.py`
- `scripts/standardize_layout_labels.py`
- `scripts/test_annotation.sh`
- `scripts/test_arena_local.py`
- `scripts/test_dataset_generation.py`
- `scripts/test_escalation_comprehensive.py`
- `scripts/test_modal_arena.py`
- `scripts/triage_local_analysis.py`
- `scripts/triage_text_analysis.py`
- `scripts/update_data_locations.py`
- `scripts/upload_datasets_to_gcs.sh`
- `scripts/validate-workflows.sh`
- `scripts/validate_annotation_output.py`
- `scripts/validate_architecture_links.sh`
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

### `src/` (143 files)

- `src/image_preprocessing_detector/__init__.py`
- `src/image_preprocessing_detector/annotation/__init__.py`
- `src/image_preprocessing_detector/annotation/cli.py`
- `src/image_preprocessing_detector/annotation/config/__init__.py`
- `src/image_preprocessing_detector/annotation/config/datasets.py`
- `src/image_preprocessing_detector/annotation/config/settings.py`
- `src/image_preprocessing_detector/annotation/config/tiers.py`
- `src/image_preprocessing_detector/annotation/config/validators.py`
- `src/image_preprocessing_detector/annotation/enrichment/__init__.py`
- `src/image_preprocessing_detector/annotation/enrichment/errors.py`
- `src/image_preprocessing_detector/annotation/enrichment/manager.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/__init__.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/base.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/docling_layout.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/language_detector.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/siglip.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/simulated.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/yolo.py`
- `src/image_preprocessing_detector/annotation/integrity/__init__.py`
- `src/image_preprocessing_detector/annotation/integrity/atomic.py`
- `src/image_preprocessing_detector/annotation/integrity/checkpointing.py`
- `src/image_preprocessing_detector/annotation/integrity/hashing.py`
- `src/image_preprocessing_detector/annotation/monitoring/__init__.py`
- `src/image_preprocessing_detector/annotation/monitoring/logging.py`
- `src/image_preprocessing_detector/annotation/monitoring/metrics.py`
- `src/image_preprocessing_detector/annotation/parsers/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/base.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/anyphotodoc6300.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/docalign12k.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/docreal.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/drccbi.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/sd7k.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/staindoc.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/warpdoc.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/wsrd.py`
- `src/image_preprocessing_detector/annotation/parsers/document/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/document/document_haystack.py`
- `src/image_preprocessing_detector/annotation/parsers/document/financebench.py`
- `src/image_preprocessing_detector/annotation/parsers/document/markushgrapher.py`
- `src/image_preprocessing_detector/annotation/parsers/document/midv500.py`
- `src/image_preprocessing_detector/annotation/parsers/document/multimodal_textbook.py`
- `src/image_preprocessing_detector/annotation/parsers/document/ohr_bench.py`
- `src/image_preprocessing_detector/annotation/parsers/document/omnidocbench.py`
- `src/image_preprocessing_detector/annotation/parsers/document/realdae.py`
- `src/image_preprocessing_detector/annotation/parsers/document/rvl_cdip.py`
- `src/image_preprocessing_detector/annotation/parsers/document/tobacco800.py`
- `src/image_preprocessing_detector/annotation/parsers/formula/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py`
- `src/image_preprocessing_detector/annotation/parsers/generic.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/hasyv2.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/maths_handwriting.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/muharaf.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_db2.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd19.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd6.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/pucit_ohul.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/signatr.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/doclaynet.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/docsynth300k.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/fintabnet.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/funsd.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/funsd_plus.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/indicdlp.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/pubtabnet.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/sroie.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/tablebank.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/arabic_docs.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cc_ocr.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cocotext.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cvsi.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/hiertext.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/hindi_ocr_synthetic.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/jssoda.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mdiw13.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mle2e.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mlt19.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/multilingual_scripts.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/nepali_handwritten.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/siw13.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/synth_multiscript.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/tibhcr.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/yarmouk.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/dibco.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/diqa.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/ocr_quality.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/q_doc.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/smartdoc.py`
- `src/image_preprocessing_detector/annotation/parsers/registry.py`
- `src/image_preprocessing_detector/annotation/parsers/template.py`
- `src/image_preprocessing_detector/annotation/schemas/__init__.py`
- `src/image_preprocessing_detector/annotation/schemas/enrichment.py`
- `src/image_preprocessing_detector/annotation/schemas/enums.py`
- `src/image_preprocessing_detector/annotation/schemas/immutable.py`
- `src/image_preprocessing_detector/annotation/schemas/migrations.py`
- `src/image_preprocessing_detector/annotation/schemas/sample.py`
- `src/image_preprocessing_detector/annotation/schemas/validators.py`
- `src/image_preprocessing_detector/annotation/storage/__init__.py`
- `src/image_preprocessing_detector/annotation/storage/cache.py`
- `src/image_preprocessing_detector/annotation/storage/parquet_writer.py`
- `src/image_preprocessing_detector/annotation/workflow/__init__.py`
- `src/image_preprocessing_detector/annotation/workflow/orchestrator.py`
- `src/image_preprocessing_detector/annotation/workflow/pipeline.py`
- `src/image_preprocessing_detector/annotation/workflow/preflight.py`
- `src/image_preprocessing_detector/annotation/workflow/progress.py`
- `src/image_preprocessing_detector/annotation/workflow/scanner.py`
- `src/image_preprocessing_detector/api/__init__.py`
- `src/image_preprocessing_detector/api/routes/__init__.py`
- `src/image_preprocessing_detector/core/__init__.py`
- `src/image_preprocessing_detector/labeling/__init__.py`
- `src/image_preprocessing_detector/labeling/domain/__init__.py`
- `src/image_preprocessing_detector/labeling/domain/classifier.py`
- `src/image_preprocessing_detector/labeling/domain/config.py`
- `src/image_preprocessing_detector/labeling/domain/openrouter_client.py`
- `src/image_preprocessing_detector/labeling/domain/prompts.py`
- `src/image_preprocessing_detector/labeling/model_spec.py`
- `src/image_preprocessing_detector/logging/__init__.py`
- `src/image_preprocessing_detector/models/__init__.py`
- `src/image_preprocessing_detector/monitoring/__init__.py`
- `src/image_preprocessing_detector/orchestration/__init__.py`
- `src/image_preprocessing_detector/pipeline/__init__.py`
- `src/image_preprocessing_detector/py.typed`
- `src/image_preprocessing_detector/schema_utils/__init__.py`
- `src/image_preprocessing_detector/schema_utils/bbox_utils.py`
- `src/image_preprocessing_detector/schema_utils/dataset_source.py`
- `src/image_preprocessing_detector/schema_utils/degradation_mapping.py`
- `src/image_preprocessing_detector/schema_utils/iso_language_script.py`
- `src/image_preprocessing_detector/schema_utils/iso_paper_sizes.py`
- `src/image_preprocessing_detector/schema_utils/layout_taxonomy.py`
- `src/image_preprocessing_detector/schema_utils/openlid_integration.py`
- `src/image_preprocessing_detector/schema_utils/resolution_quality.py`
- `src/image_preprocessing_detector/schema_utils/script_ml_mapping.py`
- `src/image_preprocessing_detector/schema_utils/split_registry.py`
- `src/image_preprocessing_detector/schema_utils/text_scope.py`
- `src/image_preprocessing_detector/schema_utils/validation.py`
- `src/image_preprocessing_detector/synthetic/__init__.py`
- `src/image_preprocessing_detector/utils/__init__.py`

### `tools/` (10 files)

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

---

## GAP_B — In Inventory, NOT in Git

These entries appear in `FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md` but are **not**
git-tracked. They were likely deleted, renamed, or moved. Remove them from the inventory.

### `configs/` (2 files)

- `configs/monitoring/*.yaml`
- `configs/training/*.yaml`

### `modal/` (4 files)

- `modal/export_onnx.py`
- `modal/stage1_deqa_inference.py`
- `modal/teacher_inference.py`
- `modal/train_mobilenetv4.py`

### `src/` (17 files)

- `src/image_preprocessing_detector/datasets/iqa_dataset.py`
- `src/image_preprocessing_detector/datasets/multitask_dataset.py`
- `src/image_preprocessing_detector/detection/mobilenetv4_precorrection.py`
- `src/image_preprocessing_detector/detection/stage_gate.py`
- `src/image_preprocessing_detector/labeling/arena/utils/__init__.py`
- `src/image_preprocessing_detector/labeling/arena/utils/bootstrap.py`
- `src/image_preprocessing_detector/labeling/arena/utils/reproducibility.py`
- `src/image_preprocessing_detector/labeling/arena/utils/visualization.py`
- `src/image_preprocessing_detector/labeling/deqa/config.py`
- `src/image_preprocessing_detector/labeling/finetuning/dataset.py`
- `src/image_preprocessing_detector/models/mobilenetv4_gate.py`
- `src/image_preprocessing_detector/models/siglip2_naflex.py`
- `src/image_preprocessing_detector/routing/document_type_router.py`
- `src/image_preprocessing_detector/training/generate_soft_labels.py`
- `src/image_preprocessing_detector/training/mobilenetv4_trainer.py`
- `src/image_preprocessing_detector/training/siglip2_trainer.py`
- `src/image_preprocessing_detector/utils/logger.py`

---

## GAP_C — In Git, No PUML Reference

These git-tracked files are not referenced in any architecture diagram.
Review each to determine: (a) add a reference to the appropriate PUML diagram,
or (b) accept as undocumented (e.g., one-off scripts, migration utilities).

> **Note**: `scripts/` entries are frequently standalone utilities with no
> expected PUML reference. Focus review on `src/` first.

### `config/` (14 files)

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
- `config/siglip2_multitask.yaml`
- `config/skew_estimation.yaml`
- `config/training_criticality.yaml`

### `modal/` (5 files)

- `modal/app.py`
- `modal/shared/__init__.py`
- `modal/test_gcs.py`
- `modal/train_phase3_doclayout_yolo.py`
- `modal/train_phase6_layout_lite.py`

### `scripts/` (255 files)

- `scripts/.gitkeep`
- `scripts/README.md`
- `scripts/__init__.py`
- `scripts/_path_security.py`
- `scripts/analyze_soft_labels.py`
- `scripts/annotate_base_metadata_incremental.py`
- `scripts/annotate_base_metadata_lite.py`
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
- `scripts/audit_datasets.py`
- `scripts/audit_font_coverage.py`
- `scripts/audit_layout_labels.py`
- `scripts/audit_v3_per_script_counts.py`
- `scripts/auth_gcs.sh`
- `scripts/backfill_language_confidence.py`
- `scripts/backfill_text_quality_confidence.py`
- `scripts/benchmark_classical_skew.py`
- `scripts/benchmark_iqa_models.py`
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
- `scripts/build_orientation_real_component.py`
- `scripts/calculate_text_statistics.py`
- `scripts/check_download_progress.sh`
- `scripts/check_unresolved_pr_comments.py`
- `scripts/checkpoint_manager.py`
- `scripts/colab_utils.py`
- `scripts/collect_vlm_iqa_labels.py`
- `scripts/compare_quantization_results.py`
- `scripts/consolidate_base_images.py`
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
- `scripts/create_final_dataset.py`
- `scripts/create_sample_manifest.py`
- `scripts/create_stratified_validation.py`
- `scripts/create_symlinks.py`
- `scripts/disk_manifest.py`
- `scripts/download_all_datasets.py`
- `scripts/download_doc3d_images.py`
- `scripts/download_docbank.py`
- `scripts/download_docile.sh`
- `scripts/download_fonts.sh`
- `scripts/download_fonts_v2.sh`
- `scripts/download_multilingual_script_datasets.py`
- `scripts/download_multimodal_textbook.py`
- `scripts/download_ocr_quality_images.py`
- `scripts/download_phase3_datasets.py`
- `scripts/download_table_datasets.py`
- `scripts/download_vidore_finance.py`
- `scripts/enrich_docalign12k_p0.py`
- `scripts/enrich_docalign12k_p1.py`
- `scripts/enrich_language.py`
- `scripts/enrich_language_from_gt.py`
- `scripts/enrich_mlt19_language.py`
- `scripts/extract_doclaynet_gt_index.py`
- `scripts/extract_indicdlp_images.py`
- `scripts/extract_markushgrapher_images.py`
- `scripts/extract_test_fixtures.py`
- `scripts/extract_vidore_labels.py`
- `scripts/extract_wili_samples.py`
- `scripts/extract_workstream_loc.sh`
- `scripts/fetch_sonarcloud_issues.py`
- `scripts/fix_docling_bboxes.py`
- `scripts/gcs_helpers.sh`
- `scripts/gdrive_sync.py`
- `scripts/generate_base_dataset_v3.py`
- `scripts/generate_code_detection_dataset.py`
- `scripts/generate_combined_classification_labels.py`
- `scripts/generate_dataset_parallel.py`
- `scripts/generate_dataset_status.py`
- `scripts/generate_document_classification_labels.py`
- `scripts/generate_dqs_routing_matrix.py`
- `scripts/generate_hiertext_contact_sheets.py`
- `scripts/generate_mlt19_validation_sheets.py`
- `scripts/generate_multitask_labels.py`
- `scripts/generate_orientation_dataset.py`
- `scripts/generate_parasitic_content_labels.py`
- `scripts/generate_pubtabnet_contact_sheets.py`
- `scripts/generate_rag_pipeline_visual.py`
- `scripts/generate_vertical_text_labels.py`
- `scripts/install_fonts.sh`
- `scripts/integrate_anyphotodoc6300_enrichments.py`
- `scripts/integrate_arabic_docs_ocr_enrichments.py`
- `scripts/integrate_bhutan_afs_enrichments.py`
- `scripts/integrate_cc_ocr_enrichments.py`
- `scripts/integrate_cocotext_enrichments.py`
- `scripts/integrate_cvsi_enrichments.py`
- `scripts/integrate_dibco_enrichments.py`
- `scripts/integrate_diqa_enrichments.py`
- `scripts/integrate_docalign12k_enrichments.py`
- `scripts/integrate_doclaynet_enrichments.py`
- `scripts/integrate_docreal_enrichments.py`
- `scripts/integrate_dzongkha_digits_enrichments.py`
- `scripts/integrate_financebench_enrichments.py`
- `scripts/integrate_fintabnet_enrichments.py`
- `scripts/integrate_funsd_enrichments.py`
- `scripts/integrate_funsd_plus_enrichments.py`
- `scripts/integrate_hasy_enrichments.py`
- `scripts/integrate_hiertext_enrichments.py`
- `scripts/integrate_hindi_synth_enrichments.py`
- `scripts/integrate_iam_enrichments.py`
- `scripts/integrate_im2latex_enrichments.py`
- `scripts/integrate_invoices_kg_enrichments.py`
- `scripts/integrate_jssoda_enrichments.py`
- `scripts/integrate_mathverse_enrichments.py`
- `scripts/integrate_mdiw13_enrichments.py`
- `scripts/integrate_midv500_enrichments.py`
- `scripts/integrate_mle2e_enrichments.py`
- `scripts/integrate_mlt19_enrichments.py`
- `scripts/integrate_muharaf_enrichments.py`
- `scripts/integrate_multimodal_textbook_enrichments.py`
- `scripts/integrate_nepali_handwritten_enrichments.py`
- `scripts/integrate_nist_sd19_enrichments.py`
- `scripts/integrate_nist_sd2_enrichments.py`
- `scripts/integrate_nist_sd6_enrichments.py`
- `scripts/integrate_ocr_quality_enrichments.py`
- `scripts/integrate_ohr_bench_enrichments.py`
- `scripts/integrate_omnidocbench_enrichments.py`
- `scripts/integrate_pubtabnet_enrichments.py`
- `scripts/integrate_pucit_ohul_enrichments.py`
- `scripts/integrate_realdae_enrichments.py`
- `scripts/integrate_rvl_cdip_enrichments.py`
- `scripts/integrate_sd7k_enrichments.py`
- `scripts/integrate_signatr6k_enrichments.py`
- `scripts/integrate_siw13_enrichments.py`
- `scripts/integrate_smartdoc_qa_enrichments.py`
- `scripts/integrate_sroie_enrichments.py`
- `scripts/integrate_tablebank_enrichments.py`
- `scripts/integrate_tibhcr_enrichments.py`
- `scripts/integrate_tobacco800_enrichments.py`
- `scripts/integrate_warpdoc_enrichments.py`
- `scripts/integrate_wsrd_enrichments.py`
- `scripts/integrate_yarmouk_enrichments.py`
- `scripts/l2_integration_utils.py`
- `scripts/language_escalation.py`
- `scripts/mdiw13_groundtruth_mapper.py`
- `scripts/measure_dataset_sufficiency.py`
- `scripts/merge_skew_datasets.py`
- `scripts/metadata_completeness_report.py`
- `scripts/migrate_layer2_schema_to_full.py`
- `scripts/modal_helpers.sh`
- `scripts/monitor_annotation.sh`
- `scripts/organize_dual_storage.py`
- `scripts/poc_openlid_v2.py`
- `scripts/prepare_invoice_dataset.py`
- `scripts/prepare_orientation_dataset.py`
- `scripts/process_all_datasets.py`
- `scripts/process_local_datasets_docling.py`
- `scripts/promote_to_hf.py`
- `scripts/pubtabnet_text_extractor.py`
- `scripts/resolve_pr_comments.py`
- `scripts/run_complete_dataset_workflow.sh`
- `scripts/run_language_enrichment.py`
- `scripts/run_mutation_tests.sh`
- `scripts/run_new_dataset_orchestrator.py`
- `scripts/sample_ambiguous_cases.py`
- `scripts/select_anyphotodoc_vlm_samples.py`
- `scripts/select_iqa_vlm_images.py`
- `scripts/select_natural_scan_skew_subset.py`
- `scripts/setup_cocotext_symlinks.py`
- `scripts/setup_fonts.sh`
- `scripts/smoke_test_complex_scripts.py`
- `scripts/split_dataset_catalog.py`
- `scripts/standardize_layout_labels.py`
- `scripts/test_annotation.sh`
- `scripts/test_arena_local.py`
- `scripts/test_dataset_generation.py`
- `scripts/test_escalation_comprehensive.py`
- `scripts/test_modal_arena.py`
- `scripts/triage_local_analysis.py`
- `scripts/triage_text_analysis.py`
- `scripts/update_data_locations.py`
- `scripts/upload_datasets_to_gcs.sh`
- `scripts/validate-workflows.sh`
- `scripts/validate_annotation_output.py`
- `scripts/validate_architecture_links.sh`
- `scripts/validate_base_dataset_v3.py`
- `scripts/validate_datasets.py`
- `scripts/validate_dqs_correlation.py`
- `scripts/validate_language_detection.py`
- `scripts/validate_layout_lite.py`
- `scripts/validate_openlid_mlt19.py`
- `scripts/validate_pdf_classification.py`
- `scripts/validate_pdf_resolution.py`
- `scripts/verify_fintabnet_samples.py`
- `scripts/visualize_risk_distribution.py`
- `scripts/weak_supervision_labeling.py`

### `src/` (169 files)

- `src/image_preprocessing_detector/__init__.py`
- `src/image_preprocessing_detector/annotation/__init__.py`
- `src/image_preprocessing_detector/annotation/cli.py`
- `src/image_preprocessing_detector/annotation/config/__init__.py`
- `src/image_preprocessing_detector/annotation/config/datasets.py`
- `src/image_preprocessing_detector/annotation/config/settings.py`
- `src/image_preprocessing_detector/annotation/config/tiers.py`
- `src/image_preprocessing_detector/annotation/config/validators.py`
- `src/image_preprocessing_detector/annotation/enrichment/__init__.py`
- `src/image_preprocessing_detector/annotation/enrichment/errors.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/__init__.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/base.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/language_detector.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/simulated.py`
- `src/image_preprocessing_detector/annotation/enrichment/providers/yolo.py`
- `src/image_preprocessing_detector/annotation/integrity/__init__.py`
- `src/image_preprocessing_detector/annotation/integrity/atomic.py`
- `src/image_preprocessing_detector/annotation/integrity/checkpointing.py`
- `src/image_preprocessing_detector/annotation/integrity/hashing.py`
- `src/image_preprocessing_detector/annotation/monitoring/__init__.py`
- `src/image_preprocessing_detector/annotation/monitoring/logging.py`
- `src/image_preprocessing_detector/annotation/parsers/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/anyphotodoc6300.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/docalign12k.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/docreal.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/drccbi.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/sd7k.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/staindoc.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/warpdoc.py`
- `src/image_preprocessing_detector/annotation/parsers/correction/wsrd.py`
- `src/image_preprocessing_detector/annotation/parsers/document/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/document/document_haystack.py`
- `src/image_preprocessing_detector/annotation/parsers/document/financebench.py`
- `src/image_preprocessing_detector/annotation/parsers/document/markushgrapher.py`
- `src/image_preprocessing_detector/annotation/parsers/document/midv500.py`
- `src/image_preprocessing_detector/annotation/parsers/document/multimodal_textbook.py`
- `src/image_preprocessing_detector/annotation/parsers/document/ohr_bench.py`
- `src/image_preprocessing_detector/annotation/parsers/document/omnidocbench.py`
- `src/image_preprocessing_detector/annotation/parsers/document/realdae.py`
- `src/image_preprocessing_detector/annotation/parsers/document/rvl_cdip.py`
- `src/image_preprocessing_detector/annotation/parsers/document/tobacco800.py`
- `src/image_preprocessing_detector/annotation/parsers/formula/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py`
- `src/image_preprocessing_detector/annotation/parsers/generic.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/hasyv2.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/maths_handwriting.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/muharaf.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_db2.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd19.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd6.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/pucit_ohul.py`
- `src/image_preprocessing_detector/annotation/parsers/handwriting/signatr.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/doclaynet.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/docsynth300k.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/fintabnet.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/funsd.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/funsd_plus.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/indicdlp.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/pubtabnet.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/sroie.py`
- `src/image_preprocessing_detector/annotation/parsers/layout/tablebank.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/arabic_docs.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cc_ocr.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cocotext.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/cvsi.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/hiertext.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/hindi_ocr_synthetic.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/jssoda.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mdiw13.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mle2e.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/mlt19.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/multilingual_scripts.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/nepali_handwritten.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/siw13.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/synth_multiscript.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/tibhcr.py`
- `src/image_preprocessing_detector/annotation/parsers/multilingual/yarmouk.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/__init__.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/dibco.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/diqa.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/ocr_quality.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/q_doc.py`
- `src/image_preprocessing_detector/annotation/parsers/quality/smartdoc.py`
- `src/image_preprocessing_detector/annotation/parsers/registry.py`
- `src/image_preprocessing_detector/annotation/parsers/template.py`
- `src/image_preprocessing_detector/annotation/schemas/__init__.py`
- `src/image_preprocessing_detector/annotation/schemas/enums.py`
- `src/image_preprocessing_detector/annotation/schemas/migrations.py`
- `src/image_preprocessing_detector/annotation/schemas/sample.py`
- `src/image_preprocessing_detector/annotation/schemas/validators.py`
- `src/image_preprocessing_detector/annotation/storage/__init__.py`
- `src/image_preprocessing_detector/annotation/storage/cache.py`
- `src/image_preprocessing_detector/annotation/storage/parquet_writer.py`
- `src/image_preprocessing_detector/annotation/workflow/__init__.py`
- `src/image_preprocessing_detector/annotation/workflow/progress.py`
- `src/image_preprocessing_detector/api/__init__.py`
- `src/image_preprocessing_detector/api/models.py`
- `src/image_preprocessing_detector/api/routes/__init__.py`
- `src/image_preprocessing_detector/classification/degradation_classifier.py`
- `src/image_preprocessing_detector/classification/document_source_classifier.py`
- `src/image_preprocessing_detector/classification/text_layer_analyzer.py`
- `src/image_preprocessing_detector/cli_layout.py`
- `src/image_preprocessing_detector/core/__init__.py`
- `src/image_preprocessing_detector/core/config.py`
- `src/image_preprocessing_detector/core/exceptions.py`
- `src/image_preprocessing_detector/detection/blank_page_detector.py`
- `src/image_preprocessing_detector/detection/code_detector.py`
- `src/image_preprocessing_detector/detection/deskew_pipeline.py`
- `src/image_preprocessing_detector/detection/handwriting_detector.py`
- `src/image_preprocessing_detector/detection/hybrid_iqa.py`
- `src/image_preprocessing_detector/detection/script_detector.py`
- `src/image_preprocessing_detector/detection/shadow_detector.py`
- `src/image_preprocessing_detector/detection/table_complexity.py`
- `src/image_preprocessing_detector/detection/warping_detector.py`
- `src/image_preprocessing_detector/labeling/__init__.py`
- `src/image_preprocessing_detector/labeling/arena/__init__.py`
- `src/image_preprocessing_detector/labeling/arena/cli.py`
- `src/image_preprocessing_detector/labeling/arena/datasets/__init__.py`
- `src/image_preprocessing_detector/labeling/arena/datasets/base.py`
- `src/image_preprocessing_detector/labeling/arena/inference/__init__.py`
- `src/image_preprocessing_detector/labeling/arena/inference/base.py`
- `src/image_preprocessing_detector/labeling/arena/inference/huggingface.py`
- `src/image_preprocessing_detector/labeling/arena/inference/regression.py`
- `src/image_preprocessing_detector/labeling/arena/modal_client.py`
- `src/image_preprocessing_detector/labeling/domain/__init__.py`
- `src/image_preprocessing_detector/logging/__init__.py`
- `src/image_preprocessing_detector/logging/errors.py`
- `src/image_preprocessing_detector/logging/outcomes.py`
- `src/image_preprocessing_detector/metrics/calibration.py`
- `src/image_preprocessing_detector/models/__init__.py`
- `src/image_preprocessing_detector/models/onnx_runtime.py`
- `src/image_preprocessing_detector/monitoring/__init__.py`
- `src/image_preprocessing_detector/orchestration/__init__.py`
- `src/image_preprocessing_detector/pipeline/__init__.py`
- `src/image_preprocessing_detector/py.typed`
- `src/image_preprocessing_detector/routing/psm_recommender.py`
- `src/image_preprocessing_detector/routing/script_router.py`
- `src/image_preprocessing_detector/schema_utils/__init__.py`
- `src/image_preprocessing_detector/schema_utils/bbox_utils.py`
- `src/image_preprocessing_detector/schema_utils/dataset_source.py`
- `src/image_preprocessing_detector/schema_utils/degradation_mapping.py`
- `src/image_preprocessing_detector/schema_utils/iso_language_script.py`
- `src/image_preprocessing_detector/schema_utils/iso_paper_sizes.py`
- `src/image_preprocessing_detector/schema_utils/layout_taxonomy.py`
- `src/image_preprocessing_detector/schema_utils/openlid_integration.py`
- `src/image_preprocessing_detector/schema_utils/script_ml_mapping.py`
- `src/image_preprocessing_detector/schema_utils/split_registry.py`
- `src/image_preprocessing_detector/schema_utils/text_scope.py`
- `src/image_preprocessing_detector/schema_utils/validation.py`
- `src/image_preprocessing_detector/synthetic/__init__.py`
- `src/image_preprocessing_detector/synthetic/augmentation.py`
- `src/image_preprocessing_detector/synthetic/augmentation_fast.py`
- `src/image_preprocessing_detector/synthetic/corpus.py`
- `src/image_preprocessing_detector/synthetic/fonts.py`
- `src/image_preprocessing_detector/synthetic/renderer.py`
- `src/image_preprocessing_detector/synthetic/validation.py`
- `src/image_preprocessing_detector/utils/__init__.py`
- `src/image_preprocessing_detector/utils/datetime_compat.py`
- `src/image_preprocessing_detector/utils/log_config.py`
- `src/image_preprocessing_detector/utils/metadata_generator.py`
- `src/image_preprocessing_detector/utils/model_config.py`
- `src/image_preprocessing_detector/utils/path_security.py`
- `src/image_preprocessing_detector/utils/tensor_cache.py`

### `tools/` (10 files)

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

---

## GAP_D — PUML References NOT in Git

These paths appear in PUML diagram notes but are **not** git-tracked.
Files marked `(planned)` or `(estimated)` in the PUML are **excluded** from this list.
Fix by: (a) removing the reference if the file was deleted, or (b) creating the file.

### `docs/architecture/diagrams/level-1/PREPARE_DOC_WORKFLOW_HIERARCHY.puml`

- `modal/arena_benchmark.py` (raw: `modal/arena_benchmark.py`)
- `modal/generate_pseudo_labels.py` (raw: `modal/generate_pseudo_labels.py`)
- `modal/train_mobilenetv4_precorrection.py` (raw: `modal/train_mobilenetv4_precorrection.py`)
- `modal/export_phase7_onnx.py` (raw: `modal/export_phase7_onnx.py`)
- `modal/train_docling_layout.py` (raw: `modal/train_docling_layout.py`)
- `src/image_preprocessing_detector/models/model_optimizer.py` (raw: `src/.../models/model_optimizer.py`)
- `src/image_preprocessing_detector/routing/document_type_router.py` (raw: `src/.../routing/document_type_router.py`)
- `src/image_preprocessing_detector/ingestion/format_normalizer.py` (raw: `src/.../ingestion/format_normalizer.py`)

### `docs/architecture/diagrams/level-2/data-preparation/prepare-doc-compound-distortion-augmentation.puml`

- `scripts/generate_compound_distortion_dataset.py` (raw: `scripts/generate_compound_distortion_dataset.py`)
- `scripts/compute_compound_labels.py` (raw: `scripts/compute_compound_labels.py`)

### `docs/architecture/diagrams/level-2/data-preparation/stream-4e-handwriting-dataset.puml`

- `scripts/label_handwriting_quality.py` (raw: `scripts/label_handwriting_quality.py`)
- `scripts/audit_class_balance.py` (raw: `scripts/audit_class_balance.py`)

### `docs/architecture/diagrams/level-2/model-arena/model-arena-architecture.puml`

- `src/image_preprocessing_detector/arena/runner.py` (raw: `src/.../arena/runner.py`)
- `src/image_preprocessing_detector/arena/datasets/base.py` (raw: `src/.../arena/datasets/base.py`)
- `src/image_preprocessing_detector/arena/datasets/diqa5000.py` (raw: `src/.../arena/datasets/diqa5000.py`)
- `src/image_preprocessing_detector/arena/metrics.py` (raw: `src/.../arena/metrics.py`)
- `src/image_preprocessing_detector/arena/schemas.py` (raw: `src/.../arena/schemas.py`)
- `src/image_preprocessing_detector/arena/leaderboard.py` (raw: `src/.../arena/leaderboard.py`)
- `src/image_preprocessing_detector/arena/cli.py` (raw: `src/.../arena/cli.py`)

### `docs/architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-test-coverage.puml`

- `modal/train_phase2_iqa.py` (raw: `modal/train_phase2_iqa.py`)

### `docs/architecture/diagrams/level-2/model-training/stream-4d-mobilenetv4-integration.puml`

- `src/image_preprocessing_detector/detection/mobilenetv4_precorrection.py` (raw: `src/detection/mobilenetv4_precorrection.py`)
- `src/image_preprocessing_detector/detection/stage_gate.py` (raw: `src/detection/stage_gate.py`)
- `modal/export_onnx.py` (raw: `modal/export_onnx.py`)

### `docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.puml`

- `src/image_preprocessing_detector/detection/layout_lite.py` (raw: `src/detection/layout_lite.py`)

### `docs/architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.puml`

- `modal/train_student_distillation.py` (raw: `modal/train_student_distillation.py`)

### `docs/architecture/diagrams/level-3/pseudo-labeling/pseudo-labeling-swimlane.puml`

- `modal/stage1_deqa_inference.py` (raw: `modal/stage1_deqa_inference.py`)
- `modal/teacher_inference.py` (raw: `modal/teacher_inference.py`)

---

## Triage Guidance

| Action | Gap | Steps |
|--------|-----|-------|
| Assign to workstream | GAP_A | Open `FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`, find the correct WS section, add a table row |
| Mark as excluded | GAP_A | Add to the `Intentionally Excluded Directories` table in the inventory |
| Remove stale entry | GAP_B | Delete the table row from the inventory; check if any PUML also references it (→ GAP_D) |
| Add PUML reference | GAP_C | In the appropriate diagram's note block, add a bullet: `- src/.../module/file.py (N lines)` |
| Fix broken PUML ref | GAP_D | Update the path to the file's new location, or remove the note entirely |

_Re-run this script after making changes to verify gaps are closed._
