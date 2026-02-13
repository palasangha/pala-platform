#!/usr/bin/env python3
"""Quick functional test of Samma AI"""

import requests
import time
import json

print("=" * 60)
print("🚀 Samma AI Functional Test")
print("=" * 60)

# Test 1: Frontend accessible
print("\n1️⃣ Frontend Test:")
try:
    response = requests.get("http://localhost:8080", timeout=5)
    if response.status_code == 200:
        print("   ✅ Frontend loading (status 200)")
        if "flutter" in response.text.lower():
            print("   ✅ Flutter app detected in HTML")
    else:
        print(f"   ❌ Frontend returned {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: API Health
print("\n2️⃣ API Health Test:")
try:
    response = requests.get("http://localhost:5001/api/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ API healthy: {data}")
    else:
        print(f"   ❌ API returned {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Chat API - No wait for response, just check if request is accepted
print("\n3️⃣ Chat API Test (async test - checking if request is accepted):")
try:
    payload = {"message": "What is dukkha?", "conversation_id": "quick-test"}
    
    # Use a 60 second timeout - more realistic
    response = requests.post(
        "http://localhost:5001/api/chat",
        json=payload,
        timeout=60
    )
    
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Chat API accepts and processes requests")
        print(f"   ✅ Response received (HTTP 200)")
        
        # Check response structure
        if 'response' in data:
            resp = data['response']
            has_parts = all(k in resp for k in ['database_summary', 'interpretive_summary', 'teachings', 'final_summary'])
            if has_parts:
                print("   ✅ Response has all 4 required parts")
                db_len = len(resp.get('database_summary', ''))
                print(f"      - Database summary: {db_len} chars")
                print(f"      - Teachings: {len(resp.get('teachings', []))} items")
            else:
                print("   ⚠️ Response missing some parts")
        
        print("\n   📄 Sample response (first 200 chars):")
        sample = json.dumps(data, indent=2)[:200]
        print("   " + "\n   ".join(sample.split("\n")))
        
    else:
        print(f"   ❌ Chat API returned {response.status_code}")
        
except requests.exceptions.Timeout:
    print("   ❌ Request timeout (>60 seconds) - still slow")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Test Complete")
print("=" * 60)
