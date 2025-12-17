# Project A: Benchmarking Arena

> **Status**: Implementation Phase
> **Created**: 2025-12-17
> **Owner**: Core Team
> **Type**: Evaluation-Only

---

## 1. Project Purpose

The purpose of **Project A – Benchmarking Arena** is to provide a standardized, repeatable, and auditable evaluation framework for benchmarking document-quality models against the DIQA-5000 dataset (and selected related datasets in later phases).

Project A establishes a **model comparison arena** that enables objective, apples-to-apples comparison of:

- **Base (unmodified) models** sourced from Hugging Face
- **Quantized variants** produced by Project B
- **Fine-tuned variants** produced by Project C

**Critical Constraint**: Project A is **strictly evaluation-only**. No model training, fine-tuning, quantization, calibration, or uncertainty modeling is performed in this project.

---

## 2. In-Scope Objectives

### 2.1 Standardized Benchmarking Pipeline

Project A will implement a **deterministic inference pipeline** that:

1. Loads a specified model variant
2. Runs inference against the DIQA-5000 dataset
3. Produces standardized quality predictions aligned with DIQA labels:
   - Overall quality
   - Sharpness
   - Color fidelity

The pipeline must ensure:
- Identical dataset splits across all models
- Identical preprocessing across all models
- Identical inference settings across all models

### 2.2 Supported Model Sources

| Source Type | Description | Priority |
|-------------|-------------|----------|
| **Hugging Face** | Primary path for model loading | P0 |
| **Local Artifacts** | Quantized/fine-tuned checkpoints | P0 |
| **API Models** | OpenAI, Google Gemini (black-box) | P1 (Optional) |

API-based models must be treated as **black-box inference sources** with explicit metadata tracking.

### 2.3 Evaluation Metrics (Accuracy Only)

Project A will compute **deterministic accuracy metrics only**, aligned with DIQA-5000 and DocIQ conventions.

**Required Metrics** (per dimension and aggregated):

| Metric | Description | Range | Direction |
|--------|-------------|-------|-----------|
| **PLCC** | Pearson Linear Correlation Coefficient | [-1, 1] | Higher is better |
| **SRCC** | Spearman Rank Correlation Coefficient | [-1, 1] | Higher is better |
| **MAE** | Mean Absolute Error | [0, ∞) | Lower is better |
| **RMSE** | Root Mean Squared Error | [0, ∞) | Lower is better |

**Reporting Granularity**:
- Per DIQA dimension (overall, sharpness, color)
- Macro-averaged summaries

**Explicitly Excluded**:
- No uncertainty metrics
- No confidence intervals
- No probabilistic outputs

### 2.4 Arena-Style Reporting

Project A will generate a benchmark leaderboard ("arena") that:

- Ranks models by each metric
- Clearly distinguishes:
  - Base models
  - Quantized variants
  - Fine-tuned variants
- Allows comparison across:
  - Model family
  - Model size
  - Variant type

**Output Formats**:
- Machine-readable: JSON, Parquet
- Human-readable: Markdown, HTML, PDF

### 2.5 Model Provenance and Reproducibility

Every benchmark run must capture **complete model provenance**:

**Hugging Face Models**:
```yaml
provenance:
  source: huggingface
  repository: meta-llama/Llama-4-Maverick
  revision: abc123def456
  config_hash: sha256:...
  tokenizer_hash: sha256:...
  runtime_backend: transformers
```

**Local Artifacts**:
```yaml
provenance:
  source: local
  artifact_id: llama4-maverick-int8-v1.0
  file_checksum: sha256:...
  build_metadata:
    quantization_method: unsloth
    bits: 8
    source_model_ref: huggingface:meta-llama/Llama-4-Maverick:main
```

**API-Based Models**:
```yaml
provenance:
  source: api
  provider: openai
  model_id: gpt-4o
  api_version: "2024-08-06"
  execution_timestamp: "2025-12-17T14:30:00Z"
  request_params:
    temperature: 0.0
    max_tokens: 1024
  cost_metadata:
    input_tokens: 50000
    output_tokens: 25000
    estimated_cost_usd: 1.25
```

Each benchmark run must produce a **reproducibility manifest** linking results to the exact model and configuration used.

---

## 3. Out-of-Scope Items

Project A **explicitly does not include**:

| Item | Owner |
|------|-------|
| Model training or fine-tuning | Project C |
| LoRA, PEFT, or adapter work | Project C |
| Quantization | Project B |
| Calibration or post-hoc adjustment | Project C |
| Uncertainty estimation or confidence modeling | Project C |
| OCR preprocessing or enhancement pipelines | Existing pipeline |
| Dataset labeling or augmentation | External |

**Rule**: Any work involving learning, adaptation, or score reinterpretation belongs to Project C.

---

## 4. Inputs and Dependencies

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| **DIQA-5000 Dataset** | External | Official train/validation/test split |
| **Model Specifications** | Project B, C | ModelSpec YAML/JSON files |
| **HF Credentials** | Environment | Hugging Face access token |
| **API Credentials** | Environment | OpenAI, Google API keys |

### Dependencies

| Dependency | Purpose |
|------------|---------|
| `transformers` | Hugging Face model loading |
| `scipy` | Correlation metrics (PLCC, SRCC) |
| `scikit-learn` | Regression metrics (MAE, RMSE) |
| `pydantic` | Schema validation |
| `click` | CLI framework |

---

## 5. Outputs and Deliverables

### Required Deliverables

| Deliverable | Description | Format |
|-------------|-------------|--------|
| **Benchmark Runner** | CLI to execute benchmark runs | Python CLI |
| **Results Dataset** | Structured, versioned results | JSON/Parquet |
| **Arena Leaderboard** | Ranked model comparison | Markdown/HTML |
| **Reproducibility Manifest** | Audit trail per run | YAML |

### CLI Interface

```bash
# Run benchmark on a model
arena run --model-spec ./specs/llama4_base.yaml --dataset diqa5000 --split test

# Run with specific output
arena run --model meta-llama/Llama-4-Maverick --output ./results/

# Generate leaderboard from results
arena leaderboard --results-dir ./results/ --format markdown

# Validate reproducibility
arena validate --manifest ./manifests/run_20251217.yaml
```

### Results Schema

```json
{
  "run_id": "arena_20251217_143022_abc123",
  "timestamp": "2025-12-17T14:30:22Z",
  "model_spec": {
    "source": "huggingface",
    "id": "meta-llama/Llama-4-Maverick",
    "revision": "main",
    "variant": "base"
  },
  "dataset": {
    "name": "diqa5000",
    "split": "test",
    "num_samples": 1000,
    "version": "v1.0"
  },
  "metrics": {
    "overall": {
      "plcc": 0.89,
      "srcc": 0.87,
      "mae": 0.12,
      "rmse": 0.15
    },
    "sharpness": {
      "plcc": 0.85,
      "srcc": 0.83,
      "mae": 0.14,
      "rmse": 0.18
    },
    "color": {
      "plcc": 0.88,
      "srcc": 0.86,
      "mae": 0.11,
      "rmse": 0.14
    },
    "aggregate": {
      "plcc_mean": 0.873,
      "srcc_mean": 0.853,
      "mae_mean": 0.123,
      "rmse_mean": 0.157
    }
  },
  "provenance": {
    "checksum": "sha256:abc123...",
    "config_hash": "sha256:def456...",
    "tokenizer_hash": "sha256:ghi789..."
  },
  "execution": {
    "hardware": "NVIDIA A100 40GB",
    "duration_seconds": 3600,
    "batch_size": 8,
    "seed": 42
  },
  "manifest_path": "./manifests/arena_20251217_143022_abc123.yaml"
}
```

---

## 6. Success Criteria

Project A is considered successful when:

| Criterion | Metric |
|-----------|--------|
| **Multi-model Support** | Multiple model variants can be benchmarked with no code changes |
| **Reproducibility** | Results are reproducible across runs (±0.001 tolerance) |
| **Consistency** | Metrics are consistent and comparable across models |
| **Decision Support** | Stakeholders can confidently select models for Project B/C |

---

## 7. Relationship to Other Projects

```
┌─────────────────────────────────────────────────────────────┐
│                    Project A: Arena                         │
│              (Neutral Judge / Evaluation)                   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐        ┌──────────────┐                  │
│  │  Project B   │ ──────▶│  Project A   │◀────────────────┐│
│  │ Quantization │        │   Evaluates  │                 ││
│  │              │        │   all models │                 ││
│  └──────────────┘        └──────────────┘                 ││
│                                ▲                          ││
│  ┌──────────────┐              │                          ││
│  │  Project C   │ ─────────────┘                          ││
│  │ Fine-Tuning  │                                         ││
│  │              │◀────────────────────────────────────────┘│
│  └──────────────┘                                          │
│        │                                                   │
│        └─── Results inform which models to fine-tune       │
└─────────────────────────────────────────────────────────────┘
```

- **Project B (Quantization)** produces model variants that Project A evaluates
- **Project C (Fine-Tuning)** produces trained variants that Project A evaluates
- **Project A** is the neutral judge for the overall program

---

## 8. Implementation Architecture

### Module Structure

```
src/image_preprocessing_detector/labeling/arena/
├── __init__.py
├── cli.py              # Click-based CLI
├── runner.py           # Benchmark execution engine
├── metrics.py          # PLCC, SRCC, MAE, RMSE calculations
├── leaderboard.py      # Report generation
├── manifest.py         # Reproducibility manifest handling
├── inference/          # Model inference backends
│   ├── __init__.py
│   ├── base.py         # Abstract inference interface
│   ├── huggingface.py  # HF Transformers backend
│   ├── local.py        # Local artifact loading
│   └── api.py          # API model backends
└── datasets/           # Dataset adapters
    ├── __init__.py
    ├── base.py         # Abstract dataset interface
    └── diqa5000.py     # DIQA-5000 adapter
```

### Key Classes

```python
# Abstract inference interface
class ModelInferenceBackend(ABC):
    @abstractmethod
    def load(self, spec: ModelSpec) -> None: ...

    @abstractmethod
    def predict(self, images: list[np.ndarray]) -> list[DIQAPrediction]: ...

    @abstractmethod
    def get_provenance(self) -> dict[str, Any]: ...

# Dataset interface
class BenchmarkDataset(ABC):
    @abstractmethod
    def __iter__(self) -> Iterator[DIQASample]: ...

    @abstractmethod
    def get_split(self, split: str) -> BenchmarkDataset: ...

# Main runner
class ArenaRunner:
    def run(
        self,
        model_spec: ModelSpec,
        dataset: BenchmarkDataset,
        output_dir: Path,
    ) -> BenchmarkResult: ...
```

---

## 9. Timeline

| Week | Milestone |
|------|-----------|
| 1 | CLI scaffold, ModelSpec integration |
| 2 | Metrics implementation (PLCC, SRCC, MAE, RMSE) |
| 3 | HuggingFace inference backend |
| 4 | DIQA-5000 dataset adapter |
| 5 | Results schema, manifest generation |
| 6 | Leaderboard generator (Markdown) |
| 7 | Local artifact backend |
| 8 | API backend (optional) |
| 9 | HTML leaderboard, documentation |
| 10 | Integration testing, hardening |

---

## 10. Open Questions

1. **DIQA-5000 Access**: Is the dataset publicly available? Contact authors?
2. **Test Split Policy**: Should we ever use validation split for reporting?
3. **Batch Size**: Standard batch size across all models?
4. **Hardware Requirements**: Minimum GPU memory for largest models?
5. **API Rate Limits**: How to handle API throttling for large benchmarks?

---

*Last Updated: 2025-12-17*
