# Phase 2: ML for Image Quality Assessment - Implementation Plan

**Phase Duration**: 3-4 weeks (Weeks 8-11)
**Status**: 🚀 **READY TO START**
**Dependencies**: Phase 1 Complete ✅, Phase 1B Complete ✅

---

## Executive Summary

Phase 2 focuses on training and deploying machine learning models for improved image quality assessment (IQA). This phase will enhance the classical computer vision methods from Phase 1 with deep learning-based multi-label classification, improving detection accuracy for noise, blur, perspective distortion, and other quality issues.

### Goals

1. **Train multi-label IQA CNN** using MobileNetV3-Small or EfficientNet-B0
2. **Improve detection accuracy** beyond Phase 1 classical methods
3. **Optimize for production** via ONNX export and INT8 quantization
4. **Integrate seamlessly** with existing pipeline through ensemble methods

### Expected Outcomes

- **mAP > 0.88** across all quality issue labels
- **Per-class F1 > 0.85** for all issues (noise, blur, skew, perspective, contrast, orientation)
- **JSON Accuracy > 0.75** (vs Phase 1 baseline of 0.60)
- **Latency < 200ms** per page (CPU with ONNX optimization)
- **Well-calibrated** confidence scores (ECE < 0.05)

---

## Phase 1 → Phase 2 Transition

### What We Built in Phase 1

**Classical Detection Methods** (src/detection/iqa_classical.py):
- ✅ Skew Detection: Hough Transform + Projection Profile (±0.5° accuracy)
- ✅ Blur Detection: Laplacian variance (thresholds: 50-200)
- ✅ Contrast Detection: RMS contrast + histogram std dev
- ✅ Text Detection Gate: Morphological + connected components (95% accuracy)

**Correction Pipeline** (src/correction/corrections.py):
- ✅ Deskew: Affine rotation with guardrails
- ✅ Contrast Enhancement: CLAHE on LAB colorspace
- ✅ Sharpening: Unsharp mask with adaptive amounts

**Infrastructure**:
- ✅ 146 tests, 89.75% coverage
- ✅ Pydantic v2 schema with COCO alignment
- ✅ CLI tool with batch processing
- ✅ DPI upscaling (Phase 1B)

### Phase 1 Limitations (Addressed in Phase 2)

| Issue | Phase 1 Classical | Phase 2 ML |
|-------|------------------|------------|
| **Noise Detection** | ❌ Not implemented | ✅ Multi-label CNN |
| **Perspective Distortion** | ❌ Not implemented | ✅ Multi-label CNN |
| **Orientation** | ❌ Not implemented | ✅ Multi-label CNN |
| **Complex Blur** | ⚠️ Laplacian only | ✅ Improved with ML |
| **Subtle Issues** | ⚠️ Fixed thresholds | ✅ Learned features |

### Integration Strategy

**Ensemble Approach** (Best of Both Worlds):
- Classical methods: Fast, interpretable, reliable for skew/contrast
- ML methods: Better for noise, perspective, subtle degradation
- Ensemble: Confidence-weighted voting or fallback hierarchy

---

## Architecture & Design

### Phase 2 Pipeline Flow

```
Input Image (300 DPI from Phase 1B upscaling)
    ↓
[Text Detection Gate] (from Phase 1)
    ↓
[Classical IQA] (from Phase 1) → Skew, Contrast
    ↓
[ML IQA] (NEW) → Noise, Blur, Perspective, Orientation
    ↓
[Ensemble Fusion] (NEW) → Confidence-weighted predictions
    ↓
[Correction Pipeline] (from Phase 1, updated thresholds)
    ↓
JSON Output with ML metadata
```

### Module Architecture

#### New Components (Phase 2)

**1. ML Detector** (`src/detection/iqa_ml.py`)
- Multi-label CNN inference
- ONNX Runtime integration
- Batch processing support
- Confidence calibration

**2. Ensemble Fusion** (`src/detection/ensemble.py`)
- Combine classical + ML predictions
- Confidence-weighted voting
- Fallback logic for edge cases

**3. Model Training** (`models/iqa/`)
- Architecture definitions (MobileNetV3, EfficientNet)
- Training loop with early stopping
- Evaluation metrics (mAP, F1, ECE)
- ONNX export utilities

**4. Data Pipeline** (`data/`)
- Albumentations augmentation
- Weak supervision (BRISQUE/NIQE)
- PyTorch Dataset/DataLoader
- DVC versioning integration

### Technology Stack

**Deep Learning**:
- PyTorch 2.9.0+ (training)
- torchvision 0.24.0+ (pretrained models)
- timm 0.9.0+ (EfficientNet, MobileNetV3)
- ONNX Runtime 1.15.0+ (production inference)

**Data Augmentation**:
- Albumentations 1.3.0+ (GPU-accelerated)
- Custom document-specific augmentations

**Evaluation**:
- scikit-learn (metrics, calibration)
- matplotlib (visualizations)
- tensorboard (training monitoring)

---

## Implementation Roadmap

### Week 1: Data Collection & Augmentation

**Objective**: Build 50k+ image training dataset with weak supervision

#### Task 1.1: Collect Base Dataset (10k clean images)

**Data Sources**:
1. **RVL-CDIP** (Ryerson Vision Lab Complex Document Information Processing)
   - 400k+ document images across 16 categories
   - Publicly available, well-curated
   - Download: https://www.cs.cmu.edu/~aharley/rvl-cdip/

2. **Tobacco800**
   - 1,290 scanned document images
   - Real-world quality variations
   - Download: http://www.cs.cmu.edu/~aharley/tobacco/

3. **DocBank**
   - 500k+ document pages with layout annotations
   - Born-digital PDFs (high quality baseline)
   - Download: https://github.com/doc-analysis/DocBank

**Deliverables**:
- [ ] Download and organize 10k+ clean document images
- [ ] Create `data/raw/` directory structure
- [ ] Document licensing and attribution
- [ ] DVC tracking for raw dataset

#### Task 1.2: Build Albumentations Pipeline

**Synthetic Augmentations** (documents/augmentation.py):

```python
import albumentations as A

augmentation_pipeline = A.Compose([
    # Noise augmentations
    A.OneOf([
        A.GaussNoise(var_limit=(10.0, 50.0), p=0.5),
        A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=0.3),
        A.MultiplicativeNoise(multiplier=(0.9, 1.1), p=0.2),
    ], p=0.6),

    # Blur augmentations
    A.OneOf([
        A.GaussianBlur(blur_limit=(3, 7), p=0.4),
        A.MotionBlur(blur_limit=7, p=0.3),
        A.Defocus(radius=(3, 7), alias_blur=(0.1, 0.5), p=0.2),
    ], p=0.5),

    # Low contrast augmentations
    A.OneOf([
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.3, p=0.5),
        A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=0.3),
        A.Equalize(p=0.2),
    ], p=0.4),

    # Perspective distortion
    A.Perspective(scale=(0.05, 0.1), p=0.3),

    # Rotation (orientation issues)
    A.Rotate(limit=180, border_mode=0, value=(255, 255, 255), p=0.2),

    # Real-world artifacts
    A.ImageCompression(quality_lower=75, quality_upper=95, p=0.3),
    A.Downscale(scale_min=0.5, scale_max=0.9, p=0.2),
], p=1.0)
```

**Deliverables**:
- [ ] Implement `data/augmentation.py`
- [ ] Generate 40k synthetic augmented images
- [ ] Save augmentation parameters as metadata
- [ ] Visual validation: Sample 100 images for manual review

#### Task 1.3: Weak Supervision Labeling

**Approach**: Automated initial labeling using image quality metrics

**Labeling Functions** (data/weak_supervision.py):

1. **Blur Detection**: Laplacian variance
   - Sharp: variance > 200
   - Medium: 100-200
   - Blurred: < 100

2. **Contrast Detection**: RMS contrast
   - Good: RMS > 0.4
   - Low: RMS < 0.3

3. **Noise Detection**: BRISQUE/NIQE scores
   - Clean: BRISQUE < 30
   - Noisy: BRISQUE > 50

4. **Perspective**: Edge straightness analysis
   - Straight: max angle deviation < 5°
   - Distorted: max angle deviation > 10°

**Snorkel-Style Label Aggregation**:
- Combine multiple weak labeling functions
- Probabilistic label model
- Confidence weighting

**Manual Validation**:
- Review 10-20% of dataset (5-10k images)
- Focus on ambiguous cases (low confidence)
- Use CVAT or Label Studio
- Inter-annotator agreement metrics

**Deliverables**:
- [ ] Implement weak supervision pipeline
- [ ] Generate initial labels for 50k images
- [ ] Manual validation on 5k samples
- [ ] Create ground-truth test set (2k images, real-world only)

#### Task 1.4: Dataset Versioning with DVC

**Setup**:
```bash
# Initialize DVC
poetry run dvc init

# Add datasets
poetry run dvc add data/raw/
poetry run dvc add data/augmented/
poetry run dvc add data/labels/

# Configure remote (S3/GCS/Azure)
poetry run dvc remote add -d storage s3://your-bucket/image-preprocessing-detector

# Push to remote
poetry run dvc push
```

**Deliverables**:
- [ ] DVC initialization
- [ ] Remote storage configuration
- [ ] Version all datasets
- [ ] Document data pipeline in README

---

### Week 2: Model Training

**Objective**: Train multi-label IQA CNN with transfer learning

#### Task 2.1: Implement Model Architectures

**Option 1: MobileNetV3-Small** (Recommended for CPU deployment)

```python
# models/iqa/mobilenetv3.py
import timm
import torch.nn as nn

class MobileNetV3IQA(nn.Module):
    def __init__(self, num_classes=6, pretrained=True):
        super().__init__()
        self.backbone = timm.create_model(
            'mobilenetv3_small_100',
            pretrained=pretrained,
            num_classes=0  # Remove classification head
        )
        self.classifier = nn.Sequential(
            nn.Linear(576, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        features = self.backbone(x)
        return self.classifier(features)
```

**Option 2: EfficientNet-B0** (Balanced accuracy/speed)

```python
# models/iqa/efficientnet.py
import timm
import torch.nn as nn

class EfficientNetIQA(nn.Module):
    def __init__(self, num_classes=6, pretrained=True):
        super().__init__()
        self.backbone = timm.create_model(
            'efficientnet_b0',
            pretrained=pretrained,
            num_classes=0
        )
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        features = self.backbone(x)
        return self.classifier(features)
```

**Output Classes** (6 binary labels):
1. Noise
2. Blur
3. Skew
4. Perspective
5. Low Contrast
6. Orientation

**Deliverables**:
- [ ] Implement MobileNetV3IQA
- [ ] Implement EfficientNetIQA
- [ ] Unit tests for model architectures
- [ ] Validate output shapes

#### Task 2.2: Training Pipeline

**Training Configuration** (models/iqa/config.py):

```python
from dataclasses import dataclass

@dataclass
class TrainingConfig:
    # Model
    model_name: str = "mobilenetv3_small"  # or "efficientnet_b0"
    input_size: int = 224  # or 320 for better accuracy
    num_classes: int = 6

    # Training
    batch_size: int = 32
    num_epochs: int = 50
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4

    # Optimization
    optimizer: str = "adamw"
    scheduler: str = "cosine"  # cosine annealing
    warmup_epochs: int = 5

    # Loss
    loss_fn: str = "bce_with_logits"  # Multi-label classification
    class_weights: Optional[List[float]] = None  # For class imbalance

    # Data
    train_split: float = 0.7
    val_split: float = 0.15
    test_split: float = 0.15
    num_workers: int = 4

    # Early stopping
    patience: int = 10
    min_delta: float = 0.001
```

**Training Loop** (scripts/train_iqa.py):

```python
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

def train_epoch(model, dataloader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    for batch in dataloader:
        images, labels = batch
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(dataloader)

def validate_epoch(model, dataloader, criterion, device):
    model.eval()
    total_loss = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            images, labels = batch
            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item()

            preds = torch.sigmoid(outputs)
            all_preds.append(preds.cpu())
            all_labels.append(labels.cpu())

    return total_loss / len(dataloader), all_preds, all_labels

# Main training loop with early stopping
def train_model(config, train_loader, val_loader):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Initialize model
    if config.model_name == "mobilenetv3_small":
        model = MobileNetV3IQA(num_classes=config.num_classes)
    elif config.model_name == "efficientnet_b0":
        model = EfficientNetIQA(num_classes=config.num_classes)
    model = model.to(device)

    # Loss and optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = AdamW(model.parameters(), lr=config.learning_rate,
                      weight_decay=config.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=config.num_epochs)

    # Training loop
    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(config.num_epochs):
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_preds, val_labels = validate_epoch(model, val_loader, criterion, device)
        scheduler.step()

        print(f"Epoch {epoch+1}/{config.num_epochs}")
        print(f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

        # Early stopping
        if val_loss < best_val_loss - config.min_delta:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), f"models/checkpoints/best_model.pth")
        else:
            patience_counter += 1

        if patience_counter >= config.patience:
            print(f"Early stopping at epoch {epoch+1}")
            break

    return model
```

**Deliverables**:
- [ ] Implement training pipeline
- [ ] Add TensorBoard logging
- [ ] Checkpointing and model saving
- [ ] Training progress visualization
- [ ] Hyperparameter tuning (learning rate, batch size)

#### Task 2.3: Cross-Validation

**5-Fold Cross-Validation**:
- Ensure model generalization
- Reduce overfitting risk
- Provide robust performance estimates

**Deliverables**:
- [ ] Implement k-fold cross-validation
- [ ] Aggregate performance across folds
- [ ] Select best-performing fold for final model

---

### Week 3: Model Evaluation & Optimization

**Objective**: Evaluate model performance and optimize for production

#### Task 3.1: Evaluation Metrics

**Implementation** (models/iqa/evaluation.py):

```python
from sklearn.metrics import (
    precision_recall_fscore_support,
    roc_auc_score,
    average_precision_score,
    confusion_matrix
)
import numpy as np

def compute_metrics(predictions, labels, threshold=0.5):
    """
    Compute comprehensive evaluation metrics.

    Args:
        predictions: numpy array (N, num_classes) with probabilities
        labels: numpy array (N, num_classes) with binary labels
        threshold: float, decision threshold for binary classification

    Returns:
        dict with metrics
    """
    # Binarize predictions
    binary_preds = (predictions >= threshold).astype(int)

    # Per-class metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, binary_preds, average=None, zero_division=0
    )

    # ROC-AUC per class
    roc_auc = []
    for i in range(labels.shape[1]):
        try:
            roc_auc.append(roc_auc_score(labels[:, i], predictions[:, i]))
        except ValueError:
            roc_auc.append(np.nan)

    # Average Precision (AP) per class
    ap_scores = []
    for i in range(labels.shape[1]):
        try:
            ap_scores.append(average_precision_score(labels[:, i], predictions[:, i]))
        except ValueError:
            ap_scores.append(np.nan)

    # Mean Average Precision (mAP)
    mAP = np.nanmean(ap_scores)

    # Overall metrics (micro-average)
    precision_micro, recall_micro, f1_micro, _ = precision_recall_fscore_support(
        labels, binary_preds, average='micro', zero_division=0
    )

    return {
        'per_class_precision': precision,
        'per_class_recall': recall,
        'per_class_f1': f1,
        'per_class_roc_auc': roc_auc,
        'per_class_ap': ap_scores,
        'mAP': mAP,
        'precision_micro': precision_micro,
        'recall_micro': recall_micro,
        'f1_micro': f1_micro,
    }

def compute_calibration_metrics(predictions, labels, n_bins=10):
    """
    Compute Expected Calibration Error (ECE).

    Args:
        predictions: numpy array (N, num_classes) with probabilities
        labels: numpy array (N, num_classes) with binary labels
        n_bins: number of bins for calibration

    Returns:
        dict with calibration metrics
    """
    from sklearn.calibration import calibration_curve

    ece_scores = []
    for i in range(labels.shape[1]):
        # Compute calibration curve
        prob_true, prob_pred = calibration_curve(
            labels[:, i], predictions[:, i], n_bins=n_bins, strategy='uniform'
        )

        # Compute ECE
        ece = np.mean(np.abs(prob_true - prob_pred))
        ece_scores.append(ece)

    return {
        'per_class_ece': ece_scores,
        'mean_ece': np.mean(ece_scores)
    }
```

**Benchmark Targets**:
- mAP > 0.88
- Per-class F1 > 0.85 for all issues
- ECE < 0.05 (well-calibrated)

**Deliverables**:
- [ ] Implement evaluation metrics
- [ ] Compute metrics on test set
- [ ] Generate confusion matrices
- [ ] Create calibration plots (reliability diagrams)

#### Task 3.2: Model Calibration

**Temperature Scaling** (models/iqa/calibration.py):

```python
import torch
import torch.nn as nn
from torch.optim import LBFGS

class TemperatureScaling(nn.Module):
    """
    Temperature scaling for confidence calibration.
    """
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1))

    def forward(self, logits):
        return logits / self.temperature

    def calibrate(self, logits, labels):
        """
        Tune temperature parameter on validation set.
        """
        optimizer = LBFGS([self.temperature], lr=0.01, max_iter=50)
        criterion = nn.BCEWithLogitsLoss()

        def eval():
            optimizer.zero_grad()
            loss = criterion(self.forward(logits), labels)
            loss.backward()
            return loss

        optimizer.step(eval)
        return self.temperature.item()
```

**Deliverables**:
- [ ] Implement temperature scaling
- [ ] Calibrate on validation set
- [ ] Verify ECE improvement

#### Task 3.3: Threshold Tuning

**Per-Class Threshold Optimization**:
- Optimize F1-score for each issue type
- Balance precision vs recall based on use case
- Consider cost of false positives (over-correction)

**Deliverables**:
- [ ] Implement threshold optimization
- [ ] Generate precision-recall curves
- [ ] Document optimal thresholds per class

#### Task 3.4: ONNX Export

**Export to ONNX** (scripts/export_onnx.py):

```python
import torch
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType

def export_to_onnx(model, output_path, input_size=224):
    """
    Export PyTorch model to ONNX format.
    """
    model.eval()
    dummy_input = torch.randn(1, 3, input_size, input_size)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )

    # Verify ONNX model
    onnx_model = onnx.load(output_path)
    onnx.checker.check_model(onnx_model)
    print(f"ONNX model exported to {output_path}")

def quantize_onnx_model(input_path, output_path):
    """
    Quantize ONNX model to INT8.
    """
    quantize_dynamic(
        input_path,
        output_path,
        weight_type=QuantType.QUInt8
    )
    print(f"Quantized model saved to {output_path}")
```

**Deliverables**:
- [ ] Export trained model to ONNX
- [ ] INT8 quantization via ONNX Runtime
- [ ] Benchmark inference speed (CPU)
- [ ] Verify accuracy after quantization

---

### Week 4: Integration & Testing

**Objective**: Integrate ML models into existing pipeline

#### Task 4.1: Implement ML Detector

**ML Detector** (src/detection/iqa_ml.py):

```python
"""ML-based Image Quality Assessment detector."""

import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import List, Dict, Tuple
import cv2

from image_preprocessing_detector.schema import DetectedIssue
from image_preprocessing_detector.utils.logging import get_logger

logger = get_logger(__name__)


class IQAMLDetector:
    """
    ML-based IQA detector using ONNX Runtime.
    """

    ISSUE_CLASSES = [
        "noise",
        "blur",
        "skew",
        "perspective",
        "low_contrast",
        "orientation"
    ]

    SEVERITY_THRESHOLDS = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.8,
        "critical": 0.9
    }

    def __init__(
        self,
        model_path: str | Path,
        input_size: int = 224,
        confidence_threshold: float = 0.5
    ):
        """
        Initialize ML IQA detector.

        Args:
            model_path: Path to ONNX model file
            input_size: Input image size (224 or 320)
            confidence_threshold: Minimum confidence for detection
        """
        self.model_path = Path(model_path)
        self.input_size = input_size
        self.confidence_threshold = confidence_threshold

        # Initialize ONNX Runtime session
        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=['CPUExecutionProvider']
        )

        logger.info(f"Loaded ML IQA model from {self.model_path}")

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for model input.

        Args:
            image: Input image (H, W, 3) in BGR format

        Returns:
            Preprocessed image (1, 3, H, W) in RGB format
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize
        resized = cv2.resize(image_rgb, (self.input_size, self.input_size))

        # Normalize (ImageNet stats)
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        normalized = (resized / 255.0 - mean) / std

        # Transpose to (C, H, W) and add batch dimension
        transposed = normalized.transpose(2, 0, 1)
        batched = np.expand_dims(transposed, axis=0).astype(np.float32)

        return batched

    def postprocess_predictions(
        self,
        logits: np.ndarray
    ) -> List[Tuple[str, float]]:
        """
        Convert model logits to issue predictions.

        Args:
            logits: Model output logits (1, num_classes)

        Returns:
            List of (issue_type, confidence) tuples
        """
        # Apply sigmoid
        probabilities = 1 / (1 + np.exp(-logits[0]))

        # Filter by confidence threshold
        detected_issues = []
        for idx, prob in enumerate(probabilities):
            if prob >= self.confidence_threshold:
                issue_type = self.ISSUE_CLASSES[idx]
                detected_issues.append((issue_type, float(prob)))

        return detected_issues

    def _get_severity(self, confidence: float) -> str:
        """Determine severity level based on confidence."""
        if confidence >= self.SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif confidence >= self.SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif confidence >= self.SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    def detect(self, image: np.ndarray) -> List[DetectedIssue]:
        """
        Detect quality issues using ML model.

        Args:
            image: Input image (H, W, 3) in BGR format

        Returns:
            List of DetectedIssue objects
        """
        # Preprocess
        input_tensor = self.preprocess_image(image)

        # Inference
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        logits = self.session.run([output_name], {input_name: input_tensor})[0]

        # Postprocess
        detected = self.postprocess_predictions(logits)

        # Convert to DetectedIssue objects
        issues = []
        for issue_type, confidence in detected:
            issues.append(DetectedIssue(
                type=issue_type,
                confidence=confidence,
                severity=self._get_severity(confidence),
                metrics={
                    "ml_confidence": confidence,
                    "detector": "ml"
                }
            ))

        logger.info(f"ML detector found {len(issues)} issues")
        return issues
```

**Deliverables**:
- [ ] Implement IQAMLDetector class
- [ ] ONNX Runtime integration
- [ ] Preprocessing pipeline (resize, normalize)
- [ ] Postprocessing (sigmoid, thresholding)
- [ ] Unit tests for ML detector

#### Task 4.2: Ensemble Fusion

**Ensemble Strategy** (src/detection/ensemble.py):

```python
"""Ensemble fusion for classical + ML IQA detectors."""

from typing import List, Dict
from image_preprocessing_detector.schema import DetectedIssue
from image_preprocessing_detector.utils.logging import get_logger

logger = get_logger(__name__)


class EnsembleDetector:
    """
    Fuse predictions from classical and ML detectors.
    """

    def __init__(
        self,
        strategy: str = "confidence_weighted",
        classical_weight: float = 0.4,
        ml_weight: float = 0.6
    ):
        """
        Initialize ensemble detector.

        Args:
            strategy: Fusion strategy ("voting", "confidence_weighted", "fallback")
            classical_weight: Weight for classical detections (if weighted)
            ml_weight: Weight for ML detections (if weighted)
        """
        self.strategy = strategy
        self.classical_weight = classical_weight
        self.ml_weight = ml_weight

    def fuse(
        self,
        classical_issues: List[DetectedIssue],
        ml_issues: List[DetectedIssue]
    ) -> List[DetectedIssue]:
        """
        Fuse classical and ML predictions.

        Args:
            classical_issues: Issues from classical detector
            ml_issues: Issues from ML detector

        Returns:
            Fused list of DetectedIssue objects
        """
        if self.strategy == "voting":
            return self._voting_fusion(classical_issues, ml_issues)
        elif self.strategy == "confidence_weighted":
            return self._confidence_weighted_fusion(classical_issues, ml_issues)
        elif self.strategy == "fallback":
            return self._fallback_fusion(classical_issues, ml_issues)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _voting_fusion(
        self,
        classical_issues: List[DetectedIssue],
        ml_issues: List[DetectedIssue]
    ) -> List[DetectedIssue]:
        """
        Majority voting: Include issue if detected by either detector.
        """
        # Aggregate by issue type
        issue_map = {}

        for issue in classical_issues:
            issue_map[issue.type] = issue

        for issue in ml_issues:
            if issue.type in issue_map:
                # Both detected: Average confidence
                existing = issue_map[issue.type]
                avg_confidence = (existing.confidence + issue.confidence) / 2
                issue_map[issue.type] = DetectedIssue(
                    type=issue.type,
                    confidence=avg_confidence,
                    severity=max(existing.severity, issue.severity, key=lambda x: ["low", "medium", "high", "critical"].index(x)),
                    metrics={
                        "classical_confidence": existing.confidence,
                        "ml_confidence": issue.confidence,
                        "detector": "ensemble_voting"
                    }
                )
            else:
                # Only ML detected
                issue_map[issue.type] = issue

        return list(issue_map.values())

    def _confidence_weighted_fusion(
        self,
        classical_issues: List[DetectedIssue],
        ml_issues: List[DetectedIssue]
    ) -> List[DetectedIssue]:
        """
        Weighted confidence: Combine predictions with weights.
        """
        issue_map = {}

        for issue in classical_issues:
            weighted_conf = issue.confidence * self.classical_weight
            issue_map[issue.type] = {
                "classical": issue,
                "total_confidence": weighted_conf
            }

        for issue in ml_issues:
            weighted_conf = issue.confidence * self.ml_weight
            if issue.type in issue_map:
                issue_map[issue.type]["ml"] = issue
                issue_map[issue.type]["total_confidence"] += weighted_conf
            else:
                issue_map[issue.type] = {
                    "ml": issue,
                    "total_confidence": weighted_conf
                }

        # Convert to DetectedIssue objects
        fused_issues = []
        for issue_type, data in issue_map.items():
            classical_issue = data.get("classical")
            ml_issue = data.get("ml")
            total_conf = data["total_confidence"]

            # Determine severity
            if classical_issue and ml_issue:
                severity = max(
                    classical_issue.severity,
                    ml_issue.severity,
                    key=lambda x: ["low", "medium", "high", "critical"].index(x)
                )
            elif classical_issue:
                severity = classical_issue.severity
            else:
                severity = ml_issue.severity

            fused_issues.append(DetectedIssue(
                type=issue_type,
                confidence=min(total_conf, 1.0),
                severity=severity,
                metrics={
                    "classical_confidence": classical_issue.confidence if classical_issue else 0.0,
                    "ml_confidence": ml_issue.confidence if ml_issue else 0.0,
                    "detector": "ensemble_weighted"
                }
            ))

        return fused_issues

    def _fallback_fusion(
        self,
        classical_issues: List[DetectedIssue],
        ml_issues: List[DetectedIssue]
    ) -> List[DetectedIssue]:
        """
        Fallback strategy: Use classical for skew/contrast, ML for others.
        """
        classical_priority = {"skew", "low_contrast"}
        ml_priority = {"noise", "blur", "perspective", "orientation"}

        fused_issues = []

        # Add classical detections for priority issues
        for issue in classical_issues:
            if issue.type in classical_priority:
                fused_issues.append(issue)

        # Add ML detections for priority issues (if not already detected by classical)
        detected_types = {issue.type for issue in fused_issues}
        for issue in ml_issues:
            if issue.type in ml_priority or issue.type not in detected_types:
                fused_issues.append(issue)

        return fused_issues
```

**Deliverables**:
- [ ] Implement ensemble strategies (voting, weighted, fallback)
- [ ] Unit tests for ensemble fusion
- [ ] Integration tests with classical + ML detectors

#### Task 4.3: Pipeline Integration

**Update Detection Pipeline**:
- Integrate ML detector alongside classical detector
- Add ensemble fusion step
- Update JSON output with ML metadata
- Preserve backward compatibility

**Schema Updates** (src/schema.py):
- Add `detector_type` field to `DetectedIssue` ("classical" | "ml" | "ensemble")
- Add `model_version` to `processing_version`

**Deliverables**:
- [ ] Integrate ML detector into pipeline
- [ ] Update schema with ML metadata
- [ ] End-to-end integration tests
- [ ] CLI support for ML models

#### Task 4.4: A/B Testing

**Comparison Framework**:
- Classical only
- ML only
- Ensemble (voting)
- Ensemble (weighted)
- Ensemble (fallback)

**Metrics**:
- Detection accuracy (precision, recall, F1)
- JSON Accuracy on test set
- Processing latency
- OCR accuracy improvement (if available)

**Deliverables**:
- [ ] A/B testing script
- [ ] Performance comparison report
- [ ] Recommend best ensemble strategy

#### Task 4.5: Testing

**Unit Tests**:
- [ ] Test ML detector preprocessing
- [ ] Test ML detector inference
- [ ] Test ensemble fusion strategies
- [ ] Test schema updates

**Integration Tests**:
- [ ] End-to-end pipeline with ML detector
- [ ] ONNX model loading and inference
- [ ] Ensemble with classical detector
- [ ] JSON output validation

**Performance Tests**:
- [ ] Latency benchmarks (CPU)
- [ ] Memory usage profiling
- [ ] Throughput measurement

**Coverage Target**: Maintain 80%+ coverage

---

## Deliverables Checklist

### Week 1: Data
- [ ] 10k+ clean document images collected
- [ ] Albumentations pipeline implemented
- [ ] 50k augmented images generated
- [ ] Weak supervision labels generated
- [ ] 5k manually validated samples
- [ ] 2k ground-truth test set
- [ ] DVC versioning configured

### Week 2: Training
- [ ] MobileNetV3 architecture implemented
- [ ] EfficientNet architecture implemented
- [ ] Training pipeline with early stopping
- [ ] TensorBoard logging
- [ ] Cross-validation completed
- [ ] Best model checkpointed

### Week 3: Evaluation
- [ ] Evaluation metrics implemented
- [ ] Test set performance: mAP > 0.88
- [ ] Calibration: ECE < 0.05
- [ ] Temperature scaling applied
- [ ] Threshold optimization completed
- [ ] ONNX export successful
- [ ] INT8 quantization completed

### Week 4: Integration
- [ ] ML detector implemented (iqa_ml.py)
- [ ] Ensemble detector implemented (ensemble.py)
- [ ] Pipeline integration complete
- [ ] Schema updates complete
- [ ] A/B testing completed
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] Documentation updated

---

## Success Criteria

### Model Performance
- ✅ mAP > 0.88 across all labels
- ✅ Per-class F1 > 0.85 for all issues
- ✅ ECE < 0.05 (well-calibrated)

### End-to-End Pipeline
- ✅ JSON Accuracy > 0.75 (vs Phase 1 baseline of 0.60)
- ✅ Latency < 200ms per page (CPU with ONNX)
- ✅ No regression in existing functionality

### Code Quality
- ✅ 80%+ test coverage maintained
- ✅ All pre-commit hooks passing (Ruff, MyPy, Bandit)
- ✅ MyPy strict mode on src/

### Documentation
- ✅ Phase 2 completion summary
- ✅ Model documentation (architecture, training, performance)
- ✅ Integration guide for downstream users
- ✅ Updated README and PROJECT_PLAN

---

## Risk Assessment & Mitigation

### Risk 1: Synthetic→Real Domain Gap
**Likelihood**: MEDIUM
**Impact**: HIGH
**Mitigation**:
- Seed training data with 20% real-world images
- Use artifact-specific augmentations (JPEG compression, halftone)
- Test exclusively on real-world holdout set
- Active learning to mine production failures

### Risk 2: Over-Correction Harm
**Likelihood**: MEDIUM
**Impact**: HIGH
**Mitigation**:
- Maintain confidence thresholds for corrections
- A/B test OCR accuracy with/without corrections
- Preserve original images for rollback
- Do-no-harm guardrails from Phase 1

### Risk 3: Model Drift
**Likelihood**: HIGH (over time)
**Impact**: MEDIUM
**Mitigation**:
- Telemetry for confidence score distributions
- Periodic calibration on fresh validation set
- Drift detection (KL divergence monitoring)
- Scheduled quarterly reevaluation

### Risk 4: Latency Regression
**Likelihood**: LOW
**Impact**: MEDIUM
**Mitigation**:
- ONNX optimization and INT8 quantization
- Batch inference support
- Early exit on clean pages
- Fallback to classical for time-sensitive cases

---

## Dependencies & Prerequisites

### Software Dependencies
- ✅ PyTorch 2.9.0+ (already in pyproject.toml)
- ✅ torchvision 0.24.0+
- ✅ timm 0.9.0+
- ✅ albumentations 1.3.0+
- ✅ onnxruntime 1.15.0+
- ✅ scikit-learn (for metrics)
- ✅ matplotlib (for visualizations)
- ✅ tensorboard (for training monitoring)

### Infrastructure
- GPU for training: NVIDIA GPU with 8GB+ VRAM (RTX 3080, A4000, or cloud equivalent)
- Cloud GPU option: ~$1.50/hr for V100/A10 (estimated $75 for 50 GPU-hours)
- Storage: 50GB for datasets and models

### Phase 1/1B Completion
- ✅ Phase 1 complete (classical methods, 89.75% coverage)
- ✅ Phase 1B complete (DPI upscaling, 100% test pass rate)
- ✅ Pydantic schema with COCO alignment
- ✅ CLI tool and batch processing

---

## Next Steps After Phase 2

**Phase 3: ML for Document Layout Detection** (Weeks 12-16)
- YOLOv8 training for tables, images, handwriting, formulas
- Element-level IQA using Phase 2 models
- Active learning for custom annotations
- Production optimization (TensorRT, batching)

**Phase 2 → Phase 3 Integration Points**:
- ML IQA models will be applied per-element (detected by YOLOv8)
- ONNX models can be shared across pipeline stages
- Ensemble strategies can extend to layout detection

---

## Conclusion

Phase 2 will significantly enhance the image preprocessing detection system by introducing state-of-the-art deep learning models for quality assessment. The combination of classical methods (fast, interpretable) and ML methods (accurate, robust) through ensemble fusion provides the best of both worlds.

**Key Success Factors**:
1. **Synthetic data generation** with weak supervision minimizes annotation burden
2. **Transfer learning** from ImageNet-pretrained models accelerates training
3. **Ensemble fusion** preserves Phase 1 reliability while improving accuracy
4. **ONNX optimization** ensures production-ready performance on CPU
5. **Comprehensive testing** maintains code quality and prevents regressions

**Expected Impact**:
- 15-25% improvement in detection accuracy (mAP 0.88 vs Phase 1 baseline)
- Expanded coverage (noise, perspective, orientation detection)
- Production-ready latency (<200ms CPU with ONNX INT8)
- Scalable to Phase 3 layout detection

**Ready to begin Phase 2**: ✅

---

*Generated: 2025-11-11*
*Branch: claude/review-phase-2-plan-011CV1FwgufQeoCq19gBPXD4*
*Next: Execute Week 1 tasks (Data Collection & Augmentation)*
