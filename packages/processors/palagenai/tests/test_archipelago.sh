#!/bin/bash

  # Configuration
  API_URL="http://localhost:8001"
  EMAIL="bhushan0508@gmail.com"
  PASSWORD="abc@123"

  echo "========================================="
  echo "Archipelago Integration Test"
  echo "========================================="

  # Step 1: Login
  echo -e "\n1. Logging in..."
  LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$EMAIL\",
      \"password\": \"$PASSWORD\"
    }")

  # Check if login was successful
  if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo "✓ Login successful"
  else
    echo "✗ Login failed"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
  fi

  # Extract token
  TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
  echo "✓ Token obtained: ${TOKEN:0:30}..."

  # Step 2: Check Archipelago Connection
  echo -e "\n2. Checking Archipelago connection..."
  ARCHIPELAGO_RESPONSE=$(curl -s -X GET "$API_URL/api/archipelago/check-connection" \
    -H "Authorization: Bearer $TOKEN")

  echo "$ARCHIPELAGO_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ARCHIPELAGO_RESPONSE"

  # Step 3: Get Job History
  echo -e "\n3. Getting bulk job history..."
  HISTORY_RESPONSE=$(curl -s -X GET "$API_URL/api/bulk/history?page=1&limit=5" \
    -H "Authorization: Bearer $TOKEN")

  echo "$HISTORY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HISTORY_RESPONSE"

  echo -e "\n========================================="
  echo "Test Complete"
  echo "========================================="

