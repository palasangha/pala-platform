#!/bin/bash

# AMI Sets Endpoint Test Script
# This script tests the AMI Sets upload functionality

echo "=========================================="
echo "AMI Sets Upload Test"
echo "=========================================="
echo ""

# Configuration
BACKEND_URL="http://localhost:5000"
ARCHIPELAGO_URL="http://localhost:8001"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check if backend is running
echo "1. Checking backend status..."
if curl -s "${BACKEND_URL}/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not accessible at ${BACKEND_URL}${NC}"
    echo "Please start the backend first: docker-compose up backend"
    exit 1
fi

# Step 2: Login to get JWT token
echo ""
echo "2. Logging in to get authentication token..."
read -p "Enter username (default: test@example.com): " USERNAME
USERNAME=${USERNAME:-test@example.com}

read -sp "Enter password: " PASSWORD
echo ""

LOGIN_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*' | grep -o '[^"]*$')

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed. Please check your credentials.${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Successfully logged in${NC}"
echo "Token: ${TOKEN:0:20}..."

# Step 3: List recent bulk jobs
echo ""
echo "3. Fetching recent bulk jobs..."
JOBS_RESPONSE=$(curl -s -X GET "${BACKEND_URL}/api/bulk/jobs" \
  -H "Authorization: Bearer ${TOKEN}")

echo "$JOBS_RESPONSE" | python3 -m json.tool 2>/dev/null | head -30

# Extract a completed job ID
JOB_ID=$(echo "$JOBS_RESPONSE" | grep -o '"job_id":"[^"]*' | head -1 | grep -o '[^"]*$')

if [ -z "$JOB_ID" ]; then
    echo ""
    echo -e "${YELLOW}⚠ No bulk jobs found.${NC}"
    echo "Please run a bulk OCR job first:"
    echo "  1. Go to the frontend bulk processing page"
    echo "  2. Select a folder (e.g., 'eng-typed')"
    echo "  3. Start bulk processing"
    echo "  4. Wait for completion"
    echo "  5. Re-run this test script"
    exit 0
fi

echo ""
echo -e "${GREEN}✓ Found bulk job: ${JOB_ID}${NC}"

# Step 4: Test AMI Sets upload
echo ""
echo "4. Testing AMI Sets upload..."
read -p "Enter collection title (default: Test Collection): " COLLECTION_TITLE
COLLECTION_TITLE=${COLLECTION_TITLE:-Test Collection}

echo ""
echo "Uploading via AMI Sets..."
AMI_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/archipelago/push-bulk-ami" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"${JOB_ID}\",
    \"collection_title\": \"${COLLECTION_TITLE}\"
  }")

echo "$AMI_RESPONSE" | python3 -m json.tool 2>/dev/null

# Check if successful
if echo "$AMI_RESPONSE" | grep -q '"success":true'; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ AMI Set Created Successfully!"
    echo "==========================================${NC}"

    AMI_SET_ID=$(echo "$AMI_RESPONSE" | grep -o '"ami_set_id":[0-9]*' | grep -o '[0-9]*$')
    TOTAL_DOCS=$(echo "$AMI_RESPONSE" | grep -o '"total_documents":[0-9]*' | grep -o '[0-9]*$')

    echo ""
    echo "AMI Set ID: $AMI_SET_ID"
    echo "Total Documents: $TOTAL_DOCS"
    echo ""
    echo "Next Steps:"
    echo "  1. Open: ${ARCHIPELAGO_URL}/amiset/${AMI_SET_ID}/process"
    echo "  2. Review configuration"
    echo "  3. Click 'Process' tab"
    echo "  4. Choose processing method"
    echo "  5. Monitor progress"
    echo ""

    read -p "Open processing URL in browser? (y/n): " OPEN_BROWSER
    if [ "$OPEN_BROWSER" = "y" ] || [ "$OPEN_BROWSER" = "Y" ]; then
        xdg-open "${ARCHIPELAGO_URL}/amiset/${AMI_SET_ID}/process" 2>/dev/null || \
        open "${ARCHIPELAGO_URL}/amiset/${AMI_SET_ID}/process" 2>/dev/null || \
        echo "Please manually open: ${ARCHIPELAGO_URL}/amiset/${AMI_SET_ID}/process"
    fi
else
    echo ""
    echo -e "${RED}=========================================="
    echo "✗ AMI Set Creation Failed"
    echo "==========================================${NC}"

    ERROR=$(echo "$AMI_RESPONSE" | grep -o '"error":"[^"]*' | grep -o '[^"]*$')
    echo "Error: $ERROR"
    echo ""
    echo "Possible causes:"
    echo "  - Bulk job not completed yet"
    echo "  - No successful OCR results in job"
    echo "  - Archipelago connection issue"
    echo "  - File permissions issue"
    echo ""
    echo "Check backend logs: docker-compose logs backend"
fi

echo ""
echo "Test complete."
