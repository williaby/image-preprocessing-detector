"""OmniDocBench Baseline Evaluation Framework for Project A.

This package provides a modular benchmarking framework to evaluate
different model variants against OmniDocBench ground truth, with
versioned result tracking for comparing improvements over baselines.

Key Components:
    models/: Model adapters and registry for different model types
    benchmark_runner.py: Run evaluations for any registered model
    compare_results.py: Compare performance across model versions
    extract_ground_truth.py: Extract page-level attributes from OmniDocBench
    model_registry.yaml: Configuration for all model variants

Supported Model Types:
    - Classical CV (OpenCV heuristics)
    - ResNet IQA (baseline ImageNet, fine-tuned v1, v2, etc.)
    - Layout-Lite (heuristic layout detection)
    - DocLayout-YOLO (ML layout detection) [planned]

Usage:
    # Run benchmark for a specific model
    python scripts/omnidocbench_baseline/benchmark_runner.py --model classical_cv_baseline

    # Compare models
    python scripts/omnidocbench_baseline/compare_results.py \\
        --baseline classical_cv_baseline \\
        --compare resnet18_student_v1

    # Track version progression
    python scripts/omnidocbench_baseline/compare_results.py \\
        --progression resnet18_student

Evaluation Scope (Project A only):
    - Page attributes: fuzzy_scan, watermark, colorful_background
    - Layout classification: single_column, multi_column, three_column, complex
    - Element presence: has_tables, has_figures, has_dense_math
    - IQA score correlation with fuzzy_scan ground truth

Out of Scope (Project B):
    - Text/OCR recognition (NED, BLEU, METEOR)
    - Table structure extraction (TEDS)
    - Formula recognition (CDM)
    - Reading order
"""
