"""Object detection metrics for layout analysis.

Implements COCO-style evaluation metrics:
- mAP (mean Average Precision) @ various IoU thresholds
- Per-class AP
- Precision, Recall, F1

SPDX-License-Identifier: Apache-2.0
"""

import numpy as np
from numpy.typing import NDArray


def bbox_iou(
    bbox1: NDArray[np.float64], bbox2: NDArray[np.float64], bbox_format: str = "xywh"
) -> float:
    """Calculate IoU (Intersection over Union) between two bounding boxes.

    Args:
        bbox1: First bounding box [x, y, w, h] or [x1, y1, x2, y2]
        bbox2: Second bounding box [x, y, w, h] or [x1, y1, x2, y2]
        bbox_format: Bbox format ('xywh' or 'xyxy')

    Returns:
        IoU value (0 to 1)
    """
    # Convert to xyxy format if needed
    if bbox_format == "xywh":
        x1_1, y1_1, w1, h1 = bbox1
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1

        x1_2, y1_2, w2, h2 = bbox2
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2
    else:  # xyxy
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)

    if x2_i < x1_i or y2_i < y1_i:
        return 0.0  # No intersection

    intersection = (x2_i - x1_i) * (y2_i - y1_i)

    # Calculate union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection

    if union < 1e-6:
        return 0.0

    return float(intersection / union)


def match_detections(
    pred_boxes: list[NDArray[np.float64]],
    pred_scores: list[float],
    pred_classes: list[int],
    gt_boxes: list[NDArray[np.float64]],
    gt_classes: list[int],
    iou_threshold: float = 0.5,
) -> tuple[list[bool], list[bool]]:
    """Match predicted detections to ground truth boxes.

    Args:
        pred_boxes: List of predicted bounding boxes
        pred_scores: List of prediction scores
        pred_classes: List of predicted class IDs
        gt_boxes: List of ground truth bounding boxes
        gt_classes: List of ground truth class IDs
        iou_threshold: IoU threshold for matching

    Returns:
        Tuple of (tp_flags, matched_gt)
        - tp_flags: Boolean list indicating true positives
        - matched_gt: Boolean list indicating which GT boxes were matched
    """
    num_pred = len(pred_boxes)
    num_gt = len(gt_boxes)

    if num_pred == 0 or num_gt == 0:
        return [False] * num_pred, [False] * num_gt

    # Sort predictions by score (descending)
    sorted_indices = np.argsort(pred_scores)[::-1]

    tp_flags = [False] * num_pred
    matched_gt = [False] * num_gt

    for pred_idx in sorted_indices:
        pred_box = pred_boxes[pred_idx]
        pred_class = pred_classes[pred_idx]

        best_iou = 0.0
        best_gt_idx = -1

        # Find best matching GT box
        for gt_idx in range(num_gt):
            if matched_gt[gt_idx]:
                continue  # Already matched

            if gt_classes[gt_idx] != pred_class:
                continue  # Class mismatch

            gt_box = gt_boxes[gt_idx]
            iou = bbox_iou(pred_box, gt_box)

            if iou > best_iou:
                best_iou = iou
                best_gt_idx = gt_idx

        # Check if match is valid
        if best_iou >= iou_threshold and best_gt_idx >= 0:
            tp_flags[pred_idx] = True
            matched_gt[best_gt_idx] = True

    return tp_flags, matched_gt


def calculate_ap(
    pred_boxes: list[NDArray[np.float64]],
    pred_scores: list[float],
    pred_classes: list[int],
    gt_boxes: list[NDArray[np.float64]],
    gt_classes: list[int],
    target_class: int,
    iou_threshold: float = 0.5,
) -> float:
    """Calculate Average Precision for a single class.

    Args:
        pred_boxes: List of predicted bounding boxes
        pred_scores: List of prediction scores
        pred_classes: List of predicted class IDs
        gt_boxes: List of ground truth bounding boxes
        gt_classes: List of ground truth class IDs
        target_class: Class ID to calculate AP for
        iou_threshold: IoU threshold for matching

    Returns:
        Average Precision (0 to 1)
    """
    # Filter predictions and GT for target class
    pred_mask = np.array(pred_classes) == target_class
    filtered_pred_boxes = [b for i, b in enumerate(pred_boxes) if pred_mask[i]]
    filtered_pred_scores = [s for i, s in enumerate(pred_scores) if pred_mask[i]]
    filtered_pred_classes = [target_class] * sum(pred_mask)

    gt_mask = np.array(gt_classes) == target_class
    filtered_gt_boxes = [b for i, b in enumerate(gt_boxes) if gt_mask[i]]
    filtered_gt_classes = [target_class] * sum(gt_mask)

    num_gt = len(filtered_gt_boxes)
    if num_gt == 0:
        return 0.0  # No ground truth for this class

    if len(filtered_pred_boxes) == 0:
        return 0.0  # No predictions for this class

    # Match detections
    tp_flags, _ = match_detections(
        filtered_pred_boxes,
        filtered_pred_scores,
        filtered_pred_classes,
        filtered_gt_boxes,
        filtered_gt_classes,
        iou_threshold,
    )

    # Sort by score
    sorted_indices = np.argsort(filtered_pred_scores)[::-1]
    tp_sorted = [tp_flags[i] for i in sorted_indices]

    # Calculate cumulative TP and FP
    tp_cumsum = np.cumsum(tp_sorted)
    fp_cumsum = np.cumsum([not tp for tp in tp_sorted])

    # Calculate precision and recall at each threshold
    precisions = tp_cumsum / (tp_cumsum + fp_cumsum)
    recalls = tp_cumsum / num_gt

    # Add endpoints
    precisions = np.concatenate([[1.0], precisions, [0.0]])
    recalls = np.concatenate([[0.0], recalls, [1.0]])

    # Make precision monotonically decreasing
    for i in range(len(precisions) - 2, -1, -1):
        precisions[i] = max(precisions[i], precisions[i + 1])

    # Calculate AP using 11-point interpolation (COCO style uses 101 points)
    ap = 0.0
    for recall_threshold in np.linspace(0, 1, 101):
        # Find precision at this recall level
        indices = np.where(recalls >= recall_threshold)[0]
        if len(indices) > 0:
            ap += precisions[indices[0]]

    ap /= 101.0

    return float(ap)


def calculate_map(
    pred_boxes: list[NDArray[np.float64]],
    pred_scores: list[float],
    pred_classes: list[int],
    gt_boxes: list[NDArray[np.float64]],
    gt_classes: list[int],
    num_classes: int,
    iou_thresholds: list[float] | None = None,
) -> dict[str, float]:
    """Calculate mAP (mean Average Precision) across classes and IoU thresholds.

    Args:
        pred_boxes: List of predicted bounding boxes
        pred_scores: List of prediction scores
        pred_classes: List of predicted class IDs
        gt_boxes: List of ground truth bounding boxes
        gt_classes: List of ground truth class IDs
        num_classes: Total number of classes
        iou_thresholds: List of IoU thresholds (default: [0.5:0.95:0.05])

    Returns:
        Dictionary with mAP metrics:
        - mAP: Mean AP across all classes and IoU thresholds
        - mAP@.50: Mean AP at IoU=0.5
        - mAP@.75: Mean AP at IoU=0.75
        - per_class_AP: Dict of AP per class (at IoU=0.5)
    """
    if iou_thresholds is None:
        # COCO-style: [0.5, 0.55, 0.6, ..., 0.95]
        iou_thresholds = np.arange(0.5, 1.0, 0.05).tolist()

    # Calculate AP for each class and IoU threshold
    ap_matrix = np.zeros((num_classes, len(iou_thresholds)))

    for class_id in range(num_classes):
        for iou_idx, iou_thresh in enumerate(iou_thresholds):
            ap = calculate_ap(
                pred_boxes,
                pred_scores,
                pred_classes,
                gt_boxes,
                gt_classes,
                target_class=class_id,
                iou_threshold=iou_thresh,
            )
            ap_matrix[class_id, iou_idx] = ap

    # Calculate mAP (mean across classes and IoU thresholds)
    map_all = float(np.mean(ap_matrix))

    # Calculate mAP@.50 and mAP@.75
    iou_50_idx = iou_thresholds.index(0.5) if 0.5 in iou_thresholds else 0
    iou_75_idx = iou_thresholds.index(0.75) if 0.75 in iou_thresholds else -1

    map_50 = float(np.mean(ap_matrix[:, iou_50_idx]))
    map_75 = float(np.mean(ap_matrix[:, iou_75_idx])) if iou_75_idx >= 0 else 0.0

    # Per-class AP at IoU=0.5
    per_class_ap = {
        f"class_{class_id}": float(ap_matrix[class_id, iou_50_idx])
        for class_id in range(num_classes)
    }

    return {
        "mAP": map_all,
        "mAP@.50": map_50,
        "mAP@.75": map_75,
        "per_class_AP": per_class_ap,
    }


def precision_recall_f1(
    pred_boxes: list[NDArray[np.float64]],
    pred_scores: list[float],
    pred_classes: list[int],
    gt_boxes: list[NDArray[np.float64]],
    gt_classes: list[int],
    iou_threshold: float = 0.5,
    score_threshold: float = 0.5,
) -> dict[str, float]:
    """Calculate precision, recall, and F1 score.

    Args:
        pred_boxes: List of predicted bounding boxes
        pred_scores: List of prediction scores
        pred_classes: List of predicted class IDs
        gt_boxes: List of ground truth bounding boxes
        gt_classes: List of ground truth class IDs
        iou_threshold: IoU threshold for matching
        score_threshold: Score threshold for predictions

    Returns:
        Dictionary with precision, recall, f1
    """
    # Filter predictions by score threshold
    score_mask = np.array(pred_scores) >= score_threshold
    filtered_pred_boxes = [b for i, b in enumerate(pred_boxes) if score_mask[i]]
    filtered_pred_scores = [s for i, s in enumerate(pred_scores) if score_mask[i]]
    filtered_pred_classes = [c for i, c in enumerate(pred_classes) if score_mask[i]]

    if len(filtered_pred_boxes) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    if len(gt_boxes) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    # Match detections
    tp_flags, matched_gt = match_detections(
        filtered_pred_boxes,
        filtered_pred_scores,
        filtered_pred_classes,
        gt_boxes,
        gt_classes,
        iou_threshold,
    )

    tp = sum(tp_flags)
    fp = len(tp_flags) - tp
    fn = len(matched_gt) - sum(matched_gt)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }
