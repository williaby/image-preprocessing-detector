#!/usr/bin/env python3
"""Manual Validation UI for IQA Label Correction.

Streamlit application for reviewing and correcting weak supervision labels.

Usage:
    streamlit run tools/manual_validation_ui.py -- --input-dir data/weak_supervision_labels

Features:
    - Display images with weak supervision predictions
    - Correct binary labels for 6 quality issues
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

# Quality issue types (from data/weak_supervision.py)
QUALITY_ISSUES = [
    "noise",
    "blur",
    "skew",
    "perspective",
    "low_contrast",
    "orientation",
]

# Issue descriptions for UI
ISSUE_DESCRIPTIONS = {
    "noise": "Image contains visible noise or grain",
    "blur": "Image is blurry or out of focus",
    "skew": "Image is skewed or rotated from horizontal",
    "perspective": "Image has perspective distortion",
    "low_contrast": "Image has low contrast or washed out appearance",
    "orientation": "Image needs rotation (90/180/270°)",
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


def main() -> None:
    """Main Streamlit app."""
    st.set_page_config(
        page_title="IQA Manual Validation",
        page_icon="🔍",
        layout="wide",
    )

    st.title("🔍 IQA Manual Validation Interface")
    st.markdown(
        """
        Review and correct weak supervision labels for image quality assessment.
        **Milestone 10.3 - Sprint 3.3.1**
        """
    )

    # Sidebar configuration
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

    # Get annotation queue
    annotation_queue = get_annotation_queue(input_path)

    if not annotation_queue:
        st.warning(f"No label files found in {input_dir}")
        return

    # Progress tracking
    completed, total = get_progress(output_path, len(annotation_queue))
    st.sidebar.metric(
        "Progress", f"{completed}/{total}", f"{completed / total * 100:.1f}%"
    )

    # File navigation
    st.sidebar.header("Navigation")

    # File selector
    file_index = st.sidebar.number_input(
        "File Index",
        min_value=0,
        max_value=len(annotation_queue) - 1,
        value=completed if completed < len(annotation_queue) else 0,
        step=1,
    )

    current_file = annotation_queue[file_index]
    st.sidebar.info(f"Current: {current_file.name}")

    # Navigation buttons
    col1, col2 = st.sidebar.columns(2)
    if col1.button("⬅️ Previous") and file_index > 0:
        file_index -= 1
        st.rerun()
    if col2.button("➡️ Next") and file_index < len(annotation_queue) - 1:
        file_index += 1
        st.rerun()

    # Load weak supervision labels
    ws_labels = load_weak_supervision_labels(current_file)
    image_path = ws_labels["image_path"]

    # Check if image exists
    if not Path(image_path).exists():
        st.error(f"Image not found: {image_path}")
        st.info("Please check the image_path in the labels JSON")
        return

    # Main content area
    col_left, col_right = st.columns([2, 1])

    # Left column: Image display
    with col_left:
        st.subheader("Image Preview")
        try:
            img = load_image(image_path)
            st.image(img, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to load image: {e}")

        # Quality scores
        st.subheader("Quality Metrics")
        scores = ws_labels.get("quality_scores", {})
        score_cols = st.columns(3)

        for idx, (metric, value) in enumerate(scores.items()):
            with score_cols[idx % 3]:
                st.metric(metric.replace("_", " ").title(), f"{value:.2f}")

    # Right column: Label correction
    with col_right:
        st.subheader("Label Correction")

        # Initialize corrected labels from weak supervision
        corrected_labels = {}

        for issue in QUALITY_ISSUES:
            original_label = ws_labels["labels"].get(issue, {})
            original_value = original_label.get("value", 0)
            confidence = original_label.get("confidence", 0.0)

            st.markdown(f"**{issue.replace('_', ' ').title()}**")
            st.markdown(f"_{ISSUE_DESCRIPTIONS[issue]}_")

            # Show original prediction
            st.caption(
                f"Weak Supervision: {'✅ Issue Present' if original_value == 1 else '❌ No Issue'} "
                f"(confidence: {confidence:.2f})"
            )

            # Correction checkbox
            corrected_labels[issue] = st.checkbox(
                "Issue Present",
                value=bool(original_value),
                key=f"issue_{issue}",
            )

            st.divider()

        # Annotator notes
        st.subheader("Notes")
        annotator_notes = st.text_area(
            "Annotator Notes (optional)",
            placeholder="Any observations or comments about this image...",
            height=100,
        )

        # Save button
        if st.button("💾 Save Corrections", type="primary", use_container_width=True):
            # Convert boolean to int (0/1)
            corrected_labels_int = {k: int(v) for k, v in corrected_labels.items()}

            # Generate output filename
            output_filename = (
                current_file.stem.replace("_labels", "_corrected") + ".json"
            )
            output_file = output_path / output_filename

            # Save corrected labels
            save_corrected_labels(
                output_file,
                image_path,
                corrected_labels_int,
                ws_labels["labels"],
                ws_labels.get("quality_scores", {}),
                annotator_notes,
            )

            st.success(f"✅ Saved to {output_file}")

            # Auto-advance to next file
            if file_index < len(annotation_queue) - 1:
                st.info("Advancing to next image...")
                file_index += 1
                st.rerun()
            else:
                st.balloons()
                st.success("🎉 All images annotated!")

        # Skip button
        if st.button("⏭️ Skip (no changes)", use_container_width=True):
            st.info("Skipped. No changes saved.")
            if file_index < len(annotation_queue) - 1:
                file_index += 1
                st.rerun()


if __name__ == "__main__":
    main()
