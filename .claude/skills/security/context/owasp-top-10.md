# OWASP Top 10 Security Risks (2021)

Quick reference for the most critical web application security risks.

## 1. Broken Access Control

**Risk**: Users can access resources they shouldn't.

**Prevention**:
- Deny by default
- Implement proper authorization checks
- Log access control failures
- Disable directory listing

## 2. Cryptographic Failures

**Risk**: Sensitive data exposure due to weak/missing encryption.

**Prevention**:
- Encrypt data at rest and in transit
- Use strong algorithms (AES-256, RSA-4096)
- Never store passwords in plaintext
- Use HTTPS everywhere

## 3. Injection

**Risk**: Untrusted data sent to interpreter (SQL, NoSQL, OS commands).

**Prevention**:
- Use parameterized queries
- Validate and sanitize all inputs
- Use ORM/safe APIs
- Escape special characters

## 4. Insecure Design

**Risk**: Missing or ineffective control design.

**Prevention**:
- Threat modeling
- Secure design patterns
- Security requirements
- Defense in depth

## 5. Security Misconfiguration

**Risk**: Insecure default configurations.

**Prevention**:
- Minimal platform configuration
- Remove unnecessary features
- Update security patches
- Review cloud storage permissions

## 6. Vulnerable and Outdated Components

**Risk**: Using components with known vulnerabilities.

**Prevention**:
- Regular dependency scans
- Monitor CVE databases
- Update dependencies promptly
- Remove unused dependencies

## 7. Identification and Authentication Failures

**Risk**: Broken authentication allows attackers to compromise accounts.

**Prevention**:
- Multi-factor authentication
- Strong password policies
- Implement rate limiting
- Secure session management

## 8. Software and Data Integrity Failures

**Risk**: Code/infrastructure without integrity verification.

**Prevention**:
- Digital signatures
- Verify dependencies
- Use CI/CD with security checks
- Implement code review

## 9. Security Logging and Monitoring Failures

**Risk**: Breaches not detected/responded to.

**Prevention**:
- Log all security events
- Monitor for suspicious activity
- Implement alerting
- Regular log review

## 10. Server-Side Request Forgery (SSRF)

**Risk**: Application fetches remote resources without validation.

**Prevention**:
- Sanitize and validate all client-supplied URLs
- Whitelist allowed destinations
- Disable HTTP redirections
- Use network segmentation

---

*Use as reference when conducting security audits and code reviews.*
