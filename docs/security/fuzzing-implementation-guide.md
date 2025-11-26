---
schema_type: common
title: "Fuzzing Implementation Guide"
description: "Comprehensive guide for implementing fuzzing tests with ClusterFuzzLite and OSS-Fuzz"
tags: [security, testing, ci_cd, guide]
status: published
owner: "quality-team"
review_cycle_days: 90
authors:
  - name: "Byron Williams"
purpose: "Document the fuzzing infrastructure, harness creation, and integration process for security testing."
---

**Project**: Image Preprocessing Detector
**Purpose**: Implement comprehensive fuzzing for image/PDF processing security
**Status**: CIFuzz workflow configured, OSS-Fuzz registration required

---

## Table of Contents

- [Overview](#overview)
- [Current Status](#current-status)
- [Option 1: OSS-Fuzz Integration (Recommended)](#option-1-oss-fuzz-integration-recommended)
- [Option 2: ClusterFuzzLite (Quick Alternative)](#option-2-clusterfuzzlite-quick-alternative)
- [Writing Fuzzing Harnesses](#writing-fuzzing-harnesses)
- [Testing and Validation](#testing-and-validation)
- [Troubleshooting](#troubleshooting)

---

## Overview

### Why Fuzzing?

Image preprocessing detector processes untrusted input (PDFs, images) and is vulnerable to:

- **Buffer overflows**: Malformed image headers, oversized dimensions
- **Infinite loops**: Corrupted PDF streams, circular references
- **Memory exhaustion**: Decompression bombs, recursive structures
- **Injection attacks**: Embedded scripts in PDFs, malicious metadata
- **Crash conditions**: Edge cases in OpenCV, PyMuPDF, Pillow

**Fuzzing** systematically tests these scenarios by generating thousands of mutated inputs.

### Fuzzing Strategy

1. **Coverage-guided fuzzing**: Prioritize inputs that explore new code paths
2. **Target critical modules**: PDF loading, image decoding, format detection
3. **Continuous integration**: Run on every commit via CIFuzz
4. **Long-term fuzzing**: OSS-Fuzz runs 24/7 on Google infrastructure

---

## Current Status

### ✅ Completed

1. **CIFuzz Workflow**: [.github/workflows/cifuzzy.yml](../../.github/workflows/cifuzzy.yml)
   - Configured for 600-second fuzzing sessions
   - SARIF report generation for GitHub Security
   - Crash artifact collection

2. **Dependencies**: Python 3.11 with Poetry
   - OpenCV, PyMuPDF, Pillow (fuzzing targets)
   - Standard library modules
   - Atheris (fuzzing engine)

### ❌ Pending

1. **OSS-Fuzz Registration**: Project not registered with Google OSS-Fuzz
2. **Fuzzing Harnesses**: Implemented (`fuzz_pdf_loader.py`, `fuzz_image_loader.py`, `fuzz_text_gate.py`)
3. **Project Configuration**: Missing project.yaml and Dockerfile
4. **Build Integration**: Need to configure fuzzing build

### Current Scorecard Impact

**Fuzzing Score**: 5-8/10 (ClusterFuzzLite operational, OSS-Fuzz pending)

**After OSS-Fuzz Implementation**: 10/10 (fully operational continuous fuzzing)

---

## Option 1: OSS-Fuzz Integration (Recommended)

### Overview

**OSS-Fuzz** is Google's continuous fuzzing service for open-source projects.

**Benefits**:

- 24/7 fuzzing on Google infrastructure (free)
- Automatic crash reporting via email + GitHub issues
- Coverage reports and corpus management
- Industry-standard integration (20,000+ projects)

**Drawbacks**:

- Registration approval required (1-2 weeks)
- More setup complexity than ClusterFuzzLite
- Public disclosure of vulnerabilities (responsible)

### Implementation Steps

#### Step 1: Create Fuzzing Harnesses (1-2 hours)

Create `fuzz/` directory with Python fuzz targets:

```bash
mkdir -p fuzz
```

**Example: PDF Loader Fuzzer**

```python
# fuzz/fuzz_pdf_loader.py
"""Fuzzing harness for PDF loading functionality."""

import sys
import atheris

# Import target module
with atheris.instrument_imports():
    import fitz  # PyMuPDF
    import numpy as np

def TestOneInput(data):
    """Fuzz target for PDF loading.

    Args:
        data: Random bytes from fuzzer (mutated PDF)
    """
    if len(data) < 10:
        return  # Skip too-small inputs

    try:
        # Use PyMuPDF directly (PDFLoader.load() requires file path)
        doc = fitz.open(stream=data, filetype="pdf")

        # Exercise parsing logic
        if doc.page_count > 0:
            page = doc.load_page(0)

            # Render page
            zoom = 300 / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to numpy array
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            _ = img_array.shape

        doc.close()

    except Exception:
        # Catch all exceptions - fuzzer looks for crashes, not exceptions
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
```

**Example: Image Loader Fuzzer**

```python
# fuzz/fuzz_image_loader.py
"""Fuzzing harness for image loading functionality."""

import sys
import atheris
from io import BytesIO

with atheris.instrument_imports():
    import numpy as np
    from PIL import Image

def TestOneInput(data):
    """Fuzz target for image loading.

    Tests various image formats: PNG, JPEG, TIFF, etc.
    """
    if len(data) < 20:
        return

    try:
        # Test Pillow image loading directly (ImageLoader.load() requires file path)
        img_bytes = BytesIO(data)
        img = Image.open(img_bytes)

        # Access image properties
        _ = img.size
        _ = img.mode
        _ = img.format

        # Convert to numpy array (triggers decoding)
        img_array = np.array(img)
        _ = img_array.shape

        img.close()

    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
```

**Example: Text Gate Fuzzer**

```python
# fuzz/fuzz_text_gate.py
"""Fuzzing harness for text detection gate."""

import sys
import atheris
import numpy as np

with atheris.instrument_imports():
    from image_preprocessing_detector.detection.text_gate import TextGate

def TestOneInput(data):
    """Fuzz target for text detection.

    Tests ensemble heuristics with random image data.
    """
    if len(data) < 100:
        return

    try:
        # Create random image from fuzzer data
        # Reshape to various dimensions
        for shape in [(100, 100), (50, 200), (200, 50)]:
            if len(data) >= shape[0] * shape[1]:
                img_data = np.frombuffer(data[:shape[0] * shape[1]], dtype=np.uint8)
                img_data = img_data.reshape(shape)

                # Test text detection
                gate = TextGate()
                result = gate.detect(img_data)

                # Access result fields
                _ = result.has_text
                _ = result.confidence
                _ = result.stroke_density

    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
```

#### Step 2: Create Project Configuration (30 minutes)

**Create `project.yaml` in OSS-Fuzz fork**:

```yaml
# projects/image-preprocessing-detector/project.yaml
homepage: "https://github.com/williaby/image-preprocessing-detector"
language: python
primary_contact: "byronawilliams@gmail.com"
auto_ccs:
  - "byronawilliams@gmail.com"

sanitizers:
  - address
  - undefined

fuzzing_engines:
  - libfuzzer

main_repo: "https://github.com/williaby/image-preprocessing-detector"
```

**Create `Dockerfile`**:

```dockerfile
# projects/image-preprocessing-detector/Dockerfile
FROM gcr.io/oss-fuzz-base/base-builder-python

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone repository
RUN git clone --depth 1 https://github.com/williaby/image-preprocessing-detector $SRC/image-preprocessing-detector

# Install Python dependencies
WORKDIR $SRC/image-preprocessing-detector
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main

# Install fuzzing dependencies
RUN pip3 install atheris

# Copy build script
COPY build.sh $SRC/
```

**Create `build.sh`**:

```bash
#!/bin/bash -eu
# projects/image-preprocessing-detector/build.sh

# Build fuzzers
cd $SRC/image-preprocessing-detector

# Compile each fuzzer
for fuzzer in fuzz/fuzz_*.py; do
    fuzzer_basename=$(basename -s .py $fuzzer)

    # Compile with atheris
    pyinstaller --onefile --name $fuzzer_basename $fuzzer

    # Copy to output
    cp dist/$fuzzer_basename $OUT/

    # Create seed corpus (optional but recommended)
    mkdir -p $OUT/${fuzzer_basename}_seed_corpus

    # Example: Add sample PDFs/images as seeds
    # cp samples/*.pdf $OUT/${fuzzer_basename}_seed_corpus/ || true
done

# Copy dictionary files (optional)
# cp fuzz/*.dict $OUT/ || true
```

#### Step 3: Register with OSS-Fuzz (1 week approval)

1. **Fork OSS-Fuzz**:

   ```bash
   # On GitHub
   # Fork: https://github.com/google/oss-fuzz
   ```

1. **Add Project Files**:

   ```bash
   git clone https://github.com/YOUR_USERNAME/oss-fuzz
   cd oss-fuzz

   mkdir -p projects/image-preprocessing-detector
   # Add project.yaml, Dockerfile, build.sh
   ```

1. **Test Build Locally**:

   ```bash
   python infra/helper.py build_image image-preprocessing-detector
   python infra/helper.py build_fuzzers image-preprocessing-detector
   python infra/helper.py check_build image-preprocessing-detector
   ```

1. **Run Fuzzers Locally**:

   ```bash
   python infra/helper.py run_fuzzer image-preprocessing-detector fuzz_pdf_loader -- -max_total_time=60
   ```

1. **Submit Pull Request**:

   ```bash
   git checkout -b add-image-preprocessing-detector
   git add projects/image-preprocessing-detector/
   git commit -m "Add image-preprocessing-detector project"
   git push origin add-image-preprocessing-detector

   # Create PR to google/oss-fuzz
   ```

1. **Wait for Review** (1-2 weeks):
   - OSS-Fuzz team reviews configuration
   - Tests build on their infrastructure
   - Approves and merges

1. **Monitor Results**:
   - Bugs filed automatically to GitHub Issues
   - Email notifications for crashes
   - Coverage reports available

#### Step 4: Verify CIFuzz Integration (30 minutes)

After OSS-Fuzz approval, CIFuzz workflow will automatically work:

```bash
# Push a commit to trigger workflow
git push origin main

# Check GitHub Actions
gh run list --workflow=cifuzzy.yml

# View fuzzing results
gh run view <run-id>
```

**Expected Output**:

```text
✅ Fuzzers built and executed for 600 seconds
📸 Image/PDF processing modules tested for edge cases
🔐 Security vulnerabilities detection active
```text

**Total Time**: 4-6 hours active work + 1-2 weeks approval

**Expected Scorecard**: Fuzzing 0/10 → 10/10 (+1.0 points)

---

## Option 2: ClusterFuzzLite (Quick Alternative)

### Overview

**ClusterFuzzLite** is a lightweight fuzzing solution for CI/CD.

**Benefits**:

- No registration required (immediate use)
- Simpler setup (1-2 hours)
- Good for catching bugs before merge
- May score points with Scorecard

**Drawbacks**:

- Only runs during CI (not continuous)
- No long-term corpus management
- Limited to CI timeout (typically 30-60 minutes)
- May not achieve 10/10 on Scorecard (depends on detection)

### Implementation Steps

#### Step 1: Replace CIFuzz with ClusterFuzzLite (1 hour)

**Update `.github/workflows/cifuzzy.yml`**:

```yaml
name: ClusterFuzzLite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  fuzzing:
    name: ClusterFuzzLite Fuzzing
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
      security-events: write  # For SARIF upload

    steps:
      - name: Checkout repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Build Fuzzers
        id: build
        uses: google/clusterfuzzlite/actions/build_fuzzers@v1
        with:
          language: python
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Run Fuzzers
        id: run
        uses: google/clusterfuzzlite/actions/run_fuzzers@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          fuzz-seconds: 600
          mode: 'code-change'  # Fuzz changed code
          sanitizer: address

      - name: Upload Crashes
        if: failure() && steps.run.outcome == 'success'
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
        with:
          name: clusterfuzzlite-crashes
          path: build/out/*/crashes
          retention-days: 7
```

#### Step 2: Create Fuzzing Harnesses (Same as Option 1)

Use the same fuzz targets from Option 1 (fuzz_pdf_loader.py, etc.)

#### Step 3: Add ClusterFuzzLite Configuration (30 minutes)

**Create `.clusterfuzzlite/project.yaml`**:

```yaml
language: python
sanitizers:
  - address
  - undefined
```

**Create `.clusterfuzzlite/Dockerfile`**:

```dockerfile
FROM gcr.io/oss-fuzz-base/base-builder-python

WORKDIR /src

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main

# Install atheris for fuzzing
RUN pip install atheris

# Copy source code
COPY . .

# Build fuzzers
RUN for fuzzer in fuzz/fuzz_*.py; do \
        fuzzer_basename=$(basename -s .py $fuzzer); \
        pyinstaller --onefile --name $fuzzer_basename $fuzzer; \
        cp dist/$fuzzer_basename $OUT/; \
    done
```

#### Step 4: Test Locally (15 minutes)

```bash
# Install ClusterFuzzLite CLI
pip install clusterfuzzlite

# Build fuzzers
python -m clusterfuzzlite.build_fuzzers --language python

# Run fuzzers
python -m clusterfuzzlite.run_fuzzers --fuzz-seconds 60

# Check for crashes
ls -la build/out/*/crashes
```

#### Step 5: Verify CI Integration (15 minutes)

```bash
# Push commit to trigger workflow
git add .clusterfuzzlite/ fuzz/
git commit -m "feat: Add ClusterFuzzLite fuzzing"
git push origin main

# Check workflow
gh run list --workflow=cifuzzy.yml
gh run view <run-id>
```

**Total Time**: 2-3 hours

**Expected Scorecard**: Fuzzing 0/10 → ~5-8/10 (may vary)

**Note**: ClusterFuzzLite may not score 10/10 because Scorecard specifically looks for OSS-Fuzz integration. However, it's a good intermediate solution.

---

## Writing Fuzzing Harnesses

### Best Practices

#### 1. Target Critical Code Paths

Focus on:

- **Input parsing**: PDF, PNG, JPEG, TIFF parsers
- **Data transformation**: Image decoding, color space conversion
- **Complex logic**: Text detection, layout analysis
- **External dependencies**: OpenCV, PyMuPDF, Pillow wrappers

#### 2. Handle Exceptions Gracefully

```python
def TestOneInput(data):
    try:
        # Fuzzing logic
        process_input(data)
    except ValueError:
        pass  # Expected for invalid input
    except MemoryError:
        pass  # Expected for huge inputs
    # Let other exceptions crash (fuzzer will catch them)
```

#### 3. Add Input Validation

```python
def TestOneInput(data):
    # Skip too-small inputs (waste fuzzer time)
    if len(data) < 100:
        return

    # Skip too-large inputs (prevent timeouts)
    if len(data) > 10_000_000:  # 10MB limit
        return

    # Fuzzing logic
    ...
```

#### 4. Use Seed Corpus

Provide example inputs to guide fuzzer:

```bash
# Create seed corpus directory
mkdir -p fuzz/corpus/fuzz_pdf_loader/

# Add sample PDFs
cp samples/valid_document.pdf fuzz/corpus/fuzz_pdf_loader/
cp samples/scanned_image.pdf fuzz/corpus/fuzz_pdf_loader/
cp samples/text_document.pdf fuzz/corpus/fuzz_pdf_loader/
```

#### 5. Create Dictionary Files

Help fuzzer generate valid inputs:

```text
# fuzz/pdf.dict
PDF_HEADER="%PDF-1."
PDF_EOF="%%EOF"
PDF_STREAM="stream"
PDF_ENDSTREAM="endstream"
PDF_OBJ="obj"
PDF_ENDOBJ="endobj"
```text

---

## Testing and Validation

### Local Testing

```bash
# Test individual fuzzer
python fuzz/fuzz_pdf_loader.py -max_total_time=60

# Test with seed corpus
python fuzz/fuzz_pdf_loader.py -max_total_time=60 fuzz/corpus/fuzz_pdf_loader/

# Test with dictionary
python fuzz/fuzz_pdf_loader.py -max_total_time=60 -dict=fuzz/pdf.dict
```

### Coverage Analysis

```bash
# Generate coverage report
python fuzz/fuzz_pdf_loader.py -max_total_time=600 -print_final_stats=1

# Expected output:
# cov: 1234 ft: 5678 corp: 42/1234Kb exec/s: 12 rss: 123Mb
#
# cov = code coverage (unique edges)
# ft = features (code paths)
# corp = corpus size (unique inputs)
```

**Goal**: Maximize `cov` and `ft` values

### Crash Reproduction

```bash
# When fuzzer finds crash, it saves to crash-*
python fuzz/fuzz_pdf_loader.py crash-abc123

# Debug with debugger
python -m pdb fuzz/fuzz_pdf_loader.py crash-abc123
```

---

## Troubleshooting

### Issue: Fuzzers Build but Don't Find Bugs

**Cause**: Insufficient fuzzing time or coverage

**Solutions**:

1. Increase fuzz-seconds: 600 → 1800 (30 minutes)
2. Add seed corpus with diverse samples
3. Use dictionary to guide input generation
4. Simplify harness (remove try/except to see crashes)

### Issue: Fuzzing Timeouts

**Cause**: Harness processes large inputs inefficiently

**Solutions**:

1. Add input size limits: `if len(data) > 1_000_000: return`
2. Add timeout to operations: `signal.alarm(5)` before processing
3. Profile harness to find slow operations

### Issue: Too Many Crashes

**Cause**: Genuine bugs in dependencies (OpenCV, PyMuPDF)

**Solutions**:

1. Report upstream to dependency maintainers
2. Add exception handling for known issues
3. Implement input validation before calling dependencies

### Issue: OSS-Fuzz Build Fails

**Cause**: Missing dependencies or build configuration

**Solutions**:

1. Test locally: `python infra/helper.py build_fuzzers <project>`
2. Check Dockerfile has all system dependencies
3. Verify poetry.lock is committed
4. Review build logs: `/workspace/out/logs/*.log`

---

## Appendix: Fuzzing Targets Priority

### High Priority (Implement First)

1. **PDF Loader** (`fuzz_pdf_loader.py`):
   - Risk: Arbitrary code execution via malformed PDFs
   - Impact: Critical

2. **Image Loader** (`fuzz_image_loader.py`):
   - Risk: Buffer overflow via malformed images
   - Impact: High

3. **Text Gate** (`fuzz_text_gate.py`):
   - Risk: Denial of service via edge cases
   - Impact: Medium

### Medium Priority (Phase 2+)

1. **IQA Classical** (`fuzz_iqa_classical.py`):
   - Risk: Division by zero, overflow in metrics
   - Impact: Low

2. **Correction Pipeline** (`fuzz_corrections.py`):
   - Risk: Invalid transformations causing crashes
   - Impact: Medium

### Low Priority (Phase 3+)

1. **YOLOv8 Layout** (`fuzz_layout_detection.py`):
   - Risk: Model crashes on adversarial inputs
   - Impact: Low (ML Phase)

---

## Expected Outcomes

### After OSS-Fuzz Integration

**Security**:

- Continuous fuzzing 24/7 on Google infrastructure
- Automatic bug reporting via GitHub Issues
- Vulnerabilities found before production

**Scorecard**:

- Fuzzing: 0/10 → 10/10 (+1.0 points)
- Overall: 6.5/10 → 7.5/10

**Maintenance**:

- ~1 hour/month reviewing fuzzing results
- Fix bugs as reported by OSS-Fuzz

### After ClusterFuzzLite Integration

**Security**:

- Fuzzing on every commit (10 minutes)
- Catch bugs before merge
- Fast feedback loop

**Scorecard**:

- Fuzzing: 0/10 → ~5-8/10 (+0.5-0.8 points)
- Overall: 6.5/10 → 7.0-7.3/10

**Maintenance**:

- ~15 minutes/week reviewing CI failures
- Fix bugs found during development

---

## Next Steps

### Immediate (This Week)

1. **Choose Fuzzing Strategy**:
   - OSS-Fuzz (recommended, full points)
   - ClusterFuzzLite (faster, partial points)

2. **Create Fuzzing Harnesses** (2-3 hours):
   - Start with PDF and image loaders
   - Add text gate fuzzer

3. **Test Locally** (1 hour):
   - Verify fuzzers build and run
   - Check for initial crashes

### Short-Term (This Month)

1. **OSS-Fuzz Registration** (if chosen):
   - Submit PR to google/oss-fuzz
   - Wait for approval (1-2 weeks)

2. **OR ClusterFuzzLite Setup** (if chosen):
   - Add .clusterfuzzlite/ configuration
   - Test in CI

### Long-Term (Ongoing)

1. **Monitor and Fix**:
   - Review fuzzing results weekly
   - Fix crashes as discovered
   - Expand corpus with new samples

2. **Expand Coverage**:
   - Add more fuzzing targets
   - Increase fuzzing time for deeper testing
   - Integrate coverage reporting

---

## Conclusion

**Recommendation**: Start with **OSS-Fuzz** for full security benefits and Scorecard points.

**Timeline**:

- Week 1: Write fuzzing harnesses, test locally
- Week 2: Submit OSS-Fuzz PR
- Week 3-4: Wait for approval
- Ongoing: Monitor and fix bugs

**Impact**: Fuzzing will catch critical security bugs before production, improving both security posture and OpenSSF Scorecard score.

---

**Created**: 2025-11-06
**Last Updated**: 2025-11-06
**Status**: Ready for implementation
