---
title: Docling Configuration Reference
schema_type: reference
status: active
owner: ml-team
purpose: "Master reference for all docling adjustment levers available to Project B via DocumentMetadata routing params."
tags:
  - docling
  - ocr
  - routing
  - project-b
  - configuration
---

# Docling Configuration Reference

> **Purpose**: Master reference for all configurable levers in docling that Project A can influence
> via `DoclingRoutingParams`. Covers programmatic API, CLI flags, and engine-specific options.
>
> **Source**: [docling-project/docling](https://github.com/docling-project/docling)
> — `docling/datamodel/pipeline_options.py`, `docling/cli/main.py`
>
> **Related documents**:
>
> - [docs/planning/PROJECT_A_TO_B_HANDOFF_SPECIFICATION.md](../planning/PROJECT_A_TO_B_HANDOFF_SPECIFICATION.md) — handoff contract
> - [src/image_preprocessing_detector/routing/docling_router.py](../../src/image_preprocessing_detector/routing/docling_router.py) — our routing engine
> - [src/image_preprocessing_detector/schema.py](../../src/image_preprocessing_detector/schema.py) — DoclingRoutingParams

---

## 1. Pipeline Selection

The top-level lever that determines which processing path docling uses.

| Pipeline | CLI `--pipeline` | API `ProcessingPipeline` | Use Case |
|----------|-----------------|--------------------------|----------|
| `standard` | `--pipeline=standard` | `STANDARD` | Default — layout + OCR + TableFormer |
| `vlm` | `--pipeline=vlm` | `VLM` | Vision-Language Model for degraded/complex docs |
| `legacy` | `--pipeline=legacy` | `LEGACY` | Backward compatibility only |
| `asr` | `--pipeline=asr` | `ASR` | Audio/video transcription (not relevant for docs) |

**Our usage**: Project A's `DoclingRoutingParams.pipeline` selects between `standard` and `vlm`.
VLM is triggered by: handwriting, DQS < 0.4, low script confidence, extreme warping, complex
degradation, or script-based escalation from `script_routing.yaml`.

---

## 2. OCR Configuration

### 2.1 OCR Enable/Force

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| `--ocr` / `--no-ocr` | `PdfPipelineOptions.do_ocr` | `True` | Enable/disable OCR entirely |
| `--force-ocr` | `PdfPipelineOptions.force_full_page_ocr` | `False` | Force OCR even on born-digital with text layer |

**Our usage**: Project A sets `ocr_enabled=False` when `text_layer_quality >= 0.90` and
`text_layer_skip_ocr=True`. This emits `--no-ocr` via `to_cli_args()`.

**Gap**: `force_backend_text` (`PdfPipelineOptions.force_backend_text`) — when `True`, tells
docling to use the PDF text layer directly and skip ML-based OCR for all content. Distinct from
`--no-ocr` because it preserves text coordinates. Not yet exposed in `DoclingRoutingParams`.

### 2.2 Bitmap Area Threshold

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| *(none)* | `OcrOptions.bitmap_area_threshold` | `0.05` (5%) | Min fraction of page area that must be bitmapped to trigger OCR |

**Not yet exposed in our routing.** Could be tuned down for born-digital documents with
embedded bitmapped signatures or stamps.

### 2.3 OCR Engine Selection

| Engine Key | CLI `--ocr-engine` | API `kind` | Best For |
|------------|-------------------|------------|----------|
| `auto` | `--ocr-engine=auto` | `"auto"` | Default — docling picks per page |
| `rapidocr` | `--ocr-engine=rapidocr` | `"rapidocr"` | Latin/Cyrillic/Greek, fast; **wraps PaddleOCR** |
| `easyocr` | `--ocr-engine=easyocr` | `"easyocr"` | Multi-language, GPU-accelerated |
| `tesseract` | `--ocr-engine=tesseract` | `"tesserocr"` | Python bindings (faster) |
| `tesseract_cli` | `--ocr-engine=tesseract_cli` | `"tesseract"` | Shell-based Tesseract |
| `ocrmac` | `--ocr-engine=ocrmac` | `"ocrmac"` | macOS Vision framework |

> **PaddleOCR naming clarification**: Docling does not expose a `paddleocr` engine key.
> PaddleOCR is accessible *through* `rapidocr` — RapidOCR wraps PaddleOCR models and is the
> supported path. A Docling maintainer confirmed: *"We have RapidOCR in docling, which wraps
> PaddleOCR."* ([#626](https://github.com/docling-project/docling/discussions/626))
>
> **Consequence**: any reference to `paddleocr` as an engine value in our codebase
> (`schema.py`, `script_routing.yaml`, docstrings) is an incorrect engine key.
> The correct value is `rapidocr`.

**Our usage**: `DoclingRoutingEngine._apply_script_engine_rule()` delegates to `ScriptRouter`
which reads from `config/script_routing.yaml`. Latin/Cyrillic/Greek → `rapidocr` via
`_RAPIDOCR_SCRIPTS`. CJK → reduced batch size.

### 2.4 Language Hints

| CLI Flag | API Field | Format | Effect |
|----------|-----------|--------|--------|
| `--ocr-lang=<langs>` | `OcrOptions.lang` | List[str] | Language codes per engine |

Language code format varies by engine:

| Engine | Language Format | Examples |
|--------|----------------|---------|
| `rapidocr` | RapidOCR names | `"english"`, `"chinese"`, `"arabic"` |
| `easyocr` | EasyOCR codes | `"en"`, `"ch_sim"`, `"ar"` |
| `tesseract` | ISO 639-3 + tessdata | `"eng"`, `"chi_sim"`, `"ara"` |
| `ocrmac` | BCP-47 locale | `"en-US"`, `"zh-Hans-CN"`, `"ar-SA"` |

**Our usage**: `DoclingRoutingEngine._apply_script_engine_rule()` calls
`ScriptRouter.get_lang_hint()` which reads `lang_hint` from routing YAML.

### 2.5 Per-Engine Options

#### RapidOcrOptions

| Field | Default | Effect |
|-------|---------|--------|
| `backend` | `"onnxruntime"` | Runtime: `onnxruntime`, `openvino`, `paddle`, `torch` |
| `text_score` | `0.5` | Minimum confidence threshold to accept detection |
| `use_det` | `None` | Enable/disable text detection model |
| `use_cls` | `None` | Enable/disable direction classification model |
| `use_rec` | `None` | Enable/disable text recognition model |
| `det_model_path` | `None` | Custom detection model path |
| `cls_model_path` | `None` | Custom classification model path |
| `rec_model_path` | `None` | Custom recognition model path |
| `rapidocr_params` | `{}` | Raw RapidOCR config dict (pass-through) |

#### EasyOcrOptions

| Field | Default | Effect |
|-------|---------|--------|
| `use_gpu` | `None` | Force GPU on/off (auto if None) |
| `confidence_threshold` | `0.5` | Minimum recognition confidence |
| `model_storage_directory` | `None` | Override model download location |
| `recog_network` | `"standard"` | Recognition network variant |
| `download_enabled` | `True` | Allow model download |

#### TesseractCliOcrOptions / TesseractOcrOptions

| Field | Default | Effect |
|-------|---------|--------|
| `path` | `None` | Tessdata directory path |
| `psm` | `None` | Page Segmentation Mode (0–13); see §2.6 |

#### OcrMacOptions

| Field | Default | Effect |
|-------|---------|--------|
| `recognition` | `"accurate"` | Quality level: `"accurate"` or `"fast"` |
| `framework` | `"vision"` | Apple framework: `"vision"` |

### 2.6 Tesseract Page Segmentation Mode (PSM)

| PSM | Mode | Best For |
|-----|------|---------|
| 0 | OSD only | Orientation/script detection only |
| 1 | Auto with OSD | Default auto segmentation |
| 3 | Fully automatic | No OSD (fast, default) |
| 4 | Single column of variable sizes | Narrow column layouts |
| 5 | Single uniform block (vertical) | — |
| 6 | Single uniform block | Clean single-column docs |
| 7 | Single text line | One-line inputs |
| 8 | Single word | — |
| 9 | Single word in circle | — |
| 10 | Single character | — |
| 11 | Sparse text, no OSD | Tables, forms, sparse layouts |
| 12 | Sparse text with OSD | — |
| 13 | Raw line | Treat as single line, bypass Tesseract logic |

**Our usage**: `PSMRecommender` in `routing/psm_recommender.py` selects PSM from layout
signals. Only applies when `ocr_engine` is `tesseract` or `tesseract_cli`.

---

## 3. Layout Detection

### 3.1 Layout Enable/Configuration

| CLI Flag | API Class | Default | Effect |
|----------|-----------|---------|--------|
| *(none)* | `PdfPipelineOptions.layout_options` | `LayoutOptions()` | Layout model configuration |
| *(none)* | `LayoutOptions.model_spec` | `DOCLING_LAYOUT_HERON` | Layout model variant |
| *(none)* | `LayoutOptions.keep_empty_clusters` | `False` | Retain empty layout clusters |
| *(none)* | `LayoutOptions.skip_cell_assignment` | `False` | Skip table structure association |
| *(none)* | `LayoutOptions.create_orphan_clusters` | `True` | Create clusters for unmatched elements |

### 3.2 Layout Model Variants

Docling ships with pre-configured layout model specs:

| Constant | Model | Speed | Accuracy | VRAM |
|----------|-------|-------|----------|------|
| `DOCLING_LAYOUT_HERON` | Heron (default) | Fast | Good | ~4GB |
| `DOCLING_LAYOUT_EGRET_LARGE` | Egret-Large | Slower | High | ~8GB |
| `DOCLING_LAYOUT_EGRET_XLARGE` | Egret-XLarge | Slowest | Highest | ~12GB |

> **Our current usage**: Project A's `ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md` and
> CLAUDE.md specify `docling-layout-egret-xlarge` for accuracy and `docling-layout-heron` for
> speed. However, **Project A does not currently expose layout model selection** in
> `DoclingRoutingParams` — Project B must decide this independently. This is a gap.

### 3.3 Layout Batch Size

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| *(none)* | `ThreadedPdfPipelineOptions.layout_batch_size` | `4` | Pages per layout batch |

**Our usage**: We expose only `page_batch_size` (applies to OCR). `layout_batch_size` is not
separately controllable from our routing params.

---

## 4. Table Structure Extraction

### 4.1 Table Enable/Mode

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| `--tables` / `--no-tables` | `PdfPipelineOptions.do_table_structure` | `True` | Enable/disable TableFormer |
| `--table-mode=fast` | `TableStructureOptions.mode` | `ACCURATE` | `fast` or `accurate` |
| *(none)* | `TableStructureOptions.do_cell_matching` | `True` | Align detected cells with content |
| *(none)* | `ThreadedPdfPipelineOptions.table_batch_size` | `4` | Pages per table batch |

**Our usage**: `DoclingRoutingEngine._apply_table_mode_rule()` sets `table_mode = "accurate"`
when `complexity_score >= 0.6` or `has_merged_cells == True`; otherwise `"fast"`.

**Gap in `to_cli_args()`**: The `--no-tables` flag is never emitted even when
`tables_enabled=False`. The `--tables` flag is always omitted from our CLI args, which means
it always defaults to `True` regardless of what Project A recommends.

### 4.2 TableFormer Model

Single built-in model (`TableStructureModel`). No variant selection available.
Mode (fast/accurate) controls inference approach within the same model.

---

## 5. Enrichment Options

These are opt-in enrichment passes that run after the standard pipeline.

| CLI Flag | API Field | Default | What It Does |
|----------|-----------|---------|--------------|
| `--enrich-code` | `PdfPipelineOptions.do_code_enrichment` | `False` | Extract code blocks via VLM |
| `--enrich-formula` | `PdfPipelineOptions.do_formula_enrichment` | `False` | Extract math formulas via VLM |
| `--enrich-picture-classes` | `PdfPipelineOptions.do_picture_classification` | `False` | Classify images (chart/photo/diagram/etc.) |
| `--enrich-picture-description` | `PdfPipelineOptions.do_picture_description` | `False` | Generate VLM descriptions for pictures |
| `--enrich-chart-extraction` | `PdfPipelineOptions.do_chart_extraction` | `False` | Convert charts to tabular data |

**Our usage**:
- `DoclingRoutingEngine._apply_enrichment_rule()` sets `enrich_code=True` when `has_code=True`
- Sets `enrich_formula=True` when `has_dense_math=True`

**Gaps**: Project A does not set `enrich_picture_description`, `enrich_picture_classes`, or
`enrich_chart_extraction`. All three are unrepresented in `DoclingRoutingParams`.

---

## 6. VLM Pipeline Options

When `pipeline = "vlm"`, docling uses a vision-language model for full-page understanding.

### 6.1 VLM Model Selection

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| `--vlm-model=<preset>` | `VlmPipelineOptions.vlm_options` | `granite_docling` | VLM model preset |

Known VLM presets in docling:

| Preset | Model | Use Case |
|--------|-------|---------|
| `granite_docling` | IBM Granite DocLing | Default — document understanding |
| `smolvlm` | SmolVLM | Lightweight, fast |
| `inline_vlm` | Custom HuggingFace model | Custom via repo_id |
| `api_vlm` | External API endpoint | Custom REST API |

**Options for each**:

**InlineVlmOptions / VlmConvertOptions**:

| Field | Default | Effect |
|-------|---------|--------|
| `repo_id` | — | HuggingFace model identifier |
| `scale` | `2.0` | Image resolution multiplier for VLM input |
| `max_size` | `None` | Max image pixel dimension |
| `batch_size` | `1` | Images per VLM batch |
| `force_backend_text` | `False` | Use text layer instead of VLM for text |
| `generation_config.max_new_tokens` | `200` | Max generated tokens |
| `generation_config.do_sample` | `False` | Greedy vs sampled generation |

**ApiVlmOptions**:

| Field | Default | Effect |
|-------|---------|--------|
| `url` | `http://localhost:8000/v1/chat/completions` | Remote VLM endpoint |
| `headers` | `{}` | HTTP headers for auth |
| `timeout` | `20.0` | Request timeout (seconds) |
| `concurrency` | `1` | Parallel API requests |
| `prompt` | `"Describe this image..."` | System prompt |

**VLM Pipeline options**:

| Field | Default | Effect |
|-------|---------|--------|
| `generate_page_images` | `True` (required for VLM) | Render page to image for VLM |
| `force_backend_text` | `False` | Combine VLM with text layer |

**Gap**: `DoclingRoutingParams.vlm_model` is set to `None` by default and never populated
by `DoclingRoutingEngine._apply_vlm_escalation_rule()`. When `pipeline = "vlm"`, docling
will use its own default (`granite_docling`). Project A has no mechanism to select which VLM.

---

## 7. PDF Backend

| CLI Flag | API Enum | Effect |
|----------|----------|--------|
| `--pdf-backend=docling_parse` | `PdfBackend.DOCLING_PARSE` | Docling's native PDF parser (default) |
| `--pdf-backend=pypdfium2` | `PdfBackend.PYPDFIUM2` | PyPDFium2 backend |
| *(none)* | `--pdf-password=<pass>` | Decrypt password-protected PDFs |

**Gap**: Not exposed in `DoclingRoutingParams`. For complex or malformed PDFs where one backend
fails, Project A cannot recommend a fallback. Project A already classifies `pdf_type`, which
could inform backend selection.

---

## 8. Image Generation and Scaling

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| `--image-export-mode` | `ImageRefMode` | `embedded` | `placeholder`, `embedded` (base64), `referenced` (PNG file) |
| *(none)* | `PdfPipelineOptions.images_scale` | `1.0` | Resolution multiplier for extracted images |
| *(none)* | `PdfPipelineOptions.generate_page_images` | `False` | Render full page as image in output |
| *(none)* | `PdfPipelineOptions.generate_picture_images` | `False` | Extract picture regions as images |

**Gap**: `images_scale` is particularly relevant for Project A — the resolution quality score
could directly inform this value. A document with `resolution_quality=0.3` (marginal) might
benefit from `images_scale=2.0` to improve picture extraction quality.

---

## 9. Accelerator and Performance

### 9.1 Hardware Accelerator

| CLI Flag | API Enum | Effect |
|----------|----------|--------|
| `--device=auto` | `AcceleratorDevice.AUTO` | Auto-detect GPU (default) |
| `--device=cpu` | `AcceleratorDevice.CPU` | Force CPU |
| `--device=cuda` | `AcceleratorDevice.CUDA` | NVIDIA GPU |
| `--device=cuda:N` | `AcceleratorDevice.CUDA` + index | Specific GPU |
| `--device=mps` | `AcceleratorDevice.MPS` | Apple Silicon |
| `--device=xpu` | `AcceleratorDevice.XPU` | Intel GPU |

**Additional GPU setting** (not CLI-accessible):

| API Field | Default | Effect |
|-----------|---------|--------|
| `AcceleratorOptions.cuda_use_flash_attention2` | `False` | Flash Attention 2 for Ampere+ GPUs |

Environment variable overrides: `DOCLING_NUM_THREADS`, `OMP_NUM_THREADS`.

**Gap**: Not exposed in `DoclingRoutingParams`. Project A's device orchestration layer knows
which accelerator is available — this information could be passed to Project B.

### 9.2 Threading and Batch Sizes

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| `--num-threads=N` | `AcceleratorOptions.num_threads` | `4` | Worker thread count |
| `--page-batch-size=N` | `PdfPipelineOptions.ocr_batch_size` | `4` | OCR pages per batch |
| *(none)* | `ThreadedPdfPipelineOptions.layout_batch_size` | `4` | Layout pages per batch |
| *(none)* | `ThreadedPdfPipelineOptions.table_batch_size` | `4` | Table pages per batch |
| *(none)* | `ThreadedPdfPipelineOptions.batch_polling_interval_seconds` | `0.5` | Worker polling interval |
| *(none)* | `ThreadedPdfPipelineOptions.queue_max_size` | `100` | Page queue depth |

**Our usage**: We expose `page_batch_size` (OCR batch). For CJK scripts, it's reduced to 2.
Layout and table batch sizes are not separately controlled.

### 9.3 Document Limits

| CLI Flag | API Parameter | Default | Effect |
|----------|---------------|---------|--------|
| `--document-timeout=N` | `PipelineOptions.document_timeout` | `None` | Abort after N seconds |
| *(via convert())* | `max_num_pages` | `sys.maxsize` | Page count limit |
| *(via convert())* | `max_file_size` | `sys.maxsize` | File size limit (bytes) |
| *(via convert())* | `page_range` | all | Specific page subset to process |

**Gap**: `document_timeout` not in `DoclingRoutingParams`. For documents with DQS indicating
complex degradation, a longer timeout might be recommended by Project A.

---

## 10. Plugin and Extension System

| CLI Flag | API Field | Default | Effect |
|----------|-----------|---------|--------|
| `--enable-remote-services` | `PipelineOptions.enable_remote_services` | `False` | Allow API calls to external services |
| `--allow-external-plugins` | `PipelineOptions.allow_external_plugins` | `False` | Load third-party plugins via entrypoints |
| `--artifacts-path=<path>` | `PipelineOptions.artifacts_path` | `None` | Local model artifact directory |

The plugin system uses Python setuptools entrypoints. Plugins register additional OCR engines,
layout models, or pipeline stages under the `"layout_engines"`, `"ocr_engines"`, or
`"table_structure_engines"` registry keys.

---

## 11. Output Formats

| CLI Flag | Format | Description |
|----------|--------|-------------|
| `--to=md` | Markdown | Structured markdown with headers, tables |
| `--to=json` | DoclingDocument JSON | Full schema with bounding boxes |
| `--to=html` | HTML | Web-renderable HTML |
| `--to=doctags` | DocTags | IBM Granite-native XML-like format |
| *(default)* | DoclingDocument | In-memory Python object |

**Chunking** (downstream of conversion, relevant to Project C):

| Chunker | Config | Best For |
|---------|--------|---------|
| `HybridChunker` | `merge_peers=True` | RAG — hierarchical + token-aware |
| `HierarchicalChunker` | `merge_list_items=True` | Structure-preserving chunks |

---

## 12. Debug and Profiling

| CLI Flag | Default | Effect |
|----------|---------|--------|
| `--debug-visualize-cells` | `False` | Visualize PDF text cells |
| `--debug-visualize-ocr` | `False` | Visualize OCR bounding boxes |
| `--debug-visualize-layout` | `False` | Visualize layout clusters |
| `--debug-visualize-tables` | `False` | Visualize table cell detection |
| `--profiling` | `False` | Print per-stage timing summary |
| `--save-profiling` | `False` | Save profiling data as JSON |
| `-v` / `-vv` | info / debug | Logging verbosity |

---

## 13. Picture Description Options

When `do_picture_description=True`, configures VLM description of embedded images.

**PictureDescriptionVlmEngineOptions** (preferred):

| Field | Default | Effect |
|-------|---------|--------|
| `model_spec` | — | VlmModelSpec for description model |
| `prompt` | `"Describe this image in a few sentences."` | Description prompt |
| `generation_config.max_new_tokens` | `200` | Max description length |
| `batch_size` | `8` | Images per batch |
| `scale` | `2.0` | Image resolution multiplier |
| `picture_area_threshold` | `0.05` | Minimum area fraction to describe |

**PictureDescriptionApiOptions** (for external VLM services):

| Field | Default | Effect |
|-------|---------|--------|
| `url` | `http://localhost:8000/v1/chat/completions` | VLM API endpoint |
| `timeout` | `20.0` | Request timeout |
| `concurrency` | `1` | Parallel requests |
| `prompt` | `"Describe this image..."` | System prompt |

**Classification filtering** (for targeted description):

| Field | Default | Effect |
|-------|---------|--------|
| `classification_allow` | `None` | Only describe these picture types |
| `classification_deny` | `None` | Skip these picture types |
| `classification_min_confidence` | `0.0` | Min classification confidence to describe |

---

## 14. Programmatic API Quick Reference

```python
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    EasyOcrOptions,
    TableStructureOptions,
    TableFormerMode,
    LayoutOptions,
    AcceleratorOptions,
    AcceleratorDevice,
)

# Full configuration example
pipeline_options = PdfPipelineOptions(
    # OCR
    do_ocr=True,
    ocr_options=RapidOcrOptions(lang=["english"], text_score=0.5),

    # Tables
    do_table_structure=True,
    table_structure_options=TableStructureOptions(
        mode=TableFormerMode.ACCURATE,
        do_cell_matching=True,
    ),

    # Layout
    layout_options=LayoutOptions(),  # uses DOCLING_LAYOUT_HERON

    # Enrichments
    do_code_enrichment=True,
    do_formula_enrichment=True,

    # Image generation
    images_scale=1.0,
    generate_page_images=False,
    generate_picture_images=True,

    # Performance
    accelerator_options=AcceleratorOptions(
        device=AcceleratorDevice.AUTO,
        num_threads=4,
    ),
)

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

result = converter.convert(
    "document.pdf",
    max_num_pages=100,
    page_range=(1, 10),    # process only pages 1-10
    raises_on_error=False,
)
```

---

## 15. Current `DoclingRoutingParams` Coverage Matrix

The table below shows which docling levers are currently exposed through our routing system.

| Docling Option | CLI Flag | In `DoclingRoutingParams` | In `to_cli_args()` | Notes |
|----------------|----------|--------------------------|---------------------|-------|
| Pipeline | `--pipeline` | ✅ `pipeline` | ✅ | standard / vlm |
| VLM model | `--vlm-model` | ✅ `vlm_model` | ✅ | Always `None` in practice |
| OCR enable | `--no-ocr` | ✅ `ocr_enabled` | ✅ | |
| Force OCR | `--force-ocr` | ✅ `ocr_force` | ✅ | |
| OCR engine | `--ocr-engine` | ✅ `ocr_engine` | ✅ | "paddleocr" bug |
| OCR language | `--ocr-lang` | ✅ `ocr_lang` | ✅ | |
| Tesseract PSM | `--psm` | ✅ `psm` | ✅ | |
| Table enable | `--tables` | ✅ `tables_enabled` | ❌ **MISSING** | Flag never emitted |
| Table mode | `--table-mode` | ✅ `table_mode` | ✅ | |
| Code enrichment | `--enrich-code` | ✅ `enrich_code` | ✅ | |
| Formula enrichment | `--enrich-formula` | ✅ `enrich_formula` | ✅ | |
| Page batch size | `--page-batch-size` | ✅ `page_batch_size` | ✅ | OCR batch only |
| Force backend text | *(API only)* | ❌ **MISSING** | ❌ | Born-digital text layer |
| PDF backend | `--pdf-backend` | ❌ **MISSING** | ❌ | |
| Image scale | *(API only)* | ❌ **MISSING** | ❌ | Resolution-dependent |
| Picture description | `--enrich-picture-description` | ❌ **MISSING** | ❌ | |
| Picture classification | `--enrich-picture-classes` | ❌ **MISSING** | ❌ | |
| Chart extraction | `--enrich-chart-extraction` | ❌ **MISSING** | ❌ | |
| Layout model variant | *(API only)* | ❌ **MISSING** | ❌ | Heron vs Egret |
| Layout batch size | *(API only)* | ❌ **MISSING** | ❌ | |
| Table batch size | *(API only)* | ❌ **MISSING** | ❌ | |
| Accelerator device | `--device` | ❌ **MISSING** | ❌ | |
| Thread count | `--num-threads` | ❌ **MISSING** | ❌ | |
| Document timeout | `--document-timeout` | ❌ **MISSING** | ❌ | |
| Bitmap area threshold | *(API only)* | ❌ **MISSING** | ❌ | |
| Page range | *(convert() arg)* | ❌ **MISSING** | ❌ | |

---

*Generated 2026-02-22. Source: docling-project/docling main branch.*
