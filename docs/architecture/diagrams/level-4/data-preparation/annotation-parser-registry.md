---
owner: docs-team
title: 'Level 4: Annotation Parser Registry'
l4_category: parser
l4_generated: auto
l4_generator: scripts/generate_level4_registries.py
l4_last_generated: 2026-02-23
tags:
- architecture
- level_4
- registry
---

# Level 4: Annotation Parser Registry

> **Auto-generated** — do not edit manually. Regenerate with:
> `python scripts/generate_level4_registries.py --category parser`

Total: 59 dataset parsers across 7 task categories.

## Layout Parsers (10 datasets)

| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |
| ------- | ----------- | ---------------- | ---------------- | ------ |
| [doclaynet](../../../datasets/source/doclaynet.md) | `src/image_preprocessing_detector/annotation/parsers/layout/doclaynet.py` | `scripts/integrate_doclaynet_enrichments.py` | `doclaynet_metadata.json` | ✅ |
| [docsynth](../../../datasets/source/docsynth.md) | `src/image_preprocessing_detector/annotation/parsers/layout/docsynth300k.py` | — | `docsynth_metadata.json` | ✅ |
| [fintabnet](../../../datasets/source/fintabnet.md) | `src/image_preprocessing_detector/annotation/parsers/layout/fintabnet.py` | `scripts/integrate_fintabnet_enrichments.py` | `fintabnet_metadata.json` | ✅ |
| [funsd](../../../datasets/source/funsd.md) | `src/image_preprocessing_detector/annotation/parsers/layout/funsd.py` | `scripts/integrate_funsd_enrichments.py` | `funsd_metadata.json` | ✅ |
| [funsd-plus](../../../datasets/source/funsd-plus.md) | `src/image_preprocessing_detector/annotation/parsers/layout/funsd_plus.py` | `scripts/integrate_funsd_plus_enrichments.py` | `funsd_plus_metadata.json` | ✅ |
| [indicdlp](../../../datasets/source/indicdlp.md) | `src/image_preprocessing_detector/annotation/parsers/layout/indicdlp.py` | — | `indicdlp_metadata.json` | ✅ |
| [invoices-kg](../../../datasets/source/invoices-kg.md) | `src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py` | `scripts/integrate_invoices_kg_enrichments.py` | `invoices_kg_metadata.json` | ✅ |
| [pubtabnet](../../../datasets/source/pubtabnet.md) | `src/image_preprocessing_detector/annotation/parsers/layout/pubtabnet.py` | `scripts/integrate_pubtabnet_enrichments.py` | `pubtabnet_metadata.json` | ✅ |
| [sroie](../../../datasets/source/sroie.md) | `src/image_preprocessing_detector/annotation/parsers/layout/sroie.py` | `scripts/integrate_sroie_enrichments.py` | `sroie_metadata.json` | ✅ |
| [tablebank](../../../datasets/source/tablebank.md) | `src/image_preprocessing_detector/annotation/parsers/layout/tablebank.py` | `scripts/integrate_tablebank_enrichments.py` | `tablebank_metadata.json` | ✅ |

## Quality Parsers (5 datasets)

| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |
| ------- | ----------- | ---------------- | ---------------- | ------ |
| [dibco](../../../datasets/source/dibco.md) | `src/image_preprocessing_detector/annotation/parsers/quality/dibco.py` | `scripts/integrate_dibco_enrichments.py` | `dibco_metadata.json` | ✅ |
| [diqa-5000](../../../datasets/source/diqa-5000.md) | `src/image_preprocessing_detector/annotation/parsers/quality/diqa.py` | `scripts/integrate_diqa_enrichments.py` | `diqa_metadata.json` | ✅ |
| [ocr-quality](../../../datasets/source/ocr-quality.md) | `src/image_preprocessing_detector/annotation/parsers/quality/ocr_quality.py` | `scripts/integrate_ocr_quality_enrichments.py` | `ocr_quality_metadata.json` | ✅ |
| [q-doc](../../../datasets/source/q-doc.md) | `src/image_preprocessing_detector/annotation/parsers/quality/q_doc.py` | — | `q_doc_metadata.json` | ✅ |
| [smartdoc-qa](../../../datasets/source/smartdoc-qa.md) | `src/image_preprocessing_detector/annotation/parsers/quality/smartdoc.py` | `scripts/integrate_smartdoc_qa_enrichments.py` | `smartdoc_qa_metadata.json` | ✅ |

## Correction Parsers (8 datasets)

| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |
| ------- | ----------- | ---------------- | ---------------- | ------ |
| [anyphotodoc6300](../../../datasets/source/anyphotodoc6300.md) | `src/image_preprocessing_detector/annotation/parsers/correction/anyphotodoc6300.py` | `scripts/integrate_anyphotodoc6300_enrichments.py` | `anyphotodoc6300_metadata.json` | ✅ |
| [docalign12k](../../../datasets/source/docalign12k.md) | `src/image_preprocessing_detector/annotation/parsers/correction/docalign12k.py` | `scripts/integrate_docalign12k_enrichments.py` | `docalign12k_metadata.json` | ✅ |
| [docreal](../../../datasets/source/docreal.md) | `src/image_preprocessing_detector/annotation/parsers/correction/docreal.py` | `scripts/integrate_docreal_enrichments.py` | `docreal_metadata.json` | ✅ |
| [drccbi](../../../datasets/source/drccbi.md) | `src/image_preprocessing_detector/annotation/parsers/correction/drccbi.py` | — | `drccbi_metadata.json` | ✅ |
| [sd7k](../../../datasets/source/sd7k.md) | `src/image_preprocessing_detector/annotation/parsers/correction/sd7k.py` | `scripts/integrate_sd7k_enrichments.py` | `sd7k_metadata.json` | ✅ |
| [staindoc](../../../datasets/source/staindoc.md) | `src/image_preprocessing_detector/annotation/parsers/correction/staindoc.py` | — | `staindoc_metadata.json` | ✅ |
| [warpdoc](../../../datasets/source/warpdoc.md) | `src/image_preprocessing_detector/annotation/parsers/correction/warpdoc.py` | `scripts/integrate_warpdoc_enrichments.py` | `warpdoc_metadata.json` | ✅ |
| [wsrd](../../../datasets/source/wsrd.md) | `src/image_preprocessing_detector/annotation/parsers/correction/wsrd.py` | `scripts/integrate_wsrd_enrichments.py` | `wsrd_metadata.json` | ✅ |

## Handwriting Parsers (9 datasets)

| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |
| ------- | ----------- | ---------------- | ---------------- | ------ |
| [hasy](../../../datasets/source/hasy.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/hasyv2.py` | `scripts/integrate_hasy_enrichments.py` | `hasy_metadata.json` | ✅ |
| [iam](../../../datasets/source/iam.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py` | `scripts/integrate_iam_enrichments.py` | `iam_metadata.json` | ✅ |
| [mathverse](../../../datasets/source/mathverse.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/maths_handwriting.py` | `scripts/integrate_mathverse_enrichments.py` | `mathverse_metadata.json` | ✅ |
| [muharaf](../../../datasets/source/muharaf.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/muharaf.py` | `scripts/integrate_muharaf_enrichments.py` | `muharaf_metadata.json` | ✅ |
| [nist-sd19](../../../datasets/source/nist-sd19.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd19.py` | `scripts/integrate_nist_sd19_enrichments.py` | `nist_sd19_metadata.json` | ✅ |
| [nist-sd2](../../../datasets/source/nist-sd2.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_db2.py` | `scripts/integrate_nist_sd2_enrichments.py` | `nist_sd2_metadata.json` | ✅ |
| [nist-sd6](../../../datasets/source/nist-sd6.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd6.py` | `scripts/integrate_nist_sd6_enrichments.py` | `nist_sd6_metadata.json` | ✅ |
| [pucit-ohul](../../../datasets/source/pucit-ohul.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/pucit_ohul.py` | `scripts/integrate_pucit_ohul_enrichments.py` | `pucit_ohul_metadata.json` | ✅ |
| [signatr6k](../../../datasets/source/signatr6k.md) | `src/image_preprocessing_detector/annotation/parsers/handwriting/signatr.py` | `scripts/integrate_signatr6k_enrichments.py` | `signatr6k_metadata.json` | ✅ |

## Multilingual Parsers (16 datasets)

| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |
| ------- | ----------- | ---------------- | ---------------- | ------ |
| [arabic-docs](../../../datasets/source/arabic-docs.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/arabic_docs.py` | `scripts/integrate_arabic_docs_ocr_enrichments.py` | `arabic_docs_metadata.json` | ✅ |
| [cc-ocr](../../../datasets/source/cc-ocr.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/cc_ocr.py` | `scripts/integrate_cc_ocr_enrichments.py` | `cc_ocr_metadata.json` | ✅ |
| `coco-text` | `src/image_preprocessing_detector/annotation/parsers/multilingual/cocotext.py` | `scripts/integrate_cocotext_enrichments.py` | `cocotext_metadata.json` | ✅ |
| [cvsi](../../../datasets/source/cvsi.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/cvsi.py` | `scripts/integrate_cvsi_enrichments.py` | `cvsi_metadata.json` | ✅ |
| [hiertext](../../../datasets/source/hiertext.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/hiertext.py` | `scripts/integrate_hiertext_enrichments.py` | `hiertext_metadata.json` | ✅ |
| [hindi-synth](../../../datasets/source/hindi-synth.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/hindi_ocr_synthetic.py` | `scripts/integrate_hindi_synth_enrichments.py` | `hindi_synth_metadata.json` | ✅ |
| [jssoda](../../../datasets/source/jssoda.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/jssoda.py` | `scripts/integrate_jssoda_enrichments.py` | `jssoda_metadata.json` | ✅ |
| [mdiw13](../../../datasets/source/mdiw13.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/mdiw13.py` | `scripts/integrate_mdiw13_enrichments.py` | `mdiw13_metadata.json` | ✅ |
| [mle2e](../../../datasets/source/mle2e.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/mle2e.py` | `scripts/integrate_mle2e_enrichments.py` | `mle2e_metadata.json` | ✅ |
| [mlt19](../../../datasets/source/mlt19.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/mlt19.py` | `scripts/integrate_mlt19_enrichments.py` | `mlt19_metadata.json` | ✅ |
| `multilingual-scripts` | `src/image_preprocessing_detector/annotation/parsers/multilingual/multilingual_scripts.py` | — | `multilingual_scripts_metadata.json` | ✅ |
| [nepali-handwritten](../../../datasets/source/nepali-handwritten.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/nepali_handwritten.py` | `scripts/integrate_nepali_handwritten_enrichments.py` | `nepali_handwritten_metadata.json` | ✅ |
| [siw13](../../../datasets/source/siw13.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/siw13.py` | `scripts/integrate_siw13_enrichments.py` | `siw13_metadata.json` | ✅ |
| `synth-multiscript-v3` | `src/image_preprocessing_detector/annotation/parsers/multilingual/synth_multiscript.py` | — | `synth_multiscript_v3_metadata.json` | ✅ |
| [tibhcr](../../../datasets/source/tibhcr.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/tibhcr.py` | `scripts/integrate_tibhcr_enrichments.py` | `tibhcr_metadata.json` | ✅ |
| [yarmouk](../../../datasets/source/yarmouk.md) | `src/image_preprocessing_detector/annotation/parsers/multilingual/yarmouk.py` | `scripts/integrate_yarmouk_enrichments.py` | `yarmouk_metadata.json` | ✅ |

## Document Parsers (10 datasets)

| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |
| ------- | ----------- | ---------------- | ---------------- | ------ |
| [document-haystack](../../../datasets/source/document-haystack.md) | `src/image_preprocessing_detector/annotation/parsers/document/document_haystack.py` | — | `document_haystack_metadata.json` | ✅ |
| [financebench](../../../datasets/source/financebench.md) | `src/image_preprocessing_detector/annotation/parsers/document/financebench.py` | `scripts/integrate_financebench_enrichments.py` | `financebench_metadata.json` | ✅ |
| [markushgrapher](../../../datasets/source/markushgrapher.md) | `src/image_preprocessing_detector/annotation/parsers/document/markushgrapher.py` | — | `markushgrapher_metadata.json` | ✅ |
| [midv500](../../../datasets/source/midv500.md) | `src/image_preprocessing_detector/annotation/parsers/document/midv500.py` | `scripts/integrate_midv500_enrichments.py` | `midv500_metadata.json` | ✅ |
| [multimodal-textbook](../../../datasets/source/multimodal-textbook.md) | `src/image_preprocessing_detector/annotation/parsers/document/multimodal_textbook.py` | `scripts/integrate_multimodal_textbook_enrichments.py` | `multimodal_textbook_metadata.json` | ✅ |
| [ohr-bench](../../../datasets/source/ohr-bench.md) | `src/image_preprocessing_detector/annotation/parsers/document/ohr_bench.py` | `scripts/integrate_ohr_bench_enrichments.py` | `ohr_bench_metadata.json` | ✅ |
| [omnidocbench](../../../datasets/source/omnidocbench.md) | `src/image_preprocessing_detector/annotation/parsers/document/omnidocbench.py` | `scripts/integrate_omnidocbench_enrichments.py` | `omnidocbench_metadata.json` | ✅ |
| [realdae](../../../datasets/source/realdae.md) | `src/image_preprocessing_detector/annotation/parsers/document/realdae.py` | `scripts/integrate_realdae_enrichments.py` | `realdae_metadata.json` | ✅ |
| [rvl-cdip](../../../datasets/source/rvl-cdip.md) | `src/image_preprocessing_detector/annotation/parsers/document/rvl_cdip.py` | `scripts/integrate_rvl_cdip_enrichments.py` | `rvl_cdip_metadata.json` | ✅ |
| [tobacco800](../../../datasets/source/tobacco800.md) | `src/image_preprocessing_detector/annotation/parsers/document/tobacco800.py` | `scripts/integrate_tobacco800_enrichments.py` | `tobacco800_metadata.json` | ✅ |

## Formula Parsers (1 datasets)

| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |
| ------- | ----------- | ---------------- | ---------------- | ------ |
| [im2latex](../../../datasets/source/im2latex.md) | `src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py` | `scripts/integrate_im2latex_enrichments.py` | `im2latex_metadata.json` | ✅ |
