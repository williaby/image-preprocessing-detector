---
argument-hint: [--type=all]
description: Scans project for security vulnerabilities using safety (dependencies) and bandit (code analysis).
allowed-tools: Bash(poetry:*, safety:*, bandit:*), Read
---

# Security Vulnerability Scanning

Comprehensive security scanning for Python projects using industry-standard tools.

## Scan Types

### 1. Dependency Scanning (safety)
- Check for known vulnerabilities in dependencies
- Report CVEs with severity ratings
- Provide upgrade recommendations

```bash
poetry run safety check --full-report
```

### 2. Static Code Analysis (bandit)
- Scan for security issues in source code
- Detect SQL injection, XSS, command injection
- Identify insecure configurations

```bash
poetry run bandit -r src -ll
```

### 3. Comprehensive Scan (all)
- Run both dependency and code scans
- Generate unified security report
- Prioritize findings by severity

## Report Format

### Critical Issues (Block PR/Deploy)
- Vulnerabilities with known exploits
- Code patterns with high risk

### High Priority (Fix Soon)
- Recent CVEs in dependencies
- Insecure code patterns

### Medium/Low Priority (Plan Remediation)
- Older vulnerabilities with workarounds
- Best practice violations

## Integration

- CI/CD: Export JSON reports for automation
- Pre-commit: Quick scan for critical issues
- Regular audits: Full scans weekly

---

*Extracted from security.md command with focus on scanning workflows.*
