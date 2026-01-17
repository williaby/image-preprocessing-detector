#!/usr/bin/env bash
# Comprehensive local validation matching CI requirements
# Run this before pushing to catch all CI issues locally
#
# Usage:
#   ./scripts/validate-before-push.sh
#
# Or add as git hook:
#   ln -sf ../../scripts/validate-before-push.sh .git/hooks/pre-push
#
# Or add as git alias:
#   git config alias.validate '!./scripts/validate-before-push.sh'
#   git validate

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track failures
FAILED=0
TOTAL_CHECKS=0

# Function to run a check
run_check() {
    local check_name="$1"
    local check_command="$2"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo -e "${BLUE}[$TOTAL_CHECKS/12]${NC} ${check_name}..."

    if eval "$check_command" > /tmp/check_output_$$ 2>&1; then
        echo -e "  ${GREEN}✅ PASSED${NC}"
        return 0
    else
        echo -e "  ${RED}❌ FAILED${NC}"
        echo -e "${YELLOW}Output:${NC}"
        cat /tmp/check_output_$$
        echo ""
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Banner
echo "======================================================================"
echo "🔍 Comprehensive Pre-Push Validation"
echo "======================================================================"
echo "This matches CI checks to catch issues BEFORE pushing"
echo "Saves GitHub Actions minutes and reduces PR cycle time"
echo ""

# Check 1: Code Formatting (Ruff)
run_check "Code formatting (Ruff)" \
    "uv run ruff format --check src/ tests/" || \
    echo -e "${YELLOW}  💡 Fix with: uv run ruff format src/ tests/${NC}\n"

# Check 2: Linting (Ruff)
run_check "Linting (Ruff check)" \
    "uv run ruff check src/ tests/" || \
    echo -e "${YELLOW}  💡 Fix with: uv run ruff check --fix src/ tests/${NC}\n"

# Check 3: Type Checking (BasedPyright - strict on src/)
run_check "Type checking (BasedPyright strict)" \
    "uv run basedpyright src/" || \
    echo -e "${YELLOW}  💡 Fix type errors in src/ directory${NC}\n"

# Check 4: Security Scanning (Bandit)
run_check "Security scan (Bandit)" \
    "uv run bandit -r src/ -c pyproject.toml" || \
    echo -e "${YELLOW}  💡 Review security issues above${NC}\n"

# Check 5: Dependency Security (Safety)
run_check "Dependency vulnerabilities (Safety)" \
    "uv run safety check --bare" || \
    echo -e "${YELLOW}  ⚠️  Dependency vulnerabilities found (review above)${NC}\n"

# Check 6: Tests with Coverage (80% minimum)
run_check "Tests with 80% coverage" \
    "uv run pytest --cov=src --cov-fail-under=80 --cov-report=term-missing -x" || \
    echo -e "${YELLOW}  💡 Fix failing tests or add missing coverage${NC}\n"

# Check 7: Markdown Linting
if command -v npx &> /dev/null; then
    run_check "Markdown linting" \
        "npx markdownlint-cli '**/*.md' --ignore node_modules" || \
        echo -e "${YELLOW}  💡 Fix with: npx markdownlint-cli --fix '**/*.md'${NC}\n"
else
    echo -e "${BLUE}[7/12]${NC} Markdown linting..."
    echo -e "  ${YELLOW}⚠️  SKIPPED (npx not installed)${NC}"
fi

# Check 8: YAML Linting
if command -v yamllint &> /dev/null; then
    run_check "YAML linting" \
        "yamllint .github/workflows/*.yml" || \
        echo -e "${YELLOW}  💡 Fix YAML formatting issues${NC}\n"
else
    echo -e "${BLUE}[8/12]${NC} YAML linting..."
    echo -e "  ${YELLOW}⚠️  SKIPPED (yamllint not installed)${NC}"
fi

# Check 9: Docker Compose Validation
if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
    run_check "Docker Compose validation" \
        "docker compose config --quiet" || \
        echo -e "${YELLOW}  💡 Fix docker-compose.yml syntax errors${NC}\n"
else
    echo -e "${BLUE}[9/12]${NC} Docker Compose validation..."
    echo -e "  ${YELLOW}⚠️  SKIPPED (no docker-compose.yml or docker not installed)${NC}"
fi

# Check 10: REUSE License Compliance
if command -v reuse &> /dev/null; then
    run_check "REUSE license compliance" \
        "reuse lint" || \
        echo -e "${YELLOW}  💡 Add missing license headers (see REUSE output above)${NC}\n"
else
    echo -e "${BLUE}[10/12]${NC} REUSE license compliance..."
    echo -e "  ${YELLOW}⚠️  SKIPPED (reuse not installed)${NC}"
fi

# Check 11: Import Order and Unused Imports (Ruff specific rules)
run_check "Import ordering and unused imports" \
    "uv run ruff check --select I,F401 src/ tests/" || \
    echo -e "${YELLOW}  💡 Fix with: uv run ruff check --select I,F401 --fix src/ tests/${NC}\n"

# Check 12: Dead Code Detection (Vulture - optional but valuable)
if uv run python -c "import vulture" 2>/dev/null; then
    run_check "Dead code detection (Vulture)" \
        "uv run vulture src/ --min-confidence 80" || \
        echo -e "${YELLOW}  💡 Review potentially unused code above${NC}\n"
else
    echo -e "${BLUE}[12/12]${NC} Dead code detection (Vulture)..."
    echo -e "  ${YELLOW}⚠️  SKIPPED (vulture not installed - optional)${NC}"
fi

# Cleanup
rm -f /tmp/check_output_$$

# Summary
echo ""
echo "======================================================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All validations passed!${NC}"
    echo "Your code is ready to push and should pass CI on first try."
    echo ""
    echo "💡 This local validation saved you from:"
    echo "   - Triggering ~15 CI workflows"
    echo "   - Waiting 10-15 minutes for CI results"
    echo "   - Wasting $0.80-1.20 in GitHub Actions minutes"
    echo "   - The embarrassment of failed CI checks 😉"
    echo "======================================================================"
    exit 0
else
    echo -e "${RED}❌ ${FAILED} check(s) failed${NC}"
    echo ""
    echo "Please fix the issues above before pushing."
    echo ""
    echo "💡 Common fixes:"
    echo "   Formatting:  uv run ruff format src/ tests/"
    echo "   Linting:     uv run ruff check --fix src/ tests/"
    echo "   Tests:       uv run pytest -v"
    echo ""
    echo "After fixing, re-run: ./scripts/validate-before-push.sh"
    echo "======================================================================"
    exit 1
fi
