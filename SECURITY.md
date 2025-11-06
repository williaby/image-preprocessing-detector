# Security Policy

## Supported Versions

The Image Preprocessing Detector project follows [Semantic Versioning](https://semver.org/). We provide security updates for the following versions:

| Version | Supported          | Notes                          |
| ------- | ------------------ | ------------------------------ |
| 0.1.x   | :white_check_mark: | Active development (Phase 1)   |
| < 0.1.0 | :x:                | Pre-release, not supported     |

As the project matures, we will extend support to multiple major versions. Users should upgrade to supported versions to receive security patches.

## Reporting a Vulnerability

**IMPORTANT**: Please **DO NOT** open public GitHub issues for security vulnerabilities.

### Reporting Channels

We accept security vulnerability reports through two confidential channels:

1. **GitHub Security Advisory** (Preferred)
   - Navigate to the [Security tab](../../security/advisories) in this repository
   - Click "Report a vulnerability"
   - Fill out the confidential advisory form

2. **Encrypted Email**
   - Email: `byronawilliams@gmail.com`
   - For sensitive issues, encrypt with PGP key (available upon request)

### What to Include

Please provide as much information as possible to help us understand and resolve the issue:

- **Affected Component**: Which module or feature is vulnerable (e.g., PDF ingestion, image processing, CLI)
- **Vulnerability Type**: (e.g., path traversal, arbitrary code execution, DoS, information disclosure)
- **Affected Versions**: Version numbers where the vulnerability exists
- **Description**: Clear explanation of the security issue
- **Reproduction Steps**: Detailed steps to reproduce the vulnerability
- **Proof of Concept**: Code, screenshots, or example files demonstrating the issue
- **Impact Assessment**: Potential consequences and attack scenarios
- **Suggested Fix**: If you have ideas for remediation (optional but appreciated)
- **CVE ID**: If you've already obtained a CVE identifier (optional)

### Response Timeline

We are committed to addressing security issues promptly:

- **Acknowledgment**: Within **72 hours** of receiving your report
- **Initial Assessment**: Within **7 days** of acknowledgment
- **Status Updates**: Every **14 days** until resolution
- **Critical Issues**: Mitigation or fix within **90 days** of acknowledgment
- **High/Medium Issues**: Fix within **120 days** of acknowledgment
- **Low Issues**: Fix in next planned release or within **180 days**

### Disclosure Policy

We follow **coordinated disclosure**:

1. You report the vulnerability confidentially
2. We acknowledge and investigate
3. We develop and test a fix
4. We release a security patch
5. We publish a security advisory with credit to the reporter
6. Public disclosure occurs **90 days after the patch release** or when exploits appear in the wild (whichever comes first)

If you plan to publicly disclose the vulnerability, please give us reasonable advance notice (minimum 90 days) to develop and release a fix.

## Security Measures

The Image Preprocessing Detector implements multiple security layers:

### Automated Security Scanning

- **CodeQL Analysis**: Static analysis for security vulnerabilities ([security-analysis.yml](.github/workflows/security-analysis.yml))
- **Dependency Scanning**: Safety and Bandit scans on all dependencies
- **Semgrep Security Rules**: Custom security patterns for Python and image processing
- **Container Scanning**: Trivy scans for container vulnerabilities (Phase 4)
- **Secret Detection**: GitGuardian for leaked credentials
- **SBOM Generation**: Software Bill of Materials for supply chain transparency

### Development Security Practices

- **Pre-commit Hooks**: Bandit, Safety, and secret detection before commits ([.pre-commit-config.yaml](.pre-commit-config.yaml))
- **Code Review**: All changes require review before merging (enforced via branch protection)
- **Signed Commits**: GPG-signed commits for authenticity
- **Minimal Permissions**: GitHub Actions workflows use least-privilege permissions
- **Hardened Runners**: StepSecurity harden-runner for CI/CD supply chain security
- **Dependency Pinning**: Poetry lock files and GitHub Actions SHA pinning

### Image Processing Specific Security

This project processes untrusted PDFs and images, which are high-risk inputs. We implement:

- **Path Sanitization**: All file paths validated and resolved to prevent directory traversal
- **File Type Validation**: Magic number verification for PDF/image formats
- **Size Limits**: Maximum file size enforcement to prevent resource exhaustion
- **Timeout Enforcement**: Processing timeouts to prevent denial of service
- **Memory Limits**: Bounded memory allocation for image processing
- **Input Validation**: Schema validation for all JSON inputs (Pydantic v2)
- **Sandboxed Execution**: Isolated processing for untrusted documents (Phase 4)

### Security Testing

- **Unit Tests**: Security-focused test cases for input validation
- **Integration Tests**: End-to-end security testing with malformed inputs
- **Fuzzing**: Property-based testing with Hypothesis (Phase 2+)
- **Penetration Testing**: External security audits (planned for Phase 4)

## Known Security Limitations

### Current Phase (Phase 1 - MVP)

During early development phases, the following security features are **not yet implemented**:

- **No Sandboxing**: PDF/image processing runs in the main process (planned for Phase 4)
- **Limited Fuzzing**: Comprehensive fuzzing planned for Phase 2-3
- **No Rate Limiting**: API rate limiting planned for Phase 4
- **No RBAC**: Role-based access control planned for Phase 4 API

**Recommendation**: Do not use Phase 1 releases in production environments with untrusted inputs. Wait for Phase 4 (Production Hardening) for production deployments.

## Security Best Practices for Users

If you're integrating the Image Preprocessing Detector into your application:

1. **Run in Isolated Environment**: Use containers or VMs to isolate image processing
2. **Validate Inputs**: Apply your own input validation before passing files to the detector
3. **Set Resource Limits**: Use ulimit or container resource constraints
4. **Monitor for Anomalies**: Track processing times and memory usage for unusual patterns
5. **Keep Updated**: Regularly update to the latest version for security patches
6. **Review Dependencies**: Audit the dependency tree for known vulnerabilities
7. **Enable Logging**: Use structured logging to detect security events

## Security Contacts

- **Primary Contact**: Byron Williams (byronawilliams@gmail.com)
- **GitHub Team**: [@williaby/security](https://github.com/orgs/williaby/teams/security) (if organization team exists)

## Security Hall of Fame

We appreciate security researchers who responsibly disclose vulnerabilities. Contributors will be acknowledged here (with their permission):

*No vulnerabilities reported yet - be the first!*

---

**Last Updated**: 2025-11-05
**Security Policy Version**: 1.0
