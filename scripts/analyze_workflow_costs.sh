#!/usr/bin/env bash
# Analyze GitHub Actions workflow costs using gh CLI
#
# Prerequisites: gh CLI installed and authenticated
# Usage: ./scripts/analyze_workflow_costs.sh [days]

set -euo pipefail

DAYS="${1:-30}"
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

echo "======================================================================"
echo "GitHub Actions Workflow Analysis - Last ${DAYS} Days"
echo "======================================================================"
echo "Repository: ${REPO}"
echo ""

# Fetch workflow runs
echo "📊 Fetching workflow runs..."
TEMP_FILE=$(mktemp)
gh api "repos/${REPO}/actions/runs?per_page=100&created=>=$(date -d "${DAYS} days ago" +%Y-%m-%d)" > "$TEMP_FILE"

# Parse and analyze
echo ""
echo "Analyzing workflows..."
echo ""

# Create summary using jq
jq -r '
.workflow_runs |
group_by(.name) |
map({
  workflow: .[0].name,
  runs: length,
  total_duration: (map(.run_duration_ms // 0) | add / 60000),
  avg_duration: ((map(.run_duration_ms // 0) | add / 60000) / length),
  failed: (map(select(.conclusion == "failure")) | length),
  success: (map(select(.conclusion == "success")) | length),
  cancelled: (map(select(.conclusion == "cancelled")) | length)
}) |
sort_by(.total_duration) | reverse |
map("\(.workflow)|\(.runs)|\(.total_duration|floor)|\(.avg_duration|floor)|\(.failed)") |
.[]
' "$TEMP_FILE" | while IFS='|' read -r workflow runs duration avg failed; do
  # Estimate cost at $0.008/minute for Linux runners
  cost=$(echo "scale=2; $duration * 0.008" | bc)
  printf "%-45s %6s runs  %8s min  %8s min/run  \$%7.2f  %5s failed\n" \
    "$workflow" "$runs" "$duration" "$avg" "$cost" "$failed"
done

# Calculate totals
echo ""
echo "======================================================================"
TOTAL_RUNS=$(jq -r '.workflow_runs | length' "$TEMP_FILE")
TOTAL_DURATION=$(jq -r '.workflow_runs | map(.run_duration_ms // 0) | add / 60000 | floor' "$TEMP_FILE")
TOTAL_COST=$(echo "scale=2; $TOTAL_DURATION * 0.008" | bc)

echo "TOTAL: $TOTAL_RUNS runs, $TOTAL_DURATION minutes, \$$TOTAL_COST (estimated)"
echo "======================================================================"

# Top 5 most expensive
echo ""
echo "🔥 TOP 5 MOST EXPENSIVE WORKFLOWS:"
jq -r '
.workflow_runs |
group_by(.name) |
map({
  workflow: .[0].name,
  total_duration: (map(.run_duration_ms // 0) | add / 60000)
}) |
sort_by(.total_duration) | reverse |
.[:5] |
.[] |
"\(.workflow): \(.total_duration|floor) min ($(\(.total_duration * 0.008)|floor) USD)"
' "$TEMP_FILE" | nl

# Workflows with high failure rates
echo ""
echo "⚠️  WORKFLOWS WITH HIGH FAILURE RATES:"
jq -r '
.workflow_runs |
group_by(.name) |
map({
  workflow: .[0].name,
  runs: length,
  failed: (map(select(.conclusion == "failure")) | length)
}) |
map(select(.runs >= 5 and (.failed / .runs) > 0.2)) |
sort_by(.failed / .runs) | reverse |
.[] |
"\(.workflow): \((.failed / .runs * 100)|floor)% failure rate (\(.failed)/\(.runs))"
' "$TEMP_FILE" | nl

rm -f "$TEMP_FILE"

echo ""
echo "💡 OPTIMIZATION TIPS:"
echo "1. Review workflows with high duration - consider caching dependencies"
echo "2. Check failed workflows - fix issues to avoid wasted compute"
echo "3. Use 'if:' conditions to skip unnecessary jobs"
echo "4. Add path filters to run workflows only when relevant files change"
echo "5. Consider consolidating similar workflows"
echo "6. Use matrix builds sparingly - test on fewer OS/Python versions"
