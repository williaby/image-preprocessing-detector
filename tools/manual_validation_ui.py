#!/usr/bin/env python3
"""Manual Validation UI for IQA Label Correction.

Streamlit application for reviewing and correcting weak supervision labels.

Usage:
    streamlit run tools/manual_validation_ui.py -- --input-dir data/weak_supervision_labels

Features:
    - Display images with weak supervision predictions
    - Correct binary labels for 5 quality issues (blur, noise, skew, illumination, artifacts)
    - View confidence scores and quality metrics
    - Track annotation progress
    - Export corrections to JSON

Sprint 3.3.1: Manual Validation Interface (Milestone 10.3)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import streamlit as st
from PIL import Image

# Quality issue types (aligned with ResNetTeacher.ISSUE_TYPES)
QUALITY_ISSUES = [
    "blur",
    "noise",
    "skew",
    "illumination",
    "artifacts",
]

# Issue descriptions for UI
ISSUE_DESCRIPTIONS = {
    "blur": "Image is blurry or out of focus",
    "noise": "Image contains visible noise or grain",
    "skew": "Image is skewed or rotated from horizontal",
    "illumination": "Image has poor lighting or low contrast",
    "artifacts": "Image contains compression artifacts or other distortions",
}


def load_weak_supervision_labels(labels_path: Path) -> dict[str, Any]:
    """Load weak supervision labels from JSON file.

    Args:
        labels_path: Path to labels JSON file

    Returns:
        Dictionary with image_path, labels, and quality_scores
    """
    with open(labels_path) as f:
        data: dict[str, Any] = json.load(f)
        return data


def load_image(image_path: str) -> Image.Image:
    """Load image from file path.

    Args:
        image_path: Path to image file

    Returns:
        PIL Image
    """
    # Try loading with OpenCV first (handles more formats)
    img = cv2.imread(image_path)
    if img is not None:
        # Convert BGR to RGB for PIL
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(img)

    # Fallback to PIL
    return Image.open(image_path)


def save_corrected_labels(
    output_path: Path,
    image_path: str,
    corrected_labels: dict[str, int],
    original_labels: dict[str, Any],
    quality_scores: dict[str, float],
    annotator_notes: str = "",
) -> None:
    """Save corrected labels to JSON file.

    Args:
        output_path: Path to save corrected labels
        image_path: Path to image
        corrected_labels: Dictionary mapping issue type to corrected binary label (0/1)
        original_labels: Original weak supervision labels
        quality_scores: Raw quality metric scores
        annotator_notes: Optional notes from annotator
    """
    output_data = {
        "image_path": image_path,
        "corrected_labels": corrected_labels,
        "original_labels": {
            issue: {
                "value": label["value"],
                "confidence": label["confidence"],
                "source": label["source"],
            }
            for issue, label in original_labels.items()
        },
        "quality_scores": quality_scores,
        "annotator_notes": annotator_notes,
        "annotation_source": "manual_validation_ui",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)


def get_annotation_queue(input_dir: Path) -> list[Path]:
    """Get list of label files to annotate.

    Args:
        input_dir: Directory containing weak supervision labels

    Returns:
        List of label file paths
    """
    return sorted(input_dir.glob("*_labels.json"))


def get_progress(output_dir: Path, total_files: int) -> tuple[int, int]:
    """Calculate annotation progress.

    Args:
        output_dir: Directory containing corrected labels
        total_files: Total number of files to annotate

    Returns:
        Tuple of (completed, total)
    """
    if not output_dir.exists():
        return 0, total_files

    completed = len(list(output_dir.glob("*_corrected.json")))
    return completed, total_files


def _validate_image_path(ws_labels: dict) -> str | None:
    """Validate and resolve the image path from labels.

    Returns:
        Resolved image path string, or None if invalid.
    """
    image_path = ws_labels["image_path"]
    resolved_image_path = Path(image_path).resolve()

    if ".." in Path(image_path).parts:
        st.error("Invalid image path: path traversal detected")
        return None

    if not resolved_image_path.exists():
        st.error(f"Image not found: {resolved_image_path}")
        st.info("Please check the image_path in the labels JSON")
        return None

    return str(resolved_image_path)


def _render_image_column(image_path: str, ws_labels: dict) -> None:
    """Render the left column with image preview and quality scores."""
    st.subheader("Image Preview")
    try:
        img = load_image(image_path)
        st.image(img, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to load image: {e}")

    st.subheader("Quality Metrics")
    scores = ws_labels.get("quality_scores", {})
    score_cols = st.columns(3)

    for idx, (metric, value) in enumerate(scores.items()):
        with score_cols[idx % 3]:
            st.metric(metric.replace("_", " ").title(), f"{value:.2f}")


def _render_label_column(
    ws_labels: dict,
    image_path: str,
    current_file: Path,
    output_path: Path,
    file_index: int,
    queue_length: int,
) -> None:
    """Render the right column with label corrections and save/skip controls."""
    st.subheader("Label Correction")
    corrected_labels = {}

    for issue in QUALITY_ISSUES:
        original_label = ws_labels["labels"].get(issue, {})
        original_value = original_label.get("value", 0)
        confidence = original_label.get("confidence", 0.0)

        st.markdown(f"**{issue.replace('_', ' ').title()}**")
        st.markdown(f"_{ISSUE_DESCRIPTIONS[issue]}_")

        st.caption(
            f"Weak Supervision: {'Issue Present' if original_value == 1 else 'No Issue'} "
            f"(confidence: {confidence:.2f})"
        )

        corrected_labels[issue] = st.checkbox(
            "Issue Present",
            value=bool(original_value),
            key=f"issue_{issue}",
        )
        st.divider()

    st.subheader("Notes")
    annotator_notes = st.text_area(
        "Annotator Notes (optional)",
        placeholder="Any observations or comments about this image...",
        height=100,
    )

    if st.button("Save Corrections", type="primary", use_container_width=True):
        corrected_labels_int = {k: int(v) for k, v in corrected_labels.items()}
        output_filename = current_file.stem.replace("_labels", "_corrected") + ".json"
        output_file = output_path / output_filename
        save_corrected_labels(
            output_file,
            image_path,
            corrected_labels_int,
            ws_labels["labels"],
            ws_labels.get("quality_scores", {}),
            annotator_notes,
        )
        st.success(f"Saved to {output_file}")
        if file_index < queue_length - 1:
            st.info("Advancing to next image...")
            st.rerun()
        else:
            st.balloons()
            st.success("All images annotated!")

    if st.button("Skip (no changes)", use_container_width=True):
        st.info("Skipped. No changes saved.")
        if file_index < queue_length - 1:
            st.rerun()


def main() -> None:
    """Main Streamlit app."""
    st.set_page_config(
        page_title="IQA Manual Validation",
        page_icon="🔍",
        layout="wide",
    )

    st.title("IQA Manual Validation Interface")
    st.markdown(
        """
        Review and correct weak supervision labels for image quality assessment.
        **Milestone 10.3 - Sprint 3.3.1**
        """
    )

    st.sidebar.header("Configuration")
    input_dir = st.sidebar.text_input(
        "Input Directory (weak supervision labels)",
        value="data/weak_supervision_labels",
    )
    output_dir = st.sidebar.text_input(
        "Output Directory (corrected labels)",
        value="data/corrected_labels",
    )

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        st.error(f"Input directory not found: {input_dir}")
        st.info(
            "Please create weak supervision labels first using data/weak_supervision.py"
        )
        return

    annotation_queue = get_annotation_queue(input_path)
    if not annotation_queue:
        st.warning(f"No label files found in {input_dir}")
        return

    completed, total = get_progress(output_path, len(annotation_queue))
    st.sidebar.metric(
        "Progress", f"{completed}/{total}", f"{completed / total * 100:.1f}%"
    )

    st.sidebar.header("Navigation")
    file_index = st.sidebar.number_input(
        "File Index",
        min_value=0,
        max_value=len(annotation_queue) - 1,
        value=completed if completed < len(annotation_queue) else 0,
        step=1,
    )

    current_file = annotation_queue[file_index]
    st.sidebar.info(f"Current: {current_file.name}")

    col1, col2 = st.sidebar.columns(2)
    if col1.button("Previous") and file_index > 0:
        file_index -= 1
        st.rerun()
    if col2.button("Next") and file_index < len(annotation_queue) - 1:
        file_index += 1
        st.rerun()

    ws_labels = load_weak_supervision_labels(current_file)
    image_path = _validate_image_path(ws_labels)
    if image_path is None:
        return

    col_left, col_right = st.columns([2, 1])
    with col_left:
        _render_image_column(image_path, ws_labels)
    with col_right:
        _render_label_column(
            ws_labels,
            image_path,
            current_file,
            output_path,
            file_index,
            len(annotation_queue),
        )


if __name__ == "__main__":
    main()
