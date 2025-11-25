---
category: security
complexity: low
estimated_time: "< 5 minutes"
dependencies: []
version: "1.0"
---

# Security Validate Environment

Validate security requirements for current development environment.

## Instructions

Check and validate all required security components for safe development:

### 1. GPG Key Validation

```bash
# Check for GPG secret keys (required for .env encryption)
gpg --list-secret-keys

# Check for non-expired keys with signing capability
gpg --list-secret-keys --with-colons | awk -F: '/^sec/ {print $2, $7}' | while read type expiry; do
    if [[ $expiry == "" ]] || [[ $expiry -gt $(date +%s) ]]; then
        echo "✅ Valid signing key found"
    else
        echo "⚠️  Key expired: $(date -d @$expiry)"
    fi
done

# Verify signing capability
gpg --list-secret-keys --with-colons | grep -q "^sec.*S" && echo "✅ Signing capability confirmed" || echo "❌ No signing capability"

# Expected: At least one valid, non-expired secret key with signing capability
# If no keys found: Must set up GPG key for encryption
```

### 2. SSH Key Validation

```bash
# Check for loaded SSH keys (required for signed commits)
ssh-add -l

# Expected: At least one SSH key should be loaded
# If no keys found: Must add SSH key with ssh-add
```

### 3. Git Signing Configuration

```bash
# Check Git signing key configuration
git config --get user.signingkey

# Expected: Should return a GPG key ID
# If empty: Must configure with git config --global user.signingkey <key-id>
```

### 4. Environment Security Check

```bash
# Check for .env files in project root (should be encrypted)
ls -la .env* 2>/dev/null || echo "No .env files found"

# Check for secrets in git history (basic check)
git log --oneline -n 10 | grep -i -E "(password|secret|key|token)" && echo "⚠️  Potential secrets in commit messages"
```

### 5. Dependency Security

For Python projects:

```bash
# Check for known vulnerabilities
poetry run safety check

# Security linting
poetry run bandit -r src
```

## Validation Results

Report the status of each security requirement:

**✅ PASS Requirements**:

- GPG key present and accessible
- SSH key loaded and configured
- Git signing properly configured
- No obvious security issues found

**❌ FAIL Requirements**:

- Missing GPG key (provide setup instructions)
- Missing SSH key (provide setup instructions)
- Git signing not configured (provide fix commands)
- Security vulnerabilities found (provide remediation)

## Setup Instructions

If validation fails, provide specific setup commands:

**GPG Key Setup**:

```bash
gpg --full-generate-key
# Follow prompts to generate key
```

**SSH Key Setup**:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
ssh-add ~/.ssh/id_ed25519
```

**Git Signing Setup**:

```bash
git config --global user.signingkey <your-gpg-key-id>
git config --global commit.gpgsign true
```

## Security Best Practices

- Never commit secrets to repository
- Use encrypted .env files for sensitive configuration
- Sign all commits for authenticity
- Regularly scan dependencies for vulnerabilities
- Keep GPG and SSH keys secure and backed up
