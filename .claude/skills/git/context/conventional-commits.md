# Conventional Commits Specification

Complete reference for Conventional Commits format used in commit messages.

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Type

The type indicates the nature of the change.

### Valid Types

| Type | Purpose | Example |
|------|---------|---------|
| **feat** | New feature | feat(auth): add OAuth2 support |
| **fix** | Bug fix | fix(api): resolve timeout issue |
| **docs** | Documentation | docs(readme): update installation |
| **style** | Code style | style(ui): format with prettier |
| **refactor** | Code refactoring | refactor(db): optimize queries |
| **test** | Tests | test(auth): add unit tests |
| **chore** | Maintenance | chore(deps): upgrade packages |
| **ci** | CI/CD | ci(gh): add deployment workflow |
| **perf** | Performance | perf(api): cache user queries |

---

*Based on Conventional Commits v1.0.0 specification.*
