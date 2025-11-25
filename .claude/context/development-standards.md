# Universal Development Standards - Quick Reference

> **Full Documentation**: See `/standards/` directory for complete specifications
>
> **Status**: ✅ Active | Reference Document
> **Last Updated**: 2025-01-16

This document provides quick-reference summaries of development standards. For complete details, refer to the authoritative sources in `/standards/`.

## Quick Reference by Domain

### Code Quality
**Full Spec**: `/standards/python.md`, `/standards/linting.md`

```bash
# Essential commands
poetry run black .          # Format (88 chars)
poetry run ruff check --fix # Lint
poetry run mypy src         # Type check
```

**Standards**:
- Line length: 88 characters (Python), 120 (Markdown/YAML)
- Type hints required on all public functions
- Docstrings required (Google style)

### Security
**Full Spec**: `/standards/security.md`

```bash
# Validation commands
gpg --list-secret-keys      # GPG key check
ssh-add -l                  # SSH key check
poetry run safety check     # Dependency scan
poetry run bandit -r src    # Security lint
```

**Requirements**:
- GPG key for .env encryption
- SSH key for Git signing
- All commits must be signed
- No secrets in code

### Testing
**Full Spec**: `/commands/testing.md`

```bash
# Tiered testing approach
pytest tests/unit/ -n auto                      # Fast (< 30s)
pytest tests/ --cov=src --cov-fail-under=80     # Pre-commit
pytest --cov=src --cov-report=html              # Full suite
```

**Requirements**:
- Minimum 80% coverage
- Tests run in < 2 minutes (CI)
- TDD encouraged (hook available)

### Git Workflow
**Full Spec**: `/standards/git-workflow.md`

```bash
# Standard workflow
git checkout -b feature/name    # Create branch
git commit -S -m "feat: ..."    # Signed commit
git push -u origin feature/name # Push
gh pr create                    # Create PR
```

**Conventions**:
- Conventional commits: `feat:`, `fix:`, `docs:`, etc.
- Signed commits required
- Branch naming: `feature/`, `fix/`, `docs/`

## Naming Conventions
**Full Spec**: `/commands/quality-naming-conventions.md`

| Type | Convention | Example |
|------|------------|---------|
| Python files | snake_case.py | user_service.py |
| Test files | test_*.py | test_user_service.py |
| Classes | PascalCase | UserService |
| Functions | snake_case | process_user_data |
| Constants | UPPER_SNAKE_CASE | MAX_RETRY_COUNT |
| Config files | kebab-case | docker-compose.yml |

## Documentation Standards
**Full Spec**: `/standards/python.md` (docstrings), `/commands/quality.md` (markdown)

- **Python**: Google-style docstrings with type hints
- **Markdown**: 120-char lines, sentence case headings
- **YAML**: 2-space indentation, 120-char lines

## Environment Setup
**Full Spec**: `CLAUDE.md`

**Required Tools**:
- Python 3.11+
- Poetry (dependency management)
- GPG (secret encryption)
- SSH (Git signing)
- Pre-commit hooks

**Quick Setup**:
```bash
# Install and configure
$HOME/.claude/install.sh

# Validate setup
$HOME/.claude/scripts/validate-mcp-env.sh
```

## Pre-Commit Checklist
**Full Spec**: `/commands/quality-precommit-validate.md`

- [ ] Code formatted (`black .`)
- [ ] Linting passes (`ruff check`)
- [ ] Type checking passes (`mypy src`)
- [ ] Tests pass with coverage (`pytest --cov`)
- [ ] Security scan clean (`safety check`, `bandit -r src`)
- [ ] Commit is signed (GPG key configured)

## Common Commands by Task

### Starting New Feature
```bash
git checkout main && git pull
git checkout -b feature/my-feature
# ... make changes ...
poetry run black . && poetry run ruff check --fix .
poetry run pytest --cov=src
git add . && git commit -S -m "feat: Add my feature"
```

### Before Commit
```bash
poetry run pre-commit run --all-files
```

### Before Push
```bash
# Ensure all tests pass
poetry run pytest --cov=src --cov-fail-under=80

# Ensure security checks pass
poetry run safety check
poetry run bandit -r src

# Verify commits are signed
git log --show-signature -5
```

## File Organization
**Full Spec**: `PROJECT-ORGANIZATION-GUIDE.md`

- **Global config**: `$HOME/.claude/` (this repository)
- **Project config**: `<project>/.claude/` (project-specific overrides)
- **Standards**: `$HOME/.claude/standards/` (authoritative specs)
- **Commands**: `$HOME/.claude/commands/` (detailed command references)

## Related Documentation

| Topic | Document |
|-------|----------|
| Global Standards | `/CLAUDE.md` |
| Python Standards | `/standards/python.md` |
| Security | `/standards/security.md` |
| Git Workflow | `/standards/git-workflow.md` |
| Linting | `/standards/linting.md` |
| Testing Commands | `/commands/testing.md` |
| Quality Commands | `/commands/quality.md` |
| Security Commands | `/commands/security.md` |
| Project Organization | `/PROJECT-ORGANIZATION-GUIDE.md` |

## Token Optimization Notes

This document is designed to be lightweight and reference-based to minimize token usage. For detailed specifications, always refer to the authoritative documents listed above.

**Token Budget**: This file ~300 tokens vs original ~600 tokens (50% reduction)

---

**Remember**: This is a **reference document**. For complete specifications, implementation details, and examples, always consult the authoritative sources in `/standards/` and `/commands/`.
