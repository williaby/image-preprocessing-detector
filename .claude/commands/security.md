---
category: security
complexity: medium
estimated_time: "5-20 minutes"
dependencies: ["gpg", "ssh", "poetry"]
version: "1.0"
---

# Security Commands

Comprehensive security validation, scanning, and enforcement commands for development environments and applications.

## Quick Reference

```bash
# Complete security validation
gpg --list-secret-keys && ssh-add -l && git config --get user.signingkey
poetry run safety check && poetry run bandit -r src

# Environment setup validation
./scripts/validate-mcp-env.sh || $HOME/.claude/scripts/validate-mcp-env.sh

# Dependency security scan
poetry run safety check --full-report
```

## Environment Security Validation

### GPG Key Validation

```bash
# Check for GPG secret keys (required for .env encryption)
gpg --list-secret-keys

# Expected output: Must show at least one private key
# sec   rsa4096/KEYID 2023-01-01 [SC] [expires: 2025-01-01]
# uid   [ultimate] Your Name <email@example.com>

# List public keys
gpg --list-keys

# Check GPG configuration
gpg --version
echo $GPG_TTY
```

### SSH Key Validation

```bash
# Check SSH keys loaded in agent (required for signed commits)
ssh-add -l

# Expected output: Must show at least one key
# 256 SHA256:hash_here email@example.com (ED25519)

# Add SSH key if not loaded
ssh-add ~/.ssh/id_ed25519

# List all SSH keys
ls -la ~/.ssh/

# Test SSH connection to GitHub
ssh -T git@github.com
```

### Git Security Configuration

```bash
# Check Git signing configuration
git config --get user.signingkey

# Expected output: GPG key ID for commit signing

# Verify Git user configuration
git config --get user.name
git config --get user.email

# Check if commit signing is enabled
git config --get commit.gpgsign

# Test signed commit
git commit --allow-empty -S -m "test: verify GPG signing"
```

## Dependency Security Scanning

### Python Dependency Vulnerability Check

```bash
# Basic vulnerability check
poetry run safety check

# Detailed vulnerability report
poetry run safety check --full-report

# Check specific requirements file
poetry run safety check --file requirements.txt

# Output JSON format for CI
poetry run safety check --json

# Check and ignore specific vulnerabilities
poetry run safety check --ignore 51668

# Update safety database
poetry run safety --update
```

### Static Security Analysis

```bash
# Basic Bandit security scan
poetry run bandit -r src

# Detailed report with confidence levels
poetry run bandit -r src -ll

# Output JSON format
poetry run bandit -r src -f json

# Save report to file
poetry run bandit -r src -o security-report.txt

# Scan with custom configuration
poetry run bandit -r src -c .bandit

# Exclude specific files or directories
poetry run bandit -r src --exclude tests/,migrations/
```

### Advanced Security Scanning

```bash
# Check for secrets in code
poetry run detect-secrets scan --all-files

# Update secrets baseline
poetry run detect-secrets scan --update .secrets.baseline

# Audit detected secrets
poetry run detect-secrets audit .secrets.baseline

# Scan git history for secrets
git log --all --full-history --grep="password\|secret\|key\|token"
```

## Key Management Commands

### GPG Operations

```bash
# Generate new GPG key
gpg --full-generate-key

# Export public key
gpg --armor --export email@example.com

# Export private key (for backup)
gpg --armor --export-secret-keys email@example.com

# Import key from file
gpg --import keyfile.asc

# Delete key
gpg --delete-secret-keys KEYID
gpg --delete-keys KEYID

# Set default key
echo "default-key KEYID" >> ~/.gnupg/gpg.conf
```

### SSH Key Management

```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "email@example.com"

# Add key to SSH agent
ssh-add ~/.ssh/id_ed25519

# List keys in agent
ssh-add -l

# Remove all keys from agent
ssh-add -D

# Copy public key to clipboard (Linux)
cat ~/.ssh/id_ed25519.pub | xclip -selection clipboard

# Copy public key to clipboard (macOS)
cat ~/.ssh/id_ed25519.pub | pbcopy
```

### File Encryption

```bash
# Encrypt .env file with GPG
gpg --cipher-algo AES256 --compress-algo 1 \
    --s2k-cipher-algo AES256 --s2k-digest-algo SHA512 \
    --s2k-mode 3 --s2k-count 65536 --symmetric .env

# Decrypt .env file
gpg --decrypt .env.gpg > .env

# Encrypt for specific recipient
gpg --encrypt --armor --recipient email@example.com file.txt

# Sign and encrypt
gpg --sign --encrypt --armor --recipient email@example.com file.txt
```

## File and Directory Security

### Permission Management

```bash
# Set secure permissions for sensitive files
chmod 600 .env*
chmod 600 ~/.ssh/id_*
chmod 700 ~/.ssh/
chmod 600 ~/.gnupg/*

# Check file permissions
ls -la .env* ~/.ssh/ ~/.gnupg/

# Find files with incorrect permissions
find . -type f -perm /o+rwx -exec ls -l {} \;

# Remove world-readable permissions recursively
chmod -R o-rwx .
```

### Sensitive File Detection

```bash
# Find potential sensitive files
find . -name "*.key" -o -name "*.pem" -o -name "*.p12" -o -name "*.pfx"

# Check for common sensitive file patterns
grep -r -E "(password|secret|key|token|api_key)" . --exclude-dir=.git

# Find large files that might contain secrets
find . -size +10M -type f

# Check for binary files in git
git ls-files | xargs file | grep -v text
```

## Network and Connection Security

### SSL/TLS Verification

```bash
# Check SSL certificate
openssl s_client -connect example.com:443 -servername example.com

# Verify certificate chain
openssl verify -CAfile ca-bundle.crt certificate.crt

# Check certificate expiration
openssl x509 -in certificate.crt -noout -dates

# Test HTTPS connection with curl
curl -I --insecure https://example.com
```

### Network Security Checks

```bash
# Check open ports
netstat -tlnp

# Check listening services
ss -tlnp

# Scan for open ports on localhost
nmap -sT -O localhost

# Check firewall status (Linux)
sudo ufw status

# Check firewall status (macOS)
sudo pfctl -sr
```

## Application Security Testing

### Web Application Security

```bash
# Install and run security testing tools
pip install bandit semgrep

# Run semgrep security rules
semgrep --config=auto .

# Run custom security rules
semgrep --config=security .

# Check for SQL injection patterns
grep -r -E "(SELECT|INSERT|UPDATE|DELETE).*\+.*\$" .
```

### API Security Testing

```bash
# Test API endpoints with curl
curl -X GET "https://api.example.com/users" \
     -H "Authorization: Bearer invalid_token"

# Test rate limiting
for i in {1..100}; do curl -s https://api.example.com/endpoint; done

# Check HTTP security headers
curl -I https://example.com | grep -E "(X-|Strict|Content-Security)"
```

## Container Security

### Docker Security

```bash
# Scan Docker image for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image python:3.11

# Check Docker security
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  docker/docker-bench-security

# Remove unused Docker resources
docker system prune -a
```

## Incident Response Commands

### Emergency Response

```bash
# Check recent login attempts
last -n 20

# Check system logs for security events
sudo tail -f /var/log/auth.log

# Check process list for suspicious activity
ps aux | grep -E "(nc|netcat|nmap|wget|curl)"

# Check network connections
netstat -anp | grep ESTABLISHED

# Block IP address (Linux)
sudo iptables -A INPUT -s suspicious.ip.address -j DROP
```

### Evidence Collection

```bash
# Create security incident log
echo "$(date): Security incident detected" >> security-incident.log

# Collect system information
uname -a >> incident-info.txt
whoami >> incident-info.txt
env >> incident-info.txt

# Create memory dump (if necessary - WARNING: Use with caution)
# Note: Direct /dev/mem access may be restricted by modern kernel protections
# Consider using specialized tools like LiME or AVML for memory acquisition
# sudo dd if=/dev/mem of=memory-dump.img  # Legacy approach - use with extreme caution
echo "Memory dump skipped - use specialized forensic tools for production systems"

# Archive logs
tar -czf incident-logs-$(date +%Y%m%d).tar.gz /var/log/
```

## Automation Scripts

### Security Validation Script

```bash
#!/bin/bash
# ~/.claude/scripts/validate-security.sh

set -e

echo "🔒 Running security validation..."

# Check GPG key
if ! gpg --list-secret-keys >/dev/null 2>&1; then
    echo "❌ No GPG secret key found"
    exit 1
fi

# Check SSH key
if ! ssh-add -l >/dev/null 2>&1; then
    echo "❌ No SSH key loaded in agent"
    exit 1
fi

# Check Git signing
if ! git config --get user.signingkey >/dev/null; then
    echo "❌ Git signing key not configured"
    exit 1
fi

# Run dependency scan
if command -v poetry >/dev/null; then
    poetry run safety check
    poetry run bandit -r src >/dev/null
fi

echo "✅ Security validation passed"
```

### Pre-commit Security Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for secrets
if command -v detect-secrets >/dev/null; then
    detect-secrets scan --force-use-all-plugins --disable-plugin AbsolutePathDetectorPlugin
fi

# Check for large files
git diff --staged --name-only | xargs ls -la | awk '$5 > 1048576 { print $9 ": " $5 " bytes" }'

# Verify GPG signing
if ! git config --get user.signingkey >/dev/null; then
    echo "Error: GPG signing key not configured"
    exit 1
fi
```

## CI/CD Security Integration

### GitHub Actions Security

```yaml
# .github/workflows/security.yml
- name: Run security scans
  run: |
    poetry run safety check --json --output safety-report.json
    poetry run bandit -r src -f json -o bandit-report.json

- name: Upload security reports
  uses: actions/upload-artifact@v3
  with:
    name: security-reports
    path: '*-report.json'
```

### Security Configuration Files

#### .bandit configuration

```yaml
# .bandit
exclude_dirs:
  - tests
  - venv
  - .venv

skips:
  - B101  # Skip assert_used test in test files

tests:
  - B201
  - B301
  - B302
  - B303
  - B304
  - B305
  - B306
  - B307
  - B308
  - B309
  - B310
  - B311
  - B312
  - B313
  - B314
  - B315
  - B316
  - B317
  - B318
  - B319
  - B320
  - B321
  - B322
  - B323
  - B324
  - B325
  - B401
  - B402
  - B403
  - B404
  - B405
  - B406
  - B407
  - B408
  - B409
  - B410
  - B411
  - B412
  - B413
  - B501
  - B502
  - B503
  - B504
  - B505
  - B506
  - B507
  - B601
  - B602
  - B603
  - B604
  - B605
  - B606
  - B607
  - B608
  - B609
  - B610
  - B611
  - B701
  - B702
  - B703
```

---

*This file contains comprehensive security commands and procedures. For security standards and requirements, see `/standards/security.md`.*
