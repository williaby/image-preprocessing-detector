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
./scripts/validate-mcp-env.sh || /home/byron/.claude/scripts/validate-mcp-env.sh

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

# Core Security Commands Reference

## Environment Validation
```bash
# GPG key check
gpg --list-secret-keys

# SSH key check
ssh-add -l

# Git signing check
git config --get user.signingkey
git config --get commit.gpgsign
```

## Dependency Scanning
```bash
# Python vulnerabilities
poetry run safety check --full-report

# Static code analysis
poetry run bandit -r src -ll
```

## File Encryption
```bash
# Encrypt with AES256
gpg --symmetric --cipher-algo AES256 file.txt

# Decrypt
gpg --decrypt file.txt.gpg > file.txt
```

## Key Management
```bash
# Generate GPG key
gpg --full-generate-key

# Generate SSH key
ssh-keygen -t ed25519 -C "email@example.com"

# Add SSH key to agent
ssh-add ~/.ssh/id_ed25519
```

---

*For complete command reference, see original security.md in commands/ directory.*
*This is a quick reference for common security operations.*
