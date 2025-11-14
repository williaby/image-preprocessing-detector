# notebooks/

**Purpose**: Jupyter/Colab notebooks for interactive model training and experimentation (Phases 2-3).

## What Goes Here

**✅ Belongs in notebooks/**:
- Google Colab training notebooks (`.ipynb`)
- Jupyter notebooks for data exploration
- Interactive model evaluation notebooks
- Tutorial notebooks for documentation
- Experiment tracking notebooks

**❌ Does NOT belong here** (and where it should go instead):
- **Production training code** → `src/image_preprocessing_detector/training/` (Phase 4+)
- **Utility scripts** → `scripts/` (standalone Python scripts)
- **One-off validation** → `validation/` (non-reusable experimental code)
- **Unit tests** → `tests/` (pytest test files)
- **Configuration files** → `configs/` (YAML/JSON configs)

## Directory Structure

```
notebooks/
├── colab/                      # Google Colab notebooks (Phases 2-3)
│   ├── phase2_iqa_training.ipynb         # IQA model training
│   ├── phase3_yolov8_training.ipynb      # Layout detection training
│   ├── phase3_docres_training.ipynb      # DocRes restoration training
│   └── model_evaluation.ipynb            # Model evaluation utilities
├── exploration/                # Data exploration (future)
│   ├── dataset_analysis.ipynb
│   └── augmentation_test.ipynb
└── README.md
```

## Current Notebooks

### Phase 2: IQA Training
**File**: `colab/phase2_iqa_training.ipynb`

**Purpose**: Train MobileNetV3/EfficientNet multi-label IQA classifier on Google Colab

**Key Features**:
- Auto-mounts Google Drive
- Loads config from `configs/colab_phase2_iqa.yaml`
- Multi-session training with `CheckpointManager`
- Auto-saves checkpoints every 30 min or 5 epochs
- Stops at 11.5 hours to avoid Colab timeout
- Embedded TensorBoard visualization
- Exports to ONNX on completion

**Usage**:
1. Open in Google Colab
2. Runtime → Change runtime type → GPU (V100 recommended)
3. Run all cells
4. Training auto-resumes if session disconnects

### Phase 3: Layout Detection
**File**: `colab/phase3_yolov8_training.ipynb`

**Purpose**: Train YOLOv8 object detector for document layout detection

**Key Features**:
- Multi-session training (5-7 sessions over 5-7 days)
- YOLOv8n/s architecture variants
- COCO-aligned bounding boxes
- Active learning integration (optional)
- Automatic checkpoint management

**Usage**:
1. Prepare dataset in YOLO format (`scripts/prepare_*.py`)
2. Upload to Google Drive
3. Open notebook in Colab
4. Run cells 1-7 for first session
5. Re-run in new sessions to auto-resume

### Model Evaluation
**File**: `colab/model_evaluation.ipynb`

**Purpose**: Evaluate trained models and generate benchmark reports

**Features**:
- Compute mAP, F1, ROC-AUC
- Calibration analysis (ECE, reliability diagrams)
- Confusion matrices
- Per-class metrics
- Benchmark comparison against baselines

## Gitignore Policy

Notebooks are **GITIGNORED** due to:
- Large file sizes with outputs
- Embedded images in outputs
- Frequent changes during experimentation
- Checkpoint metadata

**What IS committed**:
- Cleaned notebooks without outputs (optional, for documentation)
- Notebook templates with placeholders

**Storage**:
- Working notebooks: Google Drive
- Final versions: Export to `.py` format for version control

## Running Notebooks

### In Google Colab
```python
# Cell 1: Mount Drive
from google.colab import drive
drive.mount('/content/drive')

# Cell 2: Setup
%cd /content/drive/MyDrive/image_detection
!pip install -q -r requirements.txt

# Cell 3: Load config
import yaml
with open("configs/colab_phase2_iqa.yaml") as f:
    config = yaml.safe_load(f)

# Cell 4+: Training cells...
```

### Locally (Jupyter)
```bash
# Install Jupyter
poetry add --group dev jupyter

# Start Jupyter
poetry run jupyter notebook

# Open notebooks/colab/phase2_iqa_training.ipynb
# Note: Some Colab-specific features won't work
```

## Distinction from Other Folders

### vs. scripts/
- **notebooks/**: Interactive Jupyter/Colab notebooks (`.ipynb`)
- **scripts/**: Standalone command-line utilities (`.py`, `.sh`)

### vs. validation/
- **notebooks/**: Reusable training and evaluation workflows
- **validation/**: One-off experimental scripts for specific hypotheses

### vs. src/
- **notebooks/**: Exploratory code, not production-ready
- **src/**: Production library code with tests and documentation

## Best Practices

### Cell Organization
1. **Setup Cells**: Imports, Drive mounting, environment setup
2. **Config Cells**: Load configuration files
3. **Data Cells**: Dataset loading and preprocessing
4. **Training Cells**: Model training loops
5. **Evaluation Cells**: Metrics computation and visualization
6. **Export Cells**: Save models and artifacts

### Checkpoint Management
```python
from scripts.checkpoint_manager import CheckpointManager

ckpt_mgr = CheckpointManager(
    checkpoint_dir="/content/drive/MyDrive/checkpoints",
    max_session_hours=11.5,  # Colab free tier limit
    save_interval_minutes=30
)

# In training loop
for epoch in range(start_epoch, config["epochs"]):
    train_one_epoch(model, dataloader, optimizer)

    # Auto-save checkpoint
    ckpt_mgr.save_checkpoint(
        model=model,
        optimizer=optimizer,
        epoch=epoch,
        metrics=metrics
    )

    # Check if approaching session timeout
    if ckpt_mgr.should_stop_session():
        print(f"Stopping at epoch {epoch} to save checkpoint")
        break
```

### Reproducibility
- **Fix random seeds** in first cell
- **Log all hyperparameters**
- **Save training config** alongside checkpoints
- **Version datasets** with commit hashes or DVC tags

## Converting Notebooks to Scripts

For production deployment (Phase 4+):

```bash
# Convert notebook to Python script
jupyter nbconvert --to script notebooks/colab/phase2_iqa_training.ipynb

# Clean up script
# 1. Remove magic commands (%, !!)
# 2. Add argparse for CLI arguments
# 3. Refactor into functions
# 4. Add proper error handling
# 5. Move to src/image_preprocessing_detector/training/
```

## Troubleshooting

### Colab Session Disconnects
- **Solution**: Re-run all cells - CheckpointManager auto-resumes

### Out of Memory
- **Solution**: Reduce batch size in config
- **Alternative**: Use mixed precision training (FP16)

### Slow Training
- **Check GPU**: Verify GPU is allocated (`nvidia-smi`)
- **Data loading**: Use num_workers > 0 in DataLoader
- **Mixed precision**: Enable AMP for faster training

### Google Drive Quota
- **Dataset**: Keep datasets on Drive, not in Colab /content
- **Checkpoints**: Clean old checkpoints periodically
- **Logs**: Use TensorBoard with limited history

## Future: Local Jupyter (Phase 4+)

For local development without Colab:

```bash
# Setup Jupyter environment
poetry add --group dev jupyter jupyterlab ipywidgets

# Launch JupyterLab
poetry run jupyter lab

# Install kernel
poetry run python -m ipykernel install --user --name=image_detection
```

## Documentation

Notebooks can serve as interactive documentation:
- Tutorial notebooks for new contributors
- Example usage notebooks for README
- Benchmark reproduction notebooks for ADRs

**Location**: `docs/notebooks/` (separate from training notebooks)
