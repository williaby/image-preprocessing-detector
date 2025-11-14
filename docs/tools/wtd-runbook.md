---
schema_type: common
title: "What The Diff PR Summaries Runbook"
description: "Operational runbook for What The Diff AI-powered PR summary integration"
tags: [ci_cd, documentation, guide]
status: published
owner: "docs-team"
review_cycle_days: 90
authors:
  - name: "Byron Williams"
purpose: "Document the workflow and best practices for generating AI-powered PR summaries with What The Diff."
---

> **Project:** Image Preprocessing Detector
> **Last Updated:** 2025-11-06

---

## 📖 Overview

**What The Diff** (WTD) automatically generates AI-powered summaries for every pull request in the `image_detection` repository. These summaries provide reviewers with a quick, high-level overview of changes, reducing cognitive load and accelerating the review process.

**Key Benefits:**
- **Faster Reviews**: Immediate understanding of PR scope and impact
- **Consistency**: Standardized summaries across all PRs
- **Context Preservation**: Captures intent and reasoning from code changes
- **Onboarding**: Helps new contributors understand project evolution

### Integration Approach

This project uses the **shortcode method** for WTD integration:
- PR descriptions include `wtd:summary` placeholder
- What The Diff replaces placeholder with AI-generated content
- Integrated with `mcp__zen-core__pr_prepare` tool (see [CLAUDE.md](../CLAUDE.md))
- Automatic inclusion controlled by `include_wtd` parameter (default: `true`)

---

## 🚀 Initial Setup

### Prerequisites

- Repository admin access to `image_detection` on GitHub
- GitHub account with authorization to install apps

### Installation Steps

1. **Login to What The Diff**
   - Navigate to [whatthediff.ai](https://whatthediff.ai)
   - Click "Sign in with GitHub"
   - Authorize the application

2. **Grant Repository Access**
   - In the What The Diff dashboard, navigate to "Repositories"
   - Locate `image_detection` (or your organization's repository)
   - Click "Enable" to activate WTD for this repo

3. **Configure Repository Settings**
   - Click on the enabled repository to access settings
   - Configure according to recommendations below

---

## ⚙️ Configuration Recommendations

### Operational Mode

**Recommended:** Use **Pull Request Descriptions** with shortcodes

```markdown
## Summary
wtd:summary

## Test Plan
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Coverage maintained above 80%
```

**Alternative:** AI Comments (auto-posted to PRs)
- Enable if team prefers comment-based summaries
- Configure trigger: "On PR creation and updates"

### Token Limits

- **Default:** 50,000 tokens per PR
- **Typical Usage:** 2,000-8,000 tokens for Python ML projects
- **Recommendation:** Keep default unless hitting limits on large refactors

### File Exclusion Patterns

Configure What The Diff to **exclude** the following file patterns to reduce token consumption and improve summary quality:

```
# Generated code and dependencies
poetry.lock
requirements*.txt
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# Test artifacts
.pytest_cache/
htmlcov/
.coverage
*.coverage.*

# IDE and tooling
.vscode/
.idea/
*.swp
*.swo

# Documentation builds
docs/_build/
site/

# Large binary files
*.pt
*.pth
*.onnx
*.h5
*.pkl
*.joblib

# Media and test data
*.png
*.jpg
*.jpeg
*.gif
*.pdf
*.tiff

# CI/CD artifacts
.github/workflows/*.yml  # Include only if you want WTD to ignore workflow changes

# Temporary and validation files
tmp_cleanup/
validation/report.json
validation/*.png
```

### File Inclusion (Alternative)

If you prefer allowlist approach, configure **only** these directories:

```
src/
tests/
pyproject.toml
CLAUDE.md
PROJECT_PLAN.md
ARCHITECTURE_*.md
```

### Branch and Title Filters

**Recommended exclusions:**
- Branch pattern: `dependabot/*` (automated dependency updates)
- Title pattern: `WIP:`, `[WIP]`, `Draft:` (unfinished work)

---

## 🔄 Workflow Integration

### PR Preparation with Zen MCP

The project uses the `mcp__zen-core__pr_prepare` tool to automate PR creation with WTD integration:

```bash
# Claude Code automatically invokes:
mcp__zen-core__pr_prepare --include_wtd=true --target_branch=main
```

**What happens:**
1. Tool analyzes git commit history and changes
2. Generates PR title and body with context
3. Inserts `wtd:summary` shortcode in PR description
4. Pushes branch and creates draft PR on GitHub
5. What The Diff detects shortcode and generates summary
6. Summary appears inline within minutes

### Manual PR Creation

If creating PRs manually via GitHub UI or `gh` CLI:

```markdown
## Summary
wtd:summary

## Changes
- Add YOLOv8 layout detection module
- Implement hybrid IQA for embedded images
- Update schema with per-element quality assessment

## Test Plan
- [x] Unit tests pass (95% coverage)
- [x] Integration tests with sample PDFs
- [ ] Performance benchmark on T4 GPU

## Related Issues
Closes #42
```

**Important:** Place `wtd:summary` **before** detailed change descriptions to avoid duplicate content.

---

## 🛠️ How It Works

### Trigger Phase

What The Diff activates when:
- Pull request is **opened**
- Pull request is **reopened**
- New **commits** are pushed to an open PR

**Exclusions:**
- Bot-authored PRs (dependabot, renovate, github-actions)
- Draft PRs (if configured in settings)

### Diff Analysis

1. **Fetch Changes**: WTD retrieves the PR diff from GitHub API
2. **Apply Filters**: Excludes files matching configured patterns (see [File Exclusion Patterns](#file-exclusion-patterns))
3. **Token Estimation**: Calculates token usage based on remaining diff
4. **Context Building**: Includes commit messages, file paths, and code context

### Summary Generation

1. **AI Processing**: Sends filtered diff to OpenAI GPT-4 or Claude API
2. **Summary Creation**: Generates:
   - High-level overview (1-2 sentences)
   - Key changes by module/category
   - Potential impact areas
   - Testing recommendations (if applicable)
3. **Shortcode Replacement**: Injects summary into PR description where `wtd:summary` appears

**Typical Latency:** 30-90 seconds for Python ML projects with 500-2000 LOC changes

---

## 📝 .gitattributes Configuration

Add the following to `.gitattributes` to mark generated/vendored files as linguist-generated (improves GitHub diffs and WTD filtering):

```gitattributes
# Generated dependencies
poetry.lock linguist-generated=true
requirements*.txt linguist-generated=true

# Test coverage reports
htmlcov/* linguist-generated=true
.coverage linguist-generated=true

# Model weights and artifacts (if committed)
*.pt linguist-generated=true
*.pth linguist-generated=true
*.onnx linguist-generated=true

# Documentation builds
docs/_build/* linguist-generated=true

# Temporary files
tmp_cleanup/* linguist-generated=true
```

**Note:** This project's `.gitignore` already excludes most generated files, so `.gitattributes` is optional but recommended for any committed artifacts.

---

## 🐛 Troubleshooting

### Summary Not Appearing

**Symptom:** PR created but no WTD summary generated

**Checks:**
1. Verify `wtd:summary` shortcode is present in PR description
2. Check repository is enabled in What The Diff dashboard
3. Confirm PR is not from a bot account (dependabot, renovate)
4. Check What The Diff status page for service issues

**Resolution:**
- Edit PR description to add/fix `wtd:summary` shortcode
- Close and reopen PR to trigger regeneration
- Check organization billing if on paid plan

### Token Limit Exceeded

**Symptom:** Summary incomplete or error message about token limits

**Causes:**
- Large refactoring PRs (10,000+ LOC changes)
- Binary files not properly excluded
- Generated files included in diff

**Resolution:**
1. Review [File Exclusion Patterns](#file-exclusion-patterns) configuration
2. Add problematic file patterns to exclusion list
3. Split large PRs into smaller, focused changes
4. Increase token limit in What The Diff settings (if available)

### Incorrect or Low-Quality Summary

**Symptom:** Summary misses key changes or includes irrelevant details

**Causes:**
- Inadequate commit messages (WTD uses these for context)
- Complex architectural changes without documentation
- Mixed concerns in single PR (features + refactoring + fixes)

**Resolution:**
1. Write descriptive commit messages following Conventional Commits format
2. Add context in PR description **above** `wtd:summary` shortcode:
   ```markdown
   ## Context
   This PR implements Phase 2 hybrid IQA approach, addressing the architectural
   correction identified in ARCHITECTURE_CORRECTION.md.

   ## Summary
   wtd:summary
   ```
3. Split PRs to focus on single concerns
4. Regenerate summary by editing/saving PR description

### WTD Dashboard Access Issues

**Symptom:** Cannot access What The Diff dashboard or settings

**Resolution:**
- Verify GitHub organization admin privileges
- Re-authorize What The Diff GitHub app
- Check organization's third-party app policies
- Contact What The Diff support: support@whatthediff.ai

---

## 📊 Best Practices

### For PR Authors

1. **Write Clear Commit Messages**: WTD uses these for context
   ```bash
   feat(detection): add YOLOv8 layout detection for text documents

   - Implement LayoutDetector class with YOLOv8n inference
   - Add bounding box extraction with COCO alignment
   - Include confidence thresholding (default 0.5)

   Relates to #42
   ```

2. **Use Shortcodes Strategically**: Place `wtd:summary` early in PR description
   ```markdown
   ## Summary
   wtd:summary

   ## Detailed Changes
   [Your detailed notes here]
   ```

3. **Provide Context**: Add brief context for complex changes
   ```markdown
   ## Context
   Addresses architectural correction for hybrid IQA approach.
   See ARCHITECTURE_CORRECTION.md for detailed rationale.

   ## Summary
   wtd:summary
   ```

4. **Keep PRs Focused**: Smaller, focused PRs generate better summaries
   - Target: < 500 LOC changes per PR
   - Single concern per PR (one feature, one fix, one refactor)

### For Reviewers

1. **Read Summary First**: Use WTD summary as PR overview before diving into code
2. **Validate Against Changes**: Ensure summary accurately reflects actual changes
3. **Provide Feedback**: If summary misses key points, add reviewer comments to supplement
4. **Trust but Verify**: WTD is a tool, not a replacement for thorough review

### For Maintainers

1. **Monitor Token Usage**: Check What The Diff dashboard monthly for usage patterns
2. **Refine Exclusions**: Add new patterns as project evolves (e.g., new build artifacts)
3. **Review Quality**: Periodically assess summary quality and adjust settings
4. **Educate Team**: Share this runbook with new contributors

---

## 🔗 Additional Resources

- [What The Diff Documentation](https://whatthediff.ai/docs)
- [GitHub Integration Guide](https://whatthediff.ai/docs/github)
- [Shortcode Reference](https://whatthediff.ai/docs/shortcodes)
- [Project PR Preparation Tool](../CLAUDE.md#pr-preparation-workflow-automated)

---

## 📞 Support

- **What The Diff Support**: support@whatthediff.ai
- **Project Issues**: [GitHub Issues](https://github.com/YOUR_ORG/image_detection/issues)
- **Internal Questions**: Ask in #dev-tools Slack channel (if applicable)

---

*This runbook is maintained as part of the Image Preprocessing Detector project documentation.*
*Last verified with What The Diff v2.x (2025-11-06)*
