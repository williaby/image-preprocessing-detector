# Security Policy

## Supported Versions

Currently supported versions for security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via:

### GitHub Private Vulnerability Reporting

Use GitHub's private vulnerability reporting feature:
https://github.com/williaby/image-preprocessing-detector/security/advisories/new

### Email

Alternatively, email security reports to: byronawilliams@gmail.com

Include:
- Type of vulnerability
- Full path to affected source file(s)
- Location of affected code (tag/branch/commit)
- Step-by-step instructions to reproduce
- Proof-of-concept or exploit code (if possible)
- Impact assessment

## Response Timeline

- **Acknowledgment**: Within 7 days
- **Initial Assessment**: Within 14 days
- **Fix Timeline**:
  - Critical: Within 30 days
  - High: Within 60 days
  - Medium: Within 60 days
  - Low: Next release cycle

**Note**: These are target timelines for a single-maintainer project. Actual response times may vary based on severity, complexity, and maintainer availability.

## Disclosure Policy

- Security advisories published after fix is available
- CVE requested for significant vulnerabilities
- Credit given to reporters (unless anonymity requested)

## Security Update Process

1. Fix developed in private fork
2. Fix tested and reviewed
3. Security advisory published
4. Patched version released
5. Public disclosure with CVE (if applicable)

## Security Best Practices for Users

- Keep dependencies updated: `poetry update`
- Run security scans: `poetry run bandit -r src`
- Check for known vulnerabilities: `poetry run safety check`
- Review security advisories: https://github.com/williaby/image-preprocessing-detector/security/advisories

## Automated Security Tools

This project uses the following automated security tools:

| Tool | Purpose | Integration |
|------|---------|-------------|
| **Bandit** | Python security vulnerability scanning | Pre-commit hook + CI/CD |
| **Safety** | Dependency vulnerability checking | Pre-commit hook + CI/CD |
| **MyPy** | Static type checking (prevents type-related bugs) | Pre-commit hook + CI/CD |
| **Pydantic v2** | Runtime data validation and type safety | Core dependency |
| **Poetry** | Dependency lock file with cryptographic hashes | Build system |
| **CodeQL** | Semantic code analysis for vulnerabilities | GitHub Actions CI/CD |
| **Dependabot** | Automated dependency update PRs | GitHub native |

All security tools run automatically on every commit via pre-commit hooks and in the CI/CD pipeline.

## Security Design Principles

This project follows secure development practices:

### Input Validation
- All file inputs validated for type and size
- PDF parsing with size limits and timeouts
- JSON schema validation via Pydantic v2

### Dependency Security
- Regular dependency updates via Poetry
- Automated vulnerability scanning (Safety, Bandit)
- Minimal dependency footprint

### Data Handling
- No external network calls during processing
- Temporary files cleaned up after use
- No persistent storage of user data

### Code Quality
- Type safety via MyPy strict mode
- Comprehensive test coverage (94%+)
- Security-focused linting with Bandit

## Common Vulnerability Mitigations

### OWASP Top 10 Considerations

1. **Injection**: All inputs validated via Pydantic schemas
2. **Broken Authentication**: N/A (no auth system)
3. **Sensitive Data Exposure**: No storage of sensitive data
4. **XXE**: XML external entities disabled in PDF parsing
5. **Broken Access Control**: N/A (local processing only)
6. **Security Misconfiguration**: Strict linting and type checking
7. **XSS**: N/A (no web interface)
8. **Insecure Deserialization**: JSON only via Pydantic validation
9. **Vulnerable Components**: Automated scanning via Safety
10. **Insufficient Logging**: Structured logging with audit trail

### Python-Specific Vulnerabilities

- **Path Traversal**: All file paths validated
- **Command Injection**: No shell command execution
- **Pickle Deserialization**: Not used (JSON only)
- **SQL Injection**: N/A (no database)
- **Code Injection**: No `eval()` or `exec()` usage
