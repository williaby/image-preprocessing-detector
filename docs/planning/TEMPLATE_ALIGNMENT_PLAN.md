---
schema_type: planning
title: "Template Alignment Project Plan"
description: "Plan to align image_detection project with cookiecutter-python-template standards including modern tooling, CI/CD improvements, and template management"
tags:
  - planning
  - tooling
status: published
owner: core-maintainer
authors:
  - name: "Claude Code"
purpose: "Document the phased approach for aligning the image_detection project with cookiecutter-python-template standards."
component: "Development-Tools"
source: "Created during template alignment work on chore/update-project-templates branch"
---

> **Branch**: `chore/update-project-templates`
> **Created**: 2025-11-24
> **Status**: Draft - Pending User Approval

## Executive Summary

This plan outlines the work required to align the `image_detection` project with the `cookiecutter-python-template` standards. The goal is to modernize tooling, improve CI/CD, and optionally enable cruft-based template management.

## Gap Analysis Summary

| Area | Current State | Template Standard | Gap Severity |
|------|---------------|-------------------|--------------|
| **CLAUDE.md** | Project-focused (451 lines) | Template-integrated (675 lines) | MEDIUM |
| **.claude/ folder** | Minimal (1 file) | Full ecosystem (50+ files) | HIGH |
| **.github/ workflows** | Self-contained (2,530 LOC) | Modular delegation (841 LOC) | MEDIUM |
| **.standards/ folder** | MISSING | Baseline tracking (8 files) | HIGH |
| **pyproject.toml** | MyPy + Poetry | BasedPyright + semantic_release | MEDIUM |
| **Pre-commit config** | Individual tools | Qlty unified runner | MEDIUM |
| **REUSE.toml** | Apache-2.0 (excellent) | MIT (excellent) | NONE |
| **Missing configs** | 11 files absent | All present | MEDIUM |
| **.cruft.json** | Not cruft-managed | Full cruft management | HIGH |

## Recommendation: Phased Approach

Based on the analysis, I recommend a **three-phase approach** that allows incremental adoption:

- **Phase 1** (Required): Core template alignment (CLAUDE.md, .claude/, .github/)
- **Phase 2** (Recommended): Modern tooling migration (BasedPyright, Qlty, Docker)
- **Phase 3** (Optional): Full cruft integration

---

## Phase 1: Core Template Alignment (Required)

**Estimated Time**: 3-4 hours
**Priority**: HIGH

### 1.1 CLAUDE.md Updates

**Objective**: Align CLAUDE.md structure with template while preserving project-specific content.

**Changes Required**:

1. Add "Template Feedback Tracking" section
2. Add cross-references to `.claude/` modular structure
3. Update security-first development section
4. Add branch workflow requirements (already present but verify alignment)
5. Add cruft-managed files documentation

**Files**:

- [CLAUDE.md](../../CLAUDE.md)

**Source Reference**: `/home/byron/dev/template-sample/CLAUDE.md`

### 1.2 .claude/ Folder Implementation

**Objective**: Implement full Claude Code agent/command/skill ecosystem.

**Current State**:

```text
.claude/
└── settings.local.json    (only file present)
```text

**Target State** (from template):

```text
.claude/
├── README.md                    # Documentation for .claude usage
├── settings.local.json.example  # Example settings
├── agents/                      # Specialized agent definitions
│   ├── code-reviewer.md
│   ├── security-auditor.md
│   ├── test-engineer.md
│   └── merge-standards.md
├── commands/                    # Custom slash commands
│   ├── plan.md
│   ├── pr.md
│   ├── quality.md
│   ├── security.md
│   ├── testing.md
│   └── merge-standards.md
├── context/                     # Context files
│   ├── python-standards.md
│   └── testing-patterns.md
└── skills/                      # Reusable skill definitions
    ├── pr-prepare/
    ├── commit-prepare/
    ├── git/
    ├── project-planning/
    ├── quality/
    ├── security/
    └── testing/
```text

**Implementation Options**:

**Option A: Git Subtree (Recommended)**

```bash
# Add .claude as subtree from williaby/.claude repository
git subtree add --prefix .claude https://github.com/williaby/.claude.git main --squash
```

- Pros: Easy updates, shared maintenance, can contribute back
- Cons: Requires separate repo setup

**Option B: Direct Copy**

```bash
# Copy from template-sample
cp -r /home/byron/dev/template-sample/.claude/* /home/byron/dev/image_detection/.claude/
```

- Pros: Simple, no external dependencies
- Cons: Manual updates, no upstream sync

**Recommendation**: Option B for initial implementation, consider Option A for long-term maintenance.

**Files to Copy** (from template-sample):

- `.claude/README.md`
- `.claude/settings.local.json.example`
- `.claude/agents/*` (4 files)
- `.claude/commands/*` (6 files)
- `.claude/context/*` (2 files)
- `.claude/skills/*` (7 directories with subdirectories)

### 1.3 .github/ Folder Updates

**Objective**: Add missing workflows and align with template patterns.

**Missing Workflows**:

1. `sonarcloud.yml` - SonarCloud integration
2. `validate-cruft.yml` - Template validation (skip if not using cruft)

**Workflow Updates**:

1. Update `ci.yml` to support org workflow delegation (optional)
2. Add SonarCloud integration to existing security workflows
3. Ensure workflow badge URLs are correct

**Files to Add**:

- `.github/workflows/sonarcloud.yml`
- `.github/workflows/validate-cruft.yml` (if using cruft)

**Files to Update**:

- `.github/workflows/ci.yml` (add SonarCloud job)
- `.github/PULL_REQUEST_TEMPLATE.md` (verify alignment)
- `.github/copilot-instructions.md` (add if missing)

**Source Reference**: `/home/byron/dev/template-sample/.github/`

### 1.4 template_feedback/ Directory

**Objective**: Establish template feedback tracking system.

**Implementation**:

```bash
mkdir -p template_feedback
```

Create initial file: `template_feedback/11242025_template_feedback.md`

**Content Template**:

```markdown
# Template Feedback - November 24, 2025

## Summary
Initial template alignment for image_detection project.

## Issues Found

### Category: Configuration
- **Severity**: Medium
- **Description**: [Issue description]
- **Suggested Fix**: [Proposed solution]

## Improvements Applied
- [List of changes made]

## Pending Items
- [Items deferred to future updates]
```

---

## Phase 2: Modern Tooling Migration (Recommended)

**Estimated Time**: 4-5 hours
**Priority**: MEDIUM

### 2.1 BasedPyright Migration

**Objective**: Replace MyPy with BasedPyright for faster, stricter type checking.

**Current Configuration** (MyPy):

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
disallow_untyped_defs = true
```

**Target Configuration** (BasedPyright):

```toml
[tool.basedpyright]
pythonVersion = "3.12"
pythonPlatform = "Linux"
typeCheckingMode = "strict"
analyzeUnannotatedFunctions = true
strictParameterNoneValue = true
strictListInference = true
strictDictionaryInference = true
strictSetInference = true
reportMissingTypeStubs = "warning"
reportUnknownMemberType = "warning"
```

**Migration Steps**:

1. Add `basedpyright` to dev dependencies
2. Add `[tool.basedpyright]` section to pyproject.toml
3. Update pre-commit to use basedpyright instead of mypy
4. Run initial type check and fix any new errors
5. Remove or deprecate mypy configuration (keep for reference period)

**Files to Update**:

- `pyproject.toml`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`

### 2.2 Qlty Integration (Optional)

**Objective**: Add Qlty for unified quality checking.

**Configuration**:

```bash
mkdir -p .qlty
```

**Files to Add**:

- `.qlty/qlty.toml`
- `.qlty/configs/` (tool-specific configs)

**Note**: Qlty integration is optional. The project already has comprehensive individual tool configs.

### 2.3 Docker Configuration

**Objective**: Add containerization support for deployment.

**Files to Add**:

- `Dockerfile` (multi-stage production build)
- `docker-compose.yml` (development environment)
- `docker-compose.prod.yml` (production environment)
- `.dockerignore`

**Dockerfile Template** (from template-sample):

- Multi-stage build for smaller images
- Non-root user (appuser:1000)
- Health checks enabled
- OCI metadata labels

### 2.4 Additional Config Files

**Files to Add**:

- `.coderabbit.yaml` - AI code review configuration
- `.semgrep.yml` - Security patterns
- `sonar-project.properties` - SonarCloud configuration
- `.markdownlint.json` - Markdown linting rules
- `.yamllint` - YAML linting configuration
- `.prettierrc` - Code formatting
- `.shellcheckrc` - Shell script linting
- `.mutmut_config` - Mutation testing config

### 2.5 Semantic Release Setup

**Objective**: Enable automated versioning based on conventional commits.

**Add to pyproject.toml**:

```toml
[tool.semantic_release]
version_variable = "src/image_preprocessing_detector/__init__.py:__version__"
version_toml = ["pyproject.toml:project.version"]
branch = "main"
upload_to_pypi = false
upload_to_release = true
build_command = "poetry build"

[tool.semantic_release.branches.main]
match = "main"
prerelease = false

[tool.semantic_release.branches.develop]
match = "develop"
prerelease = true
prerelease_token = "dev"

[tool.semantic_release.commit_parser_options]
allowed_tags = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore"]
minor_tags = ["feat"]
patch_tags = ["fix", "perf"]
```

---

## Phase 3: Full Cruft Integration (Optional)

**Estimated Time**: 2-3 hours
**Priority**: LOW (unless template synchronization is important)

### 3.1 Cruft Initialization

**Objective**: Convert project to cruft-managed template.

**Decision Point**: Is automatic template synchronization important for this project?

**Pros of Cruft**:

- Automatic updates when template changes
- Validation workflow ensures compliance
- Baseline tracking in `.standards/`
- Structured template feedback system

**Cons of Cruft**:

- Overhead for specialized ML project
- May conflict with project-specific customizations
- Requires maintaining compatibility with template

**If YES - Proceed with Cruft**:

```bash
# Link existing project to template
cruft link /home/byron/dev/cookiecutter-python-template

# This creates .cruft.json with current template reference
```

**If NO - Skip Cruft**:

- Manually track template changes
- No `.cruft.json` or `validate-cruft.yml`
- Remove `.standards/` from plan

### 3.2 .standards/ Baseline Implementation

**Only if using Cruft**

**Files to Add**:

```text
.standards/
├── README.md
├── CLAUDE.baseline.md
├── README.baseline.md
├── REUSE.baseline.toml
├── env.example.baseline
├── mkdocs.yml.baseline
├── pyproject.toml.baseline
└── template_feedback.baseline.md
```text

**Purpose**: Track template baselines for diff comparison during updates.

### 3.3 Cruft Validation Workflow

**Only if using Cruft**

**Add**: `.github/workflows/validate-cruft.yml`

---

## Implementation Checklist

### Phase 1 Tasks (Core Alignment)

- [ ] **1.1** Update CLAUDE.md
  - [ ] Add template feedback tracking section
  - [ ] Add .claude/ references
  - [ ] Verify branch workflow section
  - [ ] Document cruft-managed files (if applicable)

- [ ] **1.2** Implement .claude/ folder
  - [ ] Copy README.md
  - [ ] Copy settings.local.json.example
  - [ ] Copy agents/ directory (4 files)
  - [ ] Copy commands/ directory (6 files)
  - [ ] Copy context/ directory (2 files)
  - [ ] Copy skills/ directory (7 subdirectories)
  - [ ] Update paths/references for image_detection

- [ ] **1.3** Update .github/ folder
  - [ ] Add sonarcloud.yml workflow
  - [ ] Add copilot-instructions.md (if missing)
  - [ ] Verify PULL_REQUEST_TEMPLATE.md alignment
  - [ ] Update ci.yml for SonarCloud integration

- [ ] **1.4** Create template_feedback/ directory
  - [ ] Create initial feedback file

### Phase 2 Tasks (Modern Tooling)

- [ ] **2.1** BasedPyright migration
  - [ ] Add basedpyright to dependencies
  - [ ] Add [tool.basedpyright] config
  - [ ] Update pre-commit hooks
  - [ ] Fix type errors
  - [ ] Update CI workflow

- [ ] **2.2** Qlty integration (optional)
  - [ ] Create .qlty/ directory
  - [ ] Add qlty.toml configuration

- [ ] **2.3** Docker configuration
  - [ ] Add Dockerfile
  - [ ] Add docker-compose.yml
  - [ ] Add docker-compose.prod.yml
  - [ ] Add .dockerignore

- [ ] **2.4** Additional config files
  - [ ] Add .coderabbit.yaml
  - [ ] Add .semgrep.yml
  - [ ] Add sonar-project.properties
  - [ ] Add .markdownlint.json
  - [ ] Add .yamllint
  - [ ] Add .prettierrc
  - [ ] Add .shellcheckrc

- [ ] **2.5** Semantic release setup
  - [ ] Add semantic_release config to pyproject.toml
  - [ ] Update release.yml workflow

### Phase 3 Tasks (Cruft - Optional)

- [ ] **3.1** Cruft initialization
  - [ ] Run `cruft link`
  - [ ] Verify .cruft.json created correctly

- [ ] **3.2** .standards/ implementation
  - [ ] Create baseline files

- [ ] **3.3** Cruft validation workflow
  - [ ] Add validate-cruft.yml

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Type errors from BasedPyright | HIGH | LOW | Gradual migration, warning mode first |
| Breaking changes in .claude/ | LOW | MEDIUM | Test commands before commit |
| CI workflow failures | MEDIUM | MEDIUM | Test in branch before merge |
| Cruft conflicts | MEDIUM | HIGH | Skip Phase 3 if conflicts arise |
| Loss of project-specific customizations | LOW | HIGH | Document all customizations first |

---

## Success Criteria

### Phase 1 Complete When

- [ ] CLAUDE.md includes template feedback section
- [ ] .claude/ folder has all agents, commands, and skills
- [ ] .github/ workflows include SonarCloud
- [ ] template_feedback/ directory exists with initial file
- [ ] All existing tests still pass
- [ ] Pre-commit hooks pass

### Phase 2 Complete When

- [ ] BasedPyright configured and passing
- [ ] Docker builds successfully
- [ ] All config files present and valid
- [ ] CI pipeline passes with new tooling
- [ ] Semantic release configured

### Phase 3 Complete When (if implemented)

- [ ] .cruft.json links to template
- [ ] .standards/ baseline files present
- [ ] validate-cruft.yml workflow passes
- [ ] `cruft check` reports no drift

---

## Appendix: File Sources

All template files sourced from:

- **Template Repository**: `/home/byron/dev/cookiecutter-python-template/`
- **Rendered Sample**: `/home/byron/dev/template-sample/`

## Appendix: Commands Reference

```bash
# Check cruft status (if using cruft)
cruft check

# Update from template (if using cruft)
cruft update

# Run basedpyright
uv run basedpyright src/

# Run qlty (if installed)
qlty check

# Build docker image
docker build -t image-detection .

# Run all pre-commit hooks
uv run pre-commit run --all-files
```
