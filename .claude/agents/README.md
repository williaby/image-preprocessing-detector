---
name: agents-architecture
description: Context-optimized agent system documentation and development guidelines
---

# Claude Code Agents Architecture

> **Context-Optimized Agent System** - Specialized agents with shared context for maximum effectiveness and minimal token usage.

## Agent Development Philosophy

### Core Principles

**Specialization with Efficiency**: Each agent maintains deep expertise in their domain while leveraging shared context to minimize redundancy and token usage.

**Layered Architecture**:

- **Core Agents**: Universal specialized expertise (code review, testing, security, AI engineering)
- **Contextual Agents**: Project or domain-specific capabilities (knowledge management, system integration)
- **Shared Context**: Common patterns, standards, and architectures referenced by all agents

### Token Optimization Strategy

**Before**: 12 agents × 300 lines avg = ~3,600 lines of context (~10% context window)
**Target**: 10 agents × 75 lines avg + shared context = ~1,200 lines (~3% context window)

## Agent Categories

### Core Specialized Agents (6)

Essential expertise that applies across all projects:

- **`code-reviewer`** - Code quality, standards compliance, best practices
- **`test-engineer`** - Test strategy, test generation, quality assurance
- **`security-auditor`** - Vulnerability detection, security analysis, compliance
- **`ai-engineer`** - LLM applications, RAG systems, prompt pipelines
- **`prompt-engineer`** - Prompt optimization, framework implementation
- **`documentation-writer`** - Technical writing, information architecture

### Contextual Agents (4)

Project or domain-specific capabilities:

- **`knowledge-manager`** - Knowledge base ingestion, semantic search, content curation
- **`mcp-integration-agent`** - MCP protocol communication, multi-agent orchestration
- **`journey-orchestrator`** - Multi-level user experience management
- **`modularization-assistant`** - System decomposition, architectural refactoring

### Merged/Eliminated

- **`test-automator`** → Merged into `test-engineer` (eliminates redundancy)

## Agent Structure Standards

### Optimal Agent Template

```yaml
---
name: agent-name
description: Single sentence describing core capability and when to use
model: opus|sonnet|haiku  # Based on complexity needs
tools: [Essential, Tools, Only]
context_refs:  # NEW: Reference shared context instead of repeating
  - /context/shared-architecture.md
  - /context/development-standards.md
---

# Agent Name

[2-3 sentence agent purpose and expertise area]

## Core Responsibilities
- [3-5 bullet points of primary responsibilities]

## Specialized Approach
[Agent-specific methodology - 2-3 paragraphs max]

## Integration Points
[Key files/systems this agent works with - bullet list]

## Output Standards
[Expected deliverables and quality criteria - bullet list]

---
*Use this agent for: [specific trigger conditions]*
```

### Context Reference System

**Shared Context Files** (`/context/` directory):

- **`shared-architecture.md`** - Common system architectures and patterns
- **`development-standards.md`** - Universal coding standards and practices
- **`integration-patterns.md`** - Common integration and API patterns
- **`project-context.md`** - Current project-specific context when needed

**Size Limits**:

- **Agent Definition**: 50-75 lines max
- **Shared Context**: 100-150 lines per file max
- **Total Context per Agent**: ~200 lines (agent + referenced context)

## Agent Specialization Guidelines

### When to Create a New Agent

✅ **Create** when:

- Domain requires deep specialized knowledge
- Distinct tool requirements or workflows
- Clear, non-overlapping responsibility boundary
- Used frequently enough to justify context cost

❌ **Don't Create** when:

- Functionality can be handled by existing agent with context
- Overlaps significantly with existing agents
- Used rarely (better as general capability)
- Would create circular dependencies

### Agent Interaction Patterns

**Hierarchical**: Some agents can delegate to others

- `ai-engineer` can invoke `prompt-engineer` for optimization
- `code-reviewer` can invoke `security-auditor` for security analysis

**Collaborative**: Agents work together on complex tasks

- `test-engineer` + `security-auditor` for security testing
- `documentation-writer` + `code-reviewer` for code documentation

**Sequential**: Agents form processing pipelines

- `knowledge-manager` → `ai-engineer` → `prompt-engineer` for RAG optimization

## Development Process

### 1. Agent Analysis Phase

```bash
# Assess current context usage
wc -l ~/.claude/agents/*.md

# Identify overlapping content
grep -r "similar patterns" ~/.claude/agents/

# Measure context impact
claude /context  # Check current context window usage
```

### 2. Optimization Phase

**Step 1**: Extract shared context

- Create `/context/shared-*.md` files
- Move common content from agent files

**Step 2**: Compress agent definitions

- Remove verbose examples → reference pattern files
- Eliminate redundant architecture descriptions
- Consolidate integration points

**Step 3**: Implement reference system

- Update agent YAML frontmatter with `context_refs`
- Test agent functionality with reduced context

### 3. Validation Phase

**Functionality Test**: Ensure agents maintain full capability
**Context Measurement**: Verify context reduction targets met
**Performance Test**: Confirm no degradation in agent effectiveness

## Quality Standards

### Agent Definition Quality

- **Clarity**: Purpose and capabilities immediately clear
- **Specificity**: Precise trigger conditions and use cases
- **Completeness**: All necessary context referenced or included
- **Efficiency**: No redundant or unnecessary content

### Documentation Standards

- **Consistent formatting** across all agent files
- **Clear separation** between agent-specific and shared content
- **Proper referencing** of shared context files
- **Regular maintenance** and updates

### Testing Requirements

- **Agent capability tests**: Verify each agent can perform core functions
- **Integration tests**: Ensure agents work together effectively
- **Context efficiency tests**: Measure and optimize context usage
- **Performance benchmarks**: Track agent response quality over time

## Context Budget Management

### Current Allocation

- **Total Context Budget**: ~8K tokens (typical Claude context)
- **Agent Context Target**: ~240 tokens (3% of budget)
- **Shared Context**: ~160 tokens (2% of budget)
- **Available for Task**: ~7.6K tokens (95% of budget)

### Monitoring and Optimization

```bash
# Monitor context usage
echo "Current agent context usage:"
wc -l ~/.claude/agents/*.md | tail -1

# Target context size
echo "Target: < 1200 lines total"

# Shared context size
wc -l ~/.claude/context/*.md 2>/dev/null || echo "Shared context not yet implemented"
```

### Optimization Techniques

**Content Compression**:

- Remove redundant examples
- Use bullet points vs. paragraphs
- Reference external resources vs. inline content

**Smart References**:

- Link to specific sections in shared files
- Use conditional context loading
- Implement context inheritance patterns

**Regular Maintenance**:

- Monthly context audits
- Remove obsolete content
- Consolidate overlapping patterns

## Usage Examples

### Invoking Specialized Agents

```bash
# Direct agent invocation
claude @code-reviewer "review the authentication module"
claude @security-auditor "analyze the API endpoints for vulnerabilities"

# Context-aware invocation (agents auto-selected based on task)
claude "implement secure user registration with comprehensive tests"
# → Triggers: ai-engineer, security-auditor, test-engineer collaboration
```

### Agent Development Workflow

```bash
# 1. Create new agent (only when justified)
cp ~/.claude/agents/template-agent.md ~/.claude/agents/new-agent.md

# 2. Update shared context if needed
vim ~/.claude/context/shared-architecture.md

# 3. Test agent functionality
claude @new-agent "test task to verify agent capabilities"

# 4. Measure context impact
wc -l ~/.claude/agents/*.md ~/.claude/context/*.md
```
