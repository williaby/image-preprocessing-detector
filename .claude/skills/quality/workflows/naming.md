---
argument-hint: [path]
description: Validate Python naming conventions (PEP 8) for modules, classes, functions, and variables.
allowed-tools: Read, Grep, Bash(find:*, grep:*)
---

# Naming Convention Validation

Validate code follows PEP 8 naming conventions.

## Python Conventions

- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`
- **Variables**: `snake_case`

## Validation Process

1. Scan Python files
2. Extract identifiers (classes, functions, constants, variables)
3. Check against PEP 8 rules
4. Report violations with suggested fixes

## Output

Reports violations with:
- File and line number
- Current name
- Expected convention
- Suggested fix

---

*Consolidated from quality-naming-conventions command and validate-naming skill.*
