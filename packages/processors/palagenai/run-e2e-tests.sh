#!/bin/bash

# RBAC E2E Test Runner Script
# Runs comprehensive Playwright tests for RBAC workflows

set -e

echo "🎭 RBAC E2E Test Suite"
echo "======================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "📡 Checking services..."
if ! curl -sk https://localhost:3000 > /dev/null 2>&1; then
    echo -e "${RED}❌ Frontend not accessible at https://localhost:3000${NC}"
    echo "Please ensure docker-compose services are running"
    exit 1
fi

if ! curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend health check failed${NC}"
    echo "Continuing anyway..."
fi

echo -e "${GREEN}✓ Services are running${NC}"
echo ""

# Install Playwright browsers if not already installed
echo "📦 Installing Playwright browsers..."
cd frontend
if ! npx playwright install chromium --with-deps > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Browser installation failed, trying without deps...${NC}"
    npx playwright install chromium
fi

echo ""
echo "🧪 Running E2E Tests..."
echo "======================="
echo ""

# Run tests
if [ "$1" == "--ui" ]; then
    echo "Opening Playwright UI..."
    npm run test:e2e:ui
elif [ "$1" == "--debug" ]; then
    echo "Running in debug mode..."
    npx playwright test --debug
elif [ "$1" == "--headed" ]; then
    echo "Running in headed mode..."
    npx playwright test --headed
else
    # Run all tests
    npm run test:e2e
    TEST_EXIT_CODE=$?
    
    echo ""
    echo "======================="
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
    else
        echo -e "${RED}❌ Some tests failed${NC}"
    fi
    
    echo ""
    echo "📊 View detailed report with:"
    echo "   npm run test:e2e:report"
    echo ""
    
    exit $TEST_EXIT_CODE
fi
