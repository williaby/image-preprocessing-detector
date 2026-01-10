# Project B: Quantization Factory (Unsloth)

> **Status**: Implementation Phase
> **Created**: 2025-12-17
> **Owner**: Core Team
> **Type**: Model Transformation Only

---

## 1. Project Purpose

The purpose of **Project B – Quantization Factory** is to produce standardized, reproducible quantized variants of candidate multimodal models using Unsloth, enabling:

- **Reduced GPU memory** and inference cost
- **Controlled performance–efficiency tradeoff** analysis
- **Consistent downstream benchmarking** (Project A)
- **Optional use as starting points** for fine-tuning (Project C)

**Critical Constraint**: Project B focuses **exclusively on model transformation**, not evaluation or learning.

---

## 2. In-Scope Objectives

### 2.1 Supported Quantization Targets

Project B will support quantization of base models sourced from Hugging Face:

| Priority | Model | Status |
|----------|-------|--------|
| P0 | **LLaMA 4 Maverick** | Initial priority |
| P1 | Qwen 2.5-VL | Next iteration |
| P2 | DeepSeek-VL | Future |
| P3 | Other HF-hosted multimodal models | As approved |

**Compatibility Requirements**:

- Models must be compatible with Unsloth
- Models must work with standard transformer runtimes

### 2.2 Quantization Variants

For each supported base model, Project B will generate:

| Variant | Bits | Memory Reduction | Status |
|---------|------|------------------|--------|
| **8-bit** | 8 | ~50% | Required |
| **4-bit** | 4 | ~75% | Required |
| **Mixed** | Variable | Selective | Optional (future) |

Each variant must be generated using a **documented, repeatable recipe**.

### 2.3 Quantization Pipeline

Project B will implement a **deterministic quantization pipeline** that:

1. Loads the specified base model
2. Applies Unsloth quantization with explicit parameters
3. Verifies successful model loading post-quantization
4. Runs a minimal smoke inference (sanity check only)

**The pipeline must NOT**:

- ❌ Train the model
- ❌ Fine-tune adapters
- ❌ Modify model architecture beyond quantization

### 2.4 Artifact Packaging and Storage

Each quantized model must be packaged as a **versioned artifact** suitable for downstream use.

**Artifact Contents**:

```
{model_id}-int{bits}-v{version}/
├── model.safetensors           # Quantized weights
├── config.json                 # Model configuration
├── tokenizer.json              # Tokenizer
├── tokenizer_config.json       # Tokenizer config
├── special_tokens_map.json     # Special tokens
├── generation_config.json      # Generation defaults
├── quantization_config.json    # Quant parameters
└── MANIFEST.yaml               # Complete metadata
```

**Storage Options**:

- Private Hugging Face repositories (preferred)
- Internal artifact storage with equivalent access control

**Immutability Rule**: Artifacts must be **immutable once published**.

### 2.5 Quantization Metadata and Manifest

Every quantized artifact must include a **quantization manifest**:

```yaml
# MANIFEST.yaml
artifact_id: llama4-maverick-int8-v1.0.0
version: 1.0.0
created_at: "2025-12-17T10:00:00Z"

base_model:
  source: huggingface
  repository: meta-llama/Llama-4-Maverick
  revision: abc123def456
  checksum: sha256:...

quantization:
  method: unsloth
  variant: int8
  bits: 8
  group_size: 128
  symmetric: true
  exclude_modules:
    - lm_head
  unsloth_version: "0.3.2"

performance:
  vram_baseline_gb: 28.5      # FP16 baseline
  vram_quantized_gb: 14.2     # Post-quantization
  vram_reduction_pct: 50.2
  inference_latency_ms:
    batch_1: 45
    batch_8: 120
  throughput_tokens_per_sec: 85

validation:
  load_successful: true
  smoke_inference_passed: true
  sample_output_hash: sha256:...

compatibility:
  transformers_version: ">=4.36.0"
  unsloth_version: ">=0.3.0"
  cuda_version: ">=11.8"
  python_version: ">=3.10"

caveats:
  - "Vision encoder not quantized"
  - "Recommend batch_size <= 8 for stability"

storage:
  huggingface_repo: our-org/llama4-maverick-int8
  local_path: null
  checksum: sha256:...
```

---

## 3. Out-of-Scope Items

Project B **explicitly does not include**:

| Item | Owner |
|------|-------|
| Benchmarking or performance evaluation | Project A |
| DIQA-5000 inference or scoring | Project A |
| Fine-tuning, LoRA, PEFT, adapter training | Project C |
| Calibration or uncertainty modeling | Project C |
| OCR preprocessing logic | Existing pipeline |
| Dataset ingestion or labeling | External |

**Rule**: Project B produces model variants only, **not performance claims**.

---

## 4. Inputs and Dependencies

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| **Base Model IDs** | Hugging Face | Repository + revision |
| **Quantization Requirements** | Configuration | Bit-depth targets |
| **Unsloth Config** | Internal | Approved parameters |

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `unsloth` | >=0.3.0 | Quantization engine |
| `transformers` | >=4.36.0 | Model loading |
| `pytorch` | >=2.0 | Runtime |
| `safetensors` | Latest | Weight serialization |
| `bitsandbytes` | >=0.41 | Quantization kernels |

### Hardware Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **GPU Memory** | 24GB | 40GB+ |
| **GPU Type** | A10 | A100 |
| **System RAM** | 64GB | 128GB |
| **Storage** | 100GB | 500GB |

---

## 5. Outputs and Deliverables

### Required Deliverables

| Deliverable | Description | Format |
|-------------|-------------|--------|
| **Quantization Pipeline** | CLI workflow for quantizing models | Python CLI |
| **Quantized Artifacts** | 8-bit and 4-bit per base model | Safetensors |
| **Quantization Manifest** | Complete metadata per artifact | YAML |
| **Artifact Registry** | Catalog of available variants | YAML/JSON |

### CLI Interface

```bash
# Quantize a model to 8-bit
quantize run --model meta-llama/Llama-4-Maverick --bits 8 --output ./artifacts/

# Quantize to 4-bit with custom group size
quantize run --model meta-llama/Llama-4-Maverick --bits 4 --group-size 64 --output ./artifacts/

# Quantize from spec file
quantize run --config ./quantize_config.yaml

# Validate a quantized artifact
quantize validate --artifact ./artifacts/llama4-maverick-int8-v1.0.0/

# Publish to HuggingFace
quantize publish --artifact ./artifacts/llama4-maverick-int8-v1.0.0/ --repo our-org/llama4-maverick-int8

# List available recipes
quantize recipes list

# Show recipe details
quantize recipes show llama4
```

### Artifact Registry Schema

```yaml
# artifact_registry.yaml
registry_version: "1.0.0"
last_updated: "2025-12-17T10:00:00Z"

artifacts:
  - id: llama4-maverick-int8-v1.0.0
    base_model: meta-llama/Llama-4-Maverick
    variant: int8
    huggingface_repo: our-org/llama4-maverick-int8
    manifest_url: https://huggingface.co/.../MANIFEST.yaml
    status: published
    created_at: "2025-12-17T10:00:00Z"

  - id: llama4-maverick-int4-v1.0.0
    base_model: meta-llama/Llama-4-Maverick
    variant: int4
    huggingface_repo: our-org/llama4-maverick-int4
    manifest_url: https://huggingface.co/.../MANIFEST.yaml
    status: published
    created_at: "2025-12-17T10:30:00Z"

  - id: qwen25-vl-int8-v1.0.0
    base_model: Qwen/Qwen2.5-VL-7B
    variant: int8
    huggingface_repo: null
    status: planned
    created_at: null
```

---

## 6. Success Criteria

Project B is considered successful when:

| Criterion | Metric |
|-----------|--------|
| **Load Success** | Quantized models load without errors |
| **Reproducibility** | Artifacts reproducible from documented inputs |
| **Memory Reduction** | VRAM and runtime materially reduced |
| **Project A Compatible** | Variants benchmarkable without modification |
| **Project C Compatible** | Variants usable as fine-tuning baselines |

---

## 7. Relationship to Other Projects

```
┌─────────────────────────────────────────────────────────────┐
│                   Project B: Quantization                   │
│                  (Model Transformation)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Base Models (HuggingFace)                                  │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────┐                   │
│  │  Quantization Pipeline              │                   │
│  │  • Load base model                  │                   │
│  │  • Apply Unsloth quantization       │                   │
│  │  • Validate loading                 │                   │
│  │  • Smoke inference                  │                   │
│  └─────────────────────────────────────┘                   │
│         │                                                   │
│         ▼                                                   │
│  Quantized Artifacts (8-bit, 4-bit)                        │
│         │                                                   │
│    ┌────┴────┐                                              │
│    ▼         ▼                                              │
│ Project A  Project C                                        │
│ (Evaluate) (Fine-tune)                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- **Project A (Benchmarking Arena)** consumes quantized artifacts and evaluates performance
- **Project C (Fine-Tuning)** may use quantized artifacts as baselines or training inputs
- **Project B does not interpret or judge model quality**

---

## 8. Design Principle

> **Project B's output is a tool, not an opinion.**

Quantization reduces cost and changes performance characteristics. Determining whether that tradeoff is acceptable is **explicitly delegated to Project A**.

---

## 9. Implementation Architecture

### Module Structure

```
src/image_preprocessing_detector/labeling/quantization/
├── __init__.py
├── cli.py                  # Click-based CLI
├── pipeline.py             # Main quantization orchestration
├── validator.py            # Post-quantization validation
├── packager.py             # Artifact packaging
├── registry.py             # Artifact registry management
├── recipes/                # Model-family-specific recipes
│   ├── __init__.py
│   ├── base.py             # Abstract recipe interface
│   ├── llama4.py           # LLaMA 4 recipe
│   ├── qwen.py             # Qwen recipe
│   └── deepseek.py         # DeepSeek recipe
└── storage/                # Storage backends
    ├── __init__.py
    ├── base.py             # Abstract storage interface
    ├── huggingface.py      # HF Hub storage
    └── local.py            # Local filesystem storage
```

### Key Classes

```python
# Abstract recipe interface
class QuantizationRecipe(ABC):
    """Base class for model-family-specific quantization recipes."""

    @property
    @abstractmethod
    def model_family(self) -> str: ...

    @property
    @abstractmethod
    def supported_bits(self) -> list[int]: ...

    @abstractmethod
    def quantize(
        self,
        model_id: str,
        bits: int,
        output_dir: Path,
        **kwargs,
    ) -> QuantizationResult: ...

# LLaMA 4 specific recipe
class Llama4Recipe(QuantizationRecipe):
    model_family = "llama4"
    supported_bits = [4, 8]

    def quantize(
        self,
        model_id: str,
        bits: int,
        output_dir: Path,
        group_size: int = 128,
        exclude_modules: list[str] | None = None,
    ) -> QuantizationResult: ...

# Main pipeline
class QuantizationPipeline:
    def run(
        self,
        model_id: str,
        recipe: QuantizationRecipe,
        bits: int,
        output_dir: Path,
    ) -> QuantizedArtifact: ...

# Validation
class ArtifactValidator:
    def validate_loading(self, artifact: QuantizedArtifact) -> bool: ...
    def run_smoke_inference(self, artifact: QuantizedArtifact) -> bool: ...
```

---

## 10. Timeline

| Week | Milestone |
|------|-----------|
| 1 | CLI scaffold, recipe interface |
| 2 | LLaMA 4 recipe implementation |
| 3 | Validation pipeline |
| 4 | Artifact packaging |
| 5 | HuggingFace publishing |
| 6 | Registry management |
| 7 | Qwen recipe |
| 8 | Integration testing |

---

## 11. Open Questions

1. **Unsloth Access**: Do we have Unsloth Pro license for advanced features?
2. **HF Organization**: Which HF org for publishing artifacts?
3. **GPU Allocation**: Dedicated GPU for quantization jobs?
4. **Version Policy**: Semantic versioning for artifacts?
5. **Mixed Precision**: When should mixed precision be implemented?

---

*Last Updated: 2025-12-17*
