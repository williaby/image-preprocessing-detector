"""OmniDocBench Baseline Evaluation Scripts for Project A.

This package provides tools to evaluate Project A's layout-lite detectors
against OmniDocBench ground truth, establishing baseline performance metrics
before any training.

Scripts:
    extract_ground_truth.py: Extract page-level attributes from OmniDocBench
    run_baseline_evaluation.py: Run evaluation and generate metrics report

Evaluation Scope (Project A only):
    - Page attributes: fuzzy_scan, watermark, colorful_background
    - Layout classification: single_column, multi_column, three_column, complex
    - Element presence: has_tables, has_figures, has_dense_math

Out of Scope (Project B):
    - Text/OCR recognition (NED, BLEU, METEOR)
    - Table structure extraction (TEDS)
    - Formula recognition (CDM)
    - Reading order
"""
