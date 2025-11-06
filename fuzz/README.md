# Fuzzing Harnesses for Image Preprocessing Detector

This directory contains fuzzing harnesses for ClusterFuzzLite, enabling continuous security testing of critical input processing code via GitHub Actions CI/CD.

## Overview

Fuzzing is a dynamic testing technique that feeds random or malformed inputs to software to discover crashes, hangs, and security vulnerabilities. These harnesses use [Atheris](https://github.com/google/atheris), Google's Python fuzzing engine, and run automatically in CI/CD via ClusterFuzzLite.

## Fuzzing Targets

### 1. fuzz_pdf_loader.py

**Module**: `image_preprocessing_detector.ingestion.pdf_loader`

**Target Areas**:
- PDF parsing and validation
- Page extraction
- DPI estimation
- Image conversion
- Error handling

**Typical Issues Found**:
- Crashes on malformed PDF headers
- Infinite loops on circular references
- Memory exhaustion on compressed objects
- Integer overflows in size calculations

### 2. fuzz_image_loader.py

**Module**: `image_preprocessing_detector.ingestion.image_loader`

**Target Areas**:
- Image format detection and validation
- Image decoding (PNG, JPEG, TIFF)
- Color space conversion
- DPI normalization
- Error handling

**Typical Issues Found**:
- Crashes on truncated image data
- Buffer overflows in decompression
- Color space conversion errors
- DPI metadata parsing issues

### 3. fuzz_text_gate.py

**Module**: `image_preprocessing_detector.detection.text_gate`

**Target Areas**:
- Stroke density calculation
- Connected components analysis
- Edge density computation
- Ensemble voting logic
- Error handling

**Typical Issues Found**:
- Division by zero on empty images
- NumPy array shape mismatches
- Out-of-bounds access
- NaN propagation in calculations

## Local Testing

### Prerequisites

Install fuzzing dependencies:
```bash
poetry install --with dev
poetry add --group dev atheris
```

### Running Fuzzers Locally

```bash
# Run PDF loader fuzzer for 60 seconds
poetry run python fuzz/fuzz_pdf_loader.py -max_total_time=60

# Run image loader fuzzer for 60 seconds
poetry run python fuzz/fuzz_image_loader.py -max_total_time=60

# Run text gate fuzzer for 60 seconds
poetry run python fuzz/fuzz_text_gate.py -max_total_time=60
```

### Interpreting Results

**Normal Output** (no issues found):
```
INFO: Seed: 1234567890
INFO: -max_len is not provided; libFuzzer will not generate inputs larger than 4096 bytes
INFO: A corpus is not provided, starting from an empty corpus
#2      INITED cov: 123 ft: 456 corp: 1/1b exec/s: 0 rss: 45Mb
#1000   NEW    cov: 145 ft: 478 corp: 12/34b lim: 4 exec/s: 1000 rss: 47Mb
...
```

**Crash Found**:
```
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6020000000ab
...
SUMMARY: AddressSanitizer: heap-buffer-overflow /path/to/file.py:123
```

If a crash is found, the fuzzer will save a reproducer file (e.g., `crash-abc123`). Report this as a security issue.

## ClusterFuzzLite CI/CD Integration

These harnesses run automatically via GitHub Actions on every push and PR:

1. **Automatic Fuzzing**: Runs in `.github/workflows/cifuzzy.yml` workflow
2. **Crash Artifacts**: Reproducer files uploaded as GitHub artifacts
3. **SARIF Reports**: Security findings uploaded to GitHub Security tab
4. **Address Sanitizer**: Detects memory corruption, buffer overflows, use-after-free

### Workflow Configuration

The ClusterFuzzLite workflow (`.github/workflows/cifuzzy.yml`):
- Installs Clang, LLVM, and dependencies
- Builds fuzzing harnesses with Atheris
- Runs each fuzzer for 600 seconds (10 minutes)
- Uploads crash artifacts if found
- Submits SARIF reports to Security tab

See [TESTING.md](./TESTING.md) for viewing results and troubleshooting.

## Coverage Goals

| Fuzzer | Target Coverage | Current Coverage |
|--------|----------------|------------------|
| fuzz_pdf_loader.py | 85%+ | TBD (run locally) |
| fuzz_image_loader.py | 80%+ | TBD (run locally) |
| fuzz_text_gate.py | 90%+ | TBD (run locally) |

## Troubleshooting

### ImportError: No module named 'atheris'

```bash
poetry add --group dev atheris
```

### "ValueError: Image array must be 2D or 3D"

Expected - fuzzer is testing invalid inputs. This should be caught gracefully.

### Fuzzer runs slowly

Adjust timeout or corpus size:
```bash
poetry run python fuzz/fuzz_pdf_loader.py -max_total_time=10 -max_len=1024
```

## Contributing

When adding new modules, create corresponding fuzzing harnesses:

1. Create `fuzz/fuzz_<module>.py` with Atheris harness
2. Add documentation to this README
3. Test locally for at least 60 seconds
4. Verify crashes are handled gracefully
5. Update OSS-Fuzz build.sh to include new harness

## References

- [Atheris Documentation](https://github.com/google/atheris)
- [OSS-Fuzz Documentation](https://google.github.io/oss-fuzz/)
- [libFuzzer Documentation](https://llvm.org/docs/LibFuzzer.html)
- [Fuzzing Best Practices](https://github.com/google/fuzzing/blob/master/docs/good-fuzz-target.md)
