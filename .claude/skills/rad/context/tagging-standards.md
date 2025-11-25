# RAD Assumption Tagging Standards

Quick reference for assumption tagging during development. Extracted from global CLAUDE.md standards.

## Tagging Syntax

When writing code, ALWAYS tag assumptions that could cause production failures:

```javascript
// #CRITICAL: [category]: [assumption that could cause outages/data loss]
// #VERIFY: [defensive code required]
// Example: Payment processing, auth flows, concurrent writes

// #ASSUME: [category]: [assumption that could cause bugs]
// #VERIFY: [validation needed]
// Example: UI state, form validation, API responses

// #EDGE: [category]: [assumption about uncommon scenarios]
// #VERIFY: [optional improvement]
// Example: Browser compatibility, slow networks
```

## Critical Assumption Categories (MANDATORY Tagging)

These categories MUST be tagged as #CRITICAL when assumptions are made:

### Timing Dependencies
State updates, async operations, race conditions

```javascript
// #CRITICAL: timing: React state update assumed complete before navigation
// #VERIFY: Use callback or state confirmation
setUserData(newData);
navigateToProfile(userData.id);  // ❌ Race condition
```

### External Resources
API availability, file existence, network connectivity

```javascript
// #CRITICAL: api: Payment gateway assumed to respond within 5s
// #VERIFY: Add timeout and retry logic
const result = await paymentGateway.charge(amount);  // ❌ No timeout
```

### Data Integrity
Type safety at boundaries, null/undefined handling

```javascript
// #CRITICAL: validation: User input assumed sanitized
// #VERIFY: Add input validation and sanitization
function executeQuery(userInput) {
    return db.query(userInput);  // ❌ SQL injection risk
}
```

### Concurrency
Shared state, transaction isolation, deadlock potential

```javascript
// #CRITICAL: concurrency: Database transaction isolation assumed
// #VERIFY: Add explicit locks and conflict resolution
async function updateBalance(userId, amount) {
    const user = await db.users.findById(userId);
    user.balance += amount;  // ❌ Race condition
    return user.save();
}
```

### Security
Authentication, authorization, input validation

```javascript
// #CRITICAL: auth: User session assumed valid
// #VERIFY: Add token validation and refresh logic
function getCurrentUser() {
    return localStorage.getItem('currentUser');  // ❌ No validation
}
```

### Payment/Financial
Transaction integrity, retry logic, rollback handling

```javascript
// #CRITICAL: payment: Transaction assumed atomic
// #VERIFY: Add rollback and idempotency checks
await chargeCard(amount);
await updateInventory(itemId);  // ❌ No transaction boundary
```

## Standard Assumption Categories (Use #ASSUME)

### State Management
React/Vue state, localStorage, session state

```javascript
// #ASSUME: state: Component state persists across re-renders
// #VERIFY: Add useEffect cleanup or state persistence
const [data, setData] = useState(initialData);
```

### API Responses
Response format, error handling, status codes

```javascript
// #ASSUME: api: API always returns 200 or 404
// #VERIFY: Add error handling for 500, timeout, network errors
const response = await fetch(url);
```

### Form Validation
Client-side validation, field requirements

```javascript
// #ASSUME: validation: Email format validated on submit
// #VERIFY: Add real-time validation or backend verification
<input type="email" />
```

### UI State
Modal visibility, loading states, disabled states

```javascript
// #ASSUME: ui: Modal closes on background click
// #VERIFY: Add explicit close handler or escape key support
<Modal isOpen={showModal} />
```

## Edge Case Categories (Use #EDGE)

### Browser Compatibility
API availability, CSS support, feature detection

```javascript
// #EDGE: browser: Clipboard API available in all browsers
// #VERIFY: Add fallback using document.execCommand
navigator.clipboard.writeText(text);
```

### Network Conditions
Slow networks, offline handling, retry logic

```javascript
// #EDGE: network: Assuming high-speed connection
// #VERIFY: Add loading states, timeout, or offline fallback
const data = await fetchLargeDataset();
```

### Performance
Large datasets, memory usage, rendering optimization

```javascript
// #EDGE: performance: Assuming dataset <1000 items
// #VERIFY: Add pagination or virtualization for large lists
{items.map(item => <ListItem key={item.id} />)}
```

## Verification Status Markers

After verification, mark assumptions as verified:

```javascript
// #CRITICAL: [VERIFIED-2025-01-30] payment: Timeout added
// #VERIFY: ✅ Added timeout and retry with exponential backoff
async function processPayment(amount) {
    return Promise.race([
        paymentGateway.charge(amount),
        timeout(5000)
    ]);
}
```

## Anti-Patterns (Do NOT Tag)

Don't tag trivial or obvious code:

```javascript
// ❌ BAD: Over-tagging trivial assumptions
// #ASSUME: math: Addition returns sum
const total = price + tax;

// ✅ GOOD: Only tag production-impacting assumptions
// #CRITICAL: payment: Tax calculation assumed to use correct jurisdiction
const total = price + calculateTax(price, userLocation);
```

## Workflow Integration

### During Development
Claude adds tags automatically during code generation

### During Code Review
Reviewers can add missing tags for risky code

### Before Commit
```bash
# Verify all assumptions in changed files
/rad/verify --scope=changed-files

# Or verify critical assumptions only
/rad/verify --strategy=critical-only
```

### During PR Review
```bash
# List all assumptions in PR
/rad/list

# Ensure no unverified critical assumptions
grep "❌" assumption-report.md && echo "Fix critical assumptions first!"
```

## Integration with Pre-Commit Hooks

Pre-commit hooks can enforce assumption verification:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: verify-critical-assumptions
      name: Verify Critical Assumptions
      entry: bash -c '/rad/verify --strategy=critical-only --scope=changed-files'
      language: system
      pass_filenames: false
```

## Resources

- **Complete Methodology**: See rad/context/methodology.md
- **Verification Workflow**: See rad/workflows/verify.md
- **Testing Guide**: See rad/workflows/test.md
- **Global Standards**: See CLAUDE.md > Response-Aware Development

---

*Extracted from Global CLAUDE.md > Response-Aware Development section.*
