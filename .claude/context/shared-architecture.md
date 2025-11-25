# Shared Architecture Patterns

## Core Development Architecture

### Technology Stack

- **Python**: 3.11+ with Poetry dependency management
- **Testing**: pytest with 80%+ coverage requirements
- **Code Quality**: Black (88 chars), Ruff linting, BasedPyright type checking
- **Security**: GPG/SSH key validation, encrypted secrets, dependency scanning

### Security-First Development

- GPG keys required for .env encryption
- SSH keys required for signed commits
- Git signing key must be configured
- All dependencies scanned with safety/bandit
- No hardcoded secrets or credentials

### File Structure Conventions

- **Python**: snake_case naming for files and functions
- **Markdown**: 120-char line length, consistent formatting
- **YAML**: 2-space indentation, 120-char line length
- **Tests**: Mirror source structure in tests/ directory

### Quality Gates

- All code formatted with Black (88-character line length)
- All code must pass Ruff linting checks
- Type hints required for all functions (BasedPyright validation)
- Minimum 80% test coverage across all Python modules
- Pre-commit hooks enforce all standards

## Common Design Patterns

### Error Handling

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise ProcessingError(f"Unable to complete operation: {e}") from e
```

### Async Patterns

```python
async def process_data(data: List[Item]) -> List[Result]:
    async with async_database() as db:
        results = await asyncio.gather(*[
            process_item(item, db) for item in data
        ])
    return results
```

### Configuration Management

- Environment-specific config files
- Encrypted .env files for secrets
- Service accounts in project-specific locations
- Feature flags for progressive enhancement
