#!/bin/bash

# Run Export Test Script
#
# This script executes the E2E export test for large datasets.
# It verifies that 100K+ records can be exported without timeout.

set -e  # Exit on error

echo "=== Large Dataset Export Test ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

# Check if TABLE_ID is set
if [ -z "$TABLE_ID" ]; then
    echo -e "${RED}Error: TABLE_ID environment variable is not set${NC}"
    echo "Set it with: export TABLE_ID=your-table-id"
    exit 1
fi
echo -e "${GREEN}✓ TABLE_ID is set${NC}"

# Check if AUTH_TOKEN is set
if [ -z "$AUTH_TOKEN" ]; then
    echo -e "${RED}Error: AUTH_TOKEN environment variable is not set${NC}"
    echo "Set it with: export AUTH_TOKEN=your-auth-token"
    exit 1
fi
echo -e "${GREEN}✓ AUTH_TOKEN is set${NC}"

# Check if API_BASE_URL is set
if [ -z "$API_BASE_URL" ]; then
    export API_BASE_URL="http://localhost:8000"
    echo -e "${YELLOW}⚠ API_BASE_URL not set, using default: $API_BASE_URL${NC}"
else
    echo -e "${GREEN}✓ API_BASE_URL is set${NC}"
fi

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo -e "${RED}Error: frontend directory not found${NC}"
    echo "Run this script from the project root directory"
    exit 1
fi
echo -e "${GREEN}✓ Frontend directory found${NC}"

# Check if Playwright is installed
cd frontend
if ! npx playwright --version > /dev/null 2>&1; then
    echo -e "${RED}Error: Playwright is not installed${NC}"
    echo "Install it with: cd frontend && npm install -D @playwright/test"
    exit 1
fi
cd ..
echo -e "${GREEN}✓ Playwright is installed${NC}"

# Check if test file exists
if [ ! -f "frontend/e2e/large-dataset-export.spec.ts" ]; then
    echo -e "${RED}Error: Test file not found: frontend/e2e/large-dataset-export.spec.ts${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Test file found${NC}"

echo ""
echo "=== Running Export Test ==="
echo ""

# Run the test
cd frontend

# Set environment variables for Playwright
export TABLE_ID="$TABLE_ID"
export AUTH_TOKEN="$AUTH_TOKEN"
export API_BASE_URL="$API_BASE_URL"

# Run Playwright test
npx playwright test large-dataset-export.spec.ts --reporter=list

TEST_EXIT_CODE=$?

cd ..

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== Export Test Passed ===${NC}"
    echo ""
    echo "Verification results:"
    echo "✓ Export starts immediately (HTTP 202)"
    echo "✓ Download completes successfully"
    echo "✓ Exported file contains all records"
    echo "✓ Streaming works with progress tracking"
    echo ""
    echo "Large dataset export is working correctly!"
else
    echo -e "${RED}=== Export Test Failed ===${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if backend server is running at $API_BASE_URL"
    echo "2. Verify TABLE_ID exists and has 100K+ records"
    echo "3. Verify AUTH_TOKEN is valid"
    echo "4. Check backend logs for errors"
    echo "5. Run test with DEBUG=pw:api to see detailed logs"
fi

exit $TEST_EXIT_CODE
