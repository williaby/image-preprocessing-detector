# models/

**Purpose**: Trained model weights and exported inference models (ONNX, PyTorch).

## What Goes Here

**✅ Belongs in models/**:

- Trained model weights (`.pth`, `.pt`, `.safetensors`)
- Exported ONNX models (`.onnx`)
- Quantized models (INT8, FP16)
- Model checkpoints from training
- Model metadata files (version, architecture, metrics)

**❌ Does NOT belong here** (and where it should go instead):

- **Training configuration** → `configs/` (YAML/JSON hyperparameters)
- **Training code** → `src/image_preprocessing_detector/training/` (Phase 4+)
- **Training datasets** → `data/training/` (images, annotations)
- **Benchmark results** → `benchmarks/` (evaluation metrics, reports)
- **Training logs** → Ignored by git, stored in `logs/` or Google Drive

## Directory Structure

```text
models/
├── .gitkeep
├── iqa/                        # Phase 2: IQA models
│   ├── mobilenet_v3_small/
│   │   ├── best.pth           # Best PyTorch checkpoint
│   │   ├── best.onnx          # Exported ONNX model
│   │   ├── best_int8.onnx     # INT8 quantized
│   │   ├── metadata.json      # Model info (version, metrics)
│   │   └── config.yaml        # Training config snapshot
│   └── efficientnet_b0/
│       ├── best.pth
│       └── best.onnx
├── layout/                     # Phase 3: Layout detection
│   ├── yolov8n/
│   │   ├── best.pt
│   │   ├── best.onnx
│   │   └── metadata.json
│   └── yolov8s/
│       └── best.pt
├── docres/                     # Phase 3: Document restoration
│   └── docres_unified/
│       ├── best.pth
│       └── metadata.json
└── README.md
```text

## Gitignore Patterns

**All model files are gitignored** to avoid bloating the repository:

```gitignore
# From .gitignore
models/**/*.pth
models/**/*.onnx
models/**/*.pt
models/**/*.safetensors
!models/.gitkeep
```text

**Where models are actually stored**:

- **During training**: Google Drive (`/content/drive/MyDrive/models/`)
- **For distribution**: Google Cloud Storage bucket
- **Local development**: Downloaded on-demand to `models/` (gitignored)

## Model Metadata

Each trained model should have a `metadata.json` file:

```json
{
  "model_name": "mobilenet_v3_small",
  "task": "iqa_multi_label",
  "version": "1.0.0",
  "phase": 2,
  "training_date": "2025-01-15",
  "framework": "pytorch",
  "architecture": {
    "backbone": "mobilenet_v3_small",
    "num_classes": 6,
    "input_size": [224, 224],
    "pretrained": true
  },
  "metrics": {
    "mAP": 0.89,
    "f1_micro": 0.87,
    "ece": 0.04
  },
  "training": {
    "epochs": 50,
    "batch_size": 64,
    "learning_rate": 0.001,
    "dataset": "iqa_phase2_50k",
    "config_file": "configs/colab_phase2_iqa.yaml"
  },
  "export": {
    "onnx_path": "models/iqa/mobilenet_v3_small/best.onnx",
    "opset_version": 17,
    "quantization": "fp32"
  }
}
```text

## Loading Models

### PyTorch Models

```python
import torch
from pathlib import Path

model_path = Path("models/iqa/mobilenet_v3_small/best.pth")
checkpoint = torch.load(model_path, map_location="cpu")
model.load_state_dict(checkpoint["state_dict"])
```text

### ONNX Models

```python
import onnxruntime as ort

session = ort.InferenceSession(
    "models/iqa/mobilenet_v3_small/best.onnx",
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)
```text

## Model Versioning

Follow Semantic Versioning for models:

- **MAJOR**: Breaking changes to input/output schema
- **MINOR**: New capabilities or improved accuracy
- **PATCH**: Bug fixes, quantization, optimization

Example: `mobilenet_v3_small-v1.2.0.onnx`

## Downloading Models

Models are hosted on GCS and downloaded on-demand:

```bash
# Download Phase 2 IQA model
bash scripts/gcs_helpers.sh download_model iqa/mobilenet_v3_small/best.onnx

# Download all Phase 2 models
bash scripts/gcs_helpers.sh download_models iqa/
```text

## Model Size Guidelines

| Model Type | Format | Size Range | Quantization |
|-----------|--------|------------|--------------|
| IQA (MobileNetV3) | `.pth` | 10-20 MB | N/A |
| IQA (MobileNetV3) | `.onnx` | 8-15 MB | FP32 |
| IQA (MobileNetV3) | `.onnx` | 3-6 MB | INT8 |
| Layout (YOLOv8n) | `.pt` | 15-25 MB | N/A |
| Layout (YOLOv8n) | `.onnx` | 12-20 MB | FP32 |
| DocRes | `.pth` | 80-120 MB | N/A |

## Distinction from Other Folders

### vs. configs/

- **models/**: Binary model weights (`.pth`, `.onnx`) - GITIGNORED
- **configs/**: Text configuration files (`.yaml`) - COMMITTED to git

### vs. data/

- **models/**: Trained neural network weights
- **data/**: Input datasets (images, annotations)

### vs. benchmarks/

- **models/**: The model artifacts themselves
- **benchmarks/**: Evaluation results and performance metrics

## Exporting Models

### PyTorch → ONNX

```python
import torch

# Load trained model
model = load_model("configs/colab_phase2_iqa.yaml")
checkpoint = torch.load("models/iqa/mobilenet_v3_small/best.pth")
model.load_state_dict(checkpoint["state_dict"])

# Export to ONNX
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    model,
    dummy_input,
    "models/iqa/mobilenet_v3_small/best.onnx",
    opset_version=17,
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={"input": {0: "batch_size"}}
)
```text

### INT8 Quantization

```python
from onnxruntime.quantization import quantize_dynamic, QuantType

quantize_dynamic(
    "models/iqa/mobilenet_v3_small/best.onnx",
    "models/iqa/mobilenet_v3_small/best_int8.onnx",
    weight_type=QuantType.QInt8
)
```text

## CI/CD Integration

Models are NOT included in CI/CD:

- **Tests**: Use mocked models or tiny fixtures from `data/test_fixtures/`
- **Integration Tests**: Download specific model versions from GCS
- **Production**: Models deployed separately via model registry (Phase 4+)

## Model Registry (Phase 4+)

Future: Integrate with model registry for versioning and deployment:

- **MLflow**: Track experiments, log models, deploy endpoints
- **Weights & Biases**: Track training runs, compare models
- **GCS with versioning**: Simple bucket-based versioning

## Phase-Specific Models

### Phase 2: IQA Models

- `models/iqa/mobilenet_v3_small/` - Primary IQA model
- `models/iqa/efficientnet_b0/` - Alternative (if trained)

### Phase 3: Layout Detection

- `models/layout/yolov8n/` - Fast layout detector
- `models/layout/yolov8s/` - Higher accuracy variant

### Phase 3: Document Restoration

- `models/docres/docres_unified/` - DocRes 5-in-1 model

### Phase 4: Ensemble Models

- `models/ensemble/` - Combined IQA + layout pipelines

## Security & Licensing

- **DO NOT** commit proprietary or licensed models to public repos
- Include LICENSE file in model directories if redistributing
- Document dataset licenses in model metadata
- Scan models for embedded secrets before distribution
