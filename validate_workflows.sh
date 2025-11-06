#!/bin/bash
set -e

echo "=========================================="
echo "LOCAL WORKFLOW VALIDATION"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

echo "==================== CI WORKFLOW ===================="
echo ""

# 1. Test Suite with Coverage
echo "📋 Running test suite with coverage..."
if poetry run pytest -v --cov=src/image_preprocessing_detector --cov-report=term-missing --cov-fail-under=80 -q; then
    echo -e "${GREEN}✅ Tests passed with adequate coverage${NC}"
else
    echo -e "${RED}❌ Tests failed or coverage below 80%${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 2. Type Checking (MyPy)
echo "🔍 Running type checking with MyPy..."
if poetry run mypy src --config-file=pyproject.toml; then
    echo -e "${GREEN}✅ MyPy type checking passed${NC}"
else
    echo -e "${RED}❌ MyPy found type errors${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 3. Code Formatting (Black)
echo "🎨 Checking code formatting with Black..."
if poetry run black . --check --config=pyproject.toml; then
    echo -e "${GREEN}✅ Black formatting check passed${NC}"
else
    echo -e "${RED}❌ Black found formatting issues${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 4. Linting (Ruff)
echo "🧹 Running linting with Ruff..."
if poetry run ruff check . --config=pyproject.toml; then
    echo -e "${GREEN}✅ Ruff linting passed${NC}"
else
    echo -e "${RED}❌ Ruff found linting issues${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "==================== PR VALIDATION WORKFLOW ===================="
echo ""

# 5. Validate Image Processing Dependencies
echo "📸 Validating image processing dependencies..."
if poetry run python -c "
import sys
critical_deps = ['cv2', 'numpy', 'PIL', 'pymupdf', 'pydantic']
failed = []
for dep in critical_deps:
    try:
        mod = __import__(dep.replace('-', '_'))
        version = getattr(mod, '__version__', 'unknown')
        if dep == 'cv2':
            version = mod.__version__
        print(f'✅ {dep} ({version}): Available')
    except ImportError as e:
        print(f'❌ {dep}: MISSING - {e}')
        failed.append(dep)
if failed:
    print(f'Critical dependencies missing: {failed}')
    sys.exit(1)
print('✅ All critical image processing dependencies available')
"; then
    echo -e "${GREEN}✅ Image processing dependencies validated${NC}"
else
    echo -e "${RED}❌ Missing critical dependencies${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 6. Validate Requirements Sync
echo "📦 Validating requirements.txt sync..."
if [ -f "requirements.txt" ]; then
    echo "Generating fresh requirements.txt..."
    poetry export -f requirements.txt --output requirements-check.txt --without-hashes
    if diff -q requirements.txt requirements-check.txt > /dev/null 2>&1; then
        echo -e "${GREEN}✅ requirements.txt is synchronized${NC}"
        rm requirements-check.txt
    else
        echo -e "${YELLOW}⚠️  requirements.txt differs from poetry.lock${NC}"
        echo "Run: poetry export -f requirements.txt --output requirements.txt --without-hashes"
        rm requirements-check.txt
    fi
else
    echo -e "${YELLOW}⚠️  No requirements.txt file found (optional)${NC}"
fi
echo ""

echo "==================== SECURITY WORKFLOW ===================="
echo ""

# 7. Bandit Security Analysis
echo "🔒 Running Bandit security analysis..."
if poetry run bandit -r src -c pyproject.toml -q; then
    echo -e "${GREEN}✅ Bandit security scan passed${NC}"
else
    echo -e "${YELLOW}⚠️  Bandit found potential security issues (review manually)${NC}"
fi
echo ""

# 8. Safety Vulnerability Scan
echo "🛡️  Running Safety vulnerability scan..."
poetry export -f requirements.txt --output requirements-scan.txt --without-hashes 2>/dev/null
if poetry run safety check --file requirements-scan.txt --json > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Safety scan passed (no known vulnerabilities)${NC}"
else
    echo -e "${YELLOW}⚠️  Safety found potential vulnerabilities (review manually)${NC}"
fi
rm -f requirements-scan.txt
echo ""

# 9. Project Structure Validation
echo "🏗️  Validating project structure..."
required_dirs=(
    "src"
    "src/image_preprocessing_detector"
    "src/image_preprocessing_detector/ingestion"
    "src/image_preprocessing_detector/detection"
    "src/image_preprocessing_detector/correction"
    "src/image_preprocessing_detector/output"
    "tests"
)

required_files=(
    "pyproject.toml"
    "README.md"
    "CLAUDE.md"
)

missing_dirs=0
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (missing)"
        missing_dirs=$((missing_dirs + 1))
    fi
done

missing_files=0
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ⚠️  $file (missing)"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_dirs -eq 0 ] && [ $missing_files -eq 0 ]; then
    echo -e "${GREEN}✅ Project structure validation passed${NC}"
elif [ $missing_dirs -gt 0 ]; then
    echo -e "${RED}❌ Required directories missing${NC}"
    FAILURES=$((FAILURES + 1))
else
    echo -e "${YELLOW}⚠️  Some recommended files missing${NC}"
fi
echo ""

echo "=========================================="
echo "VALIDATION SUMMARY"
echo "=========================================="
echo ""

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ ALL WORKFLOW VALIDATIONS PASSED${NC}"
    echo ""
    echo "Your code is ready to push to GitHub!"
    echo "The following workflows will pass:"
    echo "  ✅ CI Pipeline (ci.yml)"
    echo "  ✅ PR Validation (pr-validation.yml)"
    echo "  ✅ Security Analysis (security-analysis.yml)"
    exit 0
else
    echo -e "${RED}❌ SOME VALIDATIONS FAILED (${FAILURES} issues)${NC}"
    echo ""
    echo "Please fix the issues above before pushing to GitHub."
    exit 1
fi
