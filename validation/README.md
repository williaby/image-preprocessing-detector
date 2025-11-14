# validation/

**Purpose**: One-off experimental validation scripts for hypothesis testing and dataset quality verification.

## What Goes Here

**✅ Belongs in validation/**:
- Experimental validation scripts (one-time use)
- Dataset quality analysis scripts
- Hypothesis testing code
- Manual verification workflows
- Research prototypes before production integration

**❌ Does NOT belong here** (and where it should go instead):
- **Unit/integration tests** → `tests/` (reusable automated tests)
- **Benchmark evaluations** → `benchmarks/` (systematic performance testing)
- **Reusable utilities** → `scripts/` (production-ready scripts)
- **Training notebooks** → `notebooks/` (interactive model training)

## Directory Structure

```
validation/
├── datasets/               # Downloaded datasets for validation (gitignored)
├── synthetic_images/       # Generated test images (gitignored)
├── characteristic_curves/  # Validation analysis outputs (gitignored)
├── validate_*.py          # Validation scripts
└── README.md
```

## Gitignore Policy

**All validation content is gitignored** (scripts and data):

```gitignore
# From .gitignore
validation/*.py          # Experimental scripts (not committed)
validation/*.sh          # Shell scripts (not committed)
validation/datasets/     # Downloaded datasets
validation/synthetic_images/  # Generated test images
validation/characteristic_curves/  # Analysis outputs
validation/*.json        # Large validation results
```

**Rationale**: Validation scripts are exploratory and temporary. Once findings are documented in ADRs or `docs/`, the scripts are no longer needed in version control.

## Typical Use Cases

### Dataset Quality Verification
```python
# validation/validate_doclaynet_annotations.py
"""Verify DocLayNet annotations match expected format."""

# One-off script to check:
# - Bounding box validity
# - Class distribution
# - Image quality issues
```

### Hypothesis Testing
```python
# validation/test_blur_detection_threshold.py
"""Find optimal threshold for Laplacian blur detection."""

# Experiment with different thresholds on sample dataset
# Generate ROC curves, select best threshold
# Results inform production implementation
```

### Research Prototypes
```python
# validation/prototype_handwriting_detector.py
"""Prototype noteshrink-based handwriting detection."""

# Test approach before implementing in src/
# Evaluate on sample images
# Document findings in ADR
```

## Distinction from Other Folders

### vs. tests/
- **validation/**: One-off experimental scripts, not run in CI/CD
- **tests/**: Automated tests run on every commit

### vs. benchmarks/
- **validation/**: Ad-hoc hypothesis testing
- **benchmarks/**: Systematic, repeatable performance evaluation

### vs. scripts/
- **validation/**: Exploratory code, may not be production-ready
- **scripts/**: Reusable utilities integrated into workflows

## Running Validation Scripts

```bash
# Validation scripts need PYTHONPATH set
PYTHONPATH=$PWD:$PYTHONPATH poetry run python validation/validate_dataset.py

# Or use the validation runner (if created)
poetry run python validation/run_validation.py --script validate_doclaynet
```

## Best Practices

1. **Naming**: Use `validate_*.py` or `test_*.py` prefix
2. **Documentation**: Add docstring explaining hypothesis and findings
3. **Cleanup**: Delete or archive scripts after conclusions documented in ADRs
4. **Results**: Save findings in ADRs or tmp_cleanup/ for reference
5. **Not Permanent**: Validation code is exploratory, not production code

## Lifecycle

1. **Create** validation script for specific hypothesis
2. **Run** experiments, collect data
3. **Document** findings in ADR or tmp_cleanup/
4. **Archive or Delete** script (keep if useful for future reference)

## Example Validation Workflow

```python
# validation/validate_dgqa_calibration.py
"""
Validate Domain-Generalized Quality Assessment (DGQA) calibration.

Hypothesis: Synthetic-to-real calibration improves IQA model performance.

Method:
1. Train IQA model on synthetic dataset
2. Apply DGQA calibration layer
3. Evaluate on real-world document images
4. Compare metrics with/without calibration

Expected Results: mAP improvement >5%, ECE reduction <0.03

Findings: Document in ADR-029 (Dataset Strategy)
"""

def run_validation():
    # Load synthetic-trained model
    # Apply calibration
    # Evaluate on real dataset
    # Generate comparison report
    pass

if __name__ == "__main__":
    run_validation()
```

## Integration with ADRs

Validation findings should inform Architecture Decision Records (ADRs):
- Document hypothesis in `docs/ADRs/`
- Reference validation script in ADR
- Include key findings and metrics
- Archive validation code after ADR published

## Storage

- **Scripts**: Committed to git (small Python files)
- **Data/Results**: Gitignored (large files)
- **Findings**: Documented in `docs/ADRs/` or `tmp_cleanup/`
