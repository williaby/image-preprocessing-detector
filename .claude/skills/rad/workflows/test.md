---
description: Test the Response-Aware Development system by creating sample assumptions and demonstrating the workflow.
argument-hint: [test-type]
allowed-tools: Bash(echo:*), Read, Write
---

# RAD System Testing Workflow

Test the Response-Aware Development system by creating sample code with assumption tags and demonstrating the verification process.

## Task Overview

Create sample code with assumption tags across all risk levels and demonstrate:

- Assumption tagging methodology
- Risk-based categorization
- Model selection logic
- Integration with verification workflow
- Command-line interface

## Arguments

- `test-type`: Type of test to run (defaults to "basic" if not specified)
  - **basic**: Simple examples covering all tag types
  - **advanced**: Complex scenarios with multiple assumptions per file
  - **minimal**: Single-file quick demo

## Implementation

### 1. Create Test File with Sample Assumptions

```javascript
// test-assumptions.js - Generated for RAD testing

// #CRITICAL: payment: Payment gateway assumed to respond within 5 seconds
// #VERIFY: Add timeout handler and retry logic with exponential backoff
function processPayment(amount) {
    return paymentGateway.charge(amount);
}

// #ASSUME: state: User authentication state persists across page refreshes
// #VERIFY: Add token validation and refresh logic
function getCurrentUser() {
    return localStorage.getItem('currentUser');
}

// #EDGE: browser: Clipboard API availability assumed across all browsers
// #VERIFY: Add fallback for unsupported browsers using document.execCommand
function copyToClipboard(text) {
    return navigator.clipboard.writeText(text);
}

// #CRITICAL: concurrency: Database transaction isolation assumed for concurrent updates
// #VERIFY: Add explicit transaction locks and conflict resolution
async function updateUserBalance(userId, amount) {
    const user = await db.users.findById(userId);
    user.balance += amount;
    return user.save();
}

// #ASSUME: timing: State update completion assumed before navigation
// #VERIFY: Use callback or state confirmation before routing
function updateProfile(userData) {
    setUserData(userData);
    navigateToProfile(userData.id);
}
```

### 2. Demonstrate Assumption Detection

Use Bash to find the assumptions:

```bash
echo "=== RAD Test Results ==="
echo ""
echo "Critical Assumptions Found:"
grep -n "#CRITICAL:" test-assumptions.js || echo "None found"
echo ""
echo "Standard Assumptions Found:"
grep -n "#ASSUME:" test-assumptions.js || echo "None found"
echo ""
echo "Edge Case Assumptions Found:"
grep -n "#EDGE:" test-assumptions.js || echo "None found"
```

### 3. Show Verification Command Usage

```bash
echo ""
echo "=== Next Steps ==="
echo "1. Run verification command:"
echo "   /rad/verify --scope=current-file"
echo ""
echo "2. For critical only:"
echo "   /rad/verify --strategy=critical-only"
echo ""
echo "3. List all assumptions:"
echo "   /rad/list"
```

### 4. Demonstrate Model Selection Logic

Explain which models would be used:

- **Line 3 (payment)**: Gemini 2.5 Pro or O3-Mini (critical payment logic)
- **Line 8 (auth state)**: DeepSeek-R1 via dynamic selection (state management)
- **Line 13 (clipboard)**: Gemini Flash Lite (edge case browser compatibility)
- **Line 18 (concurrency)**: Gemini 2.5 Pro (critical database consistency)
- **Line 25 (timing)**: Qwen-Coder via dynamic selection (React/state patterns)

### 5. Show Expected Verification Output

```markdown
# Assumption Verification Report

## Summary
- **Total Assumptions**: 5
- **Critical**: 2 (payment, concurrency)
- **Standard**: 2 (state, timing)
- **Edge Cases**: 1 (browser)

## Critical Issues (❌ BLOCKING)

### payment.js:3 - Payment Timeout
**Risk**: Production payment failures under load
**Fix**: Add timeout and retry logic
```javascript
function processPayment(amount) {
    const timeout = 5000;
    return Promise.race([
        paymentGateway.charge(amount),
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Payment timeout')), timeout)
        )
    ]);
}
```

### payment.js:18 - Race Condition
**Risk**: Data corruption in concurrent updates
**Fix**: Add transaction locks
```javascript
async function updateUserBalance(userId, amount) {
    const transaction = await db.startTransaction();
    try {
        const user = await db.users.findById(userId, { transaction });
        user.balance += amount;
        await user.save({ transaction });
        await transaction.commit();
    } catch (error) {
        await transaction.rollback();
        throw error;
    }
}
```

## Standard Issues (⚠️ REVIEW)
[Additional fixes for state and timing assumptions...]

## Edge Cases (💡 NOTE)
[Browser compatibility fallback...]
```

### 6. Clean Up Test File

```bash
echo ""
echo "=== Cleanup ==="
echo "Test file created: test-assumptions.js"
echo "Remove with: rm test-assumptions.js"
echo ""
echo "RAD system test complete!"
```

## Test Validation Checklist

After running the test, verify:

- [ ] All assumption types detected (CRITICAL, ASSUME, EDGE)
- [ ] Correct model selection based on category
- [ ] Verification report generated with actionable fixes
- [ ] Cost estimation shows >90% free model usage
- [ ] Commands work as documented

## Additional Test Scenarios

### Advanced Test

Create multi-file scenario with:
- Authentication flow (security assumptions)
- Payment processing (financial assumptions)
- State management (timing assumptions)
- API integration (external resource assumptions)

### Minimal Test

Single critical assumption for quick validation:
```javascript
// #CRITICAL: security: User input assumed sanitized
// #VERIFY: Add input validation and sanitization
function executeQuery(userInput) {
    return db.query(userInput);  // SQL injection risk
}
```

---

*Migrated from test-rad command.*
