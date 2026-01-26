#!/bin/bash
# Performance Testing Script
# Runs virtual scrolling performance tests with 100K records

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Performance Testing: 60 FPS Scroll Test"
echo "========================================="
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if TABLE_ID is set
if [ -z "$TABLE_ID" ]; then
    echo -e "${RED}Error: TABLE_ID environment variable is not set${NC}"
    echo "Usage: TABLE_ID=<your_table_id> $0"
    echo ""
    echo "To get a table ID:"
    echo "1. Open the PyBase application"
    echo "2. Navigate to your test table"
    echo "3. Copy the table ID from the URL"
    exit 1
fi

echo -e "${GREEN}✓ TABLE_ID is set: $TABLE_ID${NC}"

# Check if frontend node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${RED}Error: Frontend dependencies not installed${NC}"
    echo "Run: cd frontend && npm install"
    exit 1
fi

echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Check if Playwright browsers are installed
if ! npx playwright --version > /dev/null 2>&1; then
    echo -e "${RED}Error: Playwright not found${NC}"
    echo "Run: cd frontend && npm install"
    exit 1
fi

echo -e "${GREEN}✓ Playwright installed${NC}"
echo ""

# Step 1: Seed database (if needed)
echo -e "${YELLOW}Step 1: Checking database...${NC}"
RECORD_COUNT=$(python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()
async def check():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    count = await conn.fetchval('SELECT COUNT(*) FROM records WHERE table_id = $1', '$TABLE_ID')
    await conn.close()
    print(count)
asyncio.run(check())
" 2>/dev/null || echo "0")

if [ "$RECORD_COUNT" -lt 100000 ]; then
    echo -e "${YELLOW}Current record count: $RECORD_COUNT${NC}"
    echo "Seeding database with 100K records..."
    python scripts/seed_large_dataset.py --table "$TABLE_ID" --count 100000
    echo -e "${GREEN}✓ Database seeded with 100K records${NC}"
else
    echo -e "${GREEN}✓ Database already has $RECORD_COUNT records${NC}"
fi
echo ""

# Step 2: Run performance tests
echo -e "${YELLOW}Step 2: Running performance tests...${NC}"
cd frontend

# Set environment variables for tests
export TABLE_ID="$TABLE_ID"
export BASE_URL="${BASE_URL:-http://localhost:5173}"

echo "Test configuration:"
echo "  TABLE_ID: $TABLE_ID"
echo "  BASE_URL: $BASE_URL"
echo ""

# Run Playwright tests
echo -e "${YELLOW}Starting Playwright tests...${NC}"
npx playwright test virtual-scrolling-performance.spec.ts --reporter=list

TEST_EXIT_CODE=$?

cd ..
echo ""

# Step 3: Display results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}All Performance Tests Passed! ✓${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "View detailed results:"
    echo "  frontend/test-results/index.html"
    echo ""
    echo "Performance metrics verified:"
    echo "  ✓ Average FPS: ~60"
    echo "  ✓ Memory usage: Constant (< 50MB increase)"
    echo "  ✓ DOM size: ~100 records (not 100K)"
    echo "  ✓ Scroll responsiveness: < 50ms per scroll"
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}Performance Tests Failed!${NC}"
    echo -e "${RED}=========================================${NC}"
    echo ""
    echo "View detailed results:"
    echo "  frontend/test-results/index.html"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if backend is running"
    echo "2. Verify TABLE_ID is correct"
    echo "3. Check database has 100K records"
    echo "4. Review test logs above"
    exit 1
fi
