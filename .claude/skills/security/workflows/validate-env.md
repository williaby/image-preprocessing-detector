---
argument-hint: [--verbose]
description: Validates security environment configuration including GPG keys, SSH keys, Git signing, and encrypted secrets setup.
allowed-tools: Bash(gpg:*, ssh:*, git:*), Read
---

# Security Environment Validation

Comprehensive validation of security requirements for safe development with signed commits and encrypted secrets.

## Core Validations

### 1. SSH Key Validation
- Check if SSH key is loaded in ssh-agent
- Verify key type and strength (256-bit minimum)
- Validate key permissions

### 2. Git Signing Configuration
- Check if commit signing is enabled
- Verify signing key configuration
- Validate signing format (SSH or GPG)

### 3. GPG Key Validation (Optional)
- Check for GPG secret keys
- Verify key is not expired
- Confirm encryption capability

### 4. Git User Configuration
- Verify user.name is set
- Verify user.email is set

### 5. Commit Signature Verification
- Check recent commits for signatures
- Validate signature status

## Security Posture Report

Generates comprehensive report:
- ✅ All checks passed: SECURE
- ⚠️ Some warnings: REVIEW NEEDED
- ❌ Critical failures: SETUP REQUIRED

## Verbose Mode

With `--verbose` flag, provides detailed information:
- SSH key details (algorithm, fingerprint, comment)
- Git configuration (global and local)
- GPG key details (ID, type, expiration)
- Recent commit signatures with status

---

*Consolidated from check-security-env skill and security-validate-env command.*
