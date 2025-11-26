---
schema_type: common
title: "ADR-032: DocRes Unified Document Restoration and Preprocessing"
description: "Adopt DocRes unified CNN model for 5 preprocessing tasks with dynamic task-specific
  prompts"
tags:
- adr
- preprocessing
- restoration
- deep_learning
- phase3
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to adopt DocRes unified model for document restoration,
  replacing separate specialized models for dewarping, de-shadowing, deblurring, binarization,
  and contrast enhancement."
---

**Status**: Accepted
**Date**: 2025-01-13
**Deciders**: Byron Williams
**Related**:

- [ADR-029: Three-Tier Dataset Strategy](0029-phase2-dataset-selection-strategy.md)
- [ADR-031: Comprehensive Benchmarking Framework](0031-comprehensive-benchmarking-framework.md)
- [ADR-021: Do-No-Harm Guardrails](0021-do-no-harm-guardrails.md)
- [FR-3.11: Warping/Curvature Detection](../requirements/functional_requirements_v2.md#fr-311-warpingcurvature-detection)

## Context

### Problem: Fragmented Preprocessing Pipeline

**Current State (Phase 1)**:

- Classical OpenCV methods for basic corrections (deskew, CLAHE, sharpening, denoising)
- Effective for simple quality issues but limited for complex degradations
- Works well for controlled document scans but struggles with camera-captured documents

**Phase 3+ Requirements**:

- Handle complex degradations: warping, shadows, severe blur, poor binarization
- Support camera-captured documents (AnyPhotoDoc 6300 benchmark)
- Maintain performance targets: <150ms/page GPU latency, >6 pages/sec throughput

**Original Approach (Separate Specialized Models)**:

1. **DvD (Document Image Dewarping)** for warping correction
2. **SynDocDS** for shadow removal
3. Separate models for deblurring, binarization, contrast enhancement
4. **Problem**: 5 separate model inferences = 5x memory overhead, 5x latency, integration complexity

### Research Findings (Q4 2024 - Q4 2025 Literature)

**DocRes (CVPR 2024)** emerged as **HIGHEST PRIORITY** solution:

- **Unified Model**: Single CNN handles 5 tasks (dewarping, de-shadowing, deblurring, binarization, contrast enhancement)
- **Dynamic Task-Specific Prompts (DTSPrompt)**: Runtime task selection without model switching
- **Performance**: State-of-the-art results on DocUNet, Doc3D, SynDocDS benchmarks
- **Efficiency**: 1 model inference vs. 5 separate inferences
- **License**: Research paper (implementation pending verification)

**Key Innovation**: DocRes uses task-specific prompts to guide a unified restoration network, eliminating the need for separate task-specific models.

### Dual-Track Strategy Rationale

**Why Maintain Classical Methods (ADR-021 Guardrails)?**

1. **Fallback**: Classical methods proven effective for simple cases (Phase 1: 100% coverage, zero degradation)
2. **CPU-First Deployment**: DocRes requires GPU; classical methods run on CPU
3. **Confidence Routing**: Route simple cases to classical, complex cases to DocRes
4. **Validation**: Classical outputs validate DocRes results

**When to Use DocRes vs. Classical:**

```python
if camera_captured or severe_degradation:
    # Complex degradation: use DocRes unified model
    restored = docres.restore(image, tasks=["dewarp", "deshadow", "deblur"])
elif simple_quality_issues:
    # Simple corrections: use classical methods (faster, CPU-only)
    corrected = classical_corrections.apply(image, issues=["skew", "contrast", "blur"])
```

## Decision

**Adopt DocRes unified model as PRIMARY preprocessing approach for Phase 3+, maintaining classical methods as fallback for CPU-first deployment and simple corrections.**

### Architecture

**Two-Track Preprocessing Pipeline:**

```text
Document Input
    ↓
[Quality Assessment] (FR-2.3: Learned IQA)
    ↓
[Degradation Severity Classifier]
    ↓              ↓
[SIMPLE]      [COMPLEX/CAMERA]
    ↓              ↓
Classical      DocRes Unified
(ADR-021)      (DTSPrompt)
    ↓              ↓
[Validation Gate] (Compare outputs if both available)
    ↓
Restored Document
```text

**DocRes Task Configuration:**

```python
# Example 1: Camera-captured document with warping + shadow
docres_tasks = ["dewarp", "deshadow"]
restored = docres_model.restore(
    image=camera_image,
    tasks=docres_tasks,
    use_dtsprompt=True
)

# Example 2: Scanned document with blur + poor binarization
docres_tasks = ["deblur", "binarize"]
restored = docres_model.restore(
    image=scanned_image,
    tasks=docres_tasks,
    use_dtsprompt=True
)

# Example 3: All tasks (maximum restoration)
docres_tasks = ["dewarp", "deshadow", "deblur", "binarize", "contrast"]
restored = docres_model.restore(
    image=degraded_image,
    tasks=docres_tasks,
    use_dtsprompt=True
)
```

### Five Unified Tasks

**Task 1: Dewarping (Warping/Curvature Correction)**

- **Purpose**: Correct geometric distortion from camera perspective, book binding curvature
- **Input**: Warped document image (curved text lines, perspective distortion)
- **Output**: Rectified document with straight text lines
- **Training Data**: DocUNet (130 images), Doc3D (100k synthetic), AnyPhotoDoc 6300 (6,300 real-world)
- **Benchmark**: AnyPhotoDoc 6300 test split
- **Metrics**: MS-SSIM > 0.88, OCR accuracy improvement > 15%
- **Replaces**: DvD specialized model

**Task 2: De-shadowing (Shadow Removal)**

- **Purpose**: Remove shadows from uneven illumination, hand shadows, binding shadows
- **Input**: Document image with shadows (dark regions, uneven brightness)
- **Output**: Uniformly illuminated document
- **Training Data**: SynDocDS (7,000 synthetic shadowed documents)
- **Benchmark**: SynDocDS test split
- **Metrics**: PSNR > 20 dB, SSIM > 0.90
- **Replaces**: SynDocDS specialized model

**Task 3: Deblurring (Motion/Defocus Blur Correction)**

- **Purpose**: Recover sharp text from camera shake, defocus blur
- **Input**: Blurred document image
- **Output**: Sharp document with clear text edges
- **Training Data**: DocSynth-300K + Albumentations blur augmentation
- **Benchmark**: DIQA-5000 sharpness dimension (when released)
- **Metrics**: Laplacian variance improvement > 30%, OCR accuracy improvement > 10%
- **Complements**: Classical Laplacian blur detection (FR-3.1)

**Task 4: Binarization (Adaptive Thresholding)**

- **Purpose**: Convert grayscale to binary for OCR, improve text-background separation
- **Input**: Grayscale document image with variable lighting
- **Output**: Binary image (black text, white background)
- **Training Data**: DocSynth-300K (300k layouts with ground-truth binarization)
- **Benchmark**: DIBCO (Document Image Binarization Contest) datasets (optional)
- **Metrics**: F-measure > 0.92, PSNR > 18 dB
- **Complements**: Classical Otsu thresholding

**Task 5: Contrast Enhancement (Adaptive Histogram Equalization)**

- **Purpose**: Improve text visibility in low-contrast documents
- **Input**: Low-contrast document image (faded text, washed-out appearance)
- **Output**: Enhanced document with improved text-background contrast
- **Training Data**: DIQA-5000 (when released), fallback to LIVE/CSIQ with synthetic degradation
- **Benchmark**: DIQA-5000 color fidelity dimension
- **Metrics**: Histogram spread > 120, OCR accuracy improvement > 8%
- **Complements**: Classical CLAHE enhancement (ADR-021)

### Training Data Strategy (Tier 1 - ADR-029)

**Primary Datasets:**

1. **DocSynth-300K** (50 GB, 300k layouts, Apache-2.0)
   - Base training for all 5 tasks
   - Albumentations augmentation pipeline for synthetic degradations
   - Download: `huggingface-cli download juliozhao/DocSynth300K --repo-type dataset`

2. **SynDocDS** (7,000 shadowed documents)
   - De-shadowing task fine-tuning
   - Paired shadow/clean images
   - Download: GitHub release (to be verified)

3. **Doc3D** (100k synthetic warped documents)
   - Dewarping task fine-tuning
   - 3D mesh deformation simulations
   - Download: (source to be verified)

4. **DocUNet Benchmark** (130 real-world warped images)
   - Dewarping validation
   - Real-world camera-captured documents
   - Download: (source to be verified)

**Fallback Strategy:**

- **If SynDocDS unavailable**: Use Albumentations shadow augmentation on DocSynth-300K
- **If Doc3D unavailable**: Use AnyPhotoDoc 6300 for dewarping training
- **If DIQA-5000 unavailable**: Use LIVE/CSIQ with synthetic document degradations

### Benchmarking (Tier 2 - ADR-031)

**Document-Specific Benchmarks:**

| Task | Benchmark Dataset | Metrics | Target |
|------|-------------------|---------|--------|
| **Dewarping** | AnyPhotoDoc 6300 | MS-SSIM, OCR accuracy | MS-SSIM > 0.88 |
| **De-shadowing** | SynDocDS test split | PSNR, SSIM | PSNR > 20 dB |
| **Deblurring** | DIQA-5000 sharpness | Pearson correlation | r > 0.80 |
| **Binarization** | DIBCO (optional) | F-measure, PSNR | F > 0.92 |
| **Contrast** | DIQA-5000 color fidelity | Pearson correlation | r > 0.80 |
| **Unified** | OmniDocBench | Multi-task accuracy | Baseline + 5% |

**Integration with ADR-031:**

- New adapters: `anyphotodoc6300`, `syndocds`, `docunet`
- DIQA-5000 adapter replaces `live`, `csiq` for document IQA
- OmniDocBench elevated to CRITICAL for unified validation

### Performance Targets (Phase 3)

**Latency:**

- Single task: <50ms/page (GPU)
- All 5 tasks: <150ms/page (GPU)
- CPU fallback (classical): <100ms/page (no GPU)

**Throughput:**

- GPU (T4): >6 pages/sec (unified pipeline)
- CPU: >2 pages/sec (classical fallback)

**Memory:**

- GPU VRAM: <2 GB (INT8 quantized ONNX)
- CPU RAM: <1 GB (classical methods)

**Accuracy:**

- Dewarping: MS-SSIM > 0.88 (AnyPhotoDoc 6300)
- De-shadowing: PSNR > 20 dB (SynDocDS)
- Deblurring: Laplacian variance improvement > 30%
- Binarization: F-measure > 0.92
- Contrast: Histogram spread > 120

### Implementation Plan (Phase 3 Timeline)

**Week 1-2: DocRes Model Integration**

- Research DocRes paper implementation (CVPR 2024)
- Verify license and availability
- Integrate DTSPrompt task selection
- ONNX export and INT8 quantization

**Week 3-4: Training Data Preparation**

- Download DocSynth-300K (50 GB)
- Download SynDocDS, Doc3D, DocUNet
- Implement Albumentations augmentation pipeline
- Generate synthetic degradations for 5 tasks

**Week 5-8: Multi-Task Training**

- Train unified DocRes model on DocSynth-300K base
- Fine-tune on task-specific datasets (SynDocDS, Doc3D, DocUNet)
- Validate on AnyPhotoDoc 6300, DIQA-5000 (when released)
- Benchmark against classical methods (ADR-021 baselines)

**Week 9-10: Dual-Track Integration**

- Implement severity classifier (route simple → classical, complex → DocRes)
- Add validation gate (compare classical vs. DocRes outputs)
- Performance optimization (batch processing, ONNX optimization)

**Week 11-12: Production Hardening**

- Add do-no-harm guardrails for DocRes outputs (extend ADR-021)
- Integration testing with full pipeline
- Benchmark suite execution (ADR-031 adapters)

**Timeline Impact**: +3 weeks to Phase 3 (from 5 weeks to 8 weeks)

## Consequences

### Positive

1. **Unified Architecture**: Single model for 5 tasks reduces complexity
2. **State-of-the-Art**: CVPR 2024 DocRes outperforms specialized models
3. **Efficiency**: 1 model inference vs. 5 separate inferences (5x speedup potential)
4. **Memory Savings**: Single model in VRAM vs. 5 models (80% memory reduction)
5. **Task Flexibility**: DTSPrompt enables runtime task selection without model switching
6. **Document-Specific**: Trained on document datasets (not natural images)
7. **Benchmarking**: Comprehensive validation with AnyPhotoDoc 6300, DIQA-5000, OmniDocBench

### Negative

1. **Timeline Impact**: +3 weeks to Phase 3 for DocRes integration and training
2. **License Uncertainty**: DocRes license needs verification (research paper implementation)
3. **GPU Dependency**: DocRes requires GPU; classical fallback needed for CPU-first deployment
4. **Model Complexity**: Larger unified model may be harder to debug than specialized models
5. **Training Complexity**: Multi-task learning requires careful balancing of task weights
6. **Dataset Availability**: Some datasets (DIQA-5000, SynDocDS) availability needs verification

### Neutral

1. **Dual-Track Maintenance**: Both classical and DocRes paths require maintenance
2. **Severity Classifier**: New component needed to route simple vs. complex cases
3. **Validation Overhead**: Comparing classical vs. DocRes outputs adds complexity

## Alternatives Considered

### Alternative 1: Separate Specialized Models (Original Approach)

**Approach**: Use DvD for dewarping, SynDocDS for de-shadowing, separate models for other tasks

**Advantages**:

- Task-specific optimization
- Easier debugging (isolated models)
- Independent model updates

**Disadvantages**:

- 5x model inferences (5x latency)
- 5x memory overhead (VRAM exhaustion on edge devices)
- Integration complexity (5 model pipelines)
- Inconsistent results (models may conflict)

**Why Rejected**: Efficiency and memory constraints make this infeasible for production

### Alternative 2: Classical Methods Only (Extend ADR-021)

**Approach**: Expand classical OpenCV methods to handle complex degradations

**Advantages**:

- CPU-only (no GPU required)
- Fast inference (<100ms/page)
- Simple implementation
- Zero ML training overhead

**Disadvantages**:

- Limited effectiveness on complex degradations (warping, shadows)
- Poor performance on camera-captured documents
- Cannot match state-of-the-art ML accuracy
- AnyPhotoDoc 6300 benchmark requires ML approach

**Why Rejected**: Insufficient accuracy for Phase 3+ requirements (camera-captured documents, complex degradations)

### Alternative 3: Document Transformer (Donut/LayoutLM Style)

**Approach**: Use vision transformer for end-to-end document restoration

**Advantages**:

- Transformer architecture (state-of-the-art for vision tasks)
- End-to-end learning
- Potential for multi-modal inputs (text + image)

**Disadvantages**:

- Massive model size (>100M parameters vs. DocRes ~20M)
- High latency (>500ms/page)
- Requires huge training datasets (>1M images)
- Not specialized for restoration tasks

**Why Rejected**: Overkill for preprocessing; DocRes achieves state-of-the-art with smaller model

## Implementation Details

### DocRes Architecture (DTSPrompt)

**Dynamic Task-Specific Prompts (DTSPrompt):**

```python
class DocResModel:
    def __init__(self, checkpoint_path: str):
        self.encoder = CNNEncoder()  # Shared encoder
        self.decoder = CNNDecoder()  # Shared decoder
        self.task_prompts = {
            "dewarp": TaskPrompt(embedding_dim=256),
            "deshadow": TaskPrompt(embedding_dim=256),
            "deblur": TaskPrompt(embedding_dim=256),
            "binarize": TaskPrompt(embedding_dim=256),
            "contrast": TaskPrompt(embedding_dim=256),
        }

    def restore(
        self,
        image: np.ndarray,
        tasks: List[str],
        use_dtsprompt: bool = True
    ) -> np.ndarray:
        """
        Restore document using specified tasks.

        Args:
            image: Input document image (H, W, 3)
            tasks: List of task names (e.g., ["dewarp", "deshadow"])
            use_dtsprompt: Whether to use dynamic task prompts

        Returns:
            Restored document image (H, W, 3)
        """
        # Encode image
        features = self.encoder(image)

        # Apply task-specific prompts
        if use_dtsprompt:
            for task in tasks:
                prompt = self.task_prompts[task]
                features = prompt.apply(features)

        # Decode to restored image
        restored = self.decoder(features)

        return restored
```

**Severity Classifier (Routing Logic):**

```python
class DegradationSeverityClassifier:
    def classify(self, image: np.ndarray, quality_scores: Dict[str, float]) -> str:
        """
        Classify degradation severity to route to appropriate preprocessing.

        Args:
            image: Input document image
            quality_scores: Quality assessment scores from FR-2.3

        Returns:
            "simple" (use classical) or "complex" (use DocRes)
        """
        # Check for camera capture indicators
        if self._is_camera_captured(image):
            return "complex"  # Always use DocRes for camera-captured

        # Check for severe degradations
        severe_issues = []
        if quality_scores.get("sharpness", 1.0) < 0.3:
            severe_issues.append("blur")
        if quality_scores.get("overall", 1.0) < 0.4:
            severe_issues.append("quality")
        if self._detect_warping(image):
            severe_issues.append("warping")
        if self._detect_shadows(image):
            severe_issues.append("shadows")

        # Route complex cases to DocRes
        if len(severe_issues) >= 2:
            return "complex"

        # Route simple cases to classical
        return "simple"

    def _is_camera_captured(self, image: np.ndarray) -> bool:
        """Detect camera-captured documents vs. scanned documents."""
        # Heuristics: perspective distortion, background clutter, uneven lighting
        # (Implementation details omitted)
        pass
```

**Dual-Track Pipeline:**

```python
class PreprocessingPipeline:
    def __init__(self):
        self.docres = DocResModel(checkpoint_path="models/docres.onnx")
        self.classical = ClassicalCorrections()  # ADR-021 guardrails
        self.severity_classifier = DegradationSeverityClassifier()

    def preprocess(self, image: np.ndarray, quality_scores: Dict[str, float]) -> np.ndarray:
        """
        Preprocess document using dual-track approach.

        Args:
            image: Input document image
            quality_scores: Quality assessment from FR-2.3

        Returns:
            Preprocessed document image
        """
        # Classify severity
        severity = self.severity_classifier.classify(image, quality_scores)

        if severity == "simple":
            # Use classical methods (CPU-only, fast)
            return self.classical.apply(image, quality_scores)

        else:  # severity == "complex"
            # Determine required DocRes tasks
            tasks = []
            if self._needs_dewarping(image):
                tasks.append("dewarp")
            if self._needs_deshadowing(image):
                tasks.append("deshadow")
            if quality_scores.get("sharpness", 1.0) < 0.5:
                tasks.append("deblur")
            if self._needs_binarization(image):
                tasks.append("binarize")
            if quality_scores.get("color_fidelity", 1.0) < 0.5:
                tasks.append("contrast")

            # Use DocRes unified model (GPU)
            restored = self.docres.restore(image, tasks=tasks)

            # Validation gate: compare with classical if available
            classical_output = self.classical.apply(image, quality_scores)
            if self._validate_docres_output(restored, classical_output):
                return restored
            else:
                # Rollback to classical if DocRes degraded quality
                return classical_output
```

### Guardrails Extension (ADR-021 Compatibility)

**DocRes-Specific Guardrails:**

```python
class DocResGuardrails:
    def validate_output(
        self,
        original: np.ndarray,
        restored: np.ndarray,
        tasks: List[str]
    ) -> bool:
        """
        Validate DocRes output didn't degrade quality.

        Args:
            original: Original document image
            restored: DocRes restored image
            tasks: Tasks applied

        Returns:
            True if restoration improved quality, False otherwise
        """
        # Check for artifacts (black borders, interpolation noise)
        if self._has_artifacts(restored):
            return False

        # Check blur didn't increase
        if "deblur" in tasks:
            orig_blur = cv2.Laplacian(original, cv2.CV_64F).var()
            rest_blur = cv2.Laplacian(restored, cv2.CV_64F).var()
            if rest_blur < orig_blur * 0.9:  # Blur increased
                return False

        # Check contrast didn't degrade
        if "contrast" in tasks:
            orig_contrast = original.std()
            rest_contrast = restored.std()
            if rest_contrast < orig_contrast * 0.9:  # Contrast degraded
                return False

        # All checks passed
        return True
```

## References

**Research Papers:**

- DocRes: A Generalist Model Toward Unifying Document Image Restoration Tasks (CVPR 2024)
  - Paper: <https://arxiv.org/abs/2405.04408> (to be verified)
  - Code: GitHub (to be verified)
  - License: To be verified

**Related ADRs:**

- [ADR-021: Do-No-Harm Guardrails](0021-do-no-harm-guardrails.md) - Classical correction guardrails
- [ADR-029: Three-Tier Dataset Strategy](0029-phase2-dataset-selection-strategy.md) - Training data (DocSynth-300K, SynDocDS, Doc3D)
- [ADR-031: Comprehensive Benchmarking Framework](0031-comprehensive-benchmarking-framework.md) - Validation (AnyPhotoDoc 6300, DIQA-5000)

**Datasets:**

- DocSynth-300K: HuggingFace `juliozhao/DocSynth300K` (Apache-2.0)
- SynDocDS: Shadow removal dataset (license to be verified)
- AnyPhotoDoc 6300: Dewarping benchmark (research license)
- DIQA-5000: Document IQA benchmark (pending release, Sept 2025)

**Functional Requirements:**

- [FR-2.3: Learned Quality Assessment](../requirements/functional_requirements_v2.md#fr-23-learned-quality-assessment-phase-2)
- [FR-3.11: Warping/Curvature Detection](../requirements/functional_requirements_v2.md#fr-311-warpingcurvature-detection)

## Validation Plan

**Phase 3 Week 11-12: Benchmark Suite**

1. **Dewarping Validation (AnyPhotoDoc 6300)**
   - Metric: MS-SSIM > 0.88
   - Comparison: DocRes vs. DvD baseline vs. Classical (no dewarping)
   - Sample Size: 1,000 test images

2. **De-shadowing Validation (SynDocDS)**
   - Metric: PSNR > 20 dB
   - Comparison: DocRes vs. SynDocDS baseline vs. Classical CLAHE
   - Sample Size: 500 test images

3. **Deblurring Validation (DIQA-5000 Sharpness)**
   - Metric: Pearson correlation > 0.80
   - Comparison: DocRes vs. Classical Laplacian sharpening
   - Sample Size: 1,000 test images (when DIQA-5000 releases)

4. **Unified Validation (OmniDocBench)**
   - Metric: Multi-task accuracy baseline + 5%
   - All 5 tasks combined
   - Sample Size: Full benchmark suite

5. **Performance Validation**
   - Latency: <150ms/page (all 5 tasks, GPU)
   - Throughput: >6 pages/sec (GPU)
   - Memory: <2 GB VRAM (INT8 quantized)

**Success Criteria:**

- ✅ All 5 tasks meet target metrics
- ✅ Latency and throughput within bounds
- ✅ Zero quality degradation on guardrail tests
- ✅ Classical fallback works for CPU-only deployment

## Timeline Impact

**Phase 3 Extension**: +3 weeks (5 weeks → 8 weeks)

**Breakdown:**

- Week 1-2: DocRes integration and ONNX optimization (+2 weeks)
- Week 3-4: Training data preparation (already planned)
- Week 5-8: Multi-task training and fine-tuning (+1 week)
- Week 9-10: Dual-track integration (already planned)
- Week 11-12: Production hardening (already planned)

**Total Phase 3 Duration**: 8 weeks (previously 5 weeks)

**Justification**: State-of-the-art unified restoration model worth 3-week investment for 5x efficiency gain and document-specific accuracy.

## Lessons Learned (To Be Updated Post-Phase 3)

*This section will be updated after Phase 3 implementation with actual findings.*

**Expected Learnings:**

1. DTSPrompt effectiveness for runtime task selection
2. Optimal task weight balancing for multi-task training
3. Severity classifier accuracy and routing effectiveness
4. DocRes vs. classical performance comparison on real-world documents
5. Guardrail extension effectiveness for ML-based preprocessing
