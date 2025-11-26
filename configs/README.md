<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: CC0-1.0
-->

# configs/

**Purpose**: Training configuration files for Colab and local model training (Phases 2-3).

## What Goes Here

**✅ Belongs in configs/**:

- Training hyperparameter configs (YAML/JSON)
- Colab-specific training configs (`colab_phase2_iqa.yaml`, `colab_phase3_yolov8.yaml`)
- Model architecture configs (layer sizes, activations, etc.)
- Dataset configuration files (`dataset.yaml` for YOLO)
- Augmentation pipeline configs

**❌ Does NOT belong here** (and where it should go instead):

- **Trained model weights** → `models/` (`.pth`, `.onnx`, `.safetensors` files)
- **Application config** → `src/image_preprocessing_detector/config.py` (runtime config)
- **Environment variables** → `.env` (secrets, API keys)
- **Infrastructure config** → `.github/workflows/` (CI/CD configs)
- **Documentation config** → `mkdocs.yml` (root-level)

## Current Configuration Files

### Phase 2: IQA Training

- `colab_phase2_iqa.yaml` - MobileNetV3/EfficientNet training config for Google Colab
- `colab_phase2_iqa_gcs.yaml` - IQA training with GCS dataset integration

**Key Settings**:

```yaml
model:
  architecture: mobilenet_v3_small
  num_classes: 6  # noise, blur, skew, perspective, contrast, orientation
  pretrained: true

training:
  batch_size: 64
  epochs: 50
  learning_rate: 0.001
  optimizer: adamw

data:
  image_size: 224
  augmentation: albumentations
  train_split: 0.7
  val_split: 0.15
  test_split: 0.15
```

### Phase 3: Layout Detection

- `colab_phase3_yolov8.yaml` - YOLOv8n/s training config for layout detection

**Key Settings**:

```yaml
model:
  architecture: yolov8n
  classes: [table, image, handwriting, formula]

training:
  batch_size: 16
  epochs: 100
  imgsz: 640

data:
  path: /content/drive/MyDrive/datasets/layout
  yaml: dataset.yaml  # YOLO format dataset config
```

## Configuration Structure

All configs follow this structure:

```yaml
# Model architecture
model:
  architecture: <model_name>
  pretrained: <true|false>
  checkpoint: <path_to_checkpoint>  # For resume

# Training hyperparameters
training:
  batch_size: <int>
  epochs: <int>
  learning_rate: <float>
  optimizer: <adamw|adam|sgd>
  scheduler: <cosine|step|exponential>

# Data settings
data:
  image_size: <int>
  augmentation: <none|albumentations|torchvision>
  dataset_path: <path>

# Colab-specific
colab:
  mount_drive: true
  checkpoint_dir: /content/drive/MyDrive/checkpoints
  log_dir: /content/drive/MyDrive/logs
```

## Usage

### Loading Configs in Training Scripts

```python
import yaml
from pathlib import Path

def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)

# Load Phase 2 IQA config
config = load_config(Path("configs/colab_phase2_iqa.yaml"))
model = build_model(config["model"])
trainer = Trainer(config["training"])
```

### Using in Colab Notebooks

```python
# In Colab notebook
!cp configs/colab_phase2_iqa.yaml /content/drive/MyDrive/configs/

# Load in training cell
import yaml
with open("/content/drive/MyDrive/configs/colab_phase2_iqa.yaml") as f:
    config = yaml.safe_load(f)
```

## Distinction from Other Folders

### vs. models/

- **configs/**: Text-based configuration files (YAML/JSON)
- **models/**: Binary trained model weights (`.pth`, `.onnx`)

### vs. data/

- **configs/**: Training hyperparameters and model architecture
- **data/**: Actual dataset files (images, annotations)

### vs. src/

- **configs/**: Static configuration files for training
- **src/**: Python code that reads and uses these configs

## Adding New Configurations

When creating a new config file:

1. **Naming**: Use descriptive names: `<platform>_<phase>_<model>.yaml`
   - Example: `colab_phase3_yolov8.yaml`, `local_phase2_efficientnet.yaml`
2. **Validation**: Validate YAML syntax before committing
3. **Documentation**: Add inline comments explaining non-obvious settings
4. **Defaults**: Provide sensible defaults that work out-of-the-box
5. **Version Control**: Commit configs to git (they're small text files)

## Configuration Best Practices

1. **Reproducibility**: Configs should fully specify training conditions
2. **Platform-Specific**: Separate configs for Colab vs. local vs. cloud
3. **Comments**: Explain why specific values were chosen
4. **Environment Variables**: Use `${ENV_VAR}` syntax for secrets/paths
5. **Validation**: Create Pydantic models to validate config schema

## Example: Creating a New Config

```yaml
# configs/colab_phase3_docres.yaml
# DocRes unified preprocessing model (Phase 3)

model:
  architecture: docres_cnn
  tasks: [dewarp, deshadow, deblur, binarize, contrast]
  backbone: resnet50
  pretrained: true

training:
  batch_size: 8  # Lower due to larger model
  epochs: 30
  learning_rate: 0.0001
  optimizer: adamw
  warmup_epochs: 3

data:
  image_size: 512  # Higher res for document restoration
  dataset_path: /content/drive/MyDrive/datasets/docres
  augmentation: none  # Degradation is already synthetic

colab:
  mount_drive: true
  checkpoint_dir: /content/drive/MyDrive/checkpoints/docres
  session_timeout: 11.5  # Auto-save before Colab timeout
```

## Version Control

- ✅ **Commit configs to git** (small text files, essential for reproducibility)
- ❌ **Don't commit**:
  - Generated configs with secrets/credentials
  - Experiment-specific configs with hardcoded paths
  - Temporary configs created by automated tuning

## Integration with Training Pipeline

Configs are loaded by:

- `scripts/colab_utils.py` - Colab training setup
- `notebooks/colab/phase2_iqa_training.ipynb` - Phase 2 notebook
- `notebooks/colab/phase3_yolov8_training.ipynb` - Phase 3 notebook
- (Phase 4+) `src/image_preprocessing_detector/training/` - Production training code
