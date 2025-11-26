# Manual Annotation Guide

**Milestone 10.3 - Sprints 3.3.3 & 3.3.4**

This guide explains how to conduct manual annotation sessions using the validation UI.

## Overview

Manual annotation sessions correct weak supervision labels by having human annotators review ambiguous cases (images with low confidence predictions).

**Goal**: Annotate 2,000 images total (1,000 per session)

## Prerequisites

1. **Weak supervision labels generated**:

   ```bash
   python -m data.weak_supervision <input_dir> <output_dir>
   ```

2. **Ambiguous cases sampled**:

   ```bash
   python scripts/sample_ambiguous_cases.py \
       --input-dir data/weak_supervision_labels \
       --output-dir data/annotation_queue \
       --num-samples 2000
   ```

3. **Streamlit installed**:

   ```bash
   pip install streamlit
   # or
   poetry add streamlit
   ```

## Running the Annotation UI

### Start the UI

```bash
streamlit run tools/manual_validation_ui.py -- \
    --input-dir data/annotation_queue
```

This will open a web browser with the annotation interface.

### UI Components

**Left Panel - Image Display**:

- Full resolution image preview
- Quality metric scores (BRISQUE, NIQE, Laplacian, etc.)

**Right Panel - Label Correction**:

- 6 quality issue checkboxes:
  - ✅ Noise
  - ✅ Blur
  - ✅ Skew
  - ✅ Perspective
  - ✅ Low Contrast
  - ✅ Orientation
- Original weak supervision predictions shown
- Confidence scores displayed
- Notes field for observations

**Sidebar**:

- Progress tracker (completed/total)
- File navigation (Previous/Next buttons)
- Configuration settings

### Annotation Process

For each image:

1. **Review the image** - Look for visible quality issues
2. **Check weak supervision predictions** - See what the algorithm detected
3. **Correct labels** - Toggle checkboxes for accurate ground truth
4. **Add notes** (optional) - Document edge cases or observations
5. **Save corrections** - Click "💾 Save Corrections" button
6. **Auto-advance** - UI moves to next image automatically

## Quality Issue Definitions

### 1. Noise

**Definition**: Visible grain, speckles, or random pixel variations

**Examples**:

- Salt and pepper noise
- Gaussian noise
- ISO noise from low-light scans
- Film grain artifacts

**Guidelines**:

- ✅ Check if noise is distracting or affects readability
- ❌ Don't check for minor JPEG compression artifacts

### 2. Blur

**Definition**: Image is out of focus, motion-blurred, or lacks sharp edges

**Examples**:

- Motion blur from camera shake
- Defocus blur (out of focus)
- Gaussian blur from low-quality scanning
- Radial blur

**Guidelines**:

- ✅ Check if text edges are noticeably soft
- ❌ Don't check for minor softness (slight blur is common)

### 3. Skew

**Definition**: Image is rotated from horizontal (text lines not level)

**Examples**:

- Document scanned at an angle
- Camera photo not aligned with page
- Minor rotation (1-10°)

**Guidelines**:

- ✅ Check if text lines are visibly tilted
- ❌ Don't check for very minor skew (<1°)

### 4. Perspective

**Definition**: Image has trapezoid distortion (not rectangular)

**Examples**:

- Camera photo taken at an angle
- Page not flat during scanning
- Perspective warp from camera lens

**Guidelines**:

- ✅ Check if page edges are not parallel
- ❌ Don't check for minor lens distortion

### 5. Low Contrast

**Definition**: Image appears washed out, faded, or lacks dynamic range

**Examples**:

- Faded scans
- Overexposed/underexposed photos
- Low contrast between text and background
- Histogram bunching (not using full range)

**Guidelines**:

- ✅ Check if text is hard to read due to low contrast
- ❌ Don't check for normal document contrast

### 6. Orientation

**Definition**: Image needs rotation (90°, 180°, or 270°)

**Examples**:

- Portrait document in landscape orientation
- Upside-down scan
- Rotated 90° left or right

**Guidelines**:

- ✅ Check if document is not in reading orientation
- ❌ Don't check for minor skew (that's "Skew", not "Orientation")

## Annotation Guidelines

### General Principles

1. **Binary Labels**: Each issue is either present (✅) or absent (❌)
2. **Independence**: Issues are independent (an image can have multiple issues)
3. **Readability Focus**: Focus on whether the issue affects document readability
4. **Ground Truth**: Annotate what you see, not what the algorithm predicted

### Edge Cases

**Borderline Blur**:

- If you're unsure, zoom in on text edges
- Check if edges are crisp or noticeably soft
- When in doubt, check the Laplacian variance score (>150 = sharp, <80 = blurry)

**Mild Artifacts**:

- Minor JPEG compression: ❌ Not noise (unless severe)
- Slight graininess: ❌ Not noise (unless distracting)
- Watermarks: Add to notes, don't mark as noise

**Multiple Issues**:

- An image can have multiple quality issues
- Check all that apply (e.g., blur + low contrast)

**Clean Images**:

- If image looks perfect, uncheck all boxes
- This is valid ground truth (high quality image)

## Session Planning

### Sprint 3.3.3: Session 1 (4 hours)

- **Goal**: Annotate 1,000 images
- **Rate**: ~4 images/minute (15 seconds each)
- **Breaks**: Take 5-minute break every 30 minutes

**Timeline**:

- 0:00-0:30 → 120 images
- 0:30-0:35 → Break
- 0:35-1:05 → 120 images
- 1:05-1:10 → Break
- ... (repeat for 8 cycles)
- Total: ~1,000 images

### Sprint 3.3.4: Session 2 (4 hours)

- **Goal**: Annotate remaining 1,000 images
- **Process**: Same as Session 1

## Inter-Annotator Agreement (Multiple Annotators)

If using multiple annotators:

1. **Calibration Set**: Have all annotators review 50 shared images
2. **Calculate Agreement**: Use Cohen's Kappa or Fleiss' Kappa
3. **Review Disagreements**: Discuss edge cases where annotators differ
4. **Refine Guidelines**: Update this guide based on disagreements

## Output Format

Corrected labels are saved to `data/corrected_labels/` as JSON files:

```json
{
  "image_path": "path/to/image.png",
  "corrected_labels": {
    "noise": 0,
    "blur": 1,
    "skew": 0,
    "perspective": 0,
    "low_contrast": 1,
    "orientation": 0
  },
  "original_labels": {
    "noise": {"value": 0, "confidence": 0.85, "source": "brisque"},
    "blur": {"value": 1, "confidence": 0.92, "source": "laplacian"},
    ...
  },
  "quality_scores": {
    "brisque": 35.2,
    "niqe": 12.5,
    "laplacian_variance": 85.3,
    "rms_contrast": 0.28,
    ...
  },
  "annotator_notes": "Minor blur visible on text edges",
  "annotation_source": "manual_validation_ui"
}
```

## Progress Tracking

- **UI Progress Bar**: Shows completed/total in sidebar
- **Output Directory**: Check `data/corrected_labels/` for saved files
- **Metadata File**: `data/annotation_queue/sampling_metadata.json` has full list

## Troubleshooting

**UI not loading**:

```bash
# Check Streamlit version
streamlit --version

# Reinstall if needed
pip install --upgrade streamlit
```

**Image not found**:

- Check that image paths in labels JSON are correct
- Verify images exist on disk
- Use absolute paths if needed

**Slow loading**:

- Images are loaded on-demand (not cached)
- Large images (>10MB) may load slowly
- Consider downscaling very large images

## Quality Control

After each session:

1. **Check completion**: Verify all images have corrected labels
2. **Review notes**: Read annotator notes for patterns
3. **Spot check**: Randomly sample 20 annotations for quality
4. **Merge labels**: Run final dataset creation (Sprint 3.3.5)

## Next Steps

After completing both sessions (2,000 annotations):

```bash
# Create final training dataset
python scripts/create_final_dataset.py \
    --weak-supervision-dir data/weak_supervision_labels \
    --corrected-labels-dir data/corrected_labels \
    --output-dir data/final_training_dataset
```

This merges weak supervision + manual corrections into final dataset for YOLOv8 training.
