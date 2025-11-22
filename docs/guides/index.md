---
schema_type: common
title: "User Guide"
description: "Comprehensive user documentation for Image Preprocessing Detector"
tags: [guide, documentation, tutorial]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Provide comprehensive user guides for all aspects of the system."
---

Welcome to the Image Preprocessing Detector user guide. This section contains comprehensive documentation for using the system, from installation to advanced configuration.

## Getting Started

New to Image Preprocessing Detector? Start here:

- **[Quick Start](quick-start.md)** - Get up and running in 5 minutes
- **[Installation](installation.md)** - Detailed installation instructions
- **[Configuration](configuration.md)** - Configure the system for your needs

## Core Concepts

Understand how the system works:

- **[Overview](overview.md)** - High-level system architecture and workflow
- **[Image Quality Assessment](iqa.md)** - Understanding IQA metrics and thresholds
- **[Document Layout Detection](layout.md)** - Layout analysis and classification
- **[Correction Pipeline](correction.md)** - Automated image corrections

## Training & Data Management

For ML model training and data preparation:

- **[Data Collection](data-collection.md)** - Collecting and organizing training data
- **[Dataset Installation](dataset-installation.md)** - Installing public datasets
- **[Dataset Preparation](dataset-preparation.md)** - Preparing data for training
- **[Modal Training](modal-training.md)** - Training models on Modal's serverless GPU
- **[Modal Storage](modal-storage.md)** - Managing datasets and models on Modal

## Quick Start Guide

### Installation

```bash
# Install with pip
pip install image-preprocessing-detector

# Or with poetry (development)
poetry install --with dev
```

### Basic Usage

```python
from image_preprocessing_detector import DocumentProcessor

# Initialize processor
processor = DocumentProcessor()

# Process a document
result = processor.process_document("document.pdf")

# Check results
print(f"Pages processed: {len(result.pages)}")
for page in result.pages:
    print(f"Page {page.page_number}: {len(page.detected_issues)} issues")
```

### CLI Usage

```bash
# Process a PDF
imgprep process input.pdf --output result.json

# With custom configuration
imgprep process input.pdf --config config.yaml --output result.json

# Batch processing
imgprep batch --input-dir ./pdfs --output-dir ./results
```

## Common Use Cases

### Quality Assessment Only

Run IQA without corrections:

```python
from image_preprocessing_detector import DocumentProcessor

processor = DocumentProcessor(config={
    "correction": {"auto_correct": False}
})

result = processor.process_document("document.pdf")
```

### Automatic Corrections

Apply corrections automatically:

```python
processor = DocumentProcessor(config={
    "correction": {
        "auto_correct": True,
        "confidence_threshold": 0.7
    }
})

result = processor.process_document("document.pdf")
# Corrected images saved to output directory
```

### Custom Quality Thresholds

Adjust sensitivity for issue detection:

```python
processor = DocumentProcessor(config={
    "detection": {
        "skew_threshold": 2.0,  # degrees
        "blur_threshold": 100.0,  # Laplacian variance
        "contrast_threshold": 0.3  # normalized
    }
})
```

## Configuration Reference

See [Configuration Guide](configuration.md) for complete configuration options.

### Key Configuration Areas

- **Ingestion**: DPI settings, upscaling, format support
- **Detection**: IQA thresholds, ML model selection, device preference
- **Correction**: Auto-correction, confidence thresholds, guardrails
- **Output**: JSON format, image output, logging verbosity

## Advanced Topics

### Multi-Device Support

The system supports multiple device configurations:

1. **Local GPU** (preferred): CUDA-enabled GPU for fastest inference
2. **Local CPU**: CPU-only mode with optimized ONNX models
3. **Modal GPU**: Serverless GPU for batch processing

### Teacher-Student ML IQA

Understanding the ML IQA architecture:

- **Student Model** (ResNet-18): Fast, default production inference
- **Teacher Model** (ResNet-50): High-capacity model for difficult cases
- **Selective Inference**: Automatic teacher fallback for uncertain cases

### Hybrid IQA for Text Documents

For documents with embedded images:

- Layout-aware processing
- Per-element quality assessment
- Text vs image region handling

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure proper installation
poetry install --with dev

# Or force reinstall
pip install --force-reinstall image-preprocessing-detector
```

**GPU not detected:**
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Force CPU mode
imgprep process input.pdf --device cpu
```

**Low quality scores:**
- Adjust detection thresholds in configuration
- Check input resolution (should be ≥300 DPI)
- Review correction pipeline settings

## Support & Community

- **GitHub Issues**: [Report bugs](https://github.com/williaby/image-preprocessing-detector/issues)
- **Discussions**: [Ask questions](https://github.com/williaby/image-preprocessing-detector/discussions)
- **Contributing**: See [Contributing Guide](../development/contributing.md)

## Related Documentation

- [API Reference](../api/index.md) - Detailed API documentation
- [Architecture](../development/architecture.md) - System design and architecture
- [Development Guide](../development/contributing.md) - Contributing and development
- [Project Plan](../development/RAG%20Pipeline/project-a-project-plan.md) - Roadmap and phases
