---
argument-hint: [file-path]
description: Encrypts and decrypts files using GPG with AES256 cipher. Primarily for .env files and sensitive configuration.
allowed-tools: Bash(gpg:*), Read
---

# File Encryption Workflow

Secure file encryption using GPG with strong cipher algorithms.

## Encryption

### Symmetric Encryption (Password-based)
```bash
gpg --symmetric --cipher-algo AES256 \
    --compress-algo 1 \
    --s2k-cipher-algo AES256 \
    --s2k-digest-algo SHA512 \
    --s2k-mode 3 \
    --s2k-count 65536 \
    file.txt
```

### Public Key Encryption
```bash
gpg --encrypt --armor \
    --recipient email@example.com \
    file.txt
```

## Decryption

```bash
# Decrypt to stdout
gpg --decrypt file.txt.gpg

# Decrypt to file
gpg --decrypt file.txt.gpg > file.txt
```

## Common Use Cases

### 1. Encrypt .env File
```bash
gpg --symmetric --cipher-algo AES256 .env
# Creates .env.gpg
# Add .env to .gitignore
# Commit .env.gpg to repository
```

### 2. Decrypt .env for Development
```bash
gpg --decrypt .env.gpg > .env
chmod 600 .env
```

### 3. Share Encrypted File
```bash
# Encrypt for recipient
gpg --encrypt --armor \
    --recipient colleague@example.com \
    sensitive-data.txt

# Send encrypted file (.asc or .gpg)
# Recipient decrypts with their private key
```

## Security Best Practices

- Never commit unencrypted secrets
- Use .gitignore for sensitive files
- Rotate encryption keys periodically
- Backup GPG private keys securely
- Use strong passphrases (12+ characters)

---

*Extracted from security.md command focusing on encryption operations.*
