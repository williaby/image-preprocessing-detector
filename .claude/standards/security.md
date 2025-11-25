# Security Development Standards

## Key Management Requirements

### GPG Key Requirements

- **Purpose**: Encrypt `.env` files and sensitive configuration
- **Key Type**: RSA 4096-bit minimum or Ed25519
- **Expiration**: Keys must have expiration dates (max 2 years)
- **Backup**: Secure backup of private keys required

### GPG Key Validation

```bash
# Check GPG keys are available
gpg --list-secret-keys

# Expected output: Must show at least one private key
# sec   rsa4096/KEYID 2023-01-01 [SC] [expires: 2025-01-01]
#       FINGERPRINT
# uid           [ultimate] Your Name <email@example.com>
# ssb   rsa4096/SUBKEY 2023-01-01 [E] [expires: 2025-01-01]

# Encrypt sensitive files
gpg --cipher-algo AES256 --compress-algo 1 --s2k-cipher-algo AES256 \
    --s2k-digest-algo SHA512 --s2k-mode 3 --s2k-count 65536 \
    --symmetric .env
```

### SSH Key Requirements

- **Purpose**: Sign Git commits and authenticate to repositories
- **Key Type**: Ed25519 preferred, RSA 4096-bit minimum
- **Passphrase**: All SSH keys must be passphrase-protected
- **Agent**: Use SSH agent for key management

### SSH Key Validation

```bash
# Check SSH keys are loaded
ssh-add -l

# Expected output: Must show at least one key
# 256 SHA256:hash_here email@example.com (ED25519)

# Add key if not loaded
ssh-add ~/.ssh/id_ed25519

# Generate new SSH key if needed
ssh-keygen -t ed25519 -C "email@example.com"
```

## Git Security Configuration

### Signed Commits

- **Requirement**: All commits must be GPG signed
- **Configuration**: Git signing key must be configured
- **Verification**: Commits show "Verified" badge in GitHub

### Git Configuration

```bash
# Configure signing key
git config --global user.signingkey KEYID

# Enable commit signing by default
git config --global commit.gpgsign true

# Configure GPG program
git config --global gpg.program gpg

# Verify configuration
git config --get user.signingkey  # Must return key ID
```

### Pre-commit Security Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

## Dependency Security

### Vulnerability Scanning

- **Safety**: Check Python dependencies for known vulnerabilities
- **Bandit**: Static security analysis for Python code
- **Audit**: Regular dependency audits (monthly minimum)

### Security Scanning Commands

```bash
# Python dependency vulnerability check
poetry run safety check

# Static security analysis
poetry run bandit -r src

# Generate security report
poetry run bandit -r src -f json -o security-report.json

# Audit with detailed output
poetry run safety check --full-report
```

### Dependency Management

```bash
# Update dependencies to latest secure versions
poetry update

# Check for outdated packages
poetry show --outdated

# Add dependencies with version constraints
poetry add "requests>=2.28.0,<3.0.0"
```

## Secrets Management

### Environment Variables

- **No Hardcoding**: Never hardcode secrets in source code
- **Environment Files**: Use `.env` files for local development
- **Encryption**: Encrypt `.env` files with GPG
- **Templates**: Provide `.env.example` with dummy values

### Secrets Best Practices

```bash
# Create encrypted environment file
cp .env.example .env
# Edit .env with real values
gpg --symmetric .env
rm .env  # Remove unencrypted file
```

### Secret Detection

```bash
# Scan for accidentally committed secrets
git log --all --full-history --grep="password\|secret\|key\|token"

# Use detect-secrets for comprehensive scanning
detect-secrets scan --all-files --baseline .secrets.baseline
```

## Application Security

### Input Validation

- **Sanitization**: All user inputs must be validated and sanitized
- **SQL Injection**: Use parameterized queries or ORM
- **XSS Prevention**: Escape output in web applications
- **CSRF Protection**: Implement CSRF tokens for state-changing operations

### Security Headers

```python
# Flask/FastAPI security headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

### Authentication and Authorization

- **Strong Passwords**: Enforce password complexity requirements
- **MFA**: Multi-factor authentication for admin accounts
- **Session Management**: Secure session handling with proper expiration
- **Principle of Least Privilege**: Grant minimal necessary permissions

## Environment Security

### Development Environment

```bash
# Secure file permissions
chmod 600 .env*
chmod 700 ~/.ssh/
chmod 600 ~/.ssh/id_*

# Verify permissions
ls -la .env* ~/.ssh/
```

### Production Security

- **Environment Isolation**: Separate dev/staging/prod environments
- **Access Control**: Restrict production access to authorized personnel
- **Monitoring**: Log security events and monitor for anomalies
- **Backup Security**: Encrypt backups and restrict access

## Incident Response

### Security Event Logging

```python
import logging
import structlog

# Configure security logging
security_logger = structlog.get_logger("security")

# Log security events
security_logger.warning(
    "Authentication failure",
    user_id=user_id,
    ip_address=request.remote_addr,
    timestamp=datetime.utcnow()
)
```

### Breach Response

1. **Immediate**: Isolate affected systems
2. **Assessment**: Determine scope and impact
3. **Notification**: Inform stakeholders within 24 hours
4. **Remediation**: Fix vulnerabilities and update systems
5. **Documentation**: Document incident and lessons learned

## Compliance Requirements

### Data Protection

- **GDPR**: Implement data protection by design
- **PCI DSS**: Follow standards for payment card data
- **HIPAA**: Protect health information if applicable
- **SOC 2**: Implement controls for security and availability

### Audit Requirements

- **Access Logs**: Maintain detailed access logs
- **Change Management**: Document all security-related changes
- **Regular Reviews**: Quarterly security reviews minimum
- **Penetration Testing**: Annual penetration testing

## Security Validation Checklist

Before any deployment:

- [ ] GPG key available and configured
- [ ] SSH key loaded and configured for signed commits
- [ ] All dependencies scanned for vulnerabilities
- [ ] Static security analysis passed
- [ ] No secrets detected in code
- [ ] Security headers implemented
- [ ] Authentication and authorization tested
- [ ] Input validation implemented
- [ ] Secure file permissions set
- [ ] Security logging configured

## Emergency Procedures

### Key Compromise

```bash
# Revoke compromised GPG key
gpg --gen-revoke KEYID > revoke.asc
gpg --import revoke.asc

# Generate new SSH key
ssh-keygen -t ed25519 -C "email@example.com"
# Update GitHub/GitLab with new public key
```

### Security Incident

1. **Isolate**: Disconnect affected systems
2. **Preserve**: Save logs and evidence
3. **Notify**: Contact security team immediately
4. **Document**: Record all actions taken
5. **Analyze**: Perform post-incident analysis

---

*This file contains comprehensive security standards. For security command references, see `/commands/security.md`.*
