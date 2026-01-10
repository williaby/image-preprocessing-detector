---
owner: docs-team
purpose: 'Template for creating consistent model card: documents.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card:'
---

<!--
INSTRUCTIONS:
1. Copy this template to the appropriate subdirectory (production/, classical/, planned/)
2. Replace all {placeholders} with actual values
3. Remove sections marked [OPTIONAL] if not applicable
4. Remove these instructions before committing

TEMPLATE VERSION: 3.0 (HuggingFace-Aligned)
Based on: docs/reference/detection-taxonomy.md
          docs/reference/document-type-taxonomy.md
          docs/reference/metadata-versioning-schema.md
          HuggingFace Model Card Best Practices
-->

---

## YAML Frontmatter (for HuggingFace)

<!--
If publishing to HuggingFace Hub, include this frontmatter at the very top of the file.
Remove this section for internal-only models.
-->

```yaml
---
license: apache-2.0
language: en
tags:
  - image-quality-assessment
  - document-processing
  - {additional-tags}
datasets:
  - {dataset-name}  # if public
metrics:
  - mse
  - ece
  - srcc
  - plcc
pipeline_tag: image-classification
model-index:
  - name: {model_id}
    results:
      - task:
          type: image-quality-assessment
        dataset:
          name: DIQA-5000
          type: custom
        metrics:
          - name: SRCC
            type: srcc
            value: {value}
          - name: PLCC
            type: plcc
            value: {value}
---
```

---

## Model Summary

<!--
REQUIRED: A concise 2-3 sentence summary covering:
- What the model does
- What architecture it's based on
- Primary use case
-->

> {Architecture}-based model for {task description}. {Training method if applicable - e.g., distilled from teacher, fine-tuned on dataset}. Predicts {output description} for {use case} in {pipeline context}.

**Example:**
> ResNet18-based student model for document image quality assessment, distilled from a ResNet50 teacher. Predicts quality scores across blur, lighting, orientation, and occlusion dimensions for preprocessing decisions in RAG pipelines.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `{task}_{architecture}_{variant}_v{major}.{minor}.{patch}` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | Phase {X} ({description}) |
| **Status** | `trained` / `pretrained` / `planned` / `deprecated` |
| **Priority** | P0 (Critical) / P1 (High) / P2 (Medium) / P3 (Low) |
| **Last Updated** | YYYY-MM-DD |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | e.g., ResNet-50 + MultiTaskHead |
| **Parameters** | e.g., 25.6M |
| **Precision** | FP32 / FP16 / INT8 |
| **Input Size** | e.g., 384×384×3 |
| **Output Format** | e.g., 5-class multi-label scores |
| **Output Type** | regression / classification / multi-label |
| **Export Formats** | PyTorch / ONNX / TorchScript |
| **ONNX Opset** | e.g., 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | e.g., Image Quality Assessment |
| **Role in Pipeline** | e.g., Teacher model for high-risk escalation |
| **Upstream Dependencies** | e.g., Text Gate, PDF Type Classifier |
| **Downstream Consumers** | e.g., DQS Calculator, Routing Engine |

### Intended Use

- **Primary**: {Main use case - what it's designed for}
- **Secondary**: {Alternative applications}
- **Out of Scope**: {What this model should NOT be used for - critical archival decisions, legal document authentication, etc.}

---

## 3. Training Details

<!-- Remove this section for pretrained/classical models -->

| Field | Value |
|-------|-------|
| **Dataset** | e.g., OHR-Bench (100K images) |
| **Train/Val/Test Split** | e.g., 80/10/10 |
| **Epochs** | e.g., 50 |
| **Batch Size** | e.g., 128 |
| **Learning Rate** | e.g., 1e-4 with cosine decay |
| **Optimizer** | e.g., AdamW |
| **Weight Decay** | e.g., 0.01 |
| **Loss Function** | e.g., BCE + Focal + Rank |
| **Augmentations** | e.g., Horizontal flip, rotation ±5° |
| **GPU** | e.g., Modal A10 (24GB) |
| **Training Time** | e.g., 1.91 hours |
| **Training Date** | YYYY-MM-DD |
| **Training Script** | e.g., `modal/train_phase2_iqa.py` |
| **Commit SHA** | e.g., `abc123def456` |

### Dataset Composition

<!-- [OPTIONAL] Include for models with complex training data -->

| Component | Description | Size | Source |
|-----------|-------------|------|--------|
| {component_1} | e.g., Document scans | {count} | {source} |
| {component_2} | e.g., Synthetic degradations | {count} | Generated |

### Training Emissions

<!-- [OPTIONAL] Include if tracked with codecarbon or similar -->

| Metric | Value |
|--------|-------|
| **CO2 Emissions (kg)** | {value} |
| **Power Consumption (kWh)** | {value} |
| **Hardware** | {GPU type, count} |
| **Region** | {cloud region} |
| **Tracking Tool** | codecarbon / custom |

---

## 4. Preprocessing Requirements

<!--
IMPORTANT: Document exactly how inputs need to be prepared.
Future you will thank present you.
-->

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | `[batch, channels, height, width]` e.g., `[N, 3, 224, 224]` |
| **Color Space** | RGB / BGR / Grayscale |
| **Value Range** | [0, 1] / [0, 255] / [-1, 1] |
| **Channel Order** | CHW (PyTorch) / HWC (TensorFlow) |

### Normalization

```python
# Required preprocessing values
mean = [{mean_r}, {mean_g}, {mean_b}]  # e.g., [0.485, 0.456, 0.406] for ImageNet
std = [{std_r}, {std_g}, {std_b}]      # e.g., [0.229, 0.224, 0.225] for ImageNet
```

### Resize Strategy

| Field | Value |
|-------|-------|
| **Method** | Resize then center crop / Letterbox / Pad to square |
| **Interpolation** | BILINEAR / BICUBIC / LANCZOS |
| **Aspect Ratio** | Preserved / Distorted |

### Complete Transform Pipeline

```python
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize({resize_size}),           # e.g., 256
    transforms.CenterCrop({crop_size}),         # e.g., 224
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[{mean_values}],
        std=[{std_values}]
    ),
])
```

---

## 5. Performance Metrics

### 5.1 Primary Benchmark

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Validation Loss | {value} | < {target} | ✅/❌ |
| mAP / SRCC | {value} | > {target} | ✅/❌ |
| Precision | {value} | > {target} | ✅/❌ |
| Recall | {value} | > {target} | ✅/❌ |

### 5.2 Per-Class Performance

<!-- [OPTIONAL] Include for multi-class models -->

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| {class_1} | {value} | {value} | {value} | {count} |
| {class_2} | {value} | {value} | {value} | {count} |

### 5.3 Inference Performance

| Device | Latency (p50) | Latency (p95) | Throughput | Memory |
|--------|---------------|---------------|------------|--------|
| T4 GPU | {ms} | {ms} | {img/s} | {GB} |
| A10 GPU | {ms} | {ms} | {img/s} | {GB} |
| CPU (x86) | {ms} | {ms} | {img/s} | {GB} |

### 5.4 Cross-Dataset Validation

<!-- [OPTIONAL] Include for models validated on multiple datasets -->

| Dataset | SRCC | PLCC | ECE | Notes |
|---------|------|------|-----|-------|
| {dataset_1} | {value} | {value} | {value} | Primary |
| {dataset_2} | {value} | {value} | {value} | OOD test |

### 5.5 Calculated Benchmarks

<!--
This section stores benchmark results from official tracking files.
Reference: docs/benchmarks/ for official tracking CSVs.
Add new benchmark results as subsections when evaluated.
-->

#### DIQA-5000 Benchmark

<!-- [OPTIONAL] Include when model has been evaluated on DIQA-5000 -->

| Field | Value |
|-------|-------|
| **Benchmark Date** | YYYY-MM-DD |
| **Samples** | {count} |
| **Success Rate** | {percentage} |
| **GPU** | {gpu_type} |
| **Official Tracking** | [diqa5000_benchmark_results.csv](../../benchmarks/diqa5000_benchmark_results.csv) |

**Correlation Metrics (higher is better)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | {value} | [{lower}, {upper}] | {value} | [{lower}, {upper}] |
| Sharpness | {value} | [{lower}, {upper}] | {value} | [{lower}, {upper}] |
| Color | {value} | [{lower}, {upper}] | {value} | [{lower}, {upper}] |

**Error Metrics (lower is better)**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | {value} | {value} |
| Sharpness | {value} | {value} |
| Color | {value} | {value} |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | {ms} ms |
| Model Load Time | {seconds} s |

<!-- Add additional benchmark sections below as needed -->

---

## 6. Uncertainty & Calibration

<!-- [OPTIONAL] Include for models with uncertainty estimation -->

| Field | Value |
|-------|-------|
| **Calibration Method** | e.g., Temperature scaling |
| **ECE (Expected Calibration Error)** | e.g., 0.06 |
| **MCE (Maximum Calibration Error)** | e.g., 0.12 |
| **Uncertainty Output** | e.g., Softmax entropy per head |
| **Escalation Threshold** | e.g., entropy > 0.7 → teacher |

### Calibration by Dimension

<!-- [OPTIONAL] For multi-output models -->

| Dimension | ECE | MCE | Notes |
|-----------|-----|-----|-------|
| {dim_1} | {value} | {value} | {notes} |
| {dim_2} | {value} | {value} | {notes} |

---

## 7. Limitations & Known Issues

### Limitations

- {Limitation 1}: e.g., "Trained only on OHR-Bench; may not generalize to handwritten documents"
- {Limitation 2}: e.g., "Color dimension performance below target"

### Known Failure Modes

- {Mode 1}: e.g., "High false positive rate on heavily textured backgrounds"
- {Mode 2}: e.g., "Struggles with moiré patterns from screen captures"

### Bias & Fairness Considerations

- {Consideration}: e.g., "Dataset is 85% English documents; non-Latin scripts underrepresented"

---

## 8. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | e.g., ResNet-50 (ImageNet1K_V2) |
| **Parent Version** | e.g., N/A (first version) or `v1.0.0` |
| **Derived Models** | e.g., `iqa_resnet18_student_v1.0.0` (distilled) |
| **Required Libraries** | e.g., PyTorch 2.0+, ONNX Runtime 1.15+ |

### Dependency Versions

```text
torch>=2.0.0
torchvision>=0.15.0
onnxruntime>=1.15.0
numpy>=1.24.0
```

---

## 9. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `model.pt` | PyTorch checkpoint | {size} | `{hash}` |
| `model.onnx` | ONNX export (opset 17) | {size} | `{hash}` |
| `model.torchscript` | TorchScript export | {size} | `{hash}` |
| `config.json` | Model configuration | {size} | `{hash}` |

### Storage Locations

| Environment | Path | Notes |
|-------------|------|-------|
| **GCS (Primary)** | `gs://image_detection_b/models/{model_id}/` | Production storage |
| **E: Drive (Backup)** | `E:/models/{model_id}/` | Local backup |
| **HuggingFace Hub** | `https://huggingface.co/{org}/{model_id}` | Public/private repository |
| **Local Dev** | `models/{model_id}/` | Development copy |

### Artifact Checklist

- [ ] PyTorch checkpoint uploaded to GCS
- [ ] ONNX export validated and uploaded
- [ ] Config JSON matches model version
- [ ] SHA256 hashes recorded
- [ ] E: Drive backup completed
- [ ] HuggingFace repo updated (if applicable)

---

## 10. Inference Example

<!--
REQUIRED: A minimal working code snippet.
This is one of the most valuable sections - future you will thank present you.
-->

### PyTorch Inference

```python
import torch
from torchvision import transforms
from PIL import Image

# Load model
model = torch.load("model.pt", map_location="cpu")
model.eval()

# Preprocessing
transform = transforms.Compose([
    transforms.Resize({resize_size}),
    transforms.CenterCrop({crop_size}),
    transforms.ToTensor(),
    transforms.Normalize(mean=[{mean}], std=[{std}]),
])

# Inference
image = Image.open("document.png").convert("RGB")
input_tensor = transform(image).unsqueeze(0)

with torch.no_grad():
    output = model(input_tensor)

# Post-processing
# {describe output format and how to interpret}
```

### ONNX Inference

```python
import onnxruntime as ort
import numpy as np
from PIL import Image

# Load ONNX model
session = ort.InferenceSession("model.onnx")

# Prepare input (after preprocessing)
input_name = session.get_inputs()[0].name
input_array = np.array(preprocessed_image, dtype=np.float32)

# Run inference
outputs = session.run(None, {input_name: input_array})

# Output shape: {describe output shape}
# Output interpretation: {describe how to use outputs}
```

---

## 11. Deployment Configuration

```yaml
# Production deployment settings
model_id: {model_id}
version: {version}

device_priority:
  - local_gpu
  - modal_gpu
  - cpu  # or BLOCK for heavy models

inference:
  batch_size: 8
  timeout_ms: 100
  warmup_iterations: 3

preprocessing:
  input_size: [{height}, {width}]
  normalize:
    mean: [{mean_r}, {mean_g}, {mean_b}]
    std: [{std_r}, {std_g}, {std_b}]
  color_format: RGB

monitoring:
  prometheus_metrics: true
  log_level: INFO

storage:
  gcs_path: gs://image_detection_b/models/{model_id}/
  local_cache: /tmp/models/{model_id}/
```

---

## 12. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | YYYY-MM-DD | Initial release | {author} |

### Changelog Details

#### v1.0.0 (YYYY-MM-DD)

- Initial model release
- Trained on {dataset}
- Achieves {key metric} on {benchmark}

<!-- Add detailed changelog entries for each version -->

---

## 13. Citation

```bibtex
@misc{{model_id},
  title={{{model_name}: {purpose}}},
  author={{Project A Team}},
  year={{2025}},
  note={{Internal model for document preprocessing pipeline}}
}
```

---

## 14. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | {team/individual} |
| **Technical Contact** | {email/slack} |
| **Review Cadence** | Quarterly |

---

## Production Readiness Checklist

Before marking this model as production-ready:

### Documentation

- [ ] Model Summary written (2-3 sentences)
- [ ] All required sections completed
- [ ] Limitations documented
- [ ] Inference example tested and working

### Performance

- [ ] Performance metrics meet targets
- [ ] Inference latency validated on target hardware
- [ ] Calibration metrics acceptable (if applicable)

### Artifacts

- [ ] PyTorch checkpoint saved
- [ ] ONNX export tested and validated
- [ ] TorchScript export tested (if required)
- [ ] SHA256 hashes recorded

### Storage

- [ ] GCS backup completed
- [ ] E: Drive backup completed
- [ ] HuggingFace repo updated (if public)
- [ ] Local dev copy available

### Registry

- [ ] REGISTRY.md updated
- [ ] README.md links added
- [ ] Version history documented