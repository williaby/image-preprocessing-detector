# ClusterFuzzLite Testing Guide

## Overview

ClusterFuzzLite runs fuzzing automatically in GitHub Actions CI/CD. No local testing required! The fuzzing workflow runs on every push to main/develop branches and on pull requests.

## Automatic CI/CD Fuzzing

The `.github/workflows/cifuzzy.yml` workflow:
- Installs Clang, LLVM, and libFuzzer
- Builds fuzzing harnesses with Atheris
- Runs each fuzzer for 600 seconds (10 minutes)
- Uploads crash artifacts if found
- Submits SARIF reports to GitHub Security tab

**Trigger**: Runs automatically on push/PR, or manually via workflow_dispatch

## Local Testing (Optional)

If you want to test fuzzers locally before pushing:

### Prerequisites

Atheris requires Clang and libFuzzer to build. On WSL/Ubuntu:

```bash
# Install Clang
sudo apt-get update
sudo apt-get install clang llvm lld

# Verify installation
clang --version
```

### Installing Atheris

Once Clang is installed:

```bash
# Install Atheris
pip install atheris

# Or with poetry (not in dev group to avoid WSL build issues)
# poetry add --group dev atheris
```

## Running Fuzzers Locally

```bash
# Run PDF loader fuzzer for 60 seconds
poetry run python fuzz/fuzz_pdf_loader.py -max_total_time=60

# Run image loader fuzzer for 60 seconds
poetry run python fuzz/fuzz_image_loader.py -max_total_time=60

# Run text gate fuzzer for 60 seconds
poetry run python fuzz/fuzz_text_gate.py -max_total_time=60
```

## GitHub Actions Fuzzing (Recommended)

Instead of local testing, push your changes and let GitHub Actions run fuzzing:

1. Push to branch: `git push origin feature-branch`
2. Create PR or push to main/develop
3. GitHub Actions runs fuzzing automatically
4. Check "Actions" tab for fuzzing results
5. Check "Security" tab for SARIF reports

**Advantages**:
- No local Clang/LLVM setup required
- Runs in clean environment
- Results uploaded to GitHub Security
- Crash artifacts preserved

## Expected Output (No Crashes)

```
INFO: Seed: 1234567890
INFO: -max_len is not provided; libFuzzer will not generate inputs larger than 4096 bytes
INFO: A corpus is not provided, starting from an empty corpus
#2      INITED cov: 123 ft: 456 corp: 1/1b exec/s: 0 rss: 45Mb
#1000   NEW    cov: 145 ft: 478 corp: 12/34b lim: 4 exec/s: 1000 rss: 47Mb
#2000   NEW    cov: 156 ft: 489 corp: 15/56b lim: 8 exec/s: 2000 rss: 48Mb
...
Done 60000 runs in 61 second(s)
```

## Expected Output (Crash Found)

If a crash is found:

```
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6020000000ab
    #0 0x7f1234567890 in some_function file.py:123
    #1 0x7f1234567891 in another_function file.py:456
...
SUMMARY: AddressSanitizer: heap-buffer-overflow /path/to/file.py:123
```

The fuzzer will save a reproducer file (e.g., `crash-abc123`). This should be:
1. Reported as a security issue
2. Fixed immediately
3. Added to regression tests

## Why ClusterFuzzLite CI/CD is Preferred

1. **No Local Setup**: Runs in GitHub Actions, no Clang/LLVM installation needed
2. **Sanitizers Enabled**: Address sanitizer detects memory issues
3. **Automatic Execution**: Runs on every push and PR
4. **SARIF Integration**: Results appear in GitHub Security tab
5. **Crash Artifacts**: Reproducer files saved as GitHub artifacts

## Viewing Fuzzing Results

### Actions Tab
- Go to repository → Actions tab
- Click on latest workflow run
- Check "ClusterFuzzLite" job for fuzzing summary
- Download crash artifacts if any found

### Security Tab
- Go to repository → Security tab
- Click "Code scanning alerts"
- View SARIF reports from fuzzing
- Filter by "ClusterFuzzLite" tool

## Troubleshooting

### Fuzzing workflow fails
- Check Actions logs for build errors
- Ensure fuzzing harnesses have no syntax errors
- Verify Atheris installation succeeded

### No crashes found
- Expected! This is good - fuzzers didn't find vulnerabilities
- Fuzzers run for 600 seconds (10 minutes) per push

### Crash found
- Download crash artifact from Actions tab
- Reproduce locally: `python fuzz/fuzz_<name>.py <crash-file>`
- Fix the vulnerability
- Add regression test
- Push fix
