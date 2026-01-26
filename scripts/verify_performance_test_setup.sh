#!/bin/bash
# Verification script for performance testing setup

echo "Verifying Performance Testing Setup..."
echo ""

check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1"
        return 0
    else
        echo "✗ $1 (missing)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo "✓ $1"
        return 0
    else
        echo "✗ $1 (missing)"
        return 1
    fi
}

errors=0

# Check Playwright configuration
echo "Playwright Configuration:"
check_file "frontend/playwright.config.ts" || ((errors++))

# Check E2E test files
echo ""
echo "E2E Test Files:"
check_file "frontend/e2e/virtual-scrolling-performance.spec.ts" || ((errors++))
check_file "frontend/e2e/README.md" || ((errors++))

# Check component test-ids
echo ""
echo "Component Test IDs:"
echo "Checking VirtualizedGridView for test-id attributes..."
if grep -q "data-testid=\"virtual-grid-container\"" frontend/src/components/views/VirtualizedGridView.tsx; then
    echo "✓ VirtualizedGridView has virtual-grid-container test-id"
else
    echo "✗ VirtualizedGridView missing virtual-grid-container test-id"
    ((errors++))
fi

if grep -q "data-testid=\"virtual-row-" frontend/src/components/views/VirtualizedGridView.tsx; then
    echo "✓ VirtualizedGridView has virtual-row test-id"
else
    echo "✗ VirtualizedGridView missing virtual-row test-id"
    ((errors++))
fi

echo "Checking TableViewPage for records-count test-id..."
if grep -q 'data-testid="records-count"' frontend/src/routes/TableViewPage.tsx; then
    echo "✓ TableViewPage has records-count test-id"
else
    echo "✗ TableViewPage missing records-count test-id"
    ((errors++))
fi

# Check scripts
echo ""
echo "Scripts:"
check_file "scripts/run_performance_test.sh" || ((errors++))

# Check TypeScript compilation
echo ""
echo "TypeScript Compilation:"
cd frontend
if npx tsc --noEmit 2>&1 | grep -q "error TS"; then
    echo "✗ TypeScript compilation failed"
    ((errors++))
else
    echo "✓ TypeScript compilation successful"
fi
cd ..

echo ""
if [ $errors -eq 0 ]; then
    echo "========================================="
    echo "✓ All checks passed!"
    echo "========================================="
    echo ""
    echo "To run performance tests:"
    echo "  TABLE_ID=<your_table_id> ./scripts/run_performance_test.sh"
    echo ""
    echo "Or manually:"
    echo "  cd frontend"
    echo "  TABLE_ID=<your_table_id> npx playwright test"
    exit 0
else
    echo "========================================="
    echo "✗ $errors check(s) failed"
    echo "========================================="
    exit 1
fi
