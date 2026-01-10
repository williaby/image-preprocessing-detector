---
schema_type: common
title: "Level 2 Documentation Template ('Level 2.5' Standard)"
description: "Template and guidelines for creating comprehensive Level 2 workstream
  documentation"
tags:
- architecture
- documentation
- template
- standards
- level_2
status: draft
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: Documentation for Level 2 Documentation Template ('Level 2.5' 
  Standard).
---

This template defines the "Level 2.5" documentation standard - a comprehensive Level 2 format that provides sufficient implementation context to eliminate the need for Level 3 documentation in most cases.

**Purpose**: Balance architectural clarity with implementation detail
**Target Audience**: Engineers, architects, new team members
**Scope**: Workstream-level documentation (between project-level and module-level)

---

## What is "Level 2.5"?

**"Level 2.5"** is a documentation standard that combines:

- **Level 2 Architecture**: System components, data flows, integration points
- **Level 3 Implementation Details**: Code examples, algorithms, performance metrics

**Benefits**:

- **Reduces Documentation Burden**: Eliminates need for separate Level 3 docs in 60-70% of cases
- **Provides Implementation Context**: Developers understand system without deep code diving
- **Maintains Architecture Focus**: Doesn't become implementation documentation

**When to Use Level 2.5**: Complex workstreams (>1,000 LOC) with multiple components and cross-workstream dependencies

**Examples of Level 2.5 Docs**:

- [Production Runtime](diagrams/level-2/production-runtime/index.md) - 670+ lines
- [Model Training](diagrams/level-2/model-training/index.md) - 755+ lines
- [Monitoring & Drift Detection](diagrams/level-2/monitoring-drift/index.md) - 890 lines
- [Model Arena](diagrams/level-2/model-arena/index.md) - 810 lines

---

## Template Structure

### Required Frontmatter

```yaml
---
schema_type: common
title: "Level 2: [Workstream Name]"
description: "Brief one-sentence description"
tags: [architecture, diagrams, plantuml, level-2, [workstream-tag]]
status: published  # or draft, deprecated
owner: "core-maintainer"
authors:
  - name: "[Your Name]"
purpose: "Document the [workstream name] including [key aspects]"
last_updated: "YYYY-MM-DD"
---
```

---

### Section 1: Title and Overview (Required)

**Template**:

```markdown
# Level 2: [Workstream Name]

This level provides detailed documentation for the [Workstream Name] - [brief description of purpose].

**Status**: [Active/Draft/In Progress]
**Lines of Code**: ~X,XXX across [list key components]

**Purpose**: [1-2 sentences explaining what this workstream does]

**Key Innovation**: [Optional - what makes this workstream unique]
```

**Example** (from Production Runtime):

```markdown
# Level 2: Production Runtime

This level provides detailed documentation for the Production Runtime workstream - the live document processing pipeline.

**Status**: Active
**Lines of Code**: ~15,000 across ingestion, detection, correction, routing

**Purpose**: Process incoming documents through IQA analysis, quality correction, and routing recommendation generation for downstream OCR orchestration.

**Key Innovation**: Text detection gate that routes documents to specialized processing paths, avoiding expensive layout inference for pure images.
```

---

### Section 2: Technical Diagrams (Required)

**Template**:

```markdown
## Technical Diagrams

### [Diagram 1 Name]

[Brief description of what the diagram shows]

![Diagram Alt Text](diagram-filename.svg)

*PlantUML source: [`diagram-filename.puml`](diagram-filename.puml)*

---

### [Diagram 2 Name]

[Brief description]

![Diagram Alt Text](diagram-filename.svg)

---
```

**Guidelines**:

- Include 2-5 diagrams maximum (avoid overwhelming with too many)
- Always reference PlantUML source for traceability
- Use descriptive alt text for accessibility

---

### Section 3: Key Components (Required)

**Template**:

```markdown
## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| [Component 1] | `src/path/to/file.py` | [Brief purpose] |
| [Component 2] | `src/path/to/module/` | [Brief purpose] |
| [Component 3] | `src/path/to/another.py` | [Brief purpose] |

**Component Details** (optional - add if complex):

### Component 1: [Name]

**Responsibilities**:
- [Responsibility 1]
- [Responsibility 2]

**Key Classes/Functions**:
- `ClassName`: [Purpose]
- `function_name()`: [Purpose]

**Lines of Code**: ~XXX

---
```

**Example** (from Production Runtime):

```markdown
## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| Device Orchestrator | `src/utils/device_orchestrator.py` | Device selection and fallback |
| Text Gate | `src/detection/text_gate.py` | Fast text presence detection |
| ML IQA | `src/detection/iqa_ml.py` | Teacher-student ResNet models |
```

---

### Section 4: Detailed Workflows (CRITICAL for Level 2.5)

**Template**:

```markdown
## [Workflow/Process Name]

### [Sub-section Title]

**[Aspect Being Described]**:

[Narrative explanation with technical details]

**[Configuration/Algorithm/Implementation]**:

```[language]
# Code example showing implementation
[actual working code snippet]
```

**[Performance/Metrics/Results]**:

| Metric | Value | Notes |
|--------|-------|-------|
| [Metric 1] | [Value] | [Context] |

```

**Guidelines**:
- **Include Code Examples**: Show actual implementation patterns (Python, YAML, JSON)
- **Explain Algorithms**: Decision trees, state machines, selection logic
- **Provide Context**: Why this approach? What are the tradeoffs?
- **Quantify Everything**: Latency, throughput, cost, accuracy

**Example** (from Model Training - Distillation Loss Function):

```markdown
### Distillation Loss Function

**Composite Loss** (balances teacher knowledge and ground truth):

```python
def distillation_loss(student_logits, teacher_logits, ground_truth, alpha=0.7, temperature=3.0):
    """Knowledge distillation loss with temperature scaling."""
    # Soft targets from teacher
    teacher_soft = F.softmax(teacher_logits / temperature, dim=1)
    student_soft = F.log_softmax(student_logits / temperature, dim=1)

    # KL divergence between distributions
    distillation_loss = F.kl_div(student_soft, teacher_soft, reduction='batchmean') * (temperature ** 2)

    # MSE between student output and ground truth
    hard_loss = F.mse_loss(torch.sigmoid(student_logits), ground_truth)

    return alpha * distillation_loss + (1 - alpha) * hard_loss
```

**Hyperparameters**:

- **α (alpha)**: 0.7 (70% teacher, 30% ground truth)
- **T (temperature)**: 3.0 (softer distributions)

**Training Results**:

- Teacher: val_loss = 0.27
- Student: val_loss = 0.14 (48% lower)

```

---

### Section 5: Workstream Dependencies (MANDATORY)

**Template**:

```markdown
## Workstream Dependencies

### Upstream Dependencies

| Workstream | Consumed Artifacts | Purpose |
|------------|-------------------|---------|
| **WS#: [Name]** | [Artifact type] | [How it's used] |
| **[External Service]** | [Data/API] | [Purpose] |

### Downstream Consumers

| Workstream | Provided Artifacts | Purpose |
|------------|-------------------|---------|
| **WS#: [Name]** | [Output type] | [How they use it] |
| **[External Project]** | [Output type] | [Integration point] |

### External Dependencies

| Service/Tool | Purpose | Configuration | Fallback |
|--------------|---------|---------------|----------|
| **[Service Name]** | [Why needed] | [Key config] | [What happens if unavailable] |
```

**Guidelines**:

- **Be Explicit**: Don't assume readers know the dependency graph
- **Include External Services**: Modal, GCS, databases, APIs
- **Show Integration Points**: How data flows in and out
- **Document Fallbacks**: What happens when dependencies are unavailable

**Example** (from Production Runtime):

```markdown
### Upstream Dependencies

| Workstream | Consumed Artifacts | Purpose |
|------------|-------------------|---------|
| **None** | N/A | Production Runtime is the entry point for live processing |

**Note**: Consumes trained models from Workstream 2:
- Student model (ResNet-18): Production inference
- Teacher model (ResNet-50): Selective escalation

### Downstream Consumers

| Workstream | Provided Artifacts | Purpose |
|------------|-------------------|---------|
| **Project B (Unify)** | `DocumentMetadata.json`, corrected images | OCR orchestration input |
| **Workstream 7 (Monitoring)** | Predictions, latency metrics | Drift detection, active learning |

### External Dependencies

| Service/Tool | Purpose | Configuration | Fallback |
|--------------|---------|---------------|----------|
| **Modal GPU** | Serverless GPU inference | T4/A10, $30/month budget | CPU inference |
| **Local GPU** | Primary inference device | CUDA 12.1+, 4GB+ VRAM | Modal or CPU |
```

---

### Section 6: Performance Characteristics (Recommended)

**Template**:

```markdown
## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Latency (GPU)** | [X]ms/[unit] | [Context] |
| **Latency (CPU)** | [X]ms/[unit] | [Fallback mode] |
| **Throughput** | [X] [units]/sec | [Conditions] |
| **Cost** | $[X]/[unit] | [Service used] |
| **Memory** | [X] GB | [Peak usage] |

**Optimization Strategies**:
- [Strategy 1]: [Description and benefit]
- [Strategy 2]: [Description and benefit]
```

**Example** (from Production Runtime - Device Performance):

```markdown
| Device | Latency (Student) | Latency (Teacher) | Throughput | Cost/Page |
|--------|------------------|-------------------|------------|-----------|
| **Local GPU (T4)** | 10-25ms | 30-50ms | 40-100 pages/sec | $0.00 (free) |
| **Modal GPU (T4)** | 15-30ms | 40-60ms | 30-65 pages/sec | $0.007 |
| **CPU (Local)** | 40-100ms | 150-300ms | 10-25 pages/sec | $0.00 (free) |
```

---

### Section 7: Error Handling & Edge Cases (Recommended for Complex Workstreams)

**Template**:

```markdown
## Error Handling & Recovery

### Error Categories

| Category | Severity | Recovery Strategy | Examples |
|----------|----------|-------------------|----------|
| **[Category 1]** | [Low/Medium/High/Critical] | [How to recover] | [Example errors] |

### Retry Logic

**[Pattern Name]** (e.g., Exponential Backoff):

```[language]
# Implementation showing retry pattern
```

### Fallback Strategies

- **[Scenario 1]**: [Fallback approach]
- **[Scenario 2]**: [Fallback approach]

```

**When to Include**:
- Complex state machines with multiple error paths
- Mission-critical systems requiring high reliability
- Systems with external dependencies that can fail

---

### Section 8: Integration Points (Recommended)

**Template**:

```markdown
## Integration with [Workstream Name]

### [Integration Aspect]

**Purpose**: [Why this integration exists]

**Workflow**:

```text
[Workstream A]
    ↓ ([artifact type])
[Workstream B]
    ↓ ([processing])
[Workstream C]
```

**Integration Details**:

- [Detail 1]
- [Detail 2]

```

**Example** (from Model Training - Arena Integration):

```markdown
## Integration with Model Arena (Workstream 6)

### Phase 2: Fine-Tuned Validation

**Purpose**: Validate that fine-tuning improved performance before production deployment

**Workflow**:

```text
Training Complete (this workstream)
    ↓
Export to ONNX + Metadata
    ↓
Trigger Arena Benchmark (Workstream 6)
    ↓
Graduation Check: PLCC > 0.65?
    ↓
Deploy to Runtime (Workstream 1)
```

**Graduation Criteria**:

- Target PLCC: > 0.65
- Minimum Improvement: +10% vs baseline

```

---

### Section 9: Level 3 Assessment (MANDATORY)

**Template**:

```markdown
## Level 3 Decision

**Is Level 3 Documentation Necessary?**

### Analysis

[Workstream name] involves:
- [Key complexity factor 1]
- [Key complexity factor 2]
- [Current LOC count]

**Current Complexity**: [Assessment of code complexity]

### Recommendation: **Level 3 [REQUIRED/NOT REQUIRED/CONDITIONAL]**

**Rationale**:
1. [Reason 1 for decision]
2. [Reason 2 for decision]
3. [Reason 3 for decision]

### When Level 3 WOULD Be Needed (if NOT REQUIRED):
- If [condition 1]
- If [condition 2]
- If [condition 3]

**Current Guidance**: [Where developers should look for implementation details]
```

**Example** (from Model Arena - Level 3 NOT REQUIRED):

```markdown
### Recommendation: **Level 3 NOT REQUIRED** (at current scale)

**Rationale**:
1. **Self-Contained Components**: Each component (~200-630 lines) is small enough to understand by reading source
2. **Well-Documented Code**: Existing docstrings and type hints provide implementation details
3. **Simple Data Flow**: Linear pipeline (load → infer → compute → save)

### When Level 3 WOULD Be Needed:
- If components grow beyond 1,000 lines each
- If complex state machines emerge within components
- If integration patterns become non-obvious

**Current Guidance**: Developers should read source files directly. This Level 2 doc provides sufficient architectural context.
```

---

### Section 10: Related Documentation (Required)

**Template**:

```markdown
## Related Documentation

| Level | Document | Description |
|-------|----------|-------------|
| **Level 0** | [RAG Pipeline Overview](../../level-0/index.md) | Multi-project context |
| **Level 1** | [Project A Architecture](../../level-1/index.md) | Eight workstreams overview |
| **Level 2** | [[Related Workstream 1]](../[path]/index.md) | [Relationship] |
| **Level 2** | [[Related Workstream 2]](../[path]/index.md) | [Relationship] |
| **Planning** | [[Relevant Planning Doc]](../../../planning/[doc].md) | [What it contains] |
| **ADR** | [[Relevant ADR]](../../../ADRs/[number]-[title].md) | [Decision documented] |
```

**Guidelines**:

- Always link to Level 0 and Level 1
- Include 2-4 related Level 2 workstreams
- Reference relevant planning docs and ADRs

---

### Section 11: Source Files & Traceability (Required)

**Template**:

```markdown
## Source Files

### Core Implementation

| File | Purpose | Lines |
|------|---------|-------|
| [file.py](../../../../src/path/to/file.py) | [Component name] | ~XXX |
| [module/](../../../../src/path/to/module/) | [Module purpose] | ~XXX |

### Configuration

| File | Purpose |
|------|---------|
| [config.yaml](../../../../configs/path/config.yaml) | [Config purpose] |

### Tests

| File | Purpose | Coverage |
|------|---------|----------|
| [test_file.py](../../../../tests/path/test_file.py) | [Test scope] | XX tests |

**Total Lines**: ~X,XXX (implementation) + X,XXX (tests)

---

*Last Updated: YYYY-MM-DD*
```

---

## Sizing Guidelines

### Minimum Requirements

| Workstream Complexity | Minimum Lines | Sections Required |
|----------------------|---------------|-------------------|
| **Simple** (<500 LOC) | 150+ lines | 1-3, 5, 9-11 |
| **Medium** (500-2,000 LOC) | 300+ lines | 1-6, 9-11 |
| **Complex** (2,000-5,000 LOC) | 500+ lines | All sections (1-11) |
| **Very Complex** (>5,000 LOC) | 700+ lines | All sections + custom sections |

### "Level 2.5" Qualification

A Level 2 doc achieves "Level 2.5" standard when it includes:

- ✅ Comprehensive component breakdown (with LOC counts)
- ✅ Code examples for key algorithms/patterns
- ✅ Workstream dependencies (upstream/downstream/external)
- ✅ Integration points with specific workstreams
- ✅ Performance characteristics (quantitative metrics)
- ✅ Explicit Level 3 decision with rationale

**Target**: 400-800 lines for complex workstreams (>2,000 LOC)

---

## Code Example Guidelines

### When to Include Code

**Include code examples for**:

- Complex algorithms (e.g., distillation loss, device selection)
- Configuration patterns (YAML, JSON schemas)
- API usage (how to invoke components)
- Integration patterns (how workstreams connect)

**Do NOT include**:

- Complete function implementations (link to source instead)
- Boilerplate code
- Implementation details better documented in source code docstrings

### Code Example Format

**Python**:

```python
# Brief context comment
def example_function(param: Type) -> ReturnType:
    """Docstring explaining purpose."""
    # Show key logic only
    result = key_operation(param)
    return result
```

**YAML Configuration**:

```yaml
# config_name.yaml
section:
  key: value  # Inline comment explaining purpose
  nested:
    parameter: value
```

**JSON Schema**:

```json
{
  "field_name": "value",
  "description": "What this represents"
}
```

**Text Diagrams** (for flows):

```text
Step 1: [Action]
    ↓
Step 2: [Decision]
    ├─ YES: [Path A]
    └─ NO: [Path B]
```

---

## Table Guidelines

### Component Tables

**Use for**: Listing system components with metadata

**Format**:

```markdown
| Component | Attribute 1 | Attribute 2 | Attribute 3 |
|-----------|-------------|-------------|-------------|
| **Item 1** | Value | Value | Value |
```

**Best Practices**:

- **Bold** component names for scanning
- Include source file paths when relevant
- Add "Lines" column for complexity assessment

### Comparison Tables

**Use for**: Comparing options, devices, configurations

**Format**:

```markdown
| Option | Metric 1 | Metric 2 | Use Case |
|--------|----------|----------|----------|
| Option A | Value | Value | [When to use] |
| Option B | Value | Value | [When to use] |
```

### Workflow Tables

**Use for**: State machines, phases, pipeline stages

**Format**:

```markdown
| Stage | Entry | Exit | Timeout | Fallback |
|-------|-------|------|---------|----------|
| Stage 1 | [Condition] | [Condition] | Xs | [Action] |
```

---

## Documentation Anti-Patterns

### ❌ Avoid These Mistakes

1. **Diagram-Only Documentation**:
   - ❌ BAD: Only SVG diagrams with minimal text
   - ✅ GOOD: Diagrams + comprehensive narrative explaining workflows

2. **Missing Dependencies**:
   - ❌ BAD: No explanation of where data comes from or goes to
   - ✅ GOOD: Explicit "Workstream Dependencies" section

3. **Vague Descriptions**:
   - ❌ BAD: "Component handles processing"
   - ✅ GOOD: "Device Orchestrator selects optimal inference device (Local GPU → Modal GPU → CPU) based on availability, budget, and document characteristics"

4. **No Quantitative Metrics**:
   - ❌ BAD: "Fast performance"
   - ✅ GOOD: "10-25ms latency (GPU), 40-100ms (CPU), 40-100 pages/sec throughput"

5. **Missing Code Context**:
   - ❌ BAD: "Uses exponential backoff"
   - ✅ GOOD: Shows actual retry implementation with jitter

6. **Incomplete Integration**:
   - ❌ BAD: "Integrates with Model Arena"
   - ✅ GOOD: Detailed workflow showing Training → Arena → Production with graduation criteria

---

## Quality Checklist

Before marking a Level 2 doc "complete", verify:

### Content Completeness

- [ ] All required sections (1-3, 5, 9-11) present
- [ ] Workstream Dependencies section with upstream/downstream/external
- [ ] At least 2 code examples showing implementation patterns
- [ ] Performance metrics (latency, throughput, or cost)
- [ ] Level 3 decision with clear rationale

### Technical Accuracy

- [ ] All source file paths are correct and clickable
- [ ] Code examples are syntactically valid
- [ ] LOC counts are accurate (±10%)
- [ ] Cross-references point to valid documents

### Formatting

- [ ] Markdown linting passing (run `markdownlint --fix`)
- [ ] Frontmatter schema_type is "common"
- [ ] Tables are properly formatted
- [ ] Code blocks have language specified
- [ ] Blank lines around code fences and lists

### Completeness Thresholds

- [ ] Simple workstream: ≥150 lines
- [ ] Medium workstream: ≥300 lines
- [ ] Complex workstream: ≥500 lines
- [ ] Very complex workstream: ≥700 lines

---

## Example: Full Level 2.5 Document Outline

```markdown
---
schema_type: common
title: "Level 2: Example Workstream"
description: "Example workstream documentation"
tags: [architecture, diagrams, level-2, example]
status: published
owner: "core-maintainer"
authors:
  - name: "Author Name"
purpose: "Document the example workstream..."
last_updated: "2025-01-16"
---

# Level 2: Example Workstream

Overview paragraph with status, LOC, purpose...

---

## Technical Diagrams

### High-Level Workflow
![Workflow](diagram.svg)

---

## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| Component A | `src/a.py` | Does X |

---

## [Main Workflow/Algorithm Name]

### [Sub-section 1]

Narrative with technical details...

```python
# Code example
def example():
    pass
```

### [Sub-section 2]

**Configuration**:

```yaml
config:
  key: value
```

---

## Workstream Dependencies

### Upstream Dependencies

[Table]

### Downstream Consumers

[Table]

### External Dependencies

[Table]

---

## Performance Characteristics

[Table with metrics]

---

## Integration with [Related Workstream]

[Workflow and details]

---

## Level 3 Decision

**Recommendation**: Level 3 [REQUIRED/NOT REQUIRED/CONDITIONAL]

**Rationale**: [Reasons]

---

## Related Documentation

[Links table]

---

## Source Files

[Traceability table]

---

*Last Updated: YYYY-MM-DD*

```

---

## Conversion Guide: Upgrading Existing Docs to Level 2.5

### Step 1: Audit Current Doc

Check for:
- [ ] Current line count
- [ ] Presence of Workstream Dependencies section
- [ ] Number of code examples (target: 2-5)
- [ ] Performance metrics included
- [ ] Level 3 decision documented

### Step 2: Add Missing Sections

**Priority Order** (add in this sequence):
1. **Workstream Dependencies** (if missing) - CRITICAL
2. **Code Examples** (2-5 examples) - HIGH
3. **Performance Characteristics** (quantitative metrics) - MEDIUM
4. **Integration Points** (cross-workstream flows) - MEDIUM
5. **Error Handling** (if complex system) - LOW

### Step 3: Enrich Existing Sections

- Add code examples to workflow descriptions
- Quantify performance claims
- Explain algorithms with pseudocode or actual code
- Add tables for comparisons and configurations

### Step 4: Validate Quality

- Run markdown linter
- Check all cross-references
- Verify code examples are valid
- Ensure 300+ lines for medium/complex workstreams

---

## Examples by Workstream Type

### Example 1: Simple Workstream (Data Preparation)

**Characteristics**: Data ingestion, cataloging, no complex algorithms
**Recommended Length**: 300-500 lines
**Focus**: Dataset structure, metadata layers, storage strategy
**Code Examples**: Configuration patterns, data loaders

**Actual Doc**: [data-preparation/index.md](diagrams/level-2/data-preparation/index.md) - 429 lines

---

### Example 2: Complex Workstream (Production Runtime)

**Characteristics**: 15,000+ LOC, mission-critical, complex state machine
**Recommended Length**: 600-800 lines
**Focus**: State machine, error handling, device orchestration, performance
**Code Examples**: Retry logic, circuit breaker, batch processing

**Actual Doc**: [production-runtime/index.md](diagrams/level-2/production-runtime/index.md) - 670+ lines

---

### Example 3: Very Complex Workstream (Monitoring & Drift)

**Characteristics**: 7,400 LOC, 6 sub-systems, stateful workflows
**Recommended Length**: 800-1,000 lines
**Focus**: Component architecture, integration flows, operational aspects
**Code Examples**: API usage, configuration, alert rules

**Actual Doc**: [monitoring-drift/index.md](diagrams/level-2/monitoring-drift/index.md) - 890 lines

---

## When Level 3 IS Still Needed

Even with Level 2.5, some workstreams still require Level 3 documentation:

### Clear "Yes" for Level 3

1. **Very Large Codebase** (>10,000 LOC)
   - Example: Production Runtime (15,000 LOC)
   - Level 3 Needed: Pipeline state machine, DeviceOrchestrator internals

2. **Complex Multi-Layer Architecture**
   - Example: Data Preparation (three-layer metadata)
   - Level 3 Needed: Metadata schema ER diagrams, label parser sequences

3. **Compliance/Audit Requirements**
   - Example: Monitoring & Drift (GDPR/CCPA workflows)
   - Level 3 Needed: Privacy review workflows, audit trails

### Borderline Cases

4. **Medium Complexity with Growth Potential**
   - Example: Synthetic Data Generation (1,070 LOC)
   - Decision: Monitor complexity, add Level 3 if Genalog integration grows complex

5. **Standard Patterns, Well-Documented**
   - Example: Model Training (3,000 LOC)
   - Decision: Level 2.5 sufficient if standard PyTorch workflows

---

## Maintenance Guidelines

### Keeping Level 2.5 Docs Current

**Quarterly Review**:
- [ ] Update LOC counts (or automate via Issue 3.3)
- [ ] Verify code examples still match source code
- [ ] Check cross-references for broken links (or automate via Issue 3.4)
- [ ] Update performance metrics if benchmarks change

**After Major Changes**:
- [ ] Update relevant code examples
- [ ] Revise performance characteristics
- [ ] Reassess Level 3 decision if complexity increased

**After Deprecations**:
- [ ] Move deprecated docs to `deprecated/` directory
- [ ] Update cross-references
- [ ] Add deprecation headers

---

## Success Metrics

### For Individual Docs

- **Completeness**: ≥300 lines (complex workstreams)
- **Code Examples**: 2-5 working examples
- **Dependencies**: Upstream/Downstream/External all documented
- **Performance**: Quantitative metrics included
- **Linting**: Zero markdown linting errors

### For Documentation Suite

- **Consistency**: All workstreams follow same template
- **Dependencies**: 100% of docs have dependency sections
- **Cross-References**: Zero broken links
- **Level 3 Decisions**: 100% of docs have explicit rationale

---

## References

### Established "Level 2.5" Examples

Study these docs for patterns and structure:

1. **[Production Runtime](diagrams/level-2/production-runtime/index.md)** - State machines, error handling, device orchestration
2. **[Model Training](diagrams/level-2/model-training/index.md)** - Training workflows, distillation, deployment pipeline
3. **[Monitoring & Drift](diagrams/level-2/monitoring-drift/index.md)** - Multi-component system, operational aspects
4. **[Model Arena](diagrams/level-2/model-arena/index.md)** - Component architecture, reproducibility, integration flows
5. **[Data Preparation](diagrams/level-2/data-preparation/index.md)** - Metadata architecture, storage strategy, parsers

### Related Standards

- [ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md](ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md) - Improvement roadmap
- [DOCUMENTATION_IMPROVEMENT_SESSION_SUMMARY.md](DOCUMENTATION_IMPROVEMENT_SESSION_SUMMARY.md) - Session learnings

---

*This template established 2025-01-16 based on multi-model AI consensus (Gemini 3 Pro, GPT-5.1, DeepSeek R1)*
