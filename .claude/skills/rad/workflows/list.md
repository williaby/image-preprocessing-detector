---
argument-hint: [directory]
description: Generate comprehensive inventory of all assumption tags in project for review, cleanup, and prioritization.
allowed-tools: Bash(find:*, grep:*), Grep
---

# Assumption Listing Workflow

Generate a comprehensive inventory of all assumption tags in the project to help with RAD workflow management.

## Task Overview

Scan the project (or specified directory) for all assumption tags and provide organized summary for:

- Development workflow planning
- Technical debt assessment
- Code review preparation
- Assumption verification prioritization

## Arguments

- `directory`: Directory to scan (defaults to current directory if not specified)

## Implementation Steps

### 1. Determine Scan Scope

```bash
SCAN_DIR=${ARGUMENTS:-"."}
echo "Scanning directory: $SCAN_DIR"
```

### 2. Find All Assumption Tags

Use Grep tool to find all assumption patterns:

- `#CRITICAL:` - Production blockers requiring immediate attention
- `#ASSUME:` - Standard assumptions needing verification
- `#EDGE:` - Edge cases for future consideration

Search in relevant source file types:

- `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.rs`, `.java`, `.cpp`, `.c`
- Exclude: `node_modules`, `.git`, `__pycache__`, `venv`, `build`, `dist`

### 3. Parse and Categorize Results

For each found assumption, extract:

- **File path** and **line number**
- **Tag type** (CRITICAL/ASSUME/EDGE)
- **Category** (payment/security/timing/state/etc.)
- **Description** text
- **Verification status** (if #VERIFY: comment exists or [VERIFIED] marker)

### 4. Generate Inventory Report

Create comprehensive report with:

- **Executive Summary**: Total counts by risk level
- **Risk Distribution**: Breakdown by category and file
- **Verification Status**: Which assumptions have been verified
- **Priority Recommendations**: Suggested verification order
- **File Hotspots**: Files with highest assumption density

## Report Format

```markdown
# Project Assumption Inventory

Generated: [timestamp]
Scope: [directory]

## Executive Summary
- **Total Assumptions**: [total] across [file_count] files
- **Critical**: [critical_count] (require immediate verification)
- **Standard**: [standard_count] (should verify before PR)
- **Edge Cases**: [edge_count] (can defer to backlog)

## Risk Distribution

### Critical Assumptions (🚨 High Priority)
| File | Line | Category | Description | Status |
|------|------|----------|-------------|--------|
| auth.py | 45 | security | Auth token assumed valid | ❌ Unverified |
| payment.js | 123 | payment | Transaction sync assumption | ✅ Verified 2025-01-30 |

### Standard Assumptions (⚠️ Medium Priority)
[Similar table format]

### Edge Cases (💡 Low Priority)
[Similar table format]

## File Hotspots
Files with highest assumption density:
1. **src/auth/service.py**: 8 assumptions (5 critical)
2. **frontend/payment.js**: 6 assumptions (3 critical)
3. **api/user.py**: 4 assumptions (1 critical)

## Verification Recommendations

### Immediate Action Required
- [ ] Verify critical payment assumptions in payment.js:123-145
- [ ] Review security assumptions in auth/service.py:45-67
- [ ] Address concurrency issues in async/worker.py:89

### Before Next Release
- [ ] Standard state management assumptions (15 items)
- [ ] API error handling assumptions (8 items)
- [ ] Form validation assumptions (12 items)

### Technical Debt Backlog
- [ ] Browser compatibility edge cases (23 items)
- [ ] Performance optimization assumptions (11 items)
- [ ] Large dataset handling assumptions (7 items)

## Next Steps

### For Immediate Development
```bash
# Verify critical assumptions only
/rad/verify --strategy critical-only

# Full verification of changed files
/rad/verify --scope changed-files
```

### For Code Review Process

1. **Pre-PR**: Ensure no unverified critical assumptions
2. **Review**: Check assumption verification status
3. **Merge**: All blocking assumptions resolved

### For Technical Debt

- Schedule verification sprints for standard assumptions
- Prioritize by file hotspot analysis
- Track verification progress over time
```

## Implementation Notes

### Verification Status Detection

Look for verified markers:
- `#CRITICAL: [VERIFIED-YYYY-MM-DD]` - Verified assumption
- `#ASSUME: [VERIFIED-YYYY-MM-DD]` - Verified assumption
- No marker = Unverified

### Category Extraction

Extract category from assumption text:
```bash
# Example patterns:
# #CRITICAL: payment: Transaction completion assumed
# #ASSUME: state: React state update timing
# #EDGE: browser: localStorage availability
```

### File Density Calculation

```bash
# Assumptions per file = (assumption_count / file_size_lines) * 100
# Highlight files with >2% assumption density
```

## Error Handling

If no assumptions found:

```markdown
# Project Assumption Inventory

## Summary
No assumption tags found in project.

## Getting Started with RAD
Consider adding assumption tags during development:

```javascript
// #CRITICAL: payment: Assuming payment gateway responds within 5s
// #VERIFY: Add timeout and retry logic

// #ASSUME: state: User state persists across page refreshes
// #VERIFY: Add localStorage backup or session validation

// #EDGE: browser: Clipboard API available in all browsers
// #VERIFY: Add fallback for unsupported browsers
```

## Resources

- RAD Methodology: See rad/context/methodology.md
- Verification Command: /rad/verify
- Tagging Standards: Global CLAUDE.md > Response-Aware Development
```

---

*Migrated from list-assumptions command.*
