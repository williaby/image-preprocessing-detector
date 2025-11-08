---
schema_type: common
title: "CodeQL Python Security Scanning Guide"
description: "Implementation guide for CodeQL security scanning in Python projects"
tags: [security, ci_cd, code_quality, guide]
status: published
owner: "quality-team"
review_cycle_days: 90
authors:
  - name: "Byron Williams"
purpose: "Guide developers through setting up, running, and interpreting CodeQL security scans."
---

**Image Preprocessing Detector - Security Analysis Documentation**

## Overview

CodeQL is GitHub's semantic code analysis engine that identifies security vulnerabilities and coding errors in Python code. This project implements automated CodeQL scanning through GitHub Actions to maintain high security standards for image and PDF processing operations.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Security Patterns Detected](#security-patterns-detected)
- [Workflow Integration](#workflow-integration)
- [Alert Management](#alert-management)
- [Validation and Testing](#validation-and-testing)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Viewing Security Alerts

1. Navigate to **Security** → **Code scanning alerts** in the GitHub repository
2. Filter by severity, status, or vulnerability type
3. Click on an alert to view:
   - Detailed description
   - Code location
   - Remediation guidance
   - Related CWE/CVE information

### Running CodeQL Locally

```bash
# Install CodeQL CLI
gh extension install github/gh-codeql

# Create CodeQL database
codeql database create python-db --language=python

# Run security queries
codeql database analyze python-db \
  --format=sarif-latest \
  --output=results.sarif \
  codeql/python-queries:codeql-suites/python-security-extended.qls

# View results
codeql bqrs interpret results.sarif
```

## Configuration

### Workflow Configuration

File: [`.github/workflows/security-analysis.yml`](../../.github/workflows/security-analysis.yml)

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: python
    queries: security-extended,security-and-quality
    config: |
      paths:
        - src
      paths-ignore:
        - tests
        - validation
        - scripts
      queries:
        - uses: security-extended
        - uses: security-and-quality
```

### Query Suites

**security-extended**: Comprehensive security vulnerability detection

- SQL injection
- Command injection
- Path traversal
- Hardcoded secrets
- Insecure deserialization
- Weak cryptography
- Code injection (eval/exec)

**security-and-quality**: Security + code quality issues

- All security-extended checks
- Code smell detection
- Performance anti-patterns
- Maintainability issues

### Scan Triggers

CodeQL analysis runs automatically on:

1. **Pull Requests**: Targeting `main`, `develop`, or `feature/**` branches
2. **Push Events**: To `main` or `develop` branches
3. **Weekly Schedule**: Every Monday at 02:30 UTC
4. **Manual Trigger**: Via workflow_dispatch

## Security Patterns Detected

### 1. SQL Injection (CWE-89)

**Severity**: Critical

**Description**: Unparameterized database queries with user-supplied input.

**Vulnerable Code**:

```python
# BAD: String interpolation in SQL
user_id = request.args.get('id')
query = f"SELECT * FROM users WHERE id = '{user_id}'"
cursor.execute(query)
```

**Secure Code**:

```python
# GOOD: Parameterized queries
user_id = request.args.get('id')
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

### 2. Command Injection (CWE-78)

**Severity**: Critical

**Description**: Shell command execution with unsanitized user input.

**Vulnerable Code**:

```python
# BAD: shell=True with user input
filename = request.form.get('file')
subprocess.run(f"cat {filename}", shell=True)
```

**Secure Code**:

```python
# GOOD: shell=False with argument list
filename = secure_filename(request.form.get('file'))
subprocess.run(['cat', filename], shell=False)
```

### 3. Path Traversal (CWE-22)

**Severity**: High

**Description**: File access without proper path validation.

**Vulnerable Code**:

```python
# BAD: No path validation
user_file = request.args.get('file')
with open(f'/uploads/{user_file}', 'r') as f:
    content = f.read()
```

**Secure Code**:

```python
# GOOD: Path validation and sanitization
from pathlib import Path
user_file = secure_filename(request.args.get('file'))
base_dir = Path('/uploads').resolve()
file_path = (base_dir / user_file).resolve()

# Ensure path is within base directory
if not file_path.is_relative_to(base_dir):
    raise ValueError("Path traversal attempt detected")

with open(file_path, 'r') as f:
    content = f.read()
```

### 4. Hardcoded Secrets (CWE-798)

**Severity**: High

**Description**: API keys, passwords, or tokens embedded in source code.

**Vulnerable Code**:

```python
# BAD: Hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DB_PASSWORD = "SuperSecretPassword123"
```

**Secure Code**:

```python
# GOOD: Environment variables
import os
API_KEY = os.environ['API_KEY']
DB_PASSWORD = os.environ['DB_PASSWORD']
```

### 5. Insecure Deserialization (CWE-502)

**Severity**: Critical

**Description**: Using `pickle` on untrusted data.

**Vulnerable Code**:

```python
# BAD: pickle.loads on untrusted data
import pickle
data = pickle.loads(user_provided_bytes)
```

**Secure Code**:

```python
# GOOD: Use JSON for untrusted data
import json
data = json.loads(user_provided_string)
```

### 6. Weak Cryptography (CWE-327)

**Severity**: Medium

**Description**: Using deprecated hash algorithms (MD5, SHA1).

**Vulnerable Code**:

```python
# BAD: MD5 is cryptographically broken
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()
```

**Secure Code**:

```python
# GOOD: Use SHA-256 or better
import hashlib
password_hash = hashlib.sha256(password.encode()).hexdigest()

# BETTER: Use dedicated password hashing
from passlib.hash import argon2
password_hash = argon2.hash(password)
```

### 7. Code Injection (CWE-95)

**Severity**: Critical

**Description**: Using `eval()` or `exec()` on untrusted input.

**Vulnerable Code**:

```python
# BAD: eval() with user input
user_expression = request.form.get('expression')
result = eval(user_expression)
```

**Secure Code**:

```python
# GOOD: Use ast.literal_eval for safe evaluation
import ast
user_expression = request.form.get('expression')
result = ast.literal_eval(user_expression)  # Only literals
```

## Workflow Integration

### CI/CD Pipeline

CodeQL integrates with the security analysis workflow:

```yaml
jobs:
  codeql-analysis:
    name: CodeQL Security Analysis
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: poetry install --only main

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
```

### SARIF Report Upload

Results are automatically uploaded to GitHub Security:

```yaml
- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

## Alert Management

### Alert Severity Levels

| Severity | Response Time | Action Required |
|----------|---------------|-----------------|
| **Critical** | Immediate | Block deployment, fix within 24h |
| **High** | 1-2 days | Fix before next release |
| **Medium** | 1 week | Plan fix in upcoming sprint |
| **Low** | 1 month | Address during refactoring |

### Triage Workflow

1. **Assess Severity**: Review CWE classification and impact
2. **Verify Finding**: Confirm it's not a false positive
3. **Evaluate Exploitability**: Determine if vulnerability is reachable
4. **Determine Impact**: Assess business risk
5. **Execute Response**: Fix, suppress with justification, or defer

### Accessing Alerts

**GitHub CLI**:

```bash
# List all code scanning alerts
gh api repos/williaby/image-preprocessing-detector/code-scanning/alerts \
  --jq '.[] | {number, rule: .rule.id, severity: .rule.severity, state}'

# Get specific alert details
gh api repos/williaby/image-preprocessing-detector/code-scanning/alerts/123

# Dismiss alert with reason
gh api repos/williaby/image-preprocessing-detector/code-scanning/alerts/123 \
  --method PATCH \
  -f state=dismissed \
  -f dismissed_reason=false_positive \
  -f dismissed_comment="Path is validated upstream"
```

**Web Interface**:

1. Navigate to **Security** → **Code scanning alerts**
2. Filter by:
   - Severity (Critical, High, Medium, Low)
   - Status (Open, Fixed, Dismissed)
   - Branch (main, develop, feature/*)
   - Tool (CodeQL, Semgrep, Bandit)

## Validation and Testing

### CodeQL Validation Tests

File: [`tests/security/test_codeql_validation.py`](../../tests/security/test_codeql_validation.py)

This file contains **intentional security vulnerabilities** to validate CodeQL configuration:

```python
# Expected CodeQL findings:
# - Hardcoded secrets: 4+ findings
# - SQL injection: 2+ findings
# - Command injection: 3+ findings
# - Path traversal: 3+ findings
# - Insecure deserialization: 2+ findings
# - Weak cryptography: 2+ findings
# - Unsafe eval: 3+ findings
# Total: 19+ security findings expected
```

### Verification Steps

1. **Check Workflow Logs**:
   ```bash
   gh run list --workflow=security-analysis.yml --limit 1
   gh run view <run-id>
   ```

2. **Review Security Alerts**:
   - Navigate to Security → Code scanning alerts
   - Confirm test_codeql_validation.py generates expected alerts
   - Verify alert severity and CWE mappings

3. **Download SARIF Report**:
   ```bash
   gh run download <run-id> --name security-scan-reports
   python -m json.tool sarif/codeql.sarif
   ```

## Best Practices

### 1. Scope Scanning to Source Code

Only scan production code (`src/`), exclude tests and scripts:

```yaml
paths:
  - src
paths-ignore:
  - tests
  - validation
  - scripts
```

### 2. Install Production Dependencies

CodeQL needs dependencies to understand import paths:

```yaml
- name: Install dependencies
  run: poetry install --only main --no-interaction
```

### 3. Use Extended Query Suites

Maximize vulnerability detection:

```yaml
queries: security-extended,security-and-quality
```

### 4. Enable Weekly Scans

Catch new vulnerabilities in unchanged code:

```yaml
on:
  schedule:
    - cron: '30 2 * * 1'  # Monday 02:30 UTC
```

### 5. Integrate with Branch Protection

Require CodeQL checks to pass:

```bash
gh api repos/williaby/image-preprocessing-detector/branches/main/protection \
  --method PUT \
  -f required_status_checks[contexts][]=CodeQL
```

### 6. Document Suppressions

Always justify dismissed alerts:

```yaml
# .codeql/codeql-config.yml
queries:
  - exclude:
      id: py/weak-cryptographic-algorithm
      tags: audit
    justification: "MD5 used for non-security checksums only"
```

## Troubleshooting

### Issue: No Alerts Generated

**Symptoms**: CodeQL workflow succeeds but no alerts appear

**Solutions**:

1. Check workflow logs for analysis errors
2. Verify SARIF upload step completed
3. Ensure `security-events: write` permission set
4. Confirm paths include source code directories

### Issue: Too Many False Positives

**Symptoms**: Alerts for non-exploitable code paths

**Solutions**:

1. Add path exclusions for generated code
2. Use inline suppressions with justification
3. Create custom query exclusions
4. Report false positives to CodeQL team

### Issue: Analysis Timeout

**Symptoms**: Workflow exceeds 45-minute limit

**Solutions**:

1. Reduce scope with `paths-ignore`
2. Limit query suites to `security-extended` only
3. Disable `autobuild` and specify build commands
4. Use incremental analysis (CodeQL 2.13+)

### Issue: Dependency Installation Failures

**Symptoms**: CodeQL cannot resolve imports

**Solutions**:

```yaml
# Install only required dependencies
- run: poetry install --only main --no-interaction

# Verify critical packages
- run: |
    poetry run python -c "import cv2, numpy, pymupdf"
```

## Additional Resources

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Python CodeQL Queries](https://github.com/github/codeql/tree/main/python)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)

## Version History

- **2025-02-06**: Initial CodeQL scanning guide for Image Preprocessing Detector
- **Query Suite**: security-extended + security-and-quality
- **Python Version**: 3.12
- **CodeQL Version**: Latest (auto-updated via GitHub Actions)
