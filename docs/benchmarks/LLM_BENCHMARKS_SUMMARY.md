# Benchmarks Reviewed: Short Descriptions

> **Purpose**: Handoff brief for a session reviewing LLM/VLM benchmarks relevant to this project.
> **Sources**: `docs/datasets/indices/BENCHMARKS.md`, `docs/datasets/source/*.md`,
> `docs/benchmarks/DEQA_METHODOLOGY_COMPARISON.md`, `docs/planning/CROSS_MODEL_AGREEMENT_SYSTEM.md`
> **Compiled**: 2026-09-28

## Benchmarks that evaluate LLMs / VLMs or LLM-driven pipelines

| Benchmark | Size | License | What it measures | How this project uses it |
|-----------|------|---------|------------------|--------------------------|
| **OHR-Bench** (OpenDataLab, ICCV 2025) | 8,561 pages, 1,261 PDFs, 7 domains, 8,498 Q&As | CC-BY-4.0 (treated as research-only) | How OCR errors propagate into RAG: retrieval and LLM answer quality on clean vs. OCR-noised text | Benchmark only (`training_suitable: false`). Born-digital, so it has little value for degradation training. Used as a target for VLM quality labeling and QualiCLIP evaluation. |
| **OmniDocBench** (CVPR 2025) | 1,355 pages, 9 document types | Data is research-only; code is Apache-2.0 | End-to-end PDF parsing (text, tables, formulas, layout, reading order) for pipeline tools and VLMs, scored per task and per page attribute | Benchmark only. Has a label map to DocLayNet classes (`benchmarks/labelmaps/omnidoc_to_doclaynet.yaml`). Pages are born-digital and the OCR noise is synthetic. |
| **CC-OCR** (Alibaba/Qwen) | 7,058 images (6,533 downloadable), 39 subsets, 4 tracks | MIT | OCR ability of large multimodal models: multi-scene text, multilingual (CJK-heavy) text, document parsing, key information extraction | Listed as benchmark-only for CJK and complex scripts. ⚠️ Its source file says `training_suitable: true`, which contradicts that. |
| **Document Haystack** (Amazon Science) | 400 long documents, 8,250 queries | CC-BY-NC-4.0 | Long-context retrieval by VLMs: finding "needle" facts (text or image) placed in multi-page documents | Benchmark only. Has no IQA relevance; it's here for the downstream RAG and retrieval side. |
| **FinanceBench** (Patronus AI) | 368 SEC filings (54,120 PNG pages), 150 open Q&As | CC-BY-NC-4.0 | Financial question answering with LLMs and RAG, with evidence citations | Used as a page-image source (`training_suitable: true`). The source file warns that it may be in LLM training data, so it is a contamination risk for evaluation. |
| **OCRBench** | — (external) | — | OCR skills of multimodal LLMs | Cited only in model selection (`CROSS_MODEL_AGREEMENT_SYSTEM.md`): "MiniCPM-V 4.5 beats GPT-4o on OCRBench" is the argument for making it a secondary labeling VLM. It hasn't been downloaded or run locally. |
| **DocVQA** | — (external) | — | Question answering over document images by VLMs | Cited in model selection (DeepSeek-VL2-Small, 93.3%). DocVQA images serve as an out-of-distribution IQA test set (SRCC 0.78 in `MODEL_CARDS.md`) and as a training source. |
| **OmniDocBench (as a published leaderboard)** | — | — | Same benchmark as above | Its public score (Qwen3.5-9B scores 90.8) is why Qwen3.5-9B is the primary cross-model agreement VLM. |

## Document-IQA benchmarks (used to score VLMs as quality judges)

| Benchmark | Size | License | What it measures | How this project uses it |
|-----------|------|---------|------------------|--------------------------|
| **DIQA-5000** (DocIQ, arXiv:2509.17012) | 5,500 images (500 originals × 10 enhancement methods) | Research | Human MOS for overall quality, sharpness and color | The main benchmark for picking a model. Qwen-VL and InternVL were prompted for 1–5 scores and compared with CNN IQA models by SRCC (target > 0.90). Train and val splits are allowed for training; the test split (~1,100) is reserved. `DEQA_METHODOLOGY_COMPARISON.md` explains why free-text VLM scoring underperforms DeQA-style logit scoring. |
| **Q-Doc** (2025) | ~4,260 camera-captured images | Unknown | Quality scores for documents photographed on phones | Validates SigLIP 2 IQA heads on camera captures. ⚠️ `BENCHMARKS.md` says test-only, but its source file maps about 3,400 train-split images to the SIG-G5-5 head. |
| **Q-Align** (7B MLLM scorer) | — | — | General IQA scoring by a multimodal LLM | Provides Tier 2 cross-validation for the overall_quality head. That head switched from a VLM prompt (SRCC 0.53) to a MUSIQ + TOPIQ-NR ensemble (gate: SRCC ≥ 0.55 on held-out DIQA-5000). |
| **SmartDoc-QA** (CBDAR/ICDAR 2015) | 4,280 phone photos taken with a robotic arm | Research only | Image quality measured by OCR accuracy, under controlled blur and lighting distortions | Benchmark only; training on it is explicitly prohibited. The project assigned its own splits. |

## Classical CV benchmarks (not LLM benchmarks; listed for completeness)

- **DocLayNet**: 80,863 pages, 11-class layout detection (mAP). The test split (6,480) is reserved.
- **PubTabNet / PubTables-1M, TableBank, FinTabNet**: table detection and structure recognition.
- **DocStructBench**: layout pre-training data for DocLayout-YOLO; not used as an evaluation set.
- **FUNSD / FUNSD+**: form understanding. The FUNSD test split (50) is reserved.
- **COCO-Text, MLT19, HierText, MDIW13**: scene-text and multi-script detection. Test splits are reserved.
- **HASYv2**: math symbol recognition. The test split is reserved.
- **WiLI-2018**: language identification over text.

## Notes for the reviewing session

1. **Non-commercial licenses.** OmniDocBench, OHR-Bench, Document Haystack and FinanceBench can only be used for internal evaluation. None of them can ship in a product.
2. **Contamination.** Publicly released QA benchmarks (FinanceBench, OCRBench, CC-OCR) may already be in the training data of recent VLMs. Scores from them overstate how well a model generalizes.
3. **Evaluation method.** VLM IQA scoring currently parses free text with a regex. Before comparing against published results, switch to closed-set token-logit scoring (the DeQA-Score approach).
4. **Two labeling inconsistencies need resolving** (listed above): the restriction status of CC-OCR and Q-Doc differs between `BENCHMARKS.md` and their source files.
5. **Mentioned but never reviewed in depth.** InfographicVQA, ChartQA, olmOCR-Bench, KIE-Bench, MMLongBench-Doc and Q-Bench each come up once at most, and none has a source file or audit. These are the likely candidates for the next review.
6. **VLM findings so far.** A prompted VLM for overall quality reached only SRCC 0.53 on DIQA-5000, which is why that head moved to pretrained NR-IQA models.
