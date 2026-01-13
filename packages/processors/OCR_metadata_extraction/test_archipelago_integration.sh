#!/bin/bash

# =============================================================================
# Archipelago Integration Test Script
# =============================================================================
# This script will:
# 1. Login to GVPOCR and get a JWT token
# 2. Check Archipelago connection status
# 3. Fetch your bulk job history
# 4. Show how to push a job to Archipelago
# =============================================================================

# Configuration
API_URL="http://localhost:5000"
EMAIL="bhushan0508@gmail.com"  # Replace with your GVPOCR email
PASSWORD="abc@123"         # Replace with your GVPOCR password

echo "=========================================="
echo "Archipelago Integration Test"
echo "=========================================="
echo ""

# Step 1: Login and get token
echo "Step 1: Logging in to GVPOCR..."
echo "-------------------------------------------"

LOGIN_RESPONSE=$(curl -s -X POST \
  "${API_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${EMAIL}\",
    \"password\": \"${PASSWORD}\"
  }")

# Extract token from response (field name is 'access_token')
# Try jq first, fall back to Python if not available
if command -v jq &> /dev/null; then
  TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
else
  TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
fi

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Login failed!"
  echo "Response: $LOGIN_RESPONSE"
  echo ""
  echo "Please check:"
  echo "  - Your email and password are correct"
  echo "  - The backend is running (docker-compose ps)"
  echo "  - You've replaced YOUR_EMAIL and YOUR_PASSWORD in this script"
  exit 1
fi

echo "✅ Login successful!"
echo "Token obtained: ${TOKEN:0:20}...${TOKEN: -10}"
echo ""

# Step 2: Check Archipelago connection
echo "Step 2: Checking Archipelago connection..."
echo "-------------------------------------------"

ARCHIPELAGO_STATUS=$(curl -s -X GET \
  "${API_URL}/api/archipelago/check-connection" \
  -H "Authorization: Bearer ${TOKEN}")

echo "$ARCHIPELAGO_STATUS" | python3 -m json.tool 2>/dev/null || echo "$ARCHIPELAGO_STATUS"
echo ""

# Check if Archipelago is enabled
ARCHIPELAGO_ENABLED=$(echo $ARCHIPELAGO_STATUS | grep -o '"enabled":[^,}]*' | sed 's/"enabled"://')

if [ "$ARCHIPELAGO_ENABLED" = "true" ]; then
  echo "✅ Archipelago integration is ENABLED"
else
  echo "⚠️  Archipelago integration is DISABLED"
  echo "To enable it, set ARCHIPELAGO_ENABLED=true in your .env file"
fi
echo ""

# Step 3: Fetch job history
echo "Step 3: Fetching bulk job history..."
echo "-------------------------------------------"

JOB_HISTORY=$(curl -s -X GET \
  "${API_URL}/api/bulk/history?page=1&limit=10" \
  -H "Authorization: Bearer ${TOKEN}")

echo "$JOB_HISTORY" | python3 -m json.tool 2>/dev/null || echo "$JOB_HISTORY"
echo ""

# Extract first completed job ID
JOB_ID=$(echo $JOB_HISTORY | grep -o '"job_id":"[^"]*' | head -1 | sed 's/"job_id":"//')
JOB_STATUS=$(echo $JOB_HISTORY | grep -o '"status":"[^"]*' | head -1 | sed 's/"status":"//')

if [ -n "$JOB_ID" ]; then
  echo "Found job: $JOB_ID (status: $JOB_STATUS)"
  echo ""

  # Step 4: Show how to push to Archipelago (only if job is completed)
  if [ "$JOB_STATUS" = "completed" ]; then
    echo "Step 4: Pushing job to Archipelago..."
    echo "-------------------------------------------"
    echo "Attempting to push job $JOB_ID to Archipelago..."
    echo ""

    PUSH_RESPONSE=$(curl -s -X POST \
      "${API_URL}/api/archipelago/push-bulk-job" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{
        \"job_id\": \"${JOB_ID}\",
        \"collection_title\": \"Test Collection from GVPOCR\",
        \"collection_description\": \"Automated test of Archipelago integration\",
        \"tags\": [\"ocr\", \"test\", \"gvpocr\"]
      }")

    echo "$PUSH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PUSH_RESPONSE"
    echo ""

    # Check if push was successful
    if echo "$PUSH_RESPONSE" | grep -q '"success":true'; then
      echo "✅ Successfully pushed job to Archipelago!"
      echo ""
      echo "You should now see your documents in Archipelago at:"
      ARCHIPELAGO_URL=$(echo "$PUSH_RESPONSE" | grep -o '"archipelago_url":"[^"]*' | sed 's/"archipelago_url":"//')
      echo "  $ARCHIPELAGO_URL"
    else
      echo "❌ Failed to push to Archipelago"
      echo "This could be because:"
      echo "  - Archipelago is not running"
      echo "  - Archipelago credentials are incorrect"
      echo "  - Network connectivity issues"
    fi
  else
    echo "⚠️  Job is not completed yet (status: $JOB_STATUS)"
    echo "Only completed jobs can be pushed to Archipelago."
    echo ""
    echo "To test pushing to Archipelago:"
    echo "1. Run a bulk OCR job first"
    echo "2. Wait for it to complete"
    echo "3. Run this script again"
  fi
else
  echo "⚠️  No bulk jobs found in history"
  echo ""
  echo "To test the complete workflow:"
  echo "1. Go to http://localhost:3000"
  echo "2. Navigate to 'Bulk OCR'"
  echo "3. Process some documents"
  echo "4. Run this script again to see the job history"
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Your JWT token: ${TOKEN:0:30}..."
echo "  - Use this token in the Authorization header for API requests"
echo "  - Token format: 'Bearer ${TOKEN}'"
echo ""
echo "Next steps:"
echo "  1. If Archipelago is disabled, enable it in .env"
echo "  2. Process some bulk OCR jobs if you haven't already"
echo "  3. Use the 'Push to Archipelago' button in the job history UI"
echo ""
