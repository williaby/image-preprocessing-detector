<!--
SPDX-FileCopyrightText: 2025 Byron Williams

SPDX-License-Identifier: CC-BY-4.0
-->

# Text Detection Gate vs YOLOv10-doc Benchmark

**Purpose:** Determine if implementing a text detection gate (ensemble heuristics) provides meaningful performance benefits over always running YOLOv10-doc layout detection.

**Decision Criteria:**
- If YOLOv10-doc latency < 20ms on all document types → **SKIP gate** (not worth complexity)
- If YOLOv10-doc latency > 50ms on pure images → **IMPLEMENT gate** (meaningful savings)
- If YOLOv10-doc latency 20-50ms → **MARGINAL** (decision based on complexity tolerance)

---

## Benchmark Design

### Test Datasets

**1. Pure Images (No Text):**
- Charts and diagrams (n=50)
- Photographs (n=50)
- Infographics without text (n=25)
- Maps and schematics (n=25)
- **Total:** 150 pure image pages

**2. Text Documents (Single Column):**
- Academic papers single column (n=50)
- Novels/books (n=50)
- Simple reports (n=25)
- **Total:** 125 single-column pages

**3. Text Documents (Multi-Column):**
- Academic papers two-column (n=50)
- Newspapers (n=50)
- Magazines (n=25)
- **Total:** 125 multi-column pages

**4. Complex Documents:**
- Technical manuals with mixed content (n=50)
- Financial reports with tables (n=50)
- **Total:** 100 complex pages

**Overall Dataset:** 500 pages across 4 categories

### Source Datasets

**Recommended:**
- **DocLayNet:** Validation set (6,480 pages, filter by category)
- **PubLayNet:** Public dataset (360K pages, sample subset)
- **Custom Collection:** Web-sourced images, own documents

**Minimum:** 100 pages per category (total 400 pages)

---

## Metrics to Measure

### 1. Latency Measurements

**YOLOv10-doc (Full Layout Detection):**
- Measure on **ALL** 500 pages
- Record per-page latency
- Calculate statistics:
  - Mean, median, p50, p95, p99
  - Per-category breakdown
  - CPU vs GPU performance

**Text Detection Gate (Ensemble Heuristics):**
- Measure on **ALL** 500 pages
- Three methods:
  1. Stroke density analysis
  2. Connected components analysis
  3. Edge density analysis
- Record:
  - Per-method latency
  - Ensemble (2/3 consensus) latency
  - Accuracy (precision/recall on text presence)

**Combined Workflow (Gate + Conditional Layout):**
- Run text gate on all pages
- Run YOLOv10-doc ONLY on text-detected pages
- Calculate end-to-end latency per page
- Compare to always-run-layout baseline

### 2. Accuracy Measurements

**Text Detection Gate Accuracy:**
- **Ground Truth:** Manual annotation of 500 pages (has_text: bool)
- **Metrics:**
  - Precision: (True Positives) / (True Positives + False Positives)
  - Recall: (True Positives) / (True Positives + False Negatives)
  - F1-Score: 2 * (Precision * Recall) / (Precision + Recall)
  - **Target:** Precision > 95%, Recall > 95%

**YOLOv10-doc Accuracy:**
- **Ground Truth:** DocLayNet validation annotations
- **Metrics:**
  - mAP@.50 (COCO metric)
  - Per-class AP for 11 DocLayNet classes
  - **Target:** mAP > 0.82

### 3. Cost-Benefit Analysis

**Time Savings:**
- Calculate average time saved per page by skipping layout on pure images
- Extrapolate to typical workloads (e.g., 10,000 pages/day)

**Accuracy Trade-off:**
- Measure false negatives (pure images incorrectly routed to full pipeline)
- Measure false positives (text documents incorrectly skipped)
- Calculate impact on downstream OCR quality

**Complexity Cost:**
- Estimate development time to implement text gate (hours)
- Estimate maintenance burden (additional code paths, configuration, debugging)

---

## Benchmark Implementation

### Prerequisites

**Install Dependencies:**
```bash
# YOLOv10-doc model (ONNX format)
# Obtain from: [MODEL_SOURCE_TBD]
# Place in: models/yolov10_doc_doclaynet.onnx

# Python dependencies
poetry add onnxruntime opencv-python numpy pandas matplotlib tqdm
```

**Prepare Dataset:**
```bash
# Download DocLayNet validation set
# OR use custom dataset

# Structure:
benchmarks/data/
  ├── pure_images/
  │   ├── image_001.png
  │   └── ...
  ├── single_column/
  ├── multi_column/
  └── complex/

# Ground truth annotations:
benchmarks/data/annotations.json
```

### Benchmark Script

Create `benchmarks/text_gate_vs_layout.py`:

```python
#!/usr/bin/env python3
"""
Benchmark text detection gate vs always-run-layout approaches.

Usage:
    python benchmarks/text_gate_vs_layout.py --data-dir benchmarks/data --output results.json
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import onnxruntime as ort
import pandas as pd
from tqdm import tqdm


class TextDetectionGate:
    """Ensemble text detection using stroke density, connected components, edge density."""

    def __init__(
        self,
        stroke_threshold: float = 0.15,
        component_threshold: float = 0.20,
        edge_threshold: float = 0.18,
        consensus_votes: int = 2,
    ):
        self.stroke_threshold = stroke_threshold
        self.component_threshold = component_threshold
        self.edge_threshold = edge_threshold
        self.consensus_votes = consensus_votes

    def detect_text(self, image: np.ndarray) -> Tuple[bool, Dict[str, float]]:
        """
        Detect text presence using ensemble approach.

        Returns:
            (has_text, confidence_scores)
        """
        start = time.perf_counter()

        # Method 1: Stroke density
        stroke_score = self._stroke_density(image)

        # Method 2: Connected components
        component_score = self._connected_components(image)

        # Method 3: Edge density
        edge_score = self._edge_density(image)

        # Ensemble: 2/3 consensus
        votes = [
            stroke_score > self.stroke_threshold,
            component_score > self.component_threshold,
            edge_score > self.edge_threshold,
        ]
        has_text = sum(votes) >= self.consensus_votes

        latency = (time.perf_counter() - start) * 1000  # ms

        return has_text, {
            "stroke_score": stroke_score,
            "component_score": component_score,
            "edge_score": edge_score,
            "latency_ms": latency,
            "votes": sum(votes),
        }

    def _stroke_density(self, image: np.ndarray) -> float:
        """Detect text-like stroke patterns via morphological operations."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Horizontal and vertical structuring elements (text has strong h/v strokes)
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))

        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_h)
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_v)
        strokes = cv2.bitwise_or(horizontal, vertical)

        density = np.sum(strokes > 0) / strokes.size
        return density

    def _connected_components(self, image: np.ndarray) -> float:
        """Count text-like connected components."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

        # Filter components by size (text components are typically 10-1000 pixels)
        text_like_components = [
            stat for stat in stats[1:]  # Skip background
            if 10 < stat[cv2.CC_STAT_AREA] < 1000
        ]

        component_density = len(text_like_components) / max(1, num_labels - 1)
        return component_density

    def _edge_density(self, image: np.ndarray) -> float:
        """Detect horizontal/vertical edge patterns characteristic of text lines."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Sobel edges (horizontal and vertical)
        sobel_h = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_v = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        edges = np.abs(sobel_h) + np.abs(sobel_v)
        edge_density = np.sum(edges > 50) / edges.size  # Threshold edges
        return edge_density


class YOLOv10DocDetector:
    """YOLOv10-doc layout detection."""

    def __init__(self, model_path: Path, device: str = "cpu"):
        providers = ["CUDAExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape  # Typically [1, 3, 640, 640]

    def detect(self, image: np.ndarray) -> Tuple[List[Dict], float]:
        """
        Run YOLOv10-doc detection.

        Returns:
            (detections, latency_ms)
        """
        start = time.perf_counter()

        # Preprocess
        input_tensor = self._preprocess(image)

        # Inference
        outputs = self.session.run(None, {self.input_name: input_tensor})

        # Postprocess (parse YOLO outputs)
        detections = self._postprocess(outputs, image.shape)

        latency = (time.perf_counter() - start) * 1000  # ms

        return detections, latency

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Resize and normalize image for YOLOv10 input."""
        # Resize to model input shape (e.g., 640x640)
        target_size = (self.input_shape[2], self.input_shape[3])
        resized = cv2.resize(image, target_size)

        # Convert to RGB, normalize, transpose to NCHW
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))  # HWC -> CHW
        batched = np.expand_dims(transposed, axis=0)  # Add batch dimension

        return batched

    def _postprocess(self, outputs, original_shape):
        """Parse YOLO outputs into detections (stub - needs YOLOv10 output format)."""
        # TODO: Implement YOLOv10-specific output parsing
        # This is a placeholder returning empty detections
        return []


def benchmark_approaches(
    data_dir: Path,
    annotations_file: Path,
    output_file: Path,
    yolo_model_path: Path,
    device: str = "cpu",
):
    """Run benchmark comparing text gate vs always-run-layout."""

    # Load ground truth annotations
    with open(annotations_file) as f:
        annotations = json.load(f)  # {filename: {"has_text": bool, "category": str}}

    # Initialize detectors
    text_gate = TextDetectionGate()
    yolo_detector = YOLOv10DocDetector(yolo_model_path, device=device)

    # Results storage
    results = []

    # Benchmark loop
    image_files = list(data_dir.rglob("*.png")) + list(data_dir.rglob("*.jpg"))
    for img_path in tqdm(image_files, desc="Benchmarking"):
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        filename = img_path.name
        ground_truth = annotations.get(filename, {})

        # 1. Text gate
        has_text_pred, gate_scores = text_gate.detect_text(image)

        # 2. YOLOv10-doc (always run for benchmarking)
        detections, yolo_latency = yolo_detector.detect(image)

        # 3. Combined workflow latency
        if has_text_pred:
            combined_latency = gate_scores["latency_ms"] + yolo_latency
        else:
            combined_latency = gate_scores["latency_ms"]  # Skip layout

        # Store results
        results.append({
            "filename": filename,
            "category": ground_truth.get("category", "unknown"),
            "has_text_ground_truth": ground_truth.get("has_text", None),
            "has_text_predicted": has_text_pred,
            "gate_latency_ms": gate_scores["latency_ms"],
            "gate_stroke_score": gate_scores["stroke_score"],
            "gate_component_score": gate_scores["component_score"],
            "gate_edge_score": gate_scores["edge_score"],
            "gate_votes": gate_scores["votes"],
            "yolo_latency_ms": yolo_latency,
            "yolo_num_detections": len(detections),
            "combined_latency_ms": combined_latency,
            "always_layout_latency_ms": yolo_latency,
            "time_saved_ms": yolo_latency - combined_latency if not has_text_pred else 0,
        })

    # Save results
    df = pd.DataFrame(results)
    df.to_json(output_file, orient="records", indent=2)
    print(f"Results saved to {output_file}")

    # Generate summary statistics
    _generate_summary(df, output_file.parent / "summary.txt")


def _generate_summary(df: pd.DataFrame, summary_file: Path):
    """Generate summary statistics."""

    summary_lines = [
        "=" * 80,
        "TEXT GATE VS YOLOV10-DOC BENCHMARK SUMMARY",
        "=" * 80,
        "",
        f"Total pages: {len(df)}",
        "",
        "--- LATENCY STATISTICS (ms) ---",
        "",
        "YOLOv10-doc (Always Run Layout):",
        f"  Mean: {df['yolo_latency_ms'].mean():.2f}",
        f"  Median: {df['yolo_latency_ms'].median():.2f}",
        f"  p95: {df['yolo_latency_ms'].quantile(0.95):.2f}",
        f"  p99: {df['yolo_latency_ms'].quantile(0.99):.2f}",
        "",
        "Text Detection Gate:",
        f"  Mean: {df['gate_latency_ms'].mean():.2f}",
        f"  Median: {df['gate_latency_ms'].median():.2f}",
        f"  p95: {df['gate_latency_ms'].quantile(0.95):.2f}",
        "",
        "Combined Workflow (Gate + Conditional Layout):",
        f"  Mean: {df['combined_latency_ms'].mean():.2f}",
        f"  Median: {df['combined_latency_ms'].median():.2f}",
        f"  p95: {df['combined_latency_ms'].quantile(0.95):.2f}",
        "",
        f"Average Time Saved per Page: {df['time_saved_ms'].mean():.2f} ms",
        f"Total Time Saved ({len(df)} pages): {df['time_saved_ms'].sum():.2f} ms",
        "",
    ]

    # Accuracy statistics (if ground truth available)
    if "has_text_ground_truth" in df.columns and df["has_text_ground_truth"].notnull().any():
        from sklearn.metrics import precision_score, recall_score, f1_score

        y_true = df["has_text_ground_truth"].fillna(False).astype(bool)
        y_pred = df["has_text_predicted"].astype(bool)

        precision = precision_score(y_true, y_pred)
        recall = recall_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)

        summary_lines.extend([
            "--- TEXT DETECTION GATE ACCURACY ---",
            "",
            f"Precision: {precision:.4f}",
            f"Recall: {recall:.4f}",
            f"F1-Score: {f1:.4f}",
            "",
        ])

    # Per-category breakdown
    summary_lines.extend([
        "--- PER-CATEGORY LATENCY (ms) ---",
        "",
    ])

    for category in df["category"].unique():
        cat_df = df[df["category"] == category]
        summary_lines.extend([
            f"{category} (n={len(cat_df)}):",
            f"  YOLOv10-doc mean: {cat_df['yolo_latency_ms'].mean():.2f}",
            f"  Combined mean: {cat_df['combined_latency_ms'].mean():.2f}",
            f"  Avg savings: {cat_df['time_saved_ms'].mean():.2f}",
            "",
        ])

    # Decision recommendation
    avg_yolo_latency = df["yolo_latency_ms"].mean()
    avg_time_saved = df["time_saved_ms"].mean()

    summary_lines.extend([
        "=" * 80,
        "DECISION RECOMMENDATION",
        "=" * 80,
        "",
    ])

    if avg_yolo_latency < 20:
        decision = "SKIP TEXT GATE (not worth complexity)"
        rationale = f"YOLOv10-doc is very fast ({avg_yolo_latency:.2f}ms avg). Minimal savings ({avg_time_saved:.2f}ms) don't justify added complexity."
    elif avg_time_saved > 30:
        decision = "IMPLEMENT TEXT GATE (meaningful savings)"
        rationale = f"Significant time savings ({avg_time_saved:.2f}ms avg per page). Gate adds value."
    else:
        decision = "MARGINAL BENEFIT (user decision)"
        rationale = f"Moderate savings ({avg_time_saved:.2f}ms avg). Weigh complexity vs benefit."

    summary_lines.extend([
        f"Decision: {decision}",
        f"Rationale: {rationale}",
        "",
        "=" * 80,
    ])

    # Write summary
    with open(summary_file, "w") as f:
        f.write("\n".join(summary_lines))

    print("\n" + "\n".join(summary_lines))


def main():
    parser = argparse.ArgumentParser(description="Benchmark text gate vs YOLOv10-doc")
    parser.add_argument("--data-dir", type=Path, required=True, help="Directory with test images")
    parser.add_argument("--annotations", type=Path, required=True, help="Ground truth annotations JSON")
    parser.add_argument("--yolo-model", type=Path, required=True, help="YOLOv10-doc ONNX model path")
    parser.add_argument("--output", type=Path, default=Path("results.json"), help="Output results file")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu", help="Device for inference")

    args = parser.parse_args()

    benchmark_approaches(
        data_dir=args.data_dir,
        annotations_file=args.annotations,
        output_file=args.output,
        yolo_model_path=args.yolo_model,
        device=args.device,
    )


if __name__ == "__main__":
    main()
```

---

## Running the Benchmark

### Step 1: Prepare Data

```bash
# Create benchmark directory structure
mkdir -p benchmarks/data/{pure_images,single_column,multi_column,complex}

# Download sample images from DocLayNet
# OR collect custom images

# Create ground truth annotations
# benchmarks/data/annotations.json:
{
  "image_001.png": {"has_text": false, "category": "pure_images"},
  "document_001.png": {"has_text": true, "category": "single_column"},
  ...
}
```

### Step 2: Obtain YOLOv10-doc Model

```bash
# TODO: Add YOLOv10-doc model acquisition instructions
# Options:
# 1. Pre-trained model from official source
# 2. Convert from PyTorch to ONNX
# 3. Train custom model on DocLayNet

# Place model at:
models/yolov10_doc_doclaynet.onnx
```

### Step 3: Run Benchmark

```bash
# CPU mode
PYTHONPATH=$PWD:$PYTHONPATH poetry run python benchmarks/text_gate_vs_layout.py \
  --data-dir benchmarks/data \
  --annotations benchmarks/data/annotations.json \
  --yolo-model models/yolov10_doc_doclaynet.onnx \
  --output benchmarks/results/benchmark_cpu.json \
  --device cpu

# GPU mode
PYTHONPATH=$PWD:$PYTHONPATH poetry run python benchmarks/text_gate_vs_layout.py \
  --data-dir benchmarks/data \
  --annotations benchmarks/data/annotations.json \
  --yolo-model models/yolov10_doc_doclaynet.onnx \
  --output benchmarks/results/benchmark_gpu.json \
  --device cuda
```

### Step 4: Analyze Results

```bash
# Summary statistics automatically generated in:
benchmarks/results/summary.txt

# Detailed results in:
benchmarks/results/benchmark_cpu.json
benchmarks/results/benchmark_gpu.json
```

---

## Interpreting Results

### Decision Matrix

| Avg YOLOv10 Latency | Avg Time Saved | Decision | Rationale |
|---------------------|----------------|----------|-----------|
| < 20ms | Any | **SKIP GATE** | YOLOv10-doc is already very fast |
| 20-50ms | < 15ms | **SKIP GATE** | Minimal savings, not worth complexity |
| 20-50ms | 15-30ms | **MARGINAL** | Weigh complexity vs benefit |
| 20-50ms | > 30ms | **IMPLEMENT GATE** | Meaningful savings |
| > 50ms | > 30ms | **IMPLEMENT GATE** | Significant savings |

### Additional Considerations

**Implement Gate IF:**
- Large proportion of pure images in typical workload (>30%)
- Processing cost is critical (high-volume pipeline)
- YOLOv10-doc latency consistently >40ms on pure images

**Skip Gate IF:**
- YOLOv10-doc is fast enough (<20ms) that savings are negligible
- Workload is mostly text documents (gate overhead without benefit)
- Simplicity preferred over optimization

---

## Expected Outcomes

### Hypothesis 1: YOLOv10-doc is Fast Enough (SKIP GATE)

**If YOLOv10-doc avg latency < 20ms:**
- Text gate adds ~5-10ms overhead
- Savings on pure images: ~10-15ms
- Net benefit: Minimal (<5ms avg per page)
- **Recommendation:** Skip gate, always run layout

### Hypothesis 2: Text Gate Provides Meaningful Savings (IMPLEMENT)

**If YOLOv10-doc avg latency > 50ms on pure images:**
- Text gate overhead: ~5-10ms
- Savings on pure images: ~40-50ms
- Net benefit: ~30-40ms per pure image page
- **Recommendation:** Implement gate

### Hypothesis 3: Marginal Benefit (USER DECISION)

**If YOLOv10-doc avg latency 20-50ms:**
- Moderate savings, moderate complexity
- Decision based on:
  - Workload composition (% pure images)
  - Development effort tolerance
  - Performance vs simplicity preference

---

## Next Steps After Benchmark

1. **Document decision in PROJECT_PLAN.md**
2. **Update requirements (FR-2.4)** with empirical data
3. **If IMPLEMENT:** Add text gate to Phase roadmap
4. **If SKIP:** Remove text gate from pipeline diagrams

---

**Benchmark Complete:** Use results to make informed architectural decision
