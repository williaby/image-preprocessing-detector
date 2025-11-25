# User-Level Slash Commands Setup

This directory contains custom slash commands that extend Claude Code's functionality with Response-Aware Development (RAD) workflows.

## Command Structure

Commands are implemented as `.md` files following Claude Code's standard structure:

- **File Location**: `$HOME/.claude/commands/`
- **File Format**: Markdown with YAML frontmatter
- **Naming**: Filename becomes command name (e.g., `verify-assumptions-smart.md` → `/verify-assumptions-smart`)

## Available Commands

### `/verify-assumptions-smart`

Intelligent tiered verification of code assumptions using multiple AI models based on risk level.

**Basic Usage:**

```bash
/verify-assumptions-smart
```

**Advanced Usage:**

```bash
# Critical assumptions only (for hotfixes)
/verify-assumptions-smart --strategy=critical-only --budget=free-only

# Full analysis with explanations
/verify-assumptions-smart --scope=all-files --explain --budget=premium

# Auto-apply non-critical fixes
/verify-assumptions-smart --apply-fixes=auto
```

**Parameters:**

- `--strategy=`: `tiered` (default), `uniform`, `critical-only`
- `--budget=`: `premium`, `balanced` (default), `free-only`
- `--scope=`: `current-file`, `changed-files` (default), `all-files`
- `--explain`: Show model selection reasoning (flag, no value)
- `--apply-fixes=`: `auto`, `review` (default), `none`

### `/list-assumptions`

List all assumption tags in the project for review and cleanup.

```bash
/list-assumptions
/list-assumptions src/
```

**Parameters:**

- `directory`: Optional directory to scan (defaults to current directory)

## Response-Aware Development (RAD) Workflow

### 1. Tag Assumptions During Development

```javascript
// #CRITICAL: payment: Transaction completion assumed synchronous
// #VERIFY: Add completion callback and timeout handling
processPayment(amount);
updateUserBalance(amount);

// #ASSUME: state: React state update completes before navigation
// #VERIFY: Use callback or useEffect dependency
setUser(newUser);
navigate('/profile');

// #EDGE: browser: Assumes localStorage is available
// #VERIFY: Add fallback for private browsing mode
localStorage.setItem('token', token);
```

### 2. Verify Before Commit

```bash
# Quick verification of critical assumptions
/verify-assumptions-smart --strategy critical-only

# Full tiered verification
/verify-assumptions-smart
```

### 3. Apply Fixes

```bash
# Review and apply fixes manually
git diff  # See proposed changes
git add -p  # Selectively stage fixes

# Or auto-apply non-critical fixes
/verify-assumptions-smart --apply-fixes auto
```

### 4. Mark Verified Assumptions

```javascript
// #CRITICAL: [VERIFIED-2025-01-31] payment: Added timeout and retry logic
// #VERIFY: Timeout after 30s, retry 3 times with exponential backoff
```

## Model Selection Logic

The system automatically routes assumptions to appropriate models:

### Critical Assumptions → Premium Models

- **Payment/Financial**: OpenAI O3-Mini or Gemini 2.5 Pro
- **Security/Auth**: Gemini 2.5 Pro (excellent security reasoning)
- **Concurrency/Race Conditions**: DeepSeek-R1 or Gemini 2.5 Pro
- **Database Transactions**: DeepSeek-R1 (complex state reasoning)

### Standard Assumptions → Free Models via Dynamic Selection

- **State Updates**: Qwen-Coder (React/Vue patterns)
- **API Calls**: DeepSeek-Chat (async patterns)
- **Validation**: Gemini Flash (pattern matching)
- **Caching**: Llama 3.3 70B (distributed systems)

### Edge Cases → Fast Free Models

- **Batch Processing**: Gemini Flash Lite
- **Documentation**: Any fast free model
- **Minor Optimizations**: Gemini Flash Lite

## Integration with Pre-Commit

Add assumption verification to your development workflow:

**Option 1: Pre-commit Hook (Advanced)**

```yaml
# In .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-critical-assumptions
        name: Check for Unverified Critical Assumptions
        entry: bash
        args: ['-c', 'if grep -r "#CRITICAL:" --include="*.py" --include="*.js" src/ | grep -v "VERIFIED"; then echo "Unverified critical assumptions found. Run: /verify-assumptions-smart --strategy=critical-only"; exit 1; fi']
        language: system
        pass_filenames: false
```

**Option 2: Development Checklist (Recommended)**

```markdown
## Pre-Commit Checklist
- [ ] Code formatted and linted
- [ ] Tests pass
- [ ] **Critical assumptions verified**: `/verify-assumptions-smart --critical-only`
- [ ] Security scans pass
```

## Evaluation and Metrics

Track effectiveness after 30-60 days:

### Quantitative Metrics

- Assumptions detected per 1000 lines of code
- Production incidents traced to unverified assumptions
- Cost per verification run
- Fix application rate

### Qualitative Assessment

- Developer feedback on workflow integration
- Quality of generated fixes
- False positive rate
- Model selection accuracy

## Future Enhancements

### Phase 2: Machine Learning Integration

- Risk scoring based on historical data
- Pattern recognition for common failure modes
- Cross-project assumption sharing

### Phase 3: IDE Integration

- Real-time assumption highlighting
- Inline verification suggestions
- Team analytics dashboard

## Troubleshooting

### Command Not Found

Ensure Claude Code is loading slash commands:

1. Check file permissions on `$HOME/.claude/commands/*.md` files
2. Verify commands are in correct Markdown format with YAML frontmatter
3. Restart Claude Code session to reload command definitions

### Model Selection Issues

- For free-only mode: Relies on DeepSeek-R1, Gemini Flash, Qwen-Coder
- For premium mode: Uses O3-Mini, Gemini 2.5 Pro
- Check Zen MCP Server connectivity for dynamic selection

### Git Integration Problems

- Ensure working directory is a git repository
- Check git status and permissions
- Use `--scope all-files` if git commands fail

## Cost Optimization

### Free-Only Strategy

- Uses only free models (DeepSeek-R1, Gemini Flash, Qwen-Coder)
- Batch processes similar assumptions
- Focuses on pattern matching rather than deep reasoning

### Balanced Strategy (Recommended)

- Premium models only for critical security/payment code
- Free models for 80-90% of assumptions
- Estimated cost: $0.001-$0.01 per verification run

### Premium Strategy

- Uses best available models for all assumptions
- Maximum accuracy for critical systems
- Higher cost but comprehensive coverage

---

*Last Updated: 2025-01-31*
*See `/docs/response-aware-development.md` for complete methodology*
